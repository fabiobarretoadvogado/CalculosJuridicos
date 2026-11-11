from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


APP_ID = "7d3d1b6f-7c56-4f0e-8a63-1aa1dc62c5f4"
SERVER_NAME = "calculos-juridicos"
DEFAULT_PORT = 49179
SERVICE_FILES = ("shared_host.py", "frozen_runtime.py", "manage.py", "register_service.ps1", "stop_service.ps1")
SERVER_TABLE = '[mcp_servers."calculos-juridicos"]'
HEADERS_TABLE = '[mcp_servers."calculos-juridicos".http_headers]'
POLICY_TABLE = '[plugins."calculos-juridicos@personal".mcp_servers."calculos-juridicos"]'


def service_root(home: Path | None = None) -> Path:
    return (home or Path.home()).resolve() / ".codex" / "integrations" / SERVER_NAME


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    try:
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _toml_loads(content: str) -> dict:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib
    return tomllib.loads(content)


def _header_keys(header: str) -> tuple[str, ...]:
    tokens = re.findall(r'''"(?:\\.|[^"\\])*"|'[^']*'|[A-Za-z0-9_-]+''', header[1:-1])
    return tuple(json.loads(token) if token.startswith('"') else token.strip("'") for token in tokens)


def _section(content: str, header: str) -> tuple[int, int, int] | None:
    headers = list(re.finditer(r"(?m)^[ \t]*(\[[^\r\n]+\])[ \t]*(?:#[^\r\n]*)?$", content))
    expected = _header_keys(header)
    for index, found in enumerate(headers):
        if _header_keys(found.group(1)) == expected:
            end = headers[index + 1].start() if index + 1 < len(headers) else len(content)
            return found.start(), found.end(), end
    return None


def _without_stdio_fields(content: str) -> str:
    section = _section(content, SERVER_TABLE)
    if section is None:
        return content
    start, body_start, end = section
    lines = content[body_start:end].splitlines(keepends=True)
    retained = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if re.match(r"^[ \t]*(command|args|env|env_vars|cwd)[ \t]*=", line):
            value = line.split("=", 1)[1]
            while True:
                try:
                    _toml_loads("value = " + value)
                    break
                except ValueError:
                    index += 1
                    if index >= len(lines):
                        raise ValueError("Configuração STDIO incompleta.")
                    value += lines[index]
        else:
            retained.append(line)
        index += 1
    result = content[:body_start] + "".join(retained) + content[end:]
    return _remove_section(result, '[mcp_servers."calculos-juridicos".env]')


def table_fields(content: str, header: str, values: dict[str, str]) -> str:
    section = _section(content, header)
    if section:
        start, body_start, end = section
        body = content[body_start:end]
        for key, value in values.items():
            assignment = f"{key} = {value}"
            expression = r"(?m)^[ \t]*" + re.escape(key) + r"[ \t]*=.*$"
            if re.search(expression, body):
                body = re.sub(expression, lambda match: assignment, body)
            else:
                body = body.rstrip() + "\n" + assignment + "\n"
        return content[:body_start] + "\n" + body.strip() + "\n\n" + content[end:]
    return content.rstrip() + "\n\n" + header + "\n" + "\n".join(f"{key} = {value}" for key, value in values.items()) + "\n"


def _remove_section(content: str, header: str) -> str:
    section = _section(content, header)
    if section is None:
        return content
    start, body_start, end = section
    return content[:start] + content[end:]


def _run_powershell(script: Path, arguments: list[str]) -> None:
    if os.name != "nt":
        raise RuntimeError("O serviço compartilhado requer Windows.")
    powershell = Path(os.environ["WINDIR"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    result = subprocess.run(
        [str(powershell), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script), *arguments],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=90, creationflags=subprocess.CREATE_NO_WINDOW, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"Falha ao executar {script.name}.")


def stop_shared_service(executable: Path, *, home: Path | None = None, remove_task: bool = False) -> None:
    root = service_root(home)
    source = executable.parent / "codex-service"
    script = source / "stop_service.ps1"
    if not script.is_file():
        script = Path(__file__).parent / "stop_service.ps1"
    arguments = ["-ServiceRoot", str(root), "-Executable", str(executable)]
    if remove_task:
        arguments.append("-RemoveTask")
    _run_powershell(script, arguments)


def _remove_owned_directory(path: Path, root: Path) -> None:
    if not path.exists():
        return
    resolved = path.resolve()
    resolved.relative_to(root.resolve())
    if resolved == root.resolve():
        raise ValueError("A raiz do serviço não pode ser apagada recursivamente.")
    shutil.rmtree(path)


def prepare_shared_service(executable: Path, *, home: Path | None = None, install_runtime: bool = True) -> dict:
    executable = executable.resolve()
    root = service_root(home)
    packaged = executable.parent / "codex-service"
    source = packaged if (packaged / "shared_host.py").is_file() else Path(__file__).parent
    if install_runtime:
        if not (packaged / "runtime/pythonw.exe").is_file():
            raise FileNotFoundError("O pacote não contém o ambiente do serviço MCP.")
        stop_shared_service(executable, home=home)
    root.mkdir(parents=True, exist_ok=True)
    for filename in SERVICE_FILES:
        shutil.copy2(source / filename, root / filename)
    if install_runtime:
        runtime = root / "runtime"
        source_runtime = packaged / "runtime"
        source_marker = (source_runtime / "ready.json").read_bytes()
        target_marker = runtime / "ready.json"
        if not target_marker.is_file() or target_marker.read_bytes() != source_marker:
            _remove_owned_directory(runtime, root)
            shutil.copytree(source_runtime, runtime)
    settings_file = root / "settings.json"
    settings = json.loads(settings_file.read_text(encoding="utf-8")) if settings_file.is_file() else {}
    if not isinstance(settings, dict):
        raise ValueError("A configuração do serviço é inválida.")
    token = settings.get("token")
    if not isinstance(token, str) or len(token) < 32:
        token = secrets.token_urlsafe(32)
    port = int(settings.get("port", DEFAULT_PORT))
    if not 1024 <= port <= 65535:
        raise ValueError("A porta do serviço local é inválida.")
    settings.update(executable=str(executable), owner_app_id=APP_ID, token=token, port=port)
    atomic_text(settings_file, json.dumps(settings, ensure_ascii=False, indent=2) + "\n")
    atomic_text(root / "managed.json", json.dumps({"app_id": APP_ID, "files": list(SERVICE_FILES)}, indent=2))
    return {
        "root": str(root), "url": f"http://127.0.0.1:{port}/mcp",
        "headers": {"Authorization": f"Bearer {token}"},
    }


def configure_codex(service: dict, *, home: Path | None = None) -> None:
    config = (home or Path.home()).resolve() / ".codex/config.toml"
    original = config.read_text(encoding="utf-8") if config.is_file() else ""
    _toml_loads(original)
    content = table_fields(_without_stdio_fields(original), POLICY_TABLE, {"enabled": "false"})
    content = table_fields(content, SERVER_TABLE, {
        "url": json.dumps(service["url"]), "enabled": "true",
        "startup_timeout_sec": "30", "tool_timeout_sec": "120",
    })
    content = table_fields(content, HEADERS_TABLE, {"Authorization": json.dumps(service["headers"]["Authorization"])})
    _toml_loads(content)
    if original == content:
        return
    if config.is_file():
        backup = service_root(home) / "backups" / f"config-before-install-{time.time_ns()}.toml"
        backup.parent.mkdir(parents=True, exist_ok=True)
        atomic_text(backup, original)
    atomic_text(config, content)


def check_service(*, home: Path | None = None) -> dict:
    root = service_root(home)
    settings = json.loads((root / "settings.json").read_text(encoding="utf-8"))
    request = urllib.request.Request(
        f"http://127.0.0.1:{int(settings['port'])}/health",
        headers={"Authorization": f"Bearer {settings['token']}"},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=5) as response:
        result = json.load(response)
    if result.get("service") != "calculos-juridicos-mcp":
        raise RuntimeError("O processo local não é o servidor esperado.")
    identity = Path(settings["executable"]).parent / "app-info.json"
    if identity.is_file():
        expected = json.loads(identity.read_text(encoding="utf-8"))["display_version"]
        if result.get("version") != expected:
            raise RuntimeError("O serviço está executando uma edição diferente da instalação.")
    return result


def start_shared_service(*, home: Path | None = None) -> dict:
    root = service_root(home)
    _run_powershell(root / "register_service.ps1", ["-ServiceRoot", str(root)])
    deadline = time.monotonic() + 60
    last_error = None
    while time.monotonic() < deadline:
        try:
            return check_service(home=home)
        except (OSError, ValueError, RuntimeError, urllib.error.URLError) as error:
            last_error = error
            time.sleep(0.25)
    raise RuntimeError("O serviço compartilhado não ficou disponível. Consulte host.log.") from last_error


def remove_shared_service(executable: Path | None = None, *, home: Path | None = None, stop: bool = True) -> None:
    root = service_root(home)
    settings_file = root / "settings.json"
    if not settings_file.is_file():
        return
    settings = json.loads(settings_file.read_text(encoding="utf-8"))
    if settings.get("owner_app_id") not in (None, APP_ID):
        raise ValueError("O serviço pertence a outro aplicativo.")
    if stop:
        stop_shared_service(executable or Path(settings["executable"]), home=home, remove_task=True)
    config = (home or Path.home()).resolve() / ".codex/config.toml"
    if config.is_file():
        original = config.read_text(encoding="utf-8")
        server = _section(original, SERVER_TABLE)
        headers = _section(original, HEADERS_TABLE)
        expected_url = json.dumps(f"http://127.0.0.1:{int(settings['port'])}/mcp")
        expected_token = json.dumps(f"Bearer {settings['token']}")
        if server and headers:
            server_body = original[server[1]:server[2]]
            headers_body = original[headers[1]:headers[2]]
            matches_url = re.search(r"(?m)^[ \t]*url[ \t]*=[ \t]*" + re.escape(expected_url) + r"[ \t]*$", server_body)
            matches_token = re.search(r"(?m)^[ \t]*Authorization[ \t]*=[ \t]*" + re.escape(expected_token) + r"[ \t]*$", headers_body)
            if matches_url and matches_token:
                content = _remove_section(_remove_section(original, HEADERS_TABLE), SERVER_TABLE)
                policy = _section(content, POLICY_TABLE)
                if policy and content[policy[1]:policy[2]].strip() == "enabled = false":
                    content = _remove_section(content, POLICY_TABLE)
                atomic_text(config, content)
    for directory in ("runtime", "payloads", "__pycache__"):
        _remove_owned_directory(root / directory, root)
    for filename in (*SERVICE_FILES, "settings.json", "managed.json", "instance.json", "host.lock"):
        (root / filename).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("install", "uninstall", "stop", "check"))
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--home", type=Path)
    arguments = parser.parse_args()
    if arguments.action == "stop":
        stop_shared_service(arguments.executable, home=arguments.home)
        return 0
    if arguments.action == "check":
        check_service(home=arguments.home)
        return 0
    from frozen_runtime import mount_installed

    mount_installed(arguments.executable)
    from liquidacao_custom.codex_integration import install_codex_plugin, uninstall_codex_plugin

    if arguments.action == "install":
        result = install_codex_plugin(arguments.executable, home=arguments.home)
    else:
        result = uninstall_codex_plugin(home=arguments.home)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    log_root = service_root()
    log_root.mkdir(parents=True, exist_ok=True)
    with open(log_root / "installation.log", "a", encoding="utf-8", buffering=1) as log:
        if sys.stdout is None:
            sys.stdout = log
        if sys.stderr is None:
            sys.stderr = log
        try:
            raise SystemExit(main())
        except Exception:
            import traceback

            traceback.print_exc()
            raise SystemExit(1)
