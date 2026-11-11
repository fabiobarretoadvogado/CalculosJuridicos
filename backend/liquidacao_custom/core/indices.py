"""
Módulo de carregamento e consulta de índices econômicos de correção monetária.
"""

from __future__ import annotations

import json
import os
from datetime import date
from decimal import Decimal
from typing import Optional


# Diretório base para os arquivos de dados
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from liquidacao_custom.index_data.store import DataPath, current_dataset
from liquidacao_custom.index_data.series import selic_values

DATA_DIR = DataPath()

# Cache global para evitar leituras de disco repetidas
_cache_indices: dict[tuple, dict[str, tuple[Decimal, Decimal]]] = {}


def _normalizar_nome_indice(nome: str) -> str:
    """Normaliza o identificador de compatibilidade do índice."""
    nome = nome.lower().replace("-", "").replace("_", "")
    if nome == "ipcae":
        return "ipcae"
    return nome


def carregar_indice(nome: str) -> dict[str, tuple[Decimal, Decimal]]:
    """
    Carrega o índice da base canônica fixada para a operação e retorna um dicionário indexado pela competência.
    Retorna: { "AAAA-MM": (percentual, fator) }
    """
    nome_norm = _normalizar_nome_indice(nome)
    dataset = current_dataset()
    key = (str(dataset.directory), dataset.identity, nome_norm)
    if key in _cache_indices:
        return _cache_indices[key]
    if nome_norm in ("ipca", "inpc", "igpm"):
        values = json.loads(DataPath(nome_norm + "_oficial.json").read_text(encoding="utf-8"))[nome_norm]
    elif nome_norm == "selic":
        values = selic_values(dataset.directory)
    elif nome_norm == "ipcae":
        # A API antiga não possuía ipcae.csv; o perfil oficial tem leitor próprio.
        return {}
    else:
        return {}
    dados = {comp: (Decimal(str(rate)), Decimal(1) + Decimal(str(rate)) / 100)
             for comp, rate in values.items()}
    _cache_indices[key] = dados
    return dados


def consultar_indice(nome: str, competencia: str) -> tuple[Decimal, Decimal]:
    """
    Consulta o percentual e o fator de um índice para uma competência específica (formato YYYY-MM).
    Retorna (percentual, fator). Se não achar, retorna (0, 1).
    """
    dados = carregar_indice(nome)
    if competencia in dados:
        return dados[competencia]
    return Decimal("0"), Decimal("1")


def calcular_fator_acumulado(nome: str, data_inicio: date, data_fim: date) -> tuple[Decimal, list[str]]:
    """
    Calcula o fator acumulado multiplicando os fatores mensais entre data_inicio e data_fim.
    Retorna (fator_acumulado, alertas).
    """
    alertas: list[str] = []
    if data_inicio >= data_fim:
        return Decimal("1.000000"), alertas

    fator = Decimal("1.000000")
    dados = carregar_indice(nome)

    # Iterar mês a mês
    ano_corrente = data_inicio.year
    mes_corrente = data_inicio.month

    while date(ano_corrente, mes_corrente, 1) < date(data_fim.year, data_fim.month, 1):
        comp = f"{ano_corrente:04d}-{mes_corrente:02d}"
        if comp in dados:
            fator *= dados[comp][1]
        else:
            alertas.append(f"ALERTA: Competência '{comp}' ausente no índice '{nome}'.")

        # Avançar mês
        mes_corrente += 1
        if mes_corrente > 12:
            mes_corrente = 1
            ano_corrente += 1

    return fator.quantize(Decimal("0.000001")), alertas
