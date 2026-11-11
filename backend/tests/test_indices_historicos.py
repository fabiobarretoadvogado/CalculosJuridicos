"""Origens históricas, conversões sem perda de precisão e marcos de juros preservados."""
import json
from datetime import date
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path

import pytest

from liquidacao_custom.api.routes import api_criterios
from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado
from liquidacao_custom.core.honorarios_isolados import CalculoHonorariosIsolados, executar_honorarios_isolados
from liquidacao_custom.core.honorarios_principais import criterios_correcao_honorarios, corrigir_valor_causa
from liquidacao_custom.core.moedas_historicas import conversao_monetaria
from liquidacao_custom.core.motor_simplificado import executar_calculo, criterios_publicos
from liquidacao_custom.index_data.validation import validate_directory

DATA = Path(__file__).resolve().parents[1] / "data"
CENTAVO = D("0.01")


@pytest.mark.parametrize("dia,divisor,simbolo", [
    ("1980-01-01", "2750000000000", "Cr$"), ("1986-02-27", "2750000000000", "Cr$"),
    ("1986-02-28", "2750000000", "Cz$"), ("1989-01-15", "2750000000", "Cz$"),
    ("1989-01-16", "2750000", "NCz$"), ("1990-03-15", "2750000", "NCz$"),
    ("1990-03-16", "2750000", "Cr$"), ("1993-07-31", "2750000", "Cr$"),
    ("1993-08-01", "2750", "CR$"), ("1994-06-30", "2750", "CR$"),
    ("1994-07-01", "1", "R$"),
])
def test_paridades_e_datas_exatas(dia, divisor, simbolo):
    equivalente, registro = conversao_monetaria(D(divisor), date.fromisoformat(dia))
    assert equivalente == 1
    if registro:
        assert registro["simbolo_origem"] == simbolo
        assert registro["divisor"] == divisor


def entrada(perfil="civil_2_v1", origem="1980-01-01", juros="2024-08-30", *, fim="2026-09-30", **extra):
    return CalculoSimplificado.model_validate({"perfil": perfil,
        "dados_gerais": {"data_base": fim, "criterio_inicio_juros": "data_fixa", "data_inicial_juros": juros},
        "parcelas": [{"numero": 1, "data_vencimento": origem, "valor_bruto": "1000.00"}], **extra})


def test_bases_completas_e_conciliadas():
    validate_directory(DATA)
    ipca = json.loads((DATA / "ipca_oficial.json").read_text(encoding="utf-8"))["ipca"]
    ipcae = json.loads((DATA / "indices_simplificados.json").read_text(encoding="utf-8"))["ipcae_taxas"]
    assert min(ipca) == "1980-01" and ipca["1980-01"] == "6.62"
    assert min(ipcae) == "1992-01" and ipcae["1992-01"] == "25.60"
    cobertura = criterios_correcao_honorarios()
    assert cobertura["data_base_minima"] == "1994-07-01"
    assert cobertura["ipca"]["inicio"] == "1980-01-01"
    assert cobertura["ipcae"]["inicio"] == "1992-01-01"


@pytest.mark.parametrize("perfil,fim", [
    ("fazenda_publica_1_v1", "2000-01-01"),
    ("ipca_taxa_legal_v1", "1994-07-01"),
    ("civil_2_v1", "1994-07-01"),
    ("civil_4_temporario_v1", "1994-07-01"),
    ("civil_5_taxa_legal_reconstruida_v1", "1994-07-01"),
])
def test_data_base_historica_da_api_independe_do_inicio_dos_juros(perfil, fim):
    criterios = api_criterios(perfil)
    assert criterios["data_base_minima"] == "1994-07-01"
    assert criterios["inicio_juros"] > fim
    calculo = entrada(perfil, "1993-08-01", criterios["inicio_juros"], fim=fim)
    resultado = executar_calculo(calculo)
    assert resultado.dados_gerais.data_base == date.fromisoformat(fim)
    assert resultado.parcelas[0].memoria_correcao[0].competencia == "1993-08"
    assert not resultado.parcelas[0].memoria_juros
    assert resultado.resumo.juros_mora == 0
    with pytest.raises(ValueError, match="posterior a 01/07/1994"):
        entrada(perfil, "1993-08-01", criterios["inicio_juros"], fim="1994-06-30")


def test_data_base_minima_do_civil_3_preserva_cobertura_do_inpc():
    criterios = api_criterios("civil_3_v1")
    assert criterios["data_base_minima"] == criterios["inicio_correcao"] == "2009-07-01"


@pytest.mark.parametrize("indice,origem,divisor", [("ipca", "1980-01-01", D("2750000000000")), ("ipcae", "1992-01-01", D("2750000"))])
def test_correcao_historica_confere_produto_independente(indice, origem, divisor):
    fonte = "ipca_oficial.json" if indice == "ipca" else "indices_simplificados.json"
    taxas = json.loads((DATA / fonte).read_text(encoding="utf-8"))["ipca" if indice == "ipca" else "ipcae_taxas"]
    fator = D(1)
    for comp, taxa in sorted(taxas.items()):
        if origem[:7] <= comp <= "2026-09":
            fator *= 1 + D(taxa) / 100
    calculo = CalculoHonorariosIsolados.model_validate({"base": "valor_causa", "dados_gerais": {"data_base": "2026-09-30"},
        "valor_causa": "1000", "data_protocolo": origem, "indice": indice, "percentual_sentenca": "10"})
    resultado = executar_honorarios_isolados(calculo)
    esperado = (D(1000) / divisor * fator).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    assert resultado.apuracao.base_atualizada == esperado
    assert resultado.apuracao.fator_acumulado == fator
    assert resultado.apuracao.valor_original + resultado.apuracao.correcao_monetaria == esperado
    assert resultado.premissas["entrada"]["valor_causa"] == "1000"
    assert resultado.premissas["conversoes_monetarias"][0]["divisor"] == str(divisor)
    assert "equivalência nominal" in resultado.apuracao.memoria[0].observacao


@pytest.mark.parametrize("perfil,limite", [("ipca_taxa_legal_v1", "2024-08-30"), ("civil_2_v1", "2009-07-01"),
    ("civil_4_temporario_v1", "2009-07-01"), ("civil_5_taxa_legal_reconstruida_v1", "2000-06-01")])
def test_civis_ampliam_correcao_sem_antecipar_juros(perfil, limite):
    criterios = criterios_publicos(perfil=perfil)
    assert criterios["inicio_correcao"] == "1980-01-01"
    assert criterios["inicio_juros"] == limite
    calculo = entrada(perfil=perfil, juros=limite)
    resultado = executar_calculo(calculo)
    parcela = resultado.parcelas[0]
    assert parcela.memoria_correcao[0].competencia == "1980-01"
    assert all(m.competencia >= limite[:7] for m in parcela.memoria_juros)
    assert parcela.valor_apurado + parcela.correcao_monetaria + parcela.juros_mora == parcela.total_parcela
    assert sum((c.valor for c in parcela.componentes.values()), D(0)) + parcela.valor_apurado == parcela.total_parcela
    assert resultado.premissas["entrada"]["parcelas"][0]["valor_bruto"] == "1000.00"
    with pytest.raises(ValueError):
        executar_calculo(entrada(perfil=perfil, juros="1999-12-31"))


@pytest.mark.parametrize("perfil", ["fazenda_publica_1_v1", "fazenda_publica_2_v1", "selic_ipcae_poupanca_v1", "selic_ipcae_2aa_v1"])
def test_fazenda_somente_correcao_antes_2009(perfil):
    resultado = executar_calculo(entrada(perfil=perfil, origem="1992-01-01", juros="2009-07-01"))
    parcela = resultado.parcelas[0]
    assert parcela.memoria_correcao[0].competencia == "1992-01"
    assert all(m.competencia >= "2009-07" for m in parcela.memoria_juros)
    assert parcela.valor_apurado + parcela.correcao_monetaria + parcela.juros_mora == parcela.total_parcela
    assert sum((c.valor for c in parcela.componentes.values()), D(0)) + parcela.valor_apurado == parcela.total_parcela
    with pytest.raises(ValueError, match="Juros"):
        entrada(perfil=perfil, origem="1992-01-01", juros="2009-06-30")


def test_multas_descontos_e_custas_historicos_conciliam():
    calculo = entrada(custas_despesas=[{"numero": 1, "nome": "Custas históricas", "data": "1992-01-01", "valor": "2750000"}],
        descontos={"perfil": "civil_2_v1", "criterio_inicio_juros": "data_fixa", "data_inicial_juros": "2009-07-01",
            "itens": [{"numero": 1, "descricao": "Pagamento histórico", "data": "1993-08-01", "valor": "2750", "encargos_sem_atualizacao": "275"}]})
    calculo.parcelas[0].multa_percentual = D(10)
    resultado = executar_calculo(calculo)
    p = resultado.parcelas[0]
    assert p.valor_apurado + p.correcao_monetaria + p.juros_mora + p.multa == p.total_parcela
    multa = p.multa_detalhes
    assert multa.valor_original + multa.correcao_monetaria + multa.juros_mora == multa.total_atualizado
    desconto = resultado.descontos.parcelas[0]
    assert desconto.valor_apurado + desconto.correcao_monetaria + desconto.juros_mora == desconto.total_parcela
    custa = resultado.custas_despesas[0]
    assert custa.valor_original == 1
    assert custa.valor_original + custa.correcao_monetaria == custa.valor_atualizado
    assert custa.conversao_monetaria["divisor"] == "2750000"


@pytest.mark.parametrize("indice,origem", [("ipca", "1979-12-31"), ("ipcae", "1991-12-31")])
def test_rejeita_origem_anterior_a_cada_indice(indice, origem):
    with pytest.raises(ValueError, match="série"):
        CalculoHonorariosIsolados.model_validate({"base": "valor_causa", "dados_gerais": {"data_base": "2026-09-30"},
            "valor_causa": "1000", "data_protocolo": origem, "indice": indice, "percentual_sentenca": "10"})


@pytest.mark.parametrize("perfil,origem", [("civil_2_v1", "1980-01-01"), ("fazenda_publica_1_v1", "1992-01-01")])
def test_api_historica_preserva_entrada_e_reedicao(perfil, origem):
    from fastapi.testclient import TestClient
    from liquidacao_custom.api.main import app
    client = TestClient(app)
    payload = entrada(perfil=perfil, origem=origem).model_dump(mode="json")
    response = client.post("/api/v1/calculo", json=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["premissas"]["conversoes_monetarias"][0]["data_origem"] == origem
    assert result["premissas"]["entrada"]["parcelas"][0]["valor_bruto"] == "1000.00"
    recovery = client.get("/api/v1/calculos/" + result["chave_recuperacao"])
    assert recovery.status_code == 200
    assert recovery.json()["entrada"]["parcelas"][0]["data_vencimento"] == origem
    assert recovery.json()["entrada"]["parcelas"][0]["valor_bruto"] == "1000.00"


def test_pdf_excel_csv_historicos_conservam_conversao(tmp_path):
    import io
    from pypdf import PdfReader
    from liquidacao_custom.core.relatorio_honorarios_pdf import exportar_pdf_honorarios
    from liquidacao_custom.core.exportadores import exportar_csv, exportar_excel
    import openpyxl
    c = CalculoHonorariosIsolados.model_validate({"base": "valor_causa", "indice": "ipcae", "valor_causa": "2750",
        "data_protocolo": "1993-08-01", "percentual_sentenca": "10", "dados_gerais": {"data_base": "1994-07-01", "observacoes": "EXEMPLO HIPOTÉTICO"}})
    r = executar_honorarios_isolados(c)
    pdf = PdfReader(io.BytesIO(exportar_pdf_honorarios(r)))
    text = "\n".join(page.extract_text() for page in pdf.pages)
    assert "Cruzeiro real" in text and "2750" in text
    links = [str(annotation.get_object().get("/A", {}).get("/URI", ""))
        for page in pdf.pages for annotation in page.get("/Annots", [])]
    assert any("10764" in url for url in links)
    assert "equivalência nominal" in " ".join(text.split())
    principal = executar_calculo(entrada())
    exportar_csv(principal, str(tmp_path / "csv"))
    premissas = json.loads((tmp_path / "csv/premissas.json").read_text(encoding="utf-8"))
    assert premissas["conversoes_monetarias"][0]["divisor"] == "2750000000000"
    arquivo = tmp_path / "historico.xlsx"
    exportar_excel(principal, str(arquivo))
    workbook = openpyxl.load_workbook(arquivo)
    assert any(row[0] == "conversoes_monetarias" and "2750000000000" in row[1] for row in workbook["Premissas"].values)
    workbook.close()
