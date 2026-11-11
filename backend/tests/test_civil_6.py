"""Operações fictícias: juros simples anteriores ao CC/2002 e fases compartilhadas."""
import csv
import io
import json
from datetime import date
from decimal import Decimal as D
from types import SimpleNamespace

import pytest

from liquidacao_custom.core import motor_civil_4, motor_ipca_taxa_legal
from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado
from liquidacao_custom.core.motor_simplificado import criterios_publicos, executar_calculo, moeda


def entrada(correcao="2002-01-01", juros="2002-01-01", fim="2003-01-01", valor="1000"):
    return CalculoSimplificado.model_validate({
        "perfil": "civil_6_v1",
        "dados_gerais": {"data_base": fim, "criterio_inicio_juros": "data_fixa", "data_inicial_juros": juros},
        "parcelas": [{"numero": 1, "historico": "Operação fictícia", "data_vencimento": correcao, "valor_bruto": valor}],
    })


@pytest.fixture
def indices(tmp_path, monkeypatch):
    competencias = [f"{ano}-{mes:02}" for ano in range(2000, 2025) for mes in range(1, 13)]
    dados = {
        "ipca_oficial.json": {"ipca": dict.fromkeys(competencias, "0"), "obtido_em": "2025-01-02",
            "fontes": {"ipca": "https://example.invalid/ipca"}},
        "taxa_legal_oficial.json": {"taxa_legal": {"2024-08": "0.400000", "2024-09": "0.500000"},
            "obtido_em": "2025-01-02", "fonte_publica": "https://example.invalid/legal"},
        "selic_historica.json": {"selic": [{"data": "01/01/2000", "valor": "1"}],
            "obtido_em": "2025-01-02", "fonte": "https://example.invalid/selic-historica"},
        "indices_simplificados.json": {"selic": dict.fromkeys(competencias[1:], "1"),
            "obtido_em": "2025-01-02", "fontes": {"selic": "https://example.invalid/selic"}},
        "indices_ec136.json": {"selic": [], "obtido_em": "2025-01-02",
            "fontes": {"selic": "https://example.invalid/selic-recente"}},
    }
    for nome, conteudo in dados.items():
        (tmp_path / nome).write_text(json.dumps(conteudo), encoding="utf-8")
    monkeypatch.setattr(motor_civil_4, "BASE_IPCA", tmp_path / "ipca_oficial.json")
    monkeypatch.setattr(motor_civil_4, "BASE_TAXA_LEGAL", tmp_path / "taxa_legal_oficial.json")
    monkeypatch.setattr(motor_ipca_taxa_legal, "BASE_TAXA_LEGAL", tmp_path / "taxa_legal_oficial.json")
    monkeypatch.setattr(motor_civil_4, "current_dataset", lambda: SimpleNamespace(directory=tmp_path))
    return tmp_path


def mudar(indices, arquivo, serie, competencia, valor):
    caminho = indices / arquivo
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if valor is None:
        del dados[serie][competencia]
    else:
        dados[serie][competencia] = valor
    caminho.write_text(json.dumps(dados), encoding="utf-8")


def concilia(r):
    for p in r.parcelas:
        assert p.valor_apurado + sum((c.valor for c in p.componentes.values()), D(0)) == p.total_parcela
        assert p.valor_apurado + p.correcao_monetaria + p.juros_mora == p.total_parcela
    assert r.resumo.principal_apurado + sum(r.resumo.totais_componentes.values(), D(0)) == sum(p.total_parcela for p in r.parcelas)


def test_doze_meses_05_simples_sem_capitalizacao(indices):
    r = executar_calculo(entrada())
    p = r.parcelas[0]
    assert p.componentes["juros_05am"].taxa_acumulada_percentual == D(6)
    assert p.juros_mora == D("60.00")
    assert p.total_parcela == D("1060.00")
    assert all(m.valor_base == 1000 for m in p.memoria_juros)
    assert r.premissas["memoria_selic_civil"] == []
    assert len(r.premissas["memoria_juros_05am"]) == 12
    concilia(r)


def test_ipca_concomitante_e_juros_sobre_capital_corrigido(indices):
    mudar(indices, "ipca_oficial.json", "ipca", "2002-12", "2")
    r = executar_calculo(entrada("2002-12-01", "2002-12-01", "2003-01-01"))
    p = r.parcelas[0]
    assert p.componentes["ipca_pre"].valor == D("20.00")
    assert p.componentes["juros_05am"].base_calculo == D(1020)
    assert p.componentes["juros_05am"].valor == D("5.10")
    assert p.total_parcela == D("1025.10")
    concilia(r)


@pytest.mark.parametrize("modo", ["data_fixa", "citacao", "por_parcela"])
def test_juros_podem_anteceder_correcao(indices, modo):
    c = entrada("2003-01-01", "2002-12-01", "2003-01-01")
    c.dados_gerais.criterio_inicio_juros = modo
    if modo == "por_parcela":
        c.parcelas[0].data_inicial_juros = date(2002, 12, 1)
    r = executar_calculo(c)
    assert r.parcelas[0].total_parcela == D("1005.00")
    assert r.parcelas[0].componentes["ipca_pre"].data_inicial is None
    assert r.parcelas[0].componentes["juros_05am"].data_inicial == date(2002, 12, 1)
    concilia(r)


@pytest.mark.parametrize("inicio,fim,juros_05,selic", [
    ("2003-01-10", "2003-01-11", "0.16", "0.00"),
    ("2003-01-11", "2003-01-12", "0.00", "0.32"),
    ("2003-01-10", "2003-01-12", "0.16", "0.32"),
    ("2002-12-01", "2002-12-01", "0.00", "0.00"),
])
def test_corte_exato_10_11_janeiro_e_intervalo_vazio(indices, inicio, fim, juros_05, selic):
    r = executar_calculo(entrada(inicio, inicio, fim))
    p = r.parcelas[0]
    assert p.componentes["juros_05am"].valor == D(juros_05)
    assert p.componentes["selic"].valor == D(selic)
    assert all(x["fim"] <= "2003-01-10" for x in r.premissas["memoria_juros_05am"])
    assert all(x["inicio"] >= "2003-01-11" for x in r.premissas["memoria_selic_civil"])
    concilia(r)


def test_nao_capitaliza_juros05_na_passagem_para_selic(indices):
    r = executar_calculo(entrada("2002-12-01", "2002-12-01", "2003-02-01"))
    p = r.parcelas[0]
    assert p.componentes["juros_05am"].taxa_acumulada_percentual == pytest.approx(D("0.5") * (1 + D(10) / 31), abs=D("1e-24"))
    assert p.componentes["selic"].base_calculo == 1000
    assert p.componentes["selic"].taxa_acumulada_percentual == D(21) / 31
    assert p.total_parcela == moeda(D(1000) * (1 + (D("0.5") * (1 + D(10) / 31) + D(21) / 31) / 100))
    concilia(r)


def test_selic_deduzida_preserva_datas_independentes_no_corte(indices):
    mudar(indices, "ipca_oficial.json", "ipca", "2003-01", "2")
    r = executar_calculo(entrada("2003-02-01", "2002-12-01", "2003-02-01"))
    p = r.parcelas[0]
    assert p.componentes["ipca_pre"].data_inicial is None
    assert p.componentes["juros_selic_deduzida"].data_inicial == date(2003, 1, 11)
    assert p.componentes["juros_selic_deduzida"].valor == 0
    assert r.premissas["memoria_selic_civil"][0]["piso_zero_aplicado"] is True
    concilia(r)


def test_consolidacao_2024_inclui_juros05_uma_unica_vez(indices):
    r = executar_calculo(entrada(fim="2024-10-01"))
    p = r.parcelas[0]
    taxa05 = D("0.5") * (12 + D(10) / 31)
    taxa_selic = D(21) / 31 + 11 + 20 * 12 + 7 + D(29) / 31
    consolidado = D(1000) * (1 + (taxa05 + taxa_selic) / 100)
    assert p.componentes["ipca_pos"].base_calculo == pytest.approx(consolidado)
    assert p.componentes["taxa_legal"].base_calculo == pytest.approx(consolidado)
    legal = (D("0.4") * 2 / 31 + D("0.5")).quantize(D("0.000001"))
    assert p.total_parcela == moeda(consolidado) + moeda(consolidado * legal / 100)
    concilia(r)


@pytest.mark.parametrize("inicio", ["2009-07-01", "2024-08-29", "2024-08-30", "2024-09-01"])
def test_regimes_posteriores_iguais_ao_civil4(indices, inicio):
    c6 = entrada(inicio, inicio, "2024-10-01")
    c4 = c6.model_copy(update={"perfil": "civil_4_temporario_v1"})
    r6, r4 = executar_calculo(c6), executar_calculo(c4)
    assert r6.resumo.total_atualizado == r4.resumo.total_atualizado
    for chave, componente in r4.parcelas[0].componentes.items():
        assert r6.parcelas[0].componentes[chave] == componente
    assert r6.parcelas[0].componentes["juros_05am"].data_inicial is None
    concilia(r6)


@pytest.mark.parametrize("arquivo,serie,competencia", [
    ("ipca_oficial.json", "ipca", "2002-12"),
    ("indices_simplificados.json", "selic", "2003-01"),
    ("taxa_legal_oficial.json", "taxa_legal", "2024-09"),
])
def test_indice_ausente_nao_e_estimado(indices, arquivo, serie, competencia):
    mudar(indices, arquivo, serie, competencia, None)
    with pytest.raises(ValueError, match="[Íí]ndice ausente"):
        executar_calculo(entrada(fim="2024-10-01"))


def test_criterios_cobertura_e_preservacao_civil4(indices):
    c6 = criterios_publicos(perfil="civil_6_v1")
    c4 = criterios_publicos(perfil="civil_4_temporario_v1")
    assert {"id": "civil_6_v1", "nome": "Civil 6"} in c6["perfis"]
    assert c6["transicao_cc_2002"] == "2003-01-11"
    assert c6["inicio_correcao"] == "2000-01-01"
    assert c6["inicio_juros"] == "1980-01-01"
    assert c6["inicio"] == "1994-07-01"
    assert c4["inicio_juros"] == "2009-07-01"
    assert "transicao_cc_2002" not in c4


def test_descontos_multa_api_recuperacao_e_exportacoes(indices, tmp_path):
    import openpyxl
    from fastapi.testclient import TestClient
    from pypdf import PdfReader
    from liquidacao_custom.api.main import app
    from liquidacao_custom.core.exportadores import exportar_csv, exportar_excel
    from liquidacao_custom.core.relatorio_pdf import exportar_pdf

    c = entrada()
    c.parcelas[0].multa_percentual = D(2)
    c.descontos = c.descontos.model_validate({"itens": [{"numero": 1, "data": "2002-01-01", "valor": "100"}]})
    client = TestClient(app)
    assert client.get("/api/v1/criterios?perfil=civil_6_v1").status_code == 200
    resposta = client.post("/api/v1/calculo", json=c.model_dump(mode="json"))
    assert resposta.status_code == 200, resposta.text
    recuperado = client.get("/api/v1/calculos/" + resposta.json()["chave_recuperacao"])
    assert recuperado.json()["entrada"]["perfil"] == "civil_6_v1"
    r = executar_calculo(c)
    assert r.parcelas[0].multa_detalhes.total_atualizado == D("21.20")
    assert r.descontos.resumo.total_atualizado == D("106.00")
    assert r.resumo.total_atualizado == D("975.20")
    exportar_csv(r, str(tmp_path / "csv"))
    linhas = list(csv.reader((tmp_path / "csv" / "indices_por_parcela.csv").open(encoding="utf-8-sig")))
    assert any("0,5%" in linha[1] for linha in linhas[1:])
    exportar_excel(r, str(tmp_path / "ficticio.xlsx"))
    wb = openpyxl.load_workbook(tmp_path / "ficticio.xlsx")
    assert any("0,5%" in str(cell.value) for row in wb["Índices por parcela"] for cell in row)
    texto = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(exportar_pdf(r))).pages)
    assert "0,5%" in texto and "10/01/2003" in texto
    assert "MEMÓRIA DOS ENCARGOS" in texto
    assert "Civil 6" not in texto and "civil_6" not in texto


def test_comparacao_dividas_anteriores_2003(indices):
    from pypdf import PdfReader
    from liquidacao_custom.core.honorarios_proveito import CalculoHonorariosProveito, executar_honorarios_proveito
    from liquidacao_custom.core.relatorio_honorarios_pdf import exportar_pdf_honorarios
    def operacao(valor):
        return {"perfil": "civil_6_v1", "criterio_inicio_juros": "vencimento",
            "parcelas": [{"numero": 1, "data_origem": "2002-01-01", "valor": valor}]}
    c = CalculoHonorariosProveito.model_validate({"dados_gerais": {"data_base": "2003-01-01"},
        "divida_original": operacao("1000"), "divida_correta": operacao("500"), "percentual_sentenca": "10"})
    r = executar_honorarios_proveito(c)
    assert r.proveito_economico == D(530)
    texto = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(exportar_pdf_honorarios(r))).pages)
    assert "0,5%" in texto and "MEMÓRIA DOS ENCARGOS" in texto
    assert "Civil 6" not in texto
