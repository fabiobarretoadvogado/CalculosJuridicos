from copy import deepcopy
from decimal import Decimal
import io

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from liquidacao_custom.api.main import app


def entrada():
    return {'dados_gerais': {'data_base': '2026-08-31'}, 'parcelas': [
        {'numero': 1, 'data_vencimento': '2021-03-01', 'valor_bruto': '999.13', 'data_inicial_juros': '2026-03-23'},
        {'numero': 2, 'data_vencimento': '2026-05-01', 'valor_bruto': '1000.00'},
    ]}


@pytest.mark.parametrize('modo', ['citacao', 'data_fixa'])
def test_data_geral_afeta_apenas_poupanca_e_respeita_vencimento(modo):
    client = TestClient(app)
    dados = entrada()
    dados['dados_gerais']['criterio_inicio_juros'] = 'vencimento'
    antes = client.post('/api/v1/calculo', json=dados).json()
    dados['dados_gerais'].update(criterio_inicio_juros=modo, data_inicial_juros='2026-03-23')
    depois = client.post('/api/v1/calculo', json=dados)
    assert depois.status_code == 200
    for a, b in zip(antes['parcelas'], depois.json()['parcelas']):
        for chave in ('ipcae_pre', 'selic', 'ipcae_pos'):
            assert a['componentes'][chave] == b['componentes'][chave]
        assert b['componentes']['poupanca_pos']['data_inicial'] == max('2026-03-23', b['data_vencimento'])
    assert Decimal(depois.json()['parcelas'][0]['componentes']['poupanca_pre']['valor']) == 0
    assert Decimal(antes['parcelas'][0]['componentes']['poupanca_pre']['valor']) > 0
    legado = deepcopy(dados)
    legado['dados_gerais'].pop('criterio_inicio_juros')
    legado['dados_gerais'].pop('data_inicial_juros')
    assert client.post('/api/v1/calculo', json=legado).json()['parcelas'] == depois.json()['parcelas']


@pytest.mark.parametrize('modo', ['citacao', 'data_fixa'])
@pytest.mark.parametrize('rota', ['calculo', 'calculo/exportar/pdf', 'calculo/exportar/excel'])
def test_data_obrigatoria_tambem_nas_exportacoes(modo, rota):
    dados = entrada()
    dados['dados_gerais']['criterio_inicio_juros'] = modo
    response = TestClient(app).post('/api/v1/' + rota, json=dados)
    assert response.status_code == 422
    assert 'Informe a data de início dos juros' in response.text


def test_pdf_citacao_no_inicio_dos_criterios_sem_repetir_em_parcelas():
    dados = entrada()
    dados['dados_gerais'].update(criterio_inicio_juros='citacao', data_inicial_juros='2026-03-23')
    response = TestClient(app).post('/api/v1/calculo/exportar/pdf', json=dados)
    assert response.status_code == 200
    texto = '\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(response.content)).pages)
    assert texto.count('23/03/2026') == 1
    assert texto.index('Critérios do cálculo') < texto.index('Início dos juros: 23/03/2026 (citação).') < texto.index('Tema 905')
    assert 'Início informado dos juros' not in texto


def test_pdf_preserva_datas_diferentes_nos_criterios():
    dados = entrada()
    dados['parcelas'][1]['data_inicial_juros'] = '2026-06-01'
    response = TestClient(app).post('/api/v1/calculo/exportar/pdf', json=dados)
    assert response.status_code == 200
    texto = '\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(response.content)).pages)
    assert 'Parcelas 1: 23/03/2026' in texto
    assert 'Parcelas 2: 01/06/2026' in texto
    assert texto.index('01/06/2026') < texto.index('Valores por parcela')
