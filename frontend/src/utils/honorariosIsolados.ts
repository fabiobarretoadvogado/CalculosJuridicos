import type { BaseHonorariosAutonomos, CalculoHonorariosIsolados, CoberturaHonorarios, CriteriosPublicos, CustaDespesaProcessual, DadosHonorarios, HonorariosPrincipais, EscalonamentoFazendaHonorarios, EncargosValorCerto } from '../services/api';
import { fixacaoHonorarios } from './honorariosFazenda';

export const encargosValorCertoIniciais = (): EncargosValorCerto => ({ data_fixacao: '', indice: 'ipcae', juros: 'simples', data_inicio_juros: null, percentual_mensal: null, contagem_mes_cheio: false });

export interface DetalhesLimiteHonorarios {
  data?: string;
  motivos: string[];
}

export function montarHonorariosIsolados(base: Exclude<BaseHonorariosAutonomos, 'proveito_economico'>, dados: DadosHonorarios, config: Pick<HonorariosPrincipais, 'valor_causa' | 'data_protocolo' | 'indice' | 'valor_certo'>, custas: CustaDespesaProcessual[], escalonar: boolean, percentual: string, faixas: EscalonamentoFazendaHonorarios, encargos?: EncargosValorCerto | null): CalculoHonorariosIsolados {
  const comum = { categoria: 'honorarios_sucumbenciais_isolados' as const, dados_gerais: { ...dados }, base, custas_despesas: custas.map(c => ({ ...c })) };
  return base === 'valor_certo'
    ? { ...comum, valor_certo: config.valor_certo, percentual_sentenca: null, escalonamento_fazenda: null, ...(encargos ? { encargos_valor_certo: { ...encargos, data_inicio_juros: encargos.juros === 'sem_juros' ? null : encargos.data_inicio_juros, percentual_mensal: encargos.juros === 'simples' ? encargos.percentual_mensal : null, contagem_mes_cheio: encargos.juros === 'simples' && encargos.contagem_mes_cheio } } : {}) }
    : { ...comum, valor_causa: config.valor_causa, data_protocolo: config.data_protocolo, indice: config.indice, ...fixacaoHonorarios(escalonar, percentual, faixas) };
}

export function limiteHonorariosAutonomos(base: BaseHonorariosAutonomos, indice: 'ipcae' | 'ipca', cobertura: CoberturaHonorarios | null, original: CriteriosPublicos | null, correta: CriteriosPublicos | null, temCustas: boolean, encargos?: EncargosValorCerto | null): string | undefined {
  return detalhesLimiteHonorariosAutonomos(base, indice, cobertura, original, correta, temCustas, encargos).data;
}

export function detalhesLimiteHonorariosAutonomos(base: BaseHonorariosAutonomos, indice: 'ipcae' | 'ipca', cobertura: CoberturaHonorarios | null, original: CriteriosPublicos | null, correta: CriteriosPublicos | null, temCustas: boolean, encargos?: EncargosValorCerto | null): DetalhesLimiteHonorarios {
  const nomeIndice = (valor: 'ipcae' | 'ipca') => valor === 'ipcae' ? 'IPCA-E' : 'IPCA';
  const limites: { data?: string; motivo: string }[] = base === 'proveito_economico'
    ? [
        { data: original?.data_base_maxima, motivo: 'dívida originalmente exigida' },
        { data: correta?.data_base_maxima, motivo: 'dívida correta' },
      ]
    : base === 'valor_causa'
      ? [{ data: cobertura?.[indice].data_base_maxima, motivo: `correção do valor da causa pelo ${nomeIndice(indice)}` }]
      : [];
  if (base === 'valor_certo' && encargos) {
    limites.push({ data: cobertura?.[encargos.indice].data_base_maxima, motivo: `correção do valor fixado pelo ${nomeIndice(encargos.indice)}` });
    if (encargos.juros === 'taxa_legal') limites.push({ data: cobertura?.taxa_legal?.data_base_maxima, motivo: 'Taxa Legal do valor fixado' });
  }
  if (temCustas) limites.push({ data: cobertura?.ipcae.data_base_maxima || original?.data_base_maxima_ipcae, motivo: 'custas e despesas pelo IPCA-E' });
  const validos = limites.filter((item): item is { data: string; motivo: string } => Boolean(item.data));
  const data = validos.map(item => item.data).sort()[0];
  return { data, motivos: data ? validos.filter(item => item.data === data).map(item => item.motivo) : [] };
}
