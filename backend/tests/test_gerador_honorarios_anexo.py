import importlib.util
import io
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "exports" / "gerar_honorarios_anexo_ipca.py"


def carregar_gerador():
    spec = importlib.util.spec_from_file_location("gerar_honorarios_anexo_ipca", SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_caso_do_anexo_delega_layout_ao_exportador_oficial():
    fonte = SCRIPT.read_text(encoding="utf-8")
    assert "reportlab" not in fonte
    assert "exportar_pdf_honorarios" in fonte

    reader = PdfReader(io.BytesIO(carregar_gerador().gerar()))
    texto = "\n".join(pagina.extract_text() for pagina in reader.pages)

    assert len(reader.pages) == 1
    assert reader.metadata.title == "Demonstrativo de cálculo"
    assert reader.metadata.author == "Barreto Fontes Sociedade de Advogados"
    assert "Relatório de honorários sucumbenciais" in texto
    assert "Valor da causa no protocolo" in texto
    assert "27/11/2024 a 31/08/2026" in texto
    assert texto.count("1,08117790") == 1
    assert "Fator acumulado do período" in texto
    assert "Fator do mês" not in texto
    assert "Memória da correção" not in texto
    assert "R$ 53.516,27" in texto
    assert "R$ 5.351,63" in texto
    assert "202601150833" in texto
