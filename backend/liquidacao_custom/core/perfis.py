"""Padrões oferecidos pela interface; preservam a escolha na entrada e na memória."""
FAZENDA_1 = "fazenda_publica_1_v1"
FAZENDA_2 = "fazenda_publica_2_v1"
# Os identificadores antigos são preservados para não invalidar cálculos salvos.
FAZENDA_3 = ATUAL = "selic_ipcae_poupanca_v1"
FAZENDA_4 = EC136 = "selic_ipcae_2aa_v1"
CJF = "selic_cjf_v1"
IPCAE_1AM_SIMPLES = "ipcae_1am_simples_v1"
IPCA_TAXA_LEGAL = CIVIL_1 = "ipca_taxa_legal_v1"
CIVIL_2 = "civil_2_v1"
PERFIS_FAZENDA = (FAZENDA_1, FAZENDA_2, FAZENDA_3, FAZENDA_4)
PERFIS = (
    {"id": FAZENDA_1, "nome": "Fazenda Pública 1"},
    {"id": FAZENDA_2, "nome": "Fazenda Pública 2"},
    {"id": FAZENDA_3, "nome": "Fazenda Pública 3"},
    {"id": FAZENDA_4, "nome": "Fazenda Pública 4"},
    {"id": CJF, "nome": "SELIC"},
    {"id": CIVIL_1, "nome": "Civil 1"},
    {"id": CIVIL_2, "nome": "Civil 2"},
)
