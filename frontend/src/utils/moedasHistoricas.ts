const PADROES = [
  ['1970-05-15', 'Cr$', 2_750_000_000_000],
  ['1986-02-28', 'Cz$', 2_750_000_000],
  ['1989-01-16', 'NCz$', 2_750_000],
  ['1990-03-16', 'Cr$', 2_750_000],
  ['1993-08-01', 'CR$', 2_750],
  ['1994-07-01', 'R$', 1],
] as const;

function padrao(data?: string | null) {
  return data ? [...PADROES].reverse().find(item => data >= item[0]) || PADROES[0] : PADROES.at(-1)!;
}

export const simboloMoeda = (data?: string | null) => padrao(data)[1];
export const equivalenteNominalReais = (valor: string | number | null, data?: string | null) => (Number(valor) || 0) / padrao(data)[2];
export const inicioIndice = (indice: 'ipca' | 'ipcae') => indice === 'ipca' ? '1980-01-01' : '1992-01-01';
export const notaMoeda = (data?: string | null) => data && data < '1994-07-01'
  ? `Informe o valor em ${simboloMoeda(data)}, moeda da data de origem. O resultado será convertido para reais; a conversão fica na memória.`
  : undefined;
export const formatarValorOrigem = (valor: number, data: string) => `${simboloMoeda(data)}\u00a0${valor.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
