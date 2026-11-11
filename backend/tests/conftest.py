import pytest


@pytest.fixture
def valores_do_resumo():
    import importlib.util
    from pathlib import Path

    caminho = Path(__file__).with_name("pdf_geometry.py")
    spec = importlib.util.spec_from_file_location("release_pdf_geometry", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.valores_do_resumo


@pytest.fixture(autouse=True)
def dados_locais_isolados(monkeypatch, tmp_path):
    """Impede que testes da API gravem cálculos no perfil real do Windows."""
    monkeypatch.setenv("CALCULOS_JURIDICOS_DATA_DIR", str(tmp_path / "dados-aplicativo"))
