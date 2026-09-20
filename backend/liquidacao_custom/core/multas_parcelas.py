"""Multa percentual por parcela, com os mesmos encargos e marcos da parcela."""
from decimal import Decimal

from .criterios_simplificados import CalculoSimplificado, ParcelaSimplificada
from .models import ComponenteCalculo, ResultadoMultaParcela


def incorporar_multas_parcelas(resultado, calculo):
    from .motor_simplificado import executar_calculo, moeda

    entradas = {p.numero: p for p in calculo.parcelas}
    if not any(p.multa_percentual for p in calculo.parcelas):
        return resultado
    originais = {
        p.numero: moeda((p.valor_bruto - p.valor_pago_na_data) * p.multa_percentual / 100)
        for p in calculo.parcelas
    }
    # Operação autônoma sem multa recursiva, descontos ou custas: reutiliza o
    # próprio perfil para manter contagem, SELIC única e limite EC 136 idênticos.
    parcelas_multas = [ParcelaSimplificada(
        numero=p.numero, historico=f"Multa da parcela {p.numero}",
        data_vencimento=p.data_vencimento, valor_bruto=originais[p.numero],
        data_inicial_juros=p.data_inicial_juros,
    ) for p in calculo.parcelas if originais[p.numero] > 0]
    apuradas = {}
    if parcelas_multas:
        multas = executar_calculo(CalculoSimplificado(
            perfil=calculo.perfil, dados_gerais=calculo.dados_gerais,
            parcelas=parcelas_multas,
        ))
        apuradas = {p.numero: p for p in multas.parcelas}
        resultado.alertas.extend(f"Multas: {a}" for a in multas.alertas)
    for parcela in resultado.parcelas:
        entrada = entradas[parcela.numero]
        parcela.componentes["multa_parcela"] = ComponenteCalculo()
        if not entrada.multa_percentual:
            continue
        apurada = apuradas.get(parcela.numero)
        original = originais[parcela.numero]
        memoria = [m.model_copy(update={
            "indice_aplicado": f"Multa - {m.indice_aplicado}",
            "observacao": f"Multa da parcela {parcela.numero}; {m.observacao}",
        }) for m in (apurada.memoria_correcao + apurada.memoria_juros if apurada else [])]
        detalhes = ResultadoMultaParcela(
            percentual=entrada.multa_percentual, base_calculo=parcela.valor_apurado,
            valor_original=original,
            correcao_monetaria=apurada.correcao_monetaria if apurada else 0,
            juros_mora=apurada.juros_mora if apurada else 0,
            total_atualizado=apurada.total_parcela if apurada else 0,
            componentes=apurada.componentes if apurada else {}, memoria=memoria,
        )
        parcela.multa_detalhes = detalhes
        parcela.multa = detalhes.total_atualizado
        parcela.total_parcela = moeda(parcela.total_parcela + parcela.multa)
        parcela.componentes["multa_parcela"] = ComponenteCalculo(
            data_inicial=entrada.data_vencimento, data_final=calculo.dados_gerais.data_base,
            base_calculo=parcela.valor_apurado,
            taxa_acumulada_percentual=entrada.multa_percentual, valor=parcela.multa,
        )
        resultado.memoria_mensal.extend(memoria)
    total = sum((p.multa for p in resultado.parcelas), Decimal(0))
    resultado.resumo.multas = total
    resultado.resumo.totais_componentes["multa_parcela"] = total
    resultado.resumo.total_atualizado = moeda(resultado.resumo.total_atualizado + total)
    resultado.premissas.setdefault("criterios", []).append(
        "Multa percentual por parcela sobre o saldo após pagamento no vencimento; "
        "a multa recebe a atualização e os juros do mesmo perfil e marcos da parcela."
    )
    resultado.premissas["metodologia"] = [
        nota.replace("Total = principal + SELIC.",
                     "Total da parcela = principal + SELIC + multa e encargos.")
        for nota in resultado.premissas.get("metodologia", [])
    ]
    resultado.premissas.setdefault("metodologia", []).append(
        "Multa nominal = saldo da parcela no vencimento × percentual informado / 100, "
        "arredondada ao centavo (HALF_UP). A multa nominal é atualizada em operação "
        "autônoma desde o vencimento, com os mesmos índices, início dos juros e regras "
        "de contagem da parcela. Incidem juros sobre a multa, sem nova capitalização "
        "ou duplicação da SELIC. O eventual limite EC 136 também é respeitado. "
        "A coluna Multa e encargos soma multa nominal, atualização e juros próprios; "
        "suas bases, índices e períodos são discriminados em tabela própria. "
        "O total da parcela inclui o saldo, seus encargos e a multa com seus próprios encargos. "
        "O saldo exibido no formulário permanece anterior à multa e à atualização. "
        "Descontos são abatidos depois e custas não compõem a base da multa."
    )
    return resultado
