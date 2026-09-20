"""Escalonamento opcional na categoria autônoma; valores de salário hipotéticos."""
import io
from decimal import Decimal as D, ROUND_HALF_EVEN, getcontext

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from pypdf import PdfReader

from liquidacao_custom.api.main import app
from liquidacao_custom.core.honorarios_proveito import CalculoHonorariosProveito, executar_honorarios_proveito
from liquidacao_custom.core.relatorio_honorarios_pdf import exportar_pdf_honorarios


def entrada(base="150000000.00", salario="1000.00", percentuais=None):
    return {
        "dados_gerais": {"data_base": "2026-08-01", "observacoes": "Exemplo hipotético; salário mínimo meramente demonstrativo."},
        "divida_original": {"perfil": "selic_cjf_v1", "parcelas": [{"numero": 1, "historico": "Valor exigido demonstrativo", "data_origem": "2026-08-01", "valor": str(D(base) + D("1000"))}]},
        "divida_correta": {"perfil": "selic_cjf_v1", "parcelas": [{"numero": 1, "historico": "Valor correto demonstrativo", "data_origem": "2026-08-01", "valor": "1000.00"}]},
        "escalonamento_fazenda": {"salario_minimo": salario, "marco": "sentenca_liquida", "data_decisao": "2026-09-09", "percentuais_faixas": percentuais or ["10", "8", "5", "3", "1"]},
    }


@pytest.mark.parametrize("base,esperado,bases", [
    ("0", "0", ["0", "0", "0", "0", "0"]),
    ("10.05", "1.01", ["10.05", "0", "0", "0", "0"]),
    ("199999.99", "20000", ["199999.99", "0", "0", "0", "0"]),
    ("200000", "20000", ["200000", "0", "0", "0", "0"]),
    ("200001", "20000.08", ["200000", "1", "0", "0", "0"]),
    ("2000000", "164000", ["200000", "1800000", "0", "0", "0"]),
    ("2000001", "164000.05", ["200000", "1800000", "1", "0", "0"]),
    ("20000000", "1064000", ["200000", "1800000", "18000000", "0", "0"]),
    ("20000001", "1064000.03", ["200000", "1800000", "18000000", "1", "0"]),
    ("100000000", "3464000", ["200000", "1800000", "18000000", "80000000", "0"]),
    ("100000001", "3464000.01", ["200000", "1800000", "18000000", "80000000", "1"]),
    ("150000000", "3964000", ["200000", "1800000", "18000000", "80000000", "50000000"]),
])
def test_progressao_excedentes_limites_e_arredondamento(base, esperado, bases):
    r = executar_honorarios_proveito(CalculoHonorariosProveito.model_validate(entrada(base)))
    assert r.honorarios_sucumbenciais == D(esperado)
    assert r.percentual_sentenca is None
    assert r.proveito_economico == D(base)
    e = r.escalonamento_fazenda
    assert e.base_calculo == D(base)
    assert [f.valor_incidente for f in e.faixas] == list(map(D, bases))
    assert sum(f.valor_incidente for f in e.faixas) == D(base)
    assert sum(f.valor for f in e.faixas) == e.valor_total == r.honorarios_sucumbenciais
    assert [f.limite_inferior_salarios_minimos for f in e.faixas] == list(map(D, ["0", "200", "2000", "20000", "100000"]))
    assert "custas e despesas não integram" in r.formula


def test_percentuais_maximos_e_intermediarios():
    maximo = executar_honorarios_proveito(CalculoHonorariosProveito.model_validate(entrada(percentuais=["20", "10", "8", "5", "3"])))
    assert maximo.honorarios_sucumbenciais == D("7160000.00")
    intermediario = executar_honorarios_proveito(CalculoHonorariosProveito.model_validate(entrada("10", percentuais=["15.1234", "9", "6", "4", "2"])))
    assert intermediario.honorarios_sucumbenciais == D("1.51")
    assert intermediario.escalonamento_fazenda.faixas[0].percentual_aplicado == D("15.1234")


@pytest.mark.parametrize("indice,invalido", [(0, "9.99"), (0, "20.0001"), (1, "7.99"), (1, "10.0001"), (2, "4.99"), (2, "8.0001"), (3, "2.99"), (3, "5.0001"), (4, "0.99"), (4, "3.0001"), (4, "NaN"), (0, "10.12345")])
def test_percentual_invalido_bloqueia_mesmo_faixa_nao_alcancada(indice, invalido):
    dados = entrada("10")
    dados["escalonamento_fazenda"]["percentuais_faixas"][indice] = invalido
    with pytest.raises(ValidationError):
        CalculoHonorariosProveito.model_validate(dados)


@pytest.mark.parametrize("campo,valor", [("salario_minimo", "0"), ("salario_minimo", "-1"), ("salario_minimo", "1000.001"), ("salario_minimo", None), ("data_decisao", None), ("data_decisao", "inválida"), ("marco", "data_base"), ("percentuais_faixas", ["10"] * 4), ("percentuais_faixas", ["10"] * 6)])
def test_referencia_e_cinco_percentuais_obrigatorios(campo, valor):
    dados = entrada()
    dados["escalonamento_fazenda"][campo] = valor
    with pytest.raises(ValidationError):
        CalculoHonorariosProveito.model_validate(dados)


def test_nao_busca_salario_da_data_base_e_nao_altera_arredondamento_global(monkeypatch):
    from liquidacao_custom.core import acessorios
    def proibido(*args):
        raise AssertionError("Não usar fallback de salário mínimo por ano.")
    monkeypatch.setattr(acessorios, "_salario_minimo_para_ano", proibido)
    anterior = getcontext().rounding
    getcontext().rounding = ROUND_HALF_EVEN
    try:
        dados = entrada("10.05", "2000")
        dados["escalonamento_fazenda"]["marco"] = "decisao_liquidacao"
        r = executar_honorarios_proveito(CalculoHonorariosProveito.model_validate(dados))
        assert r.honorarios_sucumbenciais == D("1.01")
        assert r.escalonamento_fazenda.salario_minimo == D("2000")
        assert str(r.escalonamento_fazenda.data_decisao) == "2026-09-09"
        assert getcontext().rounding == ROUND_HALF_EVEN
    finally:
        getcontext().rounding = anterior


def test_custas_separadas_e_sem_proveito_negativo():
    dados = entrada("200001")
    dados["custas_despesas"] = [{"numero": 1, "nome": "Custa demonstrativa", "data": "2026-08-01", "valor": "250.00"}]
    r = executar_honorarios_proveito(CalculoHonorariosProveito.model_validate(dados))
    assert r.escalonamento_fazenda.base_calculo == D("200001")
    assert r.honorarios_sucumbenciais == D("20000.08")
    assert r.total_geral == r.honorarios_sucumbenciais + r.custas_despesas_valor_atualizado
    dados["divida_original"]["parcelas"][0]["valor"] = "500"
    r = executar_honorarios_proveito(CalculoHonorariosProveito.model_validate(dados))
    assert r.diferenca_atualizada == D("-500")
    assert r.honorarios_sucumbenciais == r.proveito_economico == 0
    assert r.total_geral == r.custas_despesas_valor_atualizado
    assert r.alertas


def test_modos_exclusivos_e_legado_preservado():
    dados = entrada("200001")
    dados["percentual_sentenca"] = "20"
    with pytest.raises(ValidationError, match="sem cumular"):
        CalculoHonorariosProveito.model_validate(dados)
    del dados["escalonamento_fazenda"]
    r = executar_honorarios_proveito(CalculoHonorariosProveito.model_validate(dados))
    assert r.honorarios_sucumbenciais == D("40000.20")
    assert r.escalonamento_fazenda is None
    del dados["percentual_sentenca"]
    with pytest.raises(ValidationError, match="Informe o percentual"):
        CalculoHonorariosProveito.model_validate(dados)


def test_pdf_discrimina_faixas_sem_percentual_unico_e_custas_em_pagina_exclusiva():
    dados = entrada()
    dados["custas_despesas"] = [{"numero": 1, "nome": "Custa demonstrativa", "data": "2026-08-01", "valor": "250.00"}]
    r = executar_honorarios_proveito(CalculoHonorariosProveito.model_validate(dados))
    paginas = [p.extract_text() for p in PdfReader(io.BytesIO(exportar_pdf_honorarios(r))).pages]
    primeira = paginas[0]
    assert "Por faixas" in primeira
    assert "Percentual da sentença" not in primeira
    faixas = next(t for t in paginas if "Honorários por faixa" in t)
    assert "Acima de 100.000 SM" in faixas
    assert "R$ 3.964.000,00" in primeira
    assert "09/09/2026" in faixas
    assert "Salário mínimo vigente informado: R$ 1.000,00" in faixas
    assert sum(t.count("Base na faixa") for t in paginas) == 1
    custas = next(t for t in paginas if "Custa demonstrativa" in t)
    assert "Custas e despesas processuais" in custas
    assert "Dívida original" not in custas and "Dívida correta" not in custas


def test_api_json_pdf_validacao_e_limites_nao_editaveis():
    client = TestClient(app)
    dados = entrada()
    r = client.post("/api/v1/honorarios/proveito-economico", json=dados)
    assert r.status_code == 200, r.text
    body = r.json()
    assert D(body["honorarios_sucumbenciais"]) == D("3964000")
    assert len(body["escalonamento_fazenda"]["faixas"]) == 5
    assert body["percentual_sentenca"] is None
    assert body["escalonamento_fazenda"]["data_decisao"] == "2026-09-09"
    pdf = client.post("/api/v1/honorarios/proveito-economico/exportar/pdf", json=dados)
    assert pdf.status_code == 200, pdf.text
    assert pdf.content.startswith(b"%PDF")
    dados["escalonamento_fazenda"]["percentuais_faixas"][4] = "4"
    assert client.post("/api/v1/honorarios/proveito-economico", json=dados).status_code == 422
    dados = entrada()
    dados["escalonamento_fazenda"]["limites_faixas"] = ["100"]
    assert client.post("/api/v1/honorarios/proveito-economico", json=dados).status_code == 422
