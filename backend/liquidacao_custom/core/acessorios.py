"""
Módulo de acessórios do cálculo judicial.

Calcula honorários, multa do art. 523 CPC, custas e despesas processuais.
"""

from __future__ import annotations

import csv
import os
from datetime import date
from decimal import Decimal
from typing import Optional

from liquidacao_custom.core.models import (
    Astreintes,
    BaseCalculo,
    CustaDespesa,
    Honorarios,
    IndiceCorrecao,
    MultaAdicional,
    MultaCPC523,
    ResultadoParcela,
    TipoDevedor,
)


def _resolver_base_calculo(
    config_base: BaseCalculo,
    parcelas_resultado: list[ResultadoParcela],
    parcela_especifica: Optional[int] = None,
    valor_manual_base: Optional[Decimal] = None,
) -> Decimal:
    """Resolve o valor da base de cálculo conforme configuração."""
    if config_base == BaseCalculo.SUBTOTAL_PARCELAS:
        return sum((p.valor_apurado for p in parcelas_resultado), Decimal("0"))

    if config_base == BaseCalculo.SUBTOTAL_ATUALIZADO:
        return sum((p.total_parcela for p in parcelas_resultado), Decimal("0"))

    if config_base == BaseCalculo.PRINCIPAL_CORRIGIDO:
        return sum((p.valor_corrigido for p in parcelas_resultado), Decimal("0"))

    if config_base == BaseCalculo.JUROS:
        return sum((p.juros_mora for p in parcelas_resultado), Decimal("0"))

    if config_base == BaseCalculo.PARCELA_ESPECIFICA:
        if parcela_especifica is not None:
            for p in parcelas_resultado:
                if p.numero == parcela_especifica:
                    return p.total_parcela
        return Decimal("0")

    if config_base == BaseCalculo.VALOR_MANUAL:
        return valor_manual_base or Decimal("0")

    return Decimal("0")


def _salario_minimo_para_ano(ano: int) -> Decimal | None:
    caminho = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
        "salario_minimo.csv",
    )
    if not os.path.exists(caminho):
        return None

    salarios: dict[int, Decimal] = {}
    with open(caminho, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            salarios[int(row["ano"].strip())] = Decimal(row["valor"].strip())

    if ano in salarios:
        return salarios[ano]
    anos_anteriores = [ano_sm for ano_sm in salarios if ano_sm <= ano]
    if anos_anteriores:
        return salarios[max(anos_anteriores)]
    return None


def _calcular_honorarios_escalonados_fazenda(
    config: Honorarios,
    base: Decimal,
    data_base: date,
) -> tuple[Decimal, Decimal, list[dict], list[str]]:
    alertas: list[str] = []
    salario_minimo = config.salario_minimo or _salario_minimo_para_ano(data_base.year)
    if not salario_minimo or salario_minimo <= Decimal("0"):
        alertas.append("Salário mínimo não informado para escalonamento dos honorários da Fazenda Pública.")
        return Decimal("0"), Decimal("0"), [], alertas

    if config.salario_minimo is None:
        alertas.append(f"Salário mínimo usado no escalonamento: R$ {salario_minimo:.2f}.")

    total = Decimal("0")
    detalhes: list[dict] = []
    limite_anterior = Decimal("0")
    faixas = sorted(config.faixas_escalonamento, key=lambda faixa: faixa.ordem)

    for faixa in faixas:
        limite_atual = None
        if faixa.limite_salarios_minimos is not None:
            limite_atual = faixa.limite_salarios_minimos * salario_minimo

        if limite_atual is None:
            valor_incidente = max(base - limite_anterior, Decimal("0"))
        else:
            valor_incidente = max(min(base, limite_atual) - limite_anterior, Decimal("0"))

        percentual = faixa.percentual_aplicado
        valor_faixa = Decimal("0")
        if valor_incidente > Decimal("0") and percentual is not None:
            if percentual < faixa.percentual_minimo or percentual > faixa.percentual_maximo:
                alertas.append(
                    f"Percentual da faixa {faixa.ordem} fora do intervalo legal "
                    f"({faixa.percentual_minimo}% a {faixa.percentual_maximo}%)."
                )
            valor_faixa = (valor_incidente * percentual / Decimal("100")).quantize(Decimal("0.01"))

        detalhes.append({
            "ordem": faixa.ordem,
            "limite_salarios_minimos": faixa.limite_salarios_minimos,
            "percentual_minimo": faixa.percentual_minimo,
            "percentual_maximo": faixa.percentual_maximo,
            "percentual_aplicado": percentual,
            "valor_incidente": valor_incidente.quantize(Decimal("0.01")),
            "valor": valor_faixa,
        })
        total += valor_faixa

        if limite_atual is not None:
            limite_anterior = limite_atual
        if base <= limite_anterior and limite_atual is not None:
            continue

    return total.quantize(Decimal("0.01")), salario_minimo, detalhes, alertas


def calcular_honorarios(
    config: Honorarios,
    parcelas_resultado: list[ResultadoParcela],
    data_base: date,
) -> dict:
    """
    Calcula honorários advocatícios.

    Retorna:
        dict com 'valor', 'base_calculo_valor', 'descricao', 'detalhes'
    """
    base = _resolver_base_calculo(
        config.base_calculo,
        parcelas_resultado,
        config.parcela_especifica,
        config.valor_manual_base,
    )

    alertas: list[str] = []
    salario_minimo = None
    faixas_detalhes: list[dict] = []

    if config.escalonar_fazenda_publica:
        valor, salario_minimo, faixas_detalhes, alertas = _calcular_honorarios_escalonados_fazenda(
            config,
            base,
            data_base,
        )
    elif config.valor_fixo is not None:
        valor = config.valor_fixo
    elif config.percentual is not None:
        valor = base * config.percentual / Decimal("100")
    else:
        valor = Decimal("0")

    return {
        "valor": valor.quantize(Decimal("0.01")),
        "base_calculo_valor": base.quantize(Decimal("0.01")),
        "tipo": config.tipo.value,
        "descricao": config.descricao,
        "percentual": config.percentual,
        "valor_fixo": config.valor_fixo,
        "base_calculo": config.base_calculo.value,
        "escalonar_fazenda_publica": config.escalonar_fazenda_publica,
        "salario_minimo": salario_minimo,
        "faixas_escalonamento": faixas_detalhes,
        "alertas": alertas,
        "detalhes": f"{config.descricao}: {config.percentual or 0}% sobre {config.base_calculo.value} = R$ {valor.quantize(Decimal('0.01'))}",
    }


def calcular_multa_cpc523(
    config: MultaCPC523,
    parcelas_resultado: list[ResultadoParcela],
    tipo_devedor: TipoDevedor = TipoDevedor.PRIVADO,
) -> dict:
    """
    Calcula multa do art. 523 do CPC e honorários de cumprimento.

    Retorna:
        dict com 'multa', 'honorarios_523', 'base_calculo_valor', 'alertas'
    """
    alertas: list[str] = []

    if not config.aplicar_multa and not config.aplicar_honorarios:
        return {
            "multa": Decimal("0"),
            "honorarios_523": Decimal("0"),
            "base_calculo_valor": Decimal("0"),
            "alertas": alertas,
        }

    # Alerta para Fazenda Pública
    if tipo_devedor == TipoDevedor.FAZENDA_PUBLICA:
        alertas.append(
            "ALERTA: Multa do art. 523 do CPC aplicada contra Fazenda Pública. "
            "Verificar se a incidência é cabível conforme jurisprudência."
        )

    base = _resolver_base_calculo(
        config.base_calculo,
        parcelas_resultado,
    )

    multa = Decimal("0")
    honorarios_523 = Decimal("0")
    if config.aplicar_multa:
        multa = base * config.percentual_multa / Decimal("100")
    if config.aplicar_honorarios:
        honorarios_523 = base * config.percentual_honorarios / Decimal("100")

    return {
        "multa": multa.quantize(Decimal("0.01")),
        "honorarios_523": honorarios_523.quantize(Decimal("0.01")),
        "base_calculo_valor": base.quantize(Decimal("0.01")),
        "alertas": alertas,
    }


def calcular_multas_adicionais(
    configs: list[MultaAdicional],
    parcelas_resultado: list[ResultadoParcela],
) -> dict:
    """Calcula multas configuráveis pelo usuário."""
    detalhes: list[dict] = []
    total = Decimal("0")

    for config in configs:
        base = _resolver_base_calculo(
            config.base_calculo,
            parcelas_resultado,
            config.parcela_especifica,
            config.valor_manual_base,
        )
        if config.valor_fixo is not None:
            valor = config.valor_fixo
        elif config.percentual is not None:
            valor = base * config.percentual / Decimal("100")
        else:
            valor = Decimal("0")

        valor = valor.quantize(Decimal("0.01"))
        total += valor
        detalhes.append({
            "descricao": config.descricao,
            "valor": valor,
            "base_calculo_valor": base.quantize(Decimal("0.01")),
            "percentual": config.percentual,
            "valor_fixo": config.valor_fixo,
            "base_calculo": config.base_calculo.value,
            "observacao": config.observacao,
            "detalhes": f"{config.descricao}: {config.percentual or 0}% sobre {config.base_calculo.value} = R$ {valor}",
        })

    return {
        "total": total.quantize(Decimal("0.01")),
        "detalhes": detalhes,
    }


def calcular_custas_despesas(
    itens: list[CustaDespesa],
    data_base: date,
) -> dict:
    """
    Calcula custas e despesas processuais, com correção simples se configurada.

    Para o MVP, aplica correção simples por fator acumulado quando disponível.

    Retorna:
        dict com 'itens_calculados', 'total', 'alertas'
    """
    alertas: list[str] = []
    itens_calculados: list[dict] = []
    total = Decimal("0")

    for item in itens:
        valor_atualizado = item.valor

        # Se tem correção configurada, tenta aplicar
        if item.correcao_monetaria != IndiceCorrecao.SEM_CORRECAO and item.data_inicial_correcao:
            try:
                from liquidacao_custom.core.correcao import calcular_correcao
                from liquidacao_custom.core.models import PeriodoCorrecao

                periodo = PeriodoCorrecao(
                    indice=item.correcao_monetaria,
                    data_inicial=item.data_inicial_correcao,
                    data_final=data_base,
                )
                resultado = calcular_correcao(item.valor, [periodo], data_base)
                valor_atualizado = resultado["valor_corrigido"]
                alertas.extend(resultado.get("alertas", []))
            except Exception as e:
                alertas.append(
                    f"Erro ao corrigir custa/despesa '{item.historico}': {e}"
                )

        item_calc = {
            "historico": item.historico,
            "data": item.data,
            "valor_original": item.valor.quantize(Decimal("0.01")),
            "valor_atualizado": valor_atualizado.quantize(Decimal("0.01")),
            "correcao": item.correcao_monetaria.value,
            "observacao": item.observacao,
        }
        itens_calculados.append(item_calc)
        total += valor_atualizado

    return {
        "itens_calculados": itens_calculados,
        "total": total.quantize(Decimal("0.01")),
        "alertas": alertas,
    }


def calcular_astreintes(
    itens: list[Astreintes],
    data_base: date,
) -> dict:
    """
    Calcula astreintes (multa cominatória).

    Retorna:
        dict com 'total', 'itens_calculados', 'alertas'
    """
    alertas: list[str] = []
    itens_calculados: list[dict] = []
    total = Decimal("0")

    for item in itens:
        valor = item.valor
        if item.valor_diario and item.data_inicial and item.data_final:
            dias = (item.data_final - item.data_inicial).days
            if dias > 0:
                valor = item.valor_diario * Decimal(str(dias))

        itens_calculados.append({
            "historico": item.historico,
            "valor": valor.quantize(Decimal("0.01")),
            "observacao": item.observacao,
        })
        total += valor

    return {
        "total": total.quantize(Decimal("0.01")),
        "itens_calculados": itens_calculados,
        "alertas": alertas,
    }
