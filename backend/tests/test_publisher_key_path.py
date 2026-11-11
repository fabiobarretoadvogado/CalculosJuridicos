import importlib.util
import json
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    "publisher_key_path_test", Path(__file__).resolve().parents[2] / "scripts/publisher.py"
)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


def test_configuracao_prepara_versoes_dos_pacotes_sem_alterar_dependencias(tmp_path):
    (tmp_path / "backend").mkdir()
    (tmp_path / "frontend").mkdir()
    pyproject = tmp_path / "backend/pyproject.toml"
    pyproject.write_text('[project]\nname = "exemplo"\nversion = "1.23.0"\n', encoding="utf-8")
    pacote = tmp_path / "frontend/package.json"
    lock = tmp_path / "frontend/package-lock.json"
    pacote.write_text(json.dumps({"version": "1.23.0", "dependencies": {"x": "^1"}}), encoding="utf-8")
    lock.write_text(json.dumps({"version": "1.23.0", "packages": {"": {"version": "1.23.0"}}}), encoding="utf-8")
    updates = publisher.package_version_updates(tmp_path, "1.24")
    assert 'version = "1.24.0"' in updates[pyproject]
    assert json.loads(updates[pacote]) == {"version": "1.24.0", "dependencies": {"x": "^1"}}
    assert json.loads(updates[lock])["packages"][""]["version"] == "1.24.0"
    assert '1.23.0' in pyproject.read_text(encoding="utf-8")


def test_chave_existente_tem_prioridade_na_pasta_configurada(tmp_path, monkeypatch):
    configured = tmp_path / "configurada"
    profile = tmp_path / "perfil"
    relative = Path("CalculosJuridicos-Publisher/update-signing-key.json")
    for key in (configured / relative, profile / "AppData/Local" / relative):
        key.parent.mkdir(parents=True)
        key.write_text("teste", encoding="utf-8")
    monkeypatch.setenv("LOCALAPPDATA", str(configured))
    monkeypatch.setenv("USERPROFILE", str(profile))
    assert publisher.key_path() == configured / relative


def test_reutiliza_chave_do_perfil_quando_pasta_virtualizada_esta_vazia(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "virtualizada"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "perfil"))
    original = tmp_path / "perfil/AppData/Local/CalculosJuridicos-Publisher/update-signing-key.json"
    original.parent.mkdir(parents=True)
    original.write_text("teste", encoding="utf-8")
    assert publisher.key_path() == original
    assert not (tmp_path / "virtualizada").exists()


def test_ausencia_de_chave_nao_cria_arquivos_nem_troca_destino(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "configurada"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "perfil"))
    assert publisher.key_path() == tmp_path / "configurada/CalculosJuridicos-Publisher/update-signing-key.json"
    assert not (tmp_path / "configurada").exists()
    assert not (tmp_path / "perfil").exists()


def test_reutiliza_chave_virtualizada_pelo_codex_no_terminal_externo(tmp_path, monkeypatch):
    profile = tmp_path / "perfil"
    configured = profile / "AppData/Local"
    monkeypatch.setenv("LOCALAPPDATA", str(configured))
    monkeypatch.setenv("USERPROFILE", str(profile))
    original = configured / "Packages/OpenAI.Codex_teste/LocalCache/Local/CalculosJuridicos-Publisher/update-signing-key.json"
    original.parent.mkdir(parents=True)
    original.write_text("teste", encoding="utf-8")
    assert publisher.key_path() == original
    assert not (configured / "CalculosJuridicos-Publisher").exists()


def test_multiplas_chaves_do_codex_nao_sao_escolhidas_automaticamente(tmp_path, monkeypatch):
    import pytest

    profile = tmp_path / "perfil"
    configured = profile / "AppData/Local"
    monkeypatch.setenv("LOCALAPPDATA", str(configured))
    monkeypatch.setenv("USERPROFILE", str(profile))
    for package in ("OpenAI.Codex_a", "OpenAI.Codex_b"):
        key = configured / "Packages" / package / "LocalCache/Local/CalculosJuridicos-Publisher/update-signing-key.json"
        key.parent.mkdir(parents=True)
        key.write_text("teste", encoding="utf-8")
    with pytest.raises(ValueError, match="mais de uma chave"):
        publisher.key_path()
