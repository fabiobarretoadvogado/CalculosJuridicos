from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys


PROJECT = Path(__file__).resolve().parents[1]
SERVICE_FILES = ("shared_host.py", "frozen_runtime.py", "manage.py", "register_service.ps1", "stop_service.ps1")


def prepare(payload: Path) -> Path:
    payload = payload.resolve(strict=True)
    target = payload / "codex-service"
    if target.exists():
        target.resolve().relative_to(payload)
        shutil.rmtree(target)
    target.mkdir()
    source = PROJECT / "backend/liquidacao_custom/codex_service"
    for filename in SERVICE_FILES:
        shutil.copy2(source / filename, target / filename)
    runtime = target / "runtime"
    runtime.mkdir()
    python_root = Path(sys.base_prefix)
    library_name = f"python{sys.version_info.major}{sys.version_info.minor}.dll"
    required = ("python.exe", "pythonw.exe", library_name)
    optional = ("python3.dll", "vcruntime140.dll", "vcruntime140_1.dll", "LICENSE.txt")
    for filename in required:
        shutil.copy2(python_root / filename, runtime / filename)
    for filename in optional:
        if (python_root / filename).is_file():
            shutil.copy2(python_root / filename, runtime / filename)
    excluded = shutil.ignore_patterns("site-packages", "__pycache__", "test", "tests", "idlelib", "tkinter", "turtledemo", "ensurepip")
    for directory in ("Lib", "DLLs"):
        shutil.copytree(python_root / directory, runtime / directory, ignore=excluded)
    identity = {"python": sys.version, "library_sha256": hashlib.sha256((runtime / library_name).read_bytes()).hexdigest()}
    (runtime / "ready.json").write_text(json.dumps(identity, sort_keys=True), encoding="utf-8")
    return target


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Uso: prepare_shared_service.py PASTA_DO_APLICATIVO")
    print(f"Serviço preparado: {prepare(Path(sys.argv[1]))}")
