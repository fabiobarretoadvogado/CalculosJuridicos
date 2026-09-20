import type { CriteriosPublicos } from '../services/api';
import { formatarCompetencia, formatarData } from './formatters';

function dataAnterior(dataIso: string): string {
  const [ano, mes, dia] = dataIso.split('-').map(Number);
  const data = new Date(Date.UTC(ano, mes - 1, dia));
  data.setUTCDate(data.getUTCDate() - 1);
  return data.toISOString().slice(0, 10);
}

function enumerar(itens: string[]): string {
  if (itens.length < 2) return itens[0] || '';
  return `${itens.slice(0, -1).join(', ')} e ${itens.at(-1)}`;
}

export function mensagemCoberturaSelecionada(dataLimite: string, motivos: string[], criterios?: CriteriosPublicos | null): string {
  const base = `Data-base máxima para os critérios selecionados: ${formatarData(dataLimite)}.`;
  const causa = motivos.length ? ` Limite definido por ${enumerar(motivos)}.` : '';
  if (!criterios || criterios.data_base_maxima !== dataLimite) return base + causa;
  if (criterios.perfil === 'selic_cjf_v1' && criterios.ultima_competencia_selic_disponivel) {
    return `${base}${causa} Última competência SELIC disponível: ${formatarCompetencia(criterios.ultima_competencia_selic_disponivel)}.`;
  }
  if (['ipca_taxa_legal_v1', 'civil_2_v1'].includes(criterios.perfil)) {
    return `${base}${causa} A data-base é excluída do cálculo; os índices são utilizados até ${formatarData(dataAnterior(dataLimite))}.`;
  }
  return `${base}${causa} Todos os índices necessários estão disponíveis até essa data.`;
}
