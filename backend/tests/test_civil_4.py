"""Cenários fictícios para validar termos, fases e consolidação do perfil temporário."""
import csv
import io
import json
from datetime import date
from decimal import Decimal as D
from types import SimpleNamespace

import pytest

from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado
from liquidacao_custom.core.motor_simplificado import criterios_publicos, executar_calculo, moeda
from liquidacao_custom.core import motor_civil_4, motor_ipca_taxa_legal


def entrada(correcao="2024-06-01", juros="2024-07-01", fim="2024-08-01", valor="1000.00"):
    return CalculoSimplificado.model_validate({
        "perfil": "civil_4_temporario_v1",
        "dados_gerais": {"data_base": fim, "criterio_inicio_juros": "data_fixa", "data_inicial_juros": juros},
        "parcelas": [{"numero": 1, "historico": "Exemplo fictício", "data_vencimento": correcao, "valor_bruto": valor}],
    })


@pytest.fixture
def indices(tmp_path, monkeypatch):
    ipca = tmp_path / "ipca_oficial.json"
    legal = tmp_path / "taxa_legal_oficial.json"
    ipca.write_text(json.dumps({"ipca": {"2024-06": "2", "2024-07": "-1", "2024-08": "3", "2024-09": "-2"},
        "obtido_em": "2024-10-01", "fontes": {"ipca": "https://example.invalid/ipca"}}), encoding="utf-8")
    legal.write_text(json.dumps({"taxa_legal": {"2024-08": "0.400000", "2024-09": "0.500000"},
        "obtido_em": "2024-10-01", "fonte_publica": "https://example.invalid/tl"}), encoding="utf-8")
    (tmp_path / "selic_historica.json").write_text(json.dumps({"selic": [{"data": "01/06/2024", "valor": "0.9"}],
        "obtido_em": "2024-10-01", "fonte": "https://example.invalid/selic-historica"}), encoding="utf-8")
    (tmp_path / "indices_simplificados.json").write_text(json.dumps({"selic": {"2024-07": "1", "2024-08": "1.2"},
        "obtido_em": "2024-10-01", "fontes": {"selic": "https://example.invalid/selic"}}), encoding="utf-8")
    (tmp_path / "indices_ec136.json").write_text(json.dumps({"selic": [], "obtido_em": "2024-10-01",
        "fontes": {"selic": "https://example.invalid/selic-recente"}}), encoding="utf-8")
    monkeypatch.setattr(motor_civil_4, "BASE_IPCA", ipca)
    monkeypatch.setattr(motor_civil_4, "BASE_TAXA_LEGAL", legal)
    monkeypatch.setattr(motor_ipca_taxa_legal, "BASE_TAXA_LEGAL", legal)
    monkeypatch.setattr(motor_civil_4, "current_dataset", lambda: SimpleNamespace(directory=tmp_path))
    return tmp_path


def concilia(resultado):
    for p in resultado.parcelas:
        assert p.valor_apurado + sum((c.valor for c in p.componentes.values()), D(0)) == p.total_parcela
    assert resultado.resumo.principal_apurado + sum(resultado.resumo.totais_componentes.values(), D(0)) == sum((p.total_parcela for p in resultado.parcelas), D(0))


def test_ipca_antes_selic_sem_sobreposicao(indices):
    r = executar_calculo(entrada())
    p = r.parcelas[0]
    assert p.componentes["ipca_pre"].valor == D("20.00")
    assert p.componentes["selic"].base_calculo == D("1020")
    assert p.componentes["selic"].valor == D("10.20")
    assert p.total_parcela == D("1030.20")
    assert p.componentes["ipca_pre"].data_final == date(2024, 6, 30)
    assert p.componentes["selic"].data_inicial == date(2024, 7, 1)
    assert p.componentes["taxa_legal"].data_inicial is None
    assert [m.competencia for m in p.memoria_correcao] == ["2024-06", "2024-07"]
    concilia(r)


def test_juros_antes_correcao_sem_consolidacao_intermediaria(indices):
    r = executar_calculo(entrada("2024-07-16", "2024-07-01", "2024-08-01"))
    p = r.parcelas[0]
    liquida, integral = p.componentes["juros_selic_deduzida"], p.componentes["selic"]
    assert liquida.base_calculo == integral.base_calculo == D(1000)
    assert liquida.taxa_acumulada_percentual == pytest.approx(D(2) * D(15) / 31, abs=D("1e-24"))
    assert integral.taxa_acumulada_percentual == D(16) / 31
    assert p.total_parcela == D("1014.84")
    assert p.componentes["ipca_pre"].data_inicial is None
    registros = r.premissas["memoria_selic_civil"]
    assert registros[0]["ipca_deducao"] == "-1"
    assert registros[0]["diferenca_selic_ipca"] == "2"
    assert registros[0]["piso_zero_aplicado"] is False
    assert registros[0]["fim"] == "2024-07-15"
    assert registros[1]["inicio"] == "2024-07-16"
    concilia(r)


def test_piso_zero_na_deducao_sem_correcao_indevida(indices):
    r = executar_calculo(entrada("2024-07-01", "2024-06-01", "2024-07-01"))
    p = r.parcelas[0]
    assert p.total_parcela == D("1000.00")
    assert p.componentes["ipca_pre"].data_inicial is None
    assert p.componentes["selic"].data_inicial is None
    raw = r.premissas["memoria_selic_civil"][0]
    assert raw["diferenca_selic_ipca"] == "-1.1"
    assert raw["taxa_liquida"] == "0"
    assert raw["piso_zero_aplicado"] is True
    concilia(r)


def test_transicao_consolida_total_uma_vez_e_taxa_legal_simples(indices):
    r = executar_calculo(entrada("2024-08-01", "2024-07-01", "2024-10-01"))
    p = r.parcelas[0]
    consolidado = D(1000) * (1 + (D(2) + D("1.2") * 29 / 31) / 100)
    corrigido = consolidado * D("1.03") ** (D(2) / 31) * D("0.98")
    taxa_legal = (D("0.4") * 2 / 31 + D("0.5")).quantize(D("0.000001"))
    assert p.componentes["ipca_pos"].base_calculo == consolidado
    assert p.componentes["taxa_legal"].base_calculo == pytest.approx(corrigido, abs=D("0.00000001"))
    assert p.componentes["taxa_legal"].valor == moeda(corrigido * taxa_legal / 100)
    assert p.total_parcela == moeda(corrigido) + moeda(corrigido * taxa_legal / 100)
    assert r.premissas["memoria_transicao_civil"][0]["base_consolidada_transicao"] == str(consolidado)
    assert {m.valor_base for m in p.memoria_juros if "Taxa Legal" in m.indice_aplicado} == {p.componentes["taxa_legal"].base_calculo}
    concilia(r)


def test_correcao_posterior_corte_preserva_termos_e_selic_liquida(indices):
    r = executar_calculo(entrada("2024-09-01", "2024-07-01", "2024-10-01"))
    p = r.parcelas[0]
    assert p.componentes["selic"].data_inicial is None
    assert p.componentes["juros_selic_deduzida"].valor == D("20.00")
    assert p.componentes["ipca_pos"].data_inicial == date(2024, 9, 1)
    assert p.componentes["taxa_legal"].data_inicial == date(2024, 8, 30)
    assert p.componentes["taxa_legal"].base_calculo == D("999.6")
    concilia(r)


@pytest.mark.parametrize("modo", ["citacao", "por_parcela"])
def test_inicio_juros_global_ou_individual(indices, modo):
    calculo = entrada("2024-07-16", "2024-07-01", "2024-08-01")
    calculo.dados_gerais.criterio_inicio_juros = modo
    if modo == "por_parcela":
        calculo.parcelas[0].data_inicial_juros = date(2024, 7, 1)
    assert executar_calculo(calculo).parcelas[0].total_parcela == D("1014.84")


def test_juros_posteriores_ao_corte_sem_selic(indices):
    r = executar_calculo(entrada("2024-08-01", "2024-09-01", "2024-10-01"))
    p = r.parcelas[0]
    assert p.valor_corrigido == D("1009.40")
    assert p.componentes["selic"].data_inicial is None
    assert p.componentes["taxa_legal"].base_calculo == pytest.approx(D("1009.4"), abs=D("0.0000001"))
    assert p.juros_mora == D("5.05")
    assert p.total_parcela == D("1014.45")
    concilia(r)


def test_corte_29_30_agosto_e_data_base_excluida(indices):
    r = executar_calculo(entrada("2024-08-29", "2024-08-29", "2024-08-30"))
    p = r.parcelas[0]
    assert p.componentes["selic"].data_inicial == p.componentes["selic"].data_final == date(2024, 8, 29)
    assert p.componentes["selic"].valor == D("0.39")
    assert p.componentes["ipca_pos"].data_inicial is None
    assert p.juros_mora == 0
    concilia(r)


def test_somente_dia_30_na_fase_legal(indices):
    r = executar_calculo(entrada("2024-08-30", "2024-08-30", "2024-08-31"))
    p = r.parcelas[0]
    fator = D("1.03") ** (D(1) / D(31))
    assert p.componentes["selic"].data_inicial is None
    assert p.componentes["ipca_pos"].data_inicial == p.componentes["ipca_pos"].data_final == date(2024, 8, 30)
    assert p.valor_corrigido == moeda(D(1000) * fator)
    assert p.juros_mora == moeda(D(1000) * fator * D("0.012903") / 100)
    concilia(r)


@pytest.mark.parametrize("dia", ["2024-08-29", "2024-08-30", "2024-09-01"])
def test_data_base_igual_termos_nao_incide(indices, dia):
    r = executar_calculo(entrada(dia, dia, dia))
    assert r.parcelas[0].total_parcela == D("1000.00")
    assert not r.memoria_mensal
    assert all(c.data_inicial is None for c in r.parcelas[0].componentes.values())
    concilia(r)


def test_deflacao_em_ipca_antes_selic(indices):
    r = executar_calculo(entrada("2024-07-01", "2024-08-01", "2024-08-29"))
    assert r.parcelas[0].componentes["ipca_pre"].valor == D("-10.00")
    assert r.parcelas[0].componentes["selic"].base_calculo == D("990")
    concilia(r)


def test_indices_ausentes_nao_viram_zero(indices):
    ipca = indices / "ipca_oficial.json"
    data = json.loads(ipca.read_text())
    del data["ipca"]["2024-07"]
    ipca.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="Índice ausente: ipca"):
        executar_calculo(entrada("2024-07-01", "2024-08-01", "2024-08-29"))


def test_selic_ausente_nao_vira_zero(indices):
    arquivo = indices / "indices_simplificados.json"
    dados = json.loads(arquivo.read_text())
    del dados["selic"]["2024-07"]
    arquivo.write_text(json.dumps(dados), encoding="utf-8")
    with pytest.raises(ValueError, match="Índice ausente: selic"):
        executar_calculo(entrada())


def test_selic_parcial_na_consulta_bloqueada(indices):
    arquivo = indices / "indices_simplificados.json"
    dados = json.loads(arquivo.read_text())
    dados["obtido_em"] = "2024-07-20"
    arquivo.write_text(json.dumps(dados), encoding="utf-8")
    with pytest.raises(ValueError, match="ainda não fechada"):
        executar_calculo(entrada())


def test_selic_duplicada_divergente_bloqueada(indices):
    arquivo = indices / "indices_ec136.json"
    dados = json.loads(arquivo.read_text())
    dados["selic"] = [{"data": "01/07/2024", "valor": "9.99"}]
    arquivo.write_text(json.dumps(dados), encoding="utf-8")
    with pytest.raises(ValueError, match="divergentes"):
        executar_calculo(entrada())


def test_taxa_legal_ausente_no_intervalo_bloqueada(indices):
    arquivo = indices / "taxa_legal_oficial.json"
    dados = json.loads(arquivo.read_text())
    del dados["taxa_legal"]["2024-08"]
    arquivo.write_text(json.dumps(dados), encoding="utf-8")
    with pytest.raises(ValueError, match="Índice ausente: taxa_legal"):
        executar_calculo(entrada("2024-08-30", "2024-08-30", "2024-10-01"))


def test_datas_e_cobertura_publicas_independentes(indices):
    c = criterios_publicos(perfil="civil_4_temporario_v1")
    assert c["inicio_correcao"] == "2024-06-01"
    assert c["inicio_juros"] == "2024-06-01"
    assert c["transicao"] == "2024-08-30"
    assert c["data_base_maxima"] == "2024-10-01"
    with pytest.raises(ValueError, match="data-base máxima"):
        executar_calculo(entrada("2024-08-30", "2024-08-30", "2024-10-02"))


def test_descontos_multas_componentes_exportados_sem_caso_real(indices, tmp_path):
    from liquidacao_custom.core.exportadores import exportar_csv, exportar_excel
    from liquidacao_custom.core.relatorio_pdf import exportar_pdf
    from pypdf import PdfReader
    import openpyxl
    calculo = entrada()
    calculo.parcelas[0].multa_percentual = D(2)
    calculo.descontos = calculo.descontos.model_validate({"perfil": "civil_4_temporario_v1",
        "criterio_inicio_juros": "data_fixa", "data_inicial_juros": "2024-07-01",
        "itens": [{"numero": 1, "data": "2024-06-01", "descricao": "Pagamento fictício", "valor": "100"}]})
    r = executar_calculo(calculo)
    assert r.descontos.premissas["perfil"] == "civil_4_temporario_v1"
    assert r.descontos.resumo.total_atualizado == D("103.02")
    assert r.parcelas[0].multa_detalhes is not None
    exportar_csv(r, str(tmp_path / "csv"))
    assert (tmp_path / "csv" / "resultado.json").exists()
    rows = list(csv.reader((tmp_path / "csv" / "indices_por_parcela.csv").open(encoding="utf-8-sig")))
    assert any("IPCA anterior" in row[1] for row in rows[1:])
    assert any("SELIC" in row[1] for row in rows[1:])
    excel = tmp_path / "ficticio.xlsx"
    exportar_excel(r, str(excel))
    wb = openpyxl.load_workbook(excel)
    assert "Índices por parcela" in wb.sheetnames
    assert "Critérios descontos" in wb.sheetnames
    texto = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(exportar_pdf(r))).pages)
    assert "Civil 4" not in texto
    assert "civil_4" not in texto
    assert "MEMÓRIA DOS ENCARGOS" in texto
    assert "CRÉDITO - ACRÉSCIMO" in texto
    assert "DÉBITO - DECRÉSCIMO" in texto


def test_api_catalogo_execucao_e_recuperacao_ficticia_isolada(indices):
    from fastapi.testclient import TestClient
    from liquidacao_custom.api.main import app
    client = TestClient(app)
    criterios = client.get("/api/v1/criterios?perfil=civil_4_temporario_v1")
    assert criterios.status_code == 200
    assert {p["id"] for p in criterios.json()["perfis"]} >= {"civil_4_temporario_v1", "ipca_taxa_legal_v1", "civil_2_v1", "civil_3_v1"}
    resposta = client.post("/api/v1/calculo", json=entrada("2024-08-01", "2024-07-01", "2024-10-01").model_dump(mode="json"))
    assert resposta.status_code == 200
    salvo = resposta.json()
    recuperado = client.get("/api/v1/calculos/" + salvo["chave_recuperacao"])
    assert recuperado.status_code == 200
    assert recuperado.json()["entrada"]["perfil"] == "civil_4_temporario_v1"


def test_comparacao_dividas_e_pdf_com_consolidacao_discreta(indices):
    from liquidacao_custom.core.honorarios_proveito import CalculoHonorariosProveito, executar_honorarios_proveito
    from liquidacao_custom.core.relatorio_honorarios_pdf import exportar_pdf_honorarios
    from pypdf import PdfReader
    def operacao(valor):
        return {"perfil": "civil_4_temporario_v1", "criterio_inicio_juros": "data_fixa", "data_inicial_juros": "2024-07-01",
            "parcelas": [{"numero": 1, "data_origem": "2024-08-01", "valor": valor}]}
    c = CalculoHonorariosProveito.model_validate({"dados_gerais": {"data_base": "2024-10-01"},
        "divida_original": operacao("1000"), "divida_correta": operacao("500"), "percentual_sentenca": "10"})
    r = executar_honorarios_proveito(c)
    assert "juros_selic_deduzida" in r.divida_original.componentes
    assert r.proveito_economico == r.divida_original.valor_atualizado - r.divida_correta.valor_atualizado
    texto = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(exportar_pdf_honorarios(r))).pages)
    assert "SELIC deduzida do IPCA" in texto
    assert "Base consolidada na transição" in texto
    assert "dedução aritmética experimental" not in texto
    assert "Civil 4" not in texto
