"""IPCA e Taxa Legal simples; história reconstituída antes da série oficial."""
import hashlib
import json
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal as D, ROUND_HALF_UP
from types import SimpleNamespace

from .honorarios_principais import BASE_IPCA, corrigir_valor_causa
from .models import ComponenteCalculo, DadosGerais, MemoriaMensal, ResultadoCalculo, ResultadoParcela, ResumoGeral
from .motor_simplificado import consultar, moeda, proximo_mes, trechos
from .motor_ipca_taxa_legal import BASE_TAXA_LEGAL, INICIO, RESOLUCAO, CALCULADORA
from .perfis import CIVIL_5, PERFIS
from liquidacao_custom.index_data.store import DataPath
from liquidacao_custom.index_data.taxa_legal_reconstruida import ARQUIVO, METODOLOGIA
from liquidacao_custom.index_data.validation import monthly

BASE_RECONSTRUIDA = DataPath(ARQUIVO)
NOTA_RECONSTRUCAO = "Taxa Legal reconstruída até 29/08/2024."


def carregar_reconstruida():
    if not BASE_RECONSTRUIDA.exists():
        raise ValueError("Base histórica da Taxa Legal ausente; atualize os índices do Civil 5.")
    dados = json.loads(BASE_RECONSTRUIDA.read_text(encoding="utf-8-sig"))
    if dados.get("metodologia") != METODOLOGIA:
        raise ValueError("Metodologia histórica da Taxa Legal inválida.")
    monthly(dados["taxa_legal"], nonnegative=True)
    if max(dados["taxa_legal"]) != "2024-08":
        raise ValueError("A cobertura histórica da Taxa Legal deve terminar na transição de agosto/2024.")
    return dados


def criterios_civil_5():
    historica = carregar_reconstruida()
    ipca = json.loads(BASE_IPCA.read_text(encoding="utf-8-sig"))
    legal = json.loads(BASE_TAXA_LEGAL.read_text(encoding="utf-8-sig"))
    monthly(ipca["ipca"])
    monthly(legal["taxa_legal"], nonnegative=True)
    competencia = min(max(ipca["ipca"]), max(legal["taxa_legal"]))
    inicio_juros = min(historica["taxa_legal"]) + "-01"
    return {"perfil": CIVIL_5, "perfis": PERFIS, "inicio": inicio_juros,
        "inicio_correcao": min(ipca["ipca"]) + "-01", "inicio_juros": inicio_juros,
        "inicio_selic": "", "transicao": INICIO.isoformat(),
        "data_base_maxima": proximo_mes(date.fromisoformat(competencia + "-01")).isoformat(),
        "atualizado_em": max(ipca["obtido_em"], legal["obtido_em"], historica["obtido_em"]),
        "versao_metodologia": "civil_5_taxa_legal_reconstruida_datas_independentes_v1",
        "fontes": {"ipca": ipca["fontes"]["ipca"], "taxa_legal": legal["fonte_publica"],
            "resolucao_taxa_legal": RESOLUCAO, "calculadora_taxa_legal": CALCULADORA,
            **historica["fontes"]},
        "contagem": "Termos independentes; inclui o início e exclui a data-base. IPCA geométrico e Taxa Legal simples sobre o principal corrigido final. Taxa reconstruída até 29/08/2024; oficial desde 30/08/2024."}


def apurar_juros_civil_5(saldo_exato, inicio_juros, fim, numero=1):
    historica = carregar_reconstruida()
    legal = json.loads(BASE_TAXA_LEGAL.read_text(encoding="utf-8-sig"))
    if inicio_juros < date.fromisoformat(min(historica["taxa_legal"]) + "-01"):
        raise ValueError("Civil 5: início dos juros anterior à cobertura histórica da Taxa Legal.")
    if fim > proximo_mes(date.fromisoformat(max(legal["taxa_legal"]) + "-01")):
        raise ValueError("Civil 5: data-base além da Taxa Legal oficial publicada.")
    saldo, ultimo_dia = moeda(saldo_exato), fim - timedelta(days=1)
    acumulada, memoria, auditoria, anterior_juros = D(0), [], [], D(0)
    for ini, ate, _ in trechos(inicio_juros, ultimo_dia):
        partes = [(ini, ate)]
        if ini < INICIO <= ate:
            partes = [(ini, INICIO - timedelta(days=1)), (INICIO, ate)]
        for comeco, final in partes:
            competencia = comeco.strftime("%Y-%m")
            reconstruida = comeco < INICIO
            dados = historica if reconstruida else legal
            taxa = consultar(dados, "taxa_legal", competencia)
            if not taxa.is_finite() or taxa < 0 or taxa.as_tuple().exponent < -6:
                raise ValueError("Taxa Legal inválida: " + competencia)
            formacao = historica.get("memoria_formacao", {}).get(competencia) if reconstruida else None
            if reconstruida and (not formacao or D(formacao["taxa_mensal"]) != taxa):
                raise ValueError("Memória de formação da Taxa Legal histórica ausente ou divergente: " + competencia)
            dias = (final - comeco).days + 1
            dias_mes = monthrange(comeco.year, comeco.month)[1]
            proporcional = taxa * D(dias) / D(dias_mes)
            acumulada += proporcional
            aplicada = acumulada.quantize(D("0.000001"), rounding=ROUND_HALF_UP)
            juros_acumulados = moeda(saldo_exato * aplicada / 100)
            periodo = juros_acumulados - anterior_juros
            origem = "reconstruida" if reconstruida else "oficial"
            observacao = (f"{comeco} a {final}; Taxa Legal {'reconstruída' if reconstruida else 'oficial'} {taxa:.6f}% a.m.; {dias}/{dias_mes} dias; "
                f"taxa acumulada {aplicada:.6f}%; base: principal corrigido final pelo IPCA; juros simples, sem capitalização. Data-base excluída.")
            memoria.append(MemoriaMensal(parcela=numero, competencia=competencia,
                indice_aplicado="Taxa Legal reconstruída (CMN 5.171/2024)" if reconstruida else "Taxa Legal (BCB SGS 29543)",
                valor_base=saldo_exato, fator_aplicado=1 + proporcional / 100, valor_corrigido=saldo_exato,
                juros_periodo=periodo, juros_acumulados=juros_acumulados,
                total=saldo + juros_acumulados, observacao=observacao))
            auditoria.append({"parcela": numero, "competencia": competencia, "inicio": str(comeco), "fim": str(final),
                "dias": dias, "dias_mes": dias_mes, "origem": origem,
                "serie_publicada": None if reconstruida else 29543,
                "taxa_mensal": str(taxa), "taxa_proporcional": str(proporcional),
                "taxa_acumulada": str(aplicada), "base": str(saldo_exato),
                "juros_periodo": str(periodo), "juros_acumulados": str(juros_acumulados),
                "formacao_taxa": formacao})
            anterior_juros = juros_acumulados
    componente = ComponenteCalculo(data_inicial=inicio_juros if inicio_juros < fim else None,
        data_final=ultimo_dia if inicio_juros < fim else None, base_calculo=saldo_exato,
        taxa_acumulada_percentual=acumulada.quantize(D("0.000001"), rounding=ROUND_HALF_UP), valor=anterior_juros)
    return anterior_juros, componente, memoria, auditoria


from .moedas_historicas import parcelas_em_reais


@parcelas_em_reais
def executar_civil_5(calculo):
    criterios = criterios_civil_5()
    fim = calculo.dados_gerais.data_base
    if fim > date.fromisoformat(criterios["data_base_maxima"]):
        raise ValueError(f"Civil 5: data-base máxima {criterios['data_base_maxima']}; não estimar índices ausentes.")
    parcelas, memoria, auditoria = [], [], []
    for entrada in calculo.parcelas:
        inicio_correcao = entrada.data_vencimento
        inicio_juros = calculo.inicio_juros_parcela(entrada)
        if inicio_correcao < date.fromisoformat(criterios["inicio_correcao"]):
            raise ValueError(f"Civil 5: início da correção anterior à cobertura IPCA ({criterios['inicio_correcao']}).")
        principal = entrada.valor_bruto - entrada.valor_pago_na_data
        fator, mem_correcao = D(1), []
        if inicio_correcao < fim:
            _, fator, registros, _, _ = corrigir_valor_causa(SimpleNamespace(
                indice="ipca", valor_causa=principal, data_protocolo=inicio_correcao), fim - timedelta(days=1), valor_em_reais=True)
            mem_correcao = [m.model_copy(update={"parcela": entrada.numero, "indice_aplicado": "IPCA (SGS 433)"}) for m in registros]
        saldo_exato = principal * fator
        saldo = moeda(saldo_exato)
        juros, componente_juros, mem_juros, registros = apurar_juros_civil_5(saldo_exato, inicio_juros, fim, entrada.numero)
        auditoria.extend(registros)
        componentes = {"ipca": ComponenteCalculo(data_inicial=inicio_correcao if inicio_correcao < fim else None,
            data_final=fim - timedelta(days=1) if inicio_correcao < fim else None,
            base_calculo=principal, fator_acumulado=fator, valor=saldo - principal), "taxa_legal": componente_juros}
        parcelas.append(ResultadoParcela(numero=entrada.numero, historico=entrada.historico,
            data_vencimento=inicio_correcao, valor_bruto=entrada.valor_bruto, valor_pago_na_data=entrada.valor_pago_na_data,
            valor_apurado=principal, correcao_monetaria=saldo - principal, valor_corrigido=saldo,
            juros_mora=juros, total_parcela=saldo + juros, componentes=componentes,
            memoria_correcao=mem_correcao, memoria_juros=mem_juros))
        memoria.extend(mem_correcao + mem_juros)

    def total(campo):
        return sum((getattr(p, campo) for p in parcelas), D(0))

    utilizou_historica = any(row["origem"] == "reconstruida" for row in auditoria)
    metodologia = [
        "IPCA: SGS 433, fatores mensais geométricos proporcionais aos dias, com deflações preservadas.",
        "Taxa Legal: soma simples das taxas proporcionais sobre o principal corrigido final. Inclui o início e exclui a data-base; termos independentes, sem capitalização ou SELIC integral adicional.",
    ]
    if utilizou_historica:
        metodologia.append(NOTA_RECONSTRUCAO)
    historica = carregar_reconstruida()
    return ResultadoCalculo(dados_gerais=DadosGerais(**calculo.dados_gerais.model_dump(), tipo_devedor="outro"),
        parcelas=parcelas, memoria_mensal=memoria,
        resumo=ResumoGeral(principal_original=total("valor_bruto"), valor_pago_na_data_parcelas=total("valor_pago_na_data"),
            principal_apurado=total("valor_apurado"), correcao_monetaria=total("correcao_monetaria"),
            juros_mora=total("juros_mora"), total_atualizado=total("total_parcela"),
            totais_componentes={"ipca": total("correcao_monetaria"), "taxa_legal": total("juros_mora")}),
        premissas={**criterios, "entrada": calculo.model_dump(mode="json"), "metodologia": metodologia,
            "criterios": [], "utilizou_taxa_legal_reconstruida": utilizou_historica,
            "memoria_taxa_legal": auditoria, "metodologia_reconstrucao": historica["metodologia"],
            "metodologia_tecnica_reconstrucao": "SELIC anual diária SGS 1178 e IPCA-15 SGS 7478 do mês anterior. Fatores SELIC diário e mensal arredondados a oito casas; fator IPCA-15 com quatro casas. Quociente dos fatores menos um, piso zero e TL percentual com seis casas, arredondamento NBR 5891 (metade para par). Desde 30/08/2024, somente taxa oficial SGS 29543. Taxa acumulada aplicada com seis casas HALF_UP; valores monetários HALF_UP ao centavo.",
            "sha256_ipca": hashlib.sha256(BASE_IPCA.read_bytes()).hexdigest(),
            "sha256_taxa_legal": hashlib.sha256(BASE_TAXA_LEGAL.read_bytes()).hexdigest(),
            "sha256_taxa_legal_reconstruida": hashlib.sha256(BASE_RECONSTRUIDA.read_bytes()).hexdigest(),
            "sha256_fontes_reconstrucao": historica["sha256_fontes"],
            "urls_fontes_reconstrucao": historica["urls_consultadas"]})
