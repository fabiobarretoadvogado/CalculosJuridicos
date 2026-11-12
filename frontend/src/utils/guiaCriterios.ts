import type { PerfilDescontos } from '../services/api';

type Faixa = { periodo: string; regra: string };
export type GuiaCriterio = { id: PerfilDescontos; nome: string; faixas: Faixa[] };

const antes2009 = { periodo: 'Antes de 01/07/2009', regra: 'Somente correção pelo IPCA-E, desde o início coberto pela base; sem juros nesse período.' };
const poupanca2009 = { periodo: '01/07/2009 a 08/12/2021', regra: 'IPCA-E para correção e juros pela remuneração da poupança.' };
const selic2021 = { periodo: '09/12/2021 a 09/09/2025', regra: 'SELIC como índice único de correção e juros.' };

/** Resumo dos critérios efetivamente implementados; a cobertura é consultada separadamente. */
export const guiaCriterios: GuiaCriterio[] = [
  { id: 'fazenda_publica_1_v1', nome: 'Fazenda Pública 1', faixas: [antes2009,
    { periodo: 'A partir de 01/07/2009', regra: 'IPCA-E para correção e juros pela remuneração da poupança, sem mudança automática de regime.' }] },
  { id: 'fazenda_publica_2_v1', nome: 'Fazenda Pública 2', faixas: [antes2009, poupanca2009,
    { periodo: 'A partir de 09/12/2021', regra: 'SELIC como índice único de correção e juros.' }] },
  { id: 'selic_ipcae_poupanca_v1', nome: 'Fazenda Pública 3', faixas: [antes2009, poupanca2009, selic2021,
    { periodo: 'A partir de 10/09/2025', regra: 'IPCA-E para correção e juros pela remuneração da poupança.' }] },
  { id: 'selic_ipcae_2aa_v1', nome: 'Fazenda Pública 4', faixas: [antes2009, poupanca2009, selic2021,
    { periodo: 'A partir de 10/09/2025', regra: 'IPCA-E mais juros simples de 2% ao ano; o saldo é comparado com a SELIC do mesmo período e prevalece o menor.' }] },
  { id: 'selic_cjf_v1', nome: 'SELIC', faixas: [
    { periodo: 'Conforme as competências disponíveis', regra: 'SELIC simples como índice único de correção e juros. A taxa de cada mês é aplicada no mês seguinte; a referência é mensal.' }] },
  { id: 'ipca_taxa_legal_v1', nome: 'Civil 1', faixas: [
    { periodo: 'Correção: desde o início informado', regra: 'IPCA, respeitada a cobertura da série.' },
    { periodo: 'Juros: a partir de 30/08/2024', regra: 'Taxa Legal oficial do Banco Central, em data própria. Juros anteriores exigem outro critério.' }] },
  { id: 'civil_2_v1', nome: 'Civil 2', faixas: [
    { periodo: 'Correção: desde o início informado', regra: 'IPCA, respeitada a cobertura da série.' },
    { periodo: 'Juros: a partir de 01/07/2009', regra: 'Juros simples de 1% ao mês, proporcionais aos dias, desde a data de juros informada.' }] },
  { id: 'civil_3_v1', nome: 'Civil 3', faixas: [
    { periodo: 'A partir de 01/07/2009', regra: 'INPC para correção e juros simples de 1% ao mês, proporcionais aos dias; os marcos podem ser diferentes.' }] },
  { id: 'civil_4_temporario_v1', nome: 'Civil 4 (temporário)', faixas: [
    { periodo: 'Até 29/08/2024', regra: 'IPCA quando incide só correção; SELIC deduzida do IPCA quando incidem só juros; SELIC integral quando ambos incidem.' },
    { periodo: 'A partir de 30/08/2024', regra: 'IPCA e Taxa Legal oficial, com datas próprias e base consolidada na transição.' }] },
  { id: 'civil_5_taxa_legal_reconstruida_v1', nome: 'Civil 5', faixas: [
    { periodo: 'Até 29/08/2024', regra: 'IPCA e Taxa Legal reconstruída pela metodologia do Banco Central, com datas próprias.' },
    { periodo: 'A partir de 30/08/2024', regra: 'IPCA e Taxa Legal oficial, com datas próprias; juros simples sobre o principal corrigido.' }] },
  { id: 'civil_6_v1', nome: 'Civil 6', faixas: [
    { periodo: 'Até 10/01/2003', regra: 'IPCA e juros simples de 0,5% ao mês, proporcionais aos dias e com datas próprias.' },
    { periodo: '11/01/2003 a 29/08/2024', regra: 'IPCA quando incide só correção; SELIC deduzida do IPCA quando incidem só juros; SELIC integral quando ambos incidem.' },
    { periodo: 'A partir de 30/08/2024', regra: 'IPCA e Taxa Legal oficial, com datas próprias e base consolidada na transição.' }] },
  { id: 'ipcae_1am_simples_v1', nome: 'IPCA-E e juros simples de 1% (uso específico)', faixas: [
    { periodo: '01/01/2010 a 30/09/2022', regra: 'IPCA-E anual por ciclo de outubro a setembro; juros simples de 1% por período completo de 30 dias.' },
    { periodo: 'A partir de 01/10/2022', regra: 'IPCA-E mensal; juros simples de 1% por período completo de 30 dias.' }] },
  { id: 'poupanca_deposito_v1', nome: 'Depósitos pela poupança (descontos)', faixas: [
    { periodo: 'Conforme a cobertura da série', regra: 'Remuneração da conta por aniversários mensais completos, sem IPCA, SELIC ou juros de mora adicionais.' }] },
];
