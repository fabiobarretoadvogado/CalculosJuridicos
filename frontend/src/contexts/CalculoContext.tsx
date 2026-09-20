import { useReducer, type ReactNode, type Dispatch } from 'react';
import type { CalculoSimplificado, CustaDespesaProcessual, ParcelaSimplificada, ResultadoCalculo, HonorariosPrincipais, CumprimentoSentenca } from '../services/api';
import { CalculoContext } from './CalculoContextBase';

interface CalculoState {
  perfil: CalculoSimplificado['perfil'];
  dadosGerais: CalculoSimplificado['dados_gerais'];
  parcelas: ParcelaSimplificada[];
  descontos: CalculoSimplificado['descontos'];
  custasDespesas: CustaDespesaProcessual[];
  honorariosSucumbenciais: HonorariosPrincipais;
  cumprimentoSentenca: CumprimentoSentenca;
  resultado: ResultadoCalculo | null;
}
type CalculoAction =
  | { type: 'SET_PERFIL'; payload: CalculoSimplificado['perfil'] }
  | { type: 'SET_DADOS_GERAIS'; payload: CalculoState['dadosGerais'] }
  | { type: 'SET_PARCELAS'; payload: ParcelaSimplificada[] }
  | { type: 'SET_DESCONTOS'; payload: CalculoState['descontos'] }
  | { type: 'SET_CUSTAS_DESPESAS'; payload: CustaDespesaProcessual[] }
  | { type: 'SET_RESULTADO'; payload: ResultadoCalculo | null };
type HonorariosAction =
  | { type: 'SET_HONORARIOS'; payload: HonorariosPrincipais }
  | { type: 'SET_CUMPRIMENTO'; payload: CumprimentoSentenca };
const initialState: CalculoState = {
  perfil: 'selic_ipcae_poupanca_v1',
  dadosGerais: { data_base: '', processo: '', classe: '', requerente: '', requerido: '', comarca: '', vara: '', observacoes: '', criterio_inicio_juros: 'vencimento', data_inicial_juros: null },
  parcelas: [], custasDespesas: [], resultado: null,
  descontos: { perfil: null, criterio_inicio_juros: 'vencimento', data_inicial_juros: null, itens: [] },
  honorariosSucumbenciais: { aplicar: false, base: 'proveito_economico', percentual: null, valor_causa: null, data_protocolo: null, indice: 'ipcae', valor_certo: null },
  cumprimentoSentenca: { aplicar_multa: false, aplicar_honorarios: false, destacar_contratuais: false, percentual_contratuais: null, base_contratuais: 'credito_parte' },
};
function calculoReducer(state: CalculoState, action: CalculoAction | HonorariosAction): CalculoState {
  switch (action.type) {
    case 'SET_PERFIL': return { ...state, perfil: action.payload, resultado: null,
      dadosGerais: action.payload === 'selic_cjf_v1' ? { ...state.dadosGerais, criterio_inicio_juros: 'vencimento' } : state.dadosGerais };
    case 'SET_DADOS_GERAIS': return { ...state, dadosGerais: action.payload, resultado: null };
    case 'SET_PARCELAS': return { ...state, parcelas: action.payload, resultado: null };
    case 'SET_DESCONTOS': return { ...state, descontos: action.payload, resultado: null };
    case 'SET_CUSTAS_DESPESAS': return { ...state, custasDespesas: action.payload, resultado: null };
    case 'SET_RESULTADO': return { ...state, resultado: action.payload };
    case 'SET_HONORARIOS': return { ...state, honorariosSucumbenciais: action.payload, resultado: null };
    case 'SET_CUMPRIMENTO': return { ...state, cumprimentoSentenca: action.payload, resultado: null };
  }
}
export interface CalculoContextValue {
  state: CalculoState;
  dispatch: Dispatch<CalculoAction | HonorariosAction>;
  buildCalculoJudicial: () => CalculoSimplificado;
}
export function CalculoProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(calculoReducer, initialState);
  return <CalculoContext.Provider value={{ state, dispatch, buildCalculoJudicial: () => ({
    perfil: state.perfil, dados_gerais: state.dadosGerais, parcelas: state.parcelas,
    custas_despesas: state.custasDespesas,
    descontos: { ...state.descontos, itens: state.descontos.itens.map(item => ({ ...item,
      data: item.data || null, valor: item.valor || null, encargos_sem_atualizacao: item.encargos_sem_atualizacao || '0',
    })) },
    honorarios_sucumbenciais: { ...state.honorariosSucumbenciais,
      percentual: state.honorariosSucumbenciais.aplicar && state.honorariosSucumbenciais.base !== 'valor_certo' ? state.honorariosSucumbenciais.percentual : null,
      valor_causa: state.honorariosSucumbenciais.aplicar && state.honorariosSucumbenciais.base === 'valor_causa' ? state.honorariosSucumbenciais.valor_causa : null,
      data_protocolo: state.honorariosSucumbenciais.aplicar && state.honorariosSucumbenciais.base === 'valor_causa' ? state.honorariosSucumbenciais.data_protocolo : null,
      valor_certo: state.honorariosSucumbenciais.aplicar && state.honorariosSucumbenciais.base === 'valor_certo' ? state.honorariosSucumbenciais.valor_certo : null,
    },
    cumprimento_sentenca: {
      aplicar_multa: state.cumprimentoSentenca.aplicar_multa,
      aplicar_honorarios: state.cumprimentoSentenca.aplicar_honorarios,
      destacar_contratuais: state.cumprimentoSentenca.destacar_contratuais,
      base_contratuais: state.cumprimentoSentenca.base_contratuais,
      percentual_contratuais: state.cumprimentoSentenca.destacar_contratuais ? state.cumprimentoSentenca.percentual_contratuais : null,
    },
  }) }}>{children}</CalculoContext.Provider>;
}
