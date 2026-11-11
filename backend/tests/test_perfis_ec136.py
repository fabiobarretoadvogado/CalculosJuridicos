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
    assert 'Juros 2% a.a.' in texto and 'valores pós EC 136/2025 são líquidos' in texto
    assert 'Ajuste ao limite SELIC' not in texto and 'Limite SELIC' not in texto
    assert 'Poupança pós' not in texto
    excel = c.post('/api/v1/calculo/exportar/excel', json=entrada())
    assert excel.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(excel.content))
    assert 'Índices por parcela' in wb.sheetnames
    assert any('Juros 2%' in str(c.value) for c in wb['Parcelas'][1])
    assert c.post('/api/v1/calculo/exportar/csv', json=entrada()).status_code == 200


@pytest.mark.parametrize('taxa_limite, correcao, total', [
    ('0.1', '-0.47', '1000.70'), ('3', '6.99', '1008.16'),
])
def test_pdf_campos_pos_ec136_liquidos_sem_mutar_apuracao(base, taxa_limite, correcao, total):
    from liquidacao_custom.core.relatorio_componentes import componentes_liquidos
    from liquidacao_custom.core.relatorio_pdf import exportar_pdf, moeda

    base[1]['selic']['2025-09'] = taxa_limite
    dados = entrada()
    dados['parcelas'][0]['multa_percentual'] = '10'
    dados['descontos'] = {'perfil': EC136, 'itens': [
        {'numero': 1, 'descricao': 'Pagamento de teste', 'data': '2025-09-10', 'valor': '100'}]}
    resultado = m.executar_calculo(CalculoSimplificado.model_validate(dados))
    antes = resultado.model_dump(mode='json')
    reader = PdfReader(io.BytesIO(exportar_pdf(resultado)))
    texto = '\n'.join(p.extract_text() for p in reader.pages)
    assert resultado.model_dump(mode='json') == antes
    assert '(-) Descontos' in reader.pages[0].extract_text()
    assert 'Descontos abatidos' not in texto and 'descontos abatidos:' not in texto
    assert 'Ajuste ao limite SELIC' not in texto and 'Limite SELIC' not in texto
    parcela = resultado.parcelas[0]
    componentes = componentes_liquidos(parcela.componentes)
    assert componentes['ipcae_pos'].valor == D(correcao)
    assert componentes['juros_2aa'].valor == D('1.17')
    assert D('1000') + componentes['ipcae_pos'].valor + componentes['juros_2aa'].valor == D(total)
    assert f'R$ {moeda(D(correcao))}' in texto
    assert 'limite_selic' not in componentes
    assert parcela.valor_apurado + sum(c.valor for c in componentes.values()) == parcela.total_parcela
    multa = parcela.multa_detalhes
    assert multa.valor_original + sum(c.valor for c in componentes_liquidos(multa.componentes).values()) == multa.total_atualizado
    pagamento = resultado.descontos.parcelas[0]
    assert pagamento.valor_apurado + sum(c.valor for c in componentes_liquidos(pagamento.componentes).values()) == pagamento.total_parcela


def test_pdf_honorarios_ec136_liquido_com_limite_ativo(base):
    from liquidacao_custom.core.honorarios_proveito import CalculoHonorariosProveito, executar_honorarios_proveito
    from liquidacao_custom.core.relatorio_honorarios_pdf import exportar_pdf_honorarios

    base[1]['selic']['2025-09'] = '0.1'
    operacao = {'perfil': EC136, 'parcelas': [
        {'numero': 1, 'data_origem': '2025-09-10', 'valor': '1000'}]}
    dados = {'dados_gerais': {'data_base': '2025-09-30'}, 'percentual_sentenca': '10',
             'divida_original': operacao, 'divida_correta': operacao}
    resultado = executar_honorarios_proveito(CalculoHonorariosProveito.model_validate(dados))
    antes = resultado.model_dump(mode='json')
    texto = '\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(exportar_pdf_honorarios(resultado))).pages)
    assert resultado.model_dump(mode='json') == antes
    assert 'R$ -0,47' in texto and 'R$ 1.000,70' in texto
    assert 'Ajuste ao limite SELIC' not in texto and 'Limite SELIC' not in texto
