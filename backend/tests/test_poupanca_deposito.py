import copy
import csv
import io
import json
import zipfile
from datetime import date
from decimal import Decimal as D

import openpyxl
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from liquidacao_custom.api.main import app
from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado
from liquidacao_custom.core.motor_simplificado import executar_calculo, criterios_publicos
from liquidacao_custom.core import motor_poupanca_deposito as motor


def entrada():
    return {'perfil': 'selic_cjf_v1',
        'dados_gerais': {'data_base': '2026-03-01', 'criterio_inicio_juros': 'vencimento'},
        'parcelas': [{'numero': 1, 'data_vencimento': '2024-11-14', 'valor_bruto': '5800'}],
        'descontos': {'perfil': 'poupanca_deposito_v1', 'criterio_inicio_juros': 'citacao', 'itens': [
            {'numero': 1, 'data': '2025-12-31', 'valor': '1100', 'encargos_sem_atualizacao': '100'}]}}


def calcular(p):
    return executar_calculo(CalculoSimplificado.model_validate(p))


@pytest.fixture
def taxas(monkeypatch):
    dados = ({'obtido_em': '2026-03-01', 'fonte': 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.195/dados'}, {
        date(2012, 5, 4): (date(2012, 6, 4), D('0.5')),
        date(2026, 1, 1): (date(2026, 2, 1), D('1')),
        date(2026, 2, 1): (date(2026, 3, 1), D('2')),
        date(2026, 3, 1): (date(2026, 4, 1), D('3')),
        date(2026, 1, 15): (date(2026, 2, 15), D('0.7')),
    }, {'fixture': 'taxas_sinteticas'})
    monkeypatch.setattr(motor, 'carregar_poupanca', lambda: dados)
    return dados


def test_fatores_reinvestidos_somente_na_conta_e_parte_nominal_preservada(taxas):
    p = entrada()
    r = calcular(p)
    sem_deposito = copy.deepcopy(p)
    sem_deposito.pop('descontos')
    original = calcular(sem_deposito)
    assert r.parcelas == original.parcelas
    assert r.resumo.principal_apurado == D('5800')
    assert r.resumo.abatimentos == D('1130.20')
    assert r.resumo.total_atualizado == original.resumo.total_atualizado - D('1130.20')
    assert r.descontos.resumo.correcao_monetaria == D('30.20')
    assert r.descontos.resumo.juros_mora == 0
    c = r.descontos.parcelas[0].componentes['poupanca_deposito']
    assert c.base_calculo == D('1000')
    assert c.fator_acumulado == D('1.0302')
    assert c.data_inicial == date(2026, 1, 1)
    assert c.data_final == date(2026, 3, 1)
    assert len(r.descontos.memoria_mensal) == 2
    assert r.descontos.memoria_mensal[1].valor_base == D('1010')
    assert set(r.descontos.parcelas[0].componentes) == {'poupanca_deposito'}
    assert any('parcela fora da conta' in m.observacao for m in r.descontos.memoria_mensal)
    json.dumps(r.premissas)
    json.dumps(r.descontos.premissas)


@pytest.mark.parametrize('dia', [29, 30, 31])
def test_fim_de_mes_inicia_no_primeiro_dia_seguinte(dia, taxas):
    p = entrada()
    p['descontos']['itens'][0]['data'] = f'2025-12-{dia}'
    assert calcular(p).resumo.abatimentos == D('1130.20')


def test_periodo_incompleto_nao_recebe_pro_rata_ou_taxa_antecipada(taxas):
    p = entrada()
    p['dados_gerais']['data_base'] = '2026-01-31'
    r = calcular(p)
    assert r.resumo.abatimentos == D('1100')
    assert r.descontos.memoria_mensal == []
    assert r.descontos.parcelas[0].componentes['poupanca_deposito'].data_inicial is None
    p['dados_gerais']['data_base'] = '2026-02-01'
    assert calcular(p).resumo.abatimentos == D('1110')


def test_taxa_e_aniversario_da_data_nao_primeiro_dia_arbitrario(taxas):
    p = entrada()
    p['dados_gerais']['data_base'] = '2026-02-28'
    p['descontos']['itens'][0]['data'] = '2026-01-15'
    r = calcular(p)
    assert r.resumo.abatimentos == D('1107')
    assert r.descontos.parcelas[0].componentes['poupanca_deposito'].data_final == date(2026, 2, 15)


def test_taxa_ausente_e_data_futura_nao_sao_estimadas(taxas):
    p = entrada()
    taxas[1].pop(date(2026, 2, 1))
    with pytest.raises(ValueError, match='Índice ausente'):
        calcular(p)
    p['dados_gerais']['data_base'] = '2026-04-01'
    with pytest.raises(ValueError, match='Poupança: atualize'):
        calcular(p)


def test_deposito_desmarcado_nao_afeta_indices_ou_total(taxas):
    p = entrada()
    p['descontos']['itens'][0].update(aplicar=False, data='2099-01-01')
    r = calcular(p)
    p.pop('descontos')
    assert r.resumo == calcular(p).resumo
    assert r.descontos is None


def test_criterios_usa_consulta_e_nao_vencimento_futuro(taxas):
    c = criterios_publicos(perfil='poupanca_deposito_v1')
    assert c['data_base_maxima'] == '2026-03-01'
    assert c['perfil'] == 'poupanca_deposito_v1'
    assert all(item['id'] != 'poupanca_deposito_v1' for item in c['perfis'])


def test_caso_real_selic_independente_e_ir_nominal():
    p = entrada()
    p['dados_gerais']['data_base'] = '2026-09-01'
    p['descontos']['itens'][0].update(valor='5845.82', encargos_sem_atualizacao='531.89')
    r = calcular(p)
    assert r.parcelas[0].total_parcela == D('7200.70')
    assert r.descontos.resumo.correcao_monetaria == D('289.50')
    assert r.descontos.resumo.total_atualizado == D('6135.32')
    assert r.resumo.total_atualizado == D('1065.38')
    assert r.descontos.parcelas[0].componentes['poupanca_deposito'].base_calculo == D('5313.93')
    assert len(r.descontos.memoria_mensal) == 8


def test_diferenca_cresce_apos_deposito_sem_cessar_selic_da_divida():
    p = entrada()
    p['descontos']['itens'][0].update(valor='5845.82', encargos_sem_atualizacao='531.89')
    p['dados_gerais']['data_base'] = '2026-05-01'
    maio = calcular(p)
    p['dados_gerais']['data_base'] = '2026-09-01'
    setembro = calcular(p)
    assert setembro.resumo.total_atualizado > maio.resumo.total_atualizado
    assert setembro.resumo.correcao_monetaria - maio.resumo.correcao_monetaria == D('261.00')
    assert setembro.descontos.resumo.correcao_monetaria - maio.descontos.resumo.correcao_monetaria < D('261.00')


def test_api_e_exportacoes_preservam_coluna_fator_selecao_e_memoria(taxas):
    client = TestClient(app)
    p = entrada()
    resposta = client.post('/api/v1/calculo', json=p)
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()['descontos']['resumo']['total_atualizado'] == '1130.20'
    resposta = client.get('/api/v1/criterios', params={'perfil': 'poupanca_deposito_v1'})
    assert resposta.status_code == 200
    pdf = client.post('/api/v1/calculo/exportar/pdf', json=p)
    assert pdf.status_code == 200
    texto = '\n'.join(page.extract_text() for page in PdfReader(io.BytesIO(pdf.content)).pages)
    assert 'Poupança - remuneração da conta' in texto
    assert 'Fator 1,0302' in texto
    assert '1.130,20' in texto
    assert 'parte fora da conta R$ 100,00' in texto
    assert 'Início dos juros dos descontos' not in texto
    excel = client.post('/api/v1/calculo/exportar/excel', json=p)
    assert excel.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(excel.content))
    valores = [str(c.value or '') for ws in wb.worksheets for row in ws for c in row]
    assert any('Poupança - remuneração da conta' in v for v in valores)
    assert any('1.0302' in v for v in valores)
    resposta = client.post('/api/v1/calculo/exportar/csv', json=p)
    assert resposta.status_code == 200
    with zipfile.ZipFile(io.BytesIO(resposta.content)) as z:
        nome = next(n for n in z.namelist() if n.endswith('indices_descontos.csv'))
        linhas = list(csv.reader(io.StringIO(z.read(nome).decode('utf-8-sig'))))
        assert linhas[1][1] == 'Poupança - remuneração da conta'
        assert linhas[1][6] == '1.0302'
