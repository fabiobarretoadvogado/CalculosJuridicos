import type { CriteriosPublicos, PerfilCalculo } from '../services/api';

type PerfilPadrao = Exclude<PerfilCalculo, 'poupanca_deposito_v1'>;

const PERFIS_PADRAO: { id: PerfilPadrao; nome: string }[] = [
  { id: 'fazenda_publica_1_v1', nome: 'Fazenda Pública 1' },
  { id: 'fazenda_publica_2_v1', nome: 'Fazenda Pública 2' },
  { id: 'selic_ipcae_poupanca_v1', nome: 'Fazenda Pública 3' },
  { id: 'selic_ipcae_2aa_v1', nome: 'Fazenda Pública 4' },
  { id: 'selic_cjf_v1', nome: 'SELIC' },
  { id: 'ipca_taxa_legal_v1', nome: 'Civil 1' },
  { id: 'civil_2_v1', nome: 'Civil 2' },
];

export function opcoesPerfisCalculo(catalogo?: CriteriosPublicos['perfis']) {
  return (catalogo?.length ? catalogo : PERFIS_PADRAO).map(item => ({
    value: item.id,
    label: item.nome,
  }));
}
