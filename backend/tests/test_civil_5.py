"""Verificações financeiras e de integração isoladas do Civil 5."""
import csv
import io
import json
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest

from liquidacao_custom.core import motor_civil_5, motor_ipca_taxa_legal, honorarios_principais
from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado
from liquidacao_custom.core.motor_simplificado import criterios_publicos, executar_calculo, moeda
from liquidacao_custom.index_data.store import BUNDLED
from liquidacao_custom.index_data.taxa_legal_reconstruida import METODOLOGIA, fator_diario, reconstruir_mes, validar_reconstrucao

PERFIL = "civil_5_taxa_legal_reconstruida_v1"


def entrada(correcao="2024-07-01", juros="2024-06-01", fim="2024-10-01", valor="1000"):
    return CalculoSimplificado.model_validate({"perfil": PERFIL,
        "dados_gerais": {"data_base": fim, "criterio_inicio_juros": "data_fixa", "data_inicial_juros": juros},
        "parcelas": [{"numero": 1, "historico": "Exemplo fictício", "data_vencimento": correcao, "valor_bruto": valor}]})


@pytest.fixture
def indices(tmp_path, monkeypatch):
    ipca, legal, historica = [tmp_path / name for name in ("ipca_oficial.json", "taxa_legal_oficial.json", "taxa_legal_reconstruida.json")]
    ipca.write_text(json.dumps({"ipca": {"2024-06": "2", "2024-07": "-1", "2024-08": "3", "2024-09": "-2"},
        "obtido_em": "2024-10-01", "fontes": {"ipca": "https://example.invalid/ipca"}}), encoding="utf-8")
    legal.write_text(json.dumps({"taxa_legal": {"2024-08": "0.400000", "2024-09": "0.500000"},
        "obtido_em": "2024-10-01", "fonte_publica": "https://example.invalid/tl"}), encoding="utf-8")
    rates = {"2024-06": "0.300000", "2024-07": "0.000000", "2024-08": "0.400000"}
    historica.write_text(json.dumps({"taxa_legal": rates, "metodologia": METODOLOGIA, "obtido_em": "2024-10-01",
        "fontes": {"selic_diaria_anualizada": "https://example.invalid/1178", "ipca15_reconstrucao": "https://example.invalid/7478"},
        "sha256_fontes": {}, "urls_consultadas": {},
        "memoria_formacao": {k: {"taxa_mensal": v, "competencia_insumos": "2024-05", "fator_selic": "1.01000000", "fator_ipca15": "1.0000"} for k, v in rates.items()}}), encoding="utf-8")
    monkeypatch.setattr(motor_civil_5, "BASE_IPCA", ipca)
    monkeypatch.setattr(honorarios_principais, "BASE_IPCA", ipca)
    monkeypatch.setattr(motor_civil_5, "BASE_TAXA_LEGAL", legal)
    monkeypatch.setattr(motor_civil_5, "BASE_RECONSTRUIDA", historica)
    monkeypatch.setattr(motor_ipca_taxa_legal, "BASE_IPCA", ipca)
    monkeypatch.setattr(motor_ipca_taxa_legal, "BASE_TAXA_LEGAL", legal)
    return tmp_path


def concilia(resultado):
    for parcela in resultado.parcelas:
        assert parcela.valor_apurado + sum((c.valor for c in parcela.componentes.values()), D(0)) == parcela.total_parcela


def test_cinco_taxas_publicadas_e_fontes_reproduzidas_exatamente():
    historical = validar_reconstrucao(BUNDLED)
    assert {k: v["taxa_mensal"] for k, v in historical["verificacao_publicada"].items()} == {
        "2024-08": "0.605306", "2024-09": "0.676227", "2024-10": "0.704241", "2024-11": "0.385874", "2024-12": "0.171924"}
    assert historical["verificacao_publicada"]["2024-08"]["fator_selic"] == "1.00907122"
    assert min(historical["taxa_legal"]) == "2000-06"
    assert len(historical["taxa_legal"]) == 291
    assert max(historical["taxa_legal"]) == "2024-08"


def test_fatores_diarios_mensais_e_arredondamento_nbr():
    assert fator_diario("10.40") == D("1.00039270")
    row = reconstruir_mes(["10.40"] * 23, "0.30", "2024-07")
    assert row["fator_selic"] == "1.00907122"
    assert row["taxa_mensal"] == "0.605306"
    october = reconstruir_mes(["10.40"] * 13 + ["10.65"] * 8, "0.13", "2024-09")
    assert october["taxa_mensal"] == "0.704241"
    with pytest.raises(ValueError, match="SELIC anualizada inválida"):
        fator_diario("10.405")


def test_piso_zero_sem_perder_deflacao_ipca15():
    assert reconstruir_mes(["0.00"], "0.50", "2024-01")["taxa_mensal"] == "0.000000"
    assert reconstruir_mes(["0.00"], "0.50", "2024-01")["piso_zero_aplicado"] is True
    assert reconstruir_mes(["0.00"], "-0.50", "2024-01")["taxa_mensal"] == "0.502513"


@pytest.mark.parametrize("rates,inflation", [([], "0.3"), (["10.4"], None)])
def test_insumos_ausentes_nao_viram_taxa_zero(rates, inflation):
    with pytest.raises(ValueError, match="Fonte ausente"):
        reconstruir_mes(rates, inflation, "2024-07")


def test_juros_antes_correcao_com_base_corrigida_final(indices):
    r = executar_calculo(entrada())
    p = r.parcelas[0]
    corrected = D(1000) * D("0.99") * D("1.03") * D("0.98")
    assert p.valor_corrigido == moeda(corrected)
    assert p.componentes["taxa_legal"].base_calculo == corrected
    assert p.juros_mora == moeda(corrected * D("1.200000") / 100)
    assert p.componentes["taxa_legal"].data_inicial == date(2024, 6, 1)
    assert p.componentes["ipca"].data_inicial == date(2024, 7, 1)
    assert all(m.valor_base == corrected for m in p.memoria_juros)
    assert set(p.componentes) == {"ipca", "taxa_legal"}
    concilia(r)


def test_deflacao_preservada_e_taxa_historica_zero(indices):
    r = executar_calculo(entrada("2024-07-01", "2024-07-01", "2024-08-01"))
    p = r.parcelas[0]
    assert p.valor_corrigido == D("990.00")
    assert p.correcao_monetaria == D("-10.00")
    assert p.juros_mora == 0
    assert p.memoria_juros[0].indice_aplicado.startswith("Taxa Legal reconstruída")
    concilia(r)


def test_corte_29_30_mantem_taxa_sem_consolidar_saldo(indices):
    r = executar_calculo(entrada("2024-08-29", "2024-08-29", "2024-08-31"))
    rows = r.premissas["memoria_taxa_legal"]
    assert [(m["inicio"], m["fim"], m["origem"]) for m in rows] == [
        ("2024-08-29", "2024-08-29", "reconstruida"), ("2024-08-30", "2024-08-30", "oficial")]
    assert {m["taxa_mensal"] for m in rows} == {"0.400000"}
    assert len({m["base"] for m in rows}) == 1
    assert r.parcelas[0].componentes["taxa_legal"].taxa_acumulada_percentual == D("0.025806")
    concilia(r)


@pytest.mark.parametrize("modo", ["citacao", "por_parcela"])
def test_termos_globais_e_individuais_preservados(indices, modo):
    c = entrada()
    c.dados_gerais.criterio_inicio_juros = modo
    if modo == "por_parcela": c.parcelas[0].data_inicial_juros = date(2024, 6, 1)
    assert executar_calculo(c).parcelas[0].componentes["taxa_legal"].data_inicial == date(2024, 6, 1)


@pytest.mark.parametrize("dia", ["2024-08-29", "2024-08-30", "2024-09-01"])
def test_termos_iguais_data_base_sem_encargo(indices, dia):
    r = executar_calculo(entrada(dia, dia, dia))
    assert r.parcelas[0].total_parcela == D("1000.00")
    assert not r.memoria_mensal
    assert r.premissas["utilizou_taxa_legal_reconstruida"] is False


@pytest.mark.parametrize("juros", ["2024-08-30", "2024-08-31", "2024-09-01"])
def test_periodo_oficial_preserva_civil_1_exatamente(indices, juros):
    c = entrada("2024-07-16", juros)
    novo = executar_calculo(c)
    c.perfil = "ipca_taxa_legal_v1"
    antigo = executar_calculo(c)
    assert [p.model_dump() for p in novo.parcelas] == [p.model_dump() for p in antigo.parcelas]
    assert novo.resumo.model_dump() == antigo.resumo.model_dump()
    assert novo.premissas["utilizou_taxa_legal_reconstruida"] is False
    assert motor_civil_5.NOTA_RECONSTRUCAO not in novo.premissas["metodologia"]


@pytest.mark.parametrize("file,key,month", [("taxa_legal_reconstruida.json", "taxa_legal", "2024-06"), ("taxa_legal_oficial.json", "taxa_legal", "2024-08"), ("ipca_oficial.json", "ipca", "2024-07")])
def test_taxas_ausentes_impedem_calculo_sem_substituta(indices, file, key, month):
    path = indices / file
    data = json.loads(path.read_text())
    del data[key][month]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError): executar_calculo(entrada())


def test_base_historica_ausente_impede_calculo(indices):
    (indices / "taxa_legal_reconstruida.json").unlink()
    with pytest.raises(ValueError, match="Base histórica.*ausente"):
        executar_calculo(entrada())


def test_limites_independentes_e_anteriores_cobertura(indices):
    c = criterios_publicos(perfil=PERFIL)
    assert c["inicio_juros"] == c["inicio_correcao"] == "2024-06-01"
    assert c["data_base_maxima"] == "2024-10-01"
    with pytest.raises(ValueError, match="anterior à cobertura histórica"):
        executar_calculo(entrada(juros="2024-05-31"))
    with pytest.raises(ValueError, match="data-base máxima"):
        executar_calculo(entrada(fim="2024-10-02"))


def test_descontos_multas_pdf_excel_csv_com_proveniencia(indices, tmp_path):
    from liquidacao_custom.core.exportadores import exportar_csv, exportar_excel
    from liquidacao_custom.core.relatorio_pdf import exportar_pdf
    from pypdf import PdfReader
    import openpyxl
    c = entrada()
    c.parcelas[0].multa_percentual = D(2)
    c.descontos = c.descontos.model_validate({"perfil": PERFIL, "criterio_inicio_juros": "data_fixa", "data_inicial_juros": "2024-06-01",
        "itens": [{"numero": 1, "data": "2024-07-01", "descricao": "Pagamento fictício", "valor": "100"}]})
    r = executar_calculo(c)
    assert r.descontos.premissas["perfil"] == PERFIL
    assert r.parcelas[0].multa_detalhes is not None
    exportar_csv(r, str(tmp_path / "csv"))
    rows = list(csv.reader((tmp_path / "csv/taxa_legal_mensal.csv").open(encoding="utf-8-sig")))
    assert len({len(row) for row in rows}) == 1
    assert "Origem da taxa" in rows[0]
    assert {row[10] for row in rows[1:]} == {"Reconstruída", "Publicada BCB SGS 29543"}
    assert json.loads((tmp_path / "csv/resultado.json").read_text())["descontos"]["premissas"]["utilizou_taxa_legal_reconstruida"] is True
    target = tmp_path / "ficticio.xlsx"
    exportar_excel(r, str(target))
    wb = openpyxl.load_workbook(target)
    assert "Taxa Legal" in wb.sheetnames and "Índices por parcela" in wb.sheetnames
    assert "Origem da taxa" in list(next(wb["Taxa Legal"].values))
    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(exportar_pdf(r))).pages)
    assert "Civil 5" not in text and "civil_5" not in text
    assert text.count(motor_civil_5.NOTA_RECONSTRUCAO) == 1
    assert "NBR 5891" not in text
    assert "SGS 1178" in text and "SGS 7478" in text


def test_api_criterios_execucao_recuperacao_e_exportacao_isolados(indices):
    from fastapi.testclient import TestClient
    from liquidacao_custom.api.main import app
    with TestClient(app) as api:
        assert api.get("/api/v1/criterios", params={"perfil": PERFIL}).status_code == 200
        result = api.post("/api/v1/calculo", json=entrada().model_dump(mode="json"))
        assert result.status_code == 200, result.text
        saved = api.get("/api/v1/calculos/" + result.json()["chave_recuperacao"])
        assert saved.status_code == 200
        assert saved.json()["entrada"]["perfil"] == PERFIL
        pdf = api.post("/api/v1/calculo/exportar/pdf", json=entrada().model_dump(mode="json"))
        assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


def test_comparacao_civil5_preserva_memoria_e_nota_pdf(indices):
    from liquidacao_custom.core.honorarios_proveito import CalculoHonorariosProveito, executar_honorarios_proveito
    from liquidacao_custom.core.relatorio_honorarios_pdf import exportar_pdf_honorarios
    from pypdf import PdfReader
    def operation(valor):
        return {"perfil": PERFIL, "criterio_inicio_juros": "data_fixa", "data_inicial_juros": "2024-06-01",
                "parcelas": [{"numero": 1, "data_origem": "2024-07-01", "valor": valor}]}
    c = CalculoHonorariosProveito.model_validate({"dados_gerais": {"data_base": "2024-10-01"},
        "divida_original": operation("1000"), "divida_correta": operation("500"), "percentual_sentenca": "10"})
    r = executar_honorarios_proveito(c)
    assert r.proveito_economico == r.divida_original.valor_atualizado - r.divida_correta.valor_atualizado
    assert r.divida_original.premissas["utilizou_taxa_legal_reconstruida"] is True
    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(exportar_pdf_honorarios(r))).pages)
    assert "Civil 5" not in text
    assert text.count(motor_civil_5.NOTA_RECONSTRUCAO) == 1
