import pytest


@pytest.fixture(autouse=True)
def dados_locais_isolados(monkeypatch, tmp_path):
    """Impede que testes da API gravem cálculos no perfil real do Windows."""
    monkeypatch.setenv("CALCULOS_JURIDICOS_DATA_DIR", str(tmp_path / "dados-aplicativo"))
