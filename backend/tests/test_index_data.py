from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from liquidacao_custom.index_data import client, store
from liquidacao_custom.index_data.catalog import catalog
from liquidacao_custom.index_data.validation import validate_directory
from liquidacao_custom.updates import settings
from liquidacao_custom.core.perfis import PERFIS

SCRIPTS = Path(__file__).resolve().parents[2] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location('publisher_indices', SCRIPTS / 'publisher_indices.py')
publisher = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(publisher)


def signed(value, key):
    payload = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    return json.dumps({'payload': base64.b64encode(payload).decode(),
                       'signature': base64.b64encode(key.sign(payload)).decode()}).encode()


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    key = Ed25519PrivateKey.generate()
    monkeypatch.setattr(settings, 'PUBLIC_KEY', base64.b64encode(key.public_key().public_bytes_raw()).decode())
    source = tmp_path / 'source'
    shutil.copytree(store.BUNDLED, source)
    legal = source / 'taxa_legal_oficial.json'
    data = json.loads(legal.read_text())
    last = max(data['taxa_legal'])
    data['taxa_legal'][last] = str(Decimal(data['taxa_legal'][last]) + Decimal('0.000001'))
    legal.write_text(json.dumps(data), encoding='utf-8')
    directory = publisher.prepare(tmp_path / 'packages', settings.REPOSITORY, key=key, source=source)
    envelope = (directory / 'indices-update.json').read_bytes()
    manifest = client.verify_manifest(envelope, settings.PUBLIC_KEY, settings.REPOSITORY)
    raw = (directory / manifest['package']['name']).read_bytes()
    return key, manifest, envelope, raw


def test_bases_oficiais_conciliam():
    validate_directory(store.BUNDLED)


def test_catalogo_exibe_fontes_canonicas_e_limites():
    result = catalog()
    assert len(result['series']) == 9
    assert {p['id'] for p in result['perfis']} == {p['id'] for p in PERFIS} | {'ipcae_1am_simples_v1', 'poupanca_deposito_v1'}
    assert next(s for s in result['series'] if s['id'] == 'ipca')['inicio'] == '1980-01'
    assert next(s for s in result['series'] if s['id'] == 'ipcae')['inicio'] == '1992-01'
    legal = next(s for s in result['series'] if s['id'] == 'taxa_legal')
    assert legal['inicio'] == '2024-08'
    assert all(not s['legado'] for s in result['series'])
    assert next(s for s in result['series'] if s['id'] == 'inpc')['inicio'] == '2009-07'
    assert any(s['id'] == 'igpm' for s in result['series'])
    selic = next(s for s in result['series'] if s['id'] == 'selic')
    assert 'encerrada' in selic['observacao']
    assert selic['fim'] == '2026-10'


def test_assinatura_adulterada_rejeitada(prepared):
    _, manifest, envelope, raw = prepared
    wrapped = json.loads(envelope)
    wrapped['payload'] = base64.b64encode(json.dumps({**manifest, 'channel': 'stable'}).encode()).decode()
    with pytest.raises(client.UpdateError):
        client.verify_manifest(json.dumps(wrapped).encode(), settings.PUBLIC_KEY, settings.REPOSITORY)


def test_pacote_contem_somente_dados(prepared):
    _, manifest, envelope, raw = prepared
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert set(archive.namelist()) == set(store.FILES)
        assert all(name.endswith(('.json', '.csv')) for name in archive.namelist())
    assert len(raw) < 300_000


def test_instalacao_atomica_contexto_e_cache(prepared):
    _, manifest, envelope, raw = prepared
    from liquidacao_custom.core.indices import carregar_indice
    ref = store.DataPath('taxa_legal_oficial.json')
    old = ref.read_bytes()
    old_csv = carregar_indice('ipca')
    with store.index_context() as pinned:
        result = client.install_package(raw, envelope)
        assert result['atualizado']
        assert ref.read_bytes() == old
        assert store.current_dataset().identity == pinned.identity
    assert ref.read_bytes() != old
    assert store.current_dataset().identity == manifest['dataset_id']
    assert carregar_indice('ipca') == old_csv
    assert carregar_indice('ipca') is not old_csv
    assert client.install_package(raw, envelope)['atualizado'] is False


def test_download_adulterado_preserva_base_anterior(prepared):
    _, manifest, envelope, raw = prepared
    previous = store.current_dataset()
    with pytest.raises(client.UpdateError):
        client.install_package(raw[:-1], envelope)
    assert store.current_dataset().identity == previous.identity
    assert not (store.storage_root() / 'active.json').exists()


def test_zip_fora_da_lista_rejeitado(prepared, tmp_path):
    _, manifest, envelope, raw = prepared
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('../programa.py', 'invalido')
    bad = buffer.getvalue()
    manifest['package'].update(size=len(bad), sha256=hashlib.sha256(bad).hexdigest())
    with pytest.raises(client.UpdateError):
        client.unpack_package(bad, manifest, tmp_path / 'extraction')
    assert not (tmp_path / 'programa.py').exists()


def test_reducao_de_cobertura_preserva_base(prepared):
    key, manifest, envelope, raw = prepared
    client.install_package(raw, envelope)
    active = store.storage_root() / 'active.json'
    previous = active.read_bytes()
    manifest['revision'] = '20000101T000000000000Z'
    revision = manifest['revision']
    manifest['package']['name'] = f'indices-v2-{revision}.zip'
    manifest['package']['url'] = f'https://github.com/{settings.REPOSITORY}/releases/download/indices-v2-{revision}/indices-v2-{revision}.zip'
    # Identidade diferente impede que a verificação de igualdade encerre a operação.
    manifest['files']['taxa_legal_oficial.json']['sha256'] = '0' * 64
    manifest['dataset_id'] = store.dataset_id(manifest['files'])
    with pytest.raises(client.UpdateError):
        client.install_package(raw, signed(manifest, key))
    assert active.read_bytes() == previous


def test_base_local_adulterada_retorna_ao_instalador(prepared):
    _, manifest, envelope, raw = prepared
    client.install_package(raw, envelope)
    (store.storage_root() / 'versions' / manifest['dataset_id'] / 'ipca_oficial.json').write_text('{}')
    dataset = store.current_dataset()
    assert dataset.origin == 'instalador'
    assert dataset.warning


def test_calculo_registra_versao_da_base():
    from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado
    from liquidacao_custom.core.motor_simplificado import executar_calculo
    value = CalculoSimplificado.model_validate({'perfil': 'civil_2_v1',
        'dados_gerais': {'data_base': '2026-08-01'},
        'parcelas': [{'numero': 1, 'historico': 'Teste', 'data_vencimento': '2025-01-01',
                      'valor_bruto': '100', 'valor_pago_na_data': '0'}]})
    result = executar_calculo(value)
    assert result.premissas['base_indices']['sha256'] == store.current_dataset().identity


def test_api_catalogo_e_falha_de_atualizacao(monkeypatch):
    from liquidacao_custom.api.main import app
    from liquidacao_custom.index_data import routes
    with TestClient(app) as api:
        assert api.get('/api/v1/indices/catalogo').status_code == 200
        def fail(): raise OSError('rede indisponível')
        monkeypatch.setattr(routes, 'synchronize', fail)
        assert api.post('/api/v1/indices/atualizar').status_code == 503
        assert api.get('/api/v1/indices/catalogo').json()['erro_atualizacao']


def test_consulta_ignora_releases_do_programa_e_nao_publicados(prepared, monkeypatch):
    _, manifest, envelope, raw = prepared
    revision = manifest['revision']
    prefix = f'https://github.com/{settings.REPOSITORY}/releases/download/indices-v2-{revision}/'
    releases = [{'tag_name': 'v2026.9.20.12', 'draft': False, 'assets': []},
                {'tag_name': 'indices-99990101T000000000000Z', 'draft': True, 'assets': []},
                {'tag_name': 'indices-v2-' + revision, 'draft': False, 'prerelease': True, 'assets': [
                    {'name': 'indices-update.json', 'browser_download_url': prefix + 'indices-update.json'},
                    {'name': manifest['package']['name'], 'size': len(raw), 'browser_download_url': manifest['package']['url']}]}]
    def read(url, limit, token=''):
        return envelope if url.endswith('indices-update.json') else json.dumps(releases).encode()
    monkeypatch.setattr(client, 'read_small', read)
    result = client.check_latest()
    assert result[0]['dataset_id'] == manifest['dataset_id']


def test_pacote_legado_assinado_nao_reduz_base_historica(prepared, monkeypatch):
    key, manifest, _, _ = prepared
    manifest['files'] = {name: manifest['files'][name] for name in store.FILES_BASE}
    manifest['dataset_id'] = store.dataset_id(manifest['files'])
    envelope = signed(manifest, key)
    active = store.storage_root() / 'active.json'
    active.parent.mkdir(parents=True)
    active.write_bytes(envelope)

    monkeypatch.setattr(client, 'check_latest', lambda: (manifest, envelope, manifest['package']['url']))

    def unexpected_download(*args, **kwargs):
        pytest.fail("A base histórica torna desnecessário baixar o pacote anterior.")

    monkeypatch.setattr(client, 'open_url', unexpected_download)
    current = store.current_dataset()
    assert current == store.bundled_dataset()
    result = client.synchronize()
    assert result['atualizado'] is False
    assert result['base'] == current.metadata()
    assert active.read_bytes() == envelope


def test_regressao_real_de_cobertura_e_rejeitada(prepared, tmp_path):
    key, _, _, _ = prepared
    source = tmp_path / 'shorter-source'
    shutil.copytree(store.BUNDLED, source)
    path = source / 'taxa_legal_oficial.json'
    data = json.loads(path.read_text())
    del data['taxa_legal'][max(data['taxa_legal'])]
    path.write_text(json.dumps(data), encoding='utf-8')
    directory = publisher.prepare(tmp_path / 'shorter-packages', settings.REPOSITORY, key=key, source=source)
    envelope = (directory / 'indices-update.json').read_bytes()
    manifest = client.verify_manifest(envelope, settings.PUBLIC_KEY, settings.REPOSITORY)
    with pytest.raises(ValueError, match='cobertura'):
        client.install_package((directory / manifest['package']['name']).read_bytes(), envelope)
    assert not (store.storage_root() / 'active.json').exists()


def test_exportacao_rejeita_resultado_de_outra_base():
    from liquidacao_custom.api.main import app
    with TestClient(app) as api:
        response = api.post('/api/v1/calculo/exportar/pdf', json={}, headers={'X-Indices-Base': '0' * 64})
        assert response.status_code == 409
        assert 'Calcule novamente' in response.json()['detail']
        response = api.post('/api/v1/calculo/exportar/pdf', json={}, headers={'X-Indices-Base': store.current_dataset().identity})
        assert response.status_code == 422  # A base corresponde; o corpo vazio é validado normalmente.


def test_consulta_futura_da_selic_e_rejeitada(tmp_path):
    source = tmp_path / 'future-consultation'
    shutil.copytree(store.BUNDLED, source)
    path = source / 'indices_ec136.json'
    data = json.loads(path.read_text())
    data['selic_obtido_em'] = '2099-01-01'
    path.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='futura'):
        validate_directory(source)
