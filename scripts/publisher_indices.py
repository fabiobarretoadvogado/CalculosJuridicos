"""Prepara/publica somente o pacote de dados, sem compilar ou enviar instalador."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "backend"))

from liquidacao_custom.index_data.client import unpack_package, verify_manifest
from liquidacao_custom.index_data.store import BUNDLED, FILES, PACKAGE_PREFIX, dataset_id, file_records
from liquidacao_custom.index_data.validation import validate_directory
from liquidacao_custom.metadata import APP_ID
from liquidacao_custom.updates import settings
from liquidacao_custom.updates.client import read_small
from publisher import api, preflight, publication_token, signing_key, upload_file


def prepare(output: Path, repository: str, *, key=None, revision=None, source=BUNDLED):
    if repository != settings.REPOSITORY:
        raise ValueError("O repositório deve corresponder ao aplicativo distribuído.")
    validate_directory(source)
    records = file_records(source)
    revision = revision or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = output / ("indices-v2-" + revision)
    output.mkdir(parents=True, exist_ok=False)
    package = output / ("indices-v2-" + revision + ".zip")
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in FILES:
            # Conteúdo explícito: não inclui scripts, credenciais, cálculos ou fontes do aplicativo.
            archive.writestr(name, (source / name).read_bytes())
    payload = {"schema": 2, "app_id": APP_ID, "channel": "indices", "revision": revision,
               "dataset_id": dataset_id(records), "files": records,
               "package": {"name": package.name, "size": package.stat().st_size,
                           "sha256": hashlib.sha256(package.read_bytes()).hexdigest(),
                           "url": f"https://github.com/{repository}/releases/download/indices-v2-{revision}/{package.name}"}}
    signer = key or signing_key()
    public = base64.b64encode(signer.public_key().public_bytes_raw()).decode()
    if key is None and public != settings.PUBLIC_KEY:
        raise ValueError("A chave de assinatura difere dos aplicativos distribuídos.")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    envelope = json.dumps({"payload": base64.b64encode(encoded).decode(),
                           "signature": base64.b64encode(signer.sign(encoded)).decode()}, indent=2).encode()
    verify_manifest(envelope, public, repository)
    with tempfile.TemporaryDirectory(prefix="indices-verify-", dir=output) as temporary:
        unpack_package(package.read_bytes(), payload, Path(temporary))
    (output / "indices-update.json").write_bytes(envelope)
    (output / "Notas-dos-indices.md").write_text(
        "# Atualização dos índices\n\n"
        f"Pacote de dados {revision}. Identidade SHA-256: {payload['dataset_id']}.\n\n"
        "Contém somente bases econômicas e suas fontes arquivadas. "
        "Não contém instalador nem altera as regras de cálculo. "
        "Formato 2: exige o novo leitor canônico. As edições anteriores ignoram este canal e continuam usando pacotes formato 1.\n", encoding="utf-8")
    return output


def publish(directory: Path, repository: str):
    if repository != settings.REPOSITORY:
        raise ValueError("Repositório divergente da configuração.")
    envelope = (directory / "indices-update.json").read_bytes()
    manifest = verify_manifest(envelope, settings.PUBLIC_KEY, repository)
    package = directory / manifest["package"]["name"]
    with tempfile.TemporaryDirectory(prefix="indices-publish-verify-", dir=directory) as temporary:
        unpack_package(package.read_bytes(), manifest, Path(temporary))
    credential = publication_token()
    transport = preflight(repository, settings.ACCESS)
    tag = PACKAGE_PREFIX + manifest["revision"]
    try:
        api(credential, f"/repos/{transport}/releases/tags/{tag}")
    except HTTPError as exc:
        if exc.code != 404:
            raise
        exc.close()
    else:
        raise ValueError("Esta publicação já existe; nenhuma release será substituída.")
    record = api(credential, f"/repos/{transport}/releases", "POST", {
        "tag_name": tag, "name": "Índices do Cálculos Jurídicos — " + manifest["revision"],
        "body": (directory / "Notas-dos-indices.md").read_text(encoding="utf-8"),
        "draft": True, "prerelease": True, "make_latest": "false"})
    upload_url = record["upload_url"].split("{", 1)[0]
    if urlsplit(upload_url).hostname != "uploads.github.com":
        raise ValueError("Endereço de envio inesperado. O rascunho foi preservado.")
    files = [package, directory / "indices-update.json"]
    for path in files:
        upload_file(credential, upload_url + "?" + urlencode({"name": path.name}), path)
    draft = api(credential, f"/repos/{transport}/releases/{record['id']}")
    assets = {a["name"]: a for a in draft["assets"]}
    if set(assets) != {p.name for p in files}:
        raise ValueError("Arquivos inesperados no rascunho.")
    for path in files:
        asset = assets[path.name]
        if asset["state"] != "uploaded" or asset["size"] != path.stat().st_size:
            raise ValueError("O GitHub não confirmou os arquivos. Rascunho preservado.")
        remote = read_small(asset["url"], max(path.stat().st_size, 1), credential)
        if hashlib.sha256(remote).hexdigest() != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError("O arquivo remoto difere do pacote assinado. Rascunho preservado.")
    released = api(credential, f"/repos/{transport}/releases/{record['id']}", "PATCH", {
        "draft": False, "prerelease": True, "make_latest": "false"})
    (directory / "publicacao.json").write_text(json.dumps({"url": released["html_url"],
        "revision": manifest["revision"], "dataset_id": manifest["dataset_id"]}, indent=2) + "\n", encoding="utf-8")
    print("Publicado: " + released["html_url"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "publish"))
    parser.add_argument("--repository", default=settings.REPOSITORY)
    parser.add_argument("--output", type=Path, default=PROJECT / "build/indices")
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.output, args.repository)
        print(json.dumps({"directory": str(result)}, ensure_ascii=True))
    else:
        publish(args.output, args.repository)


if __name__ == "__main__":
    main()
