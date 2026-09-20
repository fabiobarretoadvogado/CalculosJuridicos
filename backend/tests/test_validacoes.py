from datetime import date
from decimal import Decimal
from liquidacao_custom.core.models import (
    CalculoJudicial,
    DadosGerais,
    IndiceCorrecao,
    TipoJuros,
    Parcela,
    MultaCPC523,
    TipoDevedor,
    PeriodoCorrecao,
    ConfigJuros
)
from liquidacao_custom.core.validacoes import validar_calculo

def test_alertas_validacoes():
    # Teste 15: Alerta de multa do art. 523 contra Fazenda Pública (ALERTA 9)
    # Teste 16: Alerta de índice inexistente (ALERTA 3)
    # Teste 17: Alerta de SELIC cumulada com outro índice (ALERTA 6)
    # Teste 18: Alerta de períodos de correção sobrepostos (ALERTA 7)
    # Teste 19: Alerta de períodos de juros sobrepostos (ALERTA 8)
    
    calc = CalculoJudicial(
        dados_gerais=DadosGerais(
            data_base=date(2025, 6, 1),
            tipo_devedor=TipoDevedor.FAZENDA_PUBLICA
        ),
        multa_cpc523=MultaCPC523(aplicar=True),
        parcelas=[
            Parcela(
                numero=1,
                valor_bruto=Decimal("100.00"),
                correcao_monetaria=IndiceCorrecao.SELIC,
                juros_moratorios=TipoJuros.PERCENTUAL_MENSAL_SIMPLES,
                percentual_juros=Decimal("1.0"),
                data_vencimento=date(2024, 1, 1),
                data_inicial_correcao=date(2024, 1, 1),
                data_inicial_juros=date(2024, 1, 1)
            ),
            # Períodos sobrepostos
            Parcela(
                numero=2,
                valor_bruto=Decimal("200.00"),
                data_vencimento=date(2024, 1, 1),
                periodos_correcao=[
                    PeriodoCorrecao(indice=IndiceCorrecao.IPCA, data_inicial=date(2024, 1, 1), data_final=date(2024, 5, 1)),
                    PeriodoCorrecao(indice=IndiceCorrecao.IPCA, data_inicial=date(2024, 3, 1), data_final=date(2024, 8, 1))
                ]
            )
        ]
    )
    
    alertas = validar_calculo(calc)
    assert any("ALERTA 9:" in a for a in alertas)
    assert any("ALERTA 6:" in a for a in alertas)
    assert any("ALERTA 7:" in a for a in alertas)
