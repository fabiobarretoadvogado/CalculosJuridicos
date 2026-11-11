"""Honorários, art. 523 e destaque contratual, sem modificar as parcelas."""
import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP, localcontext
from types import SimpleNamespace
from .moedas_historicas import (conversao_monetaria, nota_conversao, registrar_conversoes,
    validar_origem, validar_data_base_real)

from .acessorios import calcular_honorarios, calcular_multa_cpc523
from .criterios_simplificados import CustaDespesaProcessual
from .models import (
    BaseCalculo, Honorarios, MultaCPC523, ResultadoParcela, MemoriaMensal,
    ResultadoHonorariosPrincipais, ResultadoCumprimentoSentenca, ResultadoDestaqueContratuais,
)

from liquidacao_custom.index_data.store import DataPath

BASE_IPCA = DataPath("ipca_oficial.json")
CPC = "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13105.htm"


def criterios_correcao_honorarios():
    from .motor_simplificado import ultima_data_ipcae, proximo_mes, carregar_base, dados_fonte_ipcae
    dados = json.loads(BASE_IPCA.read_text(encoding="utf-8"))
    comp = max(dados["ipca"])
    fim = proximo_mes(date.fromisoformat(comp + "-01")) - timedelta(days=1)
    from .motor_ipca_taxa_legal import BASE_TAXA_LEGAL
    legal = json.loads(BASE_TAXA_LEGAL.read_text(encoding="utf-8"))
    fim_legal = proximo_mes(date.fromisoformat(max(legal["taxa_legal"]) + "-01")) - timedelta(days=1)
    return {
        "inicio": max(min(dados["ipca"]), min(carregar_base()["ipcae_taxas"])) + "-01",
        "data_base_minima": "1994-07-01",
        "ipcae": {"inicio": min(carregar_base()["ipcae_taxas"]) + "-01", "data_base_maxima": ultima_data_ipcae().isoformat(), "fonte": dados_fonte_ipcae()},
        "ipca": {"inicio": min(dados["ipca"]) + "-01", "data_base_maxima": fim.isoformat(), "fonte": dados["fontes"]["ipca"]},
        "taxa_legal": {"inicio": "2024-08-30", "data_base_maxima": fim_legal.isoformat(), "fonte": legal["fonte_publica"]},
    }


def corrigir_valor_causa(config, data_base, *, valor_em_reais=False):
    from .motor_simplificado import (
        calcular_custas_despesas_ipcae,
        moeda,
        trechos,
        consultar,
        dados_fonte_ipcae,
        proximo_mes,
    )
    validar_origem(config.data_protocolo, config.indice, "Correção")
    # Nos perfis civis, o último dia de incidência pode anteceder a data-base validada.
    if not valor_em_reais:
        validar_data_base_real(data_base)
    if config.data_protocolo > data_base:
        raise ValueError("Correção: data de origem posterior à data-base.")
    original, conversao = (config.valor_causa, None) if valor_em_reais else conversao_monetaria(config.valor_causa, config.data_protocolo, "Valor da causa / valor fixado")
    if config.indice == "ipcae":
        item = calcular_custas_despesas_ipcae([
            SimpleNamespace(numero=1, nome="Valor da causa no protocolo", data=config.data_protocolo, valor=original)
        ], data_base, valor_em_reais=True)[0]
        memoria = [m.model_copy(update={"indice_aplicado": "Valor da causa - IPCA-E"}) for m in item.memoria]
        if conversao and memoria:
            memoria[0].observacao += " " + nota_conversao(conversao)
        return item.valor_atualizado, item.fator_ipcae, memoria, dados_fonte_ipcae(), None
    if config.indice == "inpc":
        from .motor_civil_2 import dados_inpc, BASE_INPC
        dados, base_indice = dados_inpc(), BASE_INPC
    else:
        dados, base_indice = json.loads(BASE_IPCA.read_text(encoding="utf-8")), BASE_IPCA
    indice = config.indice
    nome_indice = indice.upper()
    serie = "188" if indice == "inpc" else "433"
    # A cobertura do IPCA depende apenas da própria série. Não carregue
    # IPCA-E ou Taxa Legal para validar um cálculo que usa somente IPCA.
    ultima_competencia_ipca = max(dados[indice])
    limite_ipca = proximo_mes(date.fromisoformat(ultima_competencia_ipca + "-01")) - timedelta(days=1)
    if data_base > limite_ipca:
        raise ValueError(f"Valor da causa: data-base além da cobertura oficial do {nome_indice}.")
    saldo, acumulado, memoria = original, Decimal(1), []
    for ini, fim, fracao in trechos(config.data_protocolo, data_base):
        comp = ini.strftime("%Y-%m")
        taxa = consultar(dados, indice, comp)
        fator = (1 + taxa / 100) ** fracao
        anterior = saldo
        saldo *= fator
        acumulado *= fator
        memoria.append(MemoriaMensal(
            parcela=1, competencia=comp, indice_aplicado=f"Valor da causa - {nome_indice} (SGS {serie})",
            valor_base=anterior, fator_aplicado=fator, valor_corrigido=saldo, total=saldo,
            observacao=f"{ini} a {fim}; taxa mensal {taxa}%; fator (1 + taxa / 100) ^ {fracao}; sem juros.",
        ))
    if conversao and memoria:
        memoria[0].observacao += " " + nota_conversao(conversao)
    return moeda(saldo), acumulado, memoria, dados["fontes"][indice], hashlib.sha256(base_indice.read_bytes()).hexdigest()


def incorporar_honorarios_principais(resultado, calculo):
    from .motor_simplificado import moeda
    config, cumprimento = calculo.honorarios_sucumbenciais, calculo.cumprimento_sentenca
    if not (config.aplicar or cumprimento.aplicar_multa or cumprimento.aplicar_honorarios or cumprimento.destacar_contratuais):
        return resultado
    credito = moeda(sum((p.total_parcela for p in resultado.parcelas), Decimal(0)) - resultado.resumo.abatimentos)
    honorarios = Decimal(0)
    if config.aplicar:
        fator, correcao, memoria, fonte, sha = Decimal(1), Decimal(0), [], "", None
        descricao = {"valor_causa": "Valor da causa atualizado", "proveito_economico": "Proveito econômico após descontos, sem custas", "valor_certo": "Valor certo na data-base"}[config.base]
        original, base = credito, credito
        if config.base == "valor_causa":
            original = config.valor_causa
            base, fator, memoria, fonte, sha = corrigir_valor_causa(config, calculo.dados_gerais.data_base)
            original, conversao = conversao_monetaria(original, config.data_protocolo, "Valor da causa")
            registrar_conversoes(resultado, [conversao])
            original = moeda(original)
            correcao = moeda(base - original)
        elif config.base == "valor_certo":
            original = base = config.valor_certo
        with localcontext() as contexto:
            contexto.rounding = ROUND_HALF_UP
            detalhe = calcular_honorarios(Honorarios(
                percentual=config.percentual if config.base != "valor_certo" else None,
                valor_fixo=config.valor_certo if config.base == "valor_certo" else None,
                base_calculo=BaseCalculo.VALOR_MANUAL, valor_manual_base=base,
            ), [], calculo.dados_gerais.data_base)
        honorarios = detalhe["valor"]
        resultado.honorarios_detalhes.append(detalhe)
        resultado.honorarios_sucumbenciais = ResultadoHonorariosPrincipais(
            base=config.base, descricao_base=descricao, percentual=detalhe["percentual"],
            valor_original=original, data_protocolo=config.data_protocolo if config.base == "valor_causa" else None,
            indice=config.indice if config.base == "valor_causa" else None, fator_acumulado=fator,
            correcao_monetaria=correcao, base_atualizada=base, valor=honorarios, memoria=memoria, fonte=fonte,
        )
        if fonte:
            resultado.premissas.setdefault("fontes", {})["correcao_valor_causa"] = fonte
        if sha:
            resultado.premissas["sha256_ipca_valor_causa"] = sha
        resultado.premissas.setdefault("criterios", []).append(
            f"Honorários sucumbenciais: {descricao}. Custas e despesas não integram a base. "
            + ("Valor certo informado já na data-base, sem nova atualização automática." if config.base == "valor_certo" else f"Percentual informado: {config.percentual}%.")
        )
        if config.base == "valor_causa":
            resultado.premissas.setdefault("metodologia", []).append(
                f"Valor da causa no protocolo ({config.data_protocolo:%d/%m/%Y}): correção exclusiva por {'IPCA-E IBGE (IPCA-15)' if config.indice == 'ipcae' else 'IPCA SGS 433'} até a data-base, sem juros. "
                "Meses parciais proporcionais aos dias corridos, incluindo os extremos; deflações preservadas. "
                "Arredonda-se a base atualizada ao centavo (HALF_UP), depois se aplica o percentual e arredondam-se os honorários (HALF_UP)."
            )
    multa, honorarios_523 = Decimal(0), Decimal(0)
    if cumprimento.aplicar_multa or cumprimento.aplicar_honorarios:
        base_523 = credito
        with localcontext() as contexto:
            contexto.rounding = ROUND_HALF_UP
            detalhe_523 = calcular_multa_cpc523(MultaCPC523(
                aplicar_multa=cumprimento.aplicar_multa, aplicar_honorarios=cumprimento.aplicar_honorarios,
            ), [ResultadoParcela(total_parcela=base_523)])
        multa, honorarios_523 = detalhe_523["multa"], detalhe_523["honorarios_523"]
        resultado.cumprimento_sentenca = ResultadoCumprimentoSentenca(
            credito_parte=credito, sucumbenciais_na_base=Decimal(0), base_calculo=base_523,
            multa=multa, honorarios=honorarios_523, aplicar_multa=cumprimento.aplicar_multa,
            aplicar_honorarios=cumprimento.aplicar_honorarios,
        )
        resultado.premissas.setdefault("criterios", []).append(
            "Art. 523, § 1º, CPC/2015: multa de 10% e honorários de 10% selecionados separadamente, "
            "sobre o crédito das parcelas atualizado após descontos, sem honorários da sentença, custas ou despesas. "
            "A multa do art. 523 não integra a base dos honorários do próprio art. 523."
        )
        resultado.alertas.append("Art. 523: inclusão por opção do usuário. Confirme o término do prazo para pagamento voluntário e a incidência sobre o saldo não pago. Não utilizar no cumprimento contra a Fazenda Pública (art. 534, § 2º, CPC).")
        resultado.premissas.setdefault("fontes", {})["cpc_523"] = CPC
    resultado.resumo.multas = moeda(resultado.resumo.multas + multa)
    resultado.resumo.honorarios = moeda(resultado.resumo.honorarios + honorarios + honorarios_523)
    resultado.resumo.total_atualizado = moeda(resultado.resumo.total_atualizado + honorarios + multa + honorarios_523)
    if cumprimento.destacar_contratuais:
        base = credito + multa
        descricao = "Crédito da parte, sem custas ou honorários sucumbenciais e do art. 523"
        if cumprimento.base_contratuais == "total_sem_custas":
            base = resultado.resumo.total_atualizado - resultado.resumo.custas - resultado.resumo.despesas
            descricao = "Total devido, excluídas custas e despesas"
        valor = moeda(base * cumprimento.percentual_contratuais / 100)
        resultado.destaque_contratuais = ResultadoDestaqueContratuais(
            base=cumprimento.base_contratuais, descricao_base=descricao, base_calculo=moeda(base),
            percentual=cumprimento.percentual_contratuais, valor=valor, saldo_apos_destaque=moeda(base - valor),
        )
        resultado.premissas.setdefault("criterios", []).append(
            "Honorários contratuais: apenas destaque para divisão do crédito na base escolhida, sem custas ou despesas. "
            "Não acrescem à dívida, não reduzem o total devido pelo executado e não são somados aos honorários sucumbenciais."
        )
    resultado.premissas["entrada"] = calculo.model_dump(mode="json")
    return resultado
