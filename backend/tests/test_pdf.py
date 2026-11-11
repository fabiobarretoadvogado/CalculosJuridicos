import io
from datetime import date

import pytest
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
    assert "Início dos juros: Vencimento de cada parcela." in " ".join(content.split())
    assert content.index("OBSERVAÇÕES E RESSALVAS") < content.index("CRÉDITO - ACRÉSCIMO") < content.index("CRITÉRIOS E METODOLOGIA")
    for termo in ("Tema 905", "08/12/2021", "09/12/2021", "10/09/2025", "31/08/2026"):
        assert termo in content
    assert 3 <= len(reader.pages) <= 6
    assert "Barreto Fontes" in reader.metadata.author
    assert len(reader.pages[0].images) == 1
    for n, page in enumerate(reader.pages, 1):
        assert f"Página {n}" in page.extract_text()
        assert round(float(page.mediabox.width)) == 842  # A4 horizontal
        assert round(float(page.mediabox.height)) == 595
    assert content.count("Descrição") == 1
    assert all(termo in content for termo in ("IPCA-E pré", "IPCA-E pós", "Fator ", "Poupança"))
    assert "TR" not in content
    assert "Não informado" not in content
    assert "Não informada" not in content
    assert "Classe:" in content
    assert "exportações Excel e CSV" not in content
    assert "Padrão aplicado:" not in content and "Referência final:" in content
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
    assert content.index("TOTAL ATUALIZADO") < content.index("DADOS DO PROCESSO") < content.index("123 <script> & Silva") < content.index("CRÉDITO - ACRÉSCIMO")
    assert "João de São Paulo" in content
    assert "Classe: Cumprimento <individual> & execução" in content
    assert "A & B <b>texto literal</b>" in content
    assert "01/11/2025" in content
    assert content.index("CRÉDITO - ACRÉSCIMO") < content.index("CRITÉRIOS E METODOLOGIA") < content.index("01/11/2025")
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
    assert content.count("Descrição") == 181  # Histórico integral e cabeçalho padronizado.
    assert content.count("extensa") == 180
    assert "FONTES E CONFERÊNCIA" in content


def test_pdf_indice_ausente_bloqueia_exportacao(monkeypatch):
    from liquidacao_custom.core import motor_simplificado as motor
    data = motor.carregar_base()
    del data["poupanca_total"]["2021-03-15"]
    monkeypatch.setattr(motor, "carregar_base", lambda: data)
    response = TestClient(app).post("/api/v1/calculo/exportar/pdf", json=payload_36())
    assert response.status_code == 400
    assert "Índice ausente" in response.json()["detail"]


def payload_creditos_debitos(
    quantidade, perfil, quantidade_descontos, textos_extensos,
):
    payload = payload_36()
    payload["perfil"] = perfil
    payload["parcelas"] = payload["parcelas"][:quantidade]
    for parcela in payload["parcelas"]:
        parcela["historico"] = f"Crédito de teste {parcela['numero']:03d}"
    if textos_extensos:
        payload["parcelas"][0]["historico"] += ". Descrição extensa de crédito." * 180
        payload["dados_gerais"]["observacoes"] = "Observação extensa do cálculo. " * 150
    payload["descontos"] = {"itens": [
        {"numero": numero, "descricao": f"Débito de teste {numero:03d}",
         "data": "2025-10-15", "valor": "10"}
        for numero in range(1, quantidade_descontos + 1)
    ]}
    payload["custas_despesas"] = [
        {"numero": 1, "nome": "Custa de teste", "data": "2025-10-01", "valor": "100"},
    ]
    return payload


@pytest.mark.parametrize("quantidade,perfil,quantidade_descontos,textos_extensos", [
    (1, "selic_cjf_v1", 1, False),
    (20, "selic_cjf_v1", 2, False),
    (36, "selic_ipcae_poupanca_v1", 25, False),
    (1, "selic_ipcae_poupanca_v1", 1, True),
])
def test_pdf_creditos_e_debitos_preservam_ordem_e_intervalo(
    quantidade, perfil, quantidade_descontos, textos_extensos,
):
    payload = payload_creditos_debitos(quantidade, perfil, quantidade_descontos, textos_extensos)
    client = TestClient(app)
    response = client.post("/api/v1/calculo", json=payload)
    assert response.status_code == 200, response.text
    resultado = response.json()
    reader, content = texto(client.post("/api/v1/calculo/exportar/pdf", json=payload))
    content = " ".join(content.split())
    paginas = [page.extract_text() for page in reader.pages]
    creditos = {i for i, pagina in enumerate(paginas) if "Crédito de teste" in pagina or "Histórico integral da parcela" in pagina}
    debitos = {i for i, pagina in enumerate(paginas) if "Débito de teste" in pagina}
    custas = {i for i, pagina in enumerate(paginas) if "Custa de teste" in pagina}
    assert creditos and debitos and custas
    assert max(creditos) <= min(debitos)
    assert max(debitos) <= min(custas)
    assert "DÉBITO - DECRÉSCIMO" in paginas[min(debitos)]
    assert content.index("DÉBITO - DECRÉSCIMO") < content.index("CRITÉRIOS E METODOLOGIA")
    assert content.index("CRITÉRIOS E METODOLOGIA") < content.index("FONTES E CONFERÊNCIA")
    assert content.count("CRÉDITO - ACRÉSCIMO") == 1
    assert content.count("DÉBITO - DECRÉSCIMO") == 1
    assert "Data" in content.split("DÉBITO - DECRÉSCIMO", 1)[1].split("Débito de teste", 1)[0]
    assert content.count("Débito de teste") == quantidade_descontos
    assert content.count("Crédito de teste") == quantidade
    from liquidacao_custom.core.relatorio_pdf import moeda
    assert moeda(resultado["resumo"]["total_atualizado"]) in content
    assert moeda(resultado["resumo"]["abatimentos"]) in content
    for n, pagina in enumerate(paginas, 1):
        assert f"Página {n}" in pagina
        assert len(pagina.splitlines()) > 2  # Não gerar página só com rodapé.


def test_pdf_pagamentos_desmarcados_separados_sem_debito_ficticio():
    payload = payload_36()
    payload["parcelas"] = [payload["parcelas"][0]]
    payload["descontos"] = {"itens": [
        {"numero": 1, "descricao": "Pagamento apenas informado", "aplicar": False},
    ]}
    reader, content = texto(TestClient(app).post("/api/v1/calculo/exportar/pdf", json=payload))
    paginas = [page.extract_text() for page in reader.pages]
    credito = next(i for i, pagina in enumerate(paginas) if "CRÉDITO - ACRÉSCIMO" in pagina)
    pagamento = next(i for i, pagina in enumerate(paginas) if "PAGAMENTOS NÃO ABATIDOS" in pagina)
    assert credito == pagamento
    assert paginas[credito].index("CRÉDITO - ACRÉSCIMO") < paginas[pagamento].index("PAGAMENTOS NÃO ABATIDOS")
    assert "Não selecionado; não compõe o abatimento." in content
    assert "DÉBITO - DECRÉSCIMO" not in content


@pytest.mark.parametrize("principal,linhas,multa", [("3000", 1, False), ("10000000000", 2, False), ("3000", 1, True)])
def test_resumo_campos_iguais_valores_alinhados_e_total_sem_corte(principal, linhas, multa, valores_do_resumo):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado
    from liquidacao_custom.core.motor_simplificado import executar_calculo
    from liquidacao_custom.core.relatorio_pdf import exportar_pdf
    payload = payload_creditos_debitos(1, "selic_cjf_v1", 1, False)
    payload["parcelas"][0]["valor_bruto"] = principal
    if multa:
        payload["parcelas"][0]["multa_percentual"] = "2"
    payload["honorarios_sucumbenciais"] = {"aplicar": True, "base": "proveito_economico", "percentual": "10"}
    payload["cumprimento_sentenca"] = {"aplicar_multa": True, "aplicar_honorarios": True}
    resultado = executar_calculo(CalculoSimplificado.model_validate(payload))
    antes = resultado.model_dump(mode="json")
    pagina = PdfReader(io.BytesIO(exportar_pdf(resultado))).pages[0]
    assert resultado.model_dump(mode="json") == antes
    valores = [trecho[1:] for trecho in valores_do_resumo(pagina)]
    assert len(valores) == (9 if multa else 8)
    assert len({round(y, 2) for _, y, _, _ in valores}) == linhas
    assert all(40 <= x and x + largura <= float(pagina.mediabox.width) - 40
               for x, _, largura, _ in valores)
    total = next(v for v in valores if v[3] == 12)
    if linhas > 1:
        assert sum(round(v[1], 2) == round(total[1], 2) for v in valores) >= 2
    assert total[0] + total[2] == pytest.approx(float(pagina.mediabox.width) - 40, abs=.001)
    if linhas == 1:
        assert [valores[i + 1][0] - valores[i][0] for i in range(6)] == pytest.approx(
            [(float(pagina.mediabox.width) - 80) / len(valores)] * 6)


@pytest.mark.parametrize("perfil", ["selic_cjf_v1", "ipcae_1am_simples_v1"])
def test_cabecalhos_operacionais_padronizados_sem_notas_genericas(perfil):
    payload = payload_creditos_debitos(1, perfil, 1, False)
    payload["parcelas"][0]["multa_percentual"] = "2"
    reader, content = texto(TestClient(app).post("/api/v1/calculo/exportar/pdf", json=payload))
    assert "O sinal" not in content and "Parcela / descrição" not in content
    assert content.count("Descrição") == 4  # Créditos, multas, débitos e custas.
    for pagina in reader.pages:
        trechos = []
        pagina.extract_text(visitor_text=lambda t, cm, tm, fonte, sz: trechos.append(t)
            if fonte and "Bold" in str(fonte.get("/BaseFont")) and sz == 8 else None)
        assert "até a data-base" not in " ".join(trechos)


def test_tabelas_acessorias_tem_fechamento_uniforme_e_total_do_cumprimento():
    """Confere no PDF as linhas de fechamento, inclusive tabelas de uma linha."""
    payload = payload_creditos_debitos(1, "selic_cjf_v1", 1, False)
    payload["honorarios_sucumbenciais"] = {"aplicar": True, "base": "proveito_economico", "percentual": "10"}
    payload["cumprimento_sentenca"] = {"aplicar_multa": True, "aplicar_honorarios": True,
        "destacar_contratuais": True, "percentual_contratuais": "20"}
    reader, content = texto(TestClient(app).post("/api/v1/calculo/exportar/pdf", json=payload))
    titulos = ("HONORÁRIOS SUCUMBENCIAIS", "CUMPRIMENTO DE SENTENÇA",
        "DESTAQUE DE HONORÁRIOS CONTRATUAIS", "CUSTAS E DESPESAS PROCESSUAIS")
    for titulo in titulos:
        pagina = next(p for p in reader.pages if titulo in p.extract_text())
        textos, fechamentos = [], []
        estado = {"cor": None, "largura": None, "inicio": None, "fim": None}
        def desenhar(op, args, matriz, tm):
            if op == b"RG":
                estado["cor"] = tuple(float(v) for v in args)
            elif op == b"w":
                estado["largura"] = float(args[0])
            elif op in (b"m", b"l"):
                x, y = map(float, args)
                estado["inicio" if op == b"m" else "fim"] = (
                    matriz[0] * x + matriz[2] * y + matriz[4],
                    matriz[1] * x + matriz[3] * y + matriz[5])
            elif op == b"S" and estado["inicio"] and estado["fim"]:
                a, b = estado["inicio"], estado["fim"]
                if estado["cor"] == pytest.approx((7/255, 47/255, 84/255), abs=1e-5) and estado["largura"] == .6 and b[0] - a[0] > 750:
                    fechamentos.append(a[1])
        pagina.extract_text(visitor_operand_before=desenhar,
            visitor_text=lambda t, matriz, tm, fonte, sz: textos.append(
                (t.strip(), matriz[1] * tm[4] + matriz[3] * tm[5] + matriz[5], sz)))
        inicio = next(y for t, y, _ in textos if t == titulo)
        fim = max((y for t, y, sz in textos if t and sz == 10 and y < inicio), default=40)
        assert any(fim < y < inicio for y in fechamentos), (titulo, inicio, fim, fechamentos)
        assert all(sz == 8 for t, y, sz in textos if fim < y < inicio and (t.startswith("R$ ") or t.endswith("%")))
        if titulo == "CUMPRIMENTO DE SENTENÇA":
            assert any(t == "TOTAL" and fim < y < inicio for t, y, _ in textos)
    assert "TOTAL" in content


@pytest.mark.parametrize("quantidade", [1, 13])
def test_pdf_intervalo_real_e_inicio_sem_titulo_orfao(quantidade):
    from reportlab.lib.units import cm
    payload = payload_creditos_debitos(quantidade, "selic_cjf_v1", 1, False)
    reader, _ = texto(TestClient(app).post("/api/v1/calculo/exportar/pdf", json=payload))
    paginas = [p.extract_text() for p in reader.pages]
    creditos = max(i for i, t in enumerate(paginas) if "Crédito de teste" in t)
    debito = next(i for i, t in enumerate(paginas) if "DÉBITO - DECRÉSCIMO" in t)
    assert "Data" in paginas[debito] and "Débito de teste 001" in paginas[debito]
    # A paginação depende da altura efetiva do cabeçalho, resumo e tabela.
    # Conferir o intervalo na mesma página ou o início sem espaço no topo.
    assert creditos <= debito <= creditos + 1
    if creditos == debito:
        posicoes = []
        reader.pages[debito].extract_text(visitor_text=lambda t, matriz, tm, fonte, sz:
            posicoes.append((t.strip(), matriz[1] * tm[4] + matriz[3] * tm[5] + matriz[5])))
        titulo = next(y for t, y in posicoes if t == "DÉBITO - DECRÉSCIMO")
        retangulos = []
        def registrar_fundo(operador, args, matriz, tm):
            if operador == b"re":
                retangulos.append(matriz[5] + min(float(args[1]), float(args[1] + args[3])))
        reader.pages[debito].extract_text(visitor_operand_before=registrar_fundo)
        fim_tabela_credito = min(y for y in retangulos if y > titulo)
        # Mede a borda do fundo do TOTAL até o topo da linha do título (10 pt acima da base).
        assert fim_tabela_credito - (titulo + 10) == pytest.approx(1.5 * cm, abs=.001)
    else:
        posicoes = []
        reader.pages[debito].extract_text(visitor_text=lambda t, matriz, tm, fonte, sz:
            posicoes.append((t.strip(), matriz[1] * tm[4] + matriz[3] * tm[5] + matriz[5])))
        titulo = next(y for t, y in posicoes if t == "DÉBITO - DECRÉSCIMO")
        assert titulo > float(reader.pages[debito].mediabox.height) - 65


@pytest.mark.parametrize("bloco,titulo,primeira_linha", [
    ("honorarios_sucumbenciais", "HONORÁRIOS SUCUMBENCIAIS", "Percentual fixado"),
    ("cumprimento_sentenca", "CUMPRIMENTO DE SENTENÇA", "Rubrica"),
    ("destaque_contratuais", "DESTAQUE DE HONORÁRIOS CONTRATUAIS", "Percentual contratual"),
])
def test_acessorios_aproveitam_pagina_dos_debitos(bloco, titulo, primeira_linha):
    payload = payload_creditos_debitos(1, "selic_cjf_v1", 1, False)
    payload["custas_despesas"] = []
    if bloco == "cumprimento_sentenca":
        payload[bloco] = {"aplicar_multa": True, "aplicar_honorarios": True}
    elif bloco == "destaque_contratuais":
        payload["cumprimento_sentenca"] = {"destacar_contratuais": True, "percentual_contratuais": "10"}
    else:
        payload[bloco] = {"aplicar": True, "base": "proveito_economico", "percentual": "10"}
    reader, _ = texto(TestClient(app).post("/api/v1/calculo/exportar/pdf", json=payload))
    paginas = [p.extract_text() for p in reader.pages]
    pagina = next(t for t in paginas if "DÉBITO - DECRÉSCIMO" in t)
    assert titulo in pagina and primeira_linha in pagina
    assert pagina.index("DÉBITO - DECRÉSCIMO") < pagina.index(titulo)
    from reportlab.lib.units import cm
    posicoes = []
    reader.pages[paginas.index(pagina)].extract_text(visitor_text=lambda t, matriz, tm, fonte, sz:
        posicoes.append((t.strip(), matriz[1] * tm[4] + matriz[3] * tm[5] + matriz[5], sz)))
    fim, fonte_nota = next((y, sz) for t, y, sz in posicoes if t.startswith("Parcelas atualizadas:"))
    inicio, fonte_titulo = next((y, sz) for t, y, sz in posicoes if t == titulo)
    assert (fim - fonte_nota) - (inicio + fonte_titulo) == pytest.approx(1.5 * cm, abs=.001)
