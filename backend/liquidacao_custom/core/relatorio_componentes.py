"""Apresentação líquida dos componentes nas exportações, sem alterar a apuração."""
from decimal import Decimal


def componentes_liquidos(componentes):
    """Incorpora o limite na correção, como valor_corrigido do motor EC 136."""
    exibidos = {chave: componente for chave, componente in componentes.items()
                if chave != "limite_selic"}
    limite = componentes.get("limite_selic")
    if limite is not None and limite.valor:
        correcao = exibidos["ipcae_pos"]
        exibidos["ipcae_pos"] = correcao.model_copy(
            update={"valor": correcao.valor + limite.valor})
    return exibidos


def totais_liquidos(parcelas):
    totais = {}
    for parcela in parcelas:
        for chave, componente in componentes_liquidos(parcela.componentes).items():
            totais[chave] = totais.get(chave, Decimal(0)) + componente.valor
    return totais


def colunas_liquidas(colunas):
    return tuple(coluna for coluna in colunas if coluna[0] != "limite_selic")
