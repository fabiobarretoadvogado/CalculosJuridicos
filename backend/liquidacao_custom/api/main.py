"""
Arquivo de inicialização principal da API REST do liquidacao-custom.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from liquidacao_custom.api.routes import router
from liquidacao_custom.metadata import APP_VERSION
from liquidacao_custom.updates.routes import router as app_router

app = FastAPI(
    title="Liquidação Custom API",
    description="API REST de motor de cálculo judicial auditável e customizado para liquidação de sentença.",
    version=APP_VERSION,
)

# Adiciona suporte a CORS para permitir integração com qualquer frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(app_router)

web_root = Path(__file__).resolve().parents[1] / "web"


@app.get("/", tags=["Root"])
def read_root(request: Request):
    """Endpoint raiz para verificação rápida do status da API."""
    if "text/html" in request.headers.get("accept", "") and (web_root / "index.html").is_file():
        return FileResponse(web_root / "index.html")
    return {
        "sistema": "liquidacao-custom",
        "status": "online",
        "api_docs": "/docs"
    }


if (web_root / "index.html").is_file():
    app.mount("/", StaticFiles(directory=web_root, html=True), name="interface")
