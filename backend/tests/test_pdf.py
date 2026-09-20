import io
from datetime import date

from fastapi.testclient import TestClient
from pypdf import PdfReader

from liquidacao_custom.api.main import app


def payload_36():
    parcelas = []
    for ano in range(2021, 2025):
        for mes in range(1, 13):
            vencimento = date(ano, mes, 1)
            if date(2021, 3, 1) <= vencimento <= date(2024, 2, 1):
                parcelas.append({"numero": len(parcelas) + 1, "historico": f"Competência {mes:02d}/{ano}",
                                 "data_vencimento": vencimento.isoformat(),
                                 "valor_bruto": "999.13" if ano == 2021 else "1231.83"})
    return {"dados_gerais": {"data_base": "2026-08-31", "observacoes": "Início adotado: dia 1 de cada competência."}, "parcelas": parcelas}


def texto(response):
    assert response.status_code == 200, response.text if response.status_code != 200 else ""
    assert response.headers["content-type"] == "application/pdf"
    assert "relatorio_calculo.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-")
    reader = PdfReader(io.BytesIO(response.content))
    return reader, "\n".join(p.extract_text() for p in reader.pages)


def test_pdf_mesmos_totais_parcelas_criterios_e_paginacao():
    client = TestClient(app)
    payload = payload_36()
    resultado = client.post("/api/v1/calculo", json=payload).json()
    reader, content = texto(client.post("/api/v1/calculo/exportar/pdf", json=payload))
    assert resultado["resumo"]["total_atualizado"] == "64307.77"
    for valor in ("42.018,88", "469,28", "14.603,06", "2.337,27", "244,13", "4.635,15", "64.307,77"):
        assert valor in content
    for parcela in payload["parcelas"]:
        assert parcela["historico"] in content
    assert "dia 1 de cada competência" in content
    assert "Início dos juros: Vencimento de cada parcela." in content
    assert content.index("Critérios do cálculo") < content.index("Observações adicionais") < content.index("Valores por parcela")
    for termo in ("Tema 905", "08/12/2021", "09/12/2021", "10/09/2025", "31/08/2026"):
        assert termo in content
    assert 2 <= len(reader.pages) <= 4
    assert "Barreto Fontes" in reader.metadata.author
    assert len(reader.pages[0].images) == 1
    for n, page in enumerate(reader.pages, 1):
        assert f"Página {n}" in page.extract_text()
        assert round(float(page.mediabox.width)) == 842  # A4 horizontal
        assert round(float(page.mediabox.height)) == 595
    assert content.count("Parcela / descrição") == 1
    assert all(termo in content for termo in ("IPCA-E pré", "IPCA-E pós", "Fator ", "Poupança"))
    assert "TR" not in content
    assert "Não informado" not in content
    assert "Não informada" not in content
    assert "Classe:" in content
    assert "exportações Excel e CSV" not in content
    assert "Como o cálculo foi feito" in content
    assert "Valor da correção" in content
    assert "base × (fator - 1)" in content
    primeira = resultado["parcelas"][0]["componentes"]
    from decimal import Decimal
    for c in primeira.values():
        indice = c["fator_acumulado"] if c["fator_acumulado"] is not None else c["taxa_acumulada_percentual"]
        assert f"{Decimal(indice):.4f}".replace(".", ",") in content
        assert f"Base {Decimal(c['base_calculo']):.4f}".replace(".", ",") in content


def test_pdf_preserva_texto_literal_pagamento_e_inicio_juros():
    payload = payload_36()
    payload["parcelas"] = [{"numero": 1, "historico": "A & B <b>texto literal</b>",
                            "data_vencimento": "2025-09-01", "data_inicial_juros": "2025-11-01",
                            "valor_bruto": "1000", "valor_pago_na_data": "200"}]
    payload["dados_gerais"].update({"processo": "123 <script> & Silva", "requerente": "João de São Paulo", "classe": "Cumprimento <individual> & execução"})
    resultado = TestClient(app).post("/api/v1/calculo", json=payload).json()
    assert resultado["dados_gerais"]["classe"] == payload["dados_gerais"]["classe"]
    _, content = texto(TestClient(app).post("/api/v1/calculo/exportar/pdf", json=payload))
    assert "123 <script> & Silva" in content
    assert content.index("TOTAL ATUALIZADO") < content.index("Dados do processo") < content.index("123 <script> & Silva") < content.index("Critérios do cálculo")
    assert "João de São Paulo" in content
    assert "Classe: Cumprimento <individual> & execução" in content
    assert "A & B <b>texto literal</b>" in content
    assert "01/11/2025" in content
    assert content.index("Critérios do cálculo") < content.index("01/11/2025") < content.index("Valores por parcela")
    assert "Início informado dos juros" not in content
    assert "200,00" in content and "800,00" in content
    assert "Pagamentos no vencimento" in content


def test_pdf_textos_longos_nao_interrompem_paginacao():
    payload = payload_36()
    payload["parcelas"] = [payload["parcelas"][0]]
    payload["parcelas"][0]["historico"] = "Descrição extensa para conferir quebra de página. " * 180
    payload["dados_gerais"]["observacoes"] = "Observações do processo. " * 150
    reader, content = texto(TestClient(app).post("/api/v1/calculo/exportar/pdf", json=payload))
    assert len(reader.pages) > 1
    # Cabeçalhos podem separar as duas palavras quando uma célula atravessa páginas.
    assert content.count("Descrição") == 180
    assert content.count("extensa") == 180
    assert "Fontes e conferência" in content


def test_pdf_indice_ausente_bloqueia_exportacao(monkeypatch):
    from liquidacao_custom.core import motor_simplificado as motor
    data = motor.carregar_base()
    del data["poupanca_total"]["2021-03-15"]
    monkeypatch.setattr(motor, "carregar_base", lambda: data)
    response = TestClient(app).post("/api/v1/calculo/exportar/pdf", json=payload_36())
    assert response.status_code == 400
    assert "Índice ausente" in response.json()["detail"]
