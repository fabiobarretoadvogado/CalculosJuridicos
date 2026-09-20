"""
MÃ³dulo de abatimentos posteriores.

Implementa a aplicaÃ§Ã£o de pagamentos parciais, alvarÃ¡s, retenÃ§Ãµes
e outros abatimentos ocorridos apÃ³s a data de vencimento das parcelas.

Regra operacional:
- Pagamentos na data do vencimento â†’ valor_pago_na_data na parcela
- Pagamentos posteriores â†’ abatimento com data e forma de imputaÃ§Ã£o prÃ³prias
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from liquidacao_custom.core.models import (
    Abatimento,
    ConfigJuros,
    FormaImputacao,
    IndiceCorrecao,
    MemoriaAbatimento,
    PeriodoCorrecao,
    ResultadoParcela,
    TipoJuros,
)
from liquidacao_custom.core.correcao import calcular_correcao
from liquidacao_custom.core.juros import calcular_juros


def aplicar_abatimentos(
    parcelas_resultado: list[ResultadoParcela],
    abatimentos: list[Abatimento],
    total_antes: Decimal = Decimal("0"),
    data_base: Optional[date] = None,
) -> dict:
    """
    Aplica abatimentos posteriores sobre o resultado das parcelas.

    Args:
        parcelas_resultado: Lista de resultados jÃ¡ calculados.
        abatimentos: Lista de abatimentos a aplicar.
        total_antes: Total antes dos abatimentos (para memÃ³ria).

    Returns:
        dict com:
            - total_abatido: Decimal
            - memorias: list[MemoriaAbatimento]
            - alertas: list[str]
            - parcelas_ajustadas: list[ResultadoParcela]
    """
    if not abatimentos:
        return {
            "total_abatido": Decimal("0"),
            "memorias": [],
            "alertas": [],
            "parcelas_ajustadas": parcelas_resultado,
        }

    alertas: list[str] = []
    memorias: list[MemoriaAbatimento] = []
    total_abatido = Decimal("0")

    # Trabalhar com cÃ³pia para nÃ£o mutar a entrada
    parcelas = [p.model_copy(deep=True) for p in parcelas_resultado]

    saldo_total = sum(p.total_parcela for p in parcelas)
    if total_antes == Decimal("0"):
        total_antes = saldo_total

    for abat in abatimentos:
        saldo_anterior = sum(p.total_parcela for p in parcelas)
        if saldo_anterior <= Decimal("0"):
            alertas.append(
                f"Abatimento de R$ {abat.valor} em {abat.data_pagamento} nÃƒÂ£o aplicado: "
                "dÃƒÂ©bito jÃƒÂ¡ quitado em abatimento anterior."
            )
            continue

        res_atualizacao = _atualizar_abatimento(abat, data_base)
        alertas.extend(res_atualizacao["alertas"])
        valor_a_abater = res_atualizacao["valor_atualizado"]

        if abat.forma_imputacao == FormaImputacao.ABATER_DO_TOTAL_NA_DATA_BASE:
            # Abate proporcionalmente do total na data-base
            parcelas, abatido = _abater_proporcional(parcelas, valor_a_abater)
            total_abatido += abatido

        elif abat.forma_imputacao == FormaImputacao.ABATER_NA_DATA_DO_PAGAMENTO:
            # Abate do total na data do pagamento (simplificado no MVP: abate do total)
            parcelas, abatido = _abater_proporcional(parcelas, valor_a_abater)
            total_abatido += abatido

        elif abat.forma_imputacao == FormaImputacao.PRIMEIRO_JUROS_DEPOIS_PRINCIPAL:
            parcelas, abatido = _abater_juros_primeiro(parcelas, valor_a_abater)
            total_abatido += abatido

        elif abat.forma_imputacao == FormaImputacao.PRIMEIRO_PRINCIPAL_DEPOIS_JUROS:
            parcelas, abatido = _abater_principal_primeiro(parcelas, valor_a_abater)
            total_abatido += abatido

        elif abat.forma_imputacao == FormaImputacao.PROPORCIONAL:
            parcelas, abatido = _abater_proporcional(parcelas, valor_a_abater)
            total_abatido += abatido

        elif abat.forma_imputacao == FormaImputacao.PARCELA_ESPECIFICA:
            if abat.parcela_especifica is not None:
                parcelas, abatido = _abater_parcela_especifica(
                    parcelas, valor_a_abater, abat.parcela_especifica
                )
                total_abatido += abatido
            else:
                alertas.append(
                    f"Abatimento com forma 'parcela_especifica' sem nÃºmero "
                    f"de parcela definido. Valor: R$ {abat.valor}"
                )
                continue

        saldo_posterior = sum(p.total_parcela for p in parcelas)
        saldo_remanescente = max(valor_a_abater - saldo_anterior, Decimal("0"))
        competencia_quitacao = None
        if saldo_posterior == Decimal("0"):
            competencia_quitacao = f"{abat.data_pagamento.year:04d}-{abat.data_pagamento.month:02d}"
        if saldo_remanescente > Decimal("0"):
            alertas.append(
                f"Debito quitado em {competencia_quitacao}. "
                f"Saldo remanescente do abatimento: R$ {saldo_remanescente.quantize(Decimal('0.01'))}."
            )


        memorias.append(MemoriaAbatimento(
            data_pagamento=abat.data_pagamento,
            valor_abatido=abatido.quantize(Decimal("0.01")),
            valor_original=abat.valor.quantize(Decimal("0.01")),
            correcao_monetaria=res_atualizacao["correcao_monetaria"],
            juros_mora=res_atualizacao["juros_mora"],
            forma_imputacao=abat.forma_imputacao,
            parcela_especifica=abat.parcela_especifica,
            historico=abat.historico,
            saldo_anterior=saldo_anterior.quantize(Decimal("0.01")),
            saldo_posterior=saldo_posterior.quantize(Decimal("0.01")),
            competencia_quitacao=competencia_quitacao,
            saldo_remanescente=saldo_remanescente.quantize(Decimal("0.01")),
        ))

    return {
        "total_abatido": total_abatido.quantize(Decimal("0.01")),
        "memorias": memorias,
        "alertas": alertas,
        "parcelas_ajustadas": parcelas,
    }


def _atualizar_abatimento(abat: Abatimento, data_base: Optional[date]) -> dict:
    """Atualiza o valor do desconto ate a data-base, quando houver criterio."""
    alertas: list[str] = []
    valor_corrigido = abat.valor
    correcao_valor = Decimal("0")
    juros_valor = Decimal("0")

    if data_base is None:
        return {
            "valor_atualizado": abat.valor.quantize(Decimal("0.01")),
            "correcao_monetaria": Decimal("0"),
            "juros_mora": Decimal("0"),
            "alertas": alertas,
        }

    if abat.correcao_monetaria != IndiceCorrecao.SEM_CORRECAO:
        periodo = PeriodoCorrecao(
            indice=abat.correcao_monetaria,
            data_inicial=abat.data_inicial_correcao or abat.data_pagamento,
            data_final=data_base,
        )
        res_corr = calcular_correcao(abat.valor, [periodo], data_base)
        valor_corrigido = res_corr["valor_corrigido"]
        correcao_valor = valor_corrigido - abat.valor
        alertas.extend(res_corr.get("alertas", []))

    if abat.juros_moratorios != TipoJuros.SEM_JUROS:
        periodo_juros = ConfigJuros(
            tipo=abat.juros_moratorios,
            data_inicial=abat.data_inicial_juros or abat.data_pagamento,
            data_final=data_base,
            percentual=abat.percentual_juros,
        )
        res_juros = calcular_juros(abat.valor, valor_corrigido, [periodo_juros], data_base)
        juros_valor = res_juros["valor_juros"]
        alertas.extend(res_juros.get("alertas", []))

    return {
        "valor_atualizado": (valor_corrigido + juros_valor).quantize(Decimal("0.01")),
        "correcao_monetaria": correcao_valor.quantize(Decimal("0.01")),
        "juros_mora": juros_valor.quantize(Decimal("0.01")),
        "alertas": alertas,
    }


def _abater_proporcional(
    parcelas: list[ResultadoParcela],
    valor: Decimal,
) -> tuple[list[ResultadoParcela], Decimal]:
    """Abate proporcionalmente entre todas as parcelas."""
    total = sum(p.total_parcela for p in parcelas)
    if total <= Decimal("0"):
        return parcelas, Decimal("0")

    abatido = Decimal("0")
    for p in parcelas:
        if p.total_parcela > Decimal("0"):
            proporcao = p.total_parcela / total
            abatimento_parcela = (valor * proporcao).quantize(Decimal("0.01"))
            abatimento_parcela = min(abatimento_parcela, p.total_parcela)
            p.total_parcela -= abatimento_parcela
            abatido += abatimento_parcela

    return parcelas, abatido


def _abater_juros_primeiro(
    parcelas: list[ResultadoParcela],
    valor: Decimal,
) -> tuple[list[ResultadoParcela], Decimal]:
    """Abate primeiro dos juros, depois do principal."""
    restante = valor
    abatido = Decimal("0")

    # Fase 1: abater dos juros
    for p in parcelas:
        if restante <= Decimal("0"):
            break
        if p.juros_mora > Decimal("0"):
            abater = min(restante, p.juros_mora)
            p.juros_mora -= abater
            p.total_parcela -= abater
            restante -= abater
            abatido += abater

    # Fase 2: abater do principal corrigido
    for p in parcelas:
        if restante <= Decimal("0"):
            break
        if p.total_parcela > Decimal("0"):
            abater = min(restante, p.total_parcela)
            p.valor_corrigido -= abater
            p.total_parcela -= abater
            restante -= abater
            abatido += abater

    return parcelas, abatido


def _abater_principal_primeiro(
    parcelas: list[ResultadoParcela],
    valor: Decimal,
) -> tuple[list[ResultadoParcela], Decimal]:
    """Abate primeiro do principal, depois dos juros."""
    restante = valor
    abatido = Decimal("0")

    # Fase 1: abater do principal corrigido
    for p in parcelas:
        if restante <= Decimal("0"):
            break
        if p.valor_corrigido > Decimal("0"):
            abater = min(restante, p.valor_corrigido)
            p.valor_corrigido -= abater
            p.total_parcela -= abater
            restante -= abater
            abatido += abater

    # Fase 2: abater dos juros
    for p in parcelas:
        if restante <= Decimal("0"):
            break
        if p.juros_mora > Decimal("0"):
            abater = min(restante, p.juros_mora)
            p.juros_mora -= abater
            p.total_parcela -= abater
            restante -= abater
            abatido += abater

    return parcelas, abatido


def _abater_parcela_especifica(
    parcelas: list[ResultadoParcela],
    valor: Decimal,
    numero_parcela: int,
) -> tuple[list[ResultadoParcela], Decimal]:
    """Abate de uma parcela especÃ­fica."""
    abatido = Decimal("0")
    for p in parcelas:
        if p.numero == numero_parcela:
            abater = min(valor, max(p.total_parcela, Decimal("0")))
            p.total_parcela -= abater
            abatido = abater
            break
    return parcelas, abatido
