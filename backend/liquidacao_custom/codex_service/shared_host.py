import hashlib
import faulthandler
import hmac
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
import traceback

if __package__:
    from .frozen_runtime import mount_installed
else:
    from frozen_runtime import mount_installed


ROOT = Path(__file__).resolve().parent


class LocalAuthentication:
    def __init__(self, app, token, version):
        self.app = app
        self.authorization = f"Bearer {token}".encode("ascii")
        self.version = version

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        authorized = hmac.compare_digest(headers.get(b"authorization", b""), self.authorization)
        if not authorized:
            await send({"type": "http.response.start", "status": 401, "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": b'{"error":"unauthorized"}'})
            return
        if scope["path"] == "/health":
            body = json.dumps({"service": "calculos-juridicos-mcp", "pid": os.getpid(), "version": self.version}).encode()
            await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)


def snapshot(executable):
    signature = hashlib.sha256(executable.read_bytes()).hexdigest()
    payload = ROOT / "payloads" / signature[:16]
    if (payload / "ready.json").is_file():
        return payload / executable.name
    payload.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="preparing-", dir=payload.parent))
    try:
        shutil.copy2(executable, temporary / executable.name)
        shutil.copytree(executable.parent / "_internal", temporary / "_internal")
        info = executable.parent / "app-info.json"
        if info.is_file():
            shutil.copy2(info, temporary / info.name)
        if hashlib.sha256(executable.read_bytes()).hexdigest() != signature:
            raise RuntimeError("O aplicativo foi atualizado durante a preparação do conector.")
        (temporary / "ready.json").write_text(json.dumps({"sha256": signature}), encoding="utf-8")
        temporary.replace(payload)
        return payload / executable.name
    finally:
        if temporary.exists():
            temporary.resolve().relative_to(payload.parent.resolve())
            shutil.rmtree(temporary)


def main():
    import msvcrt

    configuration = json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))
    lock = open(ROOT / "host.lock", "a+b")
    lock.seek(0)
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        lock.close()
        return 0
    executable = Path(configuration["executable"])
    print("Preparing installed engine snapshot", flush=True)
    original_stat = executable.stat()
    original_stamp = (original_stat.st_mtime_ns, original_stat.st_size)
    payload_executable = snapshot(executable)
    print("Loading installed engine", flush=True)
    mount_installed(payload_executable)

    import uvicorn
    from liquidacao_custom.mcp_server import mcp
    from liquidacao_custom.metadata import APP_DISPLAY_VERSION
    print("Installed engine loaded", flush=True)

    mcp.settings.host = "127.0.0.1"
    mcp.settings.port = int(configuration["port"])
    mcp.settings.stateless_http = True
    mcp.settings.json_response = True
    application = LocalAuthentication(mcp.streamable_http_app(), configuration["token"], APP_DISPLAY_VERSION)
    server = uvicorn.Server(uvicorn.Config(application, host="127.0.0.1", port=mcp.settings.port, log_level="warning", log_config=None, access_log=False))
    finished = threading.Event()
    changed = threading.Event()

    def watch_installation():
        while not finished.wait(30):
            try:
                current = executable.stat()
            except OSError:
                continue
            if (current.st_mtime_ns, current.st_size) != original_stamp:
                changed.set()
                server.should_exit = True
                return

    watcher = threading.Thread(target=watch_installation, name="installed-app-monitor", daemon=True)
    watcher.start()
    try:
        (ROOT / "instance.json").write_text(json.dumps({"pid": os.getpid(), "version": APP_DISPLAY_VERSION, "port": mcp.settings.port, "started": time.time()}), encoding="utf-8")
        faulthandler.cancel_dump_traceback_later()
        server.run()
        return 75 if changed.is_set() else 0
    finally:
        finished.set()
        lock.close()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--service-root":
        ROOT = Path(sys.argv[2]).resolve()
    ROOT.mkdir(parents=True, exist_ok=True)
    log_path = ROOT / "host.log"
    if log_path.exists() and log_path.stat().st_size > 1024 * 1024:
        log_path.replace(ROOT / "host.previous.log")
    with open(log_path, "a", encoding="utf-8", buffering=1) as log:
        sys.stdout = log
        sys.stderr = log
        faulthandler.enable(file=log)
        faulthandler.dump_traceback_later(30, repeat=True, file=log)
        try:
            raise SystemExit(main())
        except Exception:
            traceback.print_exc()
            raise SystemExit(1)
