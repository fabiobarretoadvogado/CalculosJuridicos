from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from liquidacao_custom.metadata import APP_ID, APP_VERSION, EXECUTABLE_NAME, INSTALLER_PREFIX

MANIFEST_LIMIT = 64 * 1024
INSTALLER_LIMIT = 1024 * 1024 * 1024
NETWORK_HOSTS = {
    "api.github.com", "github.com", "release-assets.githubusercontent.com",
    "objects.githubusercontent.com", "github-releases.githubusercontent.com",
}


class UpdateError(ValueError):
    pass


def version_tuple(value: str) -> tuple[int, ...]:
    pattern = r"(?:0|[1-9][0-9]{0,4})(?:\.(?:0|[1-9][0-9]{0,4})){3}"
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise UpdateError("Versão inválida.")
    parts = tuple(map(int, value.split(".")))
    if max(parts) > 65535:
        raise UpdateError("Versão fora do limite do Windows.")
    return parts


def normalize_repository(value: str) -> str:
    value = value.strip().removeprefix("https://github.com/").rstrip("/")
    if value.endswith(".git"):
        value = value[:-4]
    pattern = r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}"
    if not re.fullmatch(pattern, value):
        raise UpdateError("Informe o repositório no formato conta/nome ou a URL do GitHub.")
    return value


def check_transport_url(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https" or parsed.hostname not in NETWORK_HOSTS
        or parsed.username or parsed.password or parsed.port not in (None, 443)
        or parsed.fragment
    ):
        raise UpdateError("Endereço de atualização não autorizado.")


def check_asset_url(url: str, repository: str, version: str, name: str) -> None:
    expected = f"https://github.com/{repository}/releases/download/v{version}/{name}"
    if not isinstance(url, str) or url.casefold() != expected.casefold():
        raise UpdateError("Arquivo fora do repositório ou da versão esperada.")
    check_transport_url(url)


class SafeRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        check_transport_url(new_url)
        redirected = super().redirect_request(
            request, file_pointer, code, message, headers, new_url,
        )
        if redirected and urlsplit(request.full_url).hostname != urlsplit(new_url).hostname:
            redirected.remove_header("Authorization")
        return redirected


def open_url(url: str, token: str = ""):
    check_transport_url(url)
    headers = {
        "User-Agent": "CalculosJuridicos-Updater/1",
        "Accept": "application/vnd.github+json",
    }
    if urlsplit(url).hostname == "api.github.com" and token:
        headers["Authorization"] = "Bearer " + token
        if "/releases/assets/" in urlsplit(url).path:
            headers["Accept"] = "application/octet-stream"
    return build_opener(SafeRedirects()).open(Request(url, headers=headers), timeout=20)


def read_small(url: str, limit: int, token: str = "") -> bytes:
    with open_url(url, token) as response:
        result = response.read(limit + 1)
    if len(result) > limit:
        raise UpdateError("Resposta de atualização maior que o permitido.")
    return result


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    name: str
    url: str
    size: int
    sha256: str
    notes: str
    api_url: str = ""
    display_version: str = ""

    @property
    def visible_version(self) -> str:
        return self.display_version or self.version


def verify_manifest(envelope: bytes, public_key: str, repository: str) -> UpdateInfo:
    try:
        if len(envelope) > MANIFEST_LIMIT:
            raise ValueError("limite")
        wrapped = json.loads(envelope)
        payload = base64.b64decode(wrapped["payload"], validate=True)
        signature = base64.b64decode(wrapped["signature"], validate=True)
        key = base64.b64decode(public_key, validate=True)
        Ed25519PublicKey.from_public_bytes(key).verify(signature, payload)
        manifest = json.loads(payload)
        if (
            manifest["schema"] != 1 or manifest["app_id"] != APP_ID
            or manifest["channel"] != "stable" or manifest["architecture"] != "x64"
        ):
            raise ValueError("identidade")
        version = manifest["version"]
        version_tuple(version)
        installer = manifest["installer"]
        name = f"{INSTALLER_PREFIX}-{version}-x64.exe"
        if installer["name"] != name:
            raise ValueError("nome")
        size = installer["size"]
        digest = installer["sha256"]
        if type(size) is not int or not 0 < size <= INSTALLER_LIMIT:
            raise ValueError("tamanho")
        if not isinstance(digest, str) or not re.fullmatch("[a-f0-9]{64}", digest):
            raise ValueError("resumo")
        check_asset_url(installer["url"], normalize_repository(repository), version, name)
        notes = manifest.get("notes", "")
        if not isinstance(notes, str) or len(notes) > 8000:
            raise ValueError("notas")
        display_version = manifest.get("display_version", "")
        if not isinstance(display_version, str) or (
            display_version and not re.fullmatch(r"[1-9][0-9]{0,4}\.[0-9]{2}", display_version)
        ):
            raise ValueError("edição")
        return UpdateInfo(
            version, name, installer["url"], size, digest, notes,
            display_version=display_version,
        )
    except (ValueError, TypeError, KeyError, InvalidSignature) as exc:
        raise UpdateError(
            "A assinatura ou os dados da atualização não puderam ser confirmados."
        ) from exc


def asset_api_url(asset: dict, repository: str) -> str:
    url = asset["url"]
    prefix = f"https://api.github.com/repos/{repository}/releases/assets/"
    if (
        not isinstance(url, str)
        or not url.casefold().startswith(prefix.casefold())
        or not url[len(prefix):].isdigit()
    ):
        raise UpdateError("Endereço de arquivo privado inválido.")
    return url


def resolve_repository_alias(repository: str, token: str = "") -> str:
    try:
        record = json.loads(read_small(
            f"https://api.github.com/repos/{repository}", 256 * 1024, token,
        ))
        if type(record["id"]) is not int or record["id"] <= 0:
            raise ValueError("identidade")
        return normalize_repository(record["full_name"])
    except (ValueError, TypeError, KeyError) as exc:
        raise UpdateError(
            "A identidade atual do repositório não foi confirmada pelo GitHub."
        ) from exc


def check_latest(
    repository: str,
    public_key: str,
    current_version: str = APP_VERSION,
    token: str = "",
) -> UpdateInfo | None:
    repository = normalize_repository(repository)
    try:
        release = json.loads(read_small(
            f"https://api.github.com/repos/{repository}/releases/latest",
            256 * 1024,
            token,
        ))
    except HTTPError as exc:
        if exc.code == 404:
            exc.close()
            if token:
                read_small(f"https://api.github.com/repos/{repository}", 256 * 1024, token)
            return None
        raise
    if release.get("draft") or release.get("prerelease"):
        raise UpdateError("Publicação ainda não aprovada para distribuição.")
    tag = release["tag_name"]
    version = tag.removeprefix("v")
    version_tuple(version)
    assets = [asset for asset in release["assets"] if asset["name"] == "update.json"]
    if len(assets) != 1:
        raise UpdateError("A publicação não possui um manifesto único de atualização.")
    url = assets[0]["browser_download_url"]
    transport_repository = repository
    try:
        check_asset_url(url, repository, version, "update.json")
    except UpdateError:
        transport_repository = resolve_repository_alias(repository, token)
        check_asset_url(url, transport_repository, version, "update.json")
    manifest_url = asset_api_url(assets[0], transport_repository) if token else url
    info = verify_manifest(read_small(manifest_url, MANIFEST_LIMIT, token), public_key, repository)
    if info.version != version or tag != "v" + info.version:
        raise UpdateError("A versão assinada difere da publicação.")
    if token:
        installers = [asset for asset in release["assets"] if asset["name"] == info.name]
        if len(installers) != 1:
            raise UpdateError("Instalador privado ausente ou duplicado.")
        info = replace(info, api_url=asset_api_url(installers[0], transport_repository))
    return info if version_tuple(info.version) > version_tuple(current_version) else None


def cache_root() -> Path:
    root = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))
    return Path(root) / "CalculosJuridicos/updates"


def download_installer(
    info: UpdateInfo,
    directory: Path,
    progress=None,
    cancelled: threading.Event | None = None,
    token: str = "",
) -> Path:
    directory.mkdir(parents=True, exist_ok=False)
    target = directory / info.name
    temporary = directory / (info.name + ".part")
    digest = hashlib.sha256()
    received = 0
    try:
        with open_url(info.api_url or info.url, token) as response, temporary.open("xb") as stream:
            while True:
                if cancelled and cancelled.is_set():
                    raise UpdateError("Download cancelado.")
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                received += len(chunk)
                if received > info.size:
                    raise UpdateError("O instalador excedeu o tamanho assinado.")
                stream.write(chunk)
                digest.update(chunk)
                if progress:
                    progress(received * 100 // info.size)
            stream.flush()
            os.fsync(stream.fileno())
        if received != info.size or digest.hexdigest() != info.sha256:
            raise UpdateError("O instalador está incompleto ou foi alterado.")
        os.replace(temporary, target)
        return target
    finally:
        temporary.unlink(missing_ok=True)


def prepare_update_job(installer: Path, info: UpdateInfo, executable: Path, restart: bool = True) -> Path:
    installer = installer.resolve(strict=True)
    executable = executable.resolve(strict=True)
    directory = installer.parent
    cache = cache_root().resolve()
    if not directory.is_relative_to(cache) or directory == cache:
        raise UpdateError("Pasta de atualização inválida.")
    identity_path = executable.parent / "app-info.json"
    identity = json.loads(identity_path.read_text(encoding="utf-8-sig"))
    if (
        executable.name != EXECUTABLE_NAME or identity.get("app_id") != APP_ID
        or identity.get("distribution") != "installed"
    ):
        raise UpdateError("A atualização exige a versão instalada do aplicativo.")
    if version_tuple(info.version) <= version_tuple(identity["version"]):
        raise UpdateError("A versão instalada já é igual ou superior a esta atualização.")
    with installer.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if installer.stat().st_size != info.size or digest != info.sha256:
        raise UpdateError("O instalador mudou depois do download.")
    import shutil
    shutil.copy2(Path(__file__).with_name("install-update.ps1"), directory / "install-update.ps1")
    job = {
        "ParentPID": os.getpid(), "InstallDir": str(executable.parent), "AppId": APP_ID,
        "Installer": str(installer), "SHA256": info.sha256, "Size": info.size,
        "Version": info.version, "Executable": EXECUTABLE_NAME, "Restart": restart,
    }
    path = directory / "job.json"
    path.write_text(json.dumps(job, indent=2), encoding="utf-8")
    return path


def launch_update(job: Path) -> None:
    system_root = Path(os.environ["SystemRoot"])
    powershell = system_root / "System32/WindowsPowerShell/v1.0/powershell.exe"
    environment = os.environ.copy()
    environment["PATH"] = str(system_root / "System32") + os.pathsep + str(system_root)
    for name in ("PYTHONHOME", "PYTHONPATH"):
        environment.pop(name, None)
    restore = getattr(sys, "_MEIPASS", None) if getattr(sys, "frozen", False) else None
    kernel = None
    if restore:
        import ctypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.SetDllDirectoryW.argtypes = [ctypes.c_wchar_p]
        kernel.SetDllDirectoryW.restype = ctypes.c_int
        if not kernel.SetDllDirectoryW(None):
            raise ctypes.WinError(ctypes.get_last_error())
    try:
        subprocess.Popen(
            [str(powershell), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(job.parent / "install-update.ps1"), "-JobFile", str(job)],
            creationflags=subprocess.CREATE_NO_WINDOW,
            close_fds=True,
            env=environment,
        )
    finally:
        if kernel:
            kernel.SetDllDirectoryW(restore)

