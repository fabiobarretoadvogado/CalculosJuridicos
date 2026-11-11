import { numerarParcelas } from '../utils/reordenarParcelas';
import type { CalculoSimplificado, CustaDespesaProcessual, ParcelaSimplificada, ResultadoCalculo, HonorariosPrincipais, CumprimentoSentenca } from '../services/api';

export interface CalculoState {
  perfil: CalculoSimplificado['perfil'];
  dadosGerais: CalculoSimplificado['dados_gerais'];
  parcelas: ParcelaSimplificada[];
  descontos: CalculoSimplificado['descontos'];
  custasDespesas: CustaDespesaProcessual[];
  honorariosSucumbenciais: HonorariosPrincipais;
  cumprimentoSentenca: CumprimentoSentenca;
  resultado: ResultadoCalculo | null;
}
export type CalculoAction =
  | { type: 'LOAD_CALCULO'; payload: CalculoSimplificado }
  | { type: 'SET_PERFIL'; payload: CalculoSimplificado['perfil'] }
  | { type: 'SET_DADOS_GERAIS'; payload: CalculoState['dadosGerais'] }
  | { type: 'SET_PARCELAS'; payload: ParcelaSimplificada[] }
  | { type: 'SET_DESCONTOS'; payload: CalculoState['descontos'] }
  | { type: 'SET_CUSTAS_DESPESAS'; payload: CustaDespesaProcessual[] }
  | { type: 'SET_RESULTADO'; payload: ResultadoCalculo | null };
export type HonorariosAction =
  | { type: 'SET_HONORARIOS'; payload: HonorariosPrincipais }
  | { type: 'SET_CUMPRIMENTO'; payload: CumprimentoSentenca };
export const initialState: CalculoState = {
  perfil: 'selic_ipcae_poupanca_v1',
  dadosGerais: { data_base: '', processo: '', classe: '', requerente: '', requerido: '', comarca: '', vara: '', observacoes: '', criterio_inicio_juros: 'vencimento', data_inicial_juros: null },
  parcelas: [], custasDespesas: [], resultado: null,
  descontos: { perfil: null, criterio_inicio_juros: 'vencimento', data_inicial_juros: null, itens: [] },
  honorariosSucumbenciais: { aplicar: false, base: 'proveito_economico', percentual: null, valor_causa: null, data_protocolo: null, indice: 'ipcae', valor_certo: null },
  cumprimentoSentenca: { aplicar_multa: false, aplicar_honorarios: false, destacar_contratuais: false, percentual_contratuais: null, base_contratuais: 'credito_parte' },
};
export function calculoReducer(state: CalculoState, action: CalculoAction | HonorariosAction): CalculoState {
  switch (action.type) {
    case 'LOAD_CALCULO': return {
      ...initialState,
      perfil: action.payload.perfil,
      dadosGerais: action.payload.dados_gerais,
      parcelas: numerarParcelas(action.payload.parcelas),
      descontos: action.payload.descontos || initialState.descontos,
      custasDespesas: action.payload.custas_despesas || [],
      honorariosSucumbenciais: action.payload.honorarios_sucumbenciais || initialState.honorariosSucumbenciais,
      cumprimentoSentenca: action.payload.cumprimento_sentenca || initialState.cumprimentoSentenca,
      resultado: null,
    };
    case 'SET_PERFIL': return { ...state, perfil: action.payload, resultado: null,
      dadosGerais: action.payload === 'selic_cjf_v1' ? { ...state.dadosGerais, criterio_inicio_juros: 'vencimento' } : state.dadosGerais };
    case 'SET_DADOS_GERAIS': return { ...state, dadosGerais: action.payload, resultado: null };
    case 'SET_PARCELAS': return { ...state, parcelas: numerarParcelas(action.payload), resultado: null };
    case 'SET_DESCONTOS': return { ...state, descontos: action.payload, resultado: null };
    case 'SET_CUSTAS_DESPESAS': return { ...state, custasDespesas: action.payload, resultado: null };
    case 'SET_RESULTADO': return { ...state, resultado: action.payload };
    case 'SET_HONORARIOS': return { ...state, honorariosSucumbenciais: action.payload, resultado: null };
    case 'SET_CUMPRIMENTO': return { ...state, cumprimentoSentenca: action.payload, resultado: null };
  }
}
