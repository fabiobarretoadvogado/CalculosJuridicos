import type { BaseHonorariosAutonomos, CalculoHonorariosIsolados, CoberturaHonorarios, CriteriosPublicos, CustaDespesaProcessual, DadosHonorarios, HonorariosPrincipais, EscalonamentoFazendaHonorarios, EncargosValorCerto } from '../services/api';
import { fixacaoHonorarios } from './honorariosFazenda';

export const encargosValorCertoIniciais = (): EncargosValorCerto => ({ data_fixacao: '', indice: 'ipcae', juros: 'simples', data_inicio_juros: null, percentual_mensal: null, contagem_mes_cheio: false });

export function montarHonorariosIsolados(base: Exclude<BaseHonorariosAutonomos, 'proveito_economico'>, dados: DadosHonorarios, config: Pick<HonorariosPrincipais, 'valor_causa' | 'data_protocolo' | 'indice' | 'valor_certo'>, custas: CustaDespesaProcessual[], escalonar: boolean, percentual: string, faixas: EscalonamentoFazendaHonorarios, encargos?: EncargosValorCerto | null): CalculoHonorariosIsolados {
  const comum = { categoria: 'honorarios_sucumbenciais_isolados' as const, dados_gerais: { ...dados }, base, custas_despesas: custas.map(c => ({ ...c })) };
  return base === 'valor_certo'
    ? { ...comum, valor_certo: config.valor_certo, percentual_sentenca: null, escalonamento_fazenda: null, ...(encargos ? { encargos_valor_certo: { ...encargos, data_inicio_juros: encargos.juros === 'sem_juros' ? null : encargos.data_inicio_juros, percentual_mensal: encargos.juros === 'simples' ? encargos.percentual_mensal : null, contagem_mes_cheio: encargos.juros === 'simples' && encargos.contagem_mes_cheio } } : {}) }
    : { ...comum, valor_causa: config.valor_causa, data_protocolo: config.data_protocolo, indice: config.indice, ...fixacaoHonorarios(escalonar, percentual, faixas) };
}

export function limiteHonorariosAutonomos(base: BaseHonorariosAutonomos, indice: 'ipcae' | 'ipca', cobertura: CoberturaHonorarios | null, original: CriteriosPublicos | null, correta: CriteriosPublicos | null, temCustas: boolean, encargos?: EncargosValorCerto | null): string | undefined {
  const limites = base === 'proveito_economico' ? [original?.data_base_maxima, correta?.data_base_maxima] : base === 'valor_causa' ? [cobertura?.[indice].data_base_maxima] : [];
  if (base === 'valor_certo' && encargos) {
    limites.push(cobertura?.[encargos.indice].data_base_maxima);
    if (encargos.juros === 'taxa_legal') limites.push(cobertura?.taxa_legal?.data_base_maxima);
  }
  if (temCustas) limites.push(cobertura?.ipcae.data_base_maxima || original?.data_base_maxima_ipcae);
  return limites.filter((d): d is string => Boolean(d)).sort()[0];
}
