"""Demonstrativo A4 com bases, índices e valores por parcela."""
import io
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import CondPageBreak, Image, KeepTogether, LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import ComponenteCalculo, ResultadoCalculo
from .componentes import colunas_componentes, colunas_perfil


def texto(valor):
    """Dados do processo são texto, nunca marcação interpretada pelo PDF."""
    value = str(valor or "").replace("–", "-").replace("—", "-")
    value = "".join(c for c in value if ord(c) >= 32 or c == "\n")
    return escape(value).replace("\n", "<br/>")


def moeda(valor):
    return f"{Decimal(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def data_br(valor):
    if not valor:
        return "Não informado"
    return (date.fromisoformat(valor) if isinstance(valor, str) else valor).strftime("%d/%m/%Y")


def exportar_pdf(resultado: ResultadoCalculo) -> bytes:
    COLUNAS_COMPONENTES = colunas_componentes(resultado)
    novo = resultado.premissas.get("perfil") == "selic_ipcae_2aa_v1"
    cjf = resultado.premissas.get("perfil") == "selic_cjf_v1"
    civil_1 = resultado.premissas.get("perfil") == "ipca_taxa_legal_v1"
    civil_2 = resultado.premissas.get("perfil") == "civil_2_v1"
    datas_independentes = civil_1 or civil_2
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
    doc = SimpleDocTemplate(
        buffer, pagesize=pagina, rightMargin=40, leftMargin=40, topMargin=32, bottomMargin=40,
        title="Demonstrativo de cálculo", author="Barreto Fontes Sociedade de Advogados",
        subject=f"{rotulo_data} {data_br(data_cabecalho)}; {resultado.premissas.get('versao_metodologia', '')}",
    )
    estilos = {
        "normal": ParagraphStyle("normal", fontName="Helvetica", fontSize=9, leading=12, spaceAfter=5, textColor=colors.HexColor("#171717")),
        "titulo": ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=18, leading=23, spaceAfter=5, textColor=colors.HexColor("#072F54")),
        "secao": ParagraphStyle("secao", fontName="Helvetica-Bold", fontSize=10, leading=13, spaceBefore=12, spaceAfter=7, keepWithNext=True, textColor=colors.HexColor("#072F54")),
        "celula": ParagraphStyle("celula", fontName="Helvetica", fontSize=8, leading=9, splitLongWords=True),
        "numero": ParagraphStyle("numero", fontName="Helvetica", fontSize=8, leading=10, alignment=TA_RIGHT),
        "componente": ParagraphStyle("componente", fontName="Helvetica", fontSize=7.5, leading=9, alignment=TA_RIGHT),
        "cabecalho": ParagraphStyle("cabecalho", fontName="Helvetica-Bold", fontSize=8, leading=10, alignment=TA_CENTER, textColor=colors.HexColor("#072F54")),
        "nota": ParagraphStyle("nota", fontName="Helvetica", fontSize=8, leading=11, spaceAfter=5, textColor=colors.HexColor("#555555")),
        "total": ParagraphStyle("total", fontName="Helvetica-Bold", fontSize=12, leading=16, spaceAfter=3),
        "valor_resumo": ParagraphStyle("valor_resumo", fontName="Helvetica", fontSize=10, leading=13, alignment=TA_RIGHT),
        "valor_total": ParagraphStyle("valor_total", fontName="Helvetica-Bold", fontSize=14, leading=18, alignment=TA_RIGHT, textColor=colors.HexColor("#072F54")),
        "metrica": ParagraphStyle("metrica", fontName="Helvetica", fontSize=12, leading=17, textColor=colors.HexColor("#171717")),
    }
    estilos["secao_tabela"] = ParagraphStyle(
        "secao_tabela",
        parent=estilos["secao"],
        keepWithNext=False,
    )
    estilos["rotulo_total"] = ParagraphStyle("rotulo_total", parent=estilos["nota"], alignment=TA_RIGHT)

    def p(conteudo, estilo="normal"):
        return Paragraph(texto(conteudo), estilos[estilo])

    r = resultado.resumo
    geral = resultado.dados_gerais
    logo = Image(str(Path(__file__).resolve().parents[1] / "assets" / "logo-barreto-fontes.png"))
    image_width, image_height = logo.imageWidth, logo.imageHeight
    logo.drawWidth = 122
    logo.drawHeight = 122 * image_height / image_width
    textos_cabecalho = [p("Demonstrativo de cálculo", "titulo"), p(
        f"{rotulo_data} {data_br(data_cabecalho)}"
        f"{('  /  Último índice aplicado: ' + indice_selic) if referencia_selic else ''}"
        f"  /  {len(resultado.parcelas)} parcelas"
        f"  /  {len(resultado.custas_despesas)} custas ou despesas", "nota"
    )]
    if resultado.chave_recuperacao:
        textos_cabecalho.append(p(f"Chave de recuperação: {resultado.chave_recuperacao}", "nota"))
    header = Table([[logo, textos_cabecalho]], colWidths=[157, largura - 157], hAlign="LEFT")
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("LINEBELOW", (0, 0), (-1, -1), .5, colors.HexColor("#E1DED8"))]))
    partes = [header, Spacer(1, 14)]

    colunas_resumo = COLUNAS_COMPONENTES
    if resultado.honorarios_sucumbenciais or resultado.cumprimento_sentenca:
        colunas_resumo = [(chave, nome, faixa) for chave, nome, faixa in COLUNAS_COMPONENTES
                         if any(p.componentes.get(chave, ComponenteCalculo()).data_inicial for p in resultado.parcelas)]
    titulos_resumo = (
        "Principal apurado",
        *[nome for _, nome, _ in colunas_resumo],
        *(["(-) Descontos abatidos"] if resultado.descontos else []),
        *(["Honorários sucumbenciais"] if resultado.honorarios_sucumbenciais else []),
        *(["Multa art. 523"] if resultado.cumprimento_sentenca and resultado.cumprimento_sentenca.aplicar_multa else []),
        *(["Honorários art. 523"] if resultado.cumprimento_sentenca and resultado.cumprimento_sentenca.aplicar_honorarios else []),
        *(["Custas e despesas"] if resultado.custas_despesas else []),
        resultado.premissas.get("titulo_total", "TOTAL ATUALIZADO"),
    )
    larguras_resumo = [max(100, stringWidth(titulo, "Helvetica", 8) + 18) for titulo in titulos_resumo]
    resumo = [
        [p(x, "rotulo_total" if i == len(titulos_resumo) - 1 else "nota") for i, x in enumerate(titulos_resumo)],
        [p(f"R$ {moeda(v)}", "valor_total" if i == len(titulos_resumo) - 1 else "metrica") for i, v in enumerate((
            r.principal_apurado,
            *[r.totais_componentes.get(chave, 0) for chave, _, _ in colunas_resumo],
            *([-r.abatimentos] if resultado.descontos else []),
            *([resultado.honorarios_sucumbenciais.valor] if resultado.honorarios_sucumbenciais else []),
            *([resultado.cumprimento_sentenca.multa] if resultado.cumprimento_sentenca and resultado.cumprimento_sentenca.aplicar_multa else []),
            *([resultado.cumprimento_sentenca.honorarios] if resultado.cumprimento_sentenca and resultado.cumprimento_sentenca.aplicar_honorarios else []),
            *([r.custas] if resultado.custas_despesas else []),
            r.total_atualizado,
        ))],
    ]
    destaque_resumo = (-1, 0)
    if sum(larguras_resumo) > largura:
        # Reserva a última coluna para o total também no resumo em linhas.
        vazios = (-len(titulos_resumo)) % 4
        resumo = [linha[:-1] + [""] * vazios + linha[-1:] for linha in resumo]
        quantidade = len(resumo[0])
        linhas = []
        for inicio in range(0, quantidade, 4):
            linhas.extend([linha[inicio:inicio+4] + [""] * max(0, inicio+4-len(linha)) for linha in resumo])
        resumo = linhas
        larguras_resumo = [largura / 4] * 4
        destaque_resumo = ((quantidade - 1) % 4, ((quantidade - 1) // 4) * 2)
    else:
        # Mantém a coluna do total estreita e encostada à margem direita.
        # A folga é absorvida pela rubrica imediatamente anterior.
        larguras_resumo[-2 if len(larguras_resumo) > 1 else -1] += largura - sum(larguras_resumo)
    tabela_resumo = Table(resumo, colWidths=larguras_resumo, hAlign="LEFT")
    tabela_resumo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F5F0")),
        ("LINEABOVE", destaque_resumo, destaque_resumo, 2, colors.HexColor("#FBC108")),
        ("TOPPADDING", (0, 0), (-1, 0), 10), ("BOTTOMPADDING", (0, 1), (-1, 1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    partes += [Spacer(1, 4), tabela_resumo, Spacer(1, 8)]
    if r.valor_pago_na_data_parcelas:
        partes.append(p(f"Principal original: R$ {moeda(r.principal_original)}. Pagamentos no vencimento: R$ {moeda(r.valor_pago_na_data_parcelas)}.", "nota"))
    if not resultado.premissas.get("omitir_qualificacao", False):
        partes.append(p("Dados do processo", "secao"))
    identificacao = Table([
        [p(f"Processo: {geral.processo}"), p(f"Classe: {geral.classe}")],
        [p(f"Comarca: {geral.comarca}"), p(f"Requerente: {geral.requerente}")],
        [p(f"Vara: {geral.vara}"), p(f"Requerido: {geral.requerido}")],
    ], colWidths=[largura / 2] * 2, hAlign="LEFT", splitInRow=1)
    identificacao.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    if not resultado.premissas.get("omitir_qualificacao", False):
        partes.append(identificacao)
    partes.append(p("Critérios do cálculo", "secao"))
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
    if not somente_correcao:
        partes.append(p("Início da atualização e dos juros: competência de cada parcela, pela SELIC única." if cjf else f"Início dos juros: {inicio_juros}."))
    if referencia_selic and outras_operacoes and referencia_selic != geral.data_base.isoformat():
        partes.append(p(f"Data final das demais operações: {data_br(geral.data_base)}. A referência mensal da SELIC não altera a data exata dos demais encargos.", "nota"))
    if not cjf and not datas_independentes and not somente_correcao:
        partes.append(p("Aplica-se aos juros de 2% ao ano, respeitado o vencimento. SELIC e IPCA-E mantêm seus próprios períodos." if sem_periodo_pre else "Aplica-se aos juros de 2% ao ano e à poupança anterior à EC 113, respeitado o vencimento. SELIC e IPCA-E mantêm seus próprios períodos." if novo else "Aplica-se à poupança, respeitado o vencimento de cada parcela. A SELIC e o IPCA-E mantêm seus próprios períodos.", "nota"))
    for criterio in resultado.premissas.get("criterios", []):
        if referencia_selic and criterio.startswith("Data-base SELIC:"):
            continue  # Referência e último índice já constam no cabeçalho.
        if criterio.startswith(("Honorários sucumbenciais:", "Art. 523,", "Honorários contratuais:")):
            continue  # Demonstrados nos blocos próprios e nas notas finais, sem repetição aqui.
        if sem_periodo_pre and criterio.startswith("01/07/2009"):
            continue
        partes.append(p(criterio))

    if geral.observacoes:
        partes += [p("Observações adicionais", "secao"), p(geral.observacoes, "nota")]
    if resultado.custas_despesas:
        partes.append(PageBreak())
        partes.append(p("Custas e despesas processuais", "secao_tabela"))
        partes.append(Spacer(1, 2))
        partes.append(p(
            "Cada lançamento é atualizado exclusivamente pelo IPCA-E desde sua própria data até a data-base. "
            "Não incidem juros ou outros encargos, e o total atualizado é somado apenas ao total final.",
            "nota",
        ))
        dados_custas = [[p(x, "cabecalho") for x in (
            "Nº", "Nome", "Data", "Valor original", "Fator IPCA-E", "Correção", "Valor atualizado",
        )]]
        for item in resultado.custas_despesas:
            dados_custas.append([
                p(str(item.numero), "celula"),
                p(item.nome, "celula"),
                p(data_br(item.data), "celula"),
                p(f"R$ {moeda(item.valor_original)}", "numero"),
                p(f"{item.fator_ipcae:.4f}".replace(".", ","), "numero"),
                p(f"R$ {moeda(item.correcao_monetaria)}", "numero"),
                p(f"R$ {moeda(item.valor_atualizado)}", "numero"),
            ])
        dados_custas.append([
            "", p("TOTAL", "cabecalho"), "",
            p(f"R$ {moeda(sum(item.valor_original for item in resultado.custas_despesas))}", "numero"),
            "",
            p(f"R$ {moeda(sum(item.correcao_monetaria for item in resultado.custas_despesas))}", "numero"),
            p(f"R$ {moeda(r.custas)}", "numero"),
        ])
        larguras_custas = [28, largura - 438, 66, 86, 82, 86, 90]
        tabela_custas = LongTable(dados_custas, colWidths=larguras_custas, splitInRow=1, hAlign="LEFT")
        tabela_custas.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7F5F0")),
            ("LINEBELOW", (0, 0), (-1, 0), .6, colors.HexColor("#B2ABA0")),
            ("LINEBELOW", (0, 1), (-1, -2), .25, colors.HexColor("#E1DED8")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F7F5F0")),
            ("LINEABOVE", (0, -1), (-1, -1), .6, colors.HexColor("#072F54")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        partes.append(tabela_custas)
        partes.append(PageBreak())
    # Observações extensas podem terminar quase no rodapé. Nesse caso reserva
    # espaço para o título, a nota e o começo da tabela; relatórios comuns não
    # recebem uma quebra antecipada que aumentaria o total de páginas.
    if len(geral.observacoes or "") > 500:
        partes.append(CondPageBreak(420))
    partes.append(p("Valores por parcela", "secao"))
    nota_parcelas = p("Em cada coluna: valor usado como base, índice aplicado e valor acrescentado à parcela. O sinal \"-\" indica que a coluna não se aplica à parcela.", "nota")
    partes.append(nota_parcelas)
    curtos = {"ipcae_pre": "IPCA", "poupanca_pre": "Poupança", "selic": "SELIC", "ipcae_pos": "IPCA", "poupanca_pos": "Poupança", "juros_2aa": "Juros 2% a.a.", "limite_selic": "Limite SELIC", "multa_parcela": "Multa e encargos"}
    dados = [[p(x, "cabecalho") for x in ["Nº", "Parcela / descrição", "Correção desde" if datas_independentes else "Vencimento", "Principal", *[curtos.get(c, nome) for c, nome, _ in COLUNAS_COMPONENTES], "Total"]]]
    descricoes_extensas = {}
    largura_descricao = 120 if novo or com_multas else largura - 430 if len(COLUNAS_COMPONENTES) == 1 else largura - 496 if len(COLUNAS_COMPONENTES) == 2 else largura - 628
    for parcela in resultado.parcelas:
        descricao = parcela.historico or ""
        if parcela.valor_pago_na_data:
            descricao += f"\nOriginal: R$ {moeda(parcela.valor_bruto)}. Pago: R$ {moeda(parcela.valor_pago_na_data)}."
        if p(descricao, "celula").wrap(largura_descricao - 12, doc.height)[1] > doc.height - 90:
            descricoes_extensas[parcela.numero] = descricao
            descricao = f"Histórico integral da parcela {parcela.numero}: ver nota complementar após a tabela."
        indices = []
        for chave, _, _ in COLUNAS_COMPONENTES:
            c = parcela.componentes.get(chave, ComponenteCalculo())
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
        r.principal_apurado, *[r.totais_componentes.get(chave, 0) for chave, _, _ in COLUNAS_COMPONENTES], subtotal_parcelas)]])
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
    tabela = LongTable(dados, colWidths=larguras, repeatRows=0, splitInRow=0, hAlign="LEFT")
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7F5F0")),
        ("LINEBELOW", (0, 0), (-1, 0), .6, colors.HexColor("#B2ABA0")),
        ("LINEBELOW", (0, 1), (-1, -2), .25, colors.HexColor("#E1DED8")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F7F5F0")),
        ("LINEABOVE", (0, -1), (-1, -1), .6, colors.HexColor("#072F54")),
        ("NOSPLIT", (0, -2), (-1, -1)),
        ("NOSPLIT", (0, 0), (-1, 1)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    partes.append(tabela)
    if descricoes_extensas:
        partes.append(p("Históricos complementares", "secao"))
        for numero, descricao in descricoes_extensas.items():
            partes.append(p(f"Parcela {numero}: {descricao}", "nota"))
    if com_multas:
        colunas_multas = colunas_perfil(resultado)
        partes.append(p("Multas por parcela", "secao_tabela"))
        partes.append(p("Multa nominal calculada sobre o saldo no vencimento. Cada coluna discrimina a base, o índice e os encargos da multa; a SELIC reúne atualização e mora e não recebe juros em duplicidade. Os valores desta tabela já estão incluídos na coluna Multa e encargos da tabela de parcelas.", "nota"))
        dados_multas = [[p(x, "cabecalho") for x in ["Nº", "Parcela / descrição", "Vencimento", "Multa nominal", *[f"{nome}\n{periodo}" for _, nome, periodo in colunas_multas], "Total da multa"]]]
        for parcela in resultado.parcelas:
            m = parcela.multa_detalhes
            if m is None:
                continue
            base_nominal = f"{m.base_calculo:.4f}".replace(".", ",")
            percentual_nominal = f"{m.percentual:.4f}".replace(".", ",")
            nominal = f"Base {base_nominal}\n{percentual_nominal}%\nR$ {moeda(m.valor_original)}"
            celulas = []
            for chave, _, _ in colunas_multas:
                c = m.componentes.get(chave)
                if c is None or c.data_inicial is None:
                    celulas.append(p("-", "componente"))
                    continue
                indice = (f"Fator {c.fator_acumulado:.4f}" if c.fator_acumulado is not None else f"{c.taxa_acumulada_percentual:.4f}%").replace(".", ",")
                base_multa = f"{c.base_calculo:.4f}".replace(".", ",")
                celulas.append(p(f"{data_br(c.data_inicial)} a {data_br(c.data_final)}\nBase {base_multa}\n{indice}\nR$ {moeda(c.valor)}", "componente"))
            historico_multa = f"Ver histórico integral da parcela {parcela.numero} em nota complementar." if parcela.numero in descricoes_extensas else parcela.historico
            dados_multas.append([p(parcela.numero, "celula"), p(historico_multa, "celula"), p(data_br(parcela.data_vencimento), "celula"), p(nominal, "componente"), *celulas, p(moeda(m.total_atualizado), "numero")])
        detalhes = [x.multa_detalhes for x in resultado.parcelas if x.multa_detalhes]
        dados_multas.append(["", p("TOTAL", "celula"), "", p(moeda(sum((m.valor_original for m in detalhes), Decimal(0))), "numero"),
            *[p(moeda(sum((m.componentes.get(chave, ComponenteCalculo()).valor for m in detalhes), Decimal(0))), "numero") for chave, _, _ in colunas_multas], p(moeda(sum((m.total_atualizado for m in detalhes), Decimal(0))), "numero")])
        larguras_multas = [24, 120, 62, 76, *[(largura-358)/len(colunas_multas)]*len(colunas_multas), 76]
        tabela_multas = LongTable(dados_multas, colWidths=larguras_multas, splitByRow=1, splitInRow=0, hAlign="LEFT")
        tabela_multas.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7F5F0")),
            ("LINEBELOW", (0, 0), (-1, 0), .6, colors.HexColor("#B2ABA0")),
            ("LINEBELOW", (0, 1), (-1, -2), .25, colors.HexColor("#E1DED8")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F7F5F0")),
            ("LINEABOVE", (0, -1), (-1, -1), .6, colors.HexColor("#072F54")),
            ("NOSPLIT", (0, -2), (-1, -1)), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        partes.append(tabela_multas)
    nao_abatidos = [item for item in resultado.premissas.get("selecao_descontos", []) if not item["aplicar"]]
    if nao_abatidos:
        partes.append(p("Pagamentos não abatidos", "secao"))
        for item in nao_abatidos:
            partes.append(p(f"Lançamento {item['numero']}: {item['descricao'] or 'Sem descrição'}; "
                f"data {data_br(item['data']) if item['data'] else 'não informada'}; "
                f"valor R$ {moeda(Decimal(item['valor'])) if item['valor'] else 'não informado'}. "
                "Não selecionado; não compõe o abatimento.", "nota"))
    if resultado.descontos:
        desconto = resultado.descontos
        colunas_descontos = colunas_componentes(desconto)
        partes.append(p("Descontos atualizados", "secao"))
        partes.append(p("Cada lançamento é atualizado desde sua própria data até a data-base, com os encargos abaixo. O abatimento ocorre sobre o total atualizado das parcelas, antes das custas e despesas; não há recálculo do saldo em cada pagamento.", "nota"))
        inicio = desconto.dados_gerais.criterio_inicio_juros
        if desconto.premissas.get("perfil") != "poupanca_deposito_v1":
            partes.append(p("Início dos juros dos descontos: " + ("data de cada desconto." if inicio == "vencimento" else f"{data_br(desconto.dados_gerais.data_inicial_juros)} ({'citação' if inicio == 'citacao' else 'data específica'})."), "nota"))
        for criterio in desconto.premissas.get("criterios", []):
            partes.append(p(criterio, "nota"))
        for item in desconto.premissas.get("composicao_pagamentos", []):
            nominal = Decimal(item["encargos_sem_atualizacao"])
            if nominal:
                parte_nominal = "parte fora da conta" if desconto.premissas.get("perfil") == "poupanca_deposito_v1" else "encargos já pagos"
                partes.append(p(f"Pagamento {item['numero']}: total R$ {moeda(Decimal(item['valor']))}; "
                    f"base da atualização R$ {moeda(Decimal(item['valor']) - nominal)}; "
                    f"{parte_nominal} R$ {moeda(nominal)}, abatidos nominalmente sem nova incidência.", "nota"))
        dados_descontos = [[p(x, "cabecalho") for x in ["Nº", "Descrição", "Data do desconto", "Valor informado", *[f"{nome}\n{periodo}" for _, nome, periodo in colunas_descontos], "Atualizado"]]]
        for item in desconto.parcelas:
            celulas = []
            for chave, _, _ in colunas_descontos:
                componente = item.componentes[chave]
                if not componente.data_inicial:
                    celulas.append(p("-", "componente"))
                else:
                    indice = (f"Fator {componente.fator_acumulado:.4f}" if componente.fator_acumulado is not None else f"{componente.taxa_acumulada_percentual:.4f}%").replace(".", ",")
                    base_desconto = f"{componente.base_calculo:.4f}".replace(".", ",")
                    celulas.append(p(f"{data_br(componente.data_inicial)} a {data_br(componente.data_final)}\nBase {base_desconto}\n{indice}\nR$ {moeda(componente.valor)}", "componente"))
            dados_descontos.append([p(item.numero, "celula"), p(item.historico, "celula"), p(data_br(item.data_vencimento), "celula"), p(moeda(item.valor_bruto), "numero"), *celulas, p(moeda(item.total_parcela), "numero")])
        dados_descontos.append(["", p("TOTAL", "celula"), "", *[p(moeda(v), "numero") for v in [desconto.resumo.principal_original, *[desconto.resumo.totais_componentes[chave] for chave, _, _ in colunas_descontos], desconto.resumo.total_atualizado]]])
        larguras_descontos = [24, 140, 70, 76, *[(largura - 390) / len(colunas_descontos)] * len(colunas_descontos), 80]
        tabela_descontos = LongTable(dados_descontos, colWidths=larguras_descontos, splitByRow=1, splitInRow=0, hAlign="LEFT")
        tabela_descontos.setStyle(TableStyle([
            ("NOSPLIT", (0, 0), (-1, 1)),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7F5F0")),
            ("LINEBELOW", (0, 0), (-1, 0), .6, colors.HexColor("#B2ABA0")),
            ("LINEBELOW", (0, 1), (-1, -2), .25, colors.HexColor("#E1DED8")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F7F5F0")),
            ("LINEABOVE", (0, -1), (-1, -1), .6, colors.HexColor("#072F54")),
            ("NOSPLIT", (0, -2), (-1, -1)), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        partes.append(tabela_descontos)
        for nota in desconto.premissas.get("metodologia", []):
            partes.append(p(nota, "nota"))
        partes.append(p(f"Parcelas atualizadas: R$ {moeda(subtotal_parcelas)} - descontos abatidos: R$ {moeda(r.abatimentos)} = crédito líquido: R$ {moeda(subtotal_parcelas - r.abatimentos)}, antes dos honorários, acréscimos do cumprimento e custas.", "nota"))
        fontes_descontos = [Paragraph(f'<link href="{escape(url, {chr(34): "&quot;"})}" color="#213B5A">{texto(nome.replace("_", " "))}</link>', estilos["nota"])
                            for nome, url in desconto.premissas.get("fontes", {}).items() if url.startswith("https://")]
        if fontes_descontos:
            partes.append(p("Fontes dos descontos (links oficiais):", "nota"))
            tabela_fontes_descontos = Table([fontes_descontos[i:i+2] + ([""] if i+1 == len(fontes_descontos) else []) for i in range(0, len(fontes_descontos), 2)], colWidths=[largura / 2] * 2, hAlign="LEFT")
            tabela_fontes_descontos.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
            partes.append(tabela_fontes_descontos)
    from .relatorio_honorarios_principais import blocos_honorarios_pdf
    partes.extend(blocos_honorarios_pdf(resultado, largura, p, estilos))
    if civil_1:
        from .relatorio_taxa_legal import blocos_memoria_taxa_legal
        partes.extend(blocos_memoria_taxa_legal(resultado, largura, estilos, p))
    partes.append(p("Como o cálculo foi feito", "secao"))
    notas = [
        ("Ordem das colunas", "O primeiro par IPCA/Poupança corresponde ao período até 08/12/2021. A SELIC corresponde a 09/12/2021 a 09/09/2025. O segundo par IPCA/Poupança corresponde ao período a partir de 10/09/2025."),
        ("IPCA-E", "Atualiza o valor da parcela pelas variações mensais do IPCA-15 produzidas pelo IBGE, cuja acumulação forma o IPCA-E. O fator mensal é 1 + taxa / 100; os fatores são multiplicados. Valor da correção = base × (fator - 1). Variações negativas também são consideradas."),
        ("SELIC", "As taxas mensais são somadas, sem juros sobre juros. A base é o principal corrigido até 08/12/2021; para parcelas vencidas depois, é o próprio principal. Valor da SELIC = base × percentual acumulado ÷ 100."),
        ("Poupança", "Os juros usam a remuneração total publicada pelo Banco Central. Nos dois períodos, a base é o saldo final após IPCA-E e SELIC, sem incluir os próprios juros da poupança. Valor dos juros = base × percentual acumulado ÷ 100. Esses juros não entram na base da SELIC."),
        ("Datas e proporção", "O cálculo considera o vencimento, a data-base e as mudanças de critério, incluindo o primeiro e o último dia. Em trechos menores que um mês, SELIC e poupança são proporcionais aos dias; o fator do IPCA-E é elevado à fração de dias do mês. A poupança respeita o início dos juros informado, nunca anterior ao vencimento; para os dias 29, 30 e 31, usa a taxa de referência do dia 1 do mês seguinte."),
        ("Total da parcela", "É a soma do principal, já descontados os pagamentos informados no vencimento, com os valores das colunas de atualização e juros. As custas e despesas atualizadas são demonstradas separadamente e acrescidas somente ao total final do cálculo."),
        ("Custas e despesas", "Cada lançamento é atualizado exclusivamente pelo IPCA-E oficial do IBGE, formado pelas variações mensais do IPCA-15, desde a data informada até a data-base, sem juros ou cumulação com outro encargo. O fator, a correção em reais e o valor atualizado aparecem em tabela própria."),
        ("Casas decimais", "Bases e índices aparecem com quatro casas decimais; os valores em reais, com duas. O cálculo mantém a precisão completa, por isso refazê-lo com os índices exibidos pode gerar diferenças de centavos. IPCA-E e SELIC são apurados pela diferença entre saldos arredondados. Na poupança, o valor do segundo período é o total dos juros arredondado menos o valor do primeiro, para que a soma das colunas coincida com o total."),
    ]
    if novo:
        rotulos = (("SELIC até EC 136", "IPCA-E pós EC 136", "Juros de 2%", "Limite SELIC", "Datas e total")
                   if sem_periodo_pre else
                   ("Período anterior", "SELIC", "IPCA-E", "Juros de 2%", "Limite SELIC", "Datas e total"))
        notas = list(zip(rotulos, resultado.premissas["metodologia"]))
    if resultado.premissas.get("perfil") == "fazenda_publica_1_v1":
        notas = list(zip(("IPCA-E", "Poupança", "Datas", "Arredondamento"), resultado.premissas["metodologia"]))
    if resultado.premissas.get("perfil") == "fazenda_publica_2_v1":
        notas = list(zip(("Período inicial", "SELIC", "Datas", "Arredondamento"), resultado.premissas["metodologia"]))
    if cjf:
        notas = list(zip(("SELIC", "Competências", "Juros", "Arredondamento"), resultado.premissas["metodologia"]))
    if resultado.premissas.get("perfil") == "ipcae_1am_simples_v1":
        notas = list(zip(("IPCA-E histórico", "IPCA-E mensal", "Juros de 1%", "Arredondamento"), resultado.premissas["metodologia"]))
    if civil_1:
        notas = list(zip(("IPCA", "Taxa Legal oficial", "Datas independentes", "Base e cálculo"), resultado.premissas["metodologia"]))
    if civil_2:
        notas = list(zip(("IPCA", "Juros de 1% ao mês", "Datas independentes", "Base e cálculo"), resultado.premissas["metodologia"]))
    if somente_correcao:
        notas = list(zip(("IPCA-E mensal", "Competências", "Precisão", "Total"), resultado.premissas["metodologia"]))
    if com_multas:
        notas = [(titulo, nota.replace("com os valores das colunas de atualização e juros.",
                                       "com os valores das colunas de atualização e juros e a multa com seus próprios encargos."))
                 for titulo, nota in notas]
        notas.extend(("Multas por parcela", nota) for nota in resultado.premissas.get("metodologia", []) if nota.startswith("Multa nominal ="))
    for titulo, nota in notas:
        partes.append(Paragraph(f"<b>{texto(titulo)}.</b> {texto(nota)}", estilos["nota"]))
    if resultado.honorarios_sucumbenciais or resultado.cumprimento_sentenca or resultado.destaque_contratuais:
        partes.extend(p(nota, "nota") for nota in resultado.premissas.get("criterios", []) if nota.startswith(("Honorários sucumbenciais:", "Art. 523,", "Honorários contratuais:")))
        partes.extend(p(nota, "nota") for nota in resultado.premissas.get("metodologia", []) if nota.startswith("Valor da causa no protocolo"))
    if resultado.alertas:
        partes.append(p("Observações do cálculo", "secao"))
        partes.extend(p(alerta) for alerta in resultado.alertas)
    data_limite = resultado.premissas.get("data_base_maxima")
    if cjf and resultado.premissas.get("data_referencia_selic_maxima"):
        disponibilidade = (f"Data-base máxima para o padrão principal: {data_br(data_limite)}. "
            f"Última competência SELIC disponível: {date.fromisoformat(resultado.premissas['ultima_competencia_selic_disponivel'] + '-01'):%m/%Y}.")
    elif datas_independentes and data_limite:
        ultimo_dia = date.fromisoformat(data_limite) - timedelta(days=1)
        disponibilidade = (f"Data-base máxima para o padrão principal: {data_br(data_limite)}. "
            f"A data-base é excluída do cálculo; os índices são utilizados até {data_br(ultimo_dia)}.")
    else:
        disponibilidade = (f"Data-base máxima para o padrão principal: {data_br(data_limite)}. "
            "Todos os índices necessários estão disponíveis até essa data.")
    bloco_fontes = [p("Fontes e conferência", "secao"), p(disponibilidade, "nota")]
    nomes = {"selic_limite": "Banco Central - SELIC para comparação (SGS 4390)", "ipcae": "IBGE - IPCA-15/IPCA-E (dados via BCB SGS 7478)", "ipcae_ibge": "IBGE - metodologia e divulgação do IPCA-E", "ipcae_serie_bcb": "Banco Central - série IPCA-15 (SGS 7478)", "selic": "Banco Central - SELIC mensal (SGS 4390)",
             "poupanca_total": "Banco Central - remuneração total da poupança (SGS 195)",
             "poupanca_2009_2012": "Banco Central - poupança de 2009 a 2012 (SGS 25)",
             "poupanca_2012_2016": "Banco Central - poupança de 2012 a 2016 (SGS 195)",
             "poupanca_2017_2021": "Banco Central - poupança de 2017 a 2021 (SGS 195)",
             "tema_905": "STJ - Tema 905",
             "ipcae_custas": "IBGE - IPCA-15/IPCA-E aplicado às custas e despesas"}
    nomes.update({"correcao_valor_causa": "Fonte da correção do valor da causa", "cpc_523": "CPC/2015 - cumprimento de sentença"})
    nomes.update({"ipca": "Banco Central - IPCA oficial (SGS 433)", "taxa_legal": "Banco Central - Taxa Legal oficial (SGS 29543)",
                  "resolucao_taxa_legal": "CMN - Resolução 5.171/2024", "calculadora_taxa_legal": "BCB - Metodologia da Taxa Legal"})
    links = []
    nomes.update({"selic_historica": "Banco Central - SELIC histórica (SGS 4390)", "manual_cjf": "CJF - Manual de Cálculos da Justiça Federal", "orientacao_cjf": "CJF - Orientação sobre a EC 136/2025"})
    if cjf:
        nomes["selic_limite"] = "Banco Central - SELIC mensal, série recente (SGS 4390)"
    for chave, nome in nomes.items():
        if sem_periodo_pre and (chave.startswith("poupanca") or chave == "tema_905"):
            continue
        url = resultado.premissas.get("fontes", {}).get(chave, "")
        if url.startswith("https://"):
            links.append(Paragraph(f'<link href="{escape(url, {chr(34): "&quot;"})}" color="#213B5A">{texto(nome)}</link>', estilos["nota"]))
    if links:
        fontes = Table([links[i:i + 2] + ([""] if i + 1 == len(links) else []) for i in range(0, len(links), 2)], colWidths=[largura / 2] * 2, hAlign="LEFT")
        fontes.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        bloco_fontes.append(fontes)
    partes.append(KeepTogether(bloco_fontes))

    def rodape(canvas, _doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#E1DED8"))
        canvas.line(40, 32, pagina[0] - 40, 32)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#555555"))
        complemento = f" | Demais operações: {data_br(geral.data_base)}" if referencia_selic and outras_operacoes and referencia_selic != geral.data_base.isoformat() else ""
        canvas.drawString(40, 20, f"Barreto Fontes | {rotulo_data} {data_br(data_cabecalho)}{complemento}")
        canvas.drawRightString(pagina[0] - 40, 20, f"Página {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(partes, onFirstPage=rodape, onLaterPages=rodape)
    return buffer.getvalue()
