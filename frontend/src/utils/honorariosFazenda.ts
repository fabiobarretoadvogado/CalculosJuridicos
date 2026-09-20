import type { CalculoHonorariosProveito, EscalonamentoFazendaHonorarios } from '../services/api';

export const FAIXAS_FAZENDA = [
  { nome: 'Até 200 SM', min: 10, max: 20 },
  { nome: 'Acima de 200 até 2.000 SM', min: 8, max: 10 },
  { nome: 'Acima de 2.000 até 20.000 SM', min: 5, max: 8 },
  { nome: 'Acima de 20.000 até 100.000 SM', min: 3, max: 5 },
  { nome: 'Acima de 100.000 SM', min: 1, max: 3 },
];

export const escalonamentoInicial = (): EscalonamentoFazendaHonorarios => ({
  salario_minimo: '', marco: 'sentenca_liquida', data_decisao: '',
  percentuais_faixas: FAIXAS_FAZENDA.map(faixa => String(faixa.min)),
});

export function fixacaoHonorarios(escalonar: boolean, percentual: string, config: EscalonamentoFazendaHonorarios): Pick<CalculoHonorariosProveito, 'percentual_sentenca' | 'escalonamento_fazenda'> {
  return escalonar ? { percentual_sentenca: null, escalonamento_fazenda: { ...config, percentuais_faixas: [...config.percentuais_faixas] } } : { percentual_sentenca: percentual, escalonamento_fazenda: null };
}
