"""Contrato visual e blocos comuns aos demonstrativos de todas as modalidades."""
from datetime import date
from decimal import Decimal
from pathlib import Path
import re
from html import unescape
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import CondPageBreak, Image, KeepTogether, LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

AZUL = colors.HexColor("#072F54")
AMARELO = colors.HexColor("#FBC108")
FUNDO = colors.HexColor("#F7F5F0")
LINHA = colors.HexColor("#E1DED8")
CINZA = colors.HexColor("#555555")
ESPACO_ENTRE_OPERACOES = 1.5 * cm
COLUNA_DESCRICAO = "Descrição"


def cabecalho_componente(nome, periodo, *, periodo_na_celula=False):
    """Omite períodos repetidos nas células; mantém os marcos nos resumos."""
    nome = re.sub(r"\s+(?:pré|pós) EC \d+/\d{4}\b", "", nome)
    genericos = {"até a data-base", "desde o início da correção", "desde o início dos juros"}
    return nome if periodo_na_celula or periodo in genericos else f"{nome}\n{periodo}"


def indice_memoria(nome):
    """Rótulo curto na coluna de índice, preservando a fonte na seção própria."""
    if "Taxa Legal" in nome:
        return "Taxa Legal"
    if "IPCA-E" in nome or "IPCA-15" in nome:
        return "IPCA-E"
    if "IPCA" in nome:
        return "IPCA"
    if "INPC" in nome:
        return "INPC"
    return nome


def distribuir_larguras(linhas, larguras):
    """Distribui a largura pela leitura dos títulos e conteúdos, sem mudar fontes."""
    largura = sum(larguras)
    minimas, titulos, conteudos, flexiveis, descricoes = [], [], [], [], []
    for coluna, cabecalho in enumerate(linhas[0]):
        titulo = cabecalho.getPlainText() if isinstance(cabecalho, Paragraph) else str(cabecalho)
        font = cabecalho.style.fontName if isinstance(cabecalho, Paragraph) else "Helvetica-Bold"
        tamanho = cabecalho.style.fontSize if isinstance(cabecalho, Paragraph) else 8
        palavras = titulo.split()
        minimo = max((stringWidth(palavra, font, tamanho) for palavra in palavras), default=0) + 14
        desejado = stringWidth(titulo, font, tamanho) + 14
        # Títulos extensos continuam podendo ocupar duas linhas.
        titulos.append(max(minimo, min(desejado, 150)))
        conteudo = 0
        textual = False
        for linha in linhas[1:]:
            celula = linha[coluna]
            if isinstance(celula, Paragraph):
                minimo = max(minimo, celula.minWidth() + 14)
                linhas_celula = [unescape(re.sub(r"<[^>]+>", "", trecho))
                                for trecho in re.split(r"<br\s*/?>", celula.text, flags=re.IGNORECASE)]
                texto_celula = "\n".join(linhas_celula)
                for grupo in re.findall(r"\b(?:Base|Fator)\s+[-+]?\d[\d.,]*|R\$\s*[-+]?\d[\d.,]*", texto_celula):
                    minimo = max(minimo, stringWidth(grupo, celula.style.fontName, celula.style.fontSize) + 14)
                conteudo = max(conteudo, min(140, max((stringWidth(trecho, celula.style.fontName, celula.style.fontSize)
                               for trecho in linhas_celula), default=0) + 14))
                textual |= celula.style.alignment != TA_RIGHT and len(texto_celula) > 40
            elif celula:
                minimo = max(minimo, stringWidth(str(celula), "Helvetica", 8) + 14)
        descricao = titulo in (COLUNA_DESCRICAO, "Rubrica", "Base") and (
            titulo != "Base" or textual)
        if descricao:
            descricoes.append(coluna)
        if descricao or textual or titulo in ("Período e critério", "Período e cálculo"):
            flexiveis.append(coluna)
        minimas.append(max(24, min(minimo, largura * .18)))
        conteudos.append(conteudo)
    if sum(minimas) > largura:
        fator = largura / sum(minimas)
        return [valor * fator for valor in minimas]
    ajustadas = minimas[:]
    restante = largura - sum(ajustadas)

    def reservar(coluna, alvo):
        nonlocal restante
        acrescimo = min(restante, max(0, alvo - ajustadas[coluna]))
        ajustadas[coluna] += acrescimo
        restante -= acrescimo

    for coluna in descricoes:
        reservar(coluna, min(200 if len(larguras) <= 7 else 150, largura * .3))
    # Resolver primeiro as quebras que exigem somente alguns pontos adicionais.
    for coluna in sorted(range(len(larguras)), key=lambda c: max(0, titulos[c] - ajustadas[c])):
        reservar(coluna, titulos[coluna])
    for coluna in range(len(larguras)):
        if coluna not in flexiveis:
            reservar(coluna, conteudos[coluna])
    destinos = flexiveis or list(range(len(larguras)))
    for coluna in destinos:
        ajustadas[coluna] += restante / len(destinos)
    return ajustadas


def tabela_operacional(linhas, larguras, *, total=False, alturas=None):
    """Grade comum: cabeçalho, divisórias, margens internas e fechamento."""
    larguras = distribuir_larguras(linhas, larguras)
    if alturas is not None:
        # Recalcular após redistribuição; manter os mínimos de segurança das memórias.
        alturas = [max(altura or 0, max((celula.wrap(max(largura_coluna - 12, 1), 100000)[1]
                   for celula, largura_coluna in zip(linha, larguras, strict=True)
                   if isinstance(celula, Paragraph)), default=0) + 8)
                   for linha, altura in zip(linhas, alturas, strict=True)]
    tabela = LongTable(linhas, colWidths=larguras, rowHeights=alturas,
                      repeatRows=0, splitByRow=1, splitInRow=0, hAlign="LEFT")
    regras = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#171717")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BACKGROUND", (0, 0), (-1, 0), FUNDO),
        ("LINEBELOW", (0, 0), (-1, 0), .6, colors.HexColor("#B2ABA0")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (-1, 0), AZUL),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("NOSPLIT", (0, 0), (-1, min(1, len(linhas) - 1))),
    ]
    fim_dados = len(linhas) - (2 if total else 1)
    if fim_dados >= 1:
        regras.append(("LINEBELOW", (0, 1), (-1, fim_dados), .25, LINHA))
    if total:
        regras.extend([
            ("BACKGROUND", (0, -1), (-1, -1), FUNDO),
            ("LINEABOVE", (0, -1), (-1, -1), .6, AZUL),
            ("NOSPLIT", (0, -2), (-1, -1)),
        ])
    else:
        regras.append(("LINEBELOW", (0, -1), (-1, -1), .6, AZUL))
    tabela.setStyle(TableStyle(regras))
    return tabela


def resumo_financeiro(titulos, valores, largura, p):
    """Campos iguais, com valores alinhados e total na última coluna."""
    quantias = [f"R$ {moeda(valor)}" for valor in valores]
    # Rótulos podem quebrar; quantias nunca são comprimidas ou divididas.
    minimo = max(70, *(stringWidth(valor, "Helvetica-Bold" if i == len(valores) - 1
                                  else "Helvetica", 12 if i == len(valores) - 1
                                  else 10) + 12 for i, valor in enumerate(quantias)))
    colunas = max(1, min(len(titulos), int(largura // minimo)))
    quantidade_linhas = (len(titulos) + colunas - 1) // colunas
    colunas = (len(titulos) + quantidade_linhas - 1) // quantidade_linhas
    linhas = []
    destaque = None
    for inicio in range(0, len(titulos), colunas):
        fim = min(inicio + colunas, len(titulos))
        indices = list(range(inicio, fim))
        # Em resumo longo, manter o total à direita da última linha.
        if fim == len(titulos) and len(indices) < colunas:
            indices = indices[:-1] + [None] * (colunas - len(indices)) + indices[-1:]
        rotulos, numeros = [], []
        for coluna, indice in enumerate(indices):
            total = indice == len(titulos) - 1
            rotulos.append("" if indice is None else p(titulos[indice], "rotulo_total" if total else "rotulo"))
            numeros.append("" if indice is None else p(quantias[indice], "valor_total" if total else "metrica"))
            if total:
                destaque = (coluna, len(linhas))
        linhas.extend([rotulos, numeros])
    tabela = Table(linhas, colWidths=[largura / colunas] * colunas, hAlign="LEFT")
    estilo = [
        ("BACKGROUND", (0, 0), (-1, -1), FUNDO),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    for linha in range(0, len(linhas), 2):
        estilo.extend([("TOPPADDING", (0, linha), (-1, linha), 6),
                       ("BOTTOMPADDING", (0, linha), (-1, linha), 3),
                       ("TOPPADDING", (0, linha + 1), (-1, linha + 1), 3),
                       ("BOTTOMPADDING", (0, linha + 1), (-1, linha + 1), 6)])
        estilo.append(("VALIGN", (0, linha + 1), (-1, linha + 1), "BOTTOM"))
    estilo.append(("LINEABOVE", destaque, destaque, 2, AMARELO))
    tabela.setStyle(TableStyle(estilo))
    return tabela


class EspacoEntreOperacoes(Spacer):
    """Reserva 1,5 cm entre blocos, sem acrescentar espaço no topo da página."""

    def __init__(self):
        super().__init__(1, ESPACO_ENTRE_OPERACOES)

    def wrap(self, largura, altura):
        frame = getattr(self, "_frame", None)
        if frame is None:
            return self.width, ESPACO_ENTRE_OPERACOES
        self.height = (0 if frame._atTop else
                       max(0, ESPACO_ENTRE_OPERACOES - frame._prevASpace))
        return self.width, self.height


def separar_operacoes(introducao, tabela, largura, altura):
    """Mantém título, explicações e primeira linha juntos antes de dividir a tabela."""
    introducao[0].style = ParagraphStyle(
        "secao_apos_operacao", parent=introducao[0].style, spaceBefore=0)
    necessario = sum(item.wrap(largura, altura)[1] + item.getSpaceBefore() +
                     item.getSpaceAfter() for item in introducao)
    if tabela is not None:
        tabela.wrap(largura, altura)
        # Em tabela de um lançamento, preservar também o total, unido à última linha.
        linhas = 3 if len(tabela._rowHeights) == 3 else 2
        necessario += sum(tabela._rowHeights[:linhas])
    return [CondPageBreak(min(ESPACO_ENTRE_OPERACOES + necessario, altura - 12)),
            EspacoEntreOperacoes()]

NOMES_FONTES = {
    "ipcae_historico": "IBGE - IPCA-E histórico (BCB SGS 10764)",
    "moedas_historicas": "Histórico oficial dos padrões monetários brasileiros",
    "inpc": "IBGE - INPC (dados via BCB SGS 188)",
    "ipca": "Banco Central - IPCA oficial (SGS 433)",
    "ipcae": "IBGE - IPCA-15/IPCA-E (dados via BCB SGS 10764 e 7478)",
    "ipcae_ibge": "IBGE - metodologia e divulgação do IPCA-E",
    "ipcae_serie_bcb": "Banco Central - série IPCA-15 (SGS 7478)",
    "selic": "Banco Central - SELIC mensal (SGS 4390)",
    "selic_limite": "Banco Central - SELIC para comparação (SGS 4390)",
    "selic_historica": "Banco Central - SELIC histórica (SGS 4390)",
    "manual_cjf": "CJF - Manual de Cálculos da Justiça Federal",
    "orientacao_cjf": "CJF - Orientação sobre a EC 136/2025",
    "taxa_legal": "Banco Central - Taxa Legal oficial (SGS 29543)",
    "selic_diaria_anualizada": "Banco Central - SELIC anual diária (SGS 1178)",
    "ipca15_reconstrucao": "Banco Central - IPCA-15 histórico (SGS 7478)",
    "resolucao_taxa_legal": "CMN - Resolução 5.171/2024",
    "calculadora_taxa_legal": "BCB - Metodologia da Taxa Legal",
    "poupanca_total": "Banco Central - remuneração total da poupança (SGS 195)",
    "poupanca_2009_2012": "Banco Central - poupança de 2009 a 2012 (SGS 25)",
    "poupanca_2012_2016": "Banco Central - poupança de 2012 a 2016 (SGS 195)",
    "poupanca_2017_2021": "Banco Central - poupança de 2017 a 2021 (SGS 195)",
    "tema_905": "STJ - Tema 905",
    "correcao_valor_causa": "Fonte oficial da correção do valor da causa",
    "correcao_honorarios_fixados": "Fonte oficial da correção dos honorários fixados",
    "poupanca_regra": "Banco Central - regra de remuneração da poupança",
    "cpc_523": "CPC/2015 - cumprimento de sentença",
    "codigo_civil_1916": "Código Civil de 1916 - art. 1.062",
    "codigo_civil_2002": "Código Civil de 2002 - vigência",
}


def texto(valor):
    value = str(valor or "").replace("–", "-").replace("—", "-")
    value = re.sub(r"\bvalor informado\b", "Valor", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+até a data[- ]base\b", "", value, flags=re.IGNORECASE)
    value = "".join(c for c in value if ord(c) >= 32 or c == "\n")
    return escape(value).replace("\n", "<br/>")


def moeda(valor):
    return f"{Decimal(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def data_br(valor):
    if not valor:
        return "Não informado"
    return (date.fromisoformat(valor) if isinstance(valor, str) else valor).strftime("%d/%m/%Y")


def notas_tecnicas(criterios, metodologia):
    notas = list(criterios)
    selic_unica = any("SELIC como índice único" in nota for nota in notas)
    for nota in metodologia:
        if selic_unica:
            if nota.startswith("SELIC reúne correção e mora. "):
                continue  # Índice único já explicado; não enumerar encargos adicionais genéricos.
        if nota and nota not in notas:
            notas.append(nota)
    return notas


def criar_documento(buffer, subject):
    return SimpleDocTemplate(
        buffer, pagesize=landscape(A4), rightMargin=40, leftMargin=40,
        topMargin=32, bottomMargin=40, title="Demonstrativo de cálculo",
        author="Barreto Fontes Sociedade de Advogados", subject=subject,
    )


def criar_estilos():
    configs = {
        "normal": dict(fontSize=9, leading=12, spaceAfter=5),
        "titulo": dict(fontName="Helvetica-Bold", fontSize=18, leading=23, spaceAfter=5, textColor=AZUL),
        "subtitulo": dict(fontSize=8, leading=11, textColor=CINZA),
        "secao": dict(fontName="Helvetica-Bold", fontSize=10, leading=13, spaceBefore=12, spaceAfter=7, keepWithNext=True, textColor=AZUL, textTransform="uppercase"),
        "celula": dict(fontSize=8, leading=9, splitLongWords=True),
        "numero": dict(fontSize=8, leading=10, alignment=TA_RIGHT),
        "componente": dict(fontSize=7.5, leading=9, alignment=TA_RIGHT),
        "cabecalho": dict(fontName="Helvetica-Bold", fontSize=8, leading=10, alignment=TA_CENTER, textColor=AZUL),
        "nota": dict(fontSize=8, leading=11, spaceAfter=5, textColor=CINZA),
        "tecnico": dict(fontSize=9, leading=12, spaceAfter=4),
        "tecnico_dados": dict(fontSize=9, leading=12, spaceAfter=2),
        "tecnico_titulo": dict(fontName="Helvetica-Bold", fontSize=9, leading=12, spaceBefore=8, spaceAfter=4, keepWithNext=True, textColor=AZUL, textTransform="uppercase"),
        "total": dict(fontName="Helvetica-Bold", fontSize=12, leading=16, spaceAfter=3),
        "valor_resumo": dict(fontSize=10, leading=13, alignment=TA_RIGHT),
        "valor_total": dict(fontName="Helvetica-Bold", fontSize=12, leading=15, alignment=TA_RIGHT, textColor=AZUL),
        "metrica": dict(fontSize=10, leading=13),
        "rotulo": dict(fontSize=8, leading=10, textColor=CINZA),
        "valor": dict(fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=AZUL, alignment=TA_RIGHT),
        "destaque": dict(fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=AZUL, alignment=TA_RIGHT),
        "formula_rotulo": dict(fontSize=8, leading=10, textColor=CINZA, alignment=TA_CENTER),
        "formula_valor": dict(fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=AZUL, alignment=TA_CENTER),
        "formula_operador": dict(fontName="Helvetica-Bold", fontSize=13, leading=15, textColor=CINZA, alignment=TA_CENTER),
        "formula_resultado": dict(fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=AZUL, alignment=TA_CENTER),
    }
    estilos = {}
    for nome, config in configs.items():
        atributos = {"fontName": "Helvetica", "textColor": colors.HexColor("#171717"), **config}
        estilos[nome] = ParagraphStyle(nome, **atributos)
    estilos["secao_tabela"] = ParagraphStyle("secao_tabela", parent=estilos["secao"], keepWithNext=False)
    estilos["rotulo_total"] = ParagraphStyle("rotulo_total", parent=estilos["rotulo"], alignment=TA_RIGHT)
    return estilos


def cabecalho(largura, p, titulo, metadados, chave=None):
    logo = Image(str(Path(__file__).resolve().parents[1] / "assets" / "logo-barreto-fontes.png"))
    image_width, image_height = logo.imageWidth, logo.imageHeight
    logo.drawWidth = 122
    logo.drawHeight = 122 * image_height / image_width
    linhas = [p(titulo, "titulo"), p(metadados, "subtitulo")]
    if chave:
        linhas.append(p(f"Chave de recuperação: {chave}", "subtitulo"))
    tabela = Table([[logo, linhas]], colWidths=[157, largura - 157], hAlign="LEFT")
    tabela.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16), ("LINEBELOW", (0, 0), (-1, -1), .5, LINHA),
    ]))
    return tabela


def identificacao(geral, largura, p):
    tabela = Table([
        [p(f"Processo: {geral.processo or ''}"), p(f"Classe: {geral.classe or ''}")],
        [p(f"Comarca: {geral.comarca or ''}"), p(f"Requerente: {geral.requerente or ''}")],
        [p(f"Vara: {geral.vara or ''}"), p(f"Requerido: {geral.requerido or ''}")],
    ], colWidths=[largura / 2] * 2, hAlign="LEFT", splitInRow=1)
    tabela.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return [p("Dados do processo", "secao"), tabela]


def observacoes(observacao, alertas, p):
    if not observacao and not alertas:
        return []
    blocos = [p("Observações e ressalvas", "secao")]
    if observacao:
        blocos.append(p(observacao, "nota"))
    for alerta in alertas:
        # Formata apenas quantias de alertas gerados pelo motor, sem alterar a entrada.
        alerta = re.sub(r"R\$ (-?\d+\.\d{2})(?!\d|,|\.\d)", lambda m: "R$ " + moeda(m[1]), alerta)
        blocos.append(p(alerta, "nota"))
    return blocos


def custas_despesas(itens, largura, p, altura):
    if not itens:
        return []
    linhas = [[p(t, "cabecalho") for t in (
        "Nº", COLUNA_DESCRICAO, "Data", "Valor original", "Fator IPCA-E", "Correção", "Valor atualizado",
    )]]
    for item in itens:
        linhas.append([
            p(item.numero, "celula"), p(item.nome, "celula"), p(data_br(item.data), "celula"),
            p(f"R$ {moeda(item.valor_original)}", "numero"),
            p(f"{item.fator_ipcae:.4f}".replace(".", ","), "numero"),
            p(f"R$ {moeda(item.correcao_monetaria)}", "numero"), p(f"R$ {moeda(item.valor_atualizado)}", "numero"),
        ])
    linhas.append(["", p("TOTAL", "cabecalho"), "",
        p(f"R$ {moeda(sum((item.valor_original for item in itens), Decimal(0)))}", "numero"), "",
        p(f"R$ {moeda(sum((item.correcao_monetaria for item in itens), Decimal(0)))}", "numero"),
        p(f"R$ {moeda(sum((item.valor_atualizado for item in itens), Decimal(0)))}", "numero")])
    tabela = tabela_operacional(linhas, [28, largura - 438, 66, 86, 82, 86, 90], total=True)
    introducao = [p("CUSTAS E DESPESAS PROCESSUAIS", "secao_tabela"),
        p("Custas corrigidas somente pelo IPCA-E desde cada lançamento, sem juros; somadas apenas ao total final, fora do principal e da base dos honorários.", "nota")]
    return [*separar_operacoes(introducao, tabela, largura, altura), *introducao, tabela]


def anexo_tecnico(anexos, largura, p, altura):
    """Separa o anexo da metodologia e mantém o título junto à primeira memória."""
    if not anexos:
        return []
    memoria = list(anexos)
    # O intervalo inicial passa a preceder o título do anexo, sem duplicação.
    while memoria and isinstance(memoria[0], (CondPageBreak, EspacoEntreOperacoes)):
        memoria.pop(0)
    titulo = p("Anexo técnico - Memórias detalhadas", "secao")
    introducao = [titulo]
    for item in memoria:
        if not isinstance(item, Paragraph):
            break
        introducao.append(item)
    tabela = memoria[len(introducao) - 1] if len(memoria) >= len(introducao) else None
    if not isinstance(tabela, Table):
        tabela = None
    return [*separar_operacoes(introducao, tabela, largura, altura), titulo, *memoria]


def fontes_conferencia(grupos, largura, p, estilos, notas=(), *, altura=523):
    """Uma fonte por URL, com identificação de todas as operações que a utilizam."""
    fontes = {}
    for escopo, nomes in grupos:
        for nome, url in nomes.items():
            if not isinstance(url, str) or not url.startswith("https://"):
                continue
            rotulo = NOMES_FONTES.get(nome.lower().replace(" ", "_"), nome)
            item = fontes.setdefault(url, {"nome": rotulo, "escopos": []})
            if escopo not in item["escopos"]:
                item["escopos"].append(escopo)
    blocos = [p("Fontes e conferência", "secao"), *[p(nota, "nota") for nota in notas]]
    links = []
    for url, item in fontes.items():
        links.append(Paragraph(
            f'<link href="{escape(url, {chr(34): "&quot;"})}" color="#213B5A">{texto(item["nome"])}</link>'
            f' - {texto("; ".join(item["escopos"]))}', estilos["tecnico"],
        ))
    tabela = None
    if links:
        tabela = Table([links[i:i + 2] + ([""] if i + 1 == len(links) else []) for i in range(0, len(links), 2)], colWidths=[largura / 2] * 2, hAlign="LEFT")
        tabela.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 10)]))
        blocos.append(tabela)
    introducao = blocos[:-1] if tabela is not None else blocos
    return [*separar_operacoes(introducao, tabela, largura, altura), *blocos]


def criar_rodape(rotulo_data, data_base, complemento=""):
    def rodape(canvas, _doc):
        canvas.saveState()
        canvas.setStrokeColor(LINHA)
        canvas.line(40, 32, landscape(A4)[0] - 40, 32)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(CINZA)
        canvas.drawString(40, 20, f"Barreto Fontes | {rotulo_data} {data_br(data_base)}{complemento}")
        canvas.drawRightString(landscape(A4)[0] - 40, 20, f"Página {canvas.getPageNumber()}")
        canvas.restoreState()
    return rodape
