import json
from pathlib import Path
from subprocess import CompletedProcess

import liquidacao_custom.codex_integration as integracao
from liquidacao_custom.codex_integration import (
    PLUGIN_NAME,
    install_codex_plugin,
    uninstall_codex_plugin,
)


def test_instala_plugin_pessoal_sem_apagar_catalogo(tmp_path):
    catalogo = tmp_path / ".agents" / "plugins" / "marketplace.json"
    catalogo.parent.mkdir(parents=True)
    catalogo.write_text(
        json.dumps(
            {
                "name": "personal",
                "interface": {"displayName": "Meus plugins"},
                "plugins": [
                    {
                        "name": "outro-plugin",
                        "source": {"source": "local", "path": "./plugins/outro-plugin"},
                        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                        "category": "Productivity",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    executavel = tmp_path / "Aplicativo" / "CalculosJuridicos.exe"
    executavel.parent.mkdir()
    executavel.touch()

    resultado = install_codex_plugin(executavel, home=tmp_path, activate=False)

    assert resultado["sucesso"] is True
    destino = tmp_path / "plugins" / PLUGIN_NAME
    config = json.loads((destino / ".mcp.json").read_text(encoding="utf-8"))
    assert config["mcpServers"][PLUGIN_NAME]["command"] == str(executavel.resolve())
    assert config["mcpServers"][PLUGIN_NAME]["args"] == ["--mcp"]
    dados = json.loads(catalogo.read_text(encoding="utf-8"))
    assert [item["name"] for item in dados["plugins"]] == ["outro-plugin", PLUGIN_NAME]
    assert (destino / "skills" / PLUGIN_NAME / "SKILL.md").is_file()


def test_desinstala_somente_arquivos_gerenciados(tmp_path):
    executavel = tmp_path / "CalculosJuridicos.exe"
    executavel.touch()
    install_codex_plugin(executavel, home=tmp_path, activate=False)
    destino = tmp_path / "plugins" / PLUGIN_NAME
    arquivo_usuario = destino / "minhas-anotacoes.txt"
    arquivo_usuario.write_text("preservar", encoding="utf-8")

    resultado = uninstall_codex_plugin(home=tmp_path, deactivate=False)

    assert resultado["arquivos_removidos"] is True
    assert arquivo_usuario.read_text(encoding="utf-8") == "preservar"
    catalogo = json.loads(
        (tmp_path / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8")
    )
    assert all(item.get("name") != PLUGIN_NAME for item in catalogo["plugins"])


def test_ativacao_registra_marketplace_antes_do_plugin(tmp_path, monkeypatch):
    executavel = tmp_path / "CalculosJuridicos.exe"
    codex = tmp_path / "codex.exe"
    executavel.touch()
    codex.touch()
    chamadas = []

    monkeypatch.setattr(integracao, "_localizar_codex", lambda: codex)

    def executar(_codex, argumentos):
        chamadas.append(argumentos)
        return CompletedProcess([str(_codex), *argumentos], 0, "{}", "")

    monkeypatch.setattr(integracao, "_executar_codex", executar)
    resultado = install_codex_plugin(executavel, home=tmp_path, activate=True)

    assert resultado["ativado"] is True
    assert chamadas[0] == ["plugin", "marketplace", "add", str(tmp_path.resolve()), "--json"]
    assert chamadas[1] == ["plugin", "add", f"{PLUGIN_NAME}@personal", "--json"]
