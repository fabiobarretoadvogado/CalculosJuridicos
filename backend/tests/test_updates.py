from __future__ import annotations

import base64
import hashlib
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from liquidacao_custom.metadata import APP_ID, INSTALLER_PREFIX
from liquidacao_custom.updates.client import UpdateError, verify_manifest, version_tuple


REPOSITORY = "fabiobarretoadvogado/CalculosJuridicos"
VERSION = "2026.9.19.1"


def signed_envelope(*, digest: str | None = None, url: str | None = None):
    key = Ed25519PrivateKey.generate()
    name = f"{INSTALLER_PREFIX}-{VERSION}-x64.exe"
    payload = {
        "schema": 1,
        "app_id": APP_ID,
        "version": VERSION,
        "display_version": "1.00",
        "channel": "stable",
        "architecture": "x64",
        "notes": "Versão de teste",
        "installer": {
            "name": name,
            "size": 1234,
            "sha256": digest or hashlib.sha256(b"installer").hexdigest(),
            "url": url or f"https://github.com/{REPOSITORY}/releases/download/v{VERSION}/{name}",
        },
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    envelope = json.dumps(
        {
            "payload": base64.b64encode(encoded).decode(),
            "signature": base64.b64encode(key.sign(encoded)).decode(),
        }
    ).encode()
    public = base64.b64encode(key.public_key().public_bytes_raw()).decode()
    return envelope, public


def test_manifesto_assinado_e_aceito():
    envelope, public = signed_envelope()
    info = verify_manifest(envelope, public, REPOSITORY)
    assert info.version == VERSION
    assert info.display_version == "1.00"
    assert info.size == 1234


def test_manifesto_adulterado_e_rejeitado():
    envelope, public = signed_envelope()
    wrapped = json.loads(envelope)
    payload = base64.b64decode(wrapped["payload"])
    wrapped["payload"] = base64.b64encode(payload.replace(b"1.00", b"9.99")).decode()
    with pytest.raises(UpdateError):
        verify_manifest(json.dumps(wrapped).encode(), public, REPOSITORY)


def test_instalador_fora_do_repositorio_e_rejeitado():
    envelope, public = signed_envelope(
        url=(
            "https://github.com/outro/projeto/releases/download/"
            f"v{VERSION}/{INSTALLER_PREFIX}-{VERSION}-x64.exe"
        )
    )
    with pytest.raises(UpdateError):
        verify_manifest(envelope, public, REPOSITORY)


@pytest.mark.parametrize("value", ["1", "1.2.3", "01.2.3.4", "1.2.3.-1", "1.2.3.65536"])
def test_versao_invalida(value: str):
    with pytest.raises(UpdateError):
        version_tuple(value)
