"""Posições dos valores no resumo, incluindo o deslocamento de alinhamento Td."""
from reportlab.pdfbase.pdfmetrics import stringWidth
from numbers import Number


def valores_do_resumo(pagina):
    valores = []
    estado = {"fonte": "Helvetica", "tamanho": 0, "resumo": True}
    fontes = pagina["/Resources"]["/Font"]

    def visitar(operador, argumentos, cm, tm):
        if operador == b"Tf":
            estado["fonte"] = str(fontes[argumentos[0]].get_object()["/BaseFont"]).lstrip("/")
            estado["tamanho"] = float(argumentos[1])
        if operador not in (b"Tj", b"TJ"):
            return
        partes = list(argumentos[0]) if operador == b"TJ" else [argumentos[0]]
        texto = "".join(parte.decode("cp1252") if isinstance(parte, bytes) else str(parte)
                        for parte in partes if not isinstance(parte, Number)).strip().replace("\xa0", " ")
        if texto in ("DADOS DO PROCESSO", "CRÉDITO - ACRÉSCIMO"):
            estado["resumo"] = False
        if estado["resumo"] and texto.startswith("R$ "):
            x = cm[0] * tm[4] + cm[2] * tm[5] + cm[4]
            y = cm[1] * tm[4] + cm[3] * tm[5] + cm[5]
            tamanho = estado["tamanho"]
            ajuste = -sum(float(parte) for parte in partes if isinstance(parte, Number)) * tamanho / 1000
            valores.append((texto, x, y, stringWidth(texto, estado["fonte"], tamanho) + ajuste, tamanho))

    # visitor_text pode retornar a matriz já restaurada após o Td do parágrafo.
    # Medir no Tj conserva o deslocamento real aplicado ao valor alinhado à direita.
    pagina.extract_text(visitor_operand_before=visitar)
    return valores
