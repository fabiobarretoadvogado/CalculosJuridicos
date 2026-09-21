"""Relatório institucional dos honorários sucumbenciais por proveito econômico."""

import io
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    Image,
    KeepTogether,
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .honorarios_proveito import ResultadoHonorariosProveito, ResultadoOperacaoDivida
from .honorarios_isolados import ResultadoHonorariosIsolados
from .relatorio_pdf import data_br, moeda, texto


AZUL = colors.HexColor("#072F54")
AMARELO = colors.HexColor("#FBC108")
FUNDO = colors.HexColor("#F7F5F0")
LINHA = colors.HexColor("#E1DED8")
CINZA = colors.HexColor("#555555")

NOMES_COMPONENTES = {
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
    "ipcae_pre",
    "poupanca_pre",
    "selic",
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
    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagina,
        rightMargin=40,
        leftMargin=40,
        topMargin=32,
        # Reserva folga real entre textos/tabelas longos e o rodapé. A margem
        # também impede que um parágrafo dividido encoste na paginação.
        bottomMargin=68,
        title="Demonstrativo de cálculo",
        author="Barreto Fontes Sociedade de Advogados",
        subject=(
            f"Processo {resultado.dados_gerais.processo or 'não informado'}; "
            f"data-base {data_br(resultado.dados_gerais.data_base)}"
        ),
    )
    estilos = {
        "normal": ParagraphStyle(
            "hon-normal", fontName="Helvetica", fontSize=9, leading=12,
            spaceAfter=5, textColor=colors.HexColor("#171717"),
        ),
        "titulo": ParagraphStyle(
            "hon-titulo", fontName="Helvetica-Bold", fontSize=18, leading=23,
            spaceAfter=5, textColor=AZUL,
        ),
        "subtitulo": ParagraphStyle(
            "hon-subtitulo", fontName="Helvetica", fontSize=9, leading=12,
            textColor=CINZA,
        ),
        "secao": ParagraphStyle(
            "hon-secao", fontName="Helvetica-Bold", fontSize=12, leading=16,
            spaceBefore=12, spaceAfter=8, keepWithNext=True, textColor=AZUL,
        ),
        "cabecalho": ParagraphStyle(
            "hon-cabecalho", fontName="Helvetica-Bold", fontSize=8, leading=10,
            alignment=TA_CENTER, textColor=AZUL,
        ),
        "celula": ParagraphStyle(
            "hon-celula", fontName="Helvetica", fontSize=7.6, leading=9.2,
            splitLongWords=True,
        ),
        "numero": ParagraphStyle(
            "hon-numero", fontName="Helvetica", fontSize=8, leading=10,
            alignment=TA_RIGHT,
        ),
        "componente": ParagraphStyle(
            "hon-componente", fontName="Helvetica", fontSize=7.2, leading=8.4,
            alignment=TA_RIGHT,
        ),
        "nota": ParagraphStyle(
            "hon-nota", fontName="Helvetica", fontSize=8, leading=11,
            spaceAfter=5, textColor=CINZA,
        ),
        "rotulo": ParagraphStyle(
            "hon-rotulo", fontName="Helvetica", fontSize=8, leading=10,
            textColor=CINZA,
        ),
        "valor": ParagraphStyle(
            "hon-valor", fontName="Helvetica-Bold", fontSize=13, leading=17,
            textColor=AZUL, alignment=TA_RIGHT,
        ),
        "destaque": ParagraphStyle(
            "hon-destaque", fontName="Helvetica-Bold", fontSize=16, leading=20,
            textColor=AZUL, alignment=TA_RIGHT,
        ),
        "formula_rotulo": ParagraphStyle(
            "hon-formula-rotulo", fontName="Helvetica", fontSize=7.6, leading=9,
            textColor=CINZA, alignment=TA_CENTER,
        ),
        "formula_valor": ParagraphStyle(
            "hon-formula-valor", fontName="Helvetica-Bold", fontSize=12, leading=15,
            textColor=AZUL, alignment=TA_CENTER,
        ),
        "formula_operador": ParagraphStyle(
            "hon-formula-operador", fontName="Helvetica-Bold", fontSize=13, leading=15,
            textColor=CINZA, alignment=TA_CENTER,
        ),
        "formula_resultado": ParagraphStyle(
            "hon-formula-resultado", fontName="Helvetica-Bold", fontSize=14, leading=17,
            textColor=AZUL, alignment=TA_CENTER,
        ),
    }
    estilos["secao_tabela"] = ParagraphStyle(
        "hon-secao-tabela",
        parent=estilos["secao"],
        keepWithNext=False,
    )

    def p(conteudo, estilo="normal"):
        return Paragraph(texto(conteudo), estilos[estilo])

    def tabela_identificacao():
        geral = resultado.dados_gerais
        tabela = Table([
            [p(f"Processo: {geral.processo or 'Não informado'}"), p(f"Vara: {geral.vara or 'Não informada'}")],
            [p(f"Comarca: {geral.comarca or 'Não informada'}"), p(f"Classe: {geral.classe or 'Não informada'}")],
            [p(f"Requerente: {geral.requerente or 'Não informado'}"), p(f"Requerido: {geral.requerido or 'Não informado'}")],
        ], colWidths=[largura / 2] * 2, hAlign="LEFT", splitInRow=1)
        tabela.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return tabela

    def tabela_custas_despesas():
        dados = [[p(x, "cabecalho") for x in (
            "Nº", "Nome", "Data", "Valor original", "Fator IPCA-E", "Correção", "Valor atualizado",
        )]]
        for item in resultado.custas_despesas:
            dados.append([
                p(str(item.numero), "celula"),
                p(item.nome, "celula"),
                p(data_br(item.data), "celula"),
                p(f"R$ {moeda(item.valor_original)}", "numero"),
                p(f"{item.fator_ipcae:.4f}".replace(".", ","), "numero"),
                p(f"R$ {moeda(item.correcao_monetaria)}", "numero"),
                p(f"R$ {moeda(item.valor_atualizado)}", "numero"),
            ])
        dados.append([
            "", p("TOTAL", "cabecalho"), "",
            p(f"R$ {moeda(resultado.custas_despesas_valor_original)}", "numero"),
            "",
            p(f"R$ {moeda(resultado.custas_despesas_correcao)}", "numero"),
            p(f"R$ {moeda(resultado.custas_despesas_valor_atualizado)}", "numero"),
        ])
        tabela = Table(
            dados,
            colWidths=[28, largura - 438, 66, 86, 82, 86, 90],
            splitByRow=1,
            splitInRow=0,
            hAlign="LEFT",
        )
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), FUNDO),
            ("LINEBELOW", (0, 0), (-1, 0), .6, colors.HexColor("#B2ABA0")),
            ("LINEBELOW", (0, 1), (-1, -2), .25, LINHA),
            ("BACKGROUND", (0, -1), (-1, -1), FUNDO),
            ("LINEABOVE", (0, -1), (-1, -1), .6, AZUL),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        return tabela

    def componentes_ordenados(componentes):
        ordem = {chave: indice for indice, chave in enumerate(ORDEM_COMPONENTES)}
        return sorted(componentes.items(), key=lambda item: (ordem.get(item[0], 999), item[0]))

    def componentes_aplicados(operacao: ResultadoOperacaoDivida):
        return [
            (chave, componente)
            for chave, componente in componentes_ordenados(operacao.componentes)
            if componente.data_inicial is not None or componente.valor
        ]

    def resumo_operacao(operacao: ResultadoOperacaoDivida, colunas):
        titulos = [
            "Valor informado",
            *[nome_componente(chave) for chave, _ in colunas],
            "Valor atualizado",
        ]
        valores = [
            operacao.valor_informado,
            *[componente.valor for _, componente in colunas],
            operacao.valor_atualizado,
        ]
        tabela = Table([
            [p(titulo, "rotulo") for titulo in titulos],
            [
                p(f"R$ {moeda(valor)}", "destaque" if indice == len(valores) - 1 else "valor")
                for indice, valor in enumerate(valores)
            ],
        ], colWidths=[largura / len(titulos)] * len(titulos), hAlign="LEFT")
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), FUNDO),
            ("LINEABOVE", (-1, 0), (-1, 0), 2, AMARELO),
            ("TOPPADDING", (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING", (0, 1), (-1, 1), 11),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return tabela

    def detalhe_componente(componente):
        if componente is None or componente.data_inicial is None:
            return p("-", "componente")
        periodo = f"{data_br(componente.data_inicial)} a {data_br(componente.data_final)}"
        if componente.fator_acumulado is not None:
            indice = f"Fator {componente.fator_acumulado:.4f}"
        elif componente.taxa_acumulada_percentual is not None:
            indice = f"{componente.taxa_acumulada_percentual:.4f}%"
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
                p(f"Situação: {operacao.nome_perfil}.", "nota"),
                p(f"Saldo remanescente: R$ {moeda(operacao.valor_atualizado)}.", "normal"),
                p("Critérios e metodologia", "secao"),
                *[p(f"- {item}", "nota") for item in [*operacao.criterios, *operacao.metodologia]],
            ]
        partes = [
            p(operacao.rotulo, "secao"),
            p(
                f"Padrão aplicado: {operacao.nome_perfil}. "
                f"Quantidade: {operacao.quantidade_parcelas} item(ns).",
                "nota",
            ),
            resumo_operacao(operacao, colunas),
            Spacer(1, 12),
            p("Parcelas ou itens", "secao_tabela"),
            p(
                "Cada encargo aparece em coluna própria, com período, base de cálculo, "
                "fator ou taxa acumulada e valor acrescentado. O sinal '-' indica que "
                "o encargo não se aplica ao item.",
                "nota",
            ),
        ]
        cabecalho = [
            "Nº", "Descrição", "Origem", "Valor informado",
            *[ROTULOS_COMPONENTES_CURTOS.get(chave, nome_componente(chave)) for chave, _ in colunas],
            "Valor atualizado",
        ]
        linhas_parcelas = []
        for parcela in operacao.parcelas:
            linhas_parcelas.append([
                p(str(parcela.numero), "celula"),
                p(parcela.historico or "Item sem descrição", "celula"),
                p(data_br(parcela.data_origem), "celula"),
                p(f"R$ {moeda(parcela.valor_informado)}", "numero"),
                *[detalhe_componente(parcela.componentes.get(chave)) for chave, _ in colunas],
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

        def dividir_linhas(linhas):
            if len(linhas) <= 8:
                return [linhas]
            tamanho_inicial = 8
            restante = len(linhas) - tamanho_inicial
            if restante < 4:
                tamanho_inicial -= 4 - restante
            blocos = [linhas[:tamanho_inicial]]
            pendentes = linhas[tamanho_inicial:]
            while len(pendentes) > 12:
                tamanho = 12
                if len(pendentes) - tamanho < 4:
                    tamanho = len(pendentes) - 4
                blocos.append(pendentes[:tamanho])
                pendentes = pendentes[tamanho:]
            if pendentes:
                blocos.append(pendentes)
            return blocos

        blocos = dividir_linhas(linhas_parcelas)
        for indice_bloco, linhas_bloco in enumerate(blocos):
            primeiro = indice_bloco == 0
            ultimo = indice_bloco == len(blocos) - 1
            dados_bloco = []
            if primeiro:
                dados_bloco.append([p(item, "cabecalho") for item in cabecalho])
            dados_bloco.extend(linhas_bloco)
            if ultimo:
                dados_bloco.append(linha_total)

            tabela = Table(
                dados_bloco,
                colWidths=larguras,
                splitByRow=1,
                splitInRow=0,
                hAlign="LEFT",
            )
            inicio_dados = 1 if primeiro else 0
            fim_dados = -2 if ultimo else -1
            estilo_tabela = [
                ("LINEBELOW", (0, inicio_dados), (-1, fim_dados), .25, LINHA),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
            if primeiro:
                estilo_tabela.extend([
                    ("BACKGROUND", (0, 0), (-1, 0), FUNDO),
                    ("LINEBELOW", (0, 0), (-1, 0), .6, colors.HexColor("#B2ABA0")),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ])
            if ultimo:
                estilo_tabela.extend([
                    ("BACKGROUND", (0, -1), (-1, -1), FUNDO),
                    ("LINEABOVE", (0, -1), (-1, -1), .6, AZUL),
                ])
            tabela.setStyle(TableStyle(estilo_tabela))
            partes.append(tabela)
            if not ultimo:
                partes.append(PageBreak())

        partes.append(p("Critérios e metodologia", "secao"))
        for item in [*operacao.criterios, *operacao.metodologia]:
            partes.append(p(f"- {item}", "nota"))
        if operacao.fontes:
            partes.append(p("Fontes", "secao"))
            for nome, url in operacao.fontes.items():
                if url.startswith("https://"):
                    url_segura = escape(url, {'"': "&quot;"})
                    partes.append(Paragraph(
                        f'<b>{texto(nome.replace("_", " ").title())}:</b> '
                        f'<link href="{url_segura}" color="#213B5A">Consultar fonte oficial</link>',
                        estilos["nota"],
                    ))
        return partes

    geral = resultado.dados_gerais
    logo = Image(str(Path(__file__).resolve().parents[1] / "assets" / "logo-barreto-fontes.png"))
    proporcao = logo.imageHeight / logo.imageWidth
    logo.drawWidth = 122
    logo.drawHeight = 122 * proporcao
    textos_cabecalho = [
        p("Relatório de honorários sucumbenciais", "titulo"),
        p(
            f"{'Equidade - valor certo' if certo else 'Valor da causa atualizado' if isolado else 'Proveito econômico pela redução da dívida'}  /  Data-base {data_br(geral.data_base)}",
            "subtitulo",
        ),
    ]
    if resultado.chave_recuperacao:
        textos_cabecalho.append(p(f"Chave de recuperação: {resultado.chave_recuperacao}", "subtitulo"))
    cabecalho = Table([[logo, textos_cabecalho]], colWidths=[157, largura - 157], hAlign="LEFT")
    cabecalho.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("LINEBELOW", (0, 0), (-1, -1), .5, LINHA),
    ]))

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
    partes.extend([p("Identificação do processo", "secao"), tabela_identificacao()])
    if geral.observacoes:
        partes.extend([p("Observações", "secao"), p(geral.observacoes, "nota")])
    if resultado.alertas:
        partes.extend([p("Alertas", "secao"), *[p(f"- {item}", "nota") for item in resultado.alertas]])
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
            tabela_encargos = Table(linhas, colWidths=[143, 75, 75, 110, 90, 115, largura - 608], hAlign="LEFT")
            tabela_encargos.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), FUNDO), ("LINEBELOW", (0, 0), (-1, 0), .5, LINHA),
                ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            partes.append(KeepTogether([p("Encargos dos honorários fixados", "secao"), tabela_encargos]))
        if not certo:
            h = resultado.apuracao
            colunas = [
                [p(t, "cabecalho") for t in ("Período aplicado", "Índice", "Valor no protocolo", "Fator acumulado do período", "Correção", "Base atualizada")],
                [
                    p(f"{data_br(h.data_protocolo)} a {data_br(geral.data_base)}", "celula"),
                    p("IPCA-E IBGE (IPCA-15)" if h.indice == "ipcae" else "IPCA SGS 433", "celula"),
                    p(f"R$ {moeda(h.valor_original)}", "numero"),
                    p(f"{h.fator_acumulado:.8f}".replace(".", ","), "numero"),
                    p(f"R$ {moeda(h.correcao_monetaria)}", "numero"),
                    p(f"R$ {moeda(h.base_atualizada)}", "numero"),
                ],
            ]
            tabela_base = Table(colunas, colWidths=[145, 105, 135, 145, 125, largura - 655], hAlign="LEFT")
            tabela_base.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), FUNDO),
                ("LINEBELOW", (0, 0), (-1, 0), .5, LINHA),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            partes.append(KeepTogether([p("Base dos honorários - valor da causa", "secao"), tabela_base]))
        partes.extend([
            p("Critérios e metodologia", "secao"),
            *[p(item, "nota") for item in resultado.premissas["criterios"]],
            *[p(item, "nota") for item in ([] if certo_atualizado else resultado.premissas["metodologia"])],
        ])
        if not certo_atualizado and resultado.apuracao.fonte.startswith("https://"):
            fonte_segura = escape(resultado.apuracao.fonte, {'"': "&quot;"})
            partes.append(Paragraph(f'<b>Fonte da correção:</b> <link href="{fonte_segura}" color="#213B5A">Fonte oficial do índice aplicado</link>', estilos["nota"]))
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
            percentual = f"{faixa.percentual_aplicado:.4f}".replace(".", ",").rstrip("0").rstrip(",")
            linhas_faixas.append([
                rotulo, f"R$ {moeda(faixa.valor_incidente)}", f"{percentual}%",
                f"R$ {moeda(faixa.valor)}" if faixa.valor_incidente > 0 else "Não alcançada",
            ])
        linhas_faixas.append(["TOTAL", f"R$ {moeda(escalonamento.base_calculo)}", "", f"R$ {moeda(escalonamento.valor_total)}"])
        tabela_faixas = Table(linhas_faixas, colWidths=[largura - 400, 145, 100, 155], hAlign="LEFT")
        tabela_faixas.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), FUNDO),
            ("BACKGROUND", (0, -1), (-1, -1), FUNDO),
            ("TEXTCOLOR", (0, 0), (-1, 0), AZUL),
            ("TEXTCOLOR", (0, -1), (-1, -1), AZUL),
            ("LINEBELOW", (0, 0), (-1, 0), .5, LINHA),
            ("LINEABOVE", (0, -1), (-1, -1), .5, AZUL),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        fonte_segura = escape(escalonamento.fonte, {'"': "&quot;"})
        partes.append(KeepTogether([
            p("Honorários por faixa · Fazenda Pública", "secao"),
            p(f"{marco} de {data_br(escalonamento.data_decisao)} / Salário mínimo vigente informado: R$ {moeda(escalonamento.salario_minimo)}.", "nota"),
            tabela_faixas,
            Spacer(1, 5),
            Paragraph(
                'Aplicação progressiva: cada percentual incide somente na parcela da base dentro da faixa. '
                'Arredondamento por faixa ao centavo; total igual à soma das faixas. Custas e despesas não integram esta base. '
                f'<link href="{fonte_segura}" color="#213B5A">Art. 85, §§ 3º a 5º, CPC</link>.',
                estilos["nota"],
            ),
        ]))
    if resultado.custas_despesas:
        fonte_ipcae = resultado.fontes_custas_despesas.get("ipcae", "")
        partes.extend([
            PageBreak(),
            p("Custas e despesas processuais", "secao_tabela"),
            p(
                "Atualização exclusiva pelo IPCA-E desde a data de cada lançamento até a data-base, "
                "sem juros e sem integração à base dos honorários sucumbenciais.",
                "nota",
            ),
            tabela_custas_despesas(),
        ])
        if fonte_ipcae.startswith("https://"):
            fonte_segura = escape(fonte_ipcae, {'"': "&quot;"})
            partes.append(Paragraph(
                f'<b>Fonte do IPCA-E:</b> <link href="{fonte_segura}" color="#213B5A">'
                "IBGE - IPCA-15/IPCA-E (dados via BCB SGS 7478)</link>",
                estilos["nota"],
            ))
    if not isolado:
        partes.extend([PageBreak(), *secao_operacao(resultado.divida_original)])
        if resultado.divida_correta.parcelas:
            partes.append(PageBreak())
        partes.extend(secao_operacao(resultado.divida_correta))
    elif incluir_memoria_detalhada and resultado.apuracao.memoria:
        larguras_memoria = [60, 130, 100, 80, 110, largura - 480]
        linhas = [[p(t, "cabecalho") for t in ("Mês", "Índice", "Base", "Fator do mês", "Valor corrigido", "Período e critério")]]
        alturas_memoria = [None]
        for m in resultado.apuracao.memoria:
            linha = [
                p(m.competencia, "celula"), p(m.indice_aplicado, "celula"),
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
        tabela_memoria = LongTable(
            linhas,
            colWidths=larguras_memoria,
            rowHeights=alturas_memoria,
            hAlign="LEFT",
            repeatRows=0,
            splitByRow=1,
            splitInRow=0,
        )
        tabela_memoria.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), FUNDO),
            ("LINEBELOW", (0, 0), (-1, 0), .5, LINHA),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        titulo_memoria = (
            "Memória da correção dos honorários fixados"
            if certo_atualizado
            else "Anexo técnico - Memória da correção do valor da causa"
        )
        introducao_memoria = [] if certo_atualizado else [
            p(
                "O fator acumulado do período foi aplicado uma única vez e está consolidado na primeira página. "
                "As linhas abaixo mostram apenas a composição mensal para conferência.",
                "nota",
            )
        ]
        partes.extend([PageBreak(), p(titulo_memoria, "secao_tabela"), *introducao_memoria, tabela_memoria])
    if certo_atualizado and resultado.atualizacao_valor_certo.memoria_juros:
        linhas = [[p(t, "cabecalho") for t in ("Mês", "Índice", "Base dos juros", "Fator / taxa", "Juros no período", "Juros acumulados", "Período e critério")]]
        for m in resultado.atualizacao_valor_certo.memoria_juros:
            linhas.append([p(m.competencia, "celula"), p(m.indice_aplicado, "celula"), p(f"R$ {m.valor_base:.4f}".replace(".", ","), "numero"),
                p(f"{m.fator_aplicado:.6f}".replace(".", ","), "numero"), p(f"R$ {moeda(m.juros_periodo)}", "numero"),
                p(f"R$ {moeda(m.juros_acumulados)}", "numero"), p(m.observacao, "celula")])
        tabela_juros = Table(linhas, colWidths=[50, 100, 100, 86, 86, 86, largura - 508], hAlign="LEFT")
        tabela_juros.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), FUNDO), ("LINEBELOW", (0, 0), (-1, 0), .5, LINHA),
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        partes.extend([PageBreak(), p("Memória dos juros dos honorários fixados", "secao_tabela"), tabela_juros])
    if certo_atualizado:
        partes.extend([p("Como os encargos foram calculados", "secao"), *[p(item, "nota") for item in resultado.premissas["metodologia"]]])
        fontes = []
        for nome, url in resultado.premissas["fontes"].items():
            if url.startswith("https://"):
                link = escape(url, {'"': "&quot;"})
                fontes.append(Paragraph(f'<link href="{link}" color="#213B5A">{escape(nome.replace("_", " "))}</link>', estilos["nota"]))
        if fontes:
            partes.extend([p("Fontes e conferência", "secao"), *fontes])

    def rodape(canvas, _doc):
        canvas.saveState()
        canvas.setStrokeColor(LINHA)
        canvas.line(40, 32, pagina[0] - 40, 32)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(CINZA)
        canvas.drawString(40, 20, f"Barreto Fontes | Data-base {data_br(geral.data_base)}")
        canvas.drawRightString(pagina[0] - 40, 20, f"Página {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(partes, onFirstPage=rodape, onLaterPages=rodape)
    return buffer.getvalue()
