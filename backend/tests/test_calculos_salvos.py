import io
import re

from fastapi.testclient import TestClient
from pypdf import PdfReader

from liquidacao_custom.api.main import app


client = TestClient(app)


def entrada_principal(valor="1000.00"):
    return {
        "dados_gerais": {
            "data_base": "2025-09-30",
            "processo": "RECUPERACAO-TESTE",
            "requerente": "Parte autora",
            "requerido": "Parte ré",
        },
        "parcelas": [{
            "numero": 1,
            "historico": "Parcela recuperável",
            "data_vencimento": "2025-09-01",
            "valor_bruto": valor,
        }],
    }


def test_calculo_recebe_chave_estavel_e_pode_ser_recuperado():
    primeira = client.post("/api/v1/calculo", json=entrada_principal())
    repetida = client.post("/api/v1/calculo", json=entrada_principal())
    alterada = client.post("/api/v1/calculo", json=entrada_principal("1000.01"))

    assert primeira.status_code == repetida.status_code == alterada.status_code == 200
    chave = primeira.json()["chave_recuperacao"]
    assert re.fullmatch(r"CJ1-(?:[A-F0-9]{4}-){4}[A-F0-9]{4}", chave)
    assert repetida.json()["chave_recuperacao"] == chave
    assert alterada.json()["chave_recuperacao"] != chave

    recuperada = client.get(f"/api/v1/calculos/{chave.lower()}")
    assert recuperada.status_code == 200
    corpo = recuperada.json()
    assert corpo["categoria"] == "calculo_principal"
    assert corpo["chave_recuperacao"] == chave
    assert corpo["entrada"]["dados_gerais"]["processo"] == "RECUPERACAO-TESTE"
    assert corpo["entrada"]["parcelas"][0]["historico"] == "Parcela recuperável"


def test_chave_invalida_ou_ausente_tem_erro_claro():
    invalida = client.get("/api/v1/calculos/chave-invalida")
    ausente = client.get("/api/v1/calculos/CJ1-0000-0000-0000-0000-0000")
    assert invalida.status_code == 400
    assert invalida.json()["detail"] == "Chave de recuperação inválida."
    assert ausente.status_code == 404
    assert ausente.json()["detail"] == "Cálculo não encontrado nesta instalação."


def test_pdf_principal_imprime_a_mesma_chave_da_tela():
    calculo = client.post("/api/v1/calculo", json=entrada_principal()).json()
    pdf = client.post("/api/v1/calculo/exportar/pdf", json=entrada_principal())
    assert pdf.status_code == 200
    texto = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf.content)).pages)
    assert f"Chave de recuperação: {calculo['chave_recuperacao']}" in texto


def test_honorarios_isolados_tambem_podem_ser_recuperados_e_reeditados():
    entrada = {
        "categoria": "honorarios_sucumbenciais_isolados",
        "dados_gerais": {"data_base": "2026-08-31", "processo": "HONORARIOS-RECUPERACAO"},
        "base": "valor_certo",
        "valor_certo": "1500.05",
    }
    resposta = client.post("/api/v1/honorarios/isolados", json=entrada)
    assert resposta.status_code == 200
    chave = resposta.json()["chave_recuperacao"]
    recuperada = client.get(f"/api/v1/calculos/{chave}")
    assert recuperada.status_code == 200
    assert recuperada.json()["categoria"] == "honorarios_sucumbenciais_isolados"
    assert recuperada.json()["entrada"]["valor_certo"] == "1500.05"

    pdf = client.post("/api/v1/honorarios/isolados/exportar/pdf", json=entrada)
    texto = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf.content)).pages)
    assert f"Chave de recuperação: {chave}" in texto
