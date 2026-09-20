"""IPCA e Taxa Legal oficial, com termos iniciais independentes."""
import hashlib
import json
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path
from types import SimpleNamespace

from .honorarios_principais import BASE_IPCA, corrigir_valor_causa
from .models import ComponenteCalculo, DadosGerais, MemoriaMensal, ResultadoCalculo, ResultadoParcela, ResumoGeral
from .motor_simplificado import consultar, moeda, proximo_mes, trechos
from .perfis import IPCA_TAXA_LEGAL, PERFIS

BASE_TAXA_LEGAL = Path(__file__).resolve().parents[2] / "data" / "taxa_legal_oficial.json"
INICIO = date(2024, 8, 30)
RESOLUCAO = "https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?numero=5171&tipo=resolu%C3%A7%C3%A3o+cmn"
CALCULADORA = "https://www3.bcb.gov.br/CALCIDADAO/publico/metodologiaCorrigirPelaTaxaLegal.do?method=metodologiaCorrigirPelaTaxaLegal"


def criterios_ipca_taxa_legal():
    legal = json.loads(BASE_TAXA_LEGAL.read_text(encoding="utf-8"))
    ipca = json.loads(BASE_IPCA.read_text(encoding="utf-8"))
    competencia = min(max(legal["taxa_legal"]), max(ipca["ipca"]))
    limite = proximo_mes(date.fromisoformat(competencia + "-01")) - timedelta(days=1)
    return {"perfil": IPCA_TAXA_LEGAL, "perfis": PERFIS, "inicio": INICIO.isoformat(),
            "inicio_selic": "", "transicao": "", "data_base_maxima": limite.isoformat(),
            "atualizado_em": max(ipca["obtido_em"], legal["obtido_em"]),
            "versao_metodologia": "ipca_taxa_legal_oficial_datas_independentes_v1",
            "fontes": {"ipca": ipca["fontes"]["ipca"], "taxa_legal": legal["fonte_publica"],
                       "resolucao_taxa_legal": RESOLUCAO, "calculadora_taxa_legal": CALCULADORA},
            "contagem": "Dias corridos: inclui o início e exclui a data-base, como na Calculadora do Cidadão. IPCA geométrico proporcional; Taxa Legal simples com datas independentes."}


def apurar_juros_taxa_legal(saldo_exato, inicio_juros, fim, numero=1, indice_correcao="IPCA"):
    """Rotina oficial compartilhada; sem SELIC adicional ou taxa substituta."""
    if inicio_juros < INICIO:
        raise ValueError("Taxa Legal oficial: início dos juros a partir de 30/08/2024. Períodos anteriores exigem outro critério expresso.")
    dados = json.loads(BASE_TAXA_LEGAL.read_text(encoding="utf-8"))
    limite = proximo_mes(date.fromisoformat(max(dados["taxa_legal"]) + "-01")) - timedelta(days=1)
    if fim > limite:
        raise ValueError(f"Taxa Legal oficial: data-base além da cobertura publicada ({limite}).")
    saldo, ultimo_dia = moeda(saldo_exato), fim - timedelta(days=1)
    acumulada, memoria, auditoria, anterior_juros = D(0), [], [], D(0)
    for ini, ate, fracao in trechos(inicio_juros, ultimo_dia):
        competencia = ini.strftime("%Y-%m")
        taxa = consultar(dados, "taxa_legal", competencia)
        if taxa < 0:
            raise ValueError(f"Taxa Legal oficial negativa em {competencia}; confira a fonte. Não substituir índice inválido.")
        proporcional = taxa * fracao
        acumulada += proporcional
        taxa_aplicada = acumulada.quantize(D("0.000001"), rounding=ROUND_HALF_UP)
        juros_acumulados = moeda(saldo_exato * taxa_aplicada / 100)
        periodo = juros_acumulados - anterior_juros
        dias = (ate - ini).days + 1
        observacao = (f"{ini} a {ate}; Taxa Legal oficial {taxa:.6f}% a.m.; {dias}/{monthrange(ini.year, ini.month)[1]} dias; "
                      f"taxa acumulada {taxa_aplicada:.6f}%; base: principal corrigido final pelo {indice_correcao}; juros simples, sem capitalização. Data-base excluída.")
        memoria.append(MemoriaMensal(parcela=numero, competencia=competencia,
            indice_aplicado="Taxa Legal (BCB SGS 29543)", valor_base=saldo_exato,
            fator_aplicado=1 + proporcional / 100, valor_corrigido=saldo_exato,
            juros_periodo=periodo, juros_acumulados=juros_acumulados,
            total=saldo + juros_acumulados, observacao=observacao))
        auditoria.append({"parcela": numero, "competencia": competencia, "inicio": str(ini), "fim": str(ate),
                          "dias": dias, "dias_mes": monthrange(ini.year, ini.month)[1],
                          "taxa_mensal": str(taxa), "taxa_proporcional": str(proporcional),
                          "taxa_acumulada": str(taxa_aplicada), "base": str(saldo_exato),
                          "juros_periodo": str(periodo), "juros_acumulados": str(juros_acumulados)})
        anterior_juros = juros_acumulados
    componente = ComponenteCalculo(data_inicial=inicio_juros if inicio_juros < fim else None,
        data_final=ultimo_dia if inicio_juros < fim else None, base_calculo=saldo_exato,
        taxa_acumulada_percentual=acumulada.quantize(D("0.000001"), rounding=ROUND_HALF_UP), valor=anterior_juros)
    return anterior_juros, componente, memoria, auditoria


def executar_ipca_taxa_legal(calculo):
    dados = json.loads(BASE_TAXA_LEGAL.read_text(encoding="utf-8"))
    criterios = criterios_ipca_taxa_legal()
    fim = calculo.dados_gerais.data_base
    if fim > date.fromisoformat(criterios["data_base_maxima"]):
        raise ValueError(f"Civil 1: data-base máxima {criterios['data_base_maxima']}, último mês com IPCA publicado. Não estimar índices futuros.")
    ultimo_dia = fim - timedelta(days=1)
    parcelas, memoria, auditoria = [], [], []
    for entrada in calculo.parcelas:
        inicio_correcao = entrada.data_vencimento
        inicio_juros = calculo.inicio_juros_parcela(entrada)
        if inicio_correcao < INICIO or inicio_juros < INICIO:
            raise ValueError("Civil 1: os termos iniciais devem ser a partir de 30/08/2024. Períodos anteriores exigem outro critério expresso.")
        principal = entrada.valor_bruto - entrada.valor_pago_na_data
        fator, mem_correcao = D(1), []
        if inicio_correcao < fim:
            _, fator, registros, _, _ = corrigir_valor_causa(SimpleNamespace(
                indice="ipca", valor_causa=principal, data_protocolo=inicio_correcao), ultimo_dia)
            mem_correcao = [m.model_copy(update={"parcela": entrada.numero, "indice_aplicado": "IPCA (SGS 433)"}) for m in registros]
        saldo_exato = principal * fator
        saldo = moeda(saldo_exato)
        anterior_juros, componente_juros, mem_juros, registros = apurar_juros_taxa_legal(saldo_exato, inicio_juros, fim, entrada.numero)
        auditoria.extend(registros)
        componentes = {
            "ipca": ComponenteCalculo(data_inicial=inicio_correcao if inicio_correcao < fim else None,
                data_final=ultimo_dia if inicio_correcao < fim else None,
                base_calculo=principal, fator_acumulado=fator, valor=saldo-principal),
            "taxa_legal": componente_juros,
        }
        parcelas.append(ResultadoParcela(numero=entrada.numero, historico=entrada.historico,
            data_vencimento=inicio_correcao, valor_bruto=entrada.valor_bruto, valor_pago_na_data=entrada.valor_pago_na_data,
            valor_apurado=principal, correcao_monetaria=saldo-principal, valor_corrigido=saldo,
            juros_mora=anterior_juros, total_parcela=saldo+anterior_juros,
            componentes=componentes, memoria_correcao=mem_correcao, memoria_juros=mem_juros))
        memoria.extend(mem_correcao + mem_juros)
    def total(campo):
        return sum((getattr(p, campo) for p in parcelas), D(0))
    metodologia = [
        "IPCA: série oficial SGS 433, distinta do IPCA-E. Fatores mensais multiplicados; meses parciais elevados à fração de dias corridos. Deflações preservadas.",
        "Taxa Legal: utilizar a taxa mensal oficial SGS 29543, com seis casas decimais. O BCB aplica a metodologia da Resolução CMN 5.171/2024, com fatores SELIC e IPCA-15 do mês anterior e piso zero; não subtrair diretamente percentuais mensais de SELIC e IPCA nem usar SELIC integral como juros.",
        "Datas: termos iniciais independentes. Juros podem começar antes da correção monetária. Inclui-se o dia inicial e exclui-se a data-base, conforme a Calculadora do Cidadão; juros proporcionais = taxa mensal × dias / dias corridos do mês. Data-base igual ao termo inicial não gera encargo.",
        "Base dos juros: principal corrigido final pelo IPCA, conforme art. 7º da Resolução CMN 5.171/2024. Somam-se as taxas, sem juros sobre juros; taxa acumulada aplicada com seis casas decimais. Valores financeiros arredondados HALF_UP ao centavo. Total = principal + correção IPCA + juros da Taxa Legal, sem SELIC duplicada.",
    ]
    return ResultadoCalculo(dados_gerais=DadosGerais(**calculo.dados_gerais.model_dump(), tipo_devedor="outro"),
        parcelas=parcelas, memoria_mensal=memoria,
        resumo=ResumoGeral(principal_original=total("valor_bruto"), valor_pago_na_data_parcelas=total("valor_pago_na_data"),
            principal_apurado=total("valor_apurado"), correcao_monetaria=total("correcao_monetaria"),
            juros_mora=total("juros_mora"), total_atualizado=total("total_parcela"),
            totais_componentes={"ipca": total("correcao_monetaria"), "taxa_legal": total("juros_mora")}),
        premissas={**criterios, "entrada": calculo.model_dump(mode="json"), "metodologia": metodologia,
            "criterios": ["IPCA desde o termo inicial da correção; Taxa Legal oficial desde o termo inicial dos juros, ainda que anterior. Datas independentes, sem capitalização nem SELIC integral adicional."],
            "memoria_taxa_legal": auditoria, "sha256_ipca": hashlib.sha256(BASE_IPCA.read_bytes()).hexdigest(),
            "sha256_taxa_legal": hashlib.sha256(BASE_TAXA_LEGAL.read_bytes()).hexdigest()})
