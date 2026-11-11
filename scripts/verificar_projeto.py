"""Confere documentação, versões e o ambiente usado para preparar releases."""
from __future__ import annotations

import argparse
import ast
import importlib.metadata
import json
import re
import struct
import subprocess
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
LOCK_ENTRY = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;]+)$")


def normalizar_nome(nome: str) -> str:
    return re.sub(r"[-_.]+", "-", nome).lower()


def links_locais(documento: Path) -> list[Path]:
    """Retorna destinos de Markdown, ignorando exemplos em cercas de código."""
    resultados = []
    cerca = None
    for linha in documento.read_text(encoding="utf-8-sig").splitlines():
        abre = re.match(r"^\s*(`{3,}|~{3,})", linha)
        if abre:
            marca = abre.group(1)
            if cerca is None:
                cerca = marca
            elif marca[0] == cerca[0] and len(marca) >= len(cerca):
                cerca = None
            continue
        if cerca is not None:
            continue
        for link in LINK.findall(linha):
            texto = link.strip()
            destino = texto[1:texto.index(">")] if texto.startswith("<") and ">" in texto else texto.split(maxsplit=1)[0]
            partes = urlsplit(destino)
            if partes.scheme or partes.netloc or not partes.path:
                continue
            resultados.append((documento.parent / unquote(partes.path)).resolve())
    return resultados


def verificar_documentos(root: Path) -> list[str]:
    documentos = [root / "README.md", root / "backend" / "README.md"]
    documentos.extend(sorted((root / "docs").rglob("*.md")))
    erros = []
    for documento in documentos:
        if not documento.is_file():
            erros.append(f"Documento ausente: {documento.relative_to(root)}")
            continue
        for destino in links_locais(documento):
            if not destino.is_relative_to(root.resolve()) or not destino.exists():
                erros.append(f"Link local ausente: {documento.relative_to(root)} -> {destino}")
    return erros


def identidade(root: Path) -> dict[str, str]:
    arquivo = root / "backend/liquidacao_custom/metadata.py"
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    return {node.targets[0].id: node.value.value for node in arvore.body
            if isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)}


def verificar_versoes(root: Path) -> list[str]:
    erros = []
    info = identidade(root)
    tecnica, edicao = info.get("APP_VERSION", ""), info.get("APP_DISPLAY_VERSION", "")
    if not re.fullmatch(r"\d+\.\d{2}", edicao):
        erros.append("Edição inválida em metadata.py.")
    if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", tecnica) or any(
        int(parte) > 65535 for parte in tecnica.split(".") if parte.isdigit()
    ):
        erros.append("Versão técnica inválida em metadata.py.")
    esperado = ".".join(str(int(parte)) for parte in edicao.split(".")) + ".0" if re.fullmatch(r"\d+\.\d{2}", edicao) else ""
    projeto = tomllib.loads((root / "backend/pyproject.toml").read_text(encoding="utf-8"))
    frontend = json.loads((root / "frontend/package.json").read_text(encoding="utf-8"))
    lock = json.loads((root / "frontend/package-lock.json").read_text(encoding="utf-8"))
    raiz_lock = lock.get("packages", {}).get("", {})
    if projeto["project"]["version"] != esperado:
        erros.append("A versão do pacote Python difere da edição do aplicativo.")
    if projeto["project"]["requires-python"] != ">=3.11":
        erros.append("A versão mínima de Python deve refletir o suporte declarado: >=3.11.")
    if frontend.get("version") != esperado or lock.get("version") != esperado or raiz_lock.get("version") != esperado:
        erros.append("As versões do frontend e do package-lock diferem da edição do aplicativo.")
    for campo in ("dependencies", "devDependencies"):
        if frontend.get(campo, {}) != raiz_lock.get(campo, {}):
            erros.append(f"{campo} no package-lock não corresponde ao package.json.")
    sys.path.insert(0, str(root / "backend"))
    from liquidacao_custom.index_data.store import FILES

    if not re.search(rf"\b{len(FILES)} arquivos\b", (root / "README.md").read_text(encoding="utf-8-sig")):
        erros.append("A quantidade de arquivos da base canônica no README está desatualizada.")
    return erros


def ler_lock(arquivo: Path) -> dict[str, str]:
    resultado = {}
    for numero, linha in enumerate(arquivo.read_text(encoding="utf-8-sig").splitlines(), 1):
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        item = LOCK_ENTRY.fullmatch(linha)
        if not item:
            raise ValueError(f"Entrada inválida no lock, linha {numero}.")
        nome, versao = normalizar_nome(item.group(1)), item.group(2)
        if nome in resultado:
            raise ValueError(f"Dependência repetida no lock: {nome}.")
        resultado[nome] = versao
    if not resultado:
        raise ValueError("O lock de dependências está vazio.")
    return resultado


def verificar_dependencias_frontend(root: Path) -> list[str]:
    erros = []
    frontend = json.loads((root / "frontend/package.json").read_text(encoding="utf-8"))
    npm_lock = json.loads((root / "frontend/package-lock.json").read_text(encoding="utf-8"))
    for nome in {**frontend.get("dependencies", {}), **frontend.get("devDependencies", {})}:
        registro = npm_lock.get("packages", {}).get("node_modules/" + nome, {})
        pacote = root / "frontend/node_modules" / nome / "package.json"
        if not pacote.is_file():
            erros.append(f"Dependência do frontend ausente: {nome}. Execute npm ci.")
            continue
        atual = json.loads(pacote.read_text(encoding="utf-8"))["version"]
        if atual != registro.get("version"):
            erros.append(f"Dependência do frontend {nome}: esperada {registro.get('version')}; encontrada {atual}.")
    return erros


def verificar_ambiente(root: Path) -> list[str]:
    erros = []
    if sys.platform != "win32" or struct.calcsize("P") != 8 or sys.version_info[:3] != (3, 13, 13):
        erros.append("A compilação reproduzível requer Windows x64 e Python 3.13.13.")
    lock = ler_lock(root / "backend/requirements-build-win-py313.lock")
    instalados: dict[str, set[str]] = {}
    for dist in importlib.metadata.distributions():
        nome = dist.metadata.get("Name")
        if nome:
            instalados.setdefault(normalizar_nome(nome), set()).add(dist.version)
    for nome, esperado in lock.items():
        if instalados.get(nome) != {esperado}:
            erros.append(f"Dependência {nome}: esperado {esperado}; encontrado {sorted(instalados.get(nome, set()))}.")
    resultado = subprocess.run([sys.executable, "-m", "pip", "check"], capture_output=True, text=True)
    if resultado.returncode:
        erros.append("pip check encontrou dependências incompatíveis: " + resultado.stdout.strip())
    esperado_node = (root / ".nvmrc").read_text(encoding="ascii").strip()
    try:
        node = subprocess.run(["node", "--version"], capture_output=True, text=True, check=True).stdout.strip().removeprefix("v")
        if node != esperado_node:
            erros.append(f"Node.js: esperado {esperado_node}; encontrado {node}.")
    except (OSError, subprocess.CalledProcessError):
        erros.append("Node.js não foi encontrado.")
    erros.extend(verificar_dependencias_frontend(root))
    return erros


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ambiente", action="store_true", help="Confere também o ambiente fixado de compilação.")
    args = parser.parse_args()
    erros = verificar_documentos(ROOT) + verificar_versoes(ROOT)
    if args.ambiente:
        erros += verificar_ambiente(ROOT)
    if erros:
        for erro in erros:
            print("ERRO:", erro, file=sys.stderr)
        return 1
    print("Documentação e versões conferidas." + (" Ambiente de compilação conferido." if args.ambiente else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
