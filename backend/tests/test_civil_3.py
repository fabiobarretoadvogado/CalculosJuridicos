from datetime import date
from decimal import Decimal as D

import pytest

from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado
from liquidacao_custom.core.motor_simplificado import criterios_publicos, executar_calculo
from liquidacao_custom.core import motor_civil_2


def entrada(inicio="2025-02-01", fim="2025-03-01", juros="2025-01-01"):
    return CalculoSimplificado.model_validate({
        "perfil": "civil_3_v1",
        "dados_gerais": {"data_base": fim, "criterio_inicio_juros": "data_fixa",
                         "data_inicial_juros": juros},
        "parcelas": [{"numero": 1, "historico": "Parcela", "data_vencimento": inicio,
                      "valor_bruto": "1000.00", "valor_pago_na_data": "0"}],
    })


@pytest.fixture
def inpc(tmp_path, monkeypatch):
    import json
    arquivo = tmp_path / "inpc_oficial.json"
    arquivo.write_text(json.dumps({"inpc": {"2025-02": "2.00", "2025-03": "-1.00"},
                                   "obtido_em": "2025-04-01", "fontes": {"inpc": motor_civil_2.FONTE_INPC}}), encoding="utf-8")
    monkeypatch.setattr(motor_civil_2, "BASE_INPC", arquivo)
    return arquivo


def test_inpc_com_juros_anteriores_a_correcao_e_hash_da_serie(inpc):
    import hashlib
    resultado = executar_calculo(entrada())
    parcela = resultado.parcelas[0]
    assert parcela.valor_corrigido == D("1020.00")
    assert parcela.juros_mora == D("20.40")
    assert parcela.total_parcela == D("1040.40")
    assert set(parcela.componentes) == {"inpc", "juros_1am"}
    assert parcela.componentes["juros_1am"].data_inicial == date(2025, 1, 1)
    assert parcela.componentes["inpc"].data_final == date(2025, 2, 28)
    assert resultado.premissas["sha256_inpc"] == hashlib.sha256(inpc.read_bytes()).hexdigest()
    assert all(m.indice_aplicado == "INPC (SGS 188)" for m in parcela.memoria_correcao)
    assert "sha256_ipca" not in resultado.premissas


def test_inpc_preserva_deflacao_e_exclui_data_base(inpc):
    resultado = executar_calculo(entrada("2025-03-01", "2025-04-01", "2025-03-01"))
    assert resultado.parcelas[0].valor_corrigido == D("990.00")
    assert resultado.parcelas[0].juros_mora == D("9.90")
    assert criterios_publicos(perfil="civil_3_v1")["data_base_maxima"] == "2025-04-01"
    with pytest.raises(ValueError, match="INPC publicado"):
        executar_calculo(entrada("2025-03-01", "2025-04-02", "2025-03-01"))


def test_inpc_ausente_nao_vira_correcao_zero(inpc):
    with pytest.raises(ValueError):
        executar_calculo(entrada("2025-01-01", "2025-03-01", "2025-01-01"))


def test_inpc_parcial_preserva_mesma_proporcionalidade_do_civil_2(inpc):
    from liquidacao_custom.core.motor_simplificado import moeda
    resultado = executar_calculo(entrada("2025-02-15", "2025-03-01", "2025-02-15"))
    parcela = resultado.parcelas[0]
    fator = D("1.02") ** (D(14) / D(28))
    assert parcela.componentes["inpc"].fator_acumulado == fator
    assert parcela.valor_corrigido == moeda(D(1000) * fator)
    assert parcela.juros_mora == moeda(D(1000) * fator * D("0.005"))


def test_desconto_herda_inpc_e_exportacao_identifica_indice(inpc):
    from liquidacao_custom.core.componentes import colunas_componentes
    from liquidacao_custom.core.criterios_simplificados import OperacaoDescontos
    calculo = entrada()
    calculo.descontos = OperacaoDescontos.model_validate({
        "itens": [{"numero": 1, "descricao": "Pagamento", "data": "2025-02-01", "valor": "100.00"}],
    })
    resultado = executar_calculo(calculo)
    assert resultado.descontos.premissas["perfil"] == "civil_3_v1"
    assert resultado.descontos.resumo.total_atualizado == D("103.02")
    assert resultado.resumo.total_atualizado == D("937.38")
    assert colunas_componentes(resultado)[0][:2] == ("inpc", "INPC")
