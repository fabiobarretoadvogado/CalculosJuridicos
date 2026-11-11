from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import shutil
import tempfile
import threading
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from liquidacao_custom.metadata import APP_ID
from liquidacao_custom.updates import settings
from liquidacao_custom.updates.client import (
    UpdateError, asset_api_url, normalize_repository, open_url, read_small, resolve_repository_alias,
)
from liquidacao_custom.updates.protected import load_token
from .store import BUNDLED, FILES, FILES_BASE, PACKAGE_PREFIX, current_dataset, dataset_id, storage_root
from .validation import ensure_no_regression, validate_directory

MANIFEST_LIMIT = 128 * 1024
PACKAGE_LIMIT = 8 * 1024 * 1024
EXTRACTED_LIMIT = 32 * 1024 * 1024
REVISION_PATTERN = r"[0-9]{8}T[0-9]{12}Z"
_update_lock = threading.Lock()


class UnsupportedIndexFormat(UpdateError):
    """Pacote de formato não canônico; não deve ser carregado nem convertido."""


def token():
    return load_token(settings.REPOSITORY) if settings.ACCESS == "private" else ""


def verify_manifest(envelope: bytes, public_key: str, repository: str) -> dict:
    try:
        if len(envelope) > MANIFEST_LIMIT:
            raise ValueError("limite")
        wrapped = json.loads(envelope)
        payload = base64.b64decode(wrapped["payload"], validate=True)
        Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key, validate=True)).verify(
            base64.b64decode(wrapped["signature"], validate=True), payload)
        value = json.loads(payload)
        if value["app_id"] != APP_ID or value["channel"] != "indices":
            raise ValueError("identidade")
        if type(value.get("schema")) is not int or value["schema"] != 2:
            raise UnsupportedIndexFormat("Somente bases oficiais no formato 2 são aceitas. O pacote antigo foi preservado e não será usado.")
        revision = value["revision"]
        if not isinstance(revision, str) or not re.fullmatch(REVISION_PATTERN, revision):
            raise ValueError("versão")
        created = datetime.strptime(revision, "%Y%m%dT%H%M%S%fZ").replace(tzinfo=timezone.utc)
        if created > datetime.now(timezone.utc):
            raise ValueError("data futura")
        if set(value["files"]) not in (set(FILES), set(FILES_BASE)):
            raise ValueError("arquivos")
        for record in value["files"].values():
            if type(record["size"]) is not int or not 0 < record["size"] <= EXTRACTED_LIMIT:
                raise ValueError("tamanho")
            if not re.fullmatch(r"[a-f0-9]{64}", record["sha256"]):
                raise ValueError("hash")
        if sum(r["size"] for r in value["files"].values()) > EXTRACTED_LIMIT:
            raise ValueError("limite total")
        if value["dataset_id"] != dataset_id(value["files"]):
            raise ValueError("identidade dos dados")
        package = value["package"]
        prefix = PACKAGE_PREFIX
        name = prefix + revision + ".zip"
        expected = f"https://github.com/{normalize_repository(repository)}/releases/download/{prefix}{revision}/{name}"
        if package["name"] != name or package["url"] != expected:
            raise ValueError("endereço")
        if type(package["size"]) is not int or not 0 < package["size"] <= PACKAGE_LIMIT:
            raise ValueError("tamanho do pacote")
        if not re.fullmatch(r"[a-f0-9]{64}", package["sha256"]):
            raise ValueError("hash do pacote")
        return value
    except UnsupportedIndexFormat:
        raise
    except Exception as exc:
        raise UpdateError("A assinatura ou os dados do pacote de índices não puderam ser confirmados.") from exc


def check_latest() -> tuple[dict, bytes, str] | None:
    if not settings.REPOSITORY or not settings.PUBLIC_KEY:
        return None
    repository = normalize_repository(settings.REPOSITORY)
    credential = token()
    records = []
    # As releases de índices são separadas e nunca substituem releases/latest.
    for page in range(1, 6):
        batch = json.loads(read_small(
            f"https://api.github.com/repos/{repository}/releases?per_page=100&page={page}",
            4 * 1024 * 1024, credential))
        if not isinstance(batch, list):
            raise UpdateError("Lista de publicações inválida.")
        records.extend(r for r in batch if not r.get("draft") and re.fullmatch(
            PACKAGE_PREFIX + REVISION_PATTERN, r.get("tag_name", "")))
        if len(batch) < 100:
            break
    if not records:
        return None
    release = max(records, key=lambda r: r["tag_name"])
    tag = release["tag_name"]
    assets = [a for a in release["assets"] if a["name"] == "indices-update.json"]
    if len(assets) != 1:
        raise UpdateError("Publicação de índices sem manifesto único.")
    transport_repository = repository
    expected = f"https://github.com/{repository}/releases/download/{tag}/indices-update.json"
    if assets[0]["browser_download_url"] != expected:
        transport_repository = resolve_repository_alias(repository, credential)
        expected = f"https://github.com/{transport_repository}/releases/download/{tag}/indices-update.json"
        if assets[0]["browser_download_url"] != expected:
            raise UpdateError("Manifesto fora da publicação esperada.")
    url = asset_api_url(assets[0], transport_repository) if credential else expected
    envelope = read_small(url, MANIFEST_LIMIT, credential)
    manifest = verify_manifest(envelope, settings.PUBLIC_KEY, repository)
    if tag != PACKAGE_PREFIX + manifest["revision"]:
        raise UpdateError("A versão assinada difere da publicação dos índices.")
    package_assets = [a for a in release["assets"] if a["name"] == manifest["package"]["name"]]
    if len(package_assets) != 1 or package_assets[0]["size"] != manifest["package"]["size"]:
        raise UpdateError("Pacote ausente, duplicado ou com tamanho divergente.")
    expected_package = f"https://github.com/{transport_repository}/releases/download/{tag}/{manifest['package']['name']}"
    if package_assets[0]["browser_download_url"] != expected_package:
        raise UpdateError("Pacote fora da publicação esperada.")
    download_url = asset_api_url(package_assets[0], transport_repository) if credential else expected_package
    return manifest, envelope, download_url


def unpack_package(raw: bytes, manifest: dict, directory: Path):
    package = manifest["package"]
    if len(raw) != package["size"] or hashlib.sha256(raw).hexdigest() != package["sha256"]:
        raise UpdateError("O pacote de índices não corresponde à assinatura.")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        records = archive.infolist()
        if manifest.get("schema") != 2:
            raise UnsupportedIndexFormat("Somente bases oficiais no formato 2 são aceitas.")
        if len(records) != len(manifest["files"]) or {r.filename for r in records} != set(manifest["files"]):
            raise UpdateError("O pacote contém arquivos ausentes, duplicados ou não autorizados.")
        for record in records:
            expected = manifest["files"][record.filename]
            if (record.file_size != expected["size"] or record.flag_bits & 1
                    or record.external_attr >> 16 & 0o170000 == 0o120000):
                raise UpdateError("Arquivo de dados inválido no pacote.")
            content = archive.read(record)
            if hashlib.sha256(content).hexdigest() != expected["sha256"]:
                raise UpdateError("Hash de arquivo de dados divergente.")
            destination = directory / record.filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
    validate_directory(directory, manifest["files"])


def install_package(raw: bytes, envelope: bytes) -> dict:
    manifest = verify_manifest(envelope, settings.PUBLIC_KEY, settings.REPOSITORY)
    previous = current_dataset()
    if manifest["dataset_id"] == previous.identity:
        return {"atualizado": False, "base": previous.metadata()}
    if previous.revision and manifest["revision"] <= previous.revision:
        raise UpdateError("Uma versão anterior dos índices não será instalada.")
    root = storage_root()
    root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="stage-", dir=root))
    try:
        unpack_package(raw, manifest, stage)
        ensure_no_regression(stage, previous.directory)
        ensure_no_regression(stage, BUNDLED)
        target = root / "versions" / manifest["dataset_id"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            # Uma base arquivada nunca é reescrita enquanto um cálculo a utiliza.
            for name, expected in manifest["files"].items():
                content = (target / name).read_bytes()
                if len(content) != expected["size"] or hashlib.sha256(content).hexdigest() != expected["sha256"]:
                    raise UpdateError("A cópia arquivada do pacote está inconsistente.")
        else:
            os.replace(stage, target)
        pointer = root / "active.json"
        temporary = root / ("active-" + uuid.uuid4().hex + ".tmp")
        temporary.write_bytes(envelope)
        try:
            if pointer.exists():
                (root / "previous.json").write_bytes(pointer.read_bytes())
            os.replace(temporary, pointer)
        finally:
            temporary.unlink(missing_ok=True)
        return {"atualizado": True, "base": {"versao": manifest["revision"],
                "sha256": manifest["dataset_id"], "origem": "atualizacao", "formato": 2}}
    finally:
        if stage.exists() and root.resolve() in stage.resolve().parents:
            shutil.rmtree(stage)


def synchronize() -> dict:
    with _update_lock:
        available = check_latest()
        current = current_dataset()
        if available is None:
            return {"atualizado": False, "base": current.metadata(), "mensagem": "Nenhum pacote das novas bases oficiais foi publicado."}
        manifest, envelope, url = available
        if manifest["files"].keys() == set(FILES_BASE):
            return {"atualizado": False, "base": current.metadata(),
                    "mensagem": "A base em uso tem cobertura histórica superior à do pacote publicado."}
        if manifest["dataset_id"] == current.identity or (current.revision and manifest["revision"] <= current.revision):
            return {"atualizado": False, "base": current.metadata(), "mensagem": "Os índices disponíveis já estão em uso."}
        size = manifest["package"]["size"]
        with open_url(url, token()) as response:
            raw = response.read(size + 1)
        return install_package(raw, envelope)
