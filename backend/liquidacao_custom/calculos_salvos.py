"""Persistência local e protegida dos cálculos que podem ser reabertos pela chave do PDF."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from .metadata import APP_VERSION
from .updates.protected import protect


SCHEMA_VERSION = 1
CategoriaCalculo = Literal[
    "calculo_principal",
    "honorarios_sucumbenciais_proveito_economico",
    "honorarios_sucumbenciais_isolados",
]


class CalculoRecuperado(BaseModel):
    chave_recuperacao: str
    categoria: CategoriaCalculo
    schema_version: int
    versao_aplicativo: str
    criado_em: datetime
    entrada: dict[str, Any]


def _data_dir() -> Path:
    override = os.environ.get("CALCULOS_JURIDICOS_DATA_DIR")
    if override:
        return Path(override)
    root = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))
    return Path(root) / "CalculosJuridicos" / "data"


def _db_path() -> Path:
    return _data_dir() / "calculos.sqlite3"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS calculos (
            chave TEXT PRIMARY KEY,
            hash_completo TEXT NOT NULL UNIQUE,
            categoria TEXT NOT NULL,
            schema_version INTEGER NOT NULL,
            versao_aplicativo TEXT NOT NULL,
            criado_em TEXT NOT NULL,
            entrada BLOB NOT NULL,
            resultado BLOB NOT NULL,
            protegido INTEGER NOT NULL
        )
        """
    )
    return connection


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _payload(value: BaseModel | dict[str, Any], *, sem_chave: bool = False) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        exclude = {"chave_recuperacao"} if sem_chave else None
        return value.model_dump(mode="json", exclude=exclude)
    data = dict(value)
    if sem_chave:
        data.pop("chave_recuperacao", None)
    return data


def _proteger(value: dict[str, Any]) -> tuple[bytes, int]:
    compressed = zlib.compress(_json_bytes(value), level=9)
    if os.name == "nt":
        return protect(compressed), 1
    return compressed, 0


def _desproteger(value: bytes, protegido: int) -> dict[str, Any]:
    raw = protect(value, decrypt=True) if protegido else value
    return json.loads(zlib.decompress(raw).decode("utf-8"))


def _formatar_chave(prefixo: str) -> str:
    grupos = "-".join(prefixo[i:i + 4] for i in range(0, len(prefixo), 4))
    return f"CJ1-{grupos}"


def normalizar_chave(chave: str) -> str:
    limpa = re.sub(r"[^A-Za-z0-9]", "", chave or "").upper()
    if limpa.startswith("CJ1"):
        limpa = limpa[3:]
    if len(limpa) < 20 or not re.fullmatch(r"[A-F0-9]+", limpa):
        raise ValueError("Chave de recuperação inválida.")
    return _formatar_chave(limpa)


def registrar_calculo(
    categoria: CategoriaCalculo,
    entrada: BaseModel | dict[str, Any],
    resultado: BaseModel | dict[str, Any],
) -> str:
    entrada_json = _payload(entrada)
    resultado_json = _payload(resultado, sem_chave=True)
    identidade = {
        "schema_version": SCHEMA_VERSION,
        "categoria": categoria,
        "versao_aplicativo": APP_VERSION,
        "entrada": entrada_json,
        "resultado": resultado_json,
    }
    hash_completo = hashlib.sha256(_json_bytes(identidade)).hexdigest().upper()
    entrada_blob, protegida = _proteger(entrada_json)
    resultado_blob, protegida_resultado = _proteger(resultado_json)
    if protegida != protegida_resultado:
        raise RuntimeError("Não foi possível proteger o registro do cálculo.")

    criado_em = datetime.now(timezone.utc).isoformat()
    with _connect() as connection:
        existente = connection.execute(
            "SELECT chave FROM calculos WHERE hash_completo = ?", (hash_completo,)
        ).fetchone()
        if existente:
            return str(existente["chave"])

        for tamanho in (20, 24, 32, 64):
            chave = _formatar_chave(hash_completo[:tamanho])
            ocupada = connection.execute(
                "SELECT hash_completo FROM calculos WHERE chave = ?", (chave,)
            ).fetchone()
            if ocupada:
                if ocupada["hash_completo"] == hash_completo:
                    return chave
                continue
            connection.execute(
                """
                INSERT OR IGNORE INTO calculos (
                    chave, hash_completo, categoria, schema_version, versao_aplicativo,
                    criado_em, entrada, resultado, protegido
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chave, hash_completo, categoria, SCHEMA_VERSION, APP_VERSION,
                    criado_em, entrada_blob, resultado_blob, protegida,
                ),
            )
            gravada = connection.execute(
                "SELECT chave FROM calculos WHERE hash_completo = ?", (hash_completo,)
            ).fetchone()
            if gravada:
                return str(gravada["chave"])
    raise RuntimeError("Não foi possível gerar uma chave única para o cálculo.")


def recuperar_calculo(chave: str) -> CalculoRecuperado:
    normalizada = normalizar_chave(chave)
    with _connect() as connection:
        registro = connection.execute(
            """
            SELECT chave, categoria, schema_version, versao_aplicativo, criado_em,
                   entrada, protegido
              FROM calculos
             WHERE chave = ?
            """,
            (normalizada,),
        ).fetchone()
    if not registro:
        raise KeyError("Cálculo não encontrado nesta instalação.")
    return CalculoRecuperado(
        chave_recuperacao=registro["chave"],
        categoria=registro["categoria"],
        schema_version=registro["schema_version"],
        versao_aplicativo=registro["versao_aplicativo"],
        criado_em=datetime.fromisoformat(registro["criado_em"]),
        entrada=_desproteger(registro["entrada"], registro["protegido"]),
    )
