"""Civil 2: IPCA e juros simples de 1% a.m., com termos iniciais independentes."""
import hashlib
import json
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal as D, ROUND_HALF_UP
from types import SimpleNamespace

from .criterios_simplificados import INICIO_TEMA_905
from .honorarios_principais import BASE_IPCA, corrigir_valor_causa
from .models import ComponenteCalculo, DadosGerais, MemoriaMensal, ResultadoCalculo, ResultadoParcela, ResumoGeral
from .motor_simplificado import moeda, proximo_mes, trechos
from .perfis import CIVIL_2, PERFIS


def criterios_civil_2():
    dados = json.loads(BASE_IPCA.read_text(encoding="utf-8"))
    competencia = max(dados["ipca"])
    # Civil 2 exclui a data-base. O primeiro dia do mês seguinte encerra
    # integralmente a última competência mensal publicada.
    limite = proximo_mes(date.fromisoformat(competencia + "-01"))
    return {
        "perfil": CIVIL_2,
        "perfis": PERFIS,
        "inicio": INICIO_TEMA_905.isoformat(),
        "inicio_selic": "",
        "transicao": "",
        "data_base_maxima": limite.isoformat(),
        "atualizado_em": dados["obtido_em"],
        "versao_metodologia": "civil_2_ipca_juros_simples_1am_datas_independentes_v1",
        "fontes": {"ipca": dados["fontes"]["ipca"]},
        "contagem": (
            "Dias corridos: inclui o início e exclui a data-base. "
            "IPCA geométrico proporcional e juros de mora simples de 1% ao mês, com datas independentes."
        ),
    }


def apurar_juros_1am(saldo_exato, inicio_juros, fim, numero=1):
    if inicio_juros < INICIO_TEMA_905:
        raise ValueError("Civil 2: o início dos juros deve ser igual ou posterior a 01/07/2009.")
    ultimo_dia = fim - timedelta(days=1)
    acumulada, memoria, anterior_juros = D(0), [], D(0)
    for ini, ate, fracao in trechos(inicio_juros, ultimo_dia):
        proporcional = D("0.01") * fracao
        acumulada += proporcional
        taxa_aplicada = acumulada.quantize(D("0.000001"), rounding=ROUND_HALF_UP)
        juros_acumulados = moeda(saldo_exato * taxa_aplicada)
        periodo = juros_acumulados - anterior_juros
        dias = (ate - ini).days + 1
        memoria.append(MemoriaMensal(
            parcela=numero,
            competencia=ini.strftime("%Y-%m"),
            indice_aplicado="Juros simples de 1% a.m.",
            valor_base=saldo_exato,
            fator_aplicado=1 + proporcional,
            valor_corrigido=saldo_exato,
            juros_periodo=periodo,
            juros_acumulados=juros_acumulados,
            total=moeda(saldo_exato) + juros_acumulados,
            observacao=(
                f"{ini} a {ate}; juros de 1% a.m.; {dias}/{monthrange(ini.year, ini.month)[1]} dias; "
                f"taxa acumulada {taxa_aplicada * 100:.6f}%; base: principal corrigido final pelo IPCA; "
                "juros simples, sem capitalização. Data-base excluída."
            ),
        ))
        anterior_juros = juros_acumulados
    componente = ComponenteCalculo(
        data_inicial=inicio_juros if inicio_juros < fim else None,
        data_final=ultimo_dia if inicio_juros < fim else None,
        base_calculo=saldo_exato,
        taxa_acumulada_percentual=(acumulada * 100).quantize(D("0.000001"), rounding=ROUND_HALF_UP),
        valor=anterior_juros,
    )
    return anterior_juros, componente, memoria


def executar_civil_2(calculo):
    criterios = criterios_civil_2()
    fim = calculo.dados_gerais.data_base
    if fim > date.fromisoformat(criterios["data_base_maxima"]):
        raise ValueError(
            f"Civil 2: data-base máxima {criterios['data_base_maxima']}, último mês com IPCA publicado. "
            "Não estimar índices futuros."
        )
    ultimo_dia = fim - timedelta(days=1)
    parcelas, memoria = [], []
    for entrada in calculo.parcelas:
        inicio_correcao = entrada.data_vencimento
        inicio_juros = calculo.inicio_juros_parcela(entrada)
        if inicio_correcao < INICIO_TEMA_905 or inicio_juros < INICIO_TEMA_905:
            raise ValueError("Civil 2: os termos iniciais devem ser iguais ou posteriores a 01/07/2009.")
        principal = entrada.valor_bruto - entrada.valor_pago_na_data
        fator, mem_correcao = D(1), []
        if inicio_correcao < fim:
            _, fator, registros, _, _ = corrigir_valor_causa(
                SimpleNamespace(indice="ipca", valor_causa=principal, data_protocolo=inicio_correcao),
                ultimo_dia,
            )
            mem_correcao = [
                item.model_copy(update={"parcela": entrada.numero, "indice_aplicado": "IPCA (SGS 433)"})
                for item in registros
            ]
        saldo_exato = principal * fator
        saldo = moeda(saldo_exato)
        juros, componente_juros, mem_juros = apurar_juros_1am(
            saldo_exato, inicio_juros, fim, entrada.numero
        )
        componentes = {
            "ipca": ComponenteCalculo(
                data_inicial=inicio_correcao if inicio_correcao < fim else None,
                data_final=ultimo_dia if inicio_correcao < fim else None,
                base_calculo=principal,
                fator_acumulado=fator,
                valor=saldo - principal,
            ),
            "juros_1am": componente_juros,
        }
        parcelas.append(ResultadoParcela(
            numero=entrada.numero,
            historico=entrada.historico,
            data_vencimento=inicio_correcao,
            valor_bruto=entrada.valor_bruto,
            valor_pago_na_data=entrada.valor_pago_na_data,
            valor_apurado=principal,
            correcao_monetaria=saldo - principal,
            valor_corrigido=saldo,
            juros_mora=juros,
            total_parcela=saldo + juros,
            componentes=componentes,
            memoria_correcao=mem_correcao,
            memoria_juros=mem_juros,
        ))
        memoria.extend(mem_correcao + mem_juros)

    def total(campo):
        return sum((getattr(parcela, campo) for parcela in parcelas), D(0))

    metodologia = [
        "IPCA: série oficial SGS 433, distinta do IPCA-E. Fatores mensais multiplicados; meses parciais elevados à fração de dias corridos. Deflações preservadas.",
        "Juros de mora: 1% ao mês de forma simples, proporcional aos dias corridos de cada mês, sem juros sobre juros.",
        "Datas: termos iniciais independentes. Os juros podem começar antes da correção monetária. Inclui-se o dia inicial e exclui-se a data-base; data-base igual ao termo inicial não gera encargo.",
        "Base dos juros: principal corrigido final pelo IPCA. Somam-se as taxas mensais proporcionais e aplica-se a taxa acumulada simples. Valores financeiros são arredondados HALF_UP ao centavo.",
    ]
    return ResultadoCalculo(
        dados_gerais=DadosGerais(**calculo.dados_gerais.model_dump(), tipo_devedor="outro"),
        parcelas=parcelas,
        memoria_mensal=memoria,
        resumo=ResumoGeral(
            principal_original=total("valor_bruto"),
            valor_pago_na_data_parcelas=total("valor_pago_na_data"),
            principal_apurado=total("valor_apurado"),
            correcao_monetaria=total("correcao_monetaria"),
            juros_mora=total("juros_mora"),
            total_atualizado=total("total_parcela"),
            totais_componentes={"ipca": total("correcao_monetaria"), "juros_1am": total("juros_mora")},
        ),
        premissas={
            **criterios,
            "entrada": calculo.model_dump(mode="json"),
            "metodologia": metodologia,
            "criterios": [
                "IPCA desde o termo inicial da correção; juros de mora simples de 1% ao mês desde o termo inicial dos juros, ainda que anterior. Datas independentes e sem capitalização."
            ],
            "sha256_ipca": hashlib.sha256(BASE_IPCA.read_bytes()).hexdigest(),
        },
    )
