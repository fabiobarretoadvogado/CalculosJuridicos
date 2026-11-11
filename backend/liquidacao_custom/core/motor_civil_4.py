"""Perfil civil temporário com termos independentes e consolidação na transição."""
import hashlib
import json
from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal as D

from .models import ComponenteCalculo, DadosGerais, MemoriaMensal, ResultadoCalculo, ResultadoParcela, ResumoGeral
from .motor_simplificado import consultar, moeda, proximo_mes, trechos
from .motor_ipca_taxa_legal import BASE_TAXA_LEGAL, INICIO, RESOLUCAO, CALCULADORA, apurar_juros_taxa_legal
from .honorarios_principais import BASE_IPCA
from .perfis import CIVIL_4, CIVIL_6, PERFIS
from .moedas_historicas import INICIO_IPCA, INICIO_REAL, parcelas_em_reais
from liquidacao_custom.index_data.store import current_dataset
from liquidacao_custom.index_data.series import read_json, selic_values

INICIO_COBERTURA = date(2009, 7, 1)
# Marcos e taxa próprios do novo padrão; o Civil 4 conserva seus critérios.
INICIO_CC_2002 = date(2003, 1, 11)
TAXA_ANTERIOR_CC = D("0.5")
FONTE_CC_2002 = "https://www.planalto.gov.br/ccivil_03/leis/2002/l10406compilada.htm"
FONTE_CC_1916 = "https://www.planalto.gov.br/ccivil_03/leis/l3071.htm"
LEI = "https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2024/lei/l14905.htm"
TEMA = "https://www.stj.jus.br/sites/portalp/Paginas/Comunicacao/Noticias/2025/29102025-Tese-sobre-aplicacao-da-Selic-a-dividas-civis-passa-a-ter-os-efeitos-do-recurso-repetitivo.aspx"
TERMOS_DISTINTOS = "https://www.stj.jus.br/sites/portalp/Paginas/Comunicacao/Noticias/2025/12032025-Selic-deve-ser-aplicada-como-juros-moratorios-se-sentenca-nao-determinar-outra-taxa.aspx"
ARQUIVOS_SELIC = ("selic_historica.json", "indices_simplificados.json", "indices_ec136.json")
# Convenções expressamente escolhidas para este perfil temporário.
SELIC_ANTES_CORRECAO = "deduzida_ipca"
CORRIGIR_SELIC_HISTORICA = True
TAXA_LEGAL_SOBRE_CONSOLIDADO = True
ACORDAO = "https://scon.stj.jus.br/SCON/GetInteiroTeorDoAcordao?dt_publicacao=20%2F02%2F2025&num_registro=202200205552"


def carregar_selic_civil():
    directory = current_dataset().directory
    taxas = selic_values(directory)
    consultas, fontes, hashes = {}, {}, {}
    for name in ARQUIVOS_SELIC:
        dados = read_json(directory, name)
        consultada = dados.get("selic_obtido_em", dados["obtido_em"])
        registros = dados["selic"]
        competencias = registros if isinstance(registros, dict) else (
            datetime.strptime(item["data"], "%d/%m/%Y").strftime("%Y-%m") for item in registros
        )
        for competencia in competencias:
            consultas[competencia] = max(consultada, consultas.get(competencia, consultada))
        fontes[name] = dados.get("fonte") or dados["fontes"]["selic"]
        hashes[name] = hashlib.sha256((directory / name).read_bytes()).hexdigest()
    return {"selic": taxas, "consultas": consultas, "fontes": fontes, "hashes": hashes}


def criterios_civil_4(perfil=CIVIL_4):
    ipca = json.loads(BASE_IPCA.read_text(encoding="utf-8-sig"))
    legal = json.loads(BASE_TAXA_LEGAL.read_text(encoding="utf-8-sig"))
    selic = carregar_selic_civil()
    competencia = min(max(ipca["ipca"]), max(legal["taxa_legal"]))
    limite = proximo_mes(date.fromisoformat(competencia + "-01"))
    criterios = {
        "perfil": CIVIL_4, "perfis": PERFIS, "inicio": INICIO_COBERTURA.isoformat(),
        "inicio_correcao": min(ipca["ipca"]) + "-01",
        "inicio_juros": max(INICIO_COBERTURA.isoformat(), min(selic["selic"]) + "-01"),
        "inicio_selic": max(INICIO_COBERTURA.isoformat(), min(selic["selic"]) + "-01"),
        "transicao": INICIO.isoformat(), "data_base_maxima": limite.isoformat(),
        "atualizado_em": max(ipca["obtido_em"], legal["obtido_em"], *selic["consultas"].values()),
        "versao_metodologia": "civil_4_temporario_consolidacao_v1",
        "fontes": {"ipca": ipca["fontes"]["ipca"], "taxa_legal": legal["fonte_publica"],
            "resolucao_taxa_legal": RESOLUCAO, "calculadora_taxa_legal": CALCULADORA,
            "selic": selic["fontes"]["indices_simplificados.json"],
            "selic_historica": selic["fontes"]["selic_historica.json"],
            "lei_14905": LEI, "tema_1368": TEMA, "stj_termos_distintos": TERMOS_DISTINTOS, "stj_acordao_2059743": ACORDAO},
        "contagem": "Termos independentes; inclui o início e exclui a data-base. Fases divididas em 30/08/2024. IPCA geométrico, SELIC e Taxa Legal simples.",
    }
    if perfil == CIVIL_6:
        criterios.update(perfil=CIVIL_6, inicio=INICIO_REAL.isoformat(),
            inicio_juros=INICIO_IPCA.isoformat(),
            inicio_selic=max(INICIO_CC_2002.isoformat(), min(selic["selic"]) + "-01"),
            transicao_cc_2002=INICIO_CC_2002.isoformat(),
            juros_anteriores_cc_percentual_mensal=str(TAXA_ANTERIOR_CC),
            versao_metodologia="civil_6_juros_05am_antes_cc_2002_v1",
            contagem="Termos independentes; inclui o início e exclui a data-base. Até 10/01/2003, IPCA e juros simples de 0,5% ao mês, proporcionais aos dias corridos do mês. Desde 11/01/2003, fases do Civil 4, com consolidação em 30/08/2024.")
        criterios["fontes"].update(codigo_civil_2002=FONTE_CC_2002, codigo_civil_1916=FONTE_CC_1916)
    return criterios


def apurar_juros_anteriores_cc(base, inicio, fim, numero):
    """Juros simples sem consolidação mensal nem no corte de 11/01/2003."""
    acumulada, memoria, auditoria = D(0), [], []
    for ini, ate, fracao in trechos(inicio, fim - timedelta(days=1)):
        proporcional = TAXA_ANTERIOR_CC * fracao
        anterior = moeda(base * (1 + acumulada / 100)) - moeda(base)
        acumulada += proporcional
        juros = moeda(base * (1 + acumulada / 100)) - moeda(base)
        memoria.append(MemoriaMensal(parcela=numero, competencia=ini.strftime("%Y-%m"),
            indice_aplicado="Juros simples de 0,5% a.m.", valor_base=base,
            fator_aplicado=1 + proporcional / 100, valor_corrigido=base,
            juros_periodo=juros - anterior, juros_acumulados=juros, total=moeda(base) + juros,
            observacao=f"{ini} a {ate}; juros simples de {TAXA_ANTERIOR_CC}% ao mês × {fracao}; taxa acumulada {acumulada}%; base constante, sem capitalização; data-base excluída."))
        auditoria.append({"parcela": numero, "competencia": ini.strftime("%Y-%m"),
            "inicio": str(ini), "fim": str(ate), "dias": (ate - ini).days + 1,
            "dias_mes": monthrange(ini.year, ini.month)[1], "fracao": str(fracao),
            "taxa_mensal": str(TAXA_ANTERIOR_CC), "taxa_proporcional": str(proporcional),
            "taxa_acumulada": str(acumulada), "base": str(base),
            "juros_periodo": str(juros - anterior), "juros_acumulados": str(juros)})
    exato = base * acumulada / 100
    componente = ComponenteCalculo(data_inicial=inicio if inicio < fim else None,
        data_final=fim - timedelta(days=1) if inicio < fim else None, base_calculo=base,
        taxa_acumulada_percentual=acumulada, valor=moeda(base + exato) - moeda(base))
    return exato, componente, memoria, auditoria


def corrigir_trecho(base, inicio, fim, numero, fase, dados):
    """Intervalo semiaberto: IPCA mensal proporcional, somente onde há incidência."""
    saldo, fator, memoria = base, D(1), []
    for ini, ate, fracao in trechos(inicio, fim - timedelta(days=1)):
        comp = ini.strftime("%Y-%m")
        taxa = consultar(dados, "ipca", comp)
        if not taxa.is_finite() or taxa <= -100:
            raise ValueError(f"IPCA inválido em {comp}; não substituir índice por zero.")
        fechado = proximo_mes(ini) - timedelta(days=1)
        if fechado >= date.fromisoformat(dados["obtido_em"]):
            raise ValueError(f"IPCA: competência {comp} ainda não fechada na consulta oficial.")
        parcial = (1 + taxa / 100) ** fracao
        anterior = saldo
        saldo *= parcial
        fator *= parcial
        memoria.append(MemoriaMensal(parcela=numero, competencia=comp,
            indice_aplicado=f"IPCA {fase} (SGS 433)", valor_base=anterior, fator_aplicado=parcial,
            valor_corrigido=saldo, total=moeda(saldo),
            observacao=f"{ini} a {ate}; IPCA {taxa}%; fator (1 + taxa / 100) ^ {fracao}; deflações preservadas; data-base excluída."))
    componente = ComponenteCalculo(data_inicial=inicio if inicio < fim else None,
        data_final=fim - timedelta(days=1) if inicio < fim else None,
        base_calculo=base, fator_acumulado=fator, valor=moeda(saldo) - moeda(base))
    return saldo, fator, componente, memoria


def apurar_selic_civil(base, inicio, fim, numero, dados, ipca_deducao=None):
    acumulada, memoria, auditoria = D(0), [], []
    for ini, ate, fracao in trechos(inicio, fim - timedelta(days=1)):
        comp = ini.strftime("%Y-%m")
        taxa = consultar(dados, "selic", comp)
        if not taxa.is_finite() or taxa < 0:
            raise ValueError(f"SELIC inválida em {comp}; confira a fonte oficial.")
        consultada = date.fromisoformat(dados["consultas"][comp])
        if proximo_mes(ini) > consultada:
            raise ValueError(f"SELIC: competência {comp} ainda não fechada na consulta oficial.")
        taxa_ipca = None
        aplicada = taxa
        if ipca_deducao is not None:
            taxa_ipca = consultar(ipca_deducao, "ipca", comp)
            if not taxa_ipca.is_finite() or taxa_ipca <= -100:
                raise ValueError(f"IPCA inválido em {comp} para dedução dos juros.")
            if proximo_mes(ini) > date.fromisoformat(ipca_deducao["obtido_em"]):
                raise ValueError(f"IPCA: competência {comp} ainda não fechada na consulta oficial.")
            # Convenção temporária expressa; não representa a SGS 29543 retroativamente.
            aplicada = max(taxa - taxa_ipca, D(0))
        proporcional = aplicada * fracao
        anterior = moeda(base * (1 + acumulada / 100))
        acumulada += proporcional
        saldo = moeda(base * (1 + acumulada / 100))
        if taxa_ipca is None:
            regra = "SELIC única; sem IPCA concomitante."
        else:
            regra = f"IPCA {taxa_ipca}%; SELIC deduzida do IPCA {aplicada}%."
        observacao = (f"{ini} a {ate}; SELIC mensal {taxa}%; {(ate - ini).days + 1}/{monthrange(ini.year, ini.month)[1]} dias; "
            f"taxa acumulada simples {acumulada}%; base constante; {regra} Data-base excluída.")
        anterior_acrescimo = anterior - moeda(base)
        acumulado = saldo - moeda(base)
        memoria.append(MemoriaMensal(parcela=numero, competencia=comp,
            indice_aplicado="SELIC deduzida do IPCA" if ipca_deducao is not None else "SELIC única (SGS 4390)", valor_base=base,
            fator_aplicado=1 + proporcional / 100, valor_corrigido=base if ipca_deducao is not None else saldo,
            juros_periodo=acumulado-anterior_acrescimo if ipca_deducao is not None else D(0),
            juros_acumulados=acumulado if ipca_deducao is not None else D(0), total=saldo,
            observacao=observacao))
        auditoria.append({"parcela": numero, "competencia": comp, "inicio": str(ini), "fim": str(ate),
            "dias": (ate - ini).days + 1, "dias_mes": monthrange(ini.year, ini.month)[1],
            "taxa_mensal": str(taxa), "taxa_proporcional": str(proporcional),
            "ipca_deducao": str(taxa_ipca) if taxa_ipca is not None else None, "taxa_liquida": str(aplicada),
            "diferenca_selic_ipca": str(taxa - taxa_ipca) if taxa_ipca is not None else None,
            "piso_zero_aplicado": taxa_ipca is not None and taxa - taxa_ipca < 0,
            "taxa_acumulada": str(acumulada), "base": str(base), "acrescimo_periodo": str(saldo - anterior),
            "acrescimo_acumulado": str(saldo - moeda(base))})
    acrescimo = base * acumulada / 100
    componente = ComponenteCalculo(data_inicial=inicio if inicio < fim else None,
        data_final=fim - timedelta(days=1) if inicio < fim else None, base_calculo=base,
        taxa_acumulada_percentual=acumulada, valor=moeda(base + acrescimo) - moeda(base))
    return acrescimo, componente, memoria, auditoria


@parcelas_em_reais
def executar_civil_4(calculo):
    civil6 = calculo.perfil == CIVIL_6
    criterios = criterios_civil_4(calculo.perfil)
    nome = "Civil 6" if civil6 else "Civil 4 temporário"
    fim = calculo.dados_gerais.data_base
    if fim > date.fromisoformat(criterios["data_base_maxima"]):
        raise ValueError(f"{nome}: data-base máxima {criterios['data_base_maxima']}; não estimar índice ausente.")
    dados_ipca = json.loads(BASE_IPCA.read_text(encoding="utf-8-sig"))
    dados_legal = json.loads(BASE_TAXA_LEGAL.read_text(encoding="utf-8-sig"))
    dados_selic = carregar_selic_civil()
    parcelas, memoria, auditoria_selic, auditoria_legal, transicoes = [], [], [], [], []
    auditoria_anteriores_cc = []
    for entrada in calculo.parcelas:
        correcao, juros = entrada.data_vencimento, calculo.inicio_juros_parcela(entrada)
        if correcao < date.fromisoformat(criterios["inicio_correcao"]) or juros < date.fromisoformat(criterios["inicio_juros"]):
            raise ValueError(f"{nome}: termo inicial anterior à cobertura oficial.")
        principal = entrada.valor_bruto - entrada.valor_pago_na_data
        inicio_selic = max(juros, INICIO_CC_2002) if civil6 else juros
        fim_pre = min(inicio_selic, INICIO, fim)
        capital, fator_pre, ipca_pre, mem_pre = corrigir_trecho(principal, correcao, fim_pre, entrada.numero, "anterior", dados_ipca)
        juros_05, componente_05, mem_05, registros_05 = apurar_juros_anteriores_cc(
            capital, juros, min(INICIO_CC_2002, fim), entrada.numero) if civil6 else (D(0), None, [], [])
        fim_selic = min(INICIO, fim)
        juros_pre, liquida, mem_liquida, registros_liquida = apurar_selic_civil(capital, inicio_selic, min(correcao, fim_selic), entrada.numero, dados_selic, dados_ipca)
        acrescimo, selic, mem_selic, registros_selic = apurar_selic_civil(capital, max(inicio_selic, correcao), fim_selic, entrada.numero, dados_selic)
        inicio_pos = max(INICIO, correcao)
        consolidado = capital + juros_05 + juros_pre + acrescimo
        base_pos = consolidado if CORRIGIR_SELIC_HISTORICA else capital
        saldo_pos, fator_pos, ipca_pos, mem_pos = corrigir_trecho(base_pos, inicio_pos, fim, entrada.numero, "posterior", dados_ipca)
        capital_final = capital * fator_pos
        acrescimo_final = (juros_05 + acrescimo + juros_pre) * fator_pos if CORRIGIR_SELIC_HISTORICA else juros_05 + acrescimo + juros_pre
        saldo_exato = saldo_pos if CORRIGIR_SELIC_HISTORICA else capital_final + acrescimo_final
        liquida.valor = moeda(capital + juros_05 + juros_pre) - moeda(capital + juros_05)
        selic.valor = moeda(consolidado) - moeda(capital + juros_05 + juros_pre)
        ipca_pos.valor = moeda(saldo_exato) - moeda(consolidado)
        base_legal = saldo_exato if TAXA_LEGAL_SOBRE_CONSOLIDADO else capital_final
        for ini, _, _ in trechos(max(INICIO, juros), fim - timedelta(days=1)):
            taxa = consultar(dados_legal, "taxa_legal", ini.strftime("%Y-%m"))
            if not taxa.is_finite() or taxa < 0:
                raise ValueError(f"Taxa Legal inválida em {ini:%Y-%m}; confira a fonte oficial.")
        juros_legais, legal, mem_legal, registros_legal = apurar_juros_taxa_legal(base_legal, max(INICIO, juros), fim, entrada.numero)
        # Consolidação única em 30/08/2024; os juros da fase legal seguem simples.
        for item in mem_pos:
            item.observacao += " Base consolidada na transição."
        for item in mem_legal:
            item.observacao = item.observacao.replace("principal corrigido final pelo IPCA", "base consolidada corrigida pelo IPCA")
        componentes = {"ipca_pre": ipca_pre, "juros_selic_deduzida": liquida, "selic": selic, "ipca_pos": ipca_pos, "taxa_legal": legal}
        valor_05 = componente_05.valor if civil6 else D(0)
        if civil6:
            componentes["juros_05am"] = componente_05
        saldo = moeda(saldo_exato)
        parcelas.append(ResultadoParcela(numero=entrada.numero, historico=entrada.historico,
            data_vencimento=correcao, valor_bruto=entrada.valor_bruto, valor_pago_na_data=entrada.valor_pago_na_data,
            valor_apurado=principal, correcao_monetaria=saldo - principal - liquida.valor - valor_05, valor_corrigido=saldo - liquida.valor - valor_05,
            juros_mora=juros_legais + liquida.valor + valor_05, total_parcela=saldo + juros_legais, componentes=componentes,
            memoria_correcao=mem_pre + mem_selic + mem_pos, memoria_juros=mem_05 + mem_liquida + mem_legal))
        memoria.extend(mem_pre + mem_05 + mem_liquida + mem_selic + mem_pos + mem_legal)
        auditoria_anteriores_cc.extend(registros_05)
        auditoria_selic.extend(registros_liquida + registros_selic)
        auditoria_legal.extend(registros_legal)
        transicoes.append({"parcela": entrada.numero, "principal": str(principal), "capital_apos_ipca_pre": str(capital),
            "data_transicao": str(INICIO), "transicao_alcancada": fim > INICIO, "base_consolidada_transicao": str(consolidado),
            "acrescimo_selic_historico": str(acrescimo), "fator_ipca_posterior": str(fator_pos),
            "juros_selic_deduzida_historicos": str(juros_pre), "base_taxa_legal": str(base_legal),
            "capital_corrigido_final": str(capital_final), "acrescimo_selic_final_segregado": str(acrescimo_final),
            "saldo_corrigido_final": str(saldo_exato), "juros_taxa_legal": str(juros_legais),
            "total": str(saldo + juros_legais), "correcao_selic_historica": CORRIGIR_SELIC_HISTORICA})
        if civil6:
            transicoes[-1].update(juros_05am_historicos=str(juros_05),
                data_transicao_cc_2002=str(INICIO_CC_2002), base_selic_sem_juros_anteriores=str(capital))
    def total(campo):
        return sum((getattr(p, campo) for p in parcelas), D(0))
    chaves = ("ipca_pre", "juros_selic_deduzida", "selic", "ipca_pos", "taxa_legal") + (("juros_05am",) if civil6 else ())
    totais = {chave: sum((p.componentes[chave].valor for p in parcelas), D(0)) for chave in chaves}
    metodologia_tecnica = [
        "IPCA anterior: SGS 433 desde o termo da correção até o início dos juros ou 29/08/2024, o que ocorrer primeiro. Fatores geométricos proporcionais aos dias; deflações preservadas.",
        "SELIC: SGS 4390, mensal simples e proporcional aos dias, desde o início dos juros até 29/08/2024. Substitui juros e correção na mesma faixa, sem IPCA concomitante ou outra taxa de juros.",
        "Juros anteriores à correção: até a véspera do termo da correção ou 29/08/2024, aplica-se exclusivamente a SELIC deduzida do IPCA do mesmo mês. Convenção temporária de dedução aritmética mensal max(SELIC - IPCA, 0), proporcional aos dias e simples, sobre o capital. Deflações do IPCA preservadas na dedução; não representa a SGS 29543 ou a metodologia CMN 5.171 aplicada retroativamente. O AgInt no AREsp 2.059.743 determina a dedução, mas não fixa esta fórmula operacional.",
        "Desde 30/08/2024, IPCA a partir do seu termo próprio e Taxa Legal oficial SGS 29543 desde o termo dos juros, respeitado o início da metodologia legal. Juros simples sobre a base consolidada corrigida final, com seis casas decimais; sem taxa substituta ou SELIC adicional.",
        "Transição escolhida para o perfil temporário: em 30/08/2024, consolidação única do capital e de todos os acréscimos históricos como base do IPCA e da Taxa Legal. Não ocorre consolidação ao passar da SELIC deduzida para a SELIC integral: ambas são simples sobre o mesmo capital. Os juros da Taxa Legal não são recapitalizados mensalmente. O acórdão consultado não fixa esta regra de transição entre regimes.",
        "Contagem: inclui o termo inicial e exclui a data-base; 29/08/2024 encerra SELIC e 30/08/2024 inicia a fase legal. Data-base igual ao termo não gera encargo. Sem competências ausentes ou SELIC não fechada. Precisão integral até o arredondamento HALF_UP ao centavo; componentes conciliados por diferenças de saldos arredondados.",
    ]
    metodologia = [
        "IPCA anterior à incidência dos juros; SELIC única quando incidem juros e correção, até 29/08/2024.",
        "SELIC deduzida do IPCA quando incidem somente juros, até 29/08/2024.",
        "Desde 30/08/2024: IPCA e Taxa Legal oficial, com termos iniciais independentes. Base consolidada na transição; juros simples.",
        "Inclui o início e exclui a data-base. Deflações preservadas; competências ausentes ou não fechadas impedem o cálculo.",
    ]
    if civil6:
        regra = "Até 10/01/2003: IPCA desde o termo da correção e juros simples de 0,5% ao mês desde o termo dos juros, proporcionais aos dias corridos de cada mês, sobre o capital corrigido da fase anterior à SELIC. Os juros não são incorporados à base da SELIC em 11/01/2003; somente integram a consolidação única de 30/08/2024."
        metodologia[0] = "Até 10/01/2003: IPCA e juros simples de 0,5% ao mês, com termos independentes. Desde 11/01/2003: IPCA antes dos juros e SELIC única quando incidem juros e correção, até 29/08/2024."
        metodologia[1] = "De 11/01/2003 a 29/08/2024: SELIC deduzida do IPCA quando incidem somente juros. Sem capitalização dos juros anteriores na passagem à SELIC."
        metodologia_tecnica[0] = regra + " Após esse corte, IPCA anterior somente até o início da SELIC ou 29/08/2024. Fatores geométricos proporcionais; deflações preservadas."
        metodologia_tecnica[1] = metodologia_tecnica[1].replace("desde o início dos juros", "desde o início dos juros, respeitado o corte de 11/01/2003,")
        metodologia_tecnica[2] = "Desde 11/01/2003: " + metodologia_tecnica[2]
    return ResultadoCalculo(dados_gerais=DadosGerais(**calculo.dados_gerais.model_dump(), tipo_devedor="outro"),
        parcelas=parcelas, memoria_mensal=memoria,
        resumo=ResumoGeral(principal_original=total("valor_bruto"), valor_pago_na_data_parcelas=total("valor_pago_na_data"),
            principal_apurado=total("valor_apurado"), correcao_monetaria=total("correcao_monetaria"),
            juros_mora=total("juros_mora"), total_atualizado=total("total_parcela"), totais_componentes=totais),
        premissas={**criterios, "entrada": calculo.model_dump(mode="json"), "metodologia": metodologia,
            "metodologia_tecnica": metodologia_tecnica,
            "criterios": ["IPCA, SELIC e Taxa Legal em fases sem sobreposição; termos iniciais de juros e correção independentes."],
            "memoria_selic_civil": auditoria_selic, "memoria_taxa_legal": auditoria_legal, "memoria_transicao_civil": transicoes,
            **({"memoria_juros_05am": auditoria_anteriores_cc} if civil6 else {}),
            "convencoes_temporarias": {"selic_antes_correcao": SELIC_ANTES_CORRECAO, "corrigir_selic_historica": CORRIGIR_SELIC_HISTORICA,
                "taxa_legal_sobre_consolidado": TAXA_LEGAL_SOBRE_CONSOLIDADO},
            "sha256_ipca": hashlib.sha256(BASE_IPCA.read_bytes()).hexdigest(),
            "sha256_taxa_legal": hashlib.sha256(BASE_TAXA_LEGAL.read_bytes()).hexdigest(),
            "sha256_fontes_selic": dados_selic["hashes"]})
