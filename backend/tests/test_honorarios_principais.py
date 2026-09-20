import copy
import csv
import io
import json
import zipfile
from decimal import Decimal as D

import openpyxl
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from pypdf import PdfReader

from liquidacao_custom.api.main import app
from liquidacao_custom.core import motor_simplificado as motor
from liquidacao_custom.core import honorarios_principais as hp
from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado


def entrada(perfil="selic_cjf_v1"):
    return {"perfil": perfil, "dados_gerais": {"data_base": "2026-08-31", "criterio_inicio_juros": "vencimento"},
            "parcelas": [{"numero": 1, "historico": "Exemplo", "data_vencimento": "2026-08-01", "valor_bruto": "1000", "valor_pago_na_data": "200", "multa_percentual": "2"}],
            "descontos": {"perfil": "selic_cjf_v1", "itens": [{"numero": 1, "data": "2026-08-01", "valor": "100"}]},
            "custas_despesas": [{"numero": 1, "nome": "Taxa", "data": "2026-08-01", "valor": "300"}],
            "honorarios_sucumbenciais": {"aplicar": True, "base": "proveito_economico", "percentual": "20"}}


def calcular(payload):
    return motor.executar_calculo(CalculoSimplificado.model_validate(payload))


@pytest.mark.parametrize("perfil", ["selic_cjf_v1", "selic_ipcae_poupanca_v1", "selic_ipcae_2aa_v1", "ipcae_1am_simples_v1"])
def test_proveito_apos_multa_e_descontos_sem_custas(perfil):
    payload = entrada(perfil)
    r = calcular(payload)
    base = sum(p.total_parcela for p in r.parcelas) - r.resumo.abatimentos
    assert r.honorarios_sucumbenciais.base_atualizada == base
    assert r.honorarios_sucumbenciais.valor == motor.moeda(base * D("0.2"))
    assert r.resumo.total_atualizado == base + r.resumo.honorarios + r.resumo.custas
    payload["custas_despesas"][0]["valor"] = "900"
    assert calcular(payload).honorarios_sucumbenciais == r.honorarios_sucumbenciais
    assert r.descontos.honorarios_sucumbenciais is None
    assert r.parcelas[0].multa_detalhes.base_calculo == 800


@pytest.mark.parametrize("multa,honorarios", [(False, False), (True, False), (False, True), (True, True)])
@pytest.mark.parametrize("incluir_sucumbenciais", [False, True])
@pytest.mark.parametrize("perfil", ["selic_cjf_v1", "selic_ipcae_poupanca_v1", "selic_ipcae_2aa_v1", "ipcae_1am_simples_v1", "ipca_taxa_legal_v1"])
def test_cpc_523_mesma_base_e_opcoes_independentes(multa, honorarios, incluir_sucumbenciais, perfil):
    payload = entrada(perfil)
    payload["cumprimento_sentenca"] = {"aplicar_multa": multa, "aplicar_honorarios": honorarios, "incluir_sucumbenciais_base": incluir_sucumbenciais}
    r = calcular(payload)
    credito = sum(p.total_parcela for p in r.parcelas) - r.resumo.abatimentos
    h = motor.moeda(credito * D("0.2"))
    base = credito
    acrescimo = motor.moeda(base * D("0.1"))
    assert r.honorarios_sucumbenciais.valor == h
    if multa or honorarios:
        assert r.cumprimento_sentenca.base_calculo == base
        assert r.cumprimento_sentenca.sucumbenciais_na_base == 0
        assert r.cumprimento_sentenca.multa == (acrescimo if multa else 0)
        assert r.cumprimento_sentenca.honorarios == (acrescimo if honorarios else 0)
        assert r.resumo.multas == r.parcelas[0].multa_detalhes.total_atualizado + (acrescimo if multa else 0)
    else:
        assert r.cumprimento_sentenca is None
    assert r.resumo.total_atualizado == credito + h + r.resumo.custas + acrescimo * (int(multa) + int(honorarios))
    assert r.premissas["entrada"]["cumprimento_sentenca"]["incluir_sucumbenciais_base"] is False


@pytest.mark.parametrize("config", [
    {"aplicar": True, "base": "proveito_economico", "percentual": "20"},
    {"aplicar": True, "base": "valor_causa", "valor_causa": "10000", "data_protocolo": "2025-09-15", "indice": "ipcae", "percentual": "20"},
    {"aplicar": True, "base": "valor_certo", "valor_certo": "2000"},
])
def test_honorarios_da_sentenca_nunca_compõem_base_523(config):
    payload = entrada()
    payload["honorarios_sucumbenciais"] = config
    payload["cumprimento_sentenca"] = {"aplicar_multa": True, "aplicar_honorarios": True, "incluir_sucumbenciais_base": True}
    r = calcular(payload)
    assert r.cumprimento_sentenca.base_calculo == D("716")
    assert r.cumprimento_sentenca.sucumbenciais_na_base == 0
    assert r.cumprimento_sentenca.multa == r.cumprimento_sentenca.honorarios == D("71.60")
    assert r.resumo.total_atualizado == D("716") + r.honorarios_sucumbenciais.valor + D("143.20") + r.resumo.custas
    payload["honorarios_sucumbenciais"] = {"aplicar": False}
    assert calcular(payload).cumprimento_sentenca == r.cumprimento_sentenca
    payload["custas_despesas"][0]["valor"] = "9000"
    assert calcular(payload).cumprimento_sentenca == r.cumprimento_sentenca


@pytest.mark.parametrize("base", ["credito_parte", "total_sem_custas"])
def test_destaque_contratual_nao_acresce_nem_abate_divida(base):
    payload = entrada()
    payload["cumprimento_sentenca"] = {"aplicar_multa": True, "aplicar_honorarios": True}
    anterior = calcular(payload)
    payload["cumprimento_sentenca"].update(destacar_contratuais=True, percentual_contratuais="30", base_contratuais=base)
    r = calcular(payload)
    assert r.resumo == anterior.resumo
    destaque = r.destaque_contratuais
    assert destaque.base_calculo == (anterior.resumo.total_atualizado - anterior.resumo.custas if base == "total_sem_custas" else D("716") + anterior.cumprimento_sentenca.multa)
    assert destaque.valor == motor.moeda(destaque.base_calculo * D("0.3"))
    assert destaque.saldo_apos_destaque + destaque.valor == destaque.base_calculo
    assert destaque.acresce_total is False
    payload["custas_despesas"][0]["valor"] = "900"
    assert calcular(payload).destaque_contratuais == destaque


def test_valor_certo_ja_na_data_base_sem_percentual():
    payload = entrada()
    payload["honorarios_sucumbenciais"] = {"aplicar": True, "base": "valor_certo", "valor_certo": "200.01"}
    r = calcular(payload)
    assert r.resumo.honorarios == D("200.01")
    assert r.honorarios_sucumbenciais.percentual is None
    assert not r.honorarios_sucumbenciais.memoria


@pytest.mark.parametrize("indice", ["ipcae", "ipca"])
def test_valor_causa_exclusivamente_corrigido(indice):
    payload = entrada()
    payload["honorarios_sucumbenciais"] = {"aplicar": True, "base": "valor_causa", "valor_causa": "10000", "data_protocolo": "2025-09-15", "indice": indice, "percentual": "10"}
    r = calcular(payload)
    h = r.honorarios_sucumbenciais
    assert h.valor == motor.moeda(h.base_atualizada * D("0.1"))
    assert h.base_atualizada == h.valor_original + h.correcao_monetaria
    assert h.fonte.startswith("https://") and h.memoria
    assert all(m.juros_periodo == 0 and m.juros_acumulados == 0 for m in h.memoria)
    assert r.resumo.principal_apurado == 800  # Valor da causa não soma ao principal.


def test_ipca_deflacao_proporcao_e_indice_ausente(tmp_path, monkeypatch):
    arquivo = tmp_path / "ipca.json"
    dados = {"ipca": {"2026-07": "1", "2026-08": "-2"}, "fontes": {"ipca": "https://example.test/ipca"}}
    arquivo.write_text(json.dumps(dados), encoding="utf-8")
    monkeypatch.setattr(hp, "BASE_IPCA", arquivo)
    payload = entrada()
    payload["honorarios_sucumbenciais"] = {"aplicar": True, "base": "valor_causa", "valor_causa": "10000", "data_protocolo": "2026-07-16", "indice": "ipca", "percentual": "10"}
    h = calcular(payload).honorarios_sucumbenciais
    assert h.fator_acumulado == D("1.01") ** (D(16) / 31) * D("0.98")
    assert h.correcao_monetaria < 0
    del dados["ipca"]["2026-07"]
    arquivo.write_text(json.dumps(dados), encoding="utf-8")
    with pytest.raises(ValueError, match="Índice ausente"):
        calcular(payload)


@pytest.mark.parametrize("campo,config", [
    ("honorarios_sucumbenciais", {"aplicar": True, "base": "proveito_economico"}),
    ("honorarios_sucumbenciais", {"aplicar": True, "base": "valor_causa", "percentual": "10"}),
    ("honorarios_sucumbenciais", {"aplicar": True, "base": "valor_certo", "valor_certo": "-1"}),
    ("honorarios_sucumbenciais", {"aplicar": True, "base": "proveito_economico", "percentual": "NaN"}),
    ("cumprimento_sentenca", {"destacar_contratuais": True}),
    ("cumprimento_sentenca", {"destacar_contratuais": True, "percentual_contratuais": "100.0001"}),
])
def test_entradas_invalidas_rejeitadas(campo, config):
    payload = entrada()
    payload[campo] = config
    with pytest.raises(ValidationError):
        CalculoSimplificado.model_validate(payload)


def test_defaults_preservam_resultado_e_sem_recursao():
    payload = entrada()
    del payload["honorarios_sucumbenciais"]
    anterior = calcular(payload)
    payload.update(honorarios_sucumbenciais={"aplicar": False}, cumprimento_sentenca={})
    assert calcular(payload).model_dump() == anterior.model_dump()


def test_descontos_excedentes_zeram_proveito_sem_abater_custas():
    payload = entrada()
    payload["descontos"]["itens"][0]["valor"] = "2000"
    r = calcular(payload)
    assert r.honorarios_sucumbenciais.base_atualizada == 0
    assert r.honorarios_sucumbenciais.valor == 0
    assert r.resumo.total_atualizado == r.resumo.custas


def test_api_pdf_excel_csv_conciliam_e_separam_destaque():
    client = TestClient(app)
    payload = entrada()
    payload["cumprimento_sentenca"] = {"aplicar_multa": True, "aplicar_honorarios": True, "incluir_sucumbenciais_base": True, "destacar_contratuais": True, "percentual_contratuais": "30"}
    r = client.post("/api/v1/calculo", json=payload)
    assert r.status_code == 200
    valor = D(r.json()["resumo"]["total_atualizado"])
    assert r.json()["cumprimento_sentenca"]["base_calculo"] == "716.00"
    assert D(r.json()["cumprimento_sentenca"]["sucumbenciais_na_base"]) == 0
    assert r.json()["premissas"]["entrada"]["cumprimento_sentenca"]["incluir_sucumbenciais_base"] is False
    pdf = client.post("/api/v1/calculo/exportar/pdf", json=payload)
    assert pdf.status_code == 200
    paginas = [p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages]
    texto = " ".join(paginas)
    assert "Honorários sucumbenciais" in texto and "Destaque de honorários contratuais" in texto
    assert "não acresce ao cálculo" in texto
    assert "Honorários da sentença, custas e despesas excluídos" in texto
    assert "honorários da sentença incluídos na base" not in texto
    custos = next(p for p in paginas if "Fator IPCA-E" in p)
    assert "Destaque de honorários contratuais" not in custos and "Valores por parcela" not in custos
    excel = client.post("/api/v1/calculo/exportar/excel", json=payload)
    assert excel.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(excel.content))
    assert D(str(list(wb["Resumo"].values)[-1][1])) == valor
    linhas = list(wb["Honorários e cumprimento"].values)
    rubricas_523 = [linha for linha in linhas if str(linha[0]).startswith(("Multa - art. 523", "Honorários - art. 523"))]
    assert len(rubricas_523) == 2
    assert all(D(str(linha[5])) == D("716") and D(str(linha[7])) == D("71.60") for linha in rubricas_523)
    assert linhas[-2][-1] == "NÃO" and linhas[-1][-1] == "NÃO"
    wb.close()
    response = client.post("/api/v1/calculo/exportar/csv", json=payload)
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        linhas = list(csv.reader(io.StringIO(z.read("honorarios_cumprimento.csv").decode("utf-8-sig"))))
        rubricas_523 = [linha for linha in linhas if linha[0].startswith(("Multa - art. 523", "Honorários - art. 523"))]
        assert len(rubricas_523) == 2
        assert all(D(linha[5]) == D("716") and D(linha[7]) == D("71.60") for linha in rubricas_523)
        assert linhas[-2][-1] == "NÃO" and linhas[-1][-1] == "NÃO"


def test_cobertura_correcao_oficial():
    r = TestClient(app).get("/api/v1/honorarios/criterios-correcao")
    assert r.status_code == 200 and r.json()["ipca"]["data_base_maxima"] == "2026-08-31"
