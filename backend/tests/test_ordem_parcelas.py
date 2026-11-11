import csv
import io
import json
import zipfile
from copy import deepcopy
from itertools import permutations

import openpyxl
from fastapi.testclient import TestClient
from pypdf import PdfReader

from liquidacao_custom.api.main import app
from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado
from liquidacao_custom.core.motor_simplificado import executar_calculo


def entrada():
    return {
        "perfil": "selic_cjf_v1",
        "dados_gerais": {"data_base": "2026-08-01"},
        "parcelas": [
            {"numero": n, "historico": f"Ordem {nome}", "data_vencimento": f"2025-0{n}-01",
             "valor_bruto": str(n * 100), "valor_pago_na_data": str(n * 10),
             "multa_percentual": str(n)}
            for n, nome in [(1, "alfa"), (2, "beta"), (3, "gama")]
        ],
    }


def test_reordenacao_preserva_valores_e_ordem_na_memoria_do_motor():
    payload = entrada()
    esperado = executar_calculo(CalculoSimplificado.model_validate(payload))
    por_numero = {p.numero: p.model_dump() for p in esperado.parcelas}
    for ordem in permutations(payload["parcelas"]):
        reordenada = {**payload, "parcelas": list(ordem)}
        antes = deepcopy(reordenada)
        resultado = executar_calculo(CalculoSimplificado.model_validate(reordenada))
        numeros = [p["numero"] for p in ordem]
        assert [p.numero for p in resultado.parcelas] == numeros
        assert [p["numero"] for p in resultado.premissas["entrada"]["parcelas"]] == numeros
        assert {p.numero: p.model_dump() for p in resultado.parcelas} == por_numero
        assert resultado.resumo == esperado.resumo
        assert reordenada == antes


def test_reordenacao_preservada_na_recuperacao_e_exportacoes():
    payload = entrada()
    payload["parcelas"] = [payload["parcelas"][2], payload["parcelas"][0], payload["parcelas"][1]]
    client = TestClient(app)
    resposta = client.post("/api/v1/calculo", json=payload)
    assert resposta.status_code == 200, resposta.text
    resultado = resposta.json()
    assert [p["numero"] for p in resultado["parcelas"]] == [3, 1, 2]
    recuperado = client.get(f"/api/v1/calculos/{resultado['chave_recuperacao']}")
    assert recuperado.status_code == 200, recuperado.text
    assert [p["numero"] for p in recuperado.json()["entrada"]["parcelas"]] == [3, 1, 2]

    excel = client.post("/api/v1/calculo/exportar/excel", json=payload)
    assert excel.status_code == 200, excel.text
    wb = openpyxl.load_workbook(io.BytesIO(excel.content))
    assert [row[0] for row in wb["Parcelas"].iter_rows(min_row=2, values_only=True)] == [3, 1, 2]
    wb.close()

    arquivo_csv = client.post("/api/v1/calculo/exportar/csv", json=payload)
    assert arquivo_csv.status_code == 200, arquivo_csv.text
    with zipfile.ZipFile(io.BytesIO(arquivo_csv.content)) as arquivos:
        premissas = json.loads(arquivos.read("premissas.json"))
        assert [p["numero"] for p in premissas["entrada"]["parcelas"]] == [3, 1, 2]
        linhas = csv.reader(io.StringIO(arquivos.read("indices_por_parcela.csv").decode("utf-8-sig")))
        next(linhas)
        assert list(dict.fromkeys(int(row[0]) for row in linhas)) == [3, 1, 2]

    pdf = client.post("/api/v1/calculo/exportar/pdf", json=payload)
    assert pdf.status_code == 200, pdf.text
    texto = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
    assert texto.index("Ordem gama") < texto.index("Ordem alfa") < texto.index("Ordem beta")
