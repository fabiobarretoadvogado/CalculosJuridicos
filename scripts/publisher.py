from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "backend"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from liquidacao_custom.metadata import (  # noqa: E402
    APP_DISPLAY_VERSION,
    APP_ID,
    APP_VERSION,
    INSTALLER_PREFIX,
)
from liquidacao_custom.updates.client import (  # noqa: E402
    normalize_repository,
    verify_manifest,
    version_tuple,
)
from liquidacao_custom.updates.protected import protect  # noqa: E402


def key_path() -> Path:
    return Path(os.environ["LOCALAPPDATA"]) / "CalculosJuridicos-Publisher/update-signing-key.json"


def signing_key() -> Ed25519PrivateKey:
    path = key_path()
    if path.exists():
        stored = json.loads(path.read_text(encoding="utf-8"))
        raw = protect(
            base64.b64decode(stored["protected_private"], validate=True),
            decrypt=True,
        )
        key = Ed25519PrivateKey.from_private_bytes(raw)
        public_key = base64.b64encode(key.public_key().public_bytes_raw()).decode("ascii")
        if public_key != stored["public_key"]:
            raise ValueError("A chave de publicação está inconsistente. Preserve o arquivo para recuperação.")
        return key

    from liquidacao_custom.updates.settings import PUBLIC_KEY

    if PUBLIC_KEY:
        raise ValueError(
            "A chave de publicação não está nesta conta do Windows. "
            "Restaure a chave original antes de publicar."
        )
    key = Ed25519PrivateKey.generate()
    stored = {
        "public_key": base64.b64encode(key.public_key().public_bytes_raw()).decode("ascii"),
        "protected_private": base64.b64encode(protect(key.private_bytes_raw())).decode("ascii"),
        "created": datetime.now(timezone.utc).isoformat(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(stored, stream, indent=2)
    return key


def release_version(requested: str) -> tuple[str, str]:
    """Converte a edição amigável em uma versão crescente aceita pelo Windows."""
    import re

    if not requested:
        return APP_VERSION, APP_DISPLAY_VERSION
    if re.fullmatch(r"[1-9][0-9]{0,4}\.[0-9]{2}", requested):
        display_parts = tuple(map(int, requested.split(".")))
        current_display = tuple(map(int, APP_DISPLAY_VERSION.split(".")))
        if display_parts < current_display:
            raise ValueError("Não publique uma edição anterior ao código atual.")
        if display_parts == current_display:
            return APP_VERSION, requested
        parts = list(version_tuple(APP_VERSION))
        parts[3] += 1
        build = ".".join(map(str, parts))
        version_tuple(build)
        return build, requested
    if version_tuple(requested) < version_tuple(APP_VERSION):
        raise ValueError("Não publique uma versão anterior ao código atual.")
    return requested, APP_DISPLAY_VERSION


def configure(repository: str, version: str, access: str, display_version: str) -> None:
    import re

    if not re.fullmatch(r"[1-9][0-9]{0,4}\.[0-9]{2}", display_version):
        raise ValueError("Informe a edição no formato 1.01.")
    version_tuple(version)
    if version_tuple(version) < version_tuple(APP_VERSION):
        raise ValueError("Não publique uma versão anterior ao código atual.")
    repository = normalize_repository(repository) if repository else ""
    key = signing_key()
    public_key = base64.b64encode(key.public_key().public_bytes_raw()).decode("ascii")

    from liquidacao_custom.updates.settings import PUBLIC_KEY, REPOSITORY

    if PUBLIC_KEY and PUBLIC_KEY != public_key:
        raise ValueError("A chave difere da identidade já distribuída e não será substituída.")
    if REPOSITORY and REPOSITORY.casefold() != repository.casefold():
        raise ValueError("O repositório distribuído não pode ser trocado por este comando.")

    settings = (
        "# Configuração pública. Chaves privadas e credenciais nunca são incluídas.\n"
        f"REPOSITORY = {repository!r}\n"
        f"PUBLIC_KEY = {public_key!r}\n"
        f"ACCESS = {access!r}\n"
    )
    (PROJECT / "backend/liquidacao_custom/updates/settings.py").write_text(
        settings,
        encoding="utf-8",
    )
    metadata_path = PROJECT / "backend/liquidacao_custom/metadata.py"
    metadata = metadata_path.read_text(encoding="utf-8")
    metadata, version_count = re.subn(
        r'APP_VERSION = "[^"]+"',
        f'APP_VERSION = "{version}"',
        metadata,
    )
    metadata, display_count = re.subn(
        r'APP_DISPLAY_VERSION = "[^"]+"',
        f'APP_DISPLAY_VERSION = "{display_version}"',
        metadata,
    )
    if version_count != 1 or display_count != 1:
        raise ValueError("Não foi possível atualizar a versão do projeto.")
    metadata_path.write_text(metadata, encoding="utf-8")
    (PROJECT / "publisher.json").write_text(
        json.dumps(
            {"repository": repository, "access": access, "public_key": public_key},
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print("Identidade pública configurada. A chave privada está protegida nesta conta do Windows.")


def manifest(installer: Path, output: Path, repository: str, notes: str) -> None:
    repository = normalize_repository(repository)
    key = signing_key()
    version = APP_VERSION
    name = f"{INSTALLER_PREFIX}-{version}-x64.exe"
    if installer.name != name:
        raise ValueError("O nome do instalador difere da versão atual.")
    with installer.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    payload = {
        "schema": 1,
        "app_id": APP_ID,
        "version": version,
        "display_version": APP_DISPLAY_VERSION,
        "channel": "stable",
        "architecture": "x64",
        "published": datetime.now(timezone.utc).isoformat(),
        "notes": notes,
        "installer": {
            "name": name,
            "size": installer.stat().st_size,
            "sha256": digest,
            "url": f"https://github.com/{repository}/releases/download/v{version}/{name}",
        },
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    envelope = json.dumps(
        {
            "payload": base64.b64encode(encoded).decode("ascii"),
            "signature": base64.b64encode(key.sign(encoded)).decode("ascii"),
        },
        indent=2,
    ).encode("utf-8")

    from liquidacao_custom.updates.settings import PUBLIC_KEY, REPOSITORY

    if REPOSITORY != repository:
        raise ValueError("O instalador precisa usar o mesmo repositório da publicação.")
    verify_manifest(envelope, PUBLIC_KEY, repository)
    output.write_bytes(envelope)
    print(f"Manifesto assinado e conferido: {output}")


def publication_token() -> str:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token.strip()
    bundled = PROJECT / ".tools/GitHubCLI/bin/gh.exe"
    gh = shutil.which("gh") or (str(bundled) if bundled.is_file() else None)
    if gh:
        result = subprocess.run(
            [gh, "auth", "token", "--hostname", "github.com"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    raise ValueError(
        "Entre no GitHub CLI com gh auth login, ou defina GH_TOKEN apenas nesta máquina. "
        "Nunca coloque a credencial nos arquivos do projeto."
    )


def api(token: str, path: str, method: str = "GET", body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(
        "https://api.github.com" + path,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "User-Agent": "CalculosJuridicos-Publisher/1",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=60) as response:
        result = response.read()
        return json.loads(result) if result else None


def preflight(repository: str, access: str) -> str:
    repository = normalize_repository(repository)
    result = api(publication_token(), "/repos/" + repository)
    if bool(result["private"]) != (access == "private"):
        raise ValueError("A visibilidade do repositório difere da configuração.")
    if not result.get("permissions", {}).get("push"):
        raise ValueError("A conta atual não tem permissão para publicar nesse repositório.")
    print("Acesso ao repositório e visibilidade conferidos.")
    return normalize_repository(result.get("full_name", repository))


def upload_file(token: str, url: str, path: Path) -> None:
    import http.client
    from urllib.parse import urlsplit

    parsed = urlsplit(url)
    connection = http.client.HTTPSConnection(parsed.hostname, timeout=120)
    try:
        connection.putrequest("POST", parsed.path + "?" + parsed.query)
        connection.putheader("Authorization", "Bearer " + token)
        connection.putheader("User-Agent", "CalculosJuridicos-Publisher/1")
        connection.putheader("Accept", "application/vnd.github+json")
        connection.putheader("Content-Type", "application/octet-stream")
        connection.putheader("Content-Length", str(path.stat().st_size))
        connection.endheaders()
        with path.open("rb") as stream:
            sent = 0
            milestone = 0
            while chunk := stream.read(1024 * 1024):
                connection.send(chunk)
                sent += len(chunk)
                if sent // (8 * 1024 * 1024) > milestone:
                    milestone = sent // (8 * 1024 * 1024)
                    print(f"Envio {path.name}: {sent * 100 // path.stat().st_size}%", flush=True)
        response = connection.getresponse()
        response.read(1024 * 1024)
        if response.status != 201:
            raise ValueError(
                f"Falha no envio de {path.name}: HTTP {response.status}. "
                "O rascunho foi preservado."
            )
    finally:
        connection.close()


def publish(repository: str, directory: Path, notes_path: Path, access: str) -> None:
    from urllib.error import HTTPError
    from urllib.parse import urlencode, urlsplit

    repository = normalize_repository(repository)
    from liquidacao_custom.updates.settings import PUBLIC_KEY, REPOSITORY

    if REPOSITORY != repository:
        raise ValueError("O repositório difere do aplicativo gerado.")
    token = publication_token()
    transport_repository = preflight(repository, access)
    info = verify_manifest((directory / "update.json").read_bytes(), PUBLIC_KEY, repository)
    if info.version != APP_VERSION or info.display_version != APP_DISPLAY_VERSION:
        raise ValueError("O manifesto não corresponde à versão atual do projeto.")
    installer = directory / info.name
    with installer.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != info.sha256 or installer.stat().st_size != info.size:
        raise ValueError("O instalador mudou depois da assinatura.")

    try:
        existing = api(token, f"/repos/{transport_repository}/releases/tags/v{APP_VERSION}")
    except HTTPError as exc:
        if exc.code != 404:
            raise
        exc.close()
        existing = None
        page = 1
        while True:
            records = api(
                token,
                f"/repos/{transport_repository}/releases?per_page=100&page={page}",
            )
            matches = [record for record in records if record["tag_name"] == "v" + APP_VERSION]
            if len(matches) > 1:
                raise ValueError("Há mais de um rascunho desta versão.")
            if matches:
                existing = matches[0]
                break
            if len(records) < 100:
                break
            page += 1

    release_name = "Cálculos Jurídicos " + APP_DISPLAY_VERSION
    if existing:
        if not existing["draft"] or existing["name"] != release_name:
            raise ValueError("Esta versão já existe e uma publicação liberada não será substituída.")
        record = existing
        allowed = {info.name, info.name + ".sha256", "update.json"}
        for asset in existing["assets"]:
            if asset["name"] not in allowed:
                raise ValueError("O rascunho possui arquivos inesperados e foi preservado.")
            api(token, f"/repos/{transport_repository}/releases/assets/{asset['id']}", "DELETE")
        record = api(
            token,
            f"/repos/{transport_repository}/releases/{record['id']}",
            "PATCH",
            {"body": notes_path.read_text(encoding="utf-8-sig"), "draft": True},
        )
        print("Retomando o rascunho da mesma versão.", flush=True)
    else:
        record = api(
            token,
            f"/repos/{transport_repository}/releases",
            "POST",
            {
                "tag_name": "v" + APP_VERSION,
                "name": release_name,
                "body": notes_path.read_text(encoding="utf-8-sig"),
                "draft": True,
                "prerelease": False,
            },
        )

    upload_url = record["upload_url"].split("{", 1)[0]
    if urlsplit(upload_url).hostname != "uploads.github.com":
        raise ValueError("Endereço de envio inesperado. O rascunho foi preservado.")
    files = [installer, directory / (info.name + ".sha256"), directory / "update.json"]
    for path in files:
        upload_file(token, upload_url + "?" + urlencode({"name": path.name}), path)

    draft = api(token, f"/repos/{transport_repository}/releases/{record['id']}")
    assets = {asset["name"]: asset for asset in draft["assets"]}
    for path in files:
        asset = assets.get(path.name)
        if not asset or asset["state"] != "uploaded" or asset["size"] != path.stat().st_size:
            raise ValueError("O GitHub não confirmou os arquivos. O rascunho foi preservado.")

    released = api(
        token,
        f"/repos/{transport_repository}/releases/{record['id']}",
        "PATCH",
        {"draft": False, "make_latest": "true"},
    )
    (directory / "publicacao.json").write_text(
        json.dumps(
            {
                "version": APP_VERSION,
                "display_version": APP_DISPLAY_VERSION,
                "url": released["html_url"],
                "repository": repository,
                "access": access,
                "published": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print("Publicado: " + released["html_url"])


def export_key(output: Path) -> None:
    import getpass
    from cryptography.hazmat.primitives import serialization

    password = getpass.getpass("Senha para proteger o backup: ")
    confirmation = getpass.getpass("Repita a senha: ")
    if len(password) < 12 or password != confirmation:
        raise ValueError("Use uma senha de pelo menos 12 caracteres e confirme a mesma senha.")
    key = signing_key()
    encoded = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(password.encode("utf-8")),
    )
    with output.open("xb") as stream:
        stream.write(encoded)
    print(f"Backup criptografado criado: {output}")


def import_key(input_path: Path) -> None:
    import getpass
    from cryptography.hazmat.primitives import serialization

    key = serialization.load_pem_private_key(
        input_path.read_bytes(),
        password=getpass.getpass("Senha do backup: ").encode("utf-8"),
    )
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("O backup não possui uma chave de publicação válida.")
    public_key = base64.b64encode(key.public_key().public_bytes_raw()).decode("ascii")
    from liquidacao_custom.updates.settings import PUBLIC_KEY

    if PUBLIC_KEY and PUBLIC_KEY != public_key:
        raise ValueError("O backup não corresponde aos aplicativos já distribuídos.")
    path = key_path()
    if path.exists():
        current = signing_key().public_key().public_bytes_raw()
        if current != key.public_key().public_bytes_raw():
            raise ValueError("Já existe outra chave nesta conta e ela foi preservada.")
        print("A chave original já está disponível nesta conta.")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    stored = {
        "public_key": public_key,
        "protected_private": base64.b64encode(protect(key.private_bytes_raw())).decode("ascii"),
        "restored": datetime.now(timezone.utc).isoformat(),
    }
    with path.open("x", encoding="utf-8") as stream:
        json.dump(stored, stream, indent=2)
    print("Chave original restaurada e protegida nesta conta do Windows.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=["configure", "manifest", "preflight", "publish", "export-key", "import-key", "version"],
    )
    parser.add_argument("--repository", default="")
    parser.add_argument("--version", default=APP_VERSION)
    parser.add_argument("--display-version", default=APP_DISPLAY_VERSION)
    parser.add_argument("--access", choices=["private", "public"], default="public")
    parser.add_argument("--installer", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--notes", type=Path)
    parser.add_argument("--input", type=Path)
    arguments = parser.parse_args()
    try:
        if arguments.action == "version":
            build, display = release_version(arguments.version)
            print(json.dumps({"version": build, "display_version": display}))
        elif arguments.action == "export-key":
            export_key(arguments.output)
        elif arguments.action == "import-key":
            import_key(arguments.input)
        elif arguments.action == "configure":
            configure(
                arguments.repository,
                arguments.version,
                arguments.access,
                arguments.display_version,
            )
        elif arguments.action == "manifest":
            manifest(
                arguments.installer,
                arguments.output,
                arguments.repository,
                arguments.notes.read_text(encoding="utf-8-sig"),
            )
        elif arguments.action == "preflight":
            preflight(arguments.repository, arguments.access)
        else:
            publish(arguments.repository, arguments.output, arguments.notes, arguments.access)
    except Exception as exc:
        print("Publicação interrompida: " + str(exc), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
