import axios from 'axios';

const API_BASE_URL = '/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface DadosGerais {
  data_base: string;
  processo: string;
  classe: string;
  requerente: string;
  requerido: string;
  tipo_devedor: 'fazenda_publica';
  comarca: string;
  vara: string;
  contrato: string;
  observacoes: string;
  criterio_inicio_juros: CriterioInicioJuros;
  data_inicial_juros: string | null;
}

export interface ResumoGeral {
  totais_componentes: Record<string, string>;
  principal_original: string;
  valor_pago_na_data_parcelas: string;
  principal_apurado: string;
  correcao_monetaria: string;
  juros_mora: string;
  multas: string;
  honorarios: string;
  custas: string;
  despesas: string;
  abatimentos: string;
  total_atualizado: string;
}

export interface MemoriaMensal {
  parcela: number;
  competencia: string;
  valor_base: string;
  indice_aplicado: string;
  fator_aplicado: string;
  valor_corrigido: string;
  juros_periodo: string;
  juros_acumulados: string;
  multa: string;
  total: string;
  observacao: string;
}

export interface ComponenteCalculo {
  data_inicial: string | null;
  data_final: string | null;
  base_calculo: string;
  fator_acumulado: string | null;
  taxa_acumulada_percentual: string | null;
  valor: string;
}

export interface ResultadoParcela {
  multa_detalhes?: {
    percentual: string;
    base_calculo: string;
    valor_original: string;
    correcao_monetaria: string;
    juros_mora: string;
    total_atualizado: string;
    componentes: Record<string, ComponenteCalculo>;
    memoria: MemoriaMensal[];
  } | null;
  componentes: Record<string, ComponenteCalculo>;
  numero: number;
  natureza: string;
  historico: string;
  data_vencimento: string | null;
  valor_bruto: string;
  valor_pago_na_data: string;
  valor_apurado: string;
  correcao_monetaria: string;
  valor_corrigido: string;
  juros_mora: string;
  multa: string;
  total_parcela: string;
  memoria_correcao: MemoriaMensal[];
  memoria_juros: MemoriaMensal[];
  alertas: string[];
}

export interface PremissasCalculo {
  selecao_descontos?: Desconto[];
  composicao_pagamentos?: Desconto[];
  data_referencia_selic?: string;
  ultima_competencia_selic?: string | null;
  criterios: string[];
  metodologia: string[];
  contagem: string;
  fontes: Record<string, string>;
  atualizado_em: string;
  entrada: Omit<CalculoSimplificado, 'perfil'> & { perfil: PerfilDescontos };
  sha256_base: string;
}

export interface ResultadoCalculo {
  chave_recuperacao?: string | null;
  honorarios_sucumbenciais?: ResultadoHonorariosPrincipais | null;
  cumprimento_sentenca?: ResultadoCumprimentoSentenca | null;
  destaque_contratuais?: ResultadoDestaqueContratuais | null;
  descontos?: ResultadoCalculo | null;
  dados_gerais: DadosGerais;
  resumo: ResumoGeral;
  parcelas: ResultadoParcela[];
  custas_despesas: ResultadoCustaDespesaProcessual[];
  memoria_mensal: MemoriaMensal[];
  alertas: string[];
  premissas: PremissasCalculo;
}

// ---------------------------------------------------------------------------
// Funções de API
// ---------------------------------------------------------------------------

export const executarCalculo = async (calculo: CalculoSimplificado): Promise<ResultadoCalculo> => {
  const response = await api.post<ResultadoCalculo>('/calculo', calculo);
  return response.data;
};

export const exportarExcel = async (calculo: CalculoSimplificado): Promise<Blob> => {
  const response = await api.post('/calculo/exportar/excel', calculo, {
    responseType: 'blob',
  });
  return response.data;
};

export const exportarPdf = async (calculo: CalculoSimplificado): Promise<Blob> => {
  const response = await api.post('/calculo/exportar/pdf', calculo, { responseType: 'blob' });
  return response.data;
};

export const exportarCsv = async (calculo: CalculoSimplificado): Promise<Blob> => {
  const response = await api.post('/calculo/exportar/csv', calculo, {
    responseType: 'blob',
  });
  return response.data;
};

export const obterIndices = async (): Promise<string[]> => {
  const response = await api.get<{ indices: string[] }>('/indices');
  return response.data.indices;
};

export const obterTemplateModelo = async (): Promise<Blob> => {
  const response = await api.get('/parcelas/modelo', {
    responseType: 'blob',
  });
  return response.data;
};

export const importarExcel = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/parcelas/importar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const checkApiHealth = async () => {
  const response = await api.get('/');
  return response.data;
};

export interface AppInfo {
  nome: string;
  versao: string;
  edicao: string;
  empacotado: boolean;
  atualizacoes_configuradas: boolean;
  repositorio: string;
  acesso: 'public' | 'private';
}

export interface AtualizacaoDisponivel {
  disponivel: boolean;
  versao_atual: string;
  nova_versao?: string;
  nova_edicao?: string;
  notas?: string;
}

export const obterInformacoesApp = async (): Promise<AppInfo> => (
  await api.get<AppInfo>('/app/info')
).data;

export const verificarAtualizacao = async (): Promise<AtualizacaoDisponivel> => (
  await api.get<AtualizacaoDisponivel>('/app/atualizacoes')
).data;

export const baixarAtualizacao = async (): Promise<{ pronta: boolean; edicao: string }> => (
  await api.post('/app/atualizacoes/baixar')
).data;

export const instalarAtualizacao = async (): Promise<{ iniciada: boolean }> => (
  await api.post('/app/atualizacoes/instalar')
).data;
export interface ParcelaSimplificada {
  multa_percentual?: string;
  numero: number;
  historico: string;
  data_vencimento: string;
  valor_bruto: string;
  valor_pago_na_data: string;
  data_inicial_juros: string | null;
}
export type PerfilCalculo = 'fazenda_publica_1_v1' | 'fazenda_publica_2_v1' | 'selic_ipcae_poupanca_v1' | 'selic_ipcae_2aa_v1' | 'selic_cjf_v1' | 'ipcae_1am_simples_v1' | 'ipca_taxa_legal_v1' | 'civil_2_v1';
export type PerfilDescontos = PerfilCalculo | 'poupanca_deposito_v1';
export type CriterioInicioJuros = 'vencimento' | 'citacao' | 'data_fixa' | 'por_parcela';
export interface Desconto {
  numero: number;
  aplicar?: boolean;
  encargos_sem_atualizacao?: string;
  descricao: string;
  data: string | null;
  valor: string | null;
}
export interface OperacaoDescontos {
  perfil: PerfilDescontos | null;
  criterio_inicio_juros: 'vencimento' | 'citacao' | 'data_fixa';
  data_inicial_juros: string | null;
  itens: Desconto[];
}
export interface CalculoSimplificado {
  honorarios_sucumbenciais?: HonorariosPrincipais;
  cumprimento_sentenca?: CumprimentoSentenca;
  perfil: PerfilCalculo;
  dados_gerais: Omit<DadosGerais, 'tipo_devedor' | 'contrato'>;
  parcelas: ParcelaSimplificada[];
  descontos: OperacaoDescontos;
  custas_despesas: CustaDespesaProcessual[];
}
export interface CriteriosPublicos {
  data_referencia_selic_maxima?: string;
  ultima_competencia_selic_disponivel?: string;
  perfil: PerfilDescontos;
  perfis: { id: CalculoSimplificado['perfil']; nome: string }[];
  inicio: string;
  inicio_selic: string;
  transicao: string;
  data_base_maxima: string;
  data_base_maxima_ipcae: string;
  atualizado_em: string;
  fontes: Record<string, string>;
  contagem: string;
}
export const obterCriterios = async (perfil: PerfilDescontos = 'selic_ipcae_poupanca_v1'): Promise<CriteriosPublicos> => (await api.get('/criterios', { params: { perfil } })).data;

export interface DadosHonorarios {
  data_base: string;
  processo: string;
  classe: string;
  requerente: string;
  requerido: string;
  comarca: string;
  vara: string;
  observacoes: string;
}
export interface HonorariosPrincipais {
  aplicar: boolean;
  base: 'valor_causa' | 'proveito_economico' | 'valor_certo';
  percentual: string | null;
  valor_causa: string | null;
  data_protocolo: string | null;
  indice: 'ipcae' | 'ipca';
  valor_certo: string | null;
}
export interface CumprimentoSentenca {
  aplicar_multa: boolean;
  aplicar_honorarios: boolean;
  destacar_contratuais: boolean;
  percentual_contratuais: string | null;
  base_contratuais: 'credito_parte' | 'total_sem_custas';
}
export interface ResultadoHonorariosPrincipais {
  base: HonorariosPrincipais['base']; descricao_base: string;
  percentual: string | null; valor_original: string; data_protocolo: string | null;
  indice: string | null; fator_acumulado: string; correcao_monetaria: string;
  base_atualizada: string; valor: string; memoria: MemoriaMensal[]; fonte: string;
}
export interface ResultadoCumprimentoSentenca {
  credito_parte: string; sucumbenciais_na_base: string; base_calculo: string;
  percentual_multa: string; percentual_honorarios: string; multa: string; honorarios: string;
  aplicar_multa: boolean; aplicar_honorarios: boolean;
}
export interface ResultadoDestaqueContratuais {
  base: string; descricao_base: string; base_calculo: string; percentual: string; valor: string;
  saldo_apos_destaque: string; acresce_total: boolean;
}
export interface CoberturaHonorarios {
  inicio: string;
  ipcae: { data_base_maxima: string; fonte: string };
  ipca: { data_base_maxima: string; fonte: string };
  taxa_legal?: { inicio: string; data_base_maxima: string; fonte: string };
}
export const obterCoberturaHonorarios = async (): Promise<CoberturaHonorarios> => (
  await api.get('/honorarios/criterios-correcao')
).data;

export interface ParcelaDividaHonorarios {
  numero: number;
  historico: string;
  data_origem: string;
  valor: string;
}

export interface OperacaoDividaHonorarios {
  perfil: PerfilCalculo;
  criterio_inicio_juros: CriterioInicioJuros;
  data_inicial_juros: string | null;
  multa_moratoria_percentual: string;
  extincao_integral?: boolean;
  parcelas: ParcelaDividaHonorarios[];
}

export interface EscalonamentoFazendaHonorarios {
  salario_minimo: string;
  marco: 'sentenca_liquida' | 'decisao_liquidacao';
  data_decisao: string;
  percentuais_faixas: string[];
}

export interface ResultadoEscalonamentoFazenda extends EscalonamentoFazendaHonorarios {
  base_calculo: string;
  percentual_efetivo: string;
  valor_total: string;
  fonte: string;
  faixas: {
    ordem: number;
    limite_inferior_salarios_minimos: string;
    limite_salarios_minimos: string | null;
    percentual_minimo: string;
    percentual_maximo: string;
    percentual_aplicado: string;
    valor_incidente: string;
    valor: string;
  }[];
}

export interface CalculoHonorariosProveito {
  categoria: 'honorarios_sucumbenciais_proveito_economico';
  dados_gerais: DadosHonorarios;
  divida_original: OperacaoDividaHonorarios;
  divida_correta: OperacaoDividaHonorarios;
  custas_despesas: CustaDespesaProcessual[];
  percentual_sentenca: string | null;
  escalonamento_fazenda?: EscalonamentoFazendaHonorarios | null;
}

export interface ResultadoOperacaoDivida {
  rotulo: string;
  perfil: PerfilCalculo;
  nome_perfil: string;
  quantidade_parcelas: number;
  valor_informado: string;
  encargos_apurados: string;
  valor_atualizado: string;
  parcelas: ResultadoParcelaDivida[];
  componentes: Record<string, ComponenteCalculo>;
  memoria_mensal: MemoriaMensal[];
  criterios: string[];
  metodologia: string[];
  fontes: Record<string, string>;
  premissas: Record<string, unknown>;
}

export interface ResultadoParcelaDivida {
  numero: number;
  historico: string;
  data_origem: string;
  valor_informado: string;
  encargos_apurados: string;
  valor_atualizado: string;
  componentes: Record<string, ComponenteCalculo>;
}

export interface ResultadoHonorariosProveito {
  chave_recuperacao?: string | null;
  categoria: CalculoHonorariosProveito['categoria'];
  dados_gerais: DadosHonorarios;
  divida_original: ResultadoOperacaoDivida;
  divida_correta: ResultadoOperacaoDivida;
  diferenca_atualizada: string;
  proveito_economico: string;
  percentual_sentenca: string | null;
  escalonamento_fazenda?: ResultadoEscalonamentoFazenda | null;
  honorarios_sucumbenciais: string;
  custas_despesas: ResultadoCustaDespesaProcessual[];
  custas_despesas_valor_original: string;
  custas_despesas_correcao: string;
  custas_despesas_valor_atualizado: string;
  total_geral: string;
  fontes_custas_despesas: Record<string, string>;
  formula: string;
  alertas: string[];
}

export type BaseHonorariosAutonomos = 'proveito_economico' | 'valor_causa' | 'valor_certo';
export interface EncargosValorCerto {
  data_fixacao: string;
  indice: 'ipcae' | 'ipca';
  juros: 'simples' | 'taxa_legal' | 'sem_juros';
  data_inicio_juros: string | null;
  percentual_mensal: string | null;
  contagem_mes_cheio: boolean;
}
export interface CalculoHonorariosIsolados {
  categoria: 'honorarios_sucumbenciais_isolados';
  dados_gerais: DadosHonorarios;
  base: 'valor_causa' | 'valor_certo';
  valor_causa?: string | null;
  data_protocolo?: string | null;
  indice?: 'ipcae' | 'ipca' | null;
  valor_certo?: string | null;
  encargos_valor_certo?: EncargosValorCerto | null;
  percentual_sentenca: string | null;
  escalonamento_fazenda?: EscalonamentoFazendaHonorarios | null;
  custas_despesas: CustaDespesaProcessual[];
}
export interface ResultadoHonorariosIsolados extends Omit<ResultadoHonorariosProveito, 'categoria' | 'divida_original' | 'divida_correta' | 'diferenca_atualizada' | 'proveito_economico'> {
  categoria: 'honorarios_sucumbenciais_isolados';
  base: 'valor_causa' | 'valor_certo';
  apuracao: ResultadoHonorariosPrincipais;
  atualizacao_valor_certo?: ResultadoParcela | null;
  premissas: { criterios: string[]; metodologia: string[]; fontes: Record<string, string> };
}

export const executarHonorariosIsolados = async (calculo: CalculoHonorariosIsolados): Promise<ResultadoHonorariosIsolados> => (
  await api.post<ResultadoHonorariosIsolados>('/honorarios/isolados', calculo)
).data;
export const exportarPdfHonorariosIsolados = async (calculo: CalculoHonorariosIsolados): Promise<Blob> => (
  await api.post('/honorarios/isolados/exportar/pdf', calculo, { responseType: 'blob' })
).data;

export interface CustaDespesaProcessual {
  numero: number;
  nome: string;
  data: string;
  valor: string;
}

export interface ResultadoCustaDespesaProcessual {
  numero: number;
  nome: string;
  data: string;
  valor_original: string;
  fator_ipcae: string;
  correcao_monetaria: string;
  valor_atualizado: string;
  memoria: MemoriaMensal[];
}

export const executarHonorariosProveito = async (
  calculo: CalculoHonorariosProveito,
): Promise<ResultadoHonorariosProveito> => (
  await api.post<ResultadoHonorariosProveito>('/honorarios/proveito-economico', calculo)
).data;

export const exportarPdfHonorarios = async (
  calculo: CalculoHonorariosProveito,
): Promise<Blob> => (
  await api.post('/honorarios/proveito-economico/exportar/pdf', calculo, { responseType: 'blob' })
).data;

export interface CalculoRecuperado {
  chave_recuperacao: string;
  categoria: 'calculo_principal' | 'honorarios_sucumbenciais_proveito_economico' | 'honorarios_sucumbenciais_isolados';
  schema_version: number;
  versao_aplicativo: string;
  criado_em: string;
  entrada: CalculoSimplificado | CalculoHonorariosProveito | CalculoHonorariosIsolados;
}

export const recuperarCalculo = async (chave: string): Promise<CalculoRecuperado> => (
  await api.get<CalculoRecuperado>(`/calculos/${encodeURIComponent(chave.trim())}`)
).data;

export async function mensagemErro(erro: unknown): Promise<string> {
  if (axios.isAxiosError(erro)) {
    let data = erro.response?.data;
    if (data instanceof Blob) {
      try { data = JSON.parse(await data.text()); } catch { return 'Não foi possível gerar o arquivo.'; }
    }
    if (Array.isArray(data?.detail)) return data.detail.map((d: { msg: string }) => d.msg).join('\n');
    return data?.detail || data?.erros?.join('\n') || 'Não foi possível conectar ao serviço de cálculo. Verifique se ele está em execução.';
  }
  return erro instanceof Error ? erro.message : 'Não foi possível concluir a operação.';
}
