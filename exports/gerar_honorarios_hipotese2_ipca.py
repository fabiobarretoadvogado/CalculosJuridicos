"""Gera o demonstrativo da hipotese 2 com o IPCA oficial do projeto."""

from __future__ import annotations

import calendar
import io
import json
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
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


ROOT = Path(__file__).resolve().parents[1]
BASE_IPCA = ROOT / "backend" / "data" / "ipca_oficial.json"
LOGO = ROOT / "backend" / "liquidacao_custom" / "assets" / "logo-barreto-fontes.png"
OUTPUT = ROOT / "output" / "pdf" / "honorarios_hipotese_2_ipca_202440103644.pdf"

AZUL = colors.HexColor("#072F54")
AMARELO = colors.HexColor("#FBC108")
TEXTO = colors.HexColor("#171717")
SECUNDARIO = colors.HexColor("#555555")
SUPERFICIE = colors.HexColor("#F7F5F0")
DIVISORIA = colors.HexColor("#E1DED8")
DIVISORIA_MEDIA = colors.HexColor("#B2ABA0")


def moeda(valor: Decimal) -> Decimal:
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def brl(valor: Decimal) -> str:
    texto = f"{moeda(valor):,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def proximo_mes(valor: date) -> date:
    return date(valor.year + valor.month // 12, valor.month % 12 + 1, 1)


def calcular():
    dados = json.loads(BASE_IPCA.read_text(encoding="utf-8"))
    valor_original = Decimal("49498.12")
    inicio = date(2024, 11, 27)
    fim = date(2026, 8, 31)
    saldo = valor_original
    memoria = []
    cursor = inicio
    while cursor <= fim:
        ultimo = min(fim, proximo_mes(cursor) - timedelta(days=1))
        dias = (ultimo - cursor).days + 1
        dias_mes = calendar.monthrange(cursor.year, cursor.month)[1]
        fracao = Decimal(dias) / Decimal(dias_mes)
        competencia = cursor.strftime("%Y-%m")
        taxa = Decimal(dados["ipca"][competencia])
        fator = (Decimal(1) + taxa / Decimal(100)) ** fracao
        anterior = saldo
        saldo *= fator
        memoria.append(
            {
                "competencia": competencia,
                "inicio": cursor,
                "fim": ultimo,
                "dias": dias,
                "dias_mes": dias_mes,
                "taxa": taxa,
                "fator": fator,
                "base": anterior,
                "corrigido": saldo,
            }
        )
        cursor = ultimo + timedelta(days=1)
    atualizado = moeda(saldo)
    correcao = moeda(atualizado - valor_original)
    honorarios = moeda(atualizado * Decimal("0.10"))
    return dados, valor_original, atualizado, correcao, honorarios, saldo / valor_original, memoria


def gerar_pdf() -> bytes:
    dados, original, atualizado, correcao, honorarios, fator_total, memoria = calcular()
    assert atualizado == Decimal("53516.27")
    assert correcao == Decimal("4018.15")
    assert honorarios == Decimal("5351.63")
    assert len(memoria) == 22

    buffer = io.BytesIO()
    pagina = landscape(A4)
    largura_util = pagina[0] - 80
    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagina,
        leftMargin=40,
        rightMargin=40,
        topMargin=32,
        bottomMargin=40,
        title="Demonstrativo de calculo",
        author="Barreto Fontes Sociedade de Advogados",
    )

    estilos = {
        "titulo": ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=18, leading=21, textColor=AZUL),
        "meta": ParagraphStyle("meta", fontName="Helvetica", fontSize=8, leading=11, textColor=SECUNDARIO),
        "secao": ParagraphStyle("secao", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=AZUL, spaceBefore=9, spaceAfter=5),
        "corpo": ParagraphStyle("corpo", fontName="Helvetica", fontSize=9, leading=12, textColor=TEXTO),
        "nota": ParagraphStyle("nota", fontName="Helvetica", fontSize=8, leading=10.5, textColor=SECUNDARIO),
        "cab": ParagraphStyle("cab", fontName="Helvetica-Bold", fontSize=8, leading=9.5, textColor=AZUL, alignment=1),
        "cel": ParagraphStyle("cel", fontName="Helvetica", fontSize=8, leading=9.5, textColor=TEXTO),
        "num": ParagraphStyle("num", fontName="Helvetica", fontSize=8, leading=9.5, textColor=TEXTO, alignment=TA_RIGHT),
        "rotulo": ParagraphStyle("rotulo", fontName="Helvetica", fontSize=7.5, leading=9, textColor=SECUNDARIO),
        "valor": ParagraphStyle("valor", fontName="Helvetica-Bold", fontSize=11, leading=13, textColor=AZUL),
        "total": ParagraphStyle("total", fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=AZUL, alignment=TA_RIGHT),
    }

    def p(texto, estilo="corpo"):
        return Paragraph(str(texto), estilos[estilo])

    logo = Image(str(LOGO), width=122, height=122 * 0.285)
    cabecalho = Table(
        [[logo, p("Demonstrativo de cálculo", "titulo")], ["", p("Data-base 31/08/2026 | 1 base de honorários | IPCA", "meta")]],
        colWidths=[145, largura_util - 145],
    )
    cabecalho.setStyle(TableStyle([
        ("SPAN", (0, 0), (0, 1)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LINEBELOW", (0, 1), (-1, 1), 0.6, DIVISORIA),
    ]))

    resumo = Table(
        [[
            p("VALOR NO PROTOCOLO", "rotulo"), p("CORREÇÃO IPCA", "rotulo"),
            p("BASE ATUALIZADA", "rotulo"), p("PERCENTUAL", "rotulo"), p("HONORÁRIOS", "rotulo"),
        ], [
            p(brl(original), "valor"), p(brl(correcao), "valor"), p(brl(atualizado), "valor"),
            p("10,0000%", "valor"), p(brl(honorarios), "total"),
        ]],
        colWidths=[largura_util * x for x in (0.19, 0.18, 0.20, 0.15, 0.28)],
    )
    resumo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SUPERFICIE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 8), ("BOTTOMPADDING", (0, 1), (-1, 1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("LINEABOVE", (-1, 0), (-1, 0), 2, AMARELO),
    ]))

    processo = Table(
        [[p("Processo", "rotulo"), p("Classe", "rotulo")],
         [p("202601150833<br/><font size='7'>Origem: 202440103644 | CNJ: 0009756-68.2024.8.25.0083</font>"), p("Recurso Inominado Cível")],
         [p("Recorrente / autor", "rotulo"), p("Recorrido / executado", "rotulo")],
         [p("MANOEL MESSIAS DE JESUS MENEZES"), p("EDILSON DA PAIXÃO")],
         [p("Juízo", "rotulo"), p("Objeto", "rotulo")],
         [p("2ª Turma Recursal do TJSE"), p("Hipótese 2 - honorários sobre o valor atribuído ao cumprimento de sentença")]],
        colWidths=[largura_util / 2, largura_util / 2],
    )
    processo.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    historia = [cabecalho, Spacer(1, 12), resumo, p("Dados do processo", "secao"), processo]
    historia.extend([
        p("Critérios do cálculo", "secao"),
        p("Valor da causa de R$ 49.498,12 em 27/11/2024, corrigido exclusivamente pelo IPCA até 31/08/2026, sem juros. Honorários fixados em 10% sobre a base atualizada. A decisão é de 18/09/2026; como o IPCA é mensal, utilizou-se a última competência oficial disponível, agosto/2026."),
        p("O motor aplica proporcionalmente os meses parciais pelos dias corridos, incluindo as datas inicial e final, e preserva eventual deflação. A base atualizada é arredondada ao centavo pelo método HALF_UP; em seguida aplica-se o percentual dos honorários.", "nota"),
        p("Memória da correção do valor da causa", "secao"),
    ])

    linhas = [[p(x, "cab") for x in ("Competência", "Período", "Base", "IPCA", "Fator", "Valor corrigido")]]
    for item in memoria:
        periodo = f"{item['inicio']:%d/%m/%Y} a {item['fim']:%d/%m/%Y}"
        linhas.append([
            p(item["competencia"], "cel"), p(periodo, "cel"), p(brl(item["base"]), "num"),
            p(f"{item['taxa']:.4f}%".replace(".", ","), "num"),
            p(f"{item['fator']:.8f}".replace(".", ","), "num"), p(brl(item["corrigido"]), "num"),
        ])
    linhas.append([p("TOTAL", "cab"), "", "", "", p(f"{fator_total:.8f}".replace(".", ","), "num"), p(brl(atualizado), "num")])
    tabela = LongTable(linhas, colWidths=[72, 130, 125, 80, 96, largura_util - 503], repeatRows=0, splitInRow=0)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SUPERFICIE), ("LINEBELOW", (0, 0), (-1, 0), 0.5, DIVISORIA_MEDIA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5), ("LINEABOVE", (0, -1), (-1, -1), 0.8, AZUL),
        ("BACKGROUND", (0, -1), (-1, -1), SUPERFICIE), ("SPAN", (0, -1), (3, -1)),
    ]))
    historia.append(tabela)
    historia.extend([
        p("Como o cálculo foi feito", "secao"),
        p(
            "Em cada competência: saldo anterior × (1 + IPCA mensal ÷ 100)"
            "<super>fração do mês</super>. O fator acumulado resultou em "
            f"{fator_total:.8f}. A correção monetária foi de {brl(correcao)}, "
            f"formando a base de {brl(atualizado)}. Honorários: "
            f"{brl(atualizado)} × 10% = {brl(honorarios)}."
        ),
        p("Fontes e conferência", "secao"),
        p("Índice: série 433 do Banco Central do Brasil, base oficial arquivada no projeto em backend/data/ipca_oficial.json, obtida em " + dados["obtido_em"] + ". Fonte pública: " + dados["fontes"]["ipca"], "nota"),
        p("Título judicial conferido: decisão monocrática de 18/09/2026 no Recurso Inominado Cível nº 202601150833, que fixou honorários em 10% do valor da causa atualizado.", "nota"),
    ])

    def rodape(canv: canvas.Canvas, documento):
        canv.saveState()
        canv.setStrokeColor(DIVISORIA)
        canv.setLineWidth(0.5)
        canv.line(40, 29, pagina[0] - 40, 29)
        canv.setFont("Helvetica", 8)
        canv.setFillColor(SECUNDARIO)
        canv.drawString(40, 17, "Barreto Fontes | Data-base 31/08/2026")
        canv.drawRightString(pagina[0] - 40, 17, f"Página {documento.page}")
        canv.restoreState()

    doc.build(historia, onFirstPage=rodape, onLaterPages=rodape)
    return buffer.getvalue()


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(gerar_pdf())
    print(OUTPUT)
