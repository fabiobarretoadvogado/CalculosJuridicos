from __future__ import annotations

import os
import sys
import threading
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from liquidacao_custom.metadata import APP_DISPLAY_VERSION, APP_NAME, APP_VERSION
from liquidacao_custom.updates import settings
from liquidacao_custom.updates.client import (
    UpdateInfo,
    cache_root,
    check_latest,
    download_installer,
    launch_update,
    prepare_update_job,
)
from liquidacao_custom.updates.protected import load_token, remove_token, save_token

router = APIRouter(prefix="/api/v1/app", tags=["Aplicativo"])
_lock = threading.Lock()
_available: UpdateInfo | None = None
_downloaded: Path | None = None


class AccessCredential(BaseModel):
    token: str = Field(min_length=20, max_length=500)


def _token() -> str:
    if settings.ACCESS != "private" or not settings.REPOSITORY:
        return ""
    return load_token(settings.REPOSITORY)


def _check() -> UpdateInfo | None:
    global _available
    if not settings.REPOSITORY or not settings.PUBLIC_KEY:
        _available = None
        return None
    _available = check_latest(
        settings.REPOSITORY,
        settings.PUBLIC_KEY,
        APP_VERSION,
        _token(),
    )
    return _available


@router.get("/info")
def app_info():
    return {
        "nome": APP_NAME,
        "versao": APP_VERSION,
        "edicao": APP_DISPLAY_VERSION,
        "empacotado": bool(getattr(sys, "frozen", False)),
        "atualizacoes_configuradas": bool(settings.REPOSITORY and settings.PUBLIC_KEY),
        "repositorio": settings.REPOSITORY,
        "acesso": settings.ACCESS,
    }


@router.get("/atualizacoes")
def updates_check():
    try:
        with _lock:
            info = _check()
        result = {"disponivel": bool(info), "versao_atual": APP_VERSION}
        if info:
            result.update({
                "nova_versao": info.version,
                "nova_edicao": info.visible_version,
                "notas": info.notes,
            })
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível consultar atualizações no GitHub.",
        ) from exc


@router.post("/atualizacoes/baixar")
def updates_download():
    global _downloaded
    try:
        with _lock:
            info = _available or _check()
            if not info:
                raise HTTPException(status_code=409, detail="Nenhuma atualização está disponível.")
            attempt = cache_root() / uuid.uuid4().hex
            _downloaded = download_installer(info, attempt, token=_token())
        return {"pronta": True, "edicao": info.visible_version}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="O instalador não pôde ser baixado ou validado.",
        ) from exc


@router.post("/atualizacoes/instalar")
def updates_install():
    if not getattr(sys, "frozen", False):
        raise HTTPException(status_code=409, detail="A instalação só está disponível no aplicativo empacotado.")
    try:
        with _lock:
            if not _available or not _downloaded:
                raise HTTPException(status_code=409, detail="Baixe a atualização antes de instalar.")
            job = prepare_update_job(_downloaded, _available, Path(sys.executable))
            launch_update(job)
        threading.Timer(1.0, os._exit, args=(0,)).start()
        return {"iniciada": True}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="A atualização não pôde ser iniciada.") from exc


@router.post("/autorizacao")
def save_access(credential: AccessCredential):
    if settings.ACCESS != "private" or not settings.REPOSITORY:
        raise HTTPException(status_code=409, detail="O canal atual não exige autorização privada.")
    try:
        save_token(settings.REPOSITORY, credential.token)
        _check()
        return {"autorizado": True}
    except Exception as exc:
        remove_token()
        raise HTTPException(status_code=400, detail="A autorização não pôde ser confirmada.") from exc


@router.delete("/autorizacao")
def delete_access():
    remove_token()
    return {"autorizado": False}

