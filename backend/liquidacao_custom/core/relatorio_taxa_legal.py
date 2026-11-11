"""Memória mensal da Taxa Legal: taxas oficiais com seis casas decimais."""
from decimal import Decimal as D
from .relatorio_layout import separar_operacoes, tabela_operacional


def linhas_taxa_legal(resultado):
    civil5 = resultado.premissas.get("perfil") == "civil_5_taxa_legal_reconstruida_v1"
    extras = ["Origem da taxa", "Competência dos insumos", "Fator SELIC", "Fator IPCA-15"] if civil5 else []
    yield ["Parcela", "Mês", "Período", "Dias / mês", "Taxa Legal mensal (%)", "Taxa proporcional (%)", "Acumulada (%)", "Base corrigida", "Juros do trecho", "Juros acumulados", *extras]
    for m in resultado.premissas.get("memoria_taxa_legal", []):
        formacao = m.get("formacao_taxa") or {}
        origem = "Reconstruída" if m.get("origem") == "reconstruida" else "Publicada BCB SGS 29543"
        extras = [origem, formacao.get("competencia_insumos", ""), formacao.get("fator_selic", ""), formacao.get("fator_ipca15", "")] if civil5 else []
        yield [m["parcela"], m["competencia"], m["inicio"] + " a " + m["fim"], f"{m['dias']} / {m['dias_mes']}",
               m["taxa_mensal"], m["taxa_proporcional"], m["taxa_acumulada"], m["base"], m["juros_periodo"], m["juros_acumulados"], *extras]


def blocos_memoria_taxa_legal(resultado, largura, estilos, p, *, altura=523):
    from .relatorio_pdf import moeda, data_br
    blocos = []
    for parcela in resultado.parcelas:
        linhas = [m for m in resultado.premissas.get("memoria_taxa_legal", []) if m["parcela"] == parcela.numero]
        if not linhas:
            continue
        cabecalho = [p(t, "cabecalho") for t in ["Mês", "Período", "Dias / mês", "Taxa mensal (%)", "Proporcional (%)", "Acumulada (%)", "Juros do trecho", "Juros acumulados"]]
        dados = [cabecalho]
        for m in linhas:
            dados.append([p(m["competencia"], "celula"), p(data_br(m["inicio"]) + " a " + data_br(m["fim"]), "celula"),
                p(f"{m['dias']} / {m['dias_mes']}", "numero"),
                *[p(f"{D(m[k]):.6f}".replace(".", ","), "numero") for k in ("taxa_mensal", "taxa_proporcional", "taxa_acumulada")],
                p(moeda(m["juros_periodo"]), "numero"), p(moeda(m["juros_acumulados"]), "numero")])
        larguras = [largura*f for f in (.075, .225, .085, .12, .13, .12, .12, .125)]
        introducao = [p(f"Memória da Taxa Legal - parcela {parcela.numero}", "secao"),
            p(f"Base corrigida final: R$ {moeda(parcela.valor_corrigido)}. Taxas simples; data-base excluída; valores em reais. Taxas com seis casas decimais.", "nota")]
        memoria = tabela_operacional(dados, larguras)
        blocos.extend([*separar_operacoes(introducao, memoria, largura, altura), *introducao, memoria])
    return blocos
