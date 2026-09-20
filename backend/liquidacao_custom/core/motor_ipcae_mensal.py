"""Correção mensal exclusiva pelo IPCA-E, com memória rastreável por parcela."""
import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from .models import ComponenteCalculo, DadosGerais, MemoriaMensal, Parcela, ResultadoCalculo, ResultadoParcela, ResumoGeral
from .motor_simplificado import carregar_base, fator_ipcae


def proximo_mes(dia):
    return date(dia.year + (dia.month == 12), dia.month % 12 + 1, 1)


def calcular_ipcae_mensal(geral: DadosGerais, parcelas: list[Parcela], dados=None) -> ResultadoCalculo:
    """Exclui a competência de origem e inclui o mês da data-base; sem juros."""
    dados = carregar_base() if dados is None else dados
    fim = geral.data_base
    if fim.day != calendar.monthrange(fim.year, fim.month)[1]:
        raise ValueError("Este cálculo mensal requer data-base no último dia do mês.")
    taxas = dados["ipcae_taxas"]
    centavos = lambda v: v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    resultado = ResultadoCalculo(dados_gerais=geral)
    numeros = set()
    for parcela in parcelas:
        venc = parcela.data_vencimento
        if venc is None or venc > fim:
            raise ValueError("Cada parcela deve ter vencimento até a data-base.")
        if parcela.numero in numeros:
            raise ValueError("Numeração de parcelas duplicada.")
        numeros.add(parcela.numero)
        if (parcela.periodos_juros or parcela.juros_moratorios.value != "sem_juros"
                or parcela.multa_moratoria or parcela.periodos_correcao
                or parcela.correcao_monetaria.value not in ("sem_correcao", "ipcae")):
            raise ValueError("Este motor recebe somente IPCA-E mensal, sem outros critérios.")
        principal = parcela.valor_bruto - parcela.valor_pago_na_data
        if principal < 0:
            raise ValueError("O pagamento não pode superar o valor bruto da parcela.")
        saldo = principal
        fator_total = Decimal(1)
        atual = proximo_mes(venc)
        inicio = atual if atual <= fim else None
        memoria = []
        while atual <= fim:
            seguinte = proximo_mes(atual)
            comp = atual.strftime("%Y-%m")
            if comp not in taxas:
                raise ValueError(f"Taxa IPCA-15/IPCA-E ausente: {comp}.")
            taxa = Decimal(taxas[comp])
            fator = fator_ipcae(dados, comp)
            anterior = saldo
            saldo *= fator
            fator_total *= fator
            memoria.append(MemoriaMensal(
                parcela=parcela.numero, competencia=comp, valor_base=anterior,
                indice_aplicado="IPCA-E IBGE (IPCA-15)", fator_aplicado=fator,
                valor_corrigido=saldo, total=saldo,
                observacao=f"Taxa IPCA-15 {taxa}%; fator 1 + taxa / 100; mês completo; sem juros.",
            ))
            atual = seguinte
        total = centavos(saldo)
        correcao = total - principal
        resultado.parcelas.append(ResultadoParcela(
            numero=parcela.numero, historico=parcela.historico, data_vencimento=venc,
            valor_bruto=parcela.valor_bruto, valor_pago_na_data=parcela.valor_pago_na_data,
            valor_apurado=principal, correcao_monetaria=correcao, valor_corrigido=total,
            total_parcela=total, memoria_correcao=memoria,
            componentes={"correcao": ComponenteCalculo(
                data_inicial=inicio, data_final=fim if inicio else None,
                base_calculo=principal, fator_acumulado=fator_total, valor=correcao,
            )},
        ))
        resultado.memoria_mensal.extend(memoria)
    principal = sum((p.valor_apurado for p in resultado.parcelas), Decimal(0))
    correcao = sum((p.correcao_monetaria for p in resultado.parcelas), Decimal(0))
    resultado.resumo = ResumoGeral(
        principal_original=sum((p.valor_bruto for p in parcelas), Decimal(0)),
        valor_pago_na_data_parcelas=sum((p.valor_pago_na_data for p in parcelas), Decimal(0)),
        principal_apurado=principal, correcao_monetaria=correcao,
        total_atualizado=principal + correcao, totais_componentes={"correcao": correcao},
    )
    resultado.premissas = {
        "perfil": "correcao_mensal_v1", "nome_indice": "IPCA-E",
        "versao_metodologia": "ipcae_ibge_mensal_mes_seguinte_v2", "data_base_maxima": fim.isoformat(),
        "entrada": {"dados_gerais": geral.model_dump(mode="json"), "parcelas": [p.model_dump(mode="json") for p in parcelas]},
        "fontes": {"ipcae": dados["fontes"]["ipcae"]}, "obtido_em": dados.get("obtido_em"),
        "criterios": [
            f"Correção exclusiva pelo IPCA-E oficial do IBGE, formado pelo IPCA-15, até {fim:%d/%m/%Y}, sem juros.",
            "Competências mensais: correção a partir do mês seguinte ao da parcela, incluindo o mês da data-base. Parcelas da competência final têm fator 1,0000.",
        ],
        "metodologia": [
            "O fator de cada mês é 1 + a variação mensal do IPCA-15 / 100. Multiplicam-se os fatores mensais; deflações são preservadas. Correção = principal × (fator acumulado - 1).",
            "Adotado o último dia de cada competência como vencimento mensal. Exclui-se o mês de origem e inclui-se o mês da data-base. Não há cálculo proporcional diário.",
            "Bases e fatores são conservados com precisão decimal no cálculo; arredonda-se o saldo final de cada parcela para centavos (HALF_UP). A correção é a diferença entre esse saldo e o principal. Fatores exibidos com quatro casas.",
            "O total é a soma das parcelas atualizadas e das parcelas adicionais expressamente informadas. Valores adicionais da competência final não recebem atualização nesta data-base.",
        ],
    }
    return resultado
