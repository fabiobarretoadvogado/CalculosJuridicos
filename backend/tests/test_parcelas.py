from datetime import date
from decimal import Decimal
from liquidacao_custom.core.models import Parcela, IndiceCorrecao, TipoJuros
from liquidacao_custom.core.parcelas import (
    adicionar_parcela,
    excluir_parcela,
    duplicar_parcela,
    editar_parcela,
    copiar_criterios_anterior,
    edicao_em_lote,
    excluir_em_lote
)

def test_lancamento_manual_e_criterios_diferentes():
    # Teste 1: Lançamento manual de duas parcelas com critérios diferentes
    parcelas = []
    p1 = Parcela(
        numero=1,
        natureza="Dano Material",
        data_vencimento=date(2024, 1, 10),
        historico="Parcela 1",
        valor_bruto=Decimal("1000.00"),
        correcao_monetaria=IndiceCorrecao.IPCA,
        data_inicial_correcao=date(2024, 1, 10),
        juros_moratorios=TipoJuros.PERCENTUAL_MENSAL_SIMPLES,
        data_inicial_juros=date(2024, 1, 10),
        percentual_juros=Decimal("1.00")
    )
    p2 = Parcela(
        numero=2,
        natureza="Custas",
        data_vencimento=date(2024, 2, 10),
        historico="Parcela 2",
        valor_bruto=Decimal("200.00"),
        correcao_monetaria=IndiceCorrecao.IGPM,
        data_inicial_correcao=date(2024, 2, 10),
        juros_moratorios=TipoJuros.SEM_JUROS
    )
    adicionar_parcela(parcelas, p1)
    adicionar_parcela(parcelas, p2)
    assert len(parcelas) == 2
    assert parcelas[0].correcao_monetaria == IndiceCorrecao.IPCA
    assert parcelas[1].correcao_monetaria == IndiceCorrecao.IGPM

def test_duplicar_e_excluir():
    parcelas = [
        Parcela(numero=1, historico="P1", valor_bruto=Decimal("100.00"), data_vencimento=date(2024, 1, 1)),
        Parcela(numero=2, historico="P2", valor_bruto=Decimal("200.00"), data_vencimento=date(2024, 2, 1))
    ]
    duplicar_parcela(parcelas, 1)
    assert len(parcelas) == 3
    parcelas = excluir_parcela(parcelas, 2)
    assert len(parcelas) == 2

def test_copiar_criterios_anterior():
    p1 = Parcela(
        numero=1,
        correcao_monetaria=IndiceCorrecao.IPCA,
        data_inicial_correcao=date(2024, 1, 10),
        juros_moratorios=TipoJuros.PERCENTUAL_MENSAL_SIMPLES,
        data_inicial_juros=date(2024, 1, 10),
        percentual_juros=Decimal("1.00"),
        data_vencimento=date(2024, 1, 10)
    )
    p2 = Parcela(
        numero=2,
        correcao_monetaria=IndiceCorrecao.SEM_CORRECAO,
        data_vencimento=date(2024, 2, 10)
    )
    parcelas = [p1, p2]
    copiar_criterios_anterior(parcelas, 2)
    assert parcelas[1].correcao_monetaria == IndiceCorrecao.IPCA
    assert parcelas[1].percentual_juros == Decimal("1.00")

def test_edicao_em_lote_correcao():
    # Teste 8: Edição em lote de correção monetária
    parcelas = [
        Parcela(numero=1, correcao_monetaria=IndiceCorrecao.INPC, data_vencimento=date(2024, 1, 1)),
        Parcela(numero=2, correcao_monetaria=IndiceCorrecao.INPC, data_vencimento=date(2024, 2, 1))
    ]
    edicao_em_lote(parcelas, [1, 2], correcao_monetaria=IndiceCorrecao.IPCA)
    assert parcelas[0].correcao_monetaria == IndiceCorrecao.IPCA
    assert parcelas[1].correcao_monetaria == IndiceCorrecao.IPCA

def test_edicao_em_lote_juros():
    # Teste 9: Edição em lote de juros
    parcelas = [
        Parcela(numero=1, juros_moratorios=TipoJuros.SEM_JUROS, data_vencimento=date(2024, 1, 1)),
        Parcela(numero=2, juros_moratorios=TipoJuros.SEM_JUROS, data_vencimento=date(2024, 2, 1))
    ]
    edicao_em_lote(parcelas, [1, 2], juros_moratorios=TipoJuros.PERCENTUAL_MENSAL_SIMPLES, percentual_juros=Decimal("2.0"))
    assert parcelas[0].juros_moratorios == TipoJuros.PERCENTUAL_MENSAL_SIMPLES
    assert parcelas[0].percentual_juros == Decimal("2.0")
