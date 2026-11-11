import { useReducer, type ReactNode, type Dispatch } from 'react';
import type { CalculoSimplificado } from '../services/api';
import { calculoReducer, initialState, type CalculoState, type CalculoAction, type HonorariosAction } from './calculoReducer';
import { CalculoContext } from './CalculoContextBase';

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
