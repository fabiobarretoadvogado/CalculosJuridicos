from datetime import date
from decimal import Decimal as D
import io

import openpyxl
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from liquidacao_custom.api.main import app
from liquidacao_custom.core import motor_simplificado as m
from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado
from liquidacao_custom.core.perfis import EC136, ATUAL


@pytest.fixture
def base(monkeypatch):
    b = {'obtido_em': '2026-09-06', 'fontes': {},
         'selic': {'2025-08': '1', '2025-09': '1'},
         'ipcae_taxas': {'2025-09': '1', '2025-10': '0.9900990099009900990099009901'},
         'poupanca_total': {}}
    adicional = {'obtido_em': '2026-09-06', 'fontes': {}, 'selic': {'2025-09': '3', '2025-10': '3'}}
    monkeypatch.setattr(m, 'carregar_base', lambda: b)
    monkeypatch.setattr(m, 'carregar_base_ec136', lambda: adicional)
    return b, adicional


def entrada(inicio='2025-09-10', fim='2025-09-30', juros='2025-09-10'):
    return {'perfil': EC136, 'dados_gerais': {'data_base': fim, 'criterio_inicio_juros': 'citacao', 'data_inicial_juros': juros},
            'parcelas': [{'numero': 1, 'data_vencimento': inicio, 'valor_bruto': '1000.00'}]}


def calcular(**kw):
    return m.executar_calculo(CalculoSimplificado.model_validate(entrada(**kw)))


def test_ipcae_juros_simples_e_conciliacao(base):
    r = calcular()
    p = r.parcelas[0]
    saldo = D(1000) * D('1.01') ** D('0.7')
    assert p.componentes['ipcae_pos'].fator_acumulado == D('1.01') ** D('0.7')
    assert p.componentes['juros_2aa'].taxa_acumulada_percentual == D(2)/12*D('.7')
    assert p.total_parcela == m.moeda(saldo) + m.moeda(saldo*D('.02')/12*D('.7'))
    assert p.componentes['limite_selic'].valor == 0
    assert p.valor_apurado + sum(c.valor for c in p.componentes.values()) == p.total_parcela
    assert r.resumo.principal_apurado + r.resumo.correcao_monetaria + r.resumo.juros_mora == r.resumo.total_atualizado
    assert 'poupanca_pos' not in p.componentes


def test_parcela_posterior_a_2021_marca_faixa_anterior_como_nao_incidente(base):
    p = calcular(inicio='2025-08-01', fim='2025-09-30').parcelas[0]
    assert set(p.componentes) == {'ipcae_pre', 'poupanca_pre', 'selic', 'ipcae_pos', 'juros_2aa', 'limite_selic'}
    assert p.componentes['ipcae_pre'].data_inicial is None
    assert p.componentes['poupanca_pre'].data_inicial is None
    assert p.componentes['selic'].data_inicial == date(2025, 8, 1)
    assert p.componentes['selic'].data_final == date(2025, 9, 9)
    assert p.componentes['selic'].taxa_acumulada_percentual == D('1.3')
    assert p.componentes['selic'].valor == D('13.00')
    assert p.valor_apurado + sum(c.valor for c in p.componentes.values()) == p.total_parcela
    assert all('Tema 905' not in m.indice_aplicado and 'poupança' not in m.indice_aplicado.lower() for m in p.memoria_correcao + p.memoria_juros)


def test_cap_reduz_ao_valor_selic(base):
    base[1]['selic']['2025-09'] = '0.1'
    p = calcular().parcelas[0]
    assert p.total_parcela == D('1000.70')
    assert p.componentes['limite_selic'].valor < 0
    assert p.componentes['limite_selic'].taxa_acumulada_percentual == D('.07')
    assert p.valor_apurado + sum(c.valor for c in p.componentes.values()) == p.total_parcela
    assert any('menor valor = 1000.70' in x.observacao for x in p.memoria_correcao)


def test_compara_periodo_inteiro_nao_minimo_mensal(base):
    base[1]['selic'].update({'2025-09': '0', '2025-10': '5'})
    p = calcular(fim='2025-10-31').parcelas[0]
    assert p.componentes['limite_selic'].valor == 0
    assert p.componentes['juros_2aa'].taxa_acumulada_percentual == D(2)/12*D('1.7')


def test_inicio_juros_nao_limita_selic_nem_ipcae(base):
    r = calcular(inicio='2025-09-01', juros='2026-01-01')
    p = r.parcelas[0]
    assert p.componentes['selic'].valor == D('3.00')
    assert p.componentes['selic'].data_final == date(2025, 9, 9)
    assert p.componentes['ipcae_pos'].data_inicial == date(2025, 9, 10)
    assert p.juros_mora == 0
    assert p.componentes['juros_2aa'].data_inicial is None


def test_juros_nunca_anteriores_ao_vencimento(base):
    p = calcular(inicio='2025-09-25', juros='2020-01-01').parcelas[0]
    assert p.componentes['juros_2aa'].data_inicial == date(2025, 9, 25)
    assert p.componentes['juros_2aa'].taxa_acumulada_percentual == D(2)/12*D('.2')


def test_deflacao_preservada(base):
    base[0]['ipcae_taxas']['2025-09'] = '-1'
    assert calcular().parcelas[0].componentes['ipcae_pos'].valor < 0


def test_cobertura_independente_e_bloqueio_em_todas_saidas(base):
    assert m.criterios_publicos(perfil=EC136)['data_base_maxima'] == '2025-10-31'
    del base[1]['selic']['2025-10']
    assert m.criterios_publicos(perfil=EC136)['data_base_maxima'] == '2025-09-30'
    client = TestClient(app)
    for rota in ('calculo', 'calculo/exportar/pdf', 'calculo/exportar/excel', 'calculo/exportar/csv'):
        resp = client.post('/api/v1/'+rota, json=entrada(fim='2025-10-31'))
        assert resp.status_code == 400
        assert '30/09/2025' in resp.json()['detail']


def test_mes_corrente_parcial_nao_e_completo(base):
    base[0]['obtido_em'] = '2025-10-15'
    assert m.criterios_publicos(perfil=EC136)['data_base_maxima'] == '2025-09-30'


def test_indice_ausente_no_meio_nao_e_preenchido(base):
    del base[1]['selic']['2025-09']
    with pytest.raises(ValueError):
        calcular(fim='2025-10-31')


def test_pdf_excel_csv_e_catalogo(base):
    c = TestClient(app)
    catalogo = c.get('/api/v1/criterios', params={'perfil': EC136}).json()
    assert {ATUAL, EC136}.issubset({x['id'] for x in catalogo['perfis']})
    assert c.get('/api/v1/criterios?perfil=inexistente').status_code == 400
    pdf = c.post('/api/v1/calculo/exportar/pdf', json=entrada())
    assert pdf.status_code == 200
    texto = '\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
    assert 'Juros 2% a.a.' in texto and 'Limite SELIC' in texto
    assert 'Poupança pós' not in texto
    excel = c.post('/api/v1/calculo/exportar/excel', json=entrada())
    assert excel.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(excel.content))
    assert 'Índices por parcela' in wb.sheetnames
    assert any('Juros 2%' in str(c.value) for c in wb['Parcelas'][1])
    assert c.post('/api/v1/calculo/exportar/csv', json=entrada()).status_code == 200
