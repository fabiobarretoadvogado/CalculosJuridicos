"""Base oficial exclusiva: arquivos, formato antigo ignorado e regras financeiras."""
import base64
import hashlib
import json
from datetime import date
from decimal import Decimal as D

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from liquidacao_custom.index_data import client, store
from liquidacao_custom.index_data.validation import validate_directory
from liquidacao_custom.updates import settings


def old_envelope(key):
    value = {"schema": 1, "app_id": client.APP_ID, "channel": "indices"}
    payload = json.dumps(value).encode()
    return json.dumps({"payload": base64.b64encode(payload).decode(),
                       "signature": base64.b64encode(key.sign(payload)).decode()}).encode()


def test_formato_antigo_assinado_e_rejeitado_sem_escrever(monkeypatch, tmp_path):
    key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(settings, "PUBLIC_KEY", base64.b64encode(key.public_key().public_bytes_raw()).decode())
    envelope = old_envelope(key)
    with pytest.raises(client.UnsupportedIndexFormat, match="Somente bases oficiais"):
        client.verify_manifest(envelope, settings.PUBLIC_KEY, settings.REPOSITORY)
    with pytest.raises(client.UnsupportedIndexFormat):
        client.install_package(b"arquivo antigo", envelope)
    assert not (store.storage_root() / "active.json").exists()


def test_base_ativa_antiga_e_ignorada_preservando_arquivos(monkeypatch):
    key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(settings, "PUBLIC_KEY", base64.b64encode(key.public_key().public_bytes_raw()).decode())
    root = store.storage_root()
    original = root / "versions" / "base-anterior" / "indice-original.json"
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_bytes(b'{"recuperacao":"preservar"}')
    before = original.read_bytes()
    envelope = old_envelope(key)
    pointer = root / "active.json"
    pointer.write_bytes(envelope)
    previous = root / "previous.json"
    previous.write_bytes(b"manifesto de recuperacao")
    dataset = store.current_dataset()
    assert dataset.directory == store.BUNDLED
    assert dataset.identity == store.bundled_dataset().identity
    assert dataset.origin == "instalador"
    assert "formato antigo" in dataset.warning
    assert "novas bases oficiais" in dataset.warning
    assert pointer.read_bytes() == envelope
    assert previous.read_bytes() == b"manifesto de recuperacao"
    assert original.read_bytes() == before
    assert not (root / "derived").exists()


def test_consulta_ignora_canal_antigo_mesmo_com_revisao_mais_recente(monkeypatch):
    monkeypatch.setattr(settings, "REPOSITORY", "owner/repo")
    monkeypatch.setattr(settings, "PUBLIC_KEY", "configurada")
    releases = [{"tag_name": "indices-20990101T000000000000Z", "draft": False, "assets": []}]
    monkeypatch.setattr(client, "read_small", lambda url, limit, token="": json.dumps(releases).encode())
    assert client.check_latest() is None


def test_somente_bases_oficiais_na_distribuicao():
    assert len(store.FILES) == 26
    assert {"fontes/bcb_ipca_1980_2026.json", "fontes/bcb_ipcae_1992_2026.json", "fontes/ipcae_historico_fonte.json"}.issubset(store.FILES)
    assert "inpc_oficial.json" in store.FILES and "igpm_oficial.json" in store.FILES
    assert all(not name.startswith("indices/") for name in store.FILES)
    assert not (store.BUNDLED / "indices" / "taxa_legal.csv").exists()
    assert "indices/taxa_legal.csv" not in store.FILES
    assert not (store.BUNDLED / "metodologia_1am.json").exists()
    validate_directory(store.BUNDLED)


def test_deflacoes_oficiais_sem_modalidade_antiga():
    from liquidacao_custom.core.indices import carregar_indice
    from liquidacao_custom.core.models import IndiceCorrecao, TipoJuros
    assert carregar_indice("inpc")["2026-08"] == (D("-0.32"), D("0.9968"))
    assert carregar_indice("igpm")["2026-07"] == (D("-1.16"), D("0.9884"))
    assert "taxa_legal" not in {item.value for item in IndiceCorrecao}
    assert "taxa_legal" not in {item.value for item in TipoJuros}


def test_civil3_acessa_historico_inpc_oficial_desde_2009():
    from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado
    from liquidacao_custom.core.motor_simplificado import executar_calculo
    value = CalculoSimplificado.model_validate({"perfil": "civil_3_v1",
        "dados_gerais": {"data_base": "2009-08-01"},
        "parcelas": [{"numero": 1, "data_vencimento": "2009-07-01", "valor_bruto": "1000"}]})
    result = executar_calculo(value)
    assert result.parcelas[0].valor_corrigido == D("1002.30")
    assert result.parcelas[0].juros_mora == D("10.02")
    assert result.premissas["sha256_inpc"] == hashlib.sha256((store.BUNDLED / "inpc_oficial.json").read_bytes()).hexdigest()
