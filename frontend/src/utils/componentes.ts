import type { ComponenteCalculo, ResultadoCalculo } from '../services/api';

export const componentes = [
  { chave: 'ipcae_pre', nome: 'IPCA-E pré EC 113/2021', periodo: 'Até 08/12/2021' },
  { chave: 'poupanca_pre', nome: 'Poupança pré EC 113/2021', periodo: 'Até 08/12/2021' },
  { chave: 'selic', nome: 'SELIC única', periodo: '09/12/2021 a 09/09/2025' },
  { chave: 'ipcae_pos', nome: 'IPCA-E pós EC 136/2025', periodo: 'Desde 10/09/2025' },
  { chave: 'poupanca_pos', nome: 'Poupança pós EC 136/2025', periodo: 'Desde 10/09/2025' },
] as const;

const componentesEC136 = [
  { chave: 'ipcae_pre', nome: 'IPCA-E', periodo: 'Até 08/12/2021' },
  { chave: 'poupanca_pre', nome: 'Poupança', periodo: 'Até 08/12/2021' },
  { chave: 'selic', nome: 'SELIC única', periodo: '09/12/2021 a 09/09/2025' },
  { chave: 'ipcae_pos', nome: 'IPCA-E pós EC 136/2025', periodo: 'Desde 10/09/2025' },
  { chave: 'juros_2aa', nome: 'Juros 2% a.a. pós EC 136/2025', periodo: 'Desde 10/09/2025' },
  { chave: 'limite_selic', nome: 'Ajuste ao limite SELIC', periodo: 'Desde 10/09/2025' },
] as const;

export function componentesResultado(r: ResultadoCalculo) {
  const colunas = componentesPerfil(r);
  return 'multa_parcela' in r.resumo.totais_componentes
    ? [...colunas, { chave: 'multa_parcela', nome: 'Multa e encargos', periodo: 'Por parcela' }]
    : colunas;
}

export function componentesPerfil(r: ResultadoCalculo) {
  if (r.premissas.entrada.perfil === 'poupanca_deposito_v1') return [
    { chave: 'poupanca_deposito', nome: 'Poupança — remuneração da conta', periodo: 'Aniversários completos' },
  ];
  if (r.premissas.entrada.perfil === 'ipca_taxa_legal_v1') return [
    { chave: 'ipca', nome: 'IPCA', periodo: 'Desde o início da correção' },
    { chave: 'taxa_legal', nome: 'Taxa Legal', periodo: 'Desde o início dos juros' },
  ];
  if (r.premissas.entrada.perfil === 'civil_2_v1') return [
    { chave: 'ipca', nome: 'IPCA', periodo: 'Desde o início da correção' },
    { chave: 'juros_1am', nome: 'Juros simples de 1% a.m.', periodo: 'Desde o início dos juros' },
  ];
  if (r.premissas.entrada.perfil === 'ipcae_1am_simples_v1') return [
    { chave: 'ipcae', nome: 'IPCA-E', periodo: 'Até a data-base' },
    { chave: 'juros_1am', nome: 'Juros simples de 1% a.m.', periodo: 'Até a data-base' },
  ];
  if (r.premissas.entrada.perfil === 'selic_cjf_v1') return [{ chave: 'selic', nome: 'SELIC', periodo: 'Até a data-base' }];
  if (r.premissas.entrada.perfil === 'fazenda_publica_1_v1') return [
    { chave: 'ipcae_pre', nome: 'IPCA-E', periodo: 'Desde 01/07/2009' },
    { chave: 'poupanca_pre', nome: 'Poupança', periodo: 'Desde 01/07/2009' },
  ];
  if (r.premissas.entrada.perfil === 'fazenda_publica_2_v1') return [
    { chave: 'ipcae_pre', nome: 'IPCA-E', periodo: 'Até 08/12/2021' },
    { chave: 'poupanca_pre', nome: 'Poupança', periodo: 'Até 08/12/2021' },
    { chave: 'selic', nome: 'SELIC única', periodo: 'Desde 09/12/2021' },
  ];
  if (r.premissas.entrada.perfil !== 'selic_ipcae_2aa_v1') return componentes;
  return componentesEC136;
}

export function indiceAcumulado(c: ComponenteCalculo, casas = 4) {
  const formatar = (v: string) => Number(v).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
  return c.fator_acumulado !== null ? `Fator ${formatar(c.fator_acumulado)}` : `${formatar(c.taxa_acumulada_percentual || '0')}%`;
}

export function memoriaExibida(texto: string) {
  return texto.replace(/-?\d+\.\d{5,}/g, valor => Number(valor).toFixed(4));
}
