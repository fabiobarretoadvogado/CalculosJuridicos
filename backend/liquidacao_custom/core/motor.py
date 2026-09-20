"""
Motor de cálculo principal do sistema liquidacao-custom.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from liquidacao_custom.core.models import (
    CalculoJudicial,
    FormaImputacao,
    IndiceCorrecao,
    MemoriaMensal,
    ResultadoCalculo,
    ResultadoParcela,
    ResumoGeral,
    TipoJuros,
    PeriodoCorrecao,
    ConfigJuros,
)
from liquidacao_custom.core.correcao import calcular_correcao
from liquidacao_custom.core.juros import calcular_juros
from liquidacao_custom.core.acessorios import (
    calcular_honorarios,
    calcular_multa_cpc523,
    calcular_multas_adicionais,
    calcular_custas_despesas,
    calcular_astreintes,
)
from liquidacao_custom.core.abatimentos import aplicar_abatimentos
from liquidacao_custom.core.validacoes import validar_calculo


def executar_calculo(calculo: CalculoJudicial) -> ResultadoCalculo:
    """
    Executa a liquidação e atualização completa do débito.
    """
    alertas: list[str] = []
    data_base = calculo.dados_gerais.data_base
    tipo_devedor = calculo.dados_gerais.tipo_devedor

    # 1. Executa validações pré-cálculo
    alertas.extend(validar_calculo(calculo))

    # 2. Processa cada parcela
    resultados_parcelas: list[ResultadoParcela] = []
    todas_memorias: list[MemoriaMensal] = []

    principal_orig = Decimal("0")
    total_pago_na_data = Decimal("0")
    total_apurado_orig = Decimal("0")
    total_corr = Decimal("0")
    total_juros = Decimal("0")
    total_multa_parcelas = Decimal("0")

    for p in calculo.parcelas:
        p.recalcular_apurado()
        principal_orig += p.valor_bruto
        total_pago_na_data += p.valor_pago_na_data
        total_apurado_orig += p.valor_apurado

        periodos_correcao = p.get_periodos_correcao_efetivos(data_base)
        periodos_juros = p.get_periodos_juros_efetivos(data_base)

        # Verifica se há transição SELIC Fazenda Pública (EC 113)
        # Se configurado, altera dinamicamente os critérios a partir da data de transição
        if tipo_devedor == calculo.dados_gerais.tipo_devedor.FAZENDA_PUBLICA and calculo.config_selic_taxa_unica.aplicar:
            data_selic = calculo.config_selic_taxa_unica.data_inicio
            if data_selic:
                # Modifica as listas locais de períodos de correção/juros se necessário
                p_corr = periodos_correcao
                p_jur = periodos_juros

                # Ajusta período de transição
                # Período 1: até a transição (IPCA-E/etc. + Poupança/etc.)
                # Período 2: a partir da transição (SELIC como taxa única)
                # Trocamos pelo equivalente configurado para simplificar no motor
                
                novo_p_corr = []
                for item in p_corr:
                    if item.data_inicial and item.data_inicial < data_selic:
                        novo_p_corr.append(
                            item.model_copy(
                                update={"data_final": min(item.data_final or data_base, data_selic)}
                            )
                        )
                
                # Período SELIC
                datas_inicio_selic = [
                    data_selic,
                    *[item.data_inicial for item in p_corr if item.data_inicial],
                    *[item.data_inicial for item in p_jur if item.data_inicial],
                ]
                if p.data_vencimento:
                    datas_inicio_selic.append(p.data_vencimento)
                inicio_selic = max(datas_inicio_selic)

                if data_base >= inicio_selic:
                    novo_p_corr.append(
                        PeriodoCorrecao(
                            indice=IndiceCorrecao.SELIC,
                            data_inicial=inicio_selic,
                            data_final=data_base,
                        )
                    )
                periodos_correcao = novo_p_corr

                # Ajustar juros da mesma forma
                novo_p_jur = []
                for item in p_jur:
                    if item.data_inicial and item.data_inicial < data_selic:
                        novo_p_jur.append(
                            item.model_copy(
                                update={"data_final": min(item.data_final or data_base, data_selic)}
                            )
                        )
                # A SELIC única já inclui juros, portanto a partir da data da transição juros = SEM_JUROS
                periodos_juros = novo_p_jur

        # Cálculo da correção
        res_corr = calcular_correcao(p.valor_apurado, periodos_correcao, data_base)
        valor_corrigido = res_corr["valor_corrigido"]
        fator_corr = res_corr["fator_acumulado"]
        alertas.extend(res_corr.get("alertas", []))

        # Cálculo dos juros
        res_jur = calcular_juros(p.valor_apurado, valor_corrigido, periodos_juros, data_base)
        valor_juros = res_jur["valor_juros"]
        alertas.extend(res_jur.get("alertas", []))

        # Multa da parcela
        multa_valor = (valor_corrigido * p.multa_moratoria / Decimal("100")).quantize(Decimal("0.01"))

        total_parcela = valor_corrigido + valor_juros + multa_valor

        # Consolida memórias mensais
        for m in res_corr["memoria_mensal"]:
            m.parcela = p.numero
            todas_memorias.append(m)

        for m in res_jur["memoria_mensal"]:
            m.parcela = p.numero
            # Evita duplicar registros se forem na mesma competência
            todas_memorias.append(m)

        res_p = ResultadoParcela(
            numero=p.numero,
            natureza=p.natureza,
            historico=p.historico,
            data_vencimento=p.data_vencimento,
            valor_bruto=p.valor_bruto,
            valor_pago_na_data=p.valor_pago_na_data,
            valor_apurado=p.valor_apurado,
            correcao_monetaria=valor_corrigido - p.valor_apurado,
            valor_corrigido=valor_corrigido,
            juros_mora=valor_juros,
            multa=multa_valor,
            total_parcela=total_parcela,
            memoria_correcao=res_corr["memoria_mensal"],
            memoria_juros=res_jur["memoria_mensal"],
            alertas=[],
        )
        resultados_parcelas.append(res_p)

        total_corr += (valor_corrigido - p.valor_apurado)
        total_juros += valor_juros
        total_multa_parcelas += multa_valor

    # 3. Custas e Despesas
    custas_res = calcular_custas_despesas(calculo.custas, data_base)
    despesas_res = calcular_custas_despesas(calculo.despesas, data_base)
    alertas.extend(custas_res["alertas"])
    alertas.extend(despesas_res["alertas"])

    # 4. Astreintes
    astreintes_res = calcular_astreintes(calculo.astreintes, data_base)
    alertas.extend(astreintes_res["alertas"])

    # 5. Aplica Abatimentos posteriores
    total_sub_parcelas = sum((rp.total_parcela for rp in resultados_parcelas), Decimal("0"))
    res_abat = aplicar_abatimentos(resultados_parcelas, calculo.abatimentos, total_sub_parcelas, data_base)
    alertas.extend(res_abat["alertas"])

    # Atualiza as parcelas com os saldos abatidos
    resultados_parcelas = res_abat["parcelas_ajustadas"]
    total_final_parcelas = sum((rp.total_parcela for rp in resultados_parcelas), Decimal("0"))

    # 6. Honorários
    hon_detalhes = []
    total_honorarios = Decimal("0")
    total_honorarios_contratuais = Decimal("0")
    for hon_config in calculo.honorarios:
        res_hon = calcular_honorarios(hon_config, resultados_parcelas, data_base)
        alertas.extend(res_hon.get("alertas", []))
        total_honorarios += res_hon["valor"]
        if res_hon["tipo"] == "contratuais":
            total_honorarios_contratuais += res_hon["valor"]
        hon_detalhes.append(res_hon)

    # Multa do art. 523 CPC
    res_multa523 = calcular_multa_cpc523(calculo.multa_cpc523, resultados_parcelas, tipo_devedor)
    alertas.extend(res_multa523["alertas"])
    total_multa_cpc = res_multa523["multa"]
    total_honorarios += res_multa523["honorarios_523"]

    # Multas configuráveis pelo usuário (ex.: litigância de má-fé, embargos protelatórios)
    res_multas_adicionais = calcular_multas_adicionais(calculo.multas_adicionais, resultados_parcelas)
    total_multas_adicionais = res_multas_adicionais["total"]

    # 7. Resumo Geral
    resumo = ResumoGeral(
        principal_original=principal_orig.quantize(Decimal("0.01")),
        valor_pago_na_data_parcelas=total_pago_na_data.quantize(Decimal("0.01")),
        principal_apurado=total_apurado_orig.quantize(Decimal("0.01")),
        correcao_monetaria=total_corr.quantize(Decimal("0.01")),
        juros_mora=total_juros.quantize(Decimal("0.01")),
        multas=(total_multa_parcelas + total_multa_cpc + total_multas_adicionais + astreintes_res["total"]).quantize(Decimal("0.01")),
        honorarios=total_honorarios.quantize(Decimal("0.01")),
        custas=custas_res["total"],
        despesas=despesas_res["total"],
        abatimentos=res_abat["total_abatido"],
        total_atualizado=(
            total_final_parcelas +
            total_multa_cpc +
            total_multas_adicionais +
            total_honorarios +
            custas_res["total"] +
            despesas_res["total"] +
            astreintes_res["total"]
        ).quantize(Decimal("0.01"))
    )

    return ResultadoCalculo(
        dados_gerais=calculo.dados_gerais,
        resumo=resumo,
        parcelas=resultados_parcelas,
        memoria_mensal=todas_memorias,
        memorias_abatimento=res_abat["memorias"],
        honorarios_detalhes=hon_detalhes,
        alertas=alertas,
        premissas={
            "data_base": data_base,
            "tipo_devedor": tipo_devedor.value,
            "config_taxa_legal": calculo.config_taxa_legal.model_dump(),
            "config_selic_taxa_unica": calculo.config_selic_taxa_unica.model_dump(),
            "honorarios_contratuais_destacados": total_honorarios_contratuais.quantize(Decimal("0.01")),
        }
    )
