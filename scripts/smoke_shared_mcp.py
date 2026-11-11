from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import ctypes
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


class Client:
    def __init__(self, url: str, token: str):
        self.url = url
        self.headers = {"Authorization": f"Bearer {token}"}
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def health(self, headers=None):
        request = urllib.request.Request(self.url + "/health", headers=self.headers if headers is None else headers)
        with self.opener.open(request, timeout=5) as response:
            return json.load(response)

    def rpc(self, method, params=None):
        headers = dict(self.headers, **{"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-06-18"})
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}).encode()
        request = urllib.request.Request(self.url + "/mcp", payload, headers)
        with self.opener.open(request, timeout=30) as response:
            result = json.load(response)
        if "error" in result:
            raise RuntimeError(result["error"])
        return result["result"]

    def verify_client(self, index):
        self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": f"distribution-test-{index}", "version": "1.0"}})
        tools = self.rpc("tools/list")["tools"]
        if len(tools) != 9:
            raise AssertionError("O pacote não expõe as nove ferramentas.")
        result = self.rpc("tools/call", {"name": "informacoes_aplicativo", "arguments": {}})
        if result.get("isError"):
            raise AssertionError(result)
        return self.health()["pid"]


def idle_cpu(process):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetProcessTimes.argtypes = [ctypes.c_void_p] + [ctypes.POINTER(ctypes.c_ulonglong)] * 4

    def seconds():
        values = [ctypes.c_ulonglong() for index in range(4)]
        if not kernel.GetProcessTimes(int(process._handle), *[ctypes.byref(value) for value in values]):
            raise ctypes.WinError(ctypes.get_last_error())
        return (values[2].value + values[3].value) / 10000000

    initial = seconds()
    started = time.monotonic()
    time.sleep(5)
    return 100 * (seconds() - initial) / (time.monotonic() - started) / os.cpu_count()


def validate(executable: Path, directory: Path):
    payload = executable.parent
    runtime = payload / "codex-service/runtime/python.exe"
    host = payload / "codex-service/shared_host.py"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    token = secrets.token_urlsafe(32)
    (directory / "settings.json").write_text(json.dumps({"executable": str(executable), "port": port, "token": token}), encoding="utf-8")
    environment = {
        key: value for key, value in os.environ.items()
        if key not in ("PYTHONPATH", "PYTHONHOME") and not key.startswith("_PYI_") and not key.startswith("CALCULOS_BUILD_")
    }
    environment["CALCULOS_JURIDICOS_DATA_DIR"] = str(directory / "isolated-data")
    environment["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    arguments = [str(runtime), "-E", "-s", str(host), "--service-root", str(directory)]
    process = subprocess.Popen(arguments, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    client = Client(f"http://127.0.0.1:{port}", token)
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if process.poll() is not None:
                log = directory / "host.log"
                raise RuntimeError(log.read_text(encoding="utf-8")[-5000:] if log.is_file() else "O serviço não iniciou.")
            try:
                health = client.health()
                break
            except OSError:
                time.sleep(0.25)
        else:
            raise TimeoutError("O serviço empacotado não ficou disponível.")
        expected = json.loads((payload / "app-info.json").read_text(encoding="utf-8"))["display_version"]
        if health["version"] != expected:
            raise AssertionError("A edição do serviço difere do pacote.")
        with ThreadPoolExecutor(max_workers=8) as executor:
            identifiers = set(executor.map(client.verify_client, range(8)))
        if identifiers != {process.pid}:
            raise AssertionError("Os clientes não compartilharam o mesmo servidor.")
        for headers in ({}, {"Authorization": "Bearer invalid"}):
            try:
                client.health(headers)
            except urllib.error.HTTPError as error:
                if error.code != 401:
                    raise
            else:
                raise AssertionError("Uma conexão não autenticada foi aceita.")
        repeated = subprocess.Popen(arguments, env=environment, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            if repeated.wait(timeout=10) != 0:
                raise AssertionError("A trava não rejeitou a segunda instância corretamente.")
        finally:
            if repeated.poll() is None:
                repeated.terminate()
                repeated.wait(timeout=10)
        entry = {
            "perfil": "selic_cjf_v1",
            "dados_gerais": {"data_base": "2026-08-31", "processo": "AUTOTESTE-SERVICO-MCP"},
            "parcelas": [{"numero": 1, "historico": "Parcela sintética", "data_vencimento": "2026-08-01", "valor_bruto": "1000.00"}],
        }
        calculation = client.rpc("tools/call", {"name": "calcular_debito_judicial", "arguments": {"calculo": entry}})
        if calculation.get("isError") or calculation["structuredContent"]["quantidade_parcelas"] != 1:
            raise AssertionError(calculation)
        pdf = client.rpc("tools/call", {"name": "gerar_pdf_debito_judicial", "arguments": {"calculo": entry, "nome_arquivo": "autoteste-servico.pdf", "pasta_destino": str(directory)}})
        if pdf.get("isError"):
            raise AssertionError(pdf)
        report = Path(pdf["structuredContent"]["arquivo"])
        if not report.read_bytes().startswith(b"%PDF-"):
            raise AssertionError("O arquivo gerado não é um PDF.")
        consumption = idle_cpu(process)
        if consumption >= 0.5:
            raise AssertionError(f"CPU em repouso acima do limite: {consumption:.3f}%")
        return {"sucesso": True, "edicao": expected, "clientes_simultaneos": 8, "instancia_unica": True, "autenticacao": True, "cpu_repouso_percentual": round(consumption, 4), "pdf_bytes": report.stat().st_size}
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


def main():
    if len(sys.argv) not in (2, 3):
        raise SystemExit("Uso: smoke_shared_mcp.py EXECUTAVEL [PASTA_TEMPORARIA]")
    executable = Path(sys.argv[1]).resolve(strict=True)
    temporary_root = Path(sys.argv[2]).resolve(strict=True) if len(sys.argv) == 3 else executable.parent
    with tempfile.TemporaryDirectory(prefix="shared-mcp-test-", dir=temporary_root) as temporary:
        directory = Path(temporary)
        directory.resolve().relative_to(temporary_root)
        result = validate(executable, directory)
    (temporary_root / "validacao-servico-mcp.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
