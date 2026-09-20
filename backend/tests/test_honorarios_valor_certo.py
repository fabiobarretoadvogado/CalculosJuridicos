import io
from datetime import date
from decimal import Decimal as D
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from pypdf import PdfReader

from liquidacao_custom.api.main import app
from liquidacao_custom.core.honorarios_isolados import CalculoHonorariosIsolados, executar_honorarios_isolados
from liquidacao_custom.core.honorarios_principais import corrigir_valor_causa, criterios_correcao_honorarios
from liquidacao_custom.core.juros import calcular_juros
from liquidacao_custom.core.models import ConfigJuros, TipoJuros
from liquidacao_custom.core.motor_ipca_taxa_legal import apurar_juros_taxa_legal
from liquidacao_custom.core.relatorio_honorarios_pdf import exportar_pdf_honorarios


def entrada(juros="simples", indice="ipcae"):
    c = {"data_fixacao": "2026-01-15", "indice": indice, "juros": juros,
         "data_inicio_juros": "2026-03-03" if juros != "sem_juros" else None,
         "percentual_mensal": "1" if juros == "simples" else None, "contagem_mes_cheio": False}
    return {"base": "valor_certo", "valor_certo": "1500.05", "dados_gerais": {"data_base": "2026-08-31", "observacoes": "EXEMPLO HIPOTÉTICO"}, "encargos_valor_certo": c}


@pytest.mark.parametrize("indice", ["ipcae", "ipca"])
@pytest.mark.parametrize("juros", ["simples", "taxa_legal", "sem_juros"])
def test_valor_certo_reutiliza_correcao_e_juros_neutros(indice, juros):
    d = entrada(juros, indice)
    r = executar_honorarios_isolados(CalculoHonorariosIsolados.model_validate(d))
    p = r.atualizacao_valor_certo
    saldo, fator, memoria, fonte, _ = corrigir_valor_causa(SimpleNamespace(indice=indice, valor_causa=D("1500.05"), data_protocolo=date(2026, 1, 15)), date(2026, 8, 31))
    assert p.valor_corrigido == r.apuracao.base_atualizada == saldo
    assert r.apuracao.fator_acumulado == fator and r.apuracao.fonte == fonte
    assert len(p.memoria_correcao) == len(memoria)
    assert all("Valor da causa" not in m.indice_aplicado for m in p.memoria_correcao)
    assert p.componentes[indice].data_inicial == date(2026, 1, 15)
    if juros == "simples":
        expected = calcular_juros(D("1500.05"), D("1500.05") * fator, [ConfigJuros(tipo=TipoJuros.PERCENTUAL_MENSAL_SIMPLES, percentual=D(1), data_inicial=date(2026, 3, 3), data_final=date(2026, 8, 31), contagem_mes_cheio=False)], date(2026, 8, 31))
        assert p.juros_mora == expected["valor_juros"]
    elif juros == "taxa_legal":
        expected, component, memoria_juros, _ = apurar_juros_taxa_legal(D("1500.05") * fator, date(2026, 3, 3), date(2026, 8, 31), indice_correcao="IPCA-E" if indice == "ipcae" else "IPCA")
        assert p.juros_mora == expected and p.componentes["juros"] == component
        assert p.memoria_juros == memoria_juros and p.componentes["juros"].data_final == date(2026, 8, 30)
        assert len(r.premissas["sha256_taxa_legal"]) == 64
        assert r.premissas["memoria_taxa_legal"]
    else:
        assert p.juros_mora == 0 and p.memoria_juros == []
    assert r.honorarios_sucumbenciais == r.apuracao.valor == p.total_parcela == saldo + p.juros_mora
    assert r.percentual_sentenca is r.escalonamento_fazenda is None
    assert r.total_geral == p.total_parcela
    assert "trânsito em julgado" in r.premissas["criterios"][0] or juros == "sem_juros"
    assert r.premissas["entrada"]["encargos_valor_certo"]["data_fixacao"] == "2026-01-15"


@pytest.mark.parametrize("juros", ["simples", "taxa_legal", "sem_juros"])
def test_fixacao_na_data_base_sem_periodo_decorrido(juros):
    d = entrada(juros)
    d["encargos_valor_certo"]["data_fixacao"] = "2026-08-31"
    if juros != "sem_juros":
        d["encargos_valor_certo"]["data_inicio_juros"] = "2026-08-31"
    r = executar_honorarios_isolados(CalculoHonorariosIsolados.model_validate(d))
    assert r.honorarios_sucumbenciais == D("1500.05")
    assert r.atualizacao_valor_certo.correcao_monetaria == r.atualizacao_valor_certo.juros_mora == 0
    assert r.atualizacao_valor_certo.componentes["juros"].data_inicial is None


@pytest.mark.parametrize("campo,valor", [("data_fixacao", "2026-09-01"), ("data_fixacao", "2009-06-30"), ("data_inicio_juros", None), ("data_inicio_juros", "2026-01-14"), ("data_inicio_juros", "2026-09-01"), ("percentual_mensal", None), ("percentual_mensal", "0"), ("percentual_mensal", "101"), ("indice", "selic")])
def test_nao_presumir_fixacao_transito_taxa_ou_indice(campo, valor):
    d = entrada()
    d["encargos_valor_certo"][campo] = valor
    with pytest.raises(ValidationError):
        CalculoHonorariosIsolados.model_validate(d)


def test_taxa_legal_nao_substitui_periodo_anterior_e_admite_fixacao_antiga():
    d = entrada("taxa_legal")
    d["encargos_valor_certo"]["data_fixacao"] = "2010-01-01"
    d["encargos_valor_certo"]["data_inicio_juros"] = "2024-08-29"
    with pytest.raises(ValidationError):
        CalculoHonorariosIsolados.model_validate(d)
    d["encargos_valor_certo"]["data_inicio_juros"] = "2024-08-30"
    r = executar_honorarios_isolados(CalculoHonorariosIsolados.model_validate(d))
    assert r.atualizacao_valor_certo.juros_mora > 0
    assert r.atualizacao_valor_certo.componentes["ipcae"].data_inicial == date(2010, 1, 1)


@pytest.mark.parametrize("juros", ["simples", "taxa_legal"])
def test_api_pdf_custas_separadas_e_memorias_unicas(juros):
    d = entrada(juros)
    sem = executar_honorarios_isolados(CalculoHonorariosIsolados.model_validate(d))
    d["custas_despesas"] = [{"numero": 1, "nome": "Custa demonstrativa", "data": "2026-01-15", "valor": "250"}]
    client = TestClient(app)
    body = client.post("/api/v1/honorarios/isolados", json=d)
    assert body.status_code == 200, body.text
    assert D(body.json()["honorarios_sucumbenciais"]) == sem.honorarios_sucumbenciais
    assert D(body.json()["total_geral"]) == sem.honorarios_sucumbenciais + D(body.json()["custas_despesas_valor_atualizado"])
    response = client.post("/api/v1/honorarios/isolados/exportar/pdf", json=d)
    assert response.status_code == 200, response.text
    reader = PdfReader(io.BytesIO(response.content))
    pages = [p.extract_text() for p in reader.pages]
    text = "\n".join(pages)
    assert "Dívida correta" not in text and "Valor da causa atualizado" not in text and "Proveito econômico" not in text
    assert "Encargos dos honorários fixados" in pages[0]
    assert "15/01/2026" in pages[0] and "03/03/2026" in pages[0]
    assert "Sem nova correção ou juros automáticos" not in text
    assert text.count("Taxa acumulada") == 1 and text.count("Juros acumulados") == 1
    custo = next(t for t in pages if "Custa demonstrativa" in t)
    assert "Encargos dos honorários" not in custo and "Memória" not in custo and "Identificação" not in custo
    assert all(page.mediabox.width > page.mediabox.height for page in reader.pages)


def test_cobertura_seguida_sem_futuro_e_novo_config_so_no_valor_certo():
    d = entrada()
    d["dados_gerais"]["data_base"] = "2030-01-01"
    with pytest.raises(ValueError):
        executar_honorarios_isolados(CalculoHonorariosIsolados.model_validate(d))
    d.update(base="valor_causa", valor_certo=None, valor_causa="1000", data_protocolo="2026-01-01", indice="ipcae", percentual_sentenca="10")
    with pytest.raises(ValidationError):
        CalculoHonorariosIsolados.model_validate(d)
    coverage = criterios_correcao_honorarios()
    assert coverage["taxa_legal"]["inicio"] == "2024-08-30"
