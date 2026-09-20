import io
import json
from datetime import date
from decimal import Decimal as D

from pypdf import PdfReader

from liquidacao_custom.core.criterios_simplificados import CalculoSimplificado
from liquidacao_custom.core.honorarios_principais import BASE_IPCA
from liquidacao_custom.core.motor_simplificado import criterios_publicos, executar_calculo, moeda
from liquidacao_custom.core.relatorio_pdf import exportar_pdf


def entrada(perfil, inicio="2021-12-01", fim="2025-09-30", inicio_juros=None):
    return CalculoSimplificado.model_validate({
        "perfil": perfil,
        "dados_gerais": {
            "data_base": fim,
            "criterio_inicio_juros": "data_fixa" if inicio_juros else "vencimento",
            "data_inicial_juros": inicio_juros,
        },
        "parcelas": [{
            "numero": 1,
            "historico": "Teste",
            "data_vencimento": inicio,
            "valor_bruto": "1000.00",
            "valor_pago_na_data": "0",
        }],
    })


def test_catalogo_expoe_apenas_os_sete_perfis_novos():
    assert criterios_publicos()["perfis"] == (
        {"id": "fazenda_publica_1_v1", "nome": "Fazenda Pública 1"},
        {"id": "fazenda_publica_2_v1", "nome": "Fazenda Pública 2"},
        {"id": "selic_ipcae_poupanca_v1", "nome": "Fazenda Pública 3"},
        {"id": "selic_ipcae_2aa_v1", "nome": "Fazenda Pública 4"},
        {"id": "selic_cjf_v1", "nome": "SELIC"},
        {"id": "ipca_taxa_legal_v1", "nome": "Civil 1"},
        {"id": "civil_2_v1", "nome": "Civil 2"},
    )


def test_fazenda_publica_1_mantem_ipcae_e_poupanca_em_todo_periodo():
    resultado = executar_calculo(entrada("fazenda_publica_1_v1"))
    parcela = resultado.parcelas[0]
    assert set(parcela.componentes) == {"ipcae_pre", "poupanca_pre"}
    assert parcela.componentes["ipcae_pre"].data_final == date(2025, 9, 30)
    assert parcela.componentes["poupanca_pre"].data_final == date(2025, 9, 30)
    assert all("SELIC única" not in item.indice_aplicado for item in resultado.memoria_mensal)


def test_fazenda_publica_2_troca_para_selic_e_nao_retorna_ao_ipcae():
    resultado = executar_calculo(entrada("fazenda_publica_2_v1"))
    parcela = resultado.parcelas[0]
    assert set(parcela.componentes) == {"ipcae_pre", "poupanca_pre", "selic"}
    assert parcela.componentes["ipcae_pre"].data_final == date(2021, 12, 8)
    assert parcela.componentes["selic"].data_inicial == date(2021, 12, 9)
    assert parcela.componentes["selic"].data_final == date(2025, 9, 30)
    assert all("IPCA-E IBGE" not in item.indice_aplicado for item in parcela.memoria_correcao[1:])


def test_fazenda_publica_3_preserva_tres_faixas():
    parcela = executar_calculo(entrada("selic_ipcae_poupanca_v1")).parcelas[0]
    assert set(parcela.componentes) == {"ipcae_pre", "poupanca_pre", "selic", "ipcae_pos", "poupanca_pos"}
    assert parcela.componentes["selic"].data_final == date(2025, 9, 9)
    assert parcela.componentes["ipcae_pos"].data_inicial == date(2025, 9, 10)
    assert parcela.componentes["poupanca_pos"].data_inicial == date(2025, 9, 10)


def test_fazenda_publica_4_inclui_tema_905_antes_da_selic_e_limite_depois():
    resultado = executar_calculo(entrada("selic_ipcae_2aa_v1"))
    parcela = resultado.parcelas[0]
    assert set(parcela.componentes) == {
        "ipcae_pre", "poupanca_pre", "selic", "ipcae_pos", "juros_2aa", "limite_selic",
    }
    assert parcela.componentes["ipcae_pre"].data_final == date(2021, 12, 8)
    assert parcela.componentes["poupanca_pre"].data_final == date(2021, 12, 8)
    assert parcela.componentes["selic"].data_inicial == date(2021, 12, 9)
    assert parcela.componentes["selic"].data_final == date(2025, 9, 9)
    assert parcela.componentes["ipcae_pos"].data_inicial == date(2025, 9, 10)
    assert parcela.componentes["juros_2aa"].data_inicial == date(2025, 9, 10)
    assert resultado.resumo.totais_componentes == {
        chave: componente.valor for chave, componente in parcela.componentes.items()
    }
    assert parcela.valor_apurado + sum((item.valor for item in parcela.componentes.values()), D(0)) == parcela.total_parcela


def test_civil_2_usa_ipca_e_juros_simples_com_datas_independentes():
    calculo = entrada("civil_2_v1", inicio="2025-02-01", fim="2025-03-01", inicio_juros="2025-01-01")
    resultado = executar_calculo(calculo)
    parcela = resultado.parcelas[0]
    dados = json.loads(BASE_IPCA.read_text(encoding="utf-8"))
    fator = D(1) + D(dados["ipca"]["2025-02"]) / 100
    assert set(parcela.componentes) == {"ipca", "juros_1am"}
    assert parcela.componentes["ipca"].data_inicial == date(2025, 2, 1)
    assert parcela.componentes["juros_1am"].data_inicial == date(2025, 1, 1)
    assert parcela.componentes["juros_1am"].taxa_acumulada_percentual == D("2.000000")
    assert parcela.juros_mora == moeda(D("1000") * fator * D("0.02"))
    assert parcela.total_parcela == parcela.valor_apurado + parcela.correcao_monetaria + parcela.juros_mora
    assert resultado.premissas["versao_metodologia"] == "civil_2_ipca_juros_simples_1am_datas_independentes_v1"


def test_civil_2_aceita_primeiro_dia_seguinte_e_fecha_agosto_inteiro():
    resultado = executar_calculo(
        entrada("civil_2_v1", inicio="2026-08-01", fim="2026-09-01", inicio_juros="2026-08-01")
    )
    parcela = resultado.parcelas[0]

    assert resultado.premissas["data_base_maxima"] == "2026-09-01"
    assert parcela.componentes["ipca"].data_final == date(2026, 8, 31)
    assert parcela.componentes["ipca"].fator_acumulado == D("0.9968")
    assert parcela.valor_corrigido == D("996.80")


def test_pdf_nao_deixa_titulo_da_tabela_orfao_apos_observacao_extensa():
    calculo = entrada("fazenda_publica_1_v1", inicio="2009-07-01", fim="2026-08-31")
    calculo.dados_gerais.observacoes = "Observação extensa para testar a paginação. " * 160
    calculo.parcelas[0].historico = "Descrição extensa da parcela para testar a quebra da tabela. " * 30

    paginas = [" ".join(pagina.extract_text().split()) for pagina in PdfReader(io.BytesIO(exportar_pdf(executar_calculo(calculo)))).pages]
    pagina_tabela = next(texto for texto in paginas if "Valores por parcela" in texto)

    assert "Parcela / descrição" in pagina_tabela
    assert "Descrição extensa da parcela" in pagina_tabela
