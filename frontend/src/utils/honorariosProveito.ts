import type { OperacaoDividaHonorarios } from '../services/api';

export function prepararOperacaoDivida(
  operacao: OperacaoDividaHonorarios,
): OperacaoDividaHonorarios {
  if (!operacao.extincao_integral) return operacao;
  return {
    ...operacao,
    data_inicial_juros: null,
    multa_moratoria_percentual: '0',
    parcelas: [],
  };
}
