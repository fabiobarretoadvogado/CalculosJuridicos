import importlib.util
import json
import shutil
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("verificar_projeto", ROOT / "scripts/verificar_projeto.py")
verificador = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(verificador)


def test_links_locais_ignoram_exemplos_e_reconhecem_caminho_com_espacos(tmp_path):
    documento = tmp_path / "guia.md"
    documento.write_text(
        "[Documento](<arquivo com espacos.md>)\n"
        "[Fonte](https://example.com)\n"
        "```markdown\n[Exemplo](nao-existe.md)\n```\n",
        encoding="utf-8",
    )
    assert verificador.links_locais(documento) == [tmp_path / "arquivo com espacos.md"]


def test_documentacao_rejeita_link_local_ausente(tmp_path):
    (tmp_path / "backend").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "backend/README.md").write_text("Backend", encoding="utf-8")
    (tmp_path / "README.md").write_text("[Evidência](docs/ausente.md)", encoding="utf-8")
    assert any("ausente.md" in erro for erro in verificador.verificar_documentos(tmp_path))


def test_versoes_do_projeto_publicado_estao_coerentes():
    assert verificador.verificar_versoes(ROOT) == []


def test_detecta_versao_inconsistente_do_frontend(tmp_path):
    for nome in ("backend/liquidacao_custom/metadata.py", "backend/pyproject.toml",
                 "frontend/package.json", "frontend/package-lock.json", "README.md"):
        destino = tmp_path / nome
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / nome, destino)
    pacote = tmp_path / "frontend/package.json"
    dados = json.loads(pacote.read_text(encoding="utf-8"))
    dados["version"] = "9.99.0"
    pacote.write_text(json.dumps(dados), encoding="utf-8")
    assert any("versões do frontend" in erro for erro in verificador.verificar_versoes(tmp_path))


def test_lock_rejeita_dependencia_repetida(tmp_path):
    lock = tmp_path / "dependencias.lock"
    lock.write_text("exemplo-pacote==1.0\nexemplo_pacote==1.0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="repetida"):
        verificador.ler_lock(lock)


def test_dependencia_frontend_deve_corresponder_ao_lock(tmp_path):
    frontend = tmp_path / "frontend"
    pacote = frontend / "node_modules/exemplo/package.json"
    pacote.parent.mkdir(parents=True)
    (frontend / "package.json").write_text(json.dumps({"dependencies": {"exemplo": "^1.0.0"}}), encoding="utf-8")
    (frontend / "package-lock.json").write_text(json.dumps({"packages": {"node_modules/exemplo": {"version": "1.2.0"}}}), encoding="utf-8")
    pacote.write_text(json.dumps({"version": "1.3.0"}), encoding="utf-8")
    assert any("esperada 1.2.0" in erro for erro in verificador.verificar_dependencias_frontend(tmp_path))
    pacote.write_text(json.dumps({"version": "1.2.0"}), encoding="utf-8")
    assert verificador.verificar_dependencias_frontend(tmp_path) == []
