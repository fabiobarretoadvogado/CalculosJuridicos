from datetime import date
from decimal import Decimal
from liquidacao_custom.core.models import Abatimento, FormaImputacao, ResultadoParcela, TipoJuros
from liquidacao_custom.core.abatimentos import aplicar_abatimentos

def test_abatimento_posterior_data_propria():
    # Teste 10: Abatimento posterior em data própria
    parcelas = [
        ResultadoParcela(numero=1, valor_bruto=Decimal("1000.00"), valor_corrigido=Decimal("1100.00"), total_parcela=Decimal("1100.00"))
    ]
    abatimento = Abatimento(
        data_pagamento=date(2024, 6, 15),
        valor=Decimal("300.00"),
        forma_imputacao=FormaImputacao.ABATER_NA_DATA_DO_PAGAMENTO
    )
    res = aplicar_abatimentos(parcelas, [abatimento])
    assert res["total_abatido"] == Decimal("300.00")
    assert res["parcelas_ajustadas"][0].total_parcela == Decimal("800.00")

def test_distincao_valor_pago_na_data_e_abatimento():
    # Teste 11: Distinção entre valor pago na data da parcela e abatimento posterior
    # Parcela com valor pago na data reduz valor apurado original
    p = ResultadoParcela(
        numero=1,
        valor_bruto=Decimal("1000.00"),
        valor_pago_na_data=Decimal("200.00"),
        valor_apurado=Decimal("800.00"),
        total_parcela=Decimal("800.00")
    )
    # Abatimento posterior
    abatimento = Abatimento(
        data_pagamento=date(2024, 6, 15),
        valor=Decimal("100.00"),
        forma_imputacao=FormaImputacao.ABATER_NA_DATA_DO_PAGAMENTO
    )
    res = aplicar_abatimentos([p], [abatimento])
    assert res["parcelas_ajustadas"][0].valor_pago_na_data == Decimal("200.00")
    assert res["parcelas_ajustadas"][0].total_parcela == Decimal("700.00")

def test_abatimento_com_juros_ate_data_base():
    parcelas = [
        ResultadoParcela(numero=1, valor_bruto=Decimal("1000.00"), valor_corrigido=Decimal("1000.00"), total_parcela=Decimal("1000.00"))
    ]
    abatimento = Abatimento(
        data_pagamento=date(2024, 1, 1),
        valor=Decimal("100.00"),
        forma_imputacao=FormaImputacao.ABATER_DO_TOTAL_NA_DATA_BASE,
        juros_moratorios=TipoJuros.PERCENTUAL_MENSAL_SIMPLES,
        data_inicial_juros=date(2024, 1, 1),
        percentual_juros=Decimal("1.00"),
    )
    res = aplicar_abatimentos(parcelas, [abatimento], data_base=date(2024, 4, 1))
    assert res["total_abatido"] > Decimal("100.00")
    assert res["memorias"][0].valor_original == Decimal("100.00")
    assert res["memorias"][0].juros_mora > Decimal("0.00")


def test_abatimento_maior_que_debito_quita_e_registra_saldo_remanescente():
    parcelas = [
        ResultadoParcela(numero=1, valor_bruto=Decimal("1000.00"), valor_corrigido=Decimal("1000.00"), total_parcela=Decimal("1000.00"))
    ]
    abatimento = Abatimento(
        data_pagamento=date(2024, 2, 15),
        valor=Decimal("1500.00"),
        forma_imputacao=FormaImputacao.ABATER_DO_TOTAL_NA_DATA_BASE,
    )

    res = aplicar_abatimentos(parcelas, [abatimento], data_base=date(2024, 4, 1))

    assert res["parcelas_ajustadas"][0].total_parcela == Decimal("0.00")
    assert res["total_abatido"] == Decimal("1000.00")
    assert res["memorias"][0].saldo_posterior == Decimal("0.00")
    assert res["memorias"][0].competencia_quitacao == "2024-02"
    assert res["memorias"][0].saldo_remanescente == Decimal("500.00")
