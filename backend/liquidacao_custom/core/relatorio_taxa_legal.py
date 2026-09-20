"""Memória mensal da Taxa Legal: taxas oficiais com seis casas decimais."""
from decimal import Decimal as D
from reportlab.lib import colors
from reportlab.platypus import KeepTogether, LongTable, TableStyle


def linhas_taxa_legal(resultado):
    yield ["Parcela", "Mês", "Período", "Dias / mês", "Taxa Legal mensal (%)", "Taxa proporcional (%)", "Acumulada (%)", "Base corrigida", "Juros do trecho", "Juros acumulados"]
    for m in resultado.premissas.get("memoria_taxa_legal", []):
        yield [m["parcela"], m["competencia"], m["inicio"] + " a " + m["fim"], f"{m['dias']} / {m['dias_mes']}",
               m["taxa_mensal"], m["taxa_proporcional"], m["taxa_acumulada"], m["base"], m["juros_periodo"], m["juros_acumulados"]]


def blocos_memoria_taxa_legal(resultado, largura, estilos, p):
    from .relatorio_pdf import moeda, data_br
    blocos = []
    for parcela in resultado.parcelas:
        linhas = [m for m in resultado.premissas.get("memoria_taxa_legal", []) if m["parcela"] == parcela.numero]
        if not linhas:
            continue
        cabecalho = [p(t, "cabecalho") for t in ["Mês", "Período", "Dias / mês", "Taxa mensal (%)", "Proporcional (%)", "Acumulada (%)", "Juros do trecho", "Juros acumulados"]]
        dados = [cabecalho]
        for m in linhas:
            dados.append([p(m["competencia"], "celula"), p(data_br(m["inicio"]) + " a " + data_br(m["fim"]), "celula"),
                p(f"{m['dias']} / {m['dias_mes']}", "numero"),
                *[p(f"{D(m[k]):.6f}".replace(".", ","), "numero") for k in ("taxa_mensal", "taxa_proporcional", "taxa_acumulada")],
                p(moeda(m["juros_periodo"]), "numero"), p(moeda(m["juros_acumulados"]), "numero")])
        larguras = [largura*f for f in (.075, .225, .085, .12, .13, .12, .12, .125)]
        def tabela(conteudo, tem_cabecalho):
            t = LongTable(conteudo, colWidths=larguras, repeatRows=0, splitInRow=0, hAlign="LEFT")
            regras = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5),
                      ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 5),
                      ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LINEBELOW", (0, 0), (-1, -1), .3, colors.HexColor("#E1DED8"))]
            if tem_cabecalho:
                regras.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7F5F0")))
            t.setStyle(TableStyle(regras))
            return t
        blocos.append(KeepTogether([p(f"Memória da Taxa Legal - parcela {parcela.numero}", "secao"),
            p(f"Base corrigida final: R$ {moeda(parcela.valor_corrigido)}. Taxas simples; data-base excluída; valores em reais. Taxas com seis casas decimais.", "nota"),
            tabela(dados[:2], True)]))
        if len(dados) > 2:
            blocos.append(tabela(dados[2:], False))
    return blocos
