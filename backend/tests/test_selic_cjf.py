import io
from decimal import Decimal as D
from fastapi.testclient import TestClient
from pypdf import PdfReader
import pytest
from liquidacao_custom.api.main import app
from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado
from liquidacao_custom.core.motor_simplificado import executar_calculo


def entrada(inicio='2024-03-01', fim='2025-10-31', juros=None):
    return {'perfil':'selic_cjf_v1','dados_gerais':{'data_base':fim},'parcelas':[
        {'numero':1,'data_vencimento':inicio,'valor_bruto':'1231.86','data_inicial_juros':juros}]}


def test_reproduz_projef_dos_autos():
    r = executar_calculo(CalculoSimplificado.model_validate(entrada()))
    assert r.resumo.total_atualizado == D('1460.12')
    assert r.parcelas[0].componentes['selic'].taxa_acumulada_percentual == D('18.53')
    assert r.memoria_mensal[0].competencia == '2024-04'
    assert 'Taxa de 2024-03' in r.memoria_mensal[0].observacao
    assert 'Taxa de 2025-09' in r.memoria_mensal[-1].observacao
    assert r.resumo.juros_mora == 0
    assert r.premissas['criterios'][:2] == [
        'SELIC como índice único de atualização monetária e juros de mora.',
        'Aplicação mensal conforme o Manual de Cálculos da Justiça Federal, item 4.2.1, nota 4, alínea c.',
    ]


def test_mes_da_data_base_sem_selic():
    r = executar_calculo(CalculoSimplificado.model_validate(entrada(inicio='2025-10-01')))
    assert r.resumo.total_atualizado == D('1231.86')
    assert r.premissas['data_referencia_selic'] == '2025-10-01'
    assert r.premissas['ultima_competencia_selic'] is None
    assert 'Último índice aplicado: nenhum.' in r.premissas['criterios'][-1]


def test_referencia_mensal_e_ultima_taxa_sem_alterar_selic():
    from liquidacao_custom.core.motor_selic_cjf import criterios_cjf
    inicial = executar_calculo(CalculoSimplificado.model_validate(entrada(fim='2026-08-01')))
    final = executar_calculo(CalculoSimplificado.model_validate(entrada(fim='2026-08-31')))
    assert inicial.resumo == final.resumo
    assert inicial.memoria_mensal == final.memoria_mensal
    for r in (inicial, final):
        assert r.premissas['data_referencia_selic'] == '2026-08-01'
        assert r.premissas['ultima_competencia_selic'] == '2026-07'
        assert 'Último índice aplicado: 07/2026.' in r.premissas['criterios'][-1]
    assert final.dados_gerais.data_base.isoformat() == '2026-08-31'
    assert final.premissas['entrada']['dados_gerais']['data_base'] == '2026-08-31'
    criterios = criterios_cjf()
    assert criterios['data_base_maxima'] == '2026-09-01'
    assert criterios['data_referencia_selic_maxima'] == '2026-09-01'
    assert criterios['ultima_competencia_selic_disponivel'] == '2026-08'


def test_competencia_fechada_aplicavel_no_primeiro_dia_do_mes_corrente():
    from liquidacao_custom.core.motor_selic_cjf import criterios_cjf
    criterios = criterios_cjf({'selic': {'2026-07': '1.22', '2026-08': '1.09', '2026-09': '0.21'},
                              'obtido_em': '2026-09-06', 'fontes': {}})
    assert criterios['data_base_maxima'] == '2026-09-01'
    assert criterios['ultima_competencia_selic_disponivel'] == '2026-08'


def test_nao_usar_taxa_parcial_do_mes_da_consulta():
    from liquidacao_custom.core.motor_selic_cjf import criterios_cjf
    criterios = criterios_cjf({'selic': {'2026-07': '1.22', '2026-08': '0.50'},
                              'obtido_em': '2026-08-18', 'fontes': {}})
    assert criterios['data_base_maxima'] == '2026-08-01'
    assert criterios['ultima_competencia_selic_disponivel'] == '2026-07'


def test_conta_dativo_parte_do_original_e_reproduz_os_dois_totais_historicos():
    from copy import deepcopy
    dados = entrada(inicio='2025-03-31', fim='2026-09-01')
    dados['parcelas'][0]['valor_bruto'] = '5000.00'
    for fim, taxa, total in [('2025-05-01', '2.02', '5101.00'),
                             ('2026-06-01', '17.00', '5850.00'),
                             ('2026-09-01', '20.43', '6021.50')]:
        caso = deepcopy(dados)
        caso['dados_gerais']['data_base'] = fim
        r = executar_calculo(CalculoSimplificado.model_validate(caso))
        assert r.resumo.principal_original == D('5000.00')
        assert r.resumo.total_atualizado == D(total)
        assert r.parcelas[0].componentes['selic'].taxa_acumulada_percentual == D(taxa)
    assert r.premissas['ultima_competencia_selic'] == '2026-08'
    assert 'Taxa de 2026-08: 1.09%' in r.memoria_mensal[-1].observacao


def test_referencia_selic_preserva_data_exata_das_custas_e_valor_causa():
    from copy import deepcopy
    dados = entrada(fim='2026-08-31')
    dados['custas_despesas'] = [{'numero': 1, 'nome': 'Taxa', 'data': '2025-10-01', 'valor': '100'}]
    dados['honorarios_sucumbenciais'] = {'aplicar': True, 'base': 'valor_causa', 'valor_causa': '1000', 'data_protocolo': '2025-10-01', 'indice': 'ipcae', 'percentual': '10'}
    final = executar_calculo(CalculoSimplificado.model_validate(dados))
    anterior = deepcopy(dados)
    anterior['dados_gerais']['data_base'] = '2026-08-01'
    inicial = executar_calculo(CalculoSimplificado.model_validate(anterior))
    assert final.premissas['data_referencia_selic'] == '2026-08-01'
    assert final.parcelas[0].total_parcela == inicial.parcelas[0].total_parcela
    assert final.resumo.custas != inicial.resumo.custas
    assert final.honorarios_sucumbenciais.base_atualizada != inicial.honorarios_sucumbenciais.base_atualizada
    from liquidacao_custom.core.relatorio_pdf import exportar_pdf
    texto = '\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(exportar_pdf(final))).pages)
    assert 'Data-base SELIC 01/08/2026' in texto
    assert 'Último índice aplicado: 07/2026' in texto
    assert 'Data final das demais operações: 31/08/2026.' in texto


def test_pdf_selic_referencia_mensal_no_cabecalho_e_rodapes():
    from liquidacao_custom.core.relatorio_pdf import exportar_pdf
    dados = entrada(fim='2026-08-31')
    dados['parcelas'] *= 20
    dados['parcelas'] = [dict(p, numero=i+1, historico=f'Parcela {i+1}') for i, p in enumerate(dados['parcelas'])]
    r = executar_calculo(CalculoSimplificado.model_validate(dados))
    leitor = PdfReader(io.BytesIO(exportar_pdf(r)))
    textos = [p.extract_text() for p in leitor.pages]
    assert 'Data-base SELIC 01/08/2026' in textos[0]
    assert 'Último índice aplicado: 07/2026' in textos[0]
    assert all('Barreto Fontes | Data-base SELIC 01/08/2026' in t for t in textos)
    assert all('31/08/2026' not in t for t in textos)


def test_citacao_nao_interrompe_indice_unico():
    r = executar_calculo(CalculoSimplificado.model_validate(entrada(juros='2026-03-01')))
    assert r.resumo.total_atualizado == D('1460.12')


def test_escopo_e_meses_incompletos():
    client = TestClient(app)
    assert client.post('/api/v1/calculo',json=entrada(inicio='2021-01-01')).status_code==200
    for rota in ['calculo','calculo/exportar/pdf','calculo/exportar/excel','calculo/exportar/csv']:
        assert client.post('/api/v1/'+rota,json=entrada(fim='2026-09-30')).status_code==400


def test_selic_historica_sem_limite_de_2022():
    r = executar_calculo(CalculoSimplificado.model_validate(entrada(inicio='2021-01-01', fim='2021-02-28')))
    assert r.parcelas[0].componentes['selic'].taxa_acumulada_percentual == D('0.15')
    assert r.resumo.total_atualizado == D('1233.71')
    assert r.memoria_mensal[0].competencia == '2021-02'
    assert 'sha256_selic_historica' in r.premissas


def test_selic_anterior_ao_tema905_e_preservacao_dos_outros_modos():
    c = TestClient(app)
    dados = entrada(inicio='2009-06-01', fim='2009-07-31')
    assert c.post('/api/v1/calculo',json=dados).status_code == 200
    dados['perfil'] = 'selic_ipcae_poupanca_v1'
    assert c.post('/api/v1/calculo',json=dados).status_code == 422


def test_limite_inicial_segue_cobertura_e_nao_data_fixa():
    from liquidacao_custom.core.motor_selic_cjf import criterios_cjf
    criterios = criterios_cjf({'selic': {'2001-02': '1'}, 'obtido_em': '2026-09-06', 'fontes': {}})
    assert criterios['inicio'] == '2001-02-01'
    c = TestClient(app)
    perfis = c.get('/api/v1/criterios?perfil=selic_cjf_v1').json()['perfis']
    assert next(p for p in perfis if p['id'] == 'selic_cjf_v1')['nome'] == 'SELIC'
    resp = c.post('/api/v1/calculo',json=entrada(inicio='1980-01-01'))
    assert resp.status_code == 400
    assert 'cobertura' in resp.json()['detail']


def test_historico_sem_lacunas_e_indices_ausentes_nao_preenchidos(monkeypatch):
    from liquidacao_custom.core import motor_selic_cjf as m
    dados = m.base_cjf()
    meses = sorted(dados['selic'])
    from datetime import date
    for anterior, atual in zip(meses,meses[1:]):
        assert m.proximo_mes(date.fromisoformat(anterior+'-01')).strftime('%Y-%m') == atual
    del dados['selic']['2021-01']
    monkeypatch.setattr(m,'base_cjf',lambda: dados)
    with pytest.raises(ValueError, match='Índice ausente'):
        executar_calculo(CalculoSimplificado.model_validate(entrada(inicio='2021-01-01',fim='2021-02-28')))


def test_exportacoes_retratam_selic_sem_outras_colunas():
    c = TestClient(app)
    pdf = c.post('/api/v1/calculo/exportar/pdf',json=entrada())
    assert pdf.status_code==200
    texto = '\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
    assert 'SELIC única' in texto and 'Manual de Cálculos' in texto
    assert 'Poupança pós' not in texto and 'Limite SELIC' not in texto
    for formato in ['excel','csv']:
        assert c.post('/api/v1/calculo/exportar/'+formato,json=entrada()).status_code==200


def test_exportacoes_preservam_referencia_selic_e_data_informada():
    import json
    import zipfile
    import openpyxl
    c = TestClient(app)
    dados = entrada(fim='2026-08-31')
    excel = c.post('/api/v1/calculo/exportar/excel', json=dados)
    assert excel.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(excel.content))
    gerais = dict(wb['Dados Gerais'].iter_rows(min_row=2, values_only=True))
    assert gerais['Data-Base'] == '2026-08-31'
    assert gerais['Data-base SELIC (referência mensal)'] == '2026-08-01'
    assert gerais['Último índice SELIC aplicado (competência)'] == '2026-07'
    csv = c.post('/api/v1/calculo/exportar/csv', json=dados)
    assert csv.status_code == 200
    with zipfile.ZipFile(io.BytesIO(csv.content)) as arquivo:
        caminho = next(n for n in arquivo.namelist() if n.endswith('premissas.json'))
        premissas = json.loads(arquivo.read(caminho))
    assert premissas['entrada']['dados_gerais']['data_base'] == '2026-08-31'
    assert premissas['data_referencia_selic'] == '2026-08-01'
    assert premissas['ultima_competencia_selic'] == '2026-07'
