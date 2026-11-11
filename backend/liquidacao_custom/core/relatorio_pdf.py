"""Demonstrativo A4 com bases, índices e valores por parcela."""
import io
from datetime import date
from decimal import Decimal

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Paragraph, Spacer

from .models import ComponenteCalculo, ResultadoCalculo
from .componentes import colunas_componentes, colunas_perfil
from .relatorio_componentes import componentes_liquidos, totais_liquidos, colunas_liquidas
from .relatorio_layout import (texto, moeda, data_br, criar_documento, criar_estilos,
    cabecalho as bloco_cabecalho, identificacao, observacoes, fontes_conferencia, criar_rodape, custas_despesas, separar_operacoes,
    resumo_financeiro, COLUNA_DESCRICAO, cabecalho_componente, tabela_operacional, anexo_tecnico, NOMES_FONTES)
from .relatorio_criterios import operacao, custas, criterios_metodologia
from .moedas_historicas import simbolo_moeda


def exportar_pdf(resultado: ResultadoCalculo) -> bytes:
    COLUNAS_COMPONENTES = colunas_liquidas(colunas_componentes(resultado))
    totais_exibidos = totais_liquidos(resultado.parcelas)
    novo = resultado.premissas.get("perfil") == "selic_ipcae_2aa_v1"
    cjf = resultado.premissas.get("perfil") == "selic_cjf_v1"
    civil_1 = resultado.premissas.get("perfil") in ("ipca_taxa_legal_v1", "civil_5_taxa_legal_reconstruida_v1")
    civil_2 = resultado.premissas.get("perfil") in ("civil_2_v1", "civil_3_v1")
    civil_4 = resultado.premissas.get("perfil") in ("civil_4_temporario_v1", "civil_6_v1")
    datas_independentes = civil_1 or civil_2 or civil_4
    somente_correcao = resultado.premissas.get("perfil") == "correcao_mensal_v1"
    referencia_selic = resultado.premissas.get("data_referencia_selic") if cjf else None
    data_cabecalho = referencia_selic or resultado.dados_gerais.data_base
    rotulo_data = "Data-base SELIC" if referencia_selic else "Data-base"
    ultima_selic = resultado.premissas.get("ultima_competencia_selic")
    indice_selic = date.fromisoformat(ultima_selic + "-01").strftime("%m/%Y") if ultima_selic else "nenhum"
    outras_operacoes = bool(resultado.custas_despesas or
        (resultado.honorarios_sucumbenciais and resultado.honorarios_sucumbenciais.data_protocolo) or
        (resultado.descontos and resultado.descontos.premissas.get("perfil") != "selic_cjf_v1"))
    com_multas = "multa_parcela" in resultado.resumo.totais_componentes
    sem_periodo_pre = novo and not any(c[0] == "ipcae_pre" for c in COLUNAS_COMPONENTES)
    buffer = io.BytesIO()
    pagina = landscape(A4)
    largura = pagina[0] - 80
    doc = criar_documento(buffer, f"{rotulo_data} {data_br(data_cabecalho)}; {resultado.premissas.get('versao_metodologia', '')}")
    estilos = criar_estilos()

    def p(conteudo, estilo="normal"):
        return Paragraph(texto(conteudo), estilos[estilo])

    r = resultado.resumo
    geral = resultado.dados_gerais
    header = bloco_cabecalho(largura, p, "Demonstrativo de cálculo",
        f"Atualização de parcelas / {rotulo_data} {data_br(data_cabecalho)}"
        f"{('  /  Último índice aplicado: ' + indice_selic) if referencia_selic else ''}"
        f"  /  {len(resultado.parcelas)} parcelas  /  {len(resultado.custas_despesas)} custas ou despesas",
        resultado.chave_recuperacao)
    partes = [header, Spacer(1, 14)]
    anexos = []

    colunas_resumo = COLUNAS_COMPONENTES
    if resultado.honorarios_sucumbenciais or resultado.cumprimento_sentenca:
        colunas_resumo = [(chave, nome, faixa) for chave, nome, faixa in COLUNAS_COMPONENTES
                         if any(p.componentes.get(chave, ComponenteCalculo()).data_inicial for p in resultado.parcelas)]
    titulos_resumo = (
        "Principal",
        *[nome for _, nome, _ in colunas_resumo],
        *(["(-) Descontos"] if resultado.descontos else []),
        *(["Honorários sucumbenciais"] if resultado.honorarios_sucumbenciais else []),
        *(["Multa art. 523"] if resultado.cumprimento_sentenca and resultado.cumprimento_sentenca.aplicar_multa else []),
        *(["Honorários art. 523"] if resultado.cumprimento_sentenca and resultado.cumprimento_sentenca.aplicar_honorarios else []),
        *(["Custas e despesas"] if resultado.custas_despesas else []),
        resultado.premissas.get("titulo_total", "TOTAL ATUALIZADO"),
    )
    valores_resumo = (
            r.principal_apurado,
            *[totais_exibidos.get(chave, 0) for chave, _, _ in colunas_resumo],
            *([-r.abatimentos] if resultado.descontos else []),
            *([resultado.honorarios_sucumbenciais.valor] if resultado.honorarios_sucumbenciais else []),
            *([resultado.cumprimento_sentenca.multa] if resultado.cumprimento_sentenca and resultado.cumprimento_sentenca.aplicar_multa else []),
            *([resultado.cumprimento_sentenca.honorarios] if resultado.cumprimento_sentenca and resultado.cumprimento_sentenca.aplicar_honorarios else []),
            *([r.custas] if resultado.custas_despesas else []),
            r.total_atualizado,
    )
    tabela_resumo = resumo_financeiro(titulos_resumo, valores_resumo, largura, p)
    partes += [Spacer(1, 4), tabela_resumo, Spacer(1, 8)]
    if r.valor_pago_na_data_parcelas:
        partes.append(p(f"Principal original: R$ {moeda(r.principal_original)}. Pagamentos no vencimento: R$ {moeda(r.valor_pago_na_data_parcelas)}.", "nota"))
    if not resultado.premissas.get("omitir_qualificacao", False):
        partes.extend(identificacao(geral, largura, p))
    partes.extend(observacoes(geral.observacoes, resultado.alertas, p))
    entradas = {x["numero"]: x for x in resultado.premissas.get("entrada", {}).get("parcelas", [])}
    if geral.criterio_inicio_juros == "vencimento":
        inicio_juros = "Vencimento de cada parcela"
    elif geral.criterio_inicio_juros in ("citacao", "data_fixa"):
        rotulo = "citação" if geral.criterio_inicio_juros == "citacao" else "data específica"
        inicio_juros = f"{data_br(geral.data_inicial_juros)} ({rotulo})"
    else:
        grupos = {}
        for parcela in resultado.parcelas:
            entrada = entradas.get(parcela.numero, {})
            data = entrada.get("data_inicial_juros")
            rotulo = data_br(data) if data and data != entrada.get("data_vencimento") else "Vencimento de cada parcela"
            grupos.setdefault(rotulo, []).append(str(parcela.numero))
        inicio_juros = next(iter(grupos)) if len(grupos) == 1 else "; ".join(
            f"Parcelas {', '.join(numeros)}: {rotulo}" for rotulo, numeros in grupos.items())
    criterios_principal = [criterio for criterio in resultado.premissas.get("criterios", [])
        if not criterio.startswith(("Honorários sucumbenciais:", "Art. 523,", "Honorários contratuais:", "Custas e despesas processuais:", "Descontos:"))
        and not (sem_periodo_pre and criterio.startswith("01/07/2009"))]

    inicio_creditos = len(partes)
    partes.append(p("CRÉDITO - ACRÉSCIMO", "secao"))
    nota_parcelas = p("Em cada coluna: valor usado como base, índice aplicado e valor acrescentado à parcela.", "nota")
    partes.append(nota_parcelas)
    curtos = {"ipcae_pre": "IPCA-E", "poupanca_pre": "Poupança", "selic": "SELIC", "ipcae_pos": "IPCA-E", "poupanca_pos": "Poupança", "juros_2aa": "Juros 2% a.a.", "limite_selic": "Limite SELIC", "multa_parcela": "Multa e encargos"}
    dados = [[p(x, "cabecalho") for x in ["Nº", COLUNA_DESCRICAO, "Correção desde" if datas_independentes else "Vencimento", "Principal", *[curtos.get(c, nome) for c, nome, _ in COLUNAS_COMPONENTES], "Total"]]]
    descricoes_extensas = {}
    largura_descricao = 120 if novo or com_multas else largura - 430 if len(COLUNAS_COMPONENTES) == 1 else largura - 496 if len(COLUNAS_COMPONENTES) == 2 else largura - 628
    for parcela in resultado.parcelas:
        descricao = parcela.historico or ""
        componentes_exibidos = componentes_liquidos(parcela.componentes)
        if parcela.valor_pago_na_data:
            descricao += f"\nOriginal: R$ {moeda(parcela.valor_bruto)}. Pago: R$ {moeda(parcela.valor_pago_na_data)}."
        if p(descricao, "celula").wrap(largura_descricao - 12, doc.height)[1] > doc.height - 90:
            descricoes_extensas[parcela.numero] = descricao
            descricao = f"Histórico integral da parcela {parcela.numero}: ver nota complementar após a tabela."
        indices = []
        for chave, _, _ in COLUNAS_COMPONENTES:
            c = componentes_exibidos.get(chave, ComponenteCalculo())
            if c.data_inicial is None:
                indices.append(p("-", "componente"))
            else:
                indice = (f"Fator {c.fator_acumulado:.4f}" if c.fator_acumulado is not None
                          else f"{c.taxa_acumulada_percentual:.6f}%" if chave in ("taxa_legal", "juros_1am") else f"{c.taxa_acumulada_percentual:.4f}%").replace(".", ",")
                base = f"{c.base_calculo:.4f}".replace(".", ",")
                periodo = f"{data_br(c.data_inicial)} a {data_br(c.data_final)}\n" if datas_independentes else ""
                indices.append(p(f"{periodo}Base {base}\n{indice}\nR$ {moeda(c.valor)}", "componente"))
        dados.append([p(str(parcela.numero), "celula"), p(descricao, "celula"), p(data_br(parcela.data_vencimento), "celula"),
                      p(moeda(parcela.valor_apurado), "numero"), *indices, p(moeda(parcela.total_parcela), "numero")])
    subtotal_parcelas = sum((parcela.total_parcela for parcela in resultado.parcelas), Decimal("0"))
    dados.append(["", p("TOTAL", "celula"), "", *[p(moeda(v), "numero") for v in (
        r.principal_apurado, *[totais_exibidos.get(chave, 0) for chave, _, _ in COLUNAS_COMPONENTES], subtotal_parcelas)]])
    larguras = [24, 120, 62, 64, *[(largura-346)/len(COLUNAS_COMPONENTES)]*len(COLUNAS_COMPONENTES), 76] if novo else [24, largura - 628, 62, 64, 82, 82, 74, 82, 82, 76]
    if cjf:
        larguras = [24, largura-430, 76, 90, 140, 100]
    elif len(COLUNAS_COMPONENTES) == 1:
        larguras = [24, largura-430, 76, 90, 140, 100]
    if datas_independentes:
        larguras = [24, largura-496, 76, 80, 108, 108, 100]
    elif len(COLUNAS_COMPONENTES) == 3:
        larguras = [24, largura-526, 76, 80, 90, 90, 90, 76]
    elif len(COLUNAS_COMPONENTES) == 2:
        larguras = [24, largura-496, 76, 80, 108, 108, 100]
    if com_multas:
        larguras = [24, 120, 62, 64, *[(largura-346)/len(COLUNAS_COMPONENTES)]*len(COLUNAS_COMPONENTES), 76]
    tabela = tabela_operacional(dados, larguras, total=True)
    partes[inicio_creditos:inicio_creditos] = separar_operacoes(
        partes[inicio_creditos:], tabela, largura, doc.height)
    partes.append(tabela)
    if descricoes_extensas:
        titulo_historicos = p("Históricos complementares", "secao")
        partes.extend(separar_operacoes([titulo_historicos], None, largura, doc.height))
        partes.append(titulo_historicos)
        for numero, descricao in descricoes_extensas.items():
            partes.append(p(f"Parcela {numero}: {descricao}", "nota"))
    if com_multas:
        colunas_multas = colunas_liquidas(colunas_perfil(resultado))
        inicio_multas = len(partes)
        partes.append(p("Multas por parcela", "secao_tabela"))
        partes.append(p("Multa nominal calculada sobre o saldo no vencimento. Cada coluna discrimina a base, o índice e os encargos da multa; a SELIC reúne atualização e mora e não recebe juros em duplicidade. Os valores desta tabela já estão incluídos na coluna Multa e encargos da tabela de parcelas.", "nota"))
        dados_multas = [[p(x, "cabecalho") for x in ["Nº", COLUNA_DESCRICAO, "Vencimento", "Multa nominal", *[cabecalho_componente(nome, periodo, periodo_na_celula=True) for _, nome, periodo in colunas_multas], "Total da multa"]]]
        for parcela in resultado.parcelas:
            m = parcela.multa_detalhes
            if m is None:
                continue
            componentes_multa = componentes_liquidos(m.componentes)
            base_nominal = f"{m.base_calculo:.4f}".replace(".", ",")
            percentual_nominal = f"{m.percentual:.4f}".replace(".", ",")
            nominal = f"Base {base_nominal}\n{percentual_nominal}%\nR$ {moeda(m.valor_original)}"
            celulas = []
            for chave, _, _ in colunas_multas:
                c = componentes_multa.get(chave)
                if c is None or c.data_inicial is None:
                    celulas.append(p("-", "componente"))
                    continue
                indice = (f"Fator {c.fator_acumulado:.4f}" if c.fator_acumulado is not None else f"{c.taxa_acumulada_percentual:.4f}%").replace(".", ",")
                base_multa = f"{c.base_calculo:.4f}".replace(".", ",")
                celulas.append(p(f"{data_br(c.data_inicial)} a {data_br(c.data_final)}\nBase {base_multa}\n{indice}\nR$ {moeda(c.valor)}", "componente"))
            historico_multa = f"Ver histórico integral da parcela {parcela.numero} em nota complementar." if parcela.numero in descricoes_extensas else parcela.historico
            dados_multas.append([p(parcela.numero, "celula"), p(historico_multa, "celula"), p(data_br(parcela.data_vencimento), "celula"), p(nominal, "componente"), *celulas, p(moeda(m.total_atualizado), "numero")])
        detalhes = [x.multa_detalhes for x in resultado.parcelas if x.multa_detalhes]
        totais_multas = totais_liquidos(detalhes)
        dados_multas.append(["", p("TOTAL", "celula"), "", p(moeda(sum((m.valor_original for m in detalhes), Decimal(0))), "numero"),
            *[p(moeda(totais_multas.get(chave, 0)), "numero") for chave, _, _ in colunas_multas], p(moeda(sum((m.total_atualizado for m in detalhes), Decimal(0))), "numero")])
        larguras_multas = [24, 120, 62, 76, *[(largura-358)/len(colunas_multas)]*len(colunas_multas), 76]
        tabela_multas = tabela_operacional(dados_multas, larguras_multas, total=True)
        partes[inicio_multas:inicio_multas] = separar_operacoes(
            partes[inicio_multas:], tabela_multas, largura, doc.height)
        partes.append(tabela_multas)
    nao_abatidos = [item for item in resultado.premissas.get("selecao_descontos", []) if not item["aplicar"]]
    inicio_pagamentos = len(partes)
    tabela_descontos = None
    if nao_abatidos:
        partes.append(p("Pagamentos não abatidos", "secao"))
        for item in nao_abatidos:
            partes.append(p(f"Lançamento {item['numero']}: {item['descricao'] or 'Sem descrição'}; "
                f"data {data_br(item['data']) if item['data'] else 'não informada'}; "
                f"valor {simbolo_moeda(item['data'])} {moeda(Decimal(item['valor'])) if item['valor'] else 'não informado'}. "
                "Não selecionado; não compõe o abatimento.", "nota"))
    if resultado.descontos:
        desconto = resultado.descontos
        colunas_descontos = colunas_liquidas(colunas_componentes(desconto))
        totais_descontos = totais_liquidos(desconto.parcelas)
        partes.append(p("DÉBITO - DECRÉSCIMO", "secao"))
        partes.append(p("Débitos atualizados desde cada lançamento e descontados do total atualizado das parcelas, antes das custas e despesas, sem recálculo do saldo a cada pagamento.", "nota"))
        for item in desconto.premissas.get("composicao_pagamentos", []):
            nominal = Decimal(item["encargos_sem_atualizacao"])
            if nominal:
                parte_nominal = "parte fora da conta" if desconto.premissas.get("perfil") == "poupanca_deposito_v1" else "encargos já pagos"
                partes.append(p(f"Pagamento {item['numero']}: total R$ {moeda(Decimal(item['valor']))}; "
                    f"base da atualização R$ {moeda(Decimal(item['valor']) - nominal)}; "
                    f"{parte_nominal} R$ {moeda(nominal)}, abatidos nominalmente sem nova incidência.", "nota"))
        dados_descontos = [[p(x, "cabecalho") for x in ["Nº", COLUNA_DESCRICAO, "Data", "Valor", *[cabecalho_componente(nome, periodo, periodo_na_celula=True) for _, nome, periodo in colunas_descontos], "Atualizado"]]]
        for item in desconto.parcelas:
            celulas = []
            componentes_desconto = componentes_liquidos(item.componentes)
            for chave, _, _ in colunas_descontos:
                componente = componentes_desconto[chave]
                if not componente.data_inicial:
                    celulas.append(p("-", "componente"))
                else:
                    indice = (f"Fator {componente.fator_acumulado:.4f}" if componente.fator_acumulado is not None else f"{componente.taxa_acumulada_percentual:.4f}%").replace(".", ",")
                    base_desconto = f"{componente.base_calculo:.4f}".replace(".", ",")
                    celulas.append(p(f"{data_br(componente.data_inicial)} a {data_br(componente.data_final)}\nBase {base_desconto}\n{indice}\nR$ {moeda(componente.valor)}", "componente"))
            dados_descontos.append([p(item.numero, "celula"), p(item.historico, "celula"), p(data_br(item.data_vencimento), "celula"), p(moeda(item.valor_bruto), "numero"), *celulas, p(moeda(item.total_parcela), "numero")])
        dados_descontos.append(["", p("TOTAL", "celula"), "", *[p(moeda(v), "numero") for v in [desconto.resumo.principal_original, *[totais_descontos[chave] for chave, _, _ in colunas_descontos], desconto.resumo.total_atualizado]]])
        larguras_descontos = [24, 140, 70, 76, *[(largura - 390) / len(colunas_descontos)] * len(colunas_descontos), 80]
        tabela_descontos = tabela_operacional(dados_descontos, larguras_descontos, total=True)
        fim_introducao_pagamentos = len(partes)
        partes.append(tabela_descontos)
        partes.append(p(f"Parcelas atualizadas: R$ {moeda(subtotal_parcelas)} - descontos: R$ {moeda(r.abatimentos)} = crédito líquido: R$ {moeda(subtotal_parcelas - r.abatimentos)}, antes dos honorários, acréscimos do cumprimento e custas.", "nota"))
    if resultado.descontos or nao_abatidos:
        fim_introducao = fim_introducao_pagamentos if tabela_descontos is not None else len(partes)
        partes[inicio_pagamentos:inicio_pagamentos] = separar_operacoes(
            partes[inicio_pagamentos:fim_introducao], tabela_descontos, largura, doc.height)
    from .relatorio_honorarios_principais import blocos_honorarios_pdf
    partes.extend(blocos_honorarios_pdf(resultado, largura, p, estilos, anexos=anexos, altura=doc.height))
    if civil_1:
        from .relatorio_taxa_legal import blocos_memoria_taxa_legal
        anexos.extend(blocos_memoria_taxa_legal(resultado, largura, estilos, p, altura=doc.height))
    from .relatorio_civil_4 import blocos_memoria_civil_4
    if civil_4:
        anexos.extend(blocos_memoria_civil_4(resultado.memoria_mensal, "Créditos", largura, p, doc.height))
    if resultado.descontos and resultado.descontos.premissas.get("perfil") in ("civil_4_temporario_v1", "civil_6_v1"):
        anexos.extend(blocos_memoria_civil_4(resultado.descontos.memoria_mensal, "Débitos", largura, p, doc.height))
    partes.extend(custas_despesas(resultado.custas_despesas, largura, p, doc.height))
    metodologia = [nota for nota in resultado.premissas.get("metodologia", [])
        if not nota.startswith(("As custas e despesas são apuradas", "Valor da causa no protocolo", "Descontos:"))]
    if resultado.premissas.get("perfil") == "selic_ipcae_poupanca_v1":
        metodologia.append("Valor da correção = base × (fator - 1). Valor dos juros simples = base × percentual acumulado ÷ 100.")
    inicio = ("Competência de cada parcela; SELIC única." if cjf else
        "Correção: data própria de cada parcela. Sem juros." if somente_correcao else
        f"Correção: data própria de cada parcela. Início dos juros: {inicio_juros}.")
    operacoes = [operacao("Créditos", resultado.premissas, geral.data_base,
        inicio=inicio, criterios=criterios_principal, metodologia=metodologia)]
    if resultado.descontos:
        operacoes.append(operacao("Débitos", resultado.descontos.premissas, geral.data_base))
    operacoes.extend(custas(resultado.custas_despesas, geral.data_base))
    criterios_acessorios = [nota for nota in resultado.premissas.get("criterios", [])
        if nota.startswith(("Honorários sucumbenciais:", "Art. 523,", "Honorários contratuais:"))]
    if criterios_acessorios:
        rotulo_acessorios = " / ".join(nome for presente, nome in (
            (resultado.honorarios_sucumbenciais, "Honorários"),
            (resultado.cumprimento_sentenca, "Cumprimento"),
            (resultado.destaque_contratuais, "Destaques")) if presente)
        operacoes.append(operacao(rotulo_acessorios, {}, geral.data_base,
            nome="Bases e percentuais indicados na apuração",
            inicio="Conforme a base e os termos abaixo.",
            criterios=criterios_acessorios,
            metodologia=[nota for nota in resultado.premissas.get("metodologia", []) if nota.startswith("Valor da causa no protocolo")]))
    partes.extend(criterios_metodologia(operacoes, largura, p, estilos, doc.height))
    partes.extend(anexo_tecnico(anexos, largura, p, doc.height))
    nomes = {**NOMES_FONTES, "selic_limite": "Banco Central - SELIC para comparação (SGS 4390)", "ipcae": "IBGE - IPCA-15/IPCA-E (dados via BCB SGS 10764 e 7478)", "ipcae_ibge": "IBGE - metodologia e divulgação do IPCA-E", "ipcae_serie_bcb": "Banco Central - série IPCA-15 (SGS 7478)", "selic": "Banco Central - SELIC mensal (SGS 4390)",
             "poupanca_total": "Banco Central - remuneração total da poupança (SGS 195)",
             "poupanca_2009_2012": "Banco Central - poupança de 2009 a 2012 (SGS 25)",
             "poupanca_2012_2016": "Banco Central - poupança de 2012 a 2016 (SGS 195)",
             "poupanca_2017_2021": "Banco Central - poupança de 2017 a 2021 (SGS 195)",
             "tema_905": "STJ - Tema 905",
             "ipcae_custas": "IBGE - IPCA-15/IPCA-E aplicado às custas e despesas"}
    nomes.update({"correcao_valor_causa": "Fonte da correção do valor da causa", "cpc_523": "CPC/2015 - cumprimento de sentença"})
    nomes.update({"ipca": "Banco Central - IPCA oficial (SGS 433)", "taxa_legal": "Banco Central - Taxa Legal oficial (SGS 29543)",
                  "resolucao_taxa_legal": "CMN - Resolução 5.171/2024", "calculadora_taxa_legal": "BCB - Metodologia da Taxa Legal"})
    nomes.update({"selic_diaria_anualizada": "Banco Central - SELIC anual diária (SGS 1178)",
                  "ipca15_reconstrucao": "Banco Central - IPCA-15 histórico (SGS 7478)"})
    nomes.update({"lei_14905": "Lei 14.905/2024", "tema_1368": "STJ - Tema 1.368",
                  "stj_termos_distintos": "STJ - AREsp 2.059.743, termos distintos",
                  "stj_acordao_2059743": "STJ - AgInt no AREsp 2.059.743/RJ"})
    fontes_principal = {}
    nomes.update({"selic_historica": "Banco Central - SELIC histórica (SGS 4390)", "manual_cjf": "CJF - Manual de Cálculos da Justiça Federal", "orientacao_cjf": "CJF - Orientação sobre a EC 136/2025"})
    if cjf:
        nomes["selic_limite"] = "Banco Central - SELIC mensal, série recente (SGS 4390)"
    for chave, nome in nomes.items():
        if sem_periodo_pre and (chave.startswith("poupanca") or chave == "tema_905"):
            continue
        url = resultado.premissas.get("fontes", {}).get(chave, "")
        if url.startswith("https://"):
            fontes_principal[nome] = url
    grupos_fontes = [("Créditos e acessórios", fontes_principal)]
    if resultado.descontos:
        grupos_fontes.append(("Débitos", {nomes.get(chave, chave.replace("_", " ")): url
            for chave, url in resultado.descontos.premissas.get("fontes", {}).items()}))
    partes.extend(fontes_conferencia(grupos_fontes, largura, p, estilos, altura=doc.height))

    complemento = f" | Demais operações: {data_br(geral.data_base)}" if referencia_selic and outras_operacoes and referencia_selic != geral.data_base.isoformat() else ""
    rodape = criar_rodape(rotulo_data, data_cabecalho, complemento)
    doc.build(partes, onFirstPage=rodape, onLaterPages=rodape)
    return buffer.getvalue()
