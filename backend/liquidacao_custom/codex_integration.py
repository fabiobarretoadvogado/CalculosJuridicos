"""Instala o plugin pessoal que liga o Codex ao executável local."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


PLUGIN_NAME = "calculos-juridicos"
MARKETPLACE_NAME = "personal"
MARKER_NAME = ".managed-by-calculos-juridicos.json"


def _plugin_source() -> Path:
    return Path(__file__).resolve().parent / "codex_plugin"


def _home(home: Path | None = None) -> Path:
    return (home or Path.home()).resolve()


def _atomic_json(path: Path, dados: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".tmp",
        prefix=f".{path.name}-",
        dir=path.parent,
        delete=False,
    ) as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)
        arquivo.write("\n")
        temporario = Path(arquivo.name)
    temporario.replace(path)


def _copiar_plugin(origem: Path, destino: Path, executavel: Path) -> list[str]:
    if not origem.is_dir():
        raise FileNotFoundError(f"Modelo do plugin não encontrado: {origem}")
    destino.mkdir(parents=True, exist_ok=True)
    gerenciados: list[str] = []
    for fonte in origem.rglob("*"):
        if not fonte.is_file():
            continue
        relativo = fonte.relative_to(origem)
        alvo = destino / relativo
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fonte, alvo)
        gerenciados.append(relativo.as_posix())
    config_mcp = {
        "mcpServers": {
            PLUGIN_NAME: {
                "command": str(executavel.resolve()),
                "args": ["--mcp"],
            }
        }
    }
    _atomic_json(destino / ".mcp.json", config_mcp)
    if ".mcp.json" not in gerenciados:
        gerenciados.append(".mcp.json")
    _atomic_json(
        destino / MARKER_NAME,
        {
            "plugin": PLUGIN_NAME,
            "executavel": str(executavel.resolve()),
            "arquivos": sorted(gerenciados),
        },
    )
    return sorted(gerenciados)


def _marketplace(home: Path) -> Path:
    return home / ".agents" / "plugins" / "marketplace.json"


def _registrar_marketplace(path: Path) -> str:
    if path.is_file():
        try:
            catalogo = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"O catálogo pessoal de plugins não é um JSON válido: {path}") from exc
    else:
        catalogo = {
            "name": MARKETPLACE_NAME,
            "interface": {"displayName": "Personal"},
            "plugins": [],
        }
    nome_marketplace = str(catalogo.get("name") or MARKETPLACE_NAME)
    catalogo.setdefault("name", nome_marketplace)
    catalogo.setdefault("interface", {"displayName": "Personal"})
    plugins = catalogo.setdefault("plugins", [])
    if not isinstance(plugins, list):
        raise ValueError(f"O campo 'plugins' do catálogo pessoal é inválido: {path}")
    entrada = {
        "name": PLUGIN_NAME,
        "source": {"source": "local", "path": f"./plugins/{PLUGIN_NAME}"},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Productivity",
    }
    indice = next(
        (
            i
            for i, item in enumerate(plugins)
            if isinstance(item, dict) and item.get("name") == PLUGIN_NAME
        ),
        None,
    )
    if indice is None:
        plugins.append(entrada)
    else:
        plugins[indice] = entrada
    _atomic_json(path, catalogo)
    return nome_marketplace


def _localizar_codex() -> Path | None:
    encontrado = shutil.which("codex")
    if encontrado:
        return Path(encontrado)
    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    pasta = local_app_data / "OpenAI" / "Codex" / "bin"
    candidatos = list(pasta.glob("*/codex.exe")) if pasta.is_dir() else []
    return max(candidatos, key=lambda item: item.stat().st_mtime) if candidatos else None


def _executar_codex(codex: Path, argumentos: list[str]) -> subprocess.CompletedProcess[str]:
    kwargs: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": 60,
        "check": False,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run([str(codex), *argumentos], **kwargs)


def install_codex_plugin(
    executable: Path | None = None,
    *,
    home: Path | None = None,
    activate: bool = True,
) -> dict[str, Any]:
    base = _home(home)
    executavel = (executable or Path(sys.executable)).resolve()
    destino = base / "plugins" / PLUGIN_NAME
    arquivos = _copiar_plugin(_plugin_source(), destino, executavel)
    catalogo = _marketplace(base)
    nome_marketplace = _registrar_marketplace(catalogo)
    resultado: dict[str, Any] = {
        "sucesso": True,
        "plugin": PLUGIN_NAME,
        "pasta": str(destino),
        "marketplace": str(catalogo),
        "marketplace_nome": nome_marketplace,
        "executavel": str(executavel),
        "arquivos": arquivos,
        "ativado": False,
        "reinicio_codex_necessario": True,
    }
    if not activate:
        return resultado
    codex = _localizar_codex()
    if codex is None:
        resultado["aviso"] = "Codex não localizado. O plugin está disponível no catálogo pessoal para instalação posterior."
        return resultado
    # Em uma máquina nova, criar marketplace.json não basta: a raiz local
    # precisa ser conhecida pelo CLI. A operação repetida é inofensiva.
    _executar_codex(codex, ["plugin", "marketplace", "add", str(base), "--json"])
    seletor = f"{PLUGIN_NAME}@{nome_marketplace}"
    instalacao = _executar_codex(codex, ["plugin", "add", seletor, "--json"])
    if instalacao.returncode != 0:
        # Uma versão anterior instalada pode manter cache. Remover e adicionar
        # novamente é seguro porque a fonte pessoal acabou de ser atualizada.
        _executar_codex(codex, ["plugin", "remove", seletor, "--json"])
        instalacao = _executar_codex(codex, ["plugin", "add", seletor, "--json"])
    resultado["ativado"] = instalacao.returncode == 0
    if instalacao.returncode != 0:
        resultado["aviso"] = (
            instalacao.stderr.strip()
            or instalacao.stdout.strip()
            or "Não foi possível ativar o plugin automaticamente."
        )
    return resultado


def uninstall_codex_plugin(
    *,
    home: Path | None = None,
    deactivate: bool = True,
) -> dict[str, Any]:
    base = _home(home)
    destino = base / "plugins" / PLUGIN_NAME
    catalogo = _marketplace(base)
    marketplace_nome = MARKETPLACE_NAME
    if catalogo.is_file():
        try:
            dados = json.loads(catalogo.read_text(encoding="utf-8"))
            marketplace_nome = str(dados.get("name") or MARKETPLACE_NAME)
            plugins = dados.get("plugins", [])
            if isinstance(plugins, list):
                dados["plugins"] = [
                    item
                    for item in plugins
                    if not (isinstance(item, dict) and item.get("name") == PLUGIN_NAME)
                ]
                _atomic_json(catalogo, dados)
        except (OSError, json.JSONDecodeError):
            pass
    desativado = False
    if deactivate:
        codex = _localizar_codex()
        if codex is not None:
            seletor = f"{PLUGIN_NAME}@{marketplace_nome}"
            processo = _executar_codex(codex, ["plugin", "remove", seletor, "--json"])
            desativado = processo.returncode == 0
    marker = destino / MARKER_NAME
    removido = False
    if marker.is_file():
        try:
            gerenciados = json.loads(marker.read_text(encoding="utf-8")).get("arquivos", [])
        except (OSError, json.JSONDecodeError):
            gerenciados = []
        for relativo in gerenciados:
            alvo = (destino / relativo).resolve()
            try:
                alvo.relative_to(destino.resolve())
            except ValueError:
                continue
            if alvo.is_file():
                alvo.unlink()
                removido = True
        marker.unlink(missing_ok=True)
        for pasta in sorted((item for item in destino.rglob("*") if item.is_dir()), reverse=True):
            try:
                pasta.rmdir()
            except OSError:
                pass
        try:
            destino.rmdir()
        except OSError:
            pass
    return {
        "sucesso": True,
        "plugin": PLUGIN_NAME,
        "desativado": desativado,
        "arquivos_removidos": removido,
    }
