"""Civil 2 e Civil 3: correção mensal e juros simples de 1% a.m., com datas independentes."""
import hashlib
import json
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal as D, ROUND_HALF_UP
from types import SimpleNamespace

from .criterios_simplificados import INICIO_TEMA_905
from .moedas_historicas import parcelas_em_reais
from .honorarios_principais import BASE_IPCA, corrigir_valor_causa
from .models import ComponenteCalculo, DadosGerais, MemoriaMensal, ResultadoCalculo, ResultadoParcela, ResumoGeral
from .motor_simplificado import moeda, proximo_mes, trechos
from .perfis import CIVIL_2, CIVIL_3, PERFIS
from liquidacao_custom.index_data.store import DataPath, current_dataset

BASE_INPC = DataPath("inpc_oficial.json")
FONTE_INPC = "https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?method=consultarSeries&series=188"

def dados_inpc():
    dados = json.loads(BASE_INPC.read_text(encoding="utf-8"))
    if not dados.get("inpc"):
        raise ValueError("Base INPC sem competências publicadas.")
    return dados


def criterios_civil_2(perfil=CIVIL_2):
    indice = "inpc" if perfil == CIVIL_3 else "ipca"
    dados = dados_inpc() if perfil == CIVIL_3 else json.loads(BASE_IPCA.read_text(encoding="utf-8"))
    competencia = max(dados[indice])
    # Civil 2 exclui a data-base. O primeiro dia do mês seguinte encerra
    # integralmente a última competência mensal publicada.
    limite = proximo_mes(date.fromisoformat(competencia + "-01"))
    return {
        "perfil": perfil,
        "perfis": PERFIS,
        "inicio": INICIO_TEMA_905.isoformat(),
        "inicio_correcao": min(dados[indice]) + "-01" if perfil == CIVIL_2 else INICIO_TEMA_905.isoformat(),
        "inicio_juros": INICIO_TEMA_905.isoformat(),
        "inicio_selic": "",
        "transicao": "",
        "data_base_maxima": limite.isoformat(),
        "atualizado_em": dados["obtido_em"],
        "versao_metodologia": f"{perfil.removesuffix('_v1')}_{indice}_juros_simples_1am_datas_independentes_v1",
        "fontes": {indice: dados["fontes"][indice]},
        "contagem": (
            "Dias corridos: inclui o início e exclui a data-base. "
            f"{indice.upper()} geométrico proporcional e juros de mora simples de 1% ao mês, com datas independentes."
        ),
    }


def apurar_juros_1am(saldo_exato, inicio_juros, fim, numero=1, indice_correcao="IPCA", nome_perfil="Civil 2"):
    if inicio_juros < INICIO_TEMA_905:
        raise ValueError(f"{nome_perfil}: o início dos juros deve ser igual ou posterior a 01/07/2009.")
    ultimo_dia = fim - timedelta(days=1)
    acumulada, taxa_aplicada, anterior_juros = D(0), D(0), D(0)
    memoria = []
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
                f"taxa acumulada {taxa_aplicada * 100:.6f}%; base: principal corrigido final pelo {indice_correcao}; "
                "juros simples, sem capitalização. Data-base excluída."
            ),
        ))
        anterior_juros = juros_acumulados
    componente = ComponenteCalculo(
        data_inicial=inicio_juros if inicio_juros < fim else None,
        data_final=ultimo_dia if inicio_juros < fim else None,
        base_calculo=saldo_exato,
        taxa_acumulada_percentual=(taxa_aplicada * 100).quantize(D("0.000001")),
        valor=anterior_juros,
    )
    return anterior_juros, componente, memoria


@parcelas_em_reais
def executar_civil_2(calculo):
    perfil = calculo.perfil
    indice = "inpc" if perfil == CIVIL_3 else "ipca"
    nome_indice = indice.upper()
    serie = "188" if perfil == CIVIL_3 else "433"
    nome_perfil = "Civil 3" if perfil == CIVIL_3 else "Civil 2"
    base_indice = BASE_INPC if perfil == CIVIL_3 else BASE_IPCA
    criterios = criterios_civil_2(perfil)
    fim = calculo.dados_gerais.data_base
    if fim > date.fromisoformat(criterios["data_base_maxima"]):
        raise ValueError(
            f"{nome_perfil}: data-base máxima {criterios['data_base_maxima']}, último mês com {nome_indice} publicado. "
            "Não estimar índices futuros."
        )
    ultimo_dia = fim - timedelta(days=1)
    parcelas, memoria = [], []
    for entrada in calculo.parcelas:
        inicio_correcao = entrada.data_vencimento
        inicio_juros = calculo.inicio_juros_parcela(entrada)
        if inicio_correcao < date.fromisoformat(criterios["inicio_correcao"]):
            raise ValueError(f"{nome_perfil}: início da correção anterior à cobertura oficial ({criterios['inicio_correcao']}).")
        principal = entrada.valor_bruto - entrada.valor_pago_na_data
        fator, mem_correcao = D(1), []
        if inicio_correcao < fim:
            _, fator, registros, _, _ = corrigir_valor_causa(
                SimpleNamespace(indice=indice, valor_causa=principal, data_protocolo=inicio_correcao),
                ultimo_dia, valor_em_reais=True,
            )
            mem_correcao = [
                item.model_copy(update={"parcela": entrada.numero, "indice_aplicado": f"{nome_indice} (SGS {serie})"})
                for item in registros
            ]
        saldo_exato = principal * fator
        saldo = moeda(saldo_exato)
        juros, componente_juros, mem_juros = apurar_juros_1am(
            saldo_exato, inicio_juros, fim, entrada.numero, nome_indice, nome_perfil
        )
        componentes = {
            indice: ComponenteCalculo(
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
        f"{nome_indice}: série oficial SGS {serie}. Fatores mensais multiplicados; meses parciais elevados à fração de dias corridos. Deflações preservadas.",
        "Juros de mora: 1% ao mês de forma simples, proporcional aos dias corridos de cada mês, sem juros sobre juros.",
        "Datas: termos iniciais independentes. Os juros podem começar antes da correção monetária. Inclui-se o dia inicial e exclui-se a data-base; data-base igual ao termo inicial não gera encargo.",
        f"Base dos juros: principal corrigido final pelo {nome_indice}. Somam-se as taxas mensais proporcionais e aplica-se a taxa acumulada simples. Valores financeiros são arredondados HALF_UP ao centavo.",
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
            totais_componentes={indice: total("correcao_monetaria"), "juros_1am": total("juros_mora")},
        ),
        premissas={
            **criterios,
            "entrada": calculo.model_dump(mode="json"),
            "metodologia": metodologia,
            "criterios": [
                f"{nome_indice} desde o termo inicial da correção; juros de mora simples de 1% ao mês desde o termo inicial dos juros, ainda que anterior. Datas independentes e sem capitalização."
            ],
            f"sha256_{indice}": hashlib.sha256(base_indice.read_bytes()).hexdigest(),
        },
    )
