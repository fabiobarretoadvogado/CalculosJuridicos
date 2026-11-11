"""Contrato entre modalidades: mesma navegação, cálculos intactos e fontes únicas."""
import io
from decimal import Decimal

import pytest
from pypdf import PdfReader

from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado
from liquidacao_custom.core.honorarios_isolados import CalculoHonorariosIsolados, executar_honorarios_isolados
from liquidacao_custom.core.honorarios_proveito import CalculoHonorariosProveito, executar_honorarios_proveito
from liquidacao_custom.core.motor_simplificado import executar_calculo
from liquidacao_custom.core.relatorio_honorarios_pdf import exportar_pdf_honorarios
from liquidacao_custom.core.relatorio_pdf import exportar_pdf, moeda


def cenario(modalidade):
    geral = {"data_base": "2026-08-31", "processo": "EXEMPLO-HIPOTETICO"}
    if modalidade in ("principal", "civil_1"):
        dados = {"perfil": "ipca_taxa_legal_v1" if modalidade == "civil_1" else "selic_cjf_v1",
            "dados_gerais": geral,
            "parcelas": [{"numero": 1, "historico": "Crédito demonstrativo", "data_vencimento": "2026-01-01", "valor_bruto": "1000"}],
            "descontos": {"perfil": "selic_cjf_v1", "itens": [{"numero": 1, "descricao": "Pagamento demonstrativo", "data": "2026-02-01", "valor": "100"}]},
            "custas_despesas": [{"numero": 1, "nome": "Custa demonstrativa", "data": "2026-01-01", "valor": "100"}],
            "honorarios_sucumbenciais": {"aplicar": True, "base": "proveito_economico", "percentual": "20"}}
        if modalidade == "principal":
            dados["honorarios_sucumbenciais"].update(base="valor_causa", valor_causa="10000", data_protocolo="2026-01-01", indice="ipca")
        resultado = executar_calculo(CalculoSimplificado.model_validate(dados))
        exportador = exportar_pdf
    elif modalidade in ("proveito", "faixas", "extincao"):
        dados = {"dados_gerais": geral, "percentual_sentenca": "20",
            "divida_original": {"perfil": "selic_cjf_v1", "parcelas": [{"numero": 1, "historico": "Dívida original demonstrativa", "data_origem": "2026-01-01", "valor": "301000"}]},
            "divida_correta": {"perfil": "selic_cjf_v1", "parcelas": [{"numero": 1, "historico": "Dívida correta demonstrativa", "data_origem": "2026-01-01", "valor": "1000"}]},
            "custas_despesas": [{"numero": 1, "nome": "Custa demonstrativa", "data": "2026-01-01", "valor": "100"}]}
        if modalidade == "faixas":
            dados.pop("percentual_sentenca")
            dados["escalonamento_fazenda"] = {"salario_minimo": "1000", "marco": "sentenca_liquida", "data_decisao": "2026-01-01", "percentuais_faixas": ["10", "8", "5", "3", "1"]}
        if modalidade == "extincao":
            dados["divida_correta"]["extincao_integral"] = True
        resultado = executar_honorarios_proveito(CalculoHonorariosProveito.model_validate(dados))
        exportador = exportar_pdf_honorarios
    else:
        dados = {"dados_gerais": geral, "base": "valor_certo", "valor_certo": "1500.05"}
        if modalidade == "equidade_atualizada":
            dados["encargos_valor_certo"] = {"data_fixacao": "2026-01-15", "indice": "ipcae", "juros": "taxa_legal", "data_inicio_juros": "2026-03-03"}
        elif modalidade == "valor_causa":
            dados.pop("valor_certo")
            dados.update(base="valor_causa", valor_causa="10000", data_protocolo="2026-01-01", indice="ipcae", percentual_sentenca="20")
        resultado = executar_honorarios_isolados(CalculoHonorariosIsolados.model_validate(dados))
        exportador = exportar_pdf_honorarios
    resultado.dados_gerais.observacoes = "RESSALVA DE TESTE: conferir as premissas antes de usar o resultado."
    return resultado, exportador


@pytest.mark.parametrize("modalidade", [
    "principal", "civil_1", "proveito", "faixas", "extincao", "valor_causa", "equidade", "equidade_atualizada",
])
def test_modelos_compartilham_estrutura_sem_modificar_calculo(modalidade):
    resultado, exportador = cenario(modalidade)
    antes = resultado.model_dump(mode="json")
    reader = PdfReader(io.BytesIO(exportador(resultado)))
    assert resultado.model_dump(mode="json") == antes
    paginas = [" ".join(page.extract_text().split()) for page in reader.pages]
    texto = " ".join(paginas)
    assert "DADOS DO PROCESSO" in paginas[0]
    assert "OBSERVAÇÕES E RESSALVAS" in paginas[0] and "RESSALVA DE TESTE" in paginas[0]
    assert texto.index("OBSERVAÇÕES E RESSALVAS") < texto.index("CRITÉRIOS E METODOLOGIA")
    assert texto.count("CRITÉRIOS E METODOLOGIA") == 1
    assert texto.count("FONTES E CONFERÊNCIA") == 1
    assert "O sinal" not in texto and "Parcela / descrição" not in texto
    assert "Padrão aplicado" not in texto and "Referência final" in texto
    assert "Data-base máxima" not in texto and "competência SELIC disponível" not in texto
    assert texto.index("CRITÉRIOS E METODOLOGIA") < texto.index("FONTES E CONFERÊNCIA")
    valor = resultado.resumo.total_atualizado if hasattr(resultado, "resumo") else resultado.honorarios_sucumbenciais
    assert moeda(valor) in paginas[0]
    if "ANEXO TÉCNICO - MEMÓRIAS DETALHADAS" in texto:
        assert texto.index("CRITÉRIOS E METODOLOGIA") < texto.index("ANEXO TÉCNICO - MEMÓRIAS DETALHADAS") < texto.index("FONTES E CONFERÊNCIA")
        anexo = next(t for t in paginas if "ANEXO TÉCNICO - MEMÓRIAS DETALHADAS" in t)
        assert "MEMÓRIA DA" in anexo or "MEMÓRIA DOS" in anexo
    urls = []
    for n, page in enumerate(reader.pages, 1):
        assert round(float(page.mediabox.width)) == 842
        assert round(float(page.mediabox.height)) == 595
        assert f"Página {n}" in paginas[n - 1]
        for ref in page.get("/Annots", []):
            action = ref.get_object().get("/A", {})
            if action.get("/URI"):
                urls.append(str(action["/URI"]))
    assert len(urls) == len(set(urls)), "Fontes repetidas em locais diferentes do PDF"
    assert len(reader.pages[0].images) == 1
    imagens = []
    reader.pages[0].extract_text(visitor_operand_before=lambda operador, args, cm, tm: imagens.append(cm) if operador == b"Do" else None)
    assert len(imagens) == 1
    assert imagens[0][0] == pytest.approx(122), "Logo ultrapassa o espaço reservado no cabeçalho"
    logo = reader.pages[0].images[0].image
    assert imagens[0][3] / imagens[0][0] == pytest.approx(logo.height / logo.width)
    fontes = []
    reader.pages[0].extract_text(visitor_text=lambda texto, cm, tm, fonte, tamanho: fontes.append((texto, tamanho)))
    assert any("DADOS DO PROCESSO" in trecho and tamanho == 10 for trecho, tamanho in fontes)
    for page in reader.pages:
        titulos = []
        page.extract_text(visitor_text=lambda t, cm, tm, f, sz: titulos.append(t.strip())
            if sz == 10 and f and f["/BaseFont"] == "/Helvetica-Bold" and t.strip() else None)
        assert all(t == t.upper() for t in titulos), "Título de seção fora do padrão de maiúsculas"
    assert "Processo: EXEMPLO-HIPOTETICO" in paginas[0]


@pytest.mark.parametrize("modalidade", ["principal", "proveito", "extincao"])
def test_regras_selic_compartilhadas_sem_perder_referencia_aplicada(modalidade):
    resultado, exportador = cenario(modalidade)
    reader = PdfReader(io.BytesIO(exportador(resultado)))
    conteudo = " ".join(" ".join(page.extract_text().split()) for page in reader.pages)
    assert conteudo.count("Somam-se as taxas mensais SELIC, sem capitalização.") == 1
    assert conteudo.count("Arredondamento por parcela ao centavo, com precisão integral nos cálculos.") == 1
    assert "Último índice aplicado: 07/2026" in conteudo
    if modalidade == "extincao":
        assert "Extinção integral informada; sem encargos a apurar." in conteudo
    trechos = []
    for page in reader.pages:
        page.extract_text(visitor_text=lambda t, cm, tm, f, sz: trechos.append((t, f, sz)))
    regras = [(t, f, sz) for t, f, sz in trechos if "Somam-se as taxas" in t or "Arredondamento por parcela" in t]
    assert regras and all(sz == 8 and f["/BaseFont"] == "/Helvetica" for t, f, sz in regras)


def test_padrao_misto_preserva_regras_diarias_e_mensais_com_ambitos_distintos():
    resultado, exportador = cenario("civil_1")
    conteudo = " ".join(" ".join(p.extract_text().split()) for p in PdfReader(io.BytesIO(exportador(resultado))).pages)
    assert "Taxa Legal" in conteudo and "SELIC" in conteudo
    assert "01/08/2026" in conteudo and "31/08/2026" in conteudo
    assert "Inclui-se o dia inicial e exclui-se a data-base" in conteudo
    assert "A referência é mensal" not in conteudo  # referências estão no bloco da operação
    assert "Último índice aplicado: 07/2026" in conteudo


@pytest.mark.parametrize("modalidade", ["principal", "civil_1", "proveito"])
def test_criterios_em_blocos_alinhados_sem_colunas_e_regras_no_ambito_correto(modalidade):
    resultado, exportador = cenario(modalidade)
    reader = PdfReader(io.BytesIO(exportador(resultado)))
    trechos = []

    def registrar(t, cm, tm, fonte, tamanho):
        x = cm[0] * tm[4] + cm[2] * tm[5] + cm[4]
        trechos.append((t.strip(), x, fonte, tamanho))

    for page in reader.pages:
        page.extract_text(visitor_text=registrar)
    margem = next(x for t, x, _, _ in trechos if t == "CRITÉRIOS E METODOLOGIA")
    rotulos = [(t, x, f, sz) for t, x, f, sz in trechos
               if t.startswith(("Início dos encargos:", "Referência final:"))]
    assert len(rotulos) >= 6
    assert all(x == pytest.approx(margem) and sz == 8 and f["/BaseFont"] == "/Helvetica-Bold"
               for t, x, f, sz in rotulos), "Dados técnicos devem ser linhas à esquerda, sem colunas"
    conteudo = " ".join(" ".join(page.extract_text().split()) for page in reader.pages)
    conteudo = conteudo.split("CRITÉRIOS E METODOLOGIA", 1)[1]
    assert "REGRAS DE CÁLCULO" not in conteudo
    if modalidade == "principal":
        assert conteudo.index("CRÉDITOS") < conteudo.index("DÉBITOS") < conteudo.index("CUSTAS E DESPESAS")
        assert conteudo.index("CUSTAS E DESPESAS") < conteudo.index("IPCA-E: fatores mensais multiplicados")
        assert conteudo.index("IPCA-E: fatores mensais multiplicados") < conteudo.index("REGRAS COMUNS - CRÉDITOS / DÉBITOS")
        assert conteudo.index("REGRAS COMUNS - CRÉDITOS / DÉBITOS") < conteudo.index("Somam-se as taxas mensais SELIC")
    elif modalidade == "civil_1":
        assert conteudo.index("CRÉDITOS") < conteudo.index("Inclui-se o dia inicial e exclui-se a data-base") < conteudo.index("DÉBITOS")
        assert conteudo.index("DÉBITOS") < conteudo.index("Somam-se as taxas mensais SELIC") < conteudo.index("CUSTAS E DESPESAS")
    else:
        assert conteudo.index("DÍVIDA ORIGINAL") < conteudo.index("DÍVIDA CORRETA")
        assert conteudo.index("CUSTAS E DESPESAS") < conteudo.index("REGRAS COMUNS - DÍVIDA ORIGINAL / DÍVIDA CORRETA")


def test_excedente_e_ressalva_ficam_na_sintese_sem_transformar_comparacao_em_quitacao():
    dados = {
        "perfil": "selic_cjf_v1", "dados_gerais": {"data_base": "2026-08-01", "observacoes": "COMPARATIVO: saldo zero não significa quitação."},
        "parcelas": [{"numero": 1, "historico": "Cenário A", "data_vencimento": "2026-08-01", "valor_bruto": "1000"}],
        "descontos": {"perfil": "selic_cjf_v1", "itens": [{"numero": 1, "descricao": "Cenário B", "data": "2026-08-01", "valor": "2500"}]},
    }
    resultado = executar_calculo(CalculoSimplificado.model_validate(dados))
    reader = PdfReader(io.BytesIO(exportar_pdf(resultado)))
    primeira = " ".join(reader.pages[0].extract_text().split())
    assert "saldo zero não significa quitação" in primeira
    assert "R$ 1.500,00" in primeira and "abatimento foi limitado" in primeira
    assert resultado.resumo.total_atualizado == Decimal("0")
    assert resultado.descontos.resumo.total_atualizado == Decimal("2500")
    assert resultado.resumo.abatimentos == Decimal("1000")
