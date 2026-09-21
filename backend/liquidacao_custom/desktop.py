from __future__ import annotations

import argparse
import ctypes
import io
import json
import os
import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn

from liquidacao_custom.api.main import app
from liquidacao_custom.metadata import APP_DISPLAY_VERSION, APP_ID, APP_NAME

_mutex = None
_null_streams = []


def _ensure_standard_streams() -> None:
    """Fornece saídas válidas quando o executável Windows não possui console."""
    for name in ("stdout", "stderr"):
        if getattr(sys, name, None) is None:
            stream = open(os.devnull, "w", encoding="utf-8")
            _null_streams.append(stream)
            setattr(sys, name, stream)


def _ensure_mcp_standard_streams() -> None:
    """Recupera os pipes herdados pelo executável Windows sem console.

    O PyInstaller define stdin/stdout como ``None`` em aplicativos windowed.
    Quando o Codex inicia o executável, os handles do processo continuam sendo
    pipes válidos e precisam ser convertidos novamente em streams Python.
    """
    if sys.stdin is not None and sys.stdout is not None:
        return
    if os.name != "nt":
        raise RuntimeError("O transporte MCP por STDIO não encontrou stdin/stdout.")
    import msvcrt

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetStdHandle.argtypes = [ctypes.c_uint32]
    kernel.GetStdHandle.restype = ctypes.c_void_p
    invalid_handle = ctypes.c_void_p(-1).value

    def abrir(codigo: int, modo: str):
        handle = kernel.GetStdHandle(ctypes.c_uint32(codigo).value)
        if handle in (0, invalid_handle):
            raise RuntimeError("O Codex não forneceu um pipe STDIO válido ao conector.")
        flags = os.O_BINARY | (os.O_RDONLY if "r" in modo else os.O_WRONLY)
        descritor = msvcrt.open_osfhandle(handle, flags)
        bruto = os.fdopen(descritor, modo + "b", buffering=0)
        return io.TextIOWrapper(
            bruto,
            encoding="utf-8",
            errors="replace" if "r" in modo else "strict",
            newline="\n",
            write_through="w" in modo,
        )

    if sys.stdin is None:
        sys.stdin = abrir(-10, "r")
    if sys.stdout is None:
        sys.stdout = abrir(-11, "w")
    if sys.stderr is None:
        stream = open(os.devnull, "w", encoding="utf-8")
        _null_streams.append(stream)
        sys.stderr = stream


def _message(text: str, flags: int = 0x10) -> None:
    if os.name == "nt":
        ctypes.windll.user32.MessageBoxW(None, text, APP_NAME, flags)
    else:
        print(text, file=sys.stderr)


def _single_instance() -> bool:
    global _mutex
    if os.name != "nt":
        return True
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    _mutex = kernel.CreateMutexW(None, False, f"Local\\CalculosJuridicos-{APP_ID}")
    return bool(_mutex) and ctypes.get_last_error() != 183


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _wait_server(port: int) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("O serviço local não iniciou no tempo esperado.")


def self_check() -> int:
    package = Path(__file__).resolve().parent
    api_paths = set(app.openapi().get("paths", {}))
    try:
        import webview

        _enable_webview_downloads(webview)
        downloads_enabled = webview.settings["ALLOW_DOWNLOADS"] is True
    except Exception:
        downloads_enabled = False
    try:
        from liquidacao_custom.mcp_server import nomes_ferramentas

        ferramentas = nomes_ferramentas()
        mcp_ok = {
            "calcular_debito_judicial",
            "gerar_pdf_debito_judicial",
            "gerar_pdf_honorarios_proveito_economico",
        }.issubset(ferramentas)
    except Exception:
        mcp_ok = False
    checks = {
        "interface": (package / "web/index.html").is_file(),
        "logo": (package / "assets/logo-barreto-fontes.png").is_file(),
        "api": "/api/v1/calculo" in api_paths,
        "atualizacoes": "/api/v1/app/info" in api_paths,
        "downloads": downloads_enabled,
        "mcp": mcp_ok,
    }
    print(json.dumps({"sucesso": all(checks.values()), "itens": checks}, ensure_ascii=False))
    return 0 if all(checks.values()) else 1


def _enable_webview_downloads(webview_module) -> None:
    """Permite que a janela desktop abra o diálogo nativo de salvamento."""
    webview_module.settings["ALLOW_DOWNLOADS"] = True


def run() -> int:
    _ensure_standard_streams()
    if not _single_instance():
        _message("Cálculos Jurídicos já está aberto.", 0x40)
        return 0
    port = _free_port()
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
        log_config=None,
    )
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None
    thread = threading.Thread(target=server.run, name="calculos-api", daemon=True)
    thread.start()
    try:
        _wait_server(port)
        import webview

        _enable_webview_downloads(webview)
        webview.create_window(
            f"{APP_NAME} {APP_DISPLAY_VERSION}",
            f"http://127.0.0.1:{port}/#/processamento",
            width=1420,
            height=900,
            min_size=(900, 650),
            background_color="#F7F5F0",
            text_select=True,
        )
        webview.start(gui="edgechromium", debug=False)
        return 0
    except Exception as exc:
        _message(f"Não foi possível abrir o aplicativo.\n\n{exc}")
        return 1
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--mcp", action="store_true")
    parser.add_argument("--install-codex-plugin", action="store_true")
    parser.add_argument("--uninstall-codex-plugin", action="store_true")
    arguments, _ = parser.parse_known_args()
    if arguments.self_check:
        _ensure_standard_streams()
        return self_check()
    if arguments.mcp:
        _ensure_mcp_standard_streams()
        from liquidacao_custom.mcp_server import run as run_mcp

        run_mcp()
        return 0
    if arguments.install_codex_plugin:
        _ensure_standard_streams()
        from liquidacao_custom.codex_integration import install_codex_plugin

        print(json.dumps(install_codex_plugin(Path(sys.executable)), ensure_ascii=False))
        return 0
    if arguments.uninstall_codex_plugin:
        _ensure_standard_streams()
        from liquidacao_custom.codex_integration import uninstall_codex_plugin

        print(json.dumps(uninstall_codex_plugin(), ensure_ascii=False))
        return 0
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
