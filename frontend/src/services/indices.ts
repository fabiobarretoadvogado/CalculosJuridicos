import { api } from './api';

export interface BaseIndices { versao: string; sha256: string; origem: string }
export interface SerieIndice {
  id: string; nome: string; inicio: string; fim: string; consulta_em: string | null;
  quantidade: number; fonte: string; observacao: string; legado: boolean;
  unidade: 'competencia' | 'data';
}
export interface CatalogoIndices {
  base: BaseIndices; aviso: string; series: SerieIndice[];
  perfis: { id: string; nome: string; data_base_maxima: string | null; ultima_competencia_selic?: string | null; observacao: string }[];
  empacotado: boolean; atualizacoes_configuradas: boolean;
  ultima_verificacao: string | null; erro_atualizacao: string;
}
export const obterCatalogoIndices = async (): Promise<CatalogoIndices> => (await api.get('/indices/catalogo')).data;
export const atualizarIndices = async (): Promise<{ atualizado: boolean; base: BaseIndices; mensagem?: string }> => (
  await api.post('/indices/atualizar', undefined, { timeout: 180000 })
).data;
export function avisarIndicesAtualizados() { window.dispatchEvent(new Event('indices-atualizados')); }
export function nomeBaseIndices(base: BaseIndices) {
  if (base.origem === 'instalador') return 'Base incluída no programa';
  const v = base.versao;
  return `Pacote de ${v.slice(6, 8)}/${v.slice(4, 6)}/${v.slice(0, 4)} · ${v.slice(9, 11)}:${v.slice(11, 13)} UTC`;
}
