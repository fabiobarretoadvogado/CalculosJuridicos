from datetime import date

import pytest

from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado
from liquidacao_custom.core.motor_simplificado import criterios_publicos, executar_calculo


def entrada(juros):
    return CalculoSimplificado.model_validate({
        "perfil": "ipca_taxa_legal_v1",
        "dados_gerais": {"data_base": "2026-09-01", "criterio_inicio_juros": "data_fixa",
                         "data_inicial_juros": juros},
        "parcelas": [{"numero": 1, "historico": "Correção anterior à Taxa Legal",
                      "data_vencimento": "2011-11-10", "valor_bruto": "57000",
                      "valor_pago_na_data": "0"}],
    })


def test_ipca_anterior_a_taxa_legal_e_aceito_com_limites_independentes():
    criterios = criterios_publicos(perfil="ipca_taxa_legal_v1")
    assert criterios["inicio_correcao"] == "1980-01-01"
    assert criterios["inicio_juros"] == "2024-08-30"
    parcela = executar_calculo(entrada("2024-08-30")).parcelas[0]
    assert parcela.componentes["ipca"].data_inicial == date(2011, 11, 10)
    assert parcela.memoria_correcao[0].competencia == "2011-11"
    assert parcela.componentes["taxa_legal"].data_inicial == date(2024, 8, 30)


def test_juros_anteriores_nao_sao_truncados_automaticamente():
    with pytest.raises(ValueError, match="Taxa Legal oficial disponível desde 30/08/2024"):
        executar_calculo(entrada("2016-07-08"))
