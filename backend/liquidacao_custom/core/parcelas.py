"""
Módulo de gerenciamento de parcelas (CRUD, cópia de critérios e edições em lote).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from liquidacao_custom.core.models import IndiceCorrecao, Parcela, TipoJuros


def adicionar_parcela(parcelas: list[Parcela], parcela: Parcela) -> list[Parcela]:
    """Adiciona uma parcela à lista, garantindo a renumeração sequencial."""
    parcelas.append(parcela)
    _ordenar_e_renumerar(parcelas)
    return parcelas


def excluir_parcela(parcelas: list[Parcela], numero: int) -> list[Parcela]:
    """Exclui uma parcela pelo número e renumera a sequência."""
    parcelas = [p for p in parcelas if p.numero != numero]
    _ordenar_e_renumerar(parcelas)
    return parcelas


def duplicar_parcela(parcelas: list[Parcela], numero: int) -> list[Parcela]:
    """Duplica a parcela informada e adiciona ao final."""
    for p in parcelas:
        if p.numero == numero:
            nova = p.model_copy(deep=True)
            parcelas.append(nova)
            break
    _ordenar_e_renumerar(parcelas)
    return parcelas


def editar_parcela(parcelas: list[Parcela], numero: int, **campos: Any) -> list[Parcela]:
    """Edita os campos de uma parcela específica."""
    for p in parcelas:
        if p.numero == numero:
            for k, v in campos.items():
                if hasattr(p, k):
                    setattr(p, k, v)
            p.recalcular_apurado()
            break
    return parcelas


def copiar_criterios_anterior(parcelas: list[Parcela], numero: int) -> list[Parcela]:
    """Copia critérios de correção e juros da parcela anterior para a parcela indicada."""
    _ordenar_e_renumerar(parcelas)
    idx_target = -1
    for i, p in enumerate(parcelas):
        if p.numero == numero:
            idx_target = i
            break

    if idx_target > 0:
        ant = parcelas[idx_target - 1]
        tgt = parcelas[idx_target]

        tgt.correcao_monetaria = ant.correcao_monetaria
        tgt.data_inicial_correcao = ant.data_inicial_correcao
        tgt.data_final_correcao = ant.data_final_correcao
        tgt.periodos_correcao = [item.model_copy(deep=True) for item in ant.periodos_correcao]

        tgt.juros_moratorios = ant.juros_moratorios
        tgt.data_inicial_juros = ant.data_inicial_juros
        tgt.data_final_juros = ant.data_final_juros
        tgt.percentual_juros = ant.percentual_juros
        tgt.periodos_juros = [item.model_copy(deep=True) for item in ant.periodos_juros]

        tgt.multa_moratoria = ant.multa_moratoria

    return parcelas


def edicao_em_lote(parcelas: list[Parcela], numeros: list[int], **campos: Any) -> list[Parcela]:
    """Edita várias parcelas simultaneamente com os novos campos informados."""
    for p in parcelas:
        if p.numero in numeros:
            for k, v in campos.items():
                if hasattr(p, k):
                    setattr(p, k, v)
            p.recalcular_apurado()
    return parcelas


def excluir_em_lote(parcelas: list[Parcela], numeros: list[int]) -> list[Parcela]:
    """Exclui várias parcelas simultaneamente e renumera."""
    parcelas = [p for p in parcelas if p.numero not in numeros]
    _ordenar_e_renumerar(parcelas)
    return parcelas


def _ordenar_e_renumerar(parcelas: list[Parcela]) -> None:
    """Ordena as parcelas por data de vencimento e renumera a sequência."""
    # Se data_vencimento não existir, mantém a ordem original
    parcelas.sort(key=lambda x: x.data_vencimento if x.data_vencimento else date.max)
    for idx, p in enumerate(parcelas, 1):
        p.numero = idx
        p.recalcular_apurado()
