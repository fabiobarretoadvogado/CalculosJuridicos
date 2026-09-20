"""
Módulo de carregamento e consulta de índices econômicos de correção monetária.
"""

from __future__ import annotations

import csv
import os
from datetime import date
from decimal import Decimal
from typing import Optional


# Diretório base para os arquivos de dados
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data", "indices")

# Cache global para evitar leituras de disco repetidas
_cache_indices: dict[str, dict[str, tuple[Decimal, Decimal]]] = {}


def _normalizar_nome_indice(nome: str) -> str:
    """Normaliza o nome do índice para corresponder ao nome do arquivo CSV."""
    nome = nome.lower().replace("-", "").replace("_", "")
    if nome == "ipcae":
        return "ipcae"
    return nome


def carregar_indice(nome: str) -> dict[str, tuple[Decimal, Decimal]]:
    """
    Carrega o índice do CSV correspondente e retorna um dicionário indexado pela competência.
    Retorna: { "AAAA-MM": (percentual, fator) }
    """
    nome_norm = _normalizar_nome_indice(nome)
    if nome_norm in _cache_indices:
        return _cache_indices[nome_norm]

    caminho = os.path.join(DATA_DIR, f"{nome_norm}.csv")
    dados: dict[str, tuple[Decimal, Decimal]] = {}

    if not os.path.exists(caminho):
        # Retorna dicionário vazio caso o arquivo de índice não exista (será alertado)
        return dados

    with open(caminho, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            comp = row["competencia"].strip()
            perc = Decimal(row["percentual"].strip())
            fat = Decimal(row["fator"].strip())
            dados[comp] = (perc, fat)

    _cache_indices[nome_norm] = dados
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
