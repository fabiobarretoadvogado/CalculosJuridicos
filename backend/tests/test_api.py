import io
import json
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

import openpyxl
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from liquidacao_custom.api.main import app
from liquidacao_custom.api import routes

client = TestClient(app)


def test_api_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_api_listar_indices():
    response = client.get("/api/v1/indices")
    assert response.status_code == 200
    assert "indices" in response.json()
    assert response.json()["indices"] == ["SELIC", "IPCA-E IBGE", "POUPANCA"]


def test_api_obter_modelo():
    response = client.get("/api/v1/parcelas/modelo")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_api_executar_calculo():
    payload = {
      "dados_gerais": {
        "data_base": "2025-06-01",
        "processo": "0001234-56.2024.8.19.0001",
      },
      "parcelas": [
        {
          "numero": 1,
          "data_vencimento": "2024-01-15",
          "historico": "Reembolso",
          "valor_bruto": 1000.00,
          "data_inicial_juros": "2024-03-20",
        }
      ]
    }
    
    response = client.post("/api/v1/calculo", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert "resumo" in res_data
    assert float(res_data["resumo"]["total_atualizado"]) > 1000.00


def test_api_exportar_excel():
    payload = {
      "dados_gerais": {
        "data_base": "2025-06-01",
        "processo": "0001234-56.2024.8.19.0001",
      },
      "parcelas": [
        {
          "numero": 1,
          "data_vencimento": "2024-01-15",
          "historico": "Reembolso",
          "valor_bruto": 1000.00,
        }
      ]
    }
    
    response = client.post("/api/v1/calculo/exportar/excel", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    workbook = openpyxl.load_workbook(io.BytesIO(response.content), read_only=True)
    try:
        assert "Dados Gerais" in workbook.sheetnames
        assert "Parcelas" in workbook.sheetnames
    finally:
        workbook.close()


@pytest.mark.parametrize("formato", ["excel", "csv", "modelo", "csv_zip"])
def test_exportacao_remove_temporarios_mesmo_quando_falha(tmp_path, monkeypatch, formato):
    """Uma falha não conserva dados parciais nem remove arquivos vizinhos."""
    monkeypatch.setattr(routes.tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(routes, "executar_calculo_registrado", lambda _: object())
    preservado = tmp_path / "arquivo-preexistente.txt"
    preservado.write_text("preservar", encoding="utf-8")

    def falhar_excel(_resultado, caminho):
        Path(caminho).write_text("dados fictícios", encoding="utf-8")
        raise RuntimeError("falha simulada")

    def falhar_csv(_resultado, diretorio):
        (Path(diretorio) / "memoria.csv").write_text("dados fictícios", encoding="utf-8")
        raise RuntimeError("falha simulada")

    def falhar_modelo(caminho):
        Path(caminho).write_text("modelo parcial", encoding="utf-8")
        raise RuntimeError("falha simulada")

    def preparar_csv(_resultado, diretorio):
        (Path(diretorio) / "memoria.csv").write_text("dados fictícios", encoding="utf-8")

    if formato == "excel":
        monkeypatch.setattr(routes, "exportar_excel", falhar_excel)
        chamada = lambda: routes.api_exportar_excel(None)
    elif formato == "modelo":
        monkeypatch.setattr(routes, "gerar_template", falhar_modelo)
        chamada = routes.api_obter_modelo
    else:
        monkeypatch.setattr(routes, "exportar_csv", falhar_csv if formato == "csv" else preparar_csv)
        if formato == "csv_zip":
            def falhar_zip(*_args, **_kwargs):
                raise RuntimeError("falha simulada ao compactar")
            monkeypatch.setattr(routes.zipfile.ZipFile, "write", falhar_zip)
        chamada = lambda: routes.api_exportar_csv(None)

    with pytest.raises(HTTPException):
        chamada()
    assert list(tmp_path.iterdir()) == [preservado]
    assert preservado.read_text(encoding="utf-8") == "preservar"


def test_api_importar_excel(tmp_path):
    # Primeiro gera um modelo excel
    excel_path = os.path.join(tmp_path, "modelo.xlsx")
    from liquidacao_custom.core.importacao_simplificada import gerar_template
    gerar_template(excel_path)
    
    with open(excel_path, "rb") as f:
        file_data = f.read()
        
    response = client.post(
        "/api/v1/parcelas/importar",
        files={"file": ("modelo.xlsx", file_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert response.status_code == 200
    assert "parcelas" in response.json()
    assert len(response.json()["parcelas"]) == 1
