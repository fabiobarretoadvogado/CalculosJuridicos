"""
Módulo de validações e alertas do cálculo judicial.

O sistema não bloqueia o cálculo por padrão.
Gera alertas para revisão humana.
Exceção: erros estruturais graves podem impedir a execução.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from liquidacao_custom.core.models import (
    Abatimento,
    CalculoJudicial,
    ConfigJuros,
    Honorarios,
    IndiceCorrecao,
    Parcela,
    PeriodoCorrecao,
    TipoDevedor,
    TipoJuros,
)


def validar_calculo(calculo: CalculoJudicial) -> list[str]:
    """
    Executa todas as validações sobre o cálculo e retorna lista de alertas.

    Os alertas são informativos e não bloqueiam o cálculo,
    salvo erros estruturais graves.
    """
    alertas: list[str] = []

    data_base = calculo.dados_gerais.data_base
    tipo_devedor = calculo.dados_gerais.tipo_devedor

    for parcela in calculo.parcelas:
        alertas.extend(_validar_parcela(parcela, data_base, tipo_devedor, calculo))

    # Validação 9: Multa do art. 523 contra Fazenda Pública
    if calculo.multa_cpc523.aplicar and tipo_devedor == TipoDevedor.FAZENDA_PUBLICA:
        alertas.append(
            f"Parcela GERAL | ALERTA 9: Multa do art. 523 do CPC aplicada "
            f"contra Fazenda Pública. Verificar cabimento."
        )

    # Validação 15: Honorários sem base de cálculo definida
    for i, hon in enumerate(calculo.honorarios, 1):
        if hon.percentual is None and hon.valor_fixo is None:
            alertas.append(
                f"Honorário {i} | ALERTA 15: Honorários sem base de cálculo "
                f"definida (sem percentual e sem valor fixo)."
            )

    # Validação 11: Abatimento com data posterior à data-base
    for abat in calculo.abatimentos:
        if abat.data_pagamento > data_base:
            alertas.append(
                f"Abatimento de R$ {abat.valor} | ALERTA 11: Data do "
                f"pagamento ({abat.data_pagamento}) posterior à data-base "
                f"({data_base})."
            )

    # Validação 20: Fazenda Pública com juros separados após SELIC única
    if (
        tipo_devedor == TipoDevedor.FAZENDA_PUBLICA
        and calculo.config_selic_taxa_unica.aplicar
        and calculo.config_selic_taxa_unica.data_inicio
    ):
        data_selic = calculo.config_selic_taxa_unica.data_inicio
        for parcela in calculo.parcelas:
            periodos_juros = parcela.get_periodos_juros_efetivos(data_base)
            for pj in periodos_juros:
                if (
                    pj.tipo != TipoJuros.SEM_JUROS
                    and pj.tipo != TipoJuros.SELIC
                    and pj.data_inicial
                    and pj.data_inicial >= data_selic
                ):
                    alertas.append(
                        f"Parcela {parcela.numero} | ALERTA 20: Cálculo contra "
                        f"Fazenda Pública com juros separados ({pj.tipo.value}) "
                        f"após a data configurada para SELIC única ({data_selic})."
                    )

    return alertas


def _validar_parcela(
    parcela: Parcela,
    data_base: date,
    tipo_devedor: TipoDevedor,
    calculo: CalculoJudicial,
) -> list[str]:
    """Valida uma parcela individual e retorna alertas."""
    alertas: list[str] = []
    num = parcela.numero

    periodos_correcao = parcela.get_periodos_correcao_efetivos(data_base)
    periodos_juros = parcela.get_periodos_juros_efetivos(data_base)

    # Validação 1: Parcela sem data inicial de correção
    for pc in periodos_correcao:
        if pc.indice != IndiceCorrecao.SEM_CORRECAO and pc.data_inicial is None:
            alertas.append(
                f"Parcela {num} | ALERTA 1: Correção monetária "
                f"({pc.indice.value}) sem data inicial definida."
            )

    # Validação 2: Parcela sem data inicial de juros
    for pj in periodos_juros:
        if pj.tipo != TipoJuros.SEM_JUROS and pj.data_inicial is None:
            alertas.append(
                f"Parcela {num} | ALERTA 2: Juros moratórios "
                f"({pj.tipo.value}) sem data inicial definida."
            )

    # Validação 3: Índice de correção inexistente
    indices_validos = {e.value for e in IndiceCorrecao}
    for pc in periodos_correcao:
        if pc.indice.value not in indices_validos:
            alertas.append(
                f"Parcela {num} | ALERTA 3: Índice de correção "
                f"'{pc.indice.value}' não reconhecido."
            )

    # Validação 4: Tipo de juros inexistente
    juros_validos = {e.value for e in TipoJuros}
    for pj in periodos_juros:
        if pj.tipo.value not in juros_validos:
            alertas.append(
                f"Parcela {num} | ALERTA 4: Tipo de juros "
                f"'{pj.tipo.value}' não reconhecido."
            )

    # Validação 6: SELIC cumulada com outro índice ou juros no mesmo período
    _alertas_selic_cumulada(parcela, periodos_correcao, periodos_juros, num, alertas)

    # Validação 7: Períodos de correção sobrepostos
    _alertas_periodos_sobrepostos(periodos_correcao, num, "correção", alertas)

    # Validação 8: Períodos de juros sobrepostos
    _alertas_periodos_juros_sobrepostos(periodos_juros, num, alertas)

    # Validação 12: Data inicial dos juros anterior à data de vencimento
    if parcela.data_vencimento:
        for pj in periodos_juros:
            if (
                pj.tipo != TipoJuros.SEM_JUROS
                and pj.data_inicial
                and pj.data_inicial < parcela.data_vencimento
            ):
                alertas.append(
                    f"Parcela {num} | ALERTA 12: Data inicial dos juros "
                    f"({pj.data_inicial}) anterior à data de vencimento "
                    f"({parcela.data_vencimento})."
                )

    # Validação 13: Valor pago na data maior que valor bruto
    if parcela.valor_pago_na_data > parcela.valor_bruto:
        alertas.append(
            f"Parcela {num} | ALERTA 13: Valor pago na data "
            f"(R$ {parcela.valor_pago_na_data}) maior que valor bruto "
            f"(R$ {parcela.valor_bruto})."
        )

    # Validação 10: Valor pago na parcela + indícios de pagamento posterior
    if parcela.valor_pago_na_data > Decimal("0"):
        texto_obs = (parcela.observacao + " " + parcela.historico).lower()
        indicadores = ["pagamento posterior", "pago posteriormente",
                       "pago em", "alvará", "depósito posterior"]
        for ind in indicadores:
            if ind in texto_obs:
                alertas.append(
                    f"Parcela {num} | ALERTA 10: Valor pago informado na parcela "
                    f"(R$ {parcela.valor_pago_na_data}), mas o histórico/observação "
                    f"menciona pagamento posterior. Verificar se deve ser abatimento."
                )
                break

    # Validação 14: (verificado pós-cálculo, no motor)

    # Validação 16: SELIC como taxa única + juros separados no mesmo período
    _alerta_selic_taxa_unica_com_juros(
        parcela, periodos_correcao, periodos_juros, num, alertas
    )

    # Validação 17: Taxa Legal aplicada antes da vigência configurada
    data_vigencia_tl = calculo.config_taxa_legal.data_inicio_vigencia
    for pj in periodos_juros:
        if pj.tipo == TipoJuros.TAXA_LEGAL and pj.data_inicial:
            if pj.data_inicial < data_vigencia_tl:
                alertas.append(
                    f"Parcela {num} | ALERTA 17: Taxa Legal aplicada antes "
                    f"da data de vigência configurada ({data_vigencia_tl})."
                )

    # Validação 18: Dano moral corrigido antes do arbitramento
    if parcela.natureza.lower() in ("dano_moral", "dano moral"):
        for pc in periodos_correcao:
            if (
                pc.indice != IndiceCorrecao.SEM_CORRECAO
                and parcela.data_vencimento
                and pc.data_inicial
                and pc.data_inicial < parcela.data_vencimento
            ):
                alertas.append(
                    f"Parcela {num} | ALERTA 18: Parcela de dano moral "
                    f"com correção iniciando ({pc.data_inicial}) antes da "
                    f"data de arbitramento/vencimento ({parcela.data_vencimento})."
                )

    # Validação 19: Dano material sem data de desembolso/vencimento
    if parcela.natureza.lower() in ("dano_material", "dano material"):
        if parcela.data_vencimento is None:
            alertas.append(
                f"Parcela {num} | ALERTA 19: Parcela de dano material "
                f"sem data de desembolso ou vencimento."
            )

    return alertas


def _alertas_selic_cumulada(
    parcela: Parcela,
    periodos_correcao: list[PeriodoCorrecao],
    periodos_juros: list[ConfigJuros],
    num: int,
    alertas: list[str],
) -> None:
    """Validação 6: SELIC cumulada com outro índice ou juros."""
    tem_selic_correcao = any(
        pc.indice == IndiceCorrecao.SELIC for pc in periodos_correcao
    )
    tem_selic_juros = any(
        pj.tipo == TipoJuros.SELIC for pj in periodos_juros
    )
    tem_outro_indice = any(
        pc.indice not in (IndiceCorrecao.SEM_CORRECAO, IndiceCorrecao.SELIC)
        for pc in periodos_correcao
    )
    tem_outro_juros = any(
        pj.tipo not in (TipoJuros.SEM_JUROS, TipoJuros.SELIC)
        for pj in periodos_juros
    )

    if tem_selic_correcao and tem_outro_juros:
        alertas.append(
            f"Parcela {num} | ALERTA 6: SELIC usada como correção e "
            f"há juros de outro tipo na mesma parcela. Verificar cumulação."
        )

    if tem_selic_juros and tem_outro_indice:
        alertas.append(
            f"Parcela {num} | ALERTA 6: SELIC usada como juros e "
            f"há correção por outro índice na mesma parcela. Verificar cumulação."
        )

    if tem_selic_correcao and tem_selic_juros:
        alertas.append(
            f"Parcela {num} | ALERTA 6: SELIC usada simultaneamente como "
            f"correção e como juros na mesma parcela. Possível duplicidade."
        )


def _alertas_periodos_sobrepostos(
    periodos: list[PeriodoCorrecao],
    num: int,
    tipo: str,
    alertas: list[str],
) -> None:
    """Validação 7: Períodos de correção sobrepostos."""
    periodos_com_data = [
        p for p in periodos
        if p.data_inicial and p.data_final
        and p.indice != IndiceCorrecao.SEM_CORRECAO
    ]
    for i, p1 in enumerate(periodos_com_data):
        for p2 in periodos_com_data[i + 1:]:
            if p1.data_inicial <= p2.data_final and p2.data_inicial <= p1.data_final:
                alertas.append(
                    f"Parcela {num} | ALERTA 7: Períodos de {tipo} sobrepostos: "
                    f"{p1.data_inicial} a {p1.data_final} e "
                    f"{p2.data_inicial} a {p2.data_final}."
                )


def _alertas_periodos_juros_sobrepostos(
    periodos: list[ConfigJuros],
    num: int,
    alertas: list[str],
) -> None:
    """Validação 8: Períodos de juros sobrepostos."""
    periodos_com_data = [
        p for p in periodos
        if p.data_inicial and p.data_final
        and p.tipo != TipoJuros.SEM_JUROS
    ]
    for i, p1 in enumerate(periodos_com_data):
        for p2 in periodos_com_data[i + 1:]:
            if p1.data_inicial <= p2.data_final and p2.data_inicial <= p1.data_final:
                alertas.append(
                    f"Parcela {num} | ALERTA 8: Períodos de juros sobrepostos: "
                    f"{p1.data_inicial} a {p1.data_final} e "
                    f"{p2.data_inicial} a {p2.data_final}."
                )


def _alerta_selic_taxa_unica_com_juros(
    parcela: Parcela,
    periodos_correcao: list[PeriodoCorrecao],
    periodos_juros: list[ConfigJuros],
    num: int,
    alertas: list[str],
) -> None:
    """Validação 16: SELIC como taxa única com juros separados no mesmo período."""
    periodos_selic_correcao = [
        pc for pc in periodos_correcao if pc.indice == IndiceCorrecao.SELIC
    ]
    for ps in periodos_selic_correcao:
        if not ps.data_inicial or not ps.data_final:
            continue
        for pj in periodos_juros:
            if pj.tipo == TipoJuros.SEM_JUROS:
                continue
            if not pj.data_inicial or not pj.data_final:
                continue
            # Verifica sobreposição temporal
            if ps.data_inicial <= pj.data_final and pj.data_inicial <= ps.data_final:
                alertas.append(
                    f"Parcela {num} | ALERTA 16: SELIC como correção "
                    f"({ps.data_inicial} a {ps.data_final}) sobreposta "
                    f"com juros ({pj.tipo.value}: {pj.data_inicial} a "
                    f"{pj.data_final}). Se SELIC é taxa única, não deve "
                    f"haver juros separados."
                )
