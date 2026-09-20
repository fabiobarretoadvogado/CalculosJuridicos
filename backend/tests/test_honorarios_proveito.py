import io
from decimal import Decimal as D

from fastapi.testclient import TestClient
from pypdf import PdfReader

from liquidacao_custom.api.main import app
from liquidacao_custom.core.honorarios_proveito import (
    CalculoHonorariosProveito,
    executar_honorarios_proveito,
    moeda,
)
from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado
from liquidacao_custom.core.motor_simplificado import carregar_base, executar_calculo
from liquidacao_custom.core.motor_ipcae_1am import criterios_ipcae_1am, taxa_ipcae_anual


def entrada(valor_original="2000.00", valor_correto="1000.00"):
    return {
        "categoria": "honorarios_sucumbenciais_proveito_economico",
        "dados_gerais": {"data_base": "2025-10-31", "processo": "0000000-00.0000.0.00.0000"},
        "divida_original": {
            "perfil": "selic_cjf_v1",
            "criterio_inicio_juros": "vencimento",
            "parcelas": [
                {
                    "numero": 1,
                    "historico": "Primeiro item exigido",
                    "data_origem": "2025-09-10",
                    "valor": valor_original,
                },
                {
                    "numero": 2,
                    "historico": "Segundo item exigido",
                    "data_origem": "2025-09-15",
                    "valor": "800.00",
                },
            ],
        },
        "divida_correta": {
            "perfil": "selic_ipcae_2aa_v1",
            "criterio_inicio_juros": "data_fixa",
            "data_inicial_juros": "2025-09-20",
            "parcelas": [
                {
                    "numero": 1,
                    "historico": "Primeiro item correto",
                    "data_origem": "2025-09-10",
                    "valor": valor_correto,
                },
                {
                    "numero": 2,
                    "historico": "Segundo item correto",
                    "data_origem": "2025-09-15",
                    "valor": "400.00",
                },
            ],
        },
        "percentual_sentenca": "12.5000",
    }


def test_atualiza_operacoes_com_encargos_independentes_e_aplica_percentual():
    resultado = executar_honorarios_proveito(CalculoHonorariosProveito.model_validate(entrada()))

    assert resultado.divida_original.perfil == "selic_cjf_v1"
    assert resultado.divida_correta.perfil == "selic_ipcae_2aa_v1"
    assert set(resultado.divida_original.componentes) == {"selic"}
    assert set(resultado.divida_correta.componentes) == {
        "ipcae_pre", "poupanca_pre", "selic", "ipcae_pos", "juros_2aa", "limite_selic"
    }
    assert resultado.divida_original.quantidade_parcelas == 2
    assert resultado.divida_correta.quantidade_parcelas == 2
    assert resultado.divida_original.valor_informado == D("2800.00")
    assert resultado.divida_correta.valor_informado == D("1400.00")
    assert resultado.divida_original.valor_atualizado == sum(
        parcela.valor_atualizado for parcela in resultado.divida_original.parcelas
    )
    assert resultado.divida_correta.valor_atualizado == sum(
        parcela.valor_atualizado for parcela in resultado.divida_correta.parcelas
    )
    assert resultado.diferenca_atualizada == moeda(
        resultado.divida_original.valor_atualizado - resultado.divida_correta.valor_atualizado
    )
    assert resultado.proveito_economico == resultado.diferenca_atualizada
    assert resultado.honorarios_sucumbenciais == moeda(resultado.proveito_economico * D("0.125"))
    assert resultado.divida_correta.premissas["entrada"]["dados_gerais"]["data_inicial_juros"] == "2025-09-20"
    assert resultado.alertas == []


def test_sem_reducao_gera_alerta_e_nao_honorarios_negativos():
    resultado = executar_honorarios_proveito(
        CalculoHonorariosProveito.model_validate(entrada("500.00", "1000.00"))
    )

    assert resultado.diferenca_atualizada < 0
    assert resultado.proveito_economico == D("0.00")
    assert resultado.honorarios_sucumbenciais == D("0.00")
    assert len(resultado.alertas) == 1


def test_aceita_ipca_taxa_legal_nas_duas_dividas():
    dados = entrada()
    for chave in ("divida_original", "divida_correta"):
        dados[chave]["perfil"] = "ipca_taxa_legal_v1"
        dados[chave]["criterio_inicio_juros"] = "vencimento"
        dados[chave].pop("data_inicial_juros", None)

    resultado = executar_honorarios_proveito(CalculoHonorariosProveito.model_validate(dados))

    assert resultado.divida_original.perfil == "ipca_taxa_legal_v1"
    assert resultado.divida_correta.perfil == "ipca_taxa_legal_v1"
    assert resultado.divida_original.nome_perfil == "Civil 1"


def test_custas_despesas_nao_alteram_base_dos_honorarios_e_compoem_total_geral():
    sem_custas = executar_honorarios_proveito(CalculoHonorariosProveito.model_validate(entrada()))
    dados = entrada()
    dados["custas_despesas"] = [{
        "numero": 1,
        "nome": "Diligência do oficial de justiça",
        "data": "2025-09-01",
        "valor": "250.00",
    }]

    resultado = executar_honorarios_proveito(CalculoHonorariosProveito.model_validate(dados))
    custa = resultado.custas_despesas[0]

    assert resultado.proveito_economico == sem_custas.proveito_economico
    assert resultado.honorarios_sucumbenciais == sem_custas.honorarios_sucumbenciais
    assert custa.valor_atualizado == custa.valor_original + custa.correcao_monetaria
    assert all(memoria.juros_periodo == 0 for memoria in custa.memoria)
    assert resultado.custas_despesas_valor_original == D("250.00")
    assert resultado.custas_despesas_valor_atualizado == custa.valor_atualizado
    assert resultado.total_geral == resultado.honorarios_sucumbenciais + custa.valor_atualizado


def test_pdf_honorarios_discrimina_custas_e_total_geral():
    dados = entrada()
    dados["custas_despesas"] = [{
        "numero": 1,
        "nome": "Honorários periciais",
        "data": "2025-09-01",
        "valor": "300.00",
    }]

    response = TestClient(app).post(
        "/api/v1/honorarios/proveito-economico/exportar/pdf",
        json=dados,
    )

    assert response.status_code == 200, response.text
    reader = PdfReader(io.BytesIO(response.content))
    conteudo = "\n".join(page.extract_text() for page in reader.pages)
    primeira_pagina = reader.pages[0].extract_text()
    pagina_custas = reader.pages[1].extract_text()
    assert "Custas e despesas processuais" not in primeira_pagina
    assert "Honorários periciais" not in primeira_pagina
    assert "Custas e despesas processuais" in pagina_custas
    assert "Honorários periciais" in pagina_custas
    assert "Fator IPCA-E" in pagina_custas
    assert "Dívida originalmente exigida" not in pagina_custas
    assert "Dívida correta" not in pagina_custas
    assert "Total geral" in primeira_pagina
    assert conteudo.count("Fator IPCA-E") == 1


def test_rejeita_custa_ou_despesa_posterior_a_data_base():
    dados = entrada()
    dados["custas_despesas"] = [{
        "numero": 1,
        "nome": "Taxa judiciária",
        "data": "2025-11-01",
        "valor": "100.00",
    }]
    response = TestClient(app).post("/api/v1/honorarios/proveito-economico", json=dados)

    assert response.status_code == 422
    assert "Custa ou despesa 1" in response.text
    assert "posterior à data-base" in response.text


def test_pdf_representa_operacao_extinta_sem_parcela_ficticia():
    from liquidacao_custom.core.relatorio_honorarios_pdf import exportar_pdf_honorarios

    dados = entrada()
    dados["percentual_sentenca"] = "10"
    dados["divida_correta"]["extincao_integral"] = True
    # Campos preenchidos antes de marcar a extinção não podem criar saldo oculto.
    resultado = executar_honorarios_proveito(CalculoHonorariosProveito.model_validate(dados))
    correta = resultado.divida_correta

    assert correta.quantidade_parcelas == 0
    assert correta.valor_atualizado == D("0.00")
    assert correta.parcelas == []
    assert correta.premissas["extincao_integral"] is True
    assert resultado.proveito_economico == resultado.divida_original.valor_atualizado
    assert resultado.honorarios_sucumbenciais == moeda(resultado.proveito_economico * D("0.10"))

    reader = PdfReader(io.BytesIO(exportar_pdf_honorarios(resultado)))
    pagina_extincao = reader.pages[-1].extract_text()
    assert "Execução integralmente extinta" in pagina_extincao
    assert "Extinção integral informada pelo usuário" in pagina_extincao
    assert "R$ 0,00" in pagina_extincao
    secao_extincao = pagina_extincao.split(correta.rotulo, 1)[-1]
    assert "Parcelas ou itens" not in secao_extincao


def test_rejeita_extincao_integral_na_divida_original():
    dados = entrada()
    dados["divida_original"]["extincao_integral"] = True

    response = TestClient(app).post("/api/v1/honorarios/proveito-economico", json=dados)

    assert response.status_code == 422
    assert "extinção integral só pode ser informada para a dívida correta" in response.text


def test_exige_item_quando_divida_correta_nao_esta_extinta():
    dados = entrada()
    dados["divida_correta"]["parcelas"] = []

    response = TestClient(app).post("/api/v1/honorarios/proveito-economico", json=dados)

    assert response.status_code == 422
    assert "Informe ao menos um item da dívida ou marque a extinção integral" in response.text


def test_endpoint_preserva_formula_e_detalhamento_auditavel():
    response = TestClient(app).post("/api/v1/honorarios/proveito-economico", json=entrada())

    assert response.status_code == 200
    resultado = response.json()
    assert resultado["categoria"] == "honorarios_sucumbenciais_proveito_economico"
    assert "dívida original atualizada" in resultado["formula"]
    assert resultado["divida_original"]["memoria_mensal"]
    assert resultado["divida_correta"]["memoria_mensal"]
    assert len(resultado["divida_original"]["parcelas"]) == 2
    assert len(resultado["divida_correta"]["parcelas"]) == 2


def test_relatorio_pdf_honorarios_recalcula_e_documenta_as_duas_dividas():
    dados = entrada()
    dados["dados_gerais"].update({
        "processo": "0060479-17.2022.8.25.0001",
        "vara": "22ª Vara Cível de Aracaju",
        "requerente": "Município de Aracaju",
        "requerido": "Espólio de Edla Maria Santos França",
        "observacoes": "Comparação com encargos independentes.",
    })
    dados["percentual_sentenca"] = "20"

    response = TestClient(app).post(
        "/api/v1/honorarios/proveito-economico/exportar/pdf",
        json=dados,
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert "relatorio_honorarios_sucumbenciais.pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-")
    reader = PdfReader(io.BytesIO(response.content))
    content = "\n".join(page.extract_text() for page in reader.pages)
    primeira_pagina = reader.pages[0].extract_text()
    for termo in (
        "Relatório de honorários sucumbenciais",
        "0060479-17.2022.8.25.0001",
        "22ª Vara Cível de Aracaju",
        "Município de Aracaju",
        "Espólio de Edla Maria Santos França",
        "Dívida original",
        "Dívida correta",
        "Proveito econômico",
        "Honorários sucumbenciais",
        "20,00%",
        "Parcelas ou itens",
        "Critérios e metodologia",
        "Comparação com encargos independentes.",
    ):
        assert termo in content
    assert len(reader.pages) >= 3
    assert "Barreto Fontes" in reader.metadata.author
    assert len(reader.pages[0].images) == 1
    assert "Apuração dos honorários" not in primeira_pagina
    etapas_resumo = (
        "Dívida originalmente exigida atualizada",
        "Dívida correta atualizada",
        "Proveito econômico",
        "Percentual da sentença",
        "Honorários sucumbenciais",
    )
    cursor = 0
    for etapa in etapas_resumo:
        cursor = primeira_pagina.index(etapa, cursor) + len(etapa)
    assert primeira_pagina.count("Dívida originalmente exigida atualizada") == 1
    for numero, page in enumerate(reader.pages, 1):
        assert f"Página {numero}" in page.extract_text()
        assert round(float(page.mediabox.width)) == 842
        assert round(float(page.mediabox.height)) == 595


def test_relatorio_pdf_usa_um_unico_cabecalho_por_tabela_de_parcelas():
    dados = entrada()
    for chave in ("divida_original", "divida_correta"):
        modelo = dados[chave]["parcelas"][0]
        dados[chave]["perfil"] = (
            "ipcae_1am_simples_v1" if chave == "divida_original" else "selic_cjf_v1"
        )
        dados[chave]["multa_moratoria_percentual"] = "10"
        dados[chave]["parcelas"] = [
            {
                **modelo,
                "numero": numero,
                "historico": f"{chave} - item {numero:02d}",
                "data_origem": "2021-02-05",
            }
            for numero in range(1, 25)
        ]

    response = TestClient(app).post(
        "/api/v1/honorarios/proveito-economico/exportar/pdf",
        json=dados,
    )

    assert response.status_code == 200, response.text
    reader = PdfReader(io.BytesIO(response.content))
    paginas = [page.extract_text() for page in reader.pages]
    content = "\n".join(paginas)
    assert "Composição dos encargos" not in content
    assert content.count("Juros 1% a.m.") == 1
    assert "Multa" in content
    assert "SELIC" in content
    assert "sem cumulação com IPCA-E" not in content
    assert "sem transição automática para outro índice" not in content
    assert "Base " in content
    assert "Fator " in content
    assert "05/02/2021 a 31/10/2025" in content

    pagina_final_original = next(
        pagina for pagina in paginas if "divida_original - item 24" in pagina
    )
    for numero in range(21, 25):
        assert f"divida_original - item {numero:02d}" in pagina_final_original
    assert "TOTAL" in pagina_final_original

    pagina_final_correta = next(
        pagina for pagina in paginas if "divida_correta - item 24" in pagina
    )
    for numero in range(21, 25):
        assert f"divida_correta - item {numero:02d}" in pagina_final_correta
    assert "TOTAL" in pagina_final_correta


def test_rejeita_data_de_origem_posterior_a_data_base():
    dados = entrada()
    dados["divida_original"]["parcelas"][1]["data_origem"] = "2025-11-01"
    response = TestClient(app).post("/api/v1/honorarios/proveito-economico", json=dados)

    assert response.status_code == 422
    assert "item 2" in response.text
    assert "posterior à data-base" in response.text


def test_rejeita_numeros_repetidos_na_mesma_divida():
    dados = entrada()
    dados["divida_correta"]["parcelas"][1]["numero"] = 1
    response = TestClient(app).post("/api/v1/honorarios/proveito-economico", json=dados)

    assert response.status_code == 422
    assert "números distintos" in response.text


def test_perfil_ipcae_1am_usa_periodos_completos_de_30_dias_sem_capitalizacao():
    calculo = CalculoSimplificado.model_validate({
        "perfil": "ipcae_1am_simples_v1",
        "dados_gerais": {
            "data_base": "2022-09-30",
            "criterio_inicio_juros": "vencimento",
        },
        "parcelas": [{
            "numero": 1,
            "historico": "IPTU 2021 - parcela 001",
            "data_vencimento": "2021-02-05",
            "valor_bruto": "484.40",
        }],
    })

    parcela = executar_calculo(calculo).parcelas[0]

    assert parcela.componentes["juros_1am"].taxa_acumulada_percentual == D("20")
    assert parcela.juros_mora == D("106.61")
    assert parcela.total_parcela == parcela.valor_corrigido + parcela.juros_mora
    assert parcela.componentes["ipcae"].valor == parcela.correcao_monetaria


def test_perfil_ipcae_1am_aceita_debito_de_2018_com_indice_anual_auditavel():
    calculo = CalculoSimplificado.model_validate({
        "perfil": "ipcae_1am_simples_v1",
        "dados_gerais": {
            "data_base": "2022-09-30",
            "criterio_inicio_juros": "vencimento",
        },
        "parcelas": [{
            "numero": 1,
            "historico": "Débito original",
            "data_vencimento": "2018-04-30",
            "valor_bruto": "19403.92",
        }],
    })

    resultado = executar_calculo(calculo)
    anuais = [
        item for item in resultado.parcelas[0].memoria_correcao
        if item.indice_aplicado == "IPCA-E anual (IBGE)"
    ]

    assert criterios_ipcae_1am()["inicio"] == "2010-01-01"
    assert [item.competencia for item in anuais] == ["2019", "2020", "2021", "2022"]
    assert anuais[0].fator_aplicado == D("1.0428")
    assert taxa_ipcae_anual(carregar_base(), 2019) == D("4.28")
    textos_publicos = [
        criterios_ipcae_1am()["contagem"],
        *resultado.premissas["criterios"],
        *resultado.premissas["metodologia"],
        *(item.indice_aplicado for item in resultado.memoria_mensal),
    ]
    assert all("CDA" not in texto for texto in textos_publicos)


def test_perfil_ipcae_1am_avanca_ate_o_ultimo_mes_fechado():
    calculo = CalculoSimplificado.model_validate({
        "perfil": "ipcae_1am_simples_v1",
        "dados_gerais": {
            "data_base": "2026-08-31",
            "criterio_inicio_juros": "vencimento",
        },
        "parcelas": [{
            "numero": 1,
            "historico": "Obrigação corrigida pelo IPCA-E e juros simples",
            "data_vencimento": "2021-02-05",
            "valor_bruto": "484.40",
        }],
    })

    resultado = executar_calculo(calculo)
    parcela = resultado.parcelas[0]
    registros_mensais = [
        item for item in parcela.memoria_correcao if item.indice_aplicado == "IPCA-E mensal (IBGE)"
    ]

    assert criterios_ipcae_1am()["data_base_maxima"] == "2026-08-31"
    assert registros_mensais[0].competencia == "2022-10"
    assert registros_mensais[-1].competencia == "2026-08"
    assert parcela.componentes["juros_1am"].taxa_acumulada_percentual == D("67")
    assert parcela.total_parcela == parcela.valor_corrigido + parcela.juros_mora


def test_multa_moratoria_independente_incide_sobre_principal_corrigido():
    dados = entrada()
    dados["divida_original"]["multa_moratoria_percentual"] = "10"
    dados["divida_correta"]["multa_moratoria_percentual"] = "10"

    resultado = executar_honorarios_proveito(CalculoHonorariosProveito.model_validate(dados))

    for operacao in (resultado.divida_original, resultado.divida_correta):
        assert "multa_moratoria" in operacao.componentes
        for parcela in operacao.parcelas:
            multa = parcela.componentes["multa_moratoria"]
            assert multa.valor == moeda(multa.base_calculo * D("0.10"))
        assert operacao.premissas["multa_moratoria_percentual"] == "10"


def test_cda_420608_reconcilia_total_documental_na_data_base():
    datas = [
        "2021-02-05", "2021-03-05", "2021-04-05", "2021-05-05",
        "2021-06-07", "2021-07-05", "2021-08-05", "2021-09-06",
        "2020-02-05", "2020-03-05", "2020-04-06", "2020-05-05",
        "2020-06-05", "2020-07-06", "2020-08-05", "2020-09-08",
        "2019-02-05", "2019-03-07", "2019-04-05", "2019-05-06",
        "2019-06-05", "2019-07-05", "2019-08-05", "2019-09-05",
    ]
    valores = ["484.40"] * 8 + ["449.97"] * 8 + ["415.80"] * 8
    parcelas = [
        {
            "numero": numero,
            "historico": f"CDA 420608/2022 - item {numero:03d}",
            "data_origem": vencimento,
            "valor": valor,
        }
        for numero, (vencimento, valor) in enumerate(zip(datas, valores), start=1)
    ]
    dados = {
        "categoria": "honorarios_sucumbenciais_proveito_economico",
        "dados_gerais": {"data_base": "2022-09-30"},
        "divida_original": {
            "perfil": "ipcae_1am_simples_v1",
            "criterio_inicio_juros": "vencimento",
            "multa_moratoria_percentual": "10",
            "parcelas": parcelas,
        },
        "divida_correta": {
            "perfil": "selic_cjf_v1",
            "criterio_inicio_juros": "vencimento",
            "multa_moratoria_percentual": "10",
            "parcelas": parcelas,
        },
        "percentual_sentenca": "10",
    }

    resultado = executar_honorarios_proveito(CalculoHonorariosProveito.model_validate(dados))

    assert resultado.divida_original.valor_informado == D("10801.36")
    assert resultado.divida_original.valor_atualizado == D("16858.65")
    assert resultado.divida_original.quantidade_parcelas == 24
    assert resultado.divida_correta.quantidade_parcelas == 24
    assert resultado.honorarios_sucumbenciais == moeda(resultado.proveito_economico * D("0.10"))

    dados["dados_gerais"]["data_base"] = "2026-08-31"
    atualizado = executar_honorarios_proveito(CalculoHonorariosProveito.model_validate(dados))

    assert atualizado.divida_original.valor_atualizado == D("27052.52")
    assert atualizado.divida_correta.valor_atualizado == D("19265.76")
    assert atualizado.proveito_economico == D("7786.76")
    assert atualizado.honorarios_sucumbenciais == D("778.68")
