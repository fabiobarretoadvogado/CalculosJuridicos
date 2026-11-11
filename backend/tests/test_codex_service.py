import asyncio
import json
from pathlib import Path
import tomllib

import pytest

from liquidacao_custom.codex_service import manage
from liquidacao_custom.codex_service.manage import (
    configure_codex,
    prepare_shared_service,
    remove_shared_service,
    service_root,
    table_fields,
)
from liquidacao_custom.codex_service.shared_host import LocalAuthentication


def executable_in(directory):
    executable = directory / "Aplicativo" / "CalculosJuridicos.exe"
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.touch()
    return executable


def test_atualizacao_preserva_chave_porta_e_configuracoes_alheias(tmp_path):
    executable = executable_in(tmp_path)
    configuration = tmp_path / ".codex/config.toml"
    configuration.parent.mkdir()
    configuration.write_text('model = "manter"\n[mcp_servers.outro.env]\nVALOR = "original"\n', encoding="utf-8")
    first = prepare_shared_service(executable, home=tmp_path, install_runtime=False)
    configure_codex(first, home=tmp_path)
    settings_path = service_root(tmp_path) / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    settings["port"] = 49201
    settings_path.write_text(json.dumps(settings), encoding="utf-8")
    second = prepare_shared_service(executable, home=tmp_path, install_runtime=False)
    configure_codex(second, home=tmp_path)
    parsed = tomllib.loads(configuration.read_text(encoding="utf-8"))
    assert second["headers"] == first["headers"]
    assert second["url"] == "http://127.0.0.1:49201/mcp"
    assert parsed["model"] == "manter"
    assert parsed["mcp_servers"]["outro"]["env"] == {"VALOR": "original"}
    assert parsed["mcp_servers"]["calculos-juridicos"]["url"] == second["url"]
    assert parsed["plugins"]["calculos-juridicos@personal"]["mcp_servers"]["calculos-juridicos"]["enabled"] is False


def test_migracao_substitui_stdio_multilinha_preservando_politicas(tmp_path):
    executable = executable_in(tmp_path)
    configuration = tmp_path / ".codex/config.toml"
    configuration.parent.mkdir()
    configuration.write_text(
        '[plugins."calculos-juridicos@personal"]\nenabled = true\n'
        '[mcp_servers.calculos-juridicos]\ncommand = "legacy.exe"\n'
        'args = [\n "--mcp",\n]\ndisabled_tools = ["ferramenta_bloqueada"]\n'
        '[mcp_servers.calculos-juridicos.env]\nLEGACY = "valor"\n',
        encoding="utf-8",
    )
    descriptor = prepare_shared_service(executable, home=tmp_path, install_runtime=False)
    configure_codex(descriptor, home=tmp_path)
    configure_codex(descriptor, home=tmp_path)
    parsed = tomllib.loads(configuration.read_text(encoding="utf-8"))
    server = parsed["mcp_servers"]["calculos-juridicos"]
    assert server["url"] == descriptor["url"]
    assert "command" not in server
    assert "args" not in server
    assert "env" not in server
    assert server["disabled_tools"] == ["ferramenta_bloqueada"]
    assert parsed["plugins"]["calculos-juridicos@personal"]["enabled"] is True


def test_desinstalacao_preserva_dados_e_servidores_alheios(tmp_path):
    descriptor = prepare_shared_service(executable_in(tmp_path), home=tmp_path, install_runtime=False)
    configure_codex(descriptor, home=tmp_path)
    configuration = tmp_path / ".codex/config.toml"
    with configuration.open("a", encoding="utf-8") as output:
        output.write('\n[mcp_servers.outro]\nurl = "http://127.0.0.1:49001/mcp"\n')
    annotation = service_root(tmp_path) / "minhas-notas.txt"
    annotation.write_text("preservar", encoding="utf-8")
    saved = tmp_path / "dados/CJ1-preservar.db"
    saved.parent.mkdir()
    saved.write_bytes(b"calculos-do-usuario")
    remove_shared_service(home=tmp_path, stop=False)
    parsed = tomllib.loads(configuration.read_text(encoding="utf-8"))
    assert "calculos-juridicos" not in parsed["mcp_servers"]
    assert "outro" in parsed["mcp_servers"]
    assert saved.read_bytes() == b"calculos-do-usuario"
    assert annotation.read_text(encoding="utf-8") == "preservar"


def test_desinstalacao_nao_remove_conexao_editada_pelo_usuario(tmp_path):
    descriptor = prepare_shared_service(executable_in(tmp_path), home=tmp_path, install_runtime=False)
    configure_codex(descriptor, home=tmp_path)
    configuration = tmp_path / ".codex/config.toml"
    content = configuration.read_text(encoding="utf-8").replace(descriptor["url"], "https://servidor-do-usuario.example/mcp")
    configuration.write_text(content, encoding="utf-8")
    remove_shared_service(home=tmp_path, stop=False)
    parsed = tomllib.loads(configuration.read_text(encoding="utf-8"))
    assert parsed["mcp_servers"]["calculos-juridicos"]["url"] == "https://servidor-do-usuario.example/mcp"


def test_configuracao_repetida_preserva_politicas_existentes():
    original = '[mcp_servers."calculos-juridicos"]\nurl = "antiga"\ntool_timeout_sec = 90\n[mcp_servers.outro]\nenabled = true\n'
    changed = table_fields(original, '[mcp_servers."calculos-juridicos"]', {"url": '"http://127.0.0.1:49179/mcp"'})
    parsed = tomllib.loads(changed)
    assert parsed["mcp_servers"]["calculos-juridicos"]["tool_timeout_sec"] == 90
    assert parsed["mcp_servers"]["outro"]["enabled"] is True


def test_http_sem_chave_nao_alcanca_motor():
    messages = []

    async def child(scope, receive, send):
        raise AssertionError("O motor não pode receber uma chamada sem autenticação")

    async def receive():
        return {"type": "http.request"}

    async def send(message):
        messages.append(message)

    application = LocalAuthentication(child, "chave-de-teste", "teste")
    asyncio.run(application({"type": "http", "path": "/mcp", "headers": []}, receive, send))
    assert messages[0]["status"] == 401


def test_preparacao_recusa_pacote_sem_runtime(tmp_path):
    with pytest.raises(FileNotFoundError, match="ambiente do serviço"):
        prepare_shared_service(executable_in(tmp_path), home=tmp_path, install_runtime=True)


def test_preparacao_instala_e_atualiza_runtime_preservando_chave(tmp_path, monkeypatch):
    executable = executable_in(tmp_path)
    packaged = executable.parent / "codex-service"
    packaged.mkdir()
    for filename in manage.SERVICE_FILES:
        (packaged / filename).write_bytes((Path(manage.__file__).parent / filename).read_bytes())
    runtime = packaged / "runtime"
    runtime.mkdir()
    (runtime / "pythonw.exe").write_bytes(b"primeiro-runtime")
    marker = runtime / "ready.json"
    marker.write_text('"primeiro"', encoding="utf-8")
    stops = []
    monkeypatch.setattr(manage, "stop_shared_service", lambda *args, **kwargs: stops.append(True))
    first = prepare_shared_service(executable, home=tmp_path)
    installed = service_root(tmp_path) / "runtime"
    unchanged = installed / "preservar-se-nao-houver-atualizacao.txt"
    unchanged.touch()
    repeated = prepare_shared_service(executable, home=tmp_path)
    assert unchanged.exists()
    marker.write_text('"segundo"', encoding="utf-8")
    (runtime / "pythonw.exe").write_bytes(b"segundo-runtime")
    updated = prepare_shared_service(executable, home=tmp_path)
    assert (installed / "pythonw.exe").read_bytes() == b"segundo-runtime"
    assert not unchanged.exists()
    assert first["headers"] == repeated["headers"] == updated["headers"]
    assert len(stops) == 3
