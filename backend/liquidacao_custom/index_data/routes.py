from __future__ import annotations

import threading
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from .catalog import catalog
from .client import synchronize

router = APIRouter(prefix="/api/v1/indices", tags=["Índices oficiais"])
_status_lock = threading.Lock()
_status = {"ultima_verificacao": None, "erro_atualizacao": ""}


def synchronize_and_record():
    try:
        result = synchronize()
        with _status_lock:
            _status.update(ultima_verificacao=datetime.now(timezone.utc).isoformat(), erro_atualizacao="")
        return result
    except Exception:
        with _status_lock:
            _status.update(ultima_verificacao=datetime.now(timezone.utc).isoformat(), erro_atualizacao=(
                "Não foi possível obter e validar a atualização. Os índices anteriores foram preservados."))
        raise


@router.get("/catalogo")
def index_catalog():
    result = catalog()
    with _status_lock:
        result.update(_status)
    return result


@router.post("/atualizar")
def update_indices():
    try:
        return synchronize_and_record()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=(
            "Não foi possível obter e validar a atualização. Os índices anteriores foram preservados. "
            "Confira a conexão e tente novamente.")) from exc
