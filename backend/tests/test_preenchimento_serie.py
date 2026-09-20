from datetime import date
from decimal import Decimal
from liquidacao_custom.core.models import (
    ConfigPreenchimentoSerie,
    ConfigSalarioMinimo,
    IndiceCorrecao,
    TipoJuros,
    Periodicidade
)
from liquidacao_custom.core.preenchimento_serie import gerar_serie, gerar_serie_salario_minimo

def test_preenchimento_serie_aluguel():
    # Teste 5: Preenchimento em série de aluguel
    config = ConfigPreenchimentoSerie(
        data_inicial=date(2024, 1, 10),
        data_final=date(2024, 12, 10),
        periodicidade=Periodicidade.MENSAL,
        dia_vencimento=10,
        historico_padrao="Aluguel",
        valor_fixo=Decimal("1200.00"),
        natureza="Aluguel",
        correcao_monetaria=IndiceCorrecao.IGPM,
        juros_moratorios=TipoJuros.PERCENTUAL_MENSAL_SIMPLES,
        percentual_juros=Decimal("1.00"),
        multa_moratoria=Decimal("10.00")
    )
    parcelas = gerar_serie(config)
    assert len(parcelas) == 12
    assert parcelas[0].data_vencimento == date(2024, 1, 10)
    assert parcelas[11].data_vencimento == date(2024, 12, 10)
    assert all(p.valor_bruto == Decimal("1200.00") for p in parcelas)

def test_geracao_parcelas_salario_minimo():
    # Teste 6: Geração de parcelas com percentual do salário mínimo
    config = ConfigSalarioMinimo(
        percentual=Decimal("30.00"),
        data_inicial=date(2024, 1, 10),
        data_final=date(2024, 12, 10),
        periodicidade=Periodicidade.MENSAL,
        dia_vencimento=10,
        historico="Pensão",
        natureza="Alimentos",
        correcao_monetaria=IndiceCorrecao.INPC
    )
    parcelas, alertas = gerar_serie_salario_minimo(config)
    # SM em 2024 = 1412.00. 30% = 423.60
    assert len(parcelas) == 12
    assert parcelas[0].valor_bruto == Decimal("423.60")
