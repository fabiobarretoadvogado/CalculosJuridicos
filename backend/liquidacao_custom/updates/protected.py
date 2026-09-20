"""Protege credenciais para a conta atual do Windows com DPAPI."""
from __future__ import annotations

import base64
import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path


class Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def protect(data: bytes, decrypt: bool = False) -> bytes:
    if os.name != "nt":
        raise OSError("A proteção de credenciais requer Windows.")
    source_buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source = Blob(len(data), source_buffer)
    destination = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [
        ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob),
    ]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(destination)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(destination.data, destination.size)
    finally:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree.restype = ctypes.c_void_p
        kernel.LocalFree(destination.data)


def credential_path() -> Path:
    root = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))
    return Path(root) / "CalculosJuridicos/update-access.json"


def load_token(repository: str) -> str:
    path = credential_path()
    if not path.exists():
        return ""
    stored = json.loads(path.read_text(encoding="utf-8"))
    if stored.get("repository", "").casefold() != repository.casefold():
        return ""
    encrypted = base64.b64decode(stored["credential"], validate=True)
    return protect(encrypted, decrypt=True).decode("utf-8")


def save_token(repository: str, token: str) -> None:
    if not token.strip() or any(character.isspace() for character in token):
        raise ValueError("Credencial inválida.")
    path = credential_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    encrypted = base64.b64encode(protect(token.encode("utf-8"))).decode("ascii")
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"repository": repository, "credential": encrypted}),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def remove_token() -> None:
    credential_path().unlink(missing_ok=True)

