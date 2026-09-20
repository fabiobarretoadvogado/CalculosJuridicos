"""Tema 905, SELIC única e transição EC 136, com memória dos critérios."""
import hashlib
import json
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from .criterios_simplificados import (
    CalculoSimplificado,
    CustaDespesaProcessual,
    DadosSimplificados,
    ParcelaSimplificada,
    INICIO,
    INICIO_TEMA_905,
    TRANSICAO,
)
from .models import (
    ComponenteCalculo,
    DadosGerais,
    MemoriaMensal,
    MemoriaAbatimento,
    ResultadoCalculo,
    ResultadoCustaDespesaProcessual,
    ResultadoParcela,
    ResumoGeral,
)
from .perfis import (
    ATUAL,
    CIVIL_2,
    EC136,
    FAZENDA_1,
    FAZENDA_2,
    FAZENDA_3,
    FAZENDA_4,
    IPCAE_1AM_SIMPLES,
    PERFIS,
    PERFIS_FAZENDA,
)

BASE = Path(__file__).resolve().parents[2] / "data" / "indices_simplificados.json"
BASE_EC136 = BASE.with_name("indices_ec136.json")
BASE_SELIC_HISTORICA = BASE.with_name("selic_historica.json")
D = Decimal


def moeda(valor):
    return valor.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def proximo_mes(data):
    return date(data.year + data.month // 12, data.month % 12 + 1, 1)


def referencia_poupanca(data):
    """Poupança: referências 29, 30 e 31 correspondem ao dia 1 do mês seguinte."""
    return (proximo_mes(data) if data.day > 28 else data).isoformat()


def trechos(inicio, fim):
    """Intervalo fechado: inclui os dias inicial e final, sem sobreposição."""
    while inicio <= fim:
        ultimo = min(fim, proximo_mes(inicio) - timedelta(days=1))
        dias = (ultimo - inicio).days + 1
        yield inicio, ultimo, D(dias) / D(monthrange(inicio.year, inicio.month)[1])
        inicio = ultimo + timedelta(days=1)


def consultar(dados, serie, chave):
    try:
        return D(dados[serie][chave])
    except KeyError:
        raise ValueError(f"Índice ausente: {serie}, {chave}. Atualize a base oficial antes de calcular este período.") from None


def fator_ipcae(dados, competencia, fracao=D(1)):
    """Converte a variação mensal oficial do IPCA-15 em fator IPCA-E."""
    taxa = consultar(dados, "ipcae_taxas", competencia)
    if taxa <= D("-100"):
        raise ValueError(f"Taxa IPCA-15/IPCA-E inválida: {competencia}, {taxa}%.")
    return (D(1) + taxa / 100) ** fracao


def carregar_base():
    return json.loads(BASE.read_text(encoding="utf-8"))


def carregar_base_ec136():
    fonte = json.loads(BASE_EC136.read_text(encoding="utf-8-sig"))
    return {"selic": {date.fromisoformat(x["data"][6:] + "-" + x["data"][3:5] + "-" + x["data"][:2]).strftime("%Y-%m"): x["valor"] for x in fonte["selic"]},
            "obtido_em": fonte["obtido_em"],
            "selic_obtido_em": fonte.get("selic_obtido_em", fonte["obtido_em"]),
            "fontes": {"selic_limite": fonte["fontes"]["selic"]}}


def carregar_base_ec136_completa():
    """Combina SELIC histórica, base corrente e série pós-EC 136."""
    base = carregar_base()
    adicional = carregar_base_ec136()
    historica = json.loads(BASE_SELIC_HISTORICA.read_text(encoding="utf-8-sig"))
    selic_historica = {
        x["data"][6:] + "-" + x["data"][3:5]: x["valor"]
        for x in historica["selic"]
    }
    return {
        **base,
        # A série adicional serve exclusivamente ao limite posterior à EC 136.
        # Antes da transição, preserva-se a SELIC histórica/corrente (SGS 4390).
        "selic": {**selic_historica, **base["selic"]},
        "selic_limite": adicional["selic"],
        # A cobertura combinada só é segura até a consulta mais antiga entre
        # as fontes necessárias, evitando considerar completo um mês parcial.
        "obtido_em": min(base["obtido_em"], adicional["obtido_em"]),
        "fontes": {
            **base.get("fontes", {}),
            **adicional.get("fontes", {}),
            "selic_historica": historica["fonte"],
        },
    }


def ultima_data_disponivel(dados, perfil=ATUAL):
    """Último mês fechado com todas as séries exigidas pelo perfil selecionado."""
    competencias = set(dados.get("selic", {})) | set(dados.get("ipcae_taxas", {}))
    if perfil == FAZENDA_4:
        competencias |= set(dados.get("selic_limite", {}))
    if not competencias:
        raise ValueError("Não há índices oficiais disponíveis para cálculo.")
    ultimo_mes = date.fromisoformat(max(competencias) + "-01")
    primeiro_mes = date.fromisoformat(min(competencias) + "-01")
    regime_atual = {
        FAZENDA_1: INICIO_TEMA_905,
        FAZENDA_2: INICIO,
        FAZENDA_3: TRANSICAO,
        FAZENDA_4: TRANSICAO,
    }[perfil]
    # Bases reduzidas de teste podem começar depois de 2009. A cobertura
    # corrente é aferida de forma contínua apenas no regime mais recente.
    inicio = max(regime_atual, primeiro_mes) if ultimo_mes >= regime_atual else max(
        INICIO_TEMA_905, primeiro_mes
    )
    limites = []
    obtido_em = date.fromisoformat(dados["obtido_em"])
    while inicio <= ultimo_mes:
        fim = proximo_mes(inicio) - timedelta(days=1)
        if fim >= obtido_em:
            break
        completo = True
        atual = inicio
        while atual <= fim:
            competencia = atual.strftime("%Y-%m")
            if perfil == FAZENDA_1 or atual < INICIO:
                completo = (
                    competencia in dados["ipcae_taxas"]
                    and referencia_poupanca(atual) in dados["poupanca_total"]
                )
            elif perfil == FAZENDA_2 or atual < TRANSICAO:
                completo = competencia in dados["selic"]
            elif perfil == FAZENDA_3:
                completo = (
                    competencia in dados["ipcae_taxas"]
                    and referencia_poupanca(atual) in dados["poupanca_total"]
                )
            else:
                completo = (
                    competencia in dados["ipcae_taxas"]
                    and competencia in dados["selic_limite"]
                )
            if not completo:
                break
            atual += timedelta(days=1)
        if not completo:
            break
        limites.append(fim)
        inicio = proximo_mes(inicio)
    if not limites:
        raise ValueError("Não há mês com índices completos disponíveis para cálculo.")
    return max(limites)


def ultima_data_ipcae(dados=None):
    """Último mês fechado com taxa oficial IPCA-15/IPCA-E disponível."""
    dados = dados or carregar_base()
    obtido_em = date.fromisoformat(dados["obtido_em"])
    limites = []
    for competencia in sorted(dados["ipcae_taxas"]):
        inicio = date.fromisoformat(competencia + "-01")
        fim = proximo_mes(inicio) - timedelta(days=1)
        if inicio >= INICIO_TEMA_905 and fim < obtido_em:
            limites.append(fim)
    if not limites:
        raise ValueError("Não há mês fechado com taxas IPCA-15 do IBGE disponíveis para as custas e despesas.")
    return max(limites)


def calcular_custas_despesas_ipcae(
    itens: list[CustaDespesaProcessual],
    data_base: date,
    dados=None,
) -> list[ResultadoCustaDespesaProcessual]:
    """Atualiza cada lançamento pelo IPCA-E, sem juros ou cumulação com outro encargo."""
    if not itens:
        return []
    dados = dados or carregar_base()
    limite = ultima_data_ipcae(dados)
    if data_base > limite:
        raise ValueError(
            f"Para custas e despesas, a data-base máxima permitida é {limite.strftime('%d/%m/%Y')}, "
            "último mês fechado com taxa oficial IPCA-15/IPCA-E disponível."
        )
    resultados = []
    for item in itens:
        saldo = item.valor
        fator_total = D(1)
        memoria = []
        for ini, ate, fracao in trechos(item.data, data_base):
            competencia = ini.strftime("%Y-%m")
            taxa = consultar(dados, "ipcae_taxas", competencia)
            fator = fator_ipcae(dados, competencia, fracao)
            anterior = saldo
            saldo *= fator
            fator_total *= fator
            memoria.append(MemoriaMensal(
                parcela=item.numero,
                competencia=competencia,
                indice_aplicado="IPCA-E IBGE — custas e despesas processuais",
                valor_base=moeda(anterior),
                fator_aplicado=fator,
                valor_corrigido=moeda(saldo),
                total=moeda(saldo),
                observacao=(
                    f"{ini} a {ate}; taxa IPCA-15 {taxa}%; "
                    f"(1 + taxa / 100) ^ {fracao}; atualização exclusiva pelo IPCA-E, sem juros."
                ),
            ))
        valor_atualizado = moeda(saldo)
        resultados.append(ResultadoCustaDespesaProcessual(
            numero=item.numero,
            nome=item.nome,
            data=item.data,
            valor_original=item.valor,
            fator_ipcae=fator_total,
            correcao_monetaria=moeda(valor_atualizado - item.valor),
            valor_atualizado=valor_atualizado,
            memoria=memoria,
        ))
    return resultados


def incorporar_descontos(resultado: ResultadoCalculo, calculo: CalculoSimplificado):
    """Atualiza os abatimentos em operação autônoma e desconta-os na data-base."""
    operacao = calculo.descontos
    selecionados = [item for item in operacao.itens if item.aplicar]
    if operacao.itens:
        resultado.premissas["selecao_descontos"] = [item.model_dump(mode="json") for item in operacao.itens]
    if not selecionados:
        return resultado
    perfil = operacao.perfil or calculo.perfil
    dados = calculo.dados_gerais.model_dump()
    dados.update(criterio_inicio_juros="vencimento" if perfil in ("selic_cjf_v1", "poupanca_deposito_v1") else operacao.criterio_inicio_juros,
                 data_inicial_juros=operacao.data_inicial_juros)
    if perfil == "poupanca_deposito_v1":
        from .motor_poupanca_deposito import calcular_depositos
        descontos = calcular_depositos(dados, selecionados)
    else:
        descontos = executar_calculo(CalculoSimplificado(
            perfil=perfil, dados_gerais=DadosSimplificados(**dados),
            parcelas=[ParcelaSimplificada(numero=item.numero, historico=item.descricao,
                                         data_vencimento=item.data, valor_bruto=item.valor,
                                         valor_pago_na_data=item.encargos_sem_atualizacao)
                      for item in selecionados],
        ))
    # A operação de índices recebe somente a base ainda atualizável. A parcela
    # nominal expressamente excluída retorna ao abatimento sem novos encargos.
    for item, pago in zip(descontos.parcelas, selecionados):
        nominal = pago.encargos_sem_atualizacao
        item.valor_pago_na_data = D(0)
        item.valor_apurado = pago.valor
        item.valor_corrigido += nominal
        item.total_parcela += nominal
        if nominal:
            for registro in [*item.memoria_correcao, *item.memoria_juros]:
                parte = "parcela fora da conta" if perfil == "poupanca_deposito_v1" else "encargos já pagos"
                registro.observacao += f" Valor total R$ {pago.valor:.2f}; R$ {nominal:.2f} de {parte} são abatidos nominalmente, sem nova incidência."
    descontos.resumo.valor_pago_na_data_parcelas = D(0)
    descontos.resumo.principal_apurado = descontos.resumo.principal_original
    descontos.resumo.total_atualizado = sum((item.total_parcela for item in descontos.parcelas), D(0))
    descontos.premissas["composicao_pagamentos"] = [item.model_dump(mode="json") for item in selecionados]
    resultado.descontos = descontos
    saldo = resultado.resumo.total_atualizado
    for item in descontos.parcelas:
        abatido = min(saldo, item.total_parcela)
        resultado.memorias_abatimento.append(MemoriaAbatimento(
            data_pagamento=item.data_vencimento, historico=item.historico,
            valor_original=item.valor_bruto, correcao_monetaria=item.correcao_monetaria,
            juros_mora=item.juros_mora, valor_abatido=abatido,
            saldo_anterior=saldo, saldo_posterior=saldo - abatido,
            saldo_remanescente=item.total_parcela - abatido,
        ))
        saldo -= abatido
    resultado.resumo.abatimentos = moeda(resultado.resumo.total_atualizado - saldo)
    resultado.resumo.total_atualizado = moeda(saldo)
    excesso = moeda(descontos.resumo.total_atualizado - resultado.resumo.abatimentos)
    resultado.premissas["descontos"] = {
        "perfil": perfil, "quantidade": len(selecionados),
        "valor_original": str(descontos.resumo.principal_original),
        "valor_atualizado": str(descontos.resumo.total_atualizado),
        "valor_abatido": str(resultado.resumo.abatimentos), "excedente": str(excesso),
    }
    resultado.premissas.setdefault("metodologia", []).append(
        "Descontos: cada lançamento é atualizado desde a sua data até a data-base, "
        "com os encargos próprios da operação, e abatido do total atualizado das parcelas. "
        "Não altera o pagamento no vencimento nem recalcula o saldo em cada data de pagamento. "
        "As custas e despesas são acrescidas depois dos descontos."
    )
    resultado.alertas.extend(f"Descontos: {alerta}" for alerta in descontos.alertas)
    if excesso:
        resultado.alertas.append(
            f"Os descontos atualizados superam as parcelas em R$ {excesso:.2f}. "
            "O abatimento foi limitado ao total das parcelas; o excedente não foi compensado com custas e despesas."
        )
    return resultado


def incorporar_custas_despesas(
    resultado: ResultadoCalculo,
    calculo: CalculoSimplificado,
) -> ResultadoCalculo:
    from .multas_parcelas import incorporar_multas_parcelas
    resultado = incorporar_multas_parcelas(resultado, calculo)
    resultado = incorporar_descontos(resultado, calculo)
    itens = calcular_custas_despesas_ipcae(
        calculo.custas_despesas,
        calculo.dados_gerais.data_base,
    )
    total = sum((item.valor_atualizado for item in itens), D(0))
    resultado.custas_despesas = itens
    resultado.resumo.custas = total
    resultado.resumo.total_atualizado = moeda(resultado.resumo.total_atualizado + total)
    resultado.premissas["custas_despesas"] = {
        "criterio": "IPCA-E oficial do IBGE, formado pelas variações mensais do IPCA-15, sem juros ou outros encargos.",
        "quantidade": len(itens),
        "valor_original": str(sum((item.valor_original for item in itens), D(0))),
        "correcao_monetaria": str(sum((item.correcao_monetaria for item in itens), D(0))),
        "valor_atualizado": str(total),
    }
    if itens:
        resultado.premissas.setdefault("criterios", []).append(
            "Custas e despesas processuais: atualização exclusiva pelo IPCA-E desde a data de cada lançamento até a data-base."
        )
        resultado.premissas.setdefault("metodologia", []).append(
            "As custas e despesas são apuradas separadamente do principal, não recebem juros e não alteram a base dos demais encargos. Seus valores atualizados são somados somente ao total final."
        )
        resultado.premissas.setdefault("fontes", {}).setdefault(
            "ipcae_custas", dados_fonte_ipcae()
        )
    from .honorarios_principais import incorporar_honorarios_principais
    return incorporar_honorarios_principais(resultado, calculo)


def dados_fonte_ipcae():
    return carregar_base().get("fontes", {}).get("ipcae", "")


def criterios_publicos(dados=None, perfil=ATUAL):
    if perfil == "poupanca_deposito_v1":
        from .motor_poupanca_deposito import criterios_poupanca
        return criterios_poupanca()
    if perfil == "ipca_taxa_legal_v1":
        from .motor_ipca_taxa_legal import criterios_ipca_taxa_legal
        criterios = criterios_ipca_taxa_legal()
        criterios["data_base_maxima_ipcae"] = ultima_data_ipcae().isoformat()
        return criterios
    if perfil == CIVIL_2:
        from .motor_civil_2 import criterios_civil_2
        criterios = criterios_civil_2()
        criterios["data_base_maxima_ipcae"] = ultima_data_ipcae().isoformat()
        return criterios
    if perfil == "selic_cjf_v1":
        from .motor_selic_cjf import criterios_cjf
        criterios = criterios_cjf()
        criterios["data_base_maxima_ipcae"] = ultima_data_ipcae().isoformat()
        return criterios
    if perfil == IPCAE_1AM_SIMPLES:
        from .motor_ipcae_1am import criterios_ipcae_1am
        criterios = criterios_ipcae_1am(dados)
        criterios["data_base_maxima_ipcae"] = ultima_data_ipcae(dados).isoformat()
        return criterios
    if perfil not in PERFIS_FAZENDA:
        raise ValueError("Padrão de cálculo desconhecido.")
    if dados is None:
        dados = carregar_base_ec136_completa() if perfil == FAZENDA_4 else carregar_base()
    elif perfil == FAZENDA_4 and "selic_limite" not in dados:
        dados = carregar_base_ec136_completa()
    configuracao = {
        FAZENDA_1: {
            "versao": "fazenda_publica_1_ipcae_poupanca_v1",
            "inicio_selic": "", "transicao": "",
            "contagem": "IPCA-E proporcional geométrico e juros simples pela remuneração total da poupança em todo o período.",
        },
        FAZENDA_2: {
            "versao": "fazenda_publica_2_ipcae_poupanca_selic_v1",
            "inicio_selic": INICIO.isoformat(), "transicao": "",
            "contagem": "IPCA-E e poupança até 08/12/2021; SELIC simples a partir de 09/12/2021.",
        },
        FAZENDA_3: {
            "versao": "tema905_ipcae_ibge_poupanca_total_v4",
            "inicio_selic": INICIO.isoformat(), "transicao": TRANSICAO.isoformat(),
            "contagem": "IPCA-E e poupança até 08/12/2021; SELIC simples até 09/09/2025; IPCA-E e poupança a partir de 10/09/2025.",
        },
        FAZENDA_4: {
            "versao": "fazenda_publica_4_ipcae_poupanca_selic_ipcae_2aa_limite_v1",
            "inicio_selic": INICIO.isoformat(), "transicao": TRANSICAO.isoformat(),
            "contagem": "IPCA-E e poupança até 08/12/2021; SELIC simples até 09/09/2025; IPCA-E e juros simples de 2% a.a., limitados à SELIC quando inferior, a partir de 10/09/2025.",
        },
    }[perfil]
    return {
        "perfil": perfil, "perfis": PERFIS,
        "versao_metodologia": configuracao["versao"],
        "inicio": INICIO_TEMA_905.isoformat(),
        "inicio_selic": configuracao["inicio_selic"],
        "transicao": configuracao["transicao"],
        "data_base_maxima": ultima_data_disponivel(dados, perfil).isoformat(),
        "data_base_maxima_ipcae": ultima_data_ipcae(dados).isoformat(),
        "atualizado_em": dados["obtido_em"], "fontes": dados["fontes"],
        "contagem": configuracao["contagem"] + " Dias inicial e final incluídos; meses parciais proporcionais.",
    }


def executar_calculo(calculo: CalculoSimplificado) -> ResultadoCalculo:
    if calculo.perfil == "ipca_taxa_legal_v1":
        from .motor_ipca_taxa_legal import executar_ipca_taxa_legal
        return incorporar_custas_despesas(executar_ipca_taxa_legal(calculo), calculo)
    if calculo.perfil == CIVIL_2:
        from .motor_civil_2 import executar_civil_2
        return incorporar_custas_despesas(executar_civil_2(calculo), calculo)
    if calculo.perfil == "selic_cjf_v1":
        from .motor_selic_cjf import executar_cjf
        return incorporar_custas_despesas(executar_cjf(calculo), calculo)
    if calculo.perfil == IPCAE_1AM_SIMPLES:
        from .motor_ipcae_1am import executar_ipcae_1am
        return incorporar_custas_despesas(executar_ipcae_1am(calculo), calculo)
    dados = carregar_base_ec136_completa() if calculo.perfil == FAZENDA_4 else carregar_base()
    fazenda_1 = calculo.perfil == FAZENDA_1
    fazenda_2 = calculo.perfil == FAZENDA_2
    fazenda_3 = calculo.perfil == FAZENDA_3
    fazenda_4 = calculo.perfil == FAZENDA_4
    fim = calculo.dados_gerais.data_base
    limite = ultima_data_disponivel(dados, calculo.perfil)
    if fim > limite:
        raise ValueError(
            f"A data-base máxima permitida é {limite.strftime('%d/%m/%Y')}, "
            "último mês com todos os índices necessários disponíveis. "
            "Não é permitido calcular ou exportar períodos posteriores com índices incompletos."
        )
    resultados = []
    memorias = []
    for p in calculo.parcelas:
        principal = p.valor_bruto - p.valor_pago_na_data
        saldo = principal
        fator_pre, fator_pos = D(1), D(1)
        mem_corr, mem_juros = [], []
        # Todos os perfis da Fazenda começam com IPCA-E. No perfil 1 essa
        # faixa prossegue até a data-base; nos demais termina em 08/12/2021.
        limite_ipca_pre = fim if fazenda_1 else min(fim, INICIO - timedelta(days=1))
        for ini, ate, fracao in trechos(p.data_vencimento, limite_ipca_pre):
            comp = ini.strftime("%Y-%m")
            taxa = consultar(dados, "ipcae_taxas", comp)
            fator = fator_ipcae(dados, comp, fracao)
            anterior = saldo
            saldo *= fator
            fator_pre *= fator
            mem_corr.append(MemoriaMensal(
                parcela=p.numero, competencia=comp,
                indice_aplicado="IPCA-E IBGE (IPCA-15)" if fazenda_1 else "IPCA-E IBGE (IPCA-15) — Tema 905",
                valor_base=moeda(anterior), fator_aplicado=fator,
                valor_corrigido=moeda(saldo), total=moeda(saldo),
                observacao=(
                    f"{ini} a {ate}; taxa IPCA-15 {taxa}%; (1 + taxa / 100) ^ {fracao}; "
                    + ("Fazenda Pública 1, sem incorporar juros ao principal."
                       if fazenda_1 else "Tema 905 até 08/12/2021, sem incorporar juros ao principal.")
                ),
            ))
        base_selic = saldo
        taxa_selic = D(0)
        if not fazenda_1:
            limite_selic = fim if fazenda_2 else min(fim, TRANSICAO - timedelta(days=1))
            for ini, ate, fracao in trechos(max(p.data_vencimento, INICIO), limite_selic):
                comp = ini.strftime("%Y-%m")
                taxa = consultar(dados, "selic", comp)
                anterior = saldo
                taxa_selic += taxa / 100 * fracao
                saldo = base_selic * (1 + taxa_selic)
                mem_corr.append(MemoriaMensal(
                    parcela=p.numero, competencia=comp, indice_aplicado="SELIC única",
                    valor_base=base_selic, fator_aplicado=1 + taxa / 100 * fracao,
                    valor_corrigido=moeda(saldo), total=moeda(saldo),
                    observacao=f"{ini} a {ate}; fração {fracao}; taxa mensal {taxa}%; acréscimo {moeda(saldo-anterior)}; acumulação simples, correção e mora reunidas.",
                ))
        saldo_transicao = saldo
        inicio_ipca_pos = max(p.data_vencimento, TRANSICAO) if (fazenda_3 or fazenda_4) else fim + timedelta(days=1)
        for ini, ate, fracao in trechos(inicio_ipca_pos, fim):
            comp = ini.strftime("%Y-%m")
            taxa = consultar(dados, "ipcae_taxas", comp)
            fator = fator_ipcae(dados, comp, fracao)
            anterior = saldo
            saldo *= fator
            fator_pos *= fator
            mem_corr.append(MemoriaMensal(
                parcela=p.numero, competencia=comp, indice_aplicado="IPCA-E IBGE (IPCA-15)",
                valor_base=moeda(anterior), fator_aplicado=fator,
                valor_corrigido=moeda(saldo), total=moeda(saldo),
                observacao=f"{ini} a {ate}; taxa IPCA-15 {taxa}%; (1 + taxa / 100) ^ {fracao}; saldo consolidado na transição {moeda(saldo_transicao)}.",
            ))
        # Juros simples sobre o saldo corrigido final, sem juros sobre juros da poupança.
        juros = D(0)
        taxas_poupanca = {"pre": D(0), "pos": D(0)}
        juros_pre = D(0)
        inicio_juros = calculo.inicio_juros_parcela(p)
        if fazenda_1:
            trechos_juros = [*trechos(inicio_juros, fim)]
        elif fazenda_3:
            trechos_juros = [
                *trechos(inicio_juros, min(fim, INICIO - timedelta(days=1))),
                *trechos(max(inicio_juros, TRANSICAO), fim),
            ]
        else:
            trechos_juros = [*trechos(inicio_juros, min(fim, INICIO - timedelta(days=1)))]
        for ini, ate, fracao in trechos_juros:
            taxa_proporcional = D(0)
            atual = ini
            taxas = set()
            referencias = []
            while atual <= ate:
                referencia = referencia_poupanca(atual)
                taxa = consultar(dados, "poupanca_total", referencia)
                serie = "25" if referencia < "2012-05-04" else "195"
                referencias.append(f"{atual.isoformat()}: ref. {referencia}, {taxa}%, SGS {serie}")
                taxas.add(str(taxa))
                taxa_proporcional += taxa / 100 / monthrange(atual.year, atual.month)[1]
                atual += timedelta(days=1)
            valor_periodo = saldo * taxa_proporcional
            juros += valor_periodo
            taxas_poupanca["pre" if ini < INICIO or fazenda_1 else "pos"] += taxa_proporcional
            if ini < INICIO:
                juros_pre += valor_periodo
            mem_juros.append(MemoriaMensal(
                parcela=p.numero, competencia=ini.strftime("%Y-%m"), indice_aplicado="Juros da poupança",
                valor_base=moeda(saldo), fator_aplicado=1 + taxa_proporcional,
                valor_corrigido=moeda(saldo), juros_periodo=moeda(valor_periodo),
                juros_acumulados=moeda(juros), total=moeda(saldo) + moeda(juros),
                observacao=f"{ini} a {ate}; {'Fazenda Pública 1' if fazenda_1 else 'Tema 905' if ini < INICIO else 'art. 1º-F'}; fração {fracao}; taxas mensais totais {', '.join(sorted(taxas))}%; remuneração total; juros simples sobre o saldo corrigido final, sem integrar a base da SELIC. Referências: {'; '.join(referencias)}.",
            ))
        taxa_2aa, taxa_limite, juros_pos, ajuste = D(0), D(0), D(0), D(0)
        if fazenda_4:
            for ini, ate, fracao in trechos(max(inicio_juros, TRANSICAO), fim):
                taxa = D("0.02") / 12 * fracao
                taxa_2aa += taxa
                valor = saldo * taxa
                juros_pos += valor
                mem_juros.append(MemoriaMensal(
                    parcela=p.numero, competencia=ini.strftime("%Y-%m"), indice_aplicado="Juros simples 2% a.a.",
                    valor_base=saldo, fator_aplicado=1 + taxa, valor_corrigido=moeda(saldo),
                    juros_periodo=moeda(valor), juros_acumulados=moeda(juros_pos), total=moeda(saldo)+moeda(juros_pos),
                    observacao=f"{ini} a {ate}; 2% / 12 × fração mensal {fracao}; base: saldo corrigido final; sem capitalização; sujeito ao limite da SELIC.",
                ))
            juros += juros_pos
            for ini, ate, fracao in trechos(max(p.data_vencimento, TRANSICAO), fim):
                taxa = consultar(dados, "selic_limite", ini.strftime("%Y-%m"))
                taxa_limite += taxa / 100 * fracao
                mem_corr.append(MemoriaMensal(
                    parcela=p.numero, competencia=ini.strftime("%Y-%m"), indice_aplicado="SELIC de comparação (limite)",
                    valor_base=saldo_transicao, fator_aplicado=1 + taxa / 100 * fracao,
                    valor_corrigido=moeda(saldo_transicao * (1 + taxa_limite)),
                    total=moeda(saldo_transicao * (1 + taxa_limite)),
                    observacao=f"{ini} a {ate}; taxa mensal {taxa}%; fração {fracao}; soma simples. Valor comparativo, não somar à parcela.",
                ))
            teto = moeda(saldo_transicao * (1 + taxa_limite))
            candidato = moeda(saldo) + moeda(juros_pos)
            ajuste = min(D(0), teto - candidato)
            if max(p.data_vencimento, TRANSICAO) <= fim:
                mem_corr.append(MemoriaMensal(
                    parcela=p.numero, competencia=fim.strftime("%Y-%m"), indice_aplicado="Aplicação do limite SELIC",
                    valor_base=saldo_transicao, fator_aplicado=1 + taxa_limite,
                    valor_corrigido=moeda(saldo)+ajuste, total=candidato+ajuste,
                    observacao=f"Comparação de todo o período {max(p.data_vencimento, TRANSICAO)} a {fim}: IPCA-E + 2% = {candidato}; SELIC = {teto}; ajuste = {ajuste}; menor valor = {candidato+ajuste}. Juros anteriores à EC 113 permanecem separados.",
                ))
        def componente(inicial, final, base, valor, fator=None, taxa=None):
            if inicial > final:
                return ComponenteCalculo()
            return ComponenteCalculo(data_inicial=inicial, data_final=final, base_calculo=base,
                                     valor=valor, fator_acumulado=fator,
                                     taxa_acumulada_percentual=taxa * 100 if taxa is not None else None)

        # Diferenças dos saldos arredondados conciliam os centavos sem alterar o motor.
        if fazenda_1:
            componentes = {
                "ipcae_pre": componente(p.data_vencimento, fim, principal,
                                         moeda(saldo) - principal, fator=fator_pre),
                "poupanca_pre": componente(inicio_juros, fim, saldo,
                                             moeda(juros), taxa=taxas_poupanca["pre"]),
            }
        elif fazenda_2:
            componentes = {
                "ipcae_pre": componente(p.data_vencimento, min(fim, INICIO - timedelta(days=1)),
                                         principal, moeda(base_selic) - principal, fator=fator_pre),
                "poupanca_pre": componente(inicio_juros, min(fim, INICIO - timedelta(days=1)),
                                             saldo, moeda(juros), taxa=taxas_poupanca["pre"]),
                "selic": componente(max(p.data_vencimento, INICIO), fim,
                                     base_selic, moeda(saldo) - moeda(base_selic), taxa=taxa_selic),
            }
        elif fazenda_3:
            componentes = {
                "ipcae_pre": componente(p.data_vencimento, min(fim, INICIO - timedelta(days=1)),
                                         principal, moeda(base_selic) - principal, fator=fator_pre),
                "selic": componente(max(p.data_vencimento, INICIO), min(fim, TRANSICAO - timedelta(days=1)),
                                     base_selic, moeda(saldo_transicao) - moeda(base_selic), taxa=taxa_selic),
                "ipcae_pos": componente(max(p.data_vencimento, TRANSICAO), fim,
                                         saldo_transicao, moeda(saldo) - moeda(saldo_transicao), fator=fator_pos),
                "poupanca_pre": componente(inicio_juros, min(fim, INICIO - timedelta(days=1)),
                                            saldo, moeda(juros_pre), taxa=taxas_poupanca["pre"]),
                "poupanca_pos": componente(max(inicio_juros, TRANSICAO), fim,
                                             saldo, moeda(juros) - moeda(juros_pre), taxa=taxas_poupanca["pos"]),
            }
        else:
            componentes = {
                "ipcae_pre": componente(p.data_vencimento, min(fim, INICIO - timedelta(days=1)),
                                         principal, moeda(base_selic) - principal, fator=fator_pre),
                "poupanca_pre": componente(inicio_juros, min(fim, INICIO - timedelta(days=1)),
                                             saldo, moeda(juros_pre), taxa=taxas_poupanca["pre"]),
                "selic": componente(max(p.data_vencimento, INICIO), min(fim, TRANSICAO - timedelta(days=1)),
                                     base_selic, moeda(saldo_transicao) - moeda(base_selic), taxa=taxa_selic),
                "ipcae_pos": componente(max(p.data_vencimento, TRANSICAO), fim,
                                         saldo_transicao, moeda(saldo) - moeda(saldo_transicao), fator=fator_pos),
                "juros_2aa": componente(max(inicio_juros, TRANSICAO), fim, saldo,
                                          moeda(juros_pos), taxa=taxa_2aa),
                "limite_selic": componente(max(p.data_vencimento, TRANSICAO), fim,
                                             saldo_transicao, ajuste, taxa=taxa_limite),
            }
        rp = ResultadoParcela(
            numero=p.numero, historico=p.historico, data_vencimento=p.data_vencimento,
            valor_bruto=p.valor_bruto, valor_pago_na_data=p.valor_pago_na_data,
            valor_apurado=principal, correcao_monetaria=moeda(saldo)-principal+ajuste,
            valor_corrigido=moeda(saldo)+ajuste, juros_mora=moeda(juros),
            total_parcela=moeda(saldo)+moeda(juros)+ajuste, memoria_correcao=mem_corr, memoria_juros=mem_juros,
            componentes=componentes,
        )
        resultados.append(rp)
        memorias.extend(mem_corr + mem_juros)
    def total(campo):
        return sum((getattr(p, campo) for p in resultados), D(0))
    resultado = ResultadoCalculo(
        dados_gerais=DadosGerais(**calculo.dados_gerais.model_dump(), tipo_devedor="fazenda_publica"),
        parcelas=resultados, memoria_mensal=memorias,
        resumo=ResumoGeral(
            principal_original=total("valor_bruto"), valor_pago_na_data_parcelas=total("valor_pago_na_data"),
            principal_apurado=total("valor_apurado"), correcao_monetaria=total("correcao_monetaria"),
            juros_mora=total("juros_mora"), total_atualizado=total("total_parcela"),
            totais_componentes={chave: sum((p.componentes[chave].valor for p in resultados), D(0))
                               for chave in resultados[0].componentes},
        ),
        premissas={
            **criterios_publicos(dados, calculo.perfil), "entrada": calculo.model_dump(mode="json"),
            "sha256_base": hashlib.sha256(BASE.read_bytes()).hexdigest(),
            "criterios": ["01/07/2009 a 08/12/2021: Tema 905/STJ — IPCA-E oficial do IBGE, formado pelo IPCA-15, e juros simples pela remuneração total da poupança.",
                          "09/12/2021 a 09/09/2025: SELIC como índice único de atualização monetária e juros de mora.",
                          "A partir de 10/09/2025: IPCA-E oficial do IBGE, formado pelo IPCA-15, e juros da poupança (art. 1º-F da Lei 9.494/97, redação da Lei 11.960/09)."],
            "metodologia": [
                "Tema 905: IPCA-E até 08/12/2021. O principal corrigido nesse período constitui a base da SELIC a partir de 09/12/2021. Os juros da poupança permanecem separados e não integram essa base.",
                "SELIC: soma das taxas mensais BCB SGS 4390, ponderadas pelos dias corridos de cada mês, sobre o principal corrigido até 08/12/2021 ou sobre o principal apurado para vencimentos posteriores.",
                "IPCA-E: produto das variações mensais do IPCA-15 produzidas pelo IBGE e distribuídas na série SGS 7478. Em meses parciais, o fator (1 + taxa/100) é elevado à fração dos dias; deflações são preservadas.",
                "Poupança: remuneração total publicada pelo Banco Central (SGS 25 até 03/05/2012 e SGS 195 desde 04/05/2012), considerada integralmente. Juros simples nos períodos anterior e posterior à SELIC, sobre o saldo corrigido final, conforme a convenção do motor existente; sem juros sobre juros da poupança.",
                "As taxas das séries SGS 25 e 195 são percentuais mensais por data inicial do período, não taxas diárias. Cada dia recebe a taxa mensal da referência dividida pelos dias do mês. Referências dos dias 29, 30 e 31 usam o dia 1 do mês seguinte, conforme a convenção de aniversário da poupança. Referência ausente impede o cálculo; não se repete o último índice.",
                "A data de início dos juros limita a poupança nos dois períodos. Na faixa de 09/12/2021 a 09/09/2025 a SELIC é indivisível e começa no maior entre vencimento e 09/12/2021.",
                "Dias inicial e final incluídos. Arredondamento HALF_UP por parcela ao final, sem arredondar fatores intermediários. Memórias mensais exibem valores arredondados.",
                "A rubrica Atualização reúne o acréscimo da SELIC única e a correção pelo IPCA-E; Juros de mora contém somente a poupança.",
                "As colunas por período mostram o fator acumulado do IPCA-E e as taxas percentuais acumuladas simples da SELIC e da poupança. Índices exibidos com quatro casas decimais; o cálculo conserva a precisão integral. Traço indica período não incidente. Os valores de atualização por período são diferenças dos saldos arredondados; o último período da poupança recebe a diferença para o total arredondado, conciliando os centavos sem alterar o total da parcela.",
            ],
        },
    )
    if fazenda_1:
        resultado.premissas["criterios"] = [
            "A partir de 01/07/2009: IPCA-E oficial do IBGE, formado pelo IPCA-15, e juros simples pela remuneração total da poupança.",
        ]
        resultado.premissas["metodologia"] = [
            "IPCA-E: produto das variações mensais do IPCA-15 produzidas pelo IBGE e distribuídas na série SGS 7478. Em meses parciais, o fator é elevado à fração dos dias; deflações são preservadas.",
            "Poupança: remuneração total publicada pelo Banco Central (SGS 25 até 03/05/2012 e SGS 195 desde 04/05/2012), em juros simples sobre o saldo corrigido final, sem juros sobre juros.",
            "A data de início dos juros limita somente a poupança e respeita o vencimento. IPCA-E e poupança seguem até a data-base, sem troca de regime.",
            "Dias inicial e final incluídos. Arredondamento HALF_UP por parcela ao final, sem arredondar fatores intermediários.",
        ]
    elif fazenda_2:
        resultado.premissas["criterios"] = [
            "01/07/2009 a 08/12/2021: IPCA-E oficial do IBGE, formado pelo IPCA-15, e juros simples pela remuneração total da poupança.",
            "A partir de 09/12/2021: SELIC como índice único de atualização monetária e juros de mora.",
        ]
        resultado.premissas["metodologia"] = [
            "Até 08/12/2021, o principal recebe IPCA-E e os juros da poupança permanecem separados. O principal corrigido constitui a base da SELIC a partir de 09/12/2021.",
            "SELIC: soma simples das taxas mensais BCB SGS 4390, ponderadas pelos dias corridos de cada mês, sem capitalização e sem cumulação com poupança após 09/12/2021.",
            "A data de início dos juros limita somente a poupança até 08/12/2021 e respeita o vencimento. A SELIC começa no maior entre vencimento e 09/12/2021.",
            "Dias inicial e final incluídos. Arredondamento HALF_UP por parcela ao final, sem arredondar fatores intermediários.",
        ]
    elif fazenda_4:
        resultado.premissas["sha256_base_ec136"] = hashlib.sha256(BASE_EC136.read_bytes()).hexdigest()
        resultado.premissas["sha256_base_selic_historica"] = hashlib.sha256(BASE_SELIC_HISTORICA.read_bytes()).hexdigest()
        resultado.premissas["criterios"] = [
            "01/07/2009 a 08/12/2021: IPCA-E oficial do IBGE, formado pelo IPCA-15, e juros simples pela remuneração total da poupança.",
            "09/12/2021 a 09/09/2025: SELIC como índice único de atualização monetária e juros de mora.",
            "A partir de 10/09/2025: IPCA-E oficial do IBGE, formado pelo IPCA-15, e juros simples de 2% ao ano, com comparação ao limite SELIC do mesmo período.",
        ]
        resultado.premissas["metodologia"] = [
            "Até 08/12/2021, o principal recebe IPCA-E e os juros da poupança permanecem separados. O principal corrigido constitui a base da SELIC a partir de 09/12/2021.",
            "De 09/12/2021 a 09/09/2025: somam-se as taxas mensais BCB SGS 4390, sem capitalização, como índice único de atualização e mora.",
            "Após 10/09/2025: o saldo consolidado recebe IPCA-E pelo produto das variações mensais do IPCA-15 (IBGE, série SGS 7478). Meses parciais usam o fator elevado à fração dos dias do mês; deflações são preservadas.",
            "Os juros simples de 2% ao ano usam 2% / 12 por mês, proporcionais aos dias de cada mês, sobre o saldo final corrigido pelo IPCA-E. Começam no maior entre vencimento, início dos juros informado e 10/09/2025. Não há capitalização desses juros.",
            "Limite: compara-se, por parcela, o saldo com IPCA-E mais os juros de 2% com o saldo consolidado acrescido da soma simples das taxas SELIC do mesmo período pós EC 136. Aplica-se o menor valor ao final do período, sem escolher índices mês a mês. A coluna Ajuste ao limite SELIC desconta eventual excesso; a taxa exibida nessa coluna é a SELIC de comparação, e zero significa que não houve redução. Juros anteriores à EC 113 ficam fora dessa comparação.",
            "Dias inicial e final incluídos. Índices e bases exibidos com quatro casas; valores em reais com duas. O cálculo conserva a precisão completa. Diferenças entre saldos arredondados conciliam os centavos. O total soma o principal e todas as colunas, inclusive o ajuste negativo ao limite, quando houver.",
        ]
    return incorporar_custas_despesas(resultado, calculo)
