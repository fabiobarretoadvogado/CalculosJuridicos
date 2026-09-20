import io
import json
import os
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from liquidacao_custom.api.main import app

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
