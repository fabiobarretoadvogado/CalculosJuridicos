"""
Módulo de preenchimento de parcelas em série e por percentual de salário mínimo.
"""

from __future__ import annotations

import csv
import os
from datetime import date
from decimal import Decimal
from typing import Optional

from liquidacao_custom.core.models import (
    ConfigPreenchimentoSerie,
    ConfigSalarioMinimo,
    IndiceCorrecao,
    Parcela,
    Periodicidade,
    TipoJuros,
)


def _avancar_data(data_atual: date, periodicidade: Periodicidade) -> date:
    """Avança a data atual com base no período selecionado."""
    if periodicidade == Periodicidade.MENSAL:
        mes = data_atual.month + 1
        ano = data_atual.year
        if mes > 12:
            mes = 1
            ano += 1
        return date(ano, mes, min(data_atual.day, 28))
    elif periodicidade == Periodicidade.BIMESTRAL:
        mes = data_atual.month + 2
        ano = data_atual.year
        if mes > 12:
            mes -= 12
            ano += 1
        return date(ano, mes, min(data_atual.day, 28))
    elif periodicidade == Periodicidade.TRIMESTRAL:
        mes = data_atual.month + 3
        ano = data_atual.year
        if mes > 12:
            mes -= 12
            ano += 1
        return date(ano, mes, min(data_atual.day, 28))
    elif periodicidade == Periodicidade.ANUAL:
        return date(data_atual.year + 1, data_atual.month, min(data_atual.day, 28))
    return data_atual


def gerar_serie(config: ConfigPreenchimentoSerie) -> list[Parcela]:
    """Gera parcelas repetitivas baseado em parâmetros fixos."""
    parcelas: list[Parcela] = []
    data_corrente = config.data_inicial

    # Ajusta o dia do vencimento se aplicável
    try:
        data_corrente = date(data_corrente.year, data_corrente.month, config.dia_vencimento)
    except ValueError:
        data_corrente = date(data_corrente.year, data_corrente.month, 28)

    numero = 1
    while data_corrente <= config.data_final:
        parcela = Parcela(
            numero=numero,
            natureza=config.natureza,
            data_vencimento=data_corrente,
            historico=f"{config.historico_padrao} ({data_corrente.strftime('%m/%Y')})",
            valor_bruto=config.valor_fixo,
            valor_pago_na_data=Decimal("0"),
            correcao_monetaria=config.correcao_monetaria,
            data_inicial_correcao=config.data_inicial_correcao or data_corrente,
            juros_moratorios=config.juros_moratorios,
            data_inicial_juros=config.data_inicial_juros or data_corrente,
            percentual_juros=config.percentual_juros,
            multa_moratoria=config.multa_moratoria,
            observacao=""
        )
        parcela.recalcular_apurado()
        parcelas.append(parcela)

        # Avançar data
        data_corrente = _avancar_data(data_corrente, config.periodicidade)
        try:
            data_corrente = date(data_corrente.year, data_corrente.month, config.dia_vencimento)
        except ValueError:
            data_corrente = date(data_corrente.year, data_corrente.month, 28)

        numero += 1

    return parcelas


def carregar_salario_minimo() -> dict[int, Decimal]:
    """Carrega dados do salário mínimo do CSV."""
    caminho = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data", "salario_minimo.csv"
    )
    sm: dict[int, Decimal] = {}
    if not os.path.exists(caminho):
        return sm

    with open(caminho, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ano = int(row["ano"].strip())
            val = Decimal(row["valor"].strip())
            sm[ano] = val
    return sm


def gerar_serie_salario_minimo(config: ConfigSalarioMinimo) -> tuple[list[Parcela], list[str]]:
    """Gera parcelas com base em percentual do salário mínimo histórico."""
    parcelas: list[Parcela] = []
    alertas: list[str] = []
    sm_dict = carregar_salario_minimo()

    data_corrente = config.data_inicial
    try:
        data_corrente = date(data_corrente.year, data_corrente.month, config.dia_vencimento)
    except ValueError:
        data_corrente = date(data_corrente.year, data_corrente.month, 28)

    numero = 1
    ultimo_valor_conhecido = Decimal("1212.00")  # Fallback razoável

    while data_corrente <= config.data_final:
        ano = data_corrente.year
        if ano in sm_dict:
            valor_sm = sm_dict[ano]
        else:
            valor_sm = ultimo_valor_conhecido
            alertas.append(f"ALERTA: Salário mínimo ausente para o ano {ano}. Usando R$ {valor_sm:.2f}.")

        ultimo_valor_conhecido = valor_sm
        valor_calculado = (valor_sm * config.percentual / Decimal("100")).quantize(Decimal("0.01"))

        parcela = Parcela(
            numero=numero,
            natureza=config.natureza,
            data_vencimento=data_corrente,
            historico=f"{config.historico} ({config.percentual}% de R$ {valor_sm:.2f})",
            valor_bruto=valor_calculado,
            valor_pago_na_data=Decimal("0"),
            correcao_monetaria=config.correcao_monetaria,
            data_inicial_correcao=data_corrente,
            juros_moratorios=config.juros_moratorios,
            data_inicial_juros=data_corrente,
            percentual_juros=config.percentual_juros,
            multa_moratoria=config.multa_moratoria,
            observacao=""
        )
        parcela.recalcular_apurado()
        parcelas.append(parcela)

        data_corrente = _avancar_data(data_corrente, config.periodicidade)
        try:
            data_corrente = date(data_corrente.year, data_corrente.month, config.dia_vencimento)
        except ValueError:
            data_corrente = date(data_corrente.year, data_corrente.month, 28)

        numero += 1

    return parcelas, alertas
