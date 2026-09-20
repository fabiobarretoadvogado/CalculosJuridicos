import io
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from pypdf import PdfReader

from liquidacao_custom.api.main import app
from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado
from liquidacao_custom.core.honorarios_isolados import CalculoHonorariosIsolados, executar_honorarios_isolados
from liquidacao_custom.core.motor_simplificado import executar_calculo
from liquidacao_custom.core.relatorio_honorarios_pdf import exportar_pdf_honorarios


def entrada(base="valor_causa", indice="ipcae"):
    d = {"dados_gerais": {"data_base": "2026-08-31", "processo": "EXEMPLO-HIPOTETICO"}, "base": base}
    if base == "valor_certo":
        d["valor_certo"] = "1500.05"
    else:
        d.update(valor_causa="10000.00", data_protocolo="2025-09-01", indice=indice, percentual_sentenca="20.0000")
    return d


@pytest.mark.parametrize("indice", ["ipcae", "ipca"])
def test_causa_reutiliza_exatamente_correcao_e_honorarios_da_tela_principal(indice):
    d = entrada(indice=indice)
    r = executar_honorarios_isolados(CalculoHonorariosIsolados.model_validate(d))
    principal = executar_calculo(CalculoSimplificado.model_validate({
        "perfil": "selic_cjf_v1", "dados_gerais": d["dados_gerais"],
        "parcelas": [{"numero": 1, "data_vencimento": "2026-08-01", "valor_bruto": "1"}],
        "honorarios_sucumbenciais": {"aplicar": True, "base": "valor_causa", "percentual": d["percentual_sentenca"], "valor_causa": d["valor_causa"], "data_protocolo": d["data_protocolo"], "indice": indice},
    }))
    assert r.apuracao == principal.honorarios_sucumbenciais
    assert r.honorarios_sucumbenciais == r.apuracao.valor
    assert r.total_geral == r.honorarios_sucumbenciais
    assert r.apuracao.memoria
    assert all(m.juros_periodo == 0 for m in r.apuracao.memoria)
    assert r.premissas["entrada"]["data_protocolo"] == "2025-09-01"
    assert r.premissas["fontes"]["correcao_valor_causa"] == r.apuracao.fonte
    if indice == "ipca":
        assert len(r.premissas["sha256_ipca_valor_causa"]) == 64


def test_equidade_nao_aplica_percentual_correcao_juros_ou_escalonamento():
    r = executar_honorarios_isolados(CalculoHonorariosIsolados.model_validate(entrada("valor_certo")))
    assert r.honorarios_sucumbenciais == r.total_geral == D("1500.05")
    assert r.percentual_sentenca is r.escalonamento_fazenda is None
    assert r.apuracao.memoria == [] and r.apuracao.correcao_monetaria == 0
    assert r.apuracao.indice is r.apuracao.data_protocolo is None
    assert "sem nova correção ou juros" in r.premissas["criterios"][0]
    assert "Não arbitra" in r.premissas["criterios"][0]
    assert "divida_original" not in r.model_dump()


@pytest.mark.parametrize("base", ["valor_causa", "valor_certo"])
def test_custas_corrigidas_separadamente_e_nunca_na_base(base):
    d = entrada(base)
    sem = executar_honorarios_isolados(CalculoHonorariosIsolados.model_validate(d))
    d["custas_despesas"] = [{"numero": 1, "nome": "Custa demonstrativa", "data": "2025-09-01", "valor": "250"}]
    r = executar_honorarios_isolados(CalculoHonorariosIsolados.model_validate(d))
    assert r.honorarios_sucumbenciais == sem.honorarios_sucumbenciais
    assert r.apuracao.base_atualizada == sem.apuracao.base_atualizada
    assert r.total_geral == r.honorarios_sucumbenciais + r.custas_despesas_valor_atualizado
    assert all(m.juros_periodo == 0 for m in r.custas_despesas[0].memoria)


def test_escalonamento_causa_usa_base_corrigida_e_preserva_referencia():
    d = entrada()
    d["valor_causa"] = "250000"
    d["percentual_sentenca"] = None
    d["escalonamento_fazenda"] = {"salario_minimo": "1000", "marco": "decisao_liquidacao", "data_decisao": "2026-09-09", "percentuais_faixas": ["10", "8", "5", "3", "1"]}
    r = executar_honorarios_isolados(CalculoHonorariosIsolados.model_validate(d))
    e = r.escalonamento_fazenda
    assert e.base_calculo == r.apuracao.base_atualizada > D("250000")
    assert e.faixas[0].valor_incidente == D("200000")
    assert e.faixas[1].valor_incidente == r.apuracao.base_atualizada - D("200000")
    assert e.valor_total == r.honorarios_sucumbenciais == sum(f.valor for f in e.faixas)
    assert str(e.data_decisao) == "2026-09-09"
    assert r.apuracao.percentual is None


@pytest.mark.parametrize("campo,valor", [
    ("valor_causa", None), ("valor_causa", "0"), ("valor_causa", "-1"),
    ("data_protocolo", None), ("data_protocolo", "2026-09-01"), ("data_protocolo", "2009-06-30"),
    ("indice", None), ("indice", "selic"), ("percentual_sentenca", None),
    ("percentual_sentenca", "0"), ("percentual_sentenca", "101"), ("percentual_sentenca", "10.12345"),
    ("valor_certo", "1500"),
])
def test_causa_rejeita_dados_incompletos_ou_incompativeis(campo, valor):
    d = entrada()
    d[campo] = valor
    with pytest.raises(ValidationError):
        CalculoHonorariosIsolados.model_validate(d)


@pytest.mark.parametrize("campo,valor", [
    ("valor_certo", None), ("valor_certo", "0"), ("valor_certo", "-1"), ("valor_certo", "1500.001"),
    ("percentual_sentenca", "10"), ("valor_causa", "1000"), ("data_protocolo", "2025-01-01"),
    ("indice", "ipcae"), ("escalonamento_fazenda", {"salario_minimo": "1000", "marco": "sentenca_liquida", "data_decisao": "2026-09-09", "percentuais_faixas": ["10", "8", "5", "3", "1"]}),
])
def test_equidade_rejeita_dados_incompativeis(campo, valor):
    d = entrada("valor_certo")
    d[campo] = valor
    with pytest.raises(ValidationError):
        CalculoHonorariosIsolados.model_validate(d)


def test_custas_datas_numeros_e_cobertura_oficial():
    for data in ["2009-06-30", "2026-09-01"]:
        d = entrada()
        d["custas_despesas"] = [{"numero": 1, "nome": "Custa", "data": data, "valor": "1"}]
        with pytest.raises(ValidationError):
            CalculoHonorariosIsolados.model_validate(d)
    d = entrada()
    d["custas_despesas"] = [{"numero": 1, "nome": "Custa", "data": "2026-08-01", "valor": "1"}] * 2
    with pytest.raises(ValidationError):
        CalculoHonorariosIsolados.model_validate(d)
    for indice in ["ipcae", "ipca"]:
        d = entrada(indice=indice)
        d["dados_gerais"]["data_base"] = "2030-01-01"
        with pytest.raises(ValueError):
            executar_honorarios_isolados(CalculoHonorariosIsolados.model_validate(d))
    # Sem índices, uma quantia já na data-base não depende de cobertura publicada.
    d = entrada("valor_certo")
    d["dados_gerais"]["data_base"] = "2030-01-01"
    assert executar_honorarios_isolados(CalculoHonorariosIsolados.model_validate(d)).total_geral == D("1500.05")


@pytest.mark.parametrize("base", ["valor_causa", "valor_certo"])
def test_api_e_pdf_sem_operacoes_de_divida_e_custas_exclusivas(base):
    d = entrada(base)
    d["custas_despesas"] = [{"numero": 1, "nome": "Custa demonstrativa", "data": "2025-09-01", "valor": "250"}]
    client = TestClient(app)
    resposta = client.post("/api/v1/honorarios/isolados", json=d)
    assert resposta.status_code == 200, resposta.text
    body = resposta.json()
    assert body["base"] == base and body["categoria"] == "honorarios_sucumbenciais_isolados"
    assert "divida_original" not in body and "proveito_economico" not in body
    resposta = client.post("/api/v1/honorarios/isolados/exportar/pdf", json=d)
    assert resposta.status_code == 200, resposta.text
    reader = PdfReader(io.BytesIO(resposta.content))
    paginas = [p.extract_text() for p in reader.pages]
    texto = "\n".join(paginas)
    assert "Dívida original" not in texto and "Dívida correta" not in texto
    assert "Proveito econômico" not in texto
    assert "EXEMPLO-HIPOTETICO" in paginas[0]
    assert all(p.mediabox.width > p.mediabox.height for p in reader.pages)
    custo = next(t for t in paginas if "Custa demonstrativa" in t)
    assert "Custas e despesas processuais" in custo
    assert "Identificação do processo" not in custo and "Memória da correção" not in custo
    if base == "valor_causa":
        assert "Valor da causa atualizado" in paginas[0] and "Fator acumulado" in paginas[0]
        assert sum(t.count("Período e critério") for t in paginas) == 1
        assert "Memória da correção do valor da causa" in texto
    else:
        assert "Equidade" in paginas[0] and "1.500,05" in paginas[0]
        assert "Percentual da sentença" not in texto and "Fator acumulado" not in texto
    d["valor_certo" if base == "valor_certo" else "valor_causa"] = "0"
    assert client.post("/api/v1/honorarios/isolados", json=d).status_code == 422


def test_memoria_extensa_pdf_um_cabecalho_por_tabela_e_textos_preservados():
    d = entrada()
    d["data_protocolo"] = "2010-01-01"
    d["dados_gerais"]["observacoes"] = "Observação extensa sem perda de conteúdo. " * 70 + "MARCADOR-FINAL"
    r = executar_honorarios_isolados(CalculoHonorariosIsolados.model_validate(d))
    texto = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(exportar_pdf_honorarios(r))).pages)
    assert "MARCADOR-FINAL" in texto
    assert texto.count("Período e critério") == 1
    assert r.apuracao.memoria[-1].competencia in texto
