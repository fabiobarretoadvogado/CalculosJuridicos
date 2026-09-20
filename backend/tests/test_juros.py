from datetime import date
from decimal import Decimal
from liquidacao_custom.core.models import ConfigJuros, TipoJuros
from liquidacao_custom.core.juros import calcular_juros

def test_juros_termos_iniciais_diferentes():
    # Teste 4: Juros com datas iniciais diferentes para parcelas diferentes
    pj1 = ConfigJuros(
        tipo=TipoJuros.PERCENTUAL_MENSAL_SIMPLES,
        data_inicial=date(2024, 1, 10),
        data_final=date(2024, 5, 10),
        percentual=Decimal("1.00")
    )
    pj2 = ConfigJuros(
        tipo=TipoJuros.PERCENTUAL_MENSAL_SIMPLES,
        data_inicial=date(2024, 3, 10),
        data_final=date(2024, 5, 10),
        percentual=Decimal("1.00")
    )
    res1 = calcular_juros(Decimal("1000.00"), Decimal("1000.00"), [pj1], date(2024, 5, 10))
    res2 = calcular_juros(Decimal("1000.00"), Decimal("1000.00"), [pj2], date(2024, 5, 10))
    
    # 4 meses vs 2 meses (com contagem_mes_cheio = True)
    assert res1["valor_juros"] == Decimal("40.00")
    assert res2["valor_juros"] == Decimal("20.00")


def test_juros_compostos_pro_rata_die():
    pj = ConfigJuros(
        tipo=TipoJuros.PERCENTUAL_MENSAL_COMPOSTO,
        data_inicial=date(2024, 1, 1),
        data_final=date(2024, 2, 15),
        percentual=Decimal("1.00"),
        contagem_mes_cheio=False,
    )

    res = calcular_juros(Decimal("1000.00"), Decimal("1000.00"), [pj], date(2024, 2, 15))

    assert res["valor_juros"] == Decimal("14.82")
