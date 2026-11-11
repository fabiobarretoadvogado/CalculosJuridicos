"""Relatório institucional dos honorários sucumbenciais por proveito econômico."""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    LongTable,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .honorarios_proveito import ResultadoHonorariosProveito, ResultadoOperacaoDivida
from .honorarios_isolados import ResultadoHonorariosIsolados
from .relatorio_layout import (data_br, moeda, texto, AZUL, AMARELO, FUNDO, LINHA, CINZA,
    criar_documento, criar_estilos, cabecalho as bloco_cabecalho, identificacao,
    observacoes, fontes_conferencia, criar_rodape, custas_despesas, resumo_financeiro, COLUNA_DESCRICAO, separar_operacoes, tabela_operacional)


NOMES_COMPONENTES = {
    "ipca_pre": "IPCA anterior",
    "juros_selic_deduzida": "SELIC deduzida do IPCA",
    "ipca_pos": "IPCA posterior",
    "ipca": "IPCA",
    "taxa_legal": "Taxa Legal",
    "ipcae": "IPCA-E",
    "ipcae_historico": "IPCA-E anual (IBGE)",
    "ipcae_posterior": "IPCA-E mensal (IBGE)",
    "juros_1am": "Juros simples de 1% ao mês",
    "multa_moratoria": "Multa moratória",
    "selic": "SELIC",
    "ipcae_pre": "IPCA-E anterior",
    "poupanca_pre": "Poupança anterior",
    "ipcae_pos": "IPCA-E posterior",
    "poupanca_pos": "Poupança posterior",
    "juros_2aa": "Juros simples de 2% ao ano",
    "limite_selic": "Limite SELIC",
}

ROTULOS_COMPONENTES_CURTOS = {
    "ipca_pre": "IPCA anterior",
    "juros_selic_deduzida": "SELIC deduzida do IPCA",
    "ipca_pos": "IPCA posterior",
    "ipca": "IPCA",
    "taxa_legal": "Taxa Legal",
    "ipcae": "IPCA-E",
    "ipcae_historico": "IPCA-E histórico",
    "ipcae_posterior": "IPCA-E posterior",
    "juros_1am": "Juros 1% a.m.",
    "multa_moratoria": "Multa",
    "selic": "SELIC",
    "ipcae_pre": "IPCA-E inicial",
    "poupanca_pre": "Poupança inicial",
    "ipcae_pos": "IPCA-E final",
    "poupanca_pos": "Poupança final",
    "juros_2aa": "Juros 2% a.a.",
    "limite_selic": "Limite SELIC",
}

ORDEM_COMPONENTES = (
    "ipca_pre",
    "juros_selic_deduzida",
    "ipcae_pre",
    "poupanca_pre",
    "selic",
    "ipca_pos",
    "ipcae_pos",
    "poupanca_pos",
    "ipca",
    "taxa_legal",
    "ipcae",
    "ipcae_historico",
    "ipcae_posterior",
    "juros_1am",
    "juros_2aa",
    "limite_selic",
    "multa_moratoria",
)


from .relatorio_criterios import operacao as quadro_operacao, custas, criterios_metodologia
from .relatorio_layout import indice_memoria, anexo_tecnico
from .relatorio_componentes import componentes_liquidos

def nome_componente(chave: str) -> str:
    return NOMES_COMPONENTES.get(chave, chave.replace("_", " ").capitalize())


def exportar_pdf_honorarios(
    resultado: ResultadoHonorariosProveito | ResultadoHonorariosIsolados,
    *,
    incluir_memoria_detalhada: bool = True,
) -> bytes:
    isolado = isinstance(resultado, ResultadoHonorariosIsolados)
    certo = isolado and resultado.base == "valor_certo"
    certo_atualizado = certo and resultado.atualizacao_valor_certo is not None
    buffer = io.BytesIO()
    pagina = landscape(A4)
    largura = pagina[0] - 80
    doc = criar_documento(buffer, f"Processo {resultado.dados_gerais.processo or 'não informado'}; data-base {data_br(resultado.dados_gerais.data_base)}")
    estilos = criar_estilos()
    anexos = []

    def p(conteudo, estilo="normal"):
        return Paragraph(texto(conteudo), estilos[estilo])

    def componentes_ordenados(componentes):
        ordem = {chave: indice for indice, chave in enumerate(ORDEM_COMPONENTES)}
        return sorted(componentes.items(), key=lambda item: (ordem.get(item[0], 999), item[0]))

    def componentes_aplicados(operacao: ResultadoOperacaoDivida):
        return [
            (chave, componente)
            for chave, componente in componentes_ordenados(componentes_liquidos(operacao.componentes))
            if componente.data_inicial is not None or componente.valor
        ]

    def resumo_operacao(operacao: ResultadoOperacaoDivida, colunas):
        titulos = [
            "Valor",
            *[nome_componente(chave) for chave, _ in colunas],
            "Valor atualizado",
        ]
        valores = [
            operacao.valor_informado,
            *[componente.valor for _, componente in colunas],
            operacao.valor_atualizado,
        ]
        return resumo_financeiro(titulos, valores, largura, p)

    def detalhe_componente(componente, chave):
        if componente is None or componente.data_inicial is None:
            return p("-", "componente")
        periodo = f"{data_br(componente.data_inicial)} a {data_br(componente.data_final)}"
        if componente.fator_acumulado is not None:
            indice = f"Fator {componente.fator_acumulado:.4f}"
        elif componente.taxa_acumulada_percentual is not None:
            casas = 6 if chave == "taxa_legal" else 4
            indice = f"{componente.taxa_acumulada_percentual:.{casas}f}%"
        else:
            indice = "Taxa não informada"
        indice = indice.replace(".", ",")
        base = f"{componente.base_calculo:.4f}".replace(".", ",")
        return p(
            f"{periodo}\nBase {base}\n{indice}\nR$ {moeda(componente.valor)}",
            "componente",
        )

    def secao_operacao(operacao: ResultadoOperacaoDivida):
        colunas = componentes_aplicados(operacao)
        if not operacao.parcelas:
            return [
                p(operacao.rotulo, "secao"),
                p(f"Saldo remanescente: R$ {moeda(operacao.valor_atualizado)}.", "normal"),
            ]
        partes = [
            p(operacao.rotulo, "secao"),
            p(
                f"Quantidade: {operacao.quantidade_parcelas} item(ns).",
                "nota",
            ),
            resumo_operacao(operacao, colunas),
            p("Parcelas ou itens", "secao_tabela"),
            p(
                "Cada encargo aparece em coluna própria, com período, base de cálculo, "
                "fator ou taxa acumulada e valor acrescentado.",
                "nota",
            ),
        ]
        cabecalho = [
            "Nº", COLUNA_DESCRICAO, "Origem", "Valor",
            *[ROTULOS_COMPONENTES_CURTOS.get(chave, nome_componente(chave)) for chave, _ in colunas],
            "Valor atualizado",
        ]
        linhas_parcelas = []
        for parcela in operacao.parcelas:
            componentes_exibidos = componentes_liquidos(parcela.componentes)
            linhas_parcelas.append([
                p(str(parcela.numero), "celula"),
                p(parcela.historico or "Item sem descrição", "celula"),
                p(data_br(parcela.data_origem), "celula"),
                p(f"R$ {moeda(parcela.valor_informado)}", "numero"),
                *[detalhe_componente(componentes_exibidos.get(chave), chave) for chave, _ in colunas],
                p(f"R$ {moeda(parcela.valor_atualizado)}", "numero"),
            ])

        linha_total = [
            "", p("TOTAL", "cabecalho"), "",
            p(f"R$ {moeda(operacao.valor_informado)}", "numero"),
            *[p(f"R$ {moeda(componente.valor)}", "numero") for _, componente in colunas],
            p(f"R$ {moeda(operacao.valor_atualizado)}", "numero"),
        ]
        quantidade_componentes = len(colunas)
        largura_descricao = (
            largura - 24 - 62 - 70 - 150 - 82
            if quantidade_componentes == 1
            else max(90, 150 - max(0, quantidade_componentes - 2) * 15)
        )
        largura_componente = (
            150
            if quantidade_componentes == 1
            else (largura - 24 - largura_descricao - 62 - 70 - 82) / quantidade_componentes
        )
        larguras = [
            24, largura_descricao, 62, 70,
            *[largura_componente] * quantidade_componentes,
            82,
        ]

        tabela = tabela_operacional(
            [[p(item, "cabecalho") for item in cabecalho], *linhas_parcelas, linha_total],
            larguras, total=True)
        partes[3:3] = separar_operacoes(partes[3:], tabela, largura, doc.height)
        partes.append(tabela)

        return partes

    geral = resultado.dados_gerais
    cabecalho = bloco_cabecalho(largura, p, "Relatório de honorários sucumbenciais",
        f"{'Equidade - valor certo' if certo else 'Valor da causa atualizado' if isolado else 'Proveito econômico pela redução da dívida'}  /  Data-base {data_br(geral.data_base)}",
        resultado.chave_recuperacao)

    larguras_equacao = [156, 24, 140, 24, 132, 24, 94, 24, largura - 618]
    equacao_honorarios = Table([
        [
            p("Equidade - valor certo informado na data-base" if certo else "Valor da causa no protocolo" if isolado else "Dívida originalmente exigida atualizada", "formula_rotulo"), "",
            p("Correção monetária" if isolado else "Dívida correta atualizada", "formula_rotulo"), "",
            p("Valor da causa atualizado" if isolado else "Proveito econômico", "formula_rotulo"), "",
            p("Forma de fixação" if resultado.escalonamento_fazenda else "Percentual da sentença", "formula_rotulo"), "",
            p("Honorários sucumbenciais", "formula_rotulo"),
        ],
        [
            p("Sem nova correção ou juros automáticos" if certo else f"R$ {moeda(resultado.apuracao.valor_original if isolado else resultado.divida_original.valor_atualizado)}", "formula_rotulo" if certo else "formula_valor"),
            p("+" if isolado else "-", "formula_operador"),
            p(f"R$ {moeda(resultado.apuracao.correcao_monetaria if isolado else resultado.divida_correta.valor_atualizado)}", "formula_valor"),
            p("=", "formula_operador"),
            p(f"R$ {moeda(resultado.apuracao.base_atualizada if isolado else resultado.proveito_economico)}", "formula_valor"),
            p("x", "formula_operador"),
            p("" if certo else "Por faixas" if resultado.escalonamento_fazenda else f"{moeda(resultado.percentual_sentenca)}%", "formula_valor"),
            p("=", "formula_operador"),
            p(f"R$ {moeda(resultado.honorarios_sucumbenciais)}", "formula_resultado"),
        ],
    ], colWidths=larguras_equacao, hAlign="LEFT")
    equacao_honorarios.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), FUNDO),
        ("LINEABOVE", (-1, 0), (-1, 0), 2, AMARELO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (1, 0), (1, -1), 0),
        ("RIGHTPADDING", (1, 0), (1, -1), 0),
        ("LEFTPADDING", (3, 0), (3, -1), 0),
        ("RIGHTPADDING", (3, 0), (3, -1), 0),
        ("LEFTPADDING", (5, 0), (5, -1), 0),
        ("RIGHTPADDING", (5, 0), (5, -1), 0),
        ("LEFTPADDING", (7, 0), (7, -1), 0),
        ("RIGHTPADDING", (7, 0), (7, -1), 0),
    ]))

    equacao_total = None
    if certo and not certo_atualizado:
        equacao_honorarios.setStyle(TableStyle([
            ("SPAN", (0, 0), (7, 0)), ("SPAN", (0, 1), (7, 1)),
        ]))
    if certo_atualizado:
        h = resultado.atualizacao_valor_certo
        equacao_honorarios = Table([
            [p(t, "formula_rotulo") if t else "" for t in ("Valor fixado", "", "Correção monetária", "", "Juros de mora", "", "Honorários atualizados")],
            [p(f"R$ {moeda(h.valor_bruto)}", "formula_valor"), p("+", "formula_operador"),
             p(f"R$ {moeda(h.correcao_monetaria)}", "formula_valor"), p("+", "formula_operador"),
             p(f"R$ {moeda(h.juros_mora)}", "formula_valor"), p("=", "formula_operador"),
             p(f"R$ {moeda(h.total_parcela)}", "formula_resultado")],
        ], colWidths=[156, 24, 140, 24, 132, 24, largura - 500], hAlign="LEFT")
        equacao_honorarios.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), FUNDO), ("LINEABOVE", (-1, 0), (-1, 0), 2, AMARELO),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 2), ("TOPPADDING", (0, 1), (-1, 1), 2),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 12), ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
    if resultado.custas_despesas:
        larguras_total = [220, 28, 220, 28, largura - 496]
        equacao_total = Table([
            [
                p("Honorários sucumbenciais", "formula_rotulo"), "",
                p("Custas e despesas atualizadas", "formula_rotulo"), "",
                p("Total geral", "formula_rotulo"),
            ],
            [
                p(f"R$ {moeda(resultado.honorarios_sucumbenciais)}", "formula_valor"),
                p("+", "formula_operador"),
                p(f"R$ {moeda(resultado.custas_despesas_valor_atualizado)}", "formula_valor"),
                p("=", "formula_operador"),
                p(f"R$ {moeda(resultado.total_geral)}", "formula_resultado"),
            ],
        ], colWidths=larguras_total, hAlign="LEFT")
        equacao_total.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("LINEBELOW", (0, -1), (-1, -1), .5, LINHA),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
            ("TOPPADDING", (0, 1), (-1, 1), 1),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))

    partes = [
        cabecalho,
        Spacer(1, 14),
        equacao_honorarios,
    ]
    if equacao_total is not None:
        partes.append(equacao_total)
    partes.extend(identificacao(geral, largura, p))
    partes.extend(observacoes(geral.observacoes, resultado.alertas, p))
    if isolado:
        if certo_atualizado:
            h = resultado.atualizacao_valor_certo
            linhas = [[p(t, "cabecalho") for t in ("Encargo", "Início", "Fim", "Base", "Fator", "Taxa acumulada", "Valor")]]
            config = resultado.premissas["entrada"]["encargos_valor_certo"]
            for nome, c in h.componentes.items():
                rotulo = "IPCA-E IBGE (IPCA-15)" if nome == "ipcae" else "IPCA SGS 433" if nome == "ipca" else "Taxa Legal SGS 29543" if config["juros"] == "taxa_legal" else "Juros simples" if config["juros"] == "simples" else "Juros não incluídos"
                linhas.append([p(rotulo, "celula"), p(data_br(c.data_inicial) if c.data_inicial else "-", "celula"),
                    p(data_br(c.data_final) if c.data_final else "-", "celula"), p(f"R$ {c.base_calculo:.4f}".replace(".", ","), "numero"),
                    p(f"{c.fator_acumulado:.4f}".replace(".", ",") if c.fator_acumulado is not None else "-", "numero"),
                    p(f"{c.taxa_acumulada_percentual:.6f}%".replace(".", ",") if c.taxa_acumulada_percentual is not None else "-", "numero"),
                    p(f"R$ {moeda(c.valor)}", "numero")])
            tabela_encargos = tabela_operacional(linhas, [143, 75, 75, 110, 90, 115, largura - 608])
            introducao = [p("Encargos dos honorários fixados", "secao_tabela")]
            partes.extend([*separar_operacoes(introducao, tabela_encargos, largura, doc.height), *introducao, tabela_encargos])
        if not certo:
            h = resultado.apuracao
            colunas = [
                [p(t, "cabecalho") for t in ("Período aplicado", "Índice", "Valor no protocolo", "Fator acumulado do período", "Correção", "Base atualizada")],
                [
                    p(f"{data_br(h.data_protocolo)} a {data_br(geral.data_base)}", "celula"),
                    p("IPCA-E IBGE (IPCA-15)" if h.indice == "ipcae" else "IPCA SGS 433", "celula"),
                    p(f"R$ {moeda(h.valor_original)}", "numero"),
                    p(f"{h.fator_acumulado:.4f}".replace(".", ","), "numero"),
                    p(f"R$ {moeda(h.correcao_monetaria)}", "numero"),
                    p(f"R$ {moeda(h.base_atualizada)}", "numero"),
                ],
            ]
            tabela_base = tabela_operacional(colunas, [145, 105, 135, 145, 125, largura - 655])
            introducao = [p("Base dos honorários - valor da causa", "secao_tabela")]
            partes.extend([*separar_operacoes(introducao, tabela_base, largura, doc.height), *introducao, tabela_base])
    if resultado.escalonamento_fazenda:
        escalonamento = resultado.escalonamento_fazenda
        marco = "Sentença líquida" if escalonamento.marco == "sentenca_liquida" else "Decisão de liquidação"
        linhas_faixas = [["Faixa (salários mínimos)", "Base na faixa", "Percentual", "Honorários"]]
        for faixa in escalonamento.faixas:
            inferior = f"{faixa.limite_inferior_salarios_minimos:,.0f}".replace(",", ".")
            superior = f"{faixa.limite_salarios_minimos:,.0f}".replace(",", ".") if faixa.limite_salarios_minimos else None
            rotulo = f"Até {superior} SM" if faixa.ordem == 1 else (
                f"Acima de {inferior} até {superior} SM" if superior else f"Acima de {inferior} SM"
            )
            percentual = f"{faixa.percentual_aplicado:.4f}".replace(".", ",")
            linhas_faixas.append([
                rotulo, f"R$ {moeda(faixa.valor_incidente)}", f"{percentual}%",
                f"R$ {moeda(faixa.valor)}" if faixa.valor_incidente > 0 else "Não alcançada",
            ])
        linhas_faixas.append(["TOTAL", f"R$ {moeda(escalonamento.base_calculo)}", "", f"R$ {moeda(escalonamento.valor_total)}"])
        tabela_faixas = tabela_operacional([[p(v, "cabecalho" if i == 0 else "celula" if j == 0 else "numero") for j, v in enumerate(linha)] for i, linha in enumerate(linhas_faixas)], [largura - 400, 145, 100, 155], total=True)
        bloco_faixas = [
            p("Honorários por faixa · Fazenda Pública", "secao"),
            p(f"{marco} de {data_br(escalonamento.data_decisao)} / Salário mínimo vigente informado: R$ {moeda(escalonamento.salario_minimo)}.", "nota"),
            tabela_faixas,
            Spacer(1, 5),
            Paragraph(
                'Aplicação progressiva: cada percentual incide somente na parcela da base dentro da faixa. '
                'Arredondamento por faixa ao centavo; total igual à soma das faixas. Custas e despesas não integram esta base. '
                'Art. 85, §§ 3º a 5º, CPC.',
                estilos["nota"],
            ),
        ]
        partes.extend(separar_operacoes(bloco_faixas[:2], tabela_faixas, largura, doc.height))
        partes.extend(bloco_faixas)
    if not isolado:
        for operacao_divida in (resultado.divida_original, resultado.divida_correta):
            bloco = secao_operacao(operacao_divida)
            tabela_operacao = next((i for i, item in enumerate(bloco) if isinstance(item, LongTable)), len(bloco))
            partes.extend(separar_operacoes(bloco[:tabela_operacao], bloco[tabela_operacao] if tabela_operacao < len(bloco) else None, largura, doc.height))
            partes.extend(bloco)
    elif incluir_memoria_detalhada and resultado.apuracao.memoria:
        larguras_memoria = [60, 130, 100, 80, 110, largura - 480]
        linhas = [[p(t, "cabecalho") for t in ("Mês", "Índice", "Base", "Fator do mês", "Valor corrigido", "Período e critério")]]
        alturas_memoria = [None]
        for m in resultado.apuracao.memoria:
            linha = [
                p(m.competencia, "celula"), p(indice_memoria(m.indice_aplicado), "celula"),
                p(f"R$ {m.valor_base:.4f}".replace(".", ",") if certo_atualizado else f"R$ {moeda(m.valor_base)}", "numero"),
                p(f"{m.fator_aplicado:.4f}".replace(".", ","), "numero"),
                p(f"R$ {moeda(m.valor_corrigido)}", "numero"), p(m.observacao, "celula"),
            ]
            linhas.append(linha)
            # Algumas versões do ReportLab subestimam a altura de parágrafos
            # na última coluna ao dividir tabelas longas. A altura mínima evita
            # que a linha seguinte seja desenhada sobre a segunda linha do texto.
            altura_conteudo = max(
                celula.wrap(max(largura_coluna - 12, 1), pagina[1])[1]
                for celula, largura_coluna in zip(linha, larguras_memoria, strict=True)
            )
            alturas_memoria.append(max(36, altura_conteudo + 8))
        tabela_memoria = tabela_operacional(linhas, larguras_memoria, alturas=alturas_memoria)
        titulo_memoria = (
            "Memória da correção dos honorários fixados"
            if certo_atualizado
            else "Anexo técnico - Memória da correção do valor da causa"
        )
        introducao_memoria = [] if certo_atualizado else [
            p(
                "O fator acumulado do período foi aplicado uma única vez e está consolidado na seção Base dos honorários. "
                "As linhas abaixo mostram apenas a composição mensal para conferência.",
                "nota",
            )
        ]
        introducao_memoria = [p(titulo_memoria, "secao_tabela"), *introducao_memoria]
        if anexos:
            anexos.extend(separar_operacoes(introducao_memoria, tabela_memoria, largura, doc.height))
        anexos.extend([*introducao_memoria, tabela_memoria])
    if certo_atualizado and resultado.atualizacao_valor_certo.memoria_juros:
        linhas = [[p(t, "cabecalho") for t in ("Mês", "Índice", "Base dos juros", "Fator / taxa", "Juros no período", "Juros acumulados", "Período e critério")]]
        for m in resultado.atualizacao_valor_certo.memoria_juros:
            linhas.append([p(m.competencia, "celula"), p(indice_memoria(m.indice_aplicado), "celula"), p(f"R$ {m.valor_base:.4f}".replace(".", ","), "numero"),
                p(f"{m.fator_aplicado:.6f}".replace(".", ","), "numero"), p(f"R$ {moeda(m.juros_periodo)}", "numero"),
                p(f"R$ {moeda(m.juros_acumulados)}", "numero"), p(m.observacao, "celula")])
        tabela_juros = tabela_operacional(linhas, [50, 100, 100, 86, 86, 86, largura - 508])
        titulo_juros = p("Memória dos juros dos honorários fixados", "secao_tabela")
        if anexos:
            anexos.extend(separar_operacoes([titulo_juros], tabela_juros, largura, doc.height))
        anexos.extend([titulo_juros, tabela_juros])
    partes.extend(custas_despesas(resultado.custas_despesas, largura, p, doc.height))
    operacoes = []
    grupos_fontes = []
    if isolado:
        entrada = resultado.premissas.get("entrada", {})
        encargos = entrada.get("encargos_valor_certo") or {}
        if resultado.base == "valor_causa":
            indice = "IPCA-E" if resultado.apuracao.indice == "ipcae" else "IPCA"
            nome = f"Valor da causa / {indice} / sem juros"
            inicio = f"Protocolo: {data_br(resultado.apuracao.data_protocolo)}."
        elif encargos:
            indice = "IPCA-E" if encargos.get("indice") == "ipcae" else "IPCA"
            juros = {"taxa_legal": "Taxa Legal", "simples": "juros mensais simples", "sem_juros": "sem juros"}[encargos["juros"]]
            nome = f"Valor certo / {indice} / {juros}"
            inicio = f"Correção: {data_br(encargos.get('data_fixacao'))}. Juros: {data_br(encargos.get('data_inicio_juros'))}." if encargos.get('juros') != "sem_juros" else f"Correção: {data_br(encargos.get('data_fixacao'))}. Sem juros."
        else:
            nome = "Equidade / valor certo na data-base"
            inicio = "Sem nova correção ou juros."
        operacoes.append(quadro_operacao("Honorários", resultado.premissas, geral.data_base,
            nome=nome, inicio=inicio,
            criterios=[nota for nota in resultado.premissas["criterios"] if not nota.startswith("Custas e despesas")]))
        grupos_fontes.append(("Honorários", {nome.replace("_", " "): url for nome, url in resultado.premissas["fontes"].items()}))
        if resultado.apuracao.fonte:
            grupos_fontes.append(("Correção dos honorários", {"Fonte oficial da correção": resultado.apuracao.fonte}))
    else:
        for operacao in (resultado.divida_original, resultado.divida_correta):
            operacoes.append(quadro_operacao(operacao.rotulo, operacao.premissas, geral.data_base,
                nome=operacao.nome_perfil,
                inicio="Extinção integral informada; sem encargos a apurar." if operacao.premissas.get("extincao_integral") else None,
                criterios=operacao.criterios, metodologia=operacao.metodologia))
            grupos_fontes.append((operacao.rotulo, {nome.replace("_", " ").title(): url for nome, url in operacao.fontes.items()}))
    if resultado.custas_despesas:
        grupos_fontes.append(("Custas e despesas", {"IBGE - IPCA-15/IPCA-E (dados via BCB SGS 10764 e 7478)": resultado.fontes_custas_despesas.get("ipcae", "")}))
    if resultado.escalonamento_fazenda:
        grupos_fontes.append(("Honorários por faixa", {"Art. 85, §§ 3º a 5º, CPC": resultado.escalonamento_fazenda.fonte}))
    operacoes.extend(custas(resultado.custas_despesas, geral.data_base))
    partes.extend(criterios_metodologia(operacoes, largura, p, estilos, doc.height))
    if hasattr(resultado, "divida_original"):
        from .relatorio_civil_4 import blocos_memoria_civil_4
        for divida in (resultado.divida_original, resultado.divida_correta):
            if divida.perfil in ("civil_4_temporario_v1", "civil_6_v1"):
                anexos.extend(blocos_memoria_civil_4(divida.memoria_mensal, divida.rotulo, largura, p, doc.height))
    partes.extend(anexo_tecnico(anexos, largura, p, doc.height))
    partes.extend(fontes_conferencia(grupos_fontes, largura, p, estilos, altura=doc.height))
    rodape = criar_rodape("Data-base", geral.data_base)
    doc.build(partes, onFirstPage=rodape, onLaterPages=rodape)
    return buffer.getvalue()
