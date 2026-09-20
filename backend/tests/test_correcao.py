from datetime import date
from decimal import Decimal
from liquidacao_custom.core.models import PeriodoCorrecao, IndiceCorrecao
from liquidacao_custom.core.correcao import calcular_correcao

def test_dano_material_corrigido_desde_desembolso():
    # Teste 2: Dano material corrigido desde o desembolso
    periodo = PeriodoCorrecao(
        indice=IndiceCorrecao.IPCA,
        data_inicial=date(2024, 1, 10),
        data_final=date(2024, 3, 10)
    )
    # Entre 2024-01 e 2024-03, fatores do ipca: 2024-01 (1.0042) * 2024-02 (1.0083) = 1.012534
    res = calcular_correcao(Decimal("1000.00"), [periodo], date(2025, 6, 1))
    assert res["valor_corrigido"] > Decimal("1000.00")
    assert abs(res["fator_acumulado"] - Decimal("1.012534")) <= Decimal("0.000002")

def test_dano_moral_corrigido_desde_arbitramento():
    # Teste 3: Dano moral corrigido desde o arbitramento
    periodo = PeriodoCorrecao(
        indice=IndiceCorrecao.IPCA,
        data_inicial=date(2024, 10, 5),
        data_final=date(2024, 12, 5)
    )
    # Entre 2024-10 e 2024-12: 2024-10 (1.0056) * 2024-11 (1.0062) = 1.011835
    res = calcular_correcao(Decimal("5000.00"), [periodo], date(2025, 6, 1))
    assert res["valor_corrigido"] == Decimal("5059.18")
