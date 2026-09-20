"""Rótulos comuns às exportações do perfil de cálculo por períodos."""

COLUNAS_COMPONENTES = (
    ("ipcae_pre", "IPCA-E pré EC 113/2021", "até 08/12/2021"),
    ("poupanca_pre", "Poupança pré EC 113/2021", "até 08/12/2021"),
    ("selic", "SELIC única", "09/12/2021 a 09/09/2025"),
    ("ipcae_pos", "IPCA-E pós EC 136/2025", "desde 10/09/2025"),
    ("poupanca_pos", "Poupança pós EC 136/2025", "desde 10/09/2025"),
)

COLUNAS_COMPONENTES_EC136 = (
    ("ipcae_pre", "IPCA-E", "até 08/12/2021"),
    ("poupanca_pre", "Poupança", "até 08/12/2021"),
    ("selic", "SELIC única", "09/12/2021 a 09/09/2025"),
    ("ipcae_pos", "IPCA-E pós EC 136/2025", "desde 10/09/2025"),
    ("juros_2aa", "Juros 2% a.a. pós EC 136/2025", "desde 10/09/2025"),
    ("limite_selic", "Ajuste ao limite SELIC", "desde 10/09/2025"),
)

COLUNAS_FAZENDA_1 = (
    ("ipcae_pre", "IPCA-E", "desde 01/07/2009"),
    ("poupanca_pre", "Poupança", "desde 01/07/2009"),
)

COLUNAS_FAZENDA_2 = (
    ("ipcae_pre", "IPCA-E", "até 08/12/2021"),
    ("poupanca_pre", "Poupança", "até 08/12/2021"),
    ("selic", "SELIC única", "desde 09/12/2021"),
)


def colunas_componentes(resultado):
    colunas = colunas_perfil(resultado)
    if "multa_parcela" in resultado.resumo.totais_componentes:
        return (*colunas, ("multa_parcela", "Multa e encargos", "por parcela"))
    return colunas


def colunas_perfil(resultado):
    if resultado.premissas.get("perfil") == "poupanca_deposito_v1":
        return (("poupanca_deposito", "Poupança - remuneração da conta", "aniversários completos"),)
    if resultado.premissas.get("perfil") == "ipca_taxa_legal_v1":
        return (("ipca", "IPCA", "desde o início da correção"), ("taxa_legal", "Taxa Legal", "desde o início dos juros"))
    if resultado.premissas.get("perfil") == "civil_2_v1":
        return (("ipca", "IPCA", "desde o início da correção"), ("juros_1am", "Juros simples de 1% a.m.", "desde o início dos juros"))
    if resultado.premissas.get("perfil") == "ipcae_1am_simples_v1":
        return (("ipcae", "IPCA-E", "até a data-base"), ("juros_1am", "Juros simples de 1% a.m.", "até a data-base"))
    if resultado.premissas.get("perfil") == "correcao_mensal_v1":
        return (("correcao", "IPCA-E", "competências mensais"),)
    if resultado.premissas.get("perfil") == "selic_cjf_v1":
        return (("selic", "SELIC", "até a data-base"),)
    perfil = resultado.premissas.get("perfil")
    if perfil == "fazenda_publica_1_v1":
        return COLUNAS_FAZENDA_1
    if perfil == "fazenda_publica_2_v1":
        return COLUNAS_FAZENDA_2
    if perfil == "selic_ipcae_2aa_v1":
        return COLUNAS_COMPONENTES_EC136
    return COLUNAS_COMPONENTES
