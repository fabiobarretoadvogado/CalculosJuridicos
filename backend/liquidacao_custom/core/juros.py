"""
Módulo de cálculo de juros moratórios.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from liquidacao_custom.core.indices import carregar_indice, consultar_indice
from liquidacao_custom.core.models import ConfigJuros, MemoriaMensal, TipoJuros


def contar_meses(data_inicial: date, data_final: date, mes_cheio: bool = True) -> Decimal:
    """
    Conta o número de meses entre duas datas.
    Se mes_cheio for True, frações de mês contam como mês inteiro (arredondamento comum).
    Se for False, faz cálculo proporcional pro rata die.
    """
    if data_inicial >= data_final:
        return Decimal("0")

    diferenca_anos = data_final.year - data_inicial.year
    diferenca_meses = data_final.month - data_inicial.month
    total_meses = diferenca_anos * 12 + diferenca_meses

    if mes_cheio:
        if data_final.day > data_inicial.day:
            total_meses += 1
        return Decimal(max(total_meses, 1))

    # Pro rata die
    dias_periodo = (data_final - data_inicial).days
    # Média aproximada de dias num mês
    return (Decimal(dias_periodo) / Decimal("30.4368")).quantize(Decimal("0.000001"))


def calcular_juros(
    valor_base: Decimal,
    valor_corrigido: Decimal,
    periodos: list[ConfigJuros],
    data_base: date,
) -> dict:
    """
    Calcula os juros moratórios sobre o valor.
    """
    alertas: list[str] = []
    memoria_mensal: list[MemoriaMensal] = []
    total_juros = Decimal("0")

    for pj in periodos:
        if pj.tipo == TipoJuros.SEM_JUROS:
            continue

        data_ini = pj.data_inicial
        data_fim = pj.data_final or data_base

        if not data_ini:
            alertas.append(f"Período de juros sem data inicial informada. Ignorando.")
            continue

        base_calculo = valor_corrigido if pj.incide_sobre_corrigido else valor_base

        if pj.tipo == TipoJuros.PERCENTUAL_MENSAL_SIMPLES:
            meses = contar_meses(data_ini, data_fim, pj.contagem_mes_cheio)
            taxa_total = (pj.percentual / Decimal("100")) * meses
            juros_periodo = base_calculo * taxa_total
            total_juros += juros_periodo

            memoria_mensal.append(MemoriaMensal(
                competencia=f"{data_ini.year:04d}-{data_ini.month:02d}",
                valor_base=base_calculo,
                indice_aplicado=f"{pj.percentual}% a.m. simples",
                fator_aplicado=taxa_total,
                valor_corrigido=base_calculo,
                juros_periodo=juros_periodo,
                juros_acumulados=total_juros,
                total=base_calculo + total_juros,
                observacao=f"Juros simples de {data_ini} a {data_fim} ({meses:.2f} meses)"
            ))

        elif pj.tipo == TipoJuros.PERCENTUAL_MENSAL_COMPOSTO:
            meses = contar_meses(data_ini, data_fim, pj.contagem_mes_cheio)
            fator_base = Decimal("1") + (pj.percentual / Decimal("100"))
            fator_composto = (meses * fator_base.ln()).exp()
            juros_periodo = base_calculo * (fator_composto - Decimal("1"))
            total_juros += juros_periodo

            memoria_mensal.append(MemoriaMensal(
                competencia=f"{data_ini.year:04d}-{data_ini.month:02d}",
                valor_base=base_calculo,
                indice_aplicado=f"{pj.percentual}% a.m. composto",
                fator_aplicado=fator_composto - Decimal("1"),
                valor_corrigido=base_calculo,
                juros_periodo=juros_periodo,
                juros_acumulados=total_juros,
                total=base_calculo + total_juros,
                observacao=f"Juros compostos de {data_ini} a {data_fim} ({meses:.2f} meses)"
            ))

        elif pj.tipo == TipoJuros.SELIC:
            # Acumula juros pela taxa SELIC
            indices_selic = carregar_indice("selic")
            fator_acum = Decimal("0")
            ano_corrente = data_ini.year
            mes_corrente = data_ini.month

            while date(ano_corrente, mes_corrente, 1) < date(data_fim.year, data_fim.month, 1):
                comp = f"{ano_corrente:04d}-{mes_corrente:02d}"
                if comp in indices_selic:
                    fator_acum += indices_selic[comp][0] / Decimal("100")
                else:
                    alertas.append(f"Competência SELIC '{comp}' ausente.")
                mes_corrente += 1
                if mes_corrente > 12:
                    mes_corrente = 1
                    ano_corrente += 1

            juros_periodo = base_calculo * fator_acum
            total_juros += juros_periodo

            memoria_mensal.append(MemoriaMensal(
                competencia=f"{data_ini.year:04d}-{data_ini.month:02d}",
                valor_base=base_calculo,
                indice_aplicado="SELIC (Juros)",
                fator_aplicado=fator_acum,
                valor_corrigido=base_calculo,
                juros_periodo=juros_periodo,
                juros_acumulados=total_juros,
                total=base_calculo + total_juros,
                observacao=f"Juros SELIC acumulada de {data_ini} a {data_fim}"
            ))

        elif pj.tipo == TipoJuros.TAXA_LEGAL:
            # Acumula juros pela Taxa Legal (1% ao mês ou IPCA + 6% conforme nova lei/config)
            indices_tl = carregar_indice("taxa_legal")
            fator_acum = Decimal("0")
            ano_corrente = data_ini.year
            mes_corrente = data_ini.month

            while date(ano_corrente, mes_corrente, 1) < date(data_fim.year, data_fim.month, 1):
                comp = f"{ano_corrente:04d}-{mes_corrente:02d}"
                if comp in indices_tl:
                    fator_acum += indices_tl[comp][0] / Decimal("100")
                else:
                    # Fallback para 1% ao mês se não houver
                    fator_acum += Decimal("0.01")
                mes_corrente += 1
                if mes_corrente > 12:
                    mes_corrente = 1
                    ano_corrente += 1

            juros_periodo = base_calculo * fator_acum
            total_juros += juros_periodo

            memoria_mensal.append(MemoriaMensal(
                competencia=f"{data_ini.year:04d}-{data_ini.month:02d}",
                valor_base=base_calculo,
                indice_aplicado="Taxa Legal",
                fator_aplicado=fator_acum,
                valor_corrigido=base_calculo,
                juros_periodo=juros_periodo,
                juros_acumulados=total_juros,
                total=base_calculo + total_juros,
                observacao=f"Juros Taxa Legal acumulada de {data_ini} a {data_fim}"
            ))

        elif pj.tipo == TipoJuros.POUPANCA:
            # Poupança: MVP estruturado (0.5% + TR, usando TR como 0% fictício no MVP)
            meses = contar_meses(data_ini, data_fim, pj.contagem_mes_cheio)
            taxa_total = Decimal("0.005") * meses  # 0.5% ao mês
            juros_periodo = base_calculo * taxa_total
            total_juros += juros_periodo
            alertas.append(f"Nota: Poupança calculada de forma simplificada a 0.5% a.m. para o MVP.")

            memoria_mensal.append(MemoriaMensal(
                competencia=f"{data_ini.year:04d}-{data_ini.month:02d}",
                valor_base=base_calculo,
                indice_aplicado="Poupança (0.5% a.m.)",
                fator_aplicado=taxa_total,
                valor_corrigido=base_calculo,
                juros_periodo=juros_periodo,
                juros_acumulados=total_juros,
                total=base_calculo + total_juros,
                observacao=f"Juros Poupança de {data_ini} a {data_fim}"
            ))

        elif pj.tipo == TipoJuros.TAXA_MANUAL:
            meses = contar_meses(data_ini, data_fim, pj.contagem_mes_cheio)
            taxa_mensal = pj.taxa_manual_mensal or Decimal("0")
            taxa_total = (taxa_mensal / Decimal("100")) * meses
            juros_periodo = base_calculo * taxa_total
            total_juros += juros_periodo

            memoria_mensal.append(MemoriaMensal(
                competencia=f"{data_ini.year:04d}-{data_ini.month:02d}",
                valor_base=base_calculo,
                indice_aplicado=f"{taxa_mensal}% a.m. manual",
                fator_aplicado=taxa_total,
                valor_corrigido=base_calculo,
                juros_periodo=juros_periodo,
                juros_acumulados=total_juros,
                total=base_calculo + total_juros,
                observacao=f"Juros manuais de {data_ini} a {data_fim}"
            ))

    return {
        "valor_juros": total_juros.quantize(Decimal("0.01")),
        "memoria_mensal": memoria_mensal,
        "alertas": alertas,
    }
