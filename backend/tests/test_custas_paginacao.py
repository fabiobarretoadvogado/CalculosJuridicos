"""Paginação das custas: intervalo real, início completo e total com última linha."""
import io
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pypdf import PdfReader
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Table, TableStyle
from liquidacao_custom.core.relatorio_layout import criar_documento, criar_estilos, criar_rodape, custas_despesas, texto


@pytest.mark.parametrize("altura_anterior,quantidade", [(160, 1), (440, 1), (160, 40)])
def test_custas_intervalo_paginacao_e_total(altura_anterior, quantidade):
    buffer = io.BytesIO()
    doc = criar_documento(buffer, "Teste das custas")
    estilos = criar_estilos()
    def p(t, estilo="normal"):
        return Paragraph(texto(t), estilos[estilo])
    anterior = Table([[p("OPERAÇÃO ANTERIOR")]], colWidths=[doc.width], rowHeights=[altura_anterior])
    anterior.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), "#F7F5F0")]))
    itens = [SimpleNamespace(numero=n, nome=f"Custa {n:03d}", data=date(2026, 1, 1),
        valor_original=Decimal("100"), fator_ipcae=Decimal("1.03"),
        correcao_monetaria=Decimal("3"), valor_atualizado=Decimal("103")) for n in range(1, quantidade + 1)]
    rodape = criar_rodape("Data-base", "2026-08-31")
    doc.build([anterior, *custas_despesas(itens, doc.width, p, doc.height)], onFirstPage=rodape, onLaterPages=rodape)
    reader = PdfReader(io.BytesIO(buffer.getvalue()))
    paginas = [page.extract_text() for page in reader.pages]
    i = next(i for i, t in enumerate(paginas) if "CUSTAS E DESPESAS PROCESSUAIS" in t)
    assert "Custa 001" in paginas[i] and "Fator IPCA-E" in paginas[i]
    posicoes = []
    reader.pages[i].extract_text(visitor_text=lambda t, matriz, tm, fonte, sz:
        posicoes.append((t.strip(), matriz[1] * tm[4] + matriz[3] * tm[5] + matriz[5])))
    titulo = next(y for t, y in posicoes if t == "CUSTAS E DESPESAS PROCESSUAIS")
    if altura_anterior == 440:
        assert i == 1
        assert titulo > float(reader.pages[i].mediabox.height) - 65
    else:
        assert i == 0
        retangulos = []
        def registrar(operador, args, matriz, tm):
            if operador == b"re":
                retangulos.append(matriz[5] + min(float(args[1]), float(args[1] + args[3])))
        reader.pages[i].extract_text(visitor_operand_before=registrar)
        fim_anterior = min(y for y in retangulos if y > titulo)
        assert fim_anterior - (titulo + 10) == pytest.approx(1.5 * cm, abs=.001)
    assert sum(t.count("Fator IPCA-E") for t in paginas) == 1
    for n in range(1, quantidade + 1):
        assert sum(t.count(f"Custa {n:03d}") for t in paginas) == 1
    ultima = next(t for t in paginas if f"Custa {quantidade:03d}" in t)
    assert "TOTAL" in ultima
    for n, t in enumerate(paginas, 1):
        assert f"Página {n}" in t
