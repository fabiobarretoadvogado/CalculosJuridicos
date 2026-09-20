"""IPCA-E e juros simples de 1% a cada 30 dias, sem capitalização."""

import hashlib
from datetime import date, timedelta
from decimal import Decimal as D, ROUND_DOWN, ROUND_HALF_UP

from .models import (
    ComponenteCalculo,
    DadosGerais,
    MemoriaMensal,
    ResultadoCalculo,
    ResultadoParcela,
    ResumoGeral,
)
from .motor_simplificado import BASE, carregar_base, consultar, fator_ipcae, proximo_mes, trechos
from .perfis import IPCAE_1AM_SIMPLES, PERFIS

FIM_IPCAE_ANUAL = date(2022, 9, 30)
INICIO_IPCAE_MENSAL = FIM_IPCAE_ANUAL + timedelta(days=1)
INICIO_COBERTURA = date(2010, 1, 1)


def taxa_ipcae_anual(dados, exercicio):
    """Deriva a taxa anual do ciclo outubro-setembro a partir da série oficial."""
    atual = date(exercicio - 2, 10, 1)
    limite = date(exercicio - 1, 10, 1)
    acumulado = D(1)
    while atual < limite:
        acumulado *= fator_ipcae(dados, atual.strftime("%Y-%m"))
        atual = proximo_mes(atual)
    return ((acumulado - 1) * 100).quantize(
        D("0.01"), rounding=ROUND_HALF_UP
    )


def truncar_centavos(valor):
    """Descarta frações inferiores a um centavo em cada rubrica do item."""

    return valor.quantize(D("0.01"), rounding=ROUND_DOWN)


def ultima_data_ipcae_disponivel(dados):
    """Último mês fechado com variação IPCA-15 publicada."""

    consulta = date.fromisoformat(dados["obtido_em"])
    limites = []
    for competencia in dados["ipcae_taxas"]:
        inicio = date.fromisoformat(competencia + "-01")
        fim = proximo_mes(inicio) - timedelta(days=1)
        if fim >= consulta or fim <= FIM_IPCAE_ANUAL:
            continue
        limites.append(fim)
    if not limites:
        raise ValueError("Não há mês completo de IPCA-E posterior a 30/09/2022 na base oficial.")
    return max(limites)


def criterios_ipcae_1am(dados=None):
    dados = dados or carregar_base()
    return {
        "perfil": IPCAE_1AM_SIMPLES,
        "perfis": PERFIS,
        "versao_metodologia": "ipcae_ibge_anual_mensal_juros_simples_1am_v4",
        "inicio": INICIO_COBERTURA.isoformat(),
        "inicio_selic": "",
        "transicao": INICIO_IPCAE_MENSAL.isoformat(),
        "data_base_maxima": ultima_data_ipcae_disponivel(dados).isoformat(),
        "atualizado_em": dados["obtido_em"],
        "fontes": {"ipcae": dados["fontes"]["ipcae"]},
        "contagem": (
            "Desde 01/01/2010. Até 30/09/2022, IPCA-E anual derivado da série oficial "
            "pelo ciclo outubro a setembro; "
            "de 01/10/2022 em diante, IPCA-E mensal. Juros simples de 1% para cada "
            "período completo de 30 dias, sem capitalização."
        ),
    }


def executar_ipcae_1am(calculo):
    dados = carregar_base()
    criterios = criterios_ipcae_1am(dados)
    fim = calculo.dados_gerais.data_base
    if fim < FIM_IPCAE_ANUAL:
        raise ValueError(
            "Este padrão consolida a base histórica em 30/09/2022 e não pode ser "
            "usado em data-base anterior."
        )
    data_base_maxima = date.fromisoformat(criterios["data_base_maxima"])
    if fim > data_base_maxima:
        raise ValueError(
            f"A data-base máxima permitida é {data_base_maxima.strftime('%d/%m/%Y')}, "
            "último mês completo de IPCA-E disponível."
        )
    if any(parcela.data_vencimento < INICIO_COBERTURA for parcela in calculo.parcelas):
        raise ValueError(
            "A série oficial disponível permite o cálculo anual para parcelas "
            "com exercício a partir de 2010."
        )

    resultados = []
    memoria = []
    for parcela in calculo.parcelas:
        principal = parcela.valor_bruto - parcela.valor_pago_na_data
        saldo = principal
        fator_acumulado = D(1)
        memoria_correcao = []
        inicio_correcao = parcela.data_vencimento + timedelta(days=1)
        for ano in range(parcela.data_vencimento.year + 1, FIM_IPCAE_ANUAL.year + 1):
            taxa = taxa_ipcae_anual(dados, ano)
            fator = 1 + taxa / 100
            anterior = saldo
            saldo *= fator
            fator_acumulado *= fator
            registro = MemoriaMensal(
                parcela=parcela.numero,
                competencia=str(ano),
                indice_aplicado="IPCA-E anual (IBGE)",
                valor_base=truncar_centavos(anterior),
                fator_aplicado=fator,
                valor_corrigido=truncar_centavos(saldo),
                total=truncar_centavos(saldo),
                observacao=(
                    f"Exercício {ano}; percentual de {taxa}% derivado do produto "
                    f"das variações IPCA-15 de {ano - 2}-10 a {ano - 1}-09; "
                    "aplicação acumulada sobre os exercícios subsequentes ao débito."
                ),
            )
            memoria_correcao.append(registro)

        for ini, ate, fracao in trechos(INICIO_IPCAE_MENSAL, fim):
            competencia = ini.strftime("%Y-%m")
            taxa = consultar(dados, "ipcae_taxas", competencia)
            fator = fator_ipcae(dados, competencia, fracao)
            anterior = saldo
            saldo *= fator
            fator_acumulado *= fator
            memoria_correcao.append(MemoriaMensal(
                parcela=parcela.numero,
                competencia=competencia,
                indice_aplicado="IPCA-E mensal (IBGE)",
                valor_base=truncar_centavos(anterior),
                fator_aplicado=fator,
                valor_corrigido=truncar_centavos(saldo),
                total=truncar_centavos(saldo),
                observacao=(
                    f"Período de {ini} a {ate}; taxa IPCA-15 {taxa}%; "
                    f"fração mensal {fracao}; aplicação geométrica."
                ),
            ))

        inicio_juros = calculo.inicio_juros_parcela(parcela)
        periodos_30_dias = max((fim - inicio_juros).days // 30, 0)
        taxa_juros = D(periodos_30_dias)
        saldo_arredondado = truncar_centavos(saldo)
        juros = truncar_centavos(saldo_arredondado * taxa_juros / 100)
        memoria_juros = []
        if periodos_30_dias:
            memoria_juros.append(MemoriaMensal(
                parcela=parcela.numero,
                competencia=fim.strftime("%Y-%m"),
                indice_aplicado="Juros simples de 1% ao mês",
                valor_base=saldo_arredondado,
                fator_aplicado=1 + taxa_juros / 100,
                valor_corrigido=saldo_arredondado,
                juros_periodo=juros,
                juros_acumulados=juros,
                total=saldo_arredondado + juros,
                observacao=(
                    f"{periodos_30_dias} período(s) completo(s) de 30 dias entre "
                    f"{inicio_juros} e {fim}; 1% por período; base corrigida; sem capitalização."
                ),
            ))

        correcao = saldo_arredondado - principal
        componentes = {
            "ipcae": ComponenteCalculo(
                data_inicial=inicio_correcao if inicio_correcao <= fim else None,
                data_final=fim if inicio_correcao <= fim else None,
                base_calculo=principal,
                fator_acumulado=fator_acumulado,
                valor=correcao,
            ),
            "juros_1am": ComponenteCalculo(
                data_inicial=inicio_juros,
                data_final=fim,
                base_calculo=saldo_arredondado,
                taxa_acumulada_percentual=taxa_juros,
                valor=juros,
            ),
        }
        resultado = ResultadoParcela(
            numero=parcela.numero,
            historico=parcela.historico,
            data_vencimento=parcela.data_vencimento,
            valor_bruto=parcela.valor_bruto,
            valor_pago_na_data=parcela.valor_pago_na_data,
            valor_apurado=principal,
            correcao_monetaria=correcao,
            valor_corrigido=saldo_arredondado,
            juros_mora=juros,
            total_parcela=saldo_arredondado + juros,
            memoria_correcao=memoria_correcao,
            memoria_juros=memoria_juros,
            componentes=componentes,
        )
        resultados.append(resultado)
        memoria.extend(memoria_correcao + memoria_juros)

    def total(campo):
        return sum((getattr(parcela, campo) for parcela in resultados), D(0))

    return ResultadoCalculo(
        dados_gerais=DadosGerais(**calculo.dados_gerais.model_dump(), tipo_devedor="outro"),
        parcelas=resultados,
        memoria_mensal=memoria,
        resumo=ResumoGeral(
            principal_original=total("valor_bruto"),
            valor_pago_na_data_parcelas=total("valor_pago_na_data"),
            principal_apurado=total("valor_apurado"),
            correcao_monetaria=total("correcao_monetaria"),
            juros_mora=total("juros_mora"),
            total_atualizado=total("total_parcela"),
            totais_componentes={
                "ipcae": sum((parcela.componentes["ipcae"].valor for parcela in resultados), D(0)),
                "juros_1am": sum((parcela.componentes["juros_1am"].valor for parcela in resultados), D(0)),
            },
        ),
        premissas={
            **criterios,
            "entrada": calculo.model_dump(mode="json"),
            "sha256_base": hashlib.sha256(BASE.read_bytes()).hexdigest(),
            "criterios": [
                "Até 30/09/2022, correção monetária pelos percentuais anuais de IPCA-E derivados das variações mensais oficiais do IPCA-15 (IBGE): acumulação de outubro a setembro, arredondada a duas casas decimais.",
                "A partir de 01/10/2022, continuidade da correção pelo IPCA-E mensal da base oficial.",
                "Juros moratórios simples de 1% por período completo de 30 dias, exigíveis após o primeiro período completo.",
            ],
            "metodologia": [
                "A correção histórica usa o ciclo anual de outubro a setembro: cada parcela recebe, de forma acumulada, os percentuais dos exercícios posteriores ao ano do débito até 2022. Cada percentual é obtido pelo produto das variações mensais oficiais do IPCA-15.",
                "Após 30/09/2022, a correção prossegue mês a mês pelas variações oficiais do IPCA-15 (IBGE, série SGS 7478), com proporcionalidade geométrica quando necessário.",
                "Os juros são calculados sobre o principal corrigido final: quantidade de períodos completos de 30 dias multiplicada por 1%, sem juros sobre juros.",
                "A correção e os juros são rubricas separadas; cada rubrica é truncada por item ao centavo, sem arredondar para cima.",
            ],
        },
    )
