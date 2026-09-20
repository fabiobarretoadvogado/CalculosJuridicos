"""
Módulo de cálculo de correção monetária.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from liquidacao_custom.core.indices import calcular_fator_acumulado, consultar_indice
from liquidacao_custom.core.models import IndiceCorrecao, MemoriaMensal, PeriodoCorrecao


def calcular_correcao(
    valor: Decimal,
    periodos: list[PeriodoCorrecao],
    data_base: date,
) -> dict:
    """
    Calcula a correção monetária de um valor base com base nos períodos definidos.
    """
    alertas: list[str] = []
    memoria_mensal: list[MemoriaMensal] = []

    if not periodos:
        return {
            "valor_original": valor,
            "fator_acumulado": Decimal("1.0000"),
            "valor_corrigido": valor,
            "memoria_mensal": memoria_mensal,
            "alertas": alertas,
        }

    valor_corrigido = valor
    fator_global = Decimal("1.000000")

    for pc in periodos:
        if pc.indice == IndiceCorrecao.SEM_CORRECAO:
            continue

        data_ini = pc.data_inicial
        data_fim = pc.data_final or data_base

        if not data_ini:
            alertas.append(f"Período de correção sem data inicial informada. Ignorando período.")
            continue

        if pc.indice == IndiceCorrecao.INDICE_MANUAL:
            fator_periodo = pc.fator_manual or Decimal("1.0000")
            valor_corrigido *= fator_periodo
            fator_global *= fator_periodo
            memoria_mensal.append(MemoriaMensal(
                competencia=f"{data_ini.year:04d}-{data_ini.month:02d}",
                valor_base=valor_corrigido / fator_periodo,
                indice_aplicado="INDICE_MANUAL",
                fator_aplicado=fator_periodo,
                valor_corrigido=valor_corrigido,
                total=valor_corrigido,
                observacao=pc.observacao or "Correção manual aplicada"
            ))
            continue

        # Outros índices (IPCA, INPC, IPCA-E, IGP-M, SELIC, TAXA_LEGAL)
        fator_periodo, alertas_ind = calcular_fator_acumulado(pc.indice.value, data_ini, data_fim)
        alertas.extend(alertas_ind)

        valor_antes = valor_corrigido
        valor_corrigido *= fator_periodo
        fator_global *= fator_periodo

        memoria_mensal.append(MemoriaMensal(
            competencia=f"{data_ini.year:04d}-{data_ini.month:02d}",
            valor_base=valor_antes,
            indice_aplicado=pc.indice.value,
            fator_aplicado=fator_periodo,
            valor_corrigido=valor_corrigido,
            total=valor_corrigido,
            observacao=f"Correção de {data_ini} a {data_fim}"
        ))

    return {
        "valor_original": valor,
        "fator_acumulado": fator_global.quantize(Decimal("0.000001")),
        "valor_corrigido": valor_corrigido.quantize(Decimal("0.01")),
        "memoria_mensal": memoria_mensal,
        "alertas": alertas,
    }
