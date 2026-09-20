import { useEffect, useState, type FormEvent } from 'react';
import { Calculator, Download, Plus, RotateCcw, Trash2 } from 'lucide-react';
import { Button, Input, Select, Textarea } from '../components/ui';
import {
  executarHonorariosProveito,
  executarHonorariosIsolados,
  exportarPdfHonorarios,
  exportarPdfHonorariosIsolados,
  mensagemErro,
  obterCriterios,
  obterCoberturaHonorarios,
  type BaseHonorariosAutonomos,
  type CalculoHonorariosIsolados,
  type CoberturaHonorarios,
  type HonorariosPrincipais,
  type ResultadoHonorariosIsolados,
  type CalculoHonorariosProveito,
  type CustaDespesaProcessual,
  type CriterioInicioJuros,
  type CriteriosPublicos,
  type OperacaoDividaHonorarios,
  type ParcelaDividaHonorarios,
  type PerfilCalculo,
  type ResultadoHonorariosProveito,
  type ResultadoOperacaoDivida,
} from '../services/api';
import { downloadBlob, formatarData, formatarMoeda, formatarPercentual } from '../utils/formatters';
import { CustasDespesasForm } from '../components/CustasDespesasForm';
import { CustasDespesasResultado } from '../components/CustasDespesasResultado';
import { EscalonamentoFazendaForm, EscalonamentoFazendaResultado } from '../components/EscalonamentoFazendaHonorarios';
import { escalonamentoInicial, fixacaoHonorarios } from '../utils/honorariosFazenda';
import { detalhesLimiteHonorariosAutonomos, montarHonorariosIsolados, encargosValorCertoIniciais } from '../utils/honorariosIsolados';
import { mensagemCoberturaSelecionada } from '../utils/coberturaIndices';
import { HonorariosCausaCampos } from '../components/HonorariosPrincipaisForm';
import { HonorariosPrincipaisResultado } from '../components/HonorariosPrincipaisResultado';
import { HonorariosValorCertoCampos, HonorariosValorCertoResultado } from '../components/HonorariosValorCerto';
import { opcoesPerfisCalculo } from '../utils/perfisCalculo';
import { prepararOperacaoDivida } from '../utils/honorariosProveito';

const JUROS: { value: CriterioInicioJuros; label: string }[] = [
  { value: 'vencimento', label: 'Data de origem de cada item' },
  { value: 'citacao', label: 'Citação' },
  { value: 'data_fixa', label: 'Data específica' },
];

const parcelaInicial = (numero: number): ParcelaDividaHonorarios => ({
  numero,
  historico: '',
  data_origem: '',
  valor: '',
});

const operacaoInicial = (): OperacaoDividaHonorarios => ({
  perfil: 'selic_ipcae_poupanca_v1',
  criterio_inicio_juros: 'vencimento',
  data_inicial_juros: null,
  multa_moratoria_percentual: '0',
  extincao_integral: false,
  parcelas: [parcelaInicial(1)],
});

const dadosIniciais = () => ({
  data_base: '', processo: '', classe: '', requerente: '', requerido: '',
  comarca: '', vara: '', observacoes: '',
});

type CampoOperacao = Exclude<keyof OperacaoDividaHonorarios, 'parcelas'>;
type CampoParcela = Exclude<keyof ParcelaDividaHonorarios, 'numero'>;

function OperacaoForm({
  titulo,
  descricao,
  prefixo,
  operacao,
  criterios,
  perfis,
  dataBase,
  onChange,
  onParcelaChange,
  onAdicionar,
  onRemover,
  permiteExtincao = false,
}: {
  titulo: string;
  descricao: string;
  prefixo: string;
  operacao: OperacaoDividaHonorarios;
  criterios: CriteriosPublicos | null;
  perfis: { value: PerfilCalculo; label: string }[];
  dataBase: string;
  onChange: (campo: CampoOperacao, valor: string | boolean | null) => void;
  onParcelaChange: (indice: number, campo: CampoParcela, valor: string) => void;
  onAdicionar: () => void;
  onRemover: (indice: number) => void;
  permiteExtincao?: boolean;
}) {
  const extinta = permiteExtincao && operacao.extincao_integral === true;
  const cjf = operacao.perfil === 'selic_cjf_v1';
  const datasIndependentes = ['ipca_taxa_legal_v1', 'civil_2_v1'].includes(operacao.perfil);
  const exigeDataJuros = ['citacao', 'data_fixa'].includes(operacao.criterio_inicio_juros);
  const quantidade = extinta ? 0 : operacao.parcelas.length;
  const limiteData = dataBase || criterios?.data_base_maxima;

  return <section className="sheet-panel debt-operation" aria-labelledby={`${prefixo}-titulo`}>
    <div className="section-heading">
      <div><h2 id={`${prefixo}-titulo`}>{titulo}</h2><p>{descricao}</p></div>
      <span className="count-label">{extinta ? 'Saldo zero' : `${quantidade} ${quantidade === 1 ? 'item' : 'itens'}`}</span>
    </div>
    {permiteExtincao && <label className="debt-extinction-toggle">
      <input id={`${prefixo}-extincao-integral`} type="checkbox" checked={extinta} onChange={e => onChange('extincao_integral', e.target.checked)} />
      <span><strong>Dívida integralmente extinta</strong><small>Use quando não houver nenhum saldo remanescente. Não é necessário lançar valor, data ou encargos.</small></span>
    </label>}
    {extinta ? <div className="debt-extinction-state" role="status">
      <strong>Saldo remanescente: R$ 0,00</strong>
      <span>A dívida correta será registrada como integralmente extinta na data-base.</span>
    </div> : <>
    <div className="field-grid debt-settings">
      <Select id={`${prefixo}-perfil`} label="Padrão de encargos" value={operacao.perfil} options={perfis} onChange={e => onChange('perfil', e.target.value)} />
      {cjf ? <div className="field-note"><strong>Início dos encargos</strong><span>A SELIC é aplicada por competência desde a data de origem de cada item, conforme o padrão CJF.</span></div> : <Select id={`${prefixo}-juros`} label="Início dos juros" value={operacao.criterio_inicio_juros} options={JUROS} onChange={e => onChange('criterio_inicio_juros', e.target.value)} />}
      {!cjf && exigeDataJuros && <Input id={`${prefixo}-data-juros`} label={operacao.criterio_inicio_juros === 'citacao' ? 'Data da citação' : 'Data de início dos juros'} type="date" max={limiteData} required value={operacao.data_inicial_juros || ''} onChange={e => onChange('data_inicial_juros', e.target.value || null)} />}
      <Input id={`${prefixo}-multa`} label="Multa moratória (%)" type="number" min="0" max="100" step="0.01" value={operacao.multa_moratoria_percentual} onChange={e => onChange('multa_moratoria_percentual', e.target.value)} hint="Use zero quando não houver multa." />
    </div>

    <div className="debt-items-heading"><h3>Parcelas ou itens</h3><span>Informe cada valor na sua própria data de origem.</span></div>
    <div className="honorarios-items">
      {operacao.parcelas.map((parcela, indice) => <div className="honorarios-item" key={parcela.numero}>
        <div className="honorarios-item-top">
          <span className="honorarios-item-number" aria-label={`Item ${indice + 1}`}>{String(indice + 1).padStart(2, '0')}</span>
          <Input id={`${prefixo}-historico-${indice}`} label="Descrição (opcional)" placeholder="Ex.: parcela, serviço ou período" value={parcela.historico} onChange={e => onParcelaChange(indice, 'historico', e.target.value)} />
          <button type="button" className="icon-button honorarios-remove" aria-label={`Remover item ${indice + 1}`} title={`Remover item ${indice + 1}`} disabled={quantidade === 1} onClick={() => onRemover(indice)}><Trash2 size={16} /></button>
        </div>
        <div className="honorarios-item-values">
          <Input id={`${prefixo}-data-${indice}`} label={datasIndependentes ? 'Início da correção' : 'Data de origem'} type="date" min={criterios?.inicio} max={limiteData} required value={parcela.data_origem} onChange={e => onParcelaChange(indice, 'data_origem', e.target.value)} />
          <Input id={`${prefixo}-valor-${indice}`} label="Valor na origem (R$)" type="number" min="0.01" step="0.01" required value={parcela.valor} onChange={e => onParcelaChange(indice, 'valor', e.target.value)} />
        </div>
      </div>)}
    </div>
    <Button type="button" variant="ghost" size="sm" className="debt-item-add" onClick={onAdicionar}><Plus size={15} />Adicionar item</Button>
    {criterios && <p className="criteria-summary">Cobertura disponível desde {formatarData(criterios.inicio)}. {criterios.contagem}</p>}
    </>}
  </section>;
}

function ResultadoOperacao({ operacao }: { operacao: ResultadoOperacaoDivida }) {
  return <div className="debt-result-card">
    <div><p>{operacao.rotulo}</p><strong>{formatarMoeda(operacao.valor_atualizado)}</strong></div>
    <dl>
      <div><dt>Valor informado</dt><dd>{formatarMoeda(operacao.valor_informado)}</dd></div>
      <div><dt>Encargos apurados</dt><dd>{formatarMoeda(operacao.encargos_apurados)}</dd></div>
      <div><dt>Quantidade</dt><dd>{operacao.quantidade_parcelas} {operacao.quantidade_parcelas === 1 ? 'item' : 'itens'}</dd></div>
      <div><dt>Padrão aplicado</dt><dd>{operacao.nome_perfil}</dd></div>
    </dl>
    {operacao.parcelas.length > 0 && <details className="debt-items-details">
      <summary>Ver atualização item a item</summary>
      <div className="debt-items-result">
        {operacao.parcelas.map(parcela => <div key={parcela.numero}>
          <span><b>{String(parcela.numero).padStart(2, '0')}</b>{parcela.historico || 'Item sem descrição'}<small>{formatarData(parcela.data_origem)}</small></span>
          <span><small>{formatarMoeda(parcela.valor_informado)}</small><strong>{formatarMoeda(parcela.valor_atualizado)}</strong></span>
        </div>)}
      </div>
    </details>}
  </div>;
}

function AuditoriaOperacao({ operacao }: { operacao: ResultadoOperacaoDivida }) {
  return <details className="audit-details">
    <summary>Memória e critérios — {operacao.rotulo.toLowerCase()}</summary>
    <div className="audit-content">
      <ul>{[...operacao.criterios, ...operacao.metodologia].map(item => <li key={item}>{item}</li>)}</ul>
      {operacao.memoria_mensal.length > 0 && <div className="audit-table-wrap"><table className="audit-table"><thead><tr><th>Item</th><th>Mês</th><th>Critério</th><th>Base</th><th>Atualizado</th><th>Juros</th><th>Multa</th></tr></thead><tbody>
        {operacao.memoria_mensal.map((item, indice) => <tr key={`${item.parcela}-${item.competencia}-${item.indice_aplicado}-${indice}`}><td>{String(item.parcela).padStart(2, '0')}</td><td>{item.competencia}</td><td>{item.indice_aplicado}</td><td>{formatarMoeda(item.valor_base)}</td><td>{formatarMoeda(item.valor_corrigido)}</td><td>{formatarMoeda(item.juros_periodo)}</td><td>{formatarMoeda(item.multa)}</td></tr>)}
      </tbody></table></div>}
      {Object.keys(operacao.fontes).length > 0 && <div className="source-links">{Object.entries(operacao.fontes).map(([nome, url]) => <a key={nome} href={url} target="_blank" rel="noreferrer">{nome.replaceAll('_', ' ')}</a>)}</div>}
    </div>
  </details>;
}

export function HonorariosSucumbenciais({ baseInicial = 'proveito_economico' }: { baseInicial?: BaseHonorariosAutonomos } = {}) {
  const [base, setBase] = useState<BaseHonorariosAutonomos>(baseInicial);
  const [camposBase, setCamposBase] = useState<Pick<HonorariosPrincipais, 'valor_causa' | 'data_protocolo' | 'indice' | 'valor_certo'>>({ valor_causa: null, data_protocolo: null, indice: 'ipcae', valor_certo: null });
  const [cobertura, setCobertura] = useState<CoberturaHonorarios | null>(null);
  const [atualizarValorCerto, setAtualizarValorCerto] = useState(true);
  const [encargosValorCerto, setEncargosValorCerto] = useState(encargosValorCertoIniciais);
  const [dados, setDados] = useState(dadosIniciais);
  const [original, setOriginal] = useState(operacaoInicial);
  const [correta, setCorreta] = useState(operacaoInicial);
  const [custasDespesas, setCustasDespesas] = useState<CustaDespesaProcessual[]>([]);
  const [percentual, setPercentual] = useState('');
  const [escalonarFazenda, setEscalonarFazenda] = useState(false);
  const [escalonamento, setEscalonamento] = useState(escalonamentoInicial);
  const [criteriosOriginal, setCriteriosOriginal] = useState<CriteriosPublicos | null>(null);
  const [criteriosCorreta, setCriteriosCorreta] = useState<CriteriosPublicos | null>(null);
  const [resultado, setResultado] = useState<ResultadoHonorariosProveito | ResultadoHonorariosIsolados | null>(null);
  const [erro, setErro] = useState('');
  const [carregando, setCarregando] = useState(false);
  const [gerandoRelatorio, setGerandoRelatorio] = useState(false);
  const [erroRelatorio, setErroRelatorio] = useState('');

  useEffect(() => {
    if (base !== 'proveito_economico') return;
    let ativo = true;
    Promise.all([obterCriterios(original.perfil), obterCriterios(correta.perfil)])
      .then(([a, b]) => { if (ativo) { setCriteriosOriginal(a); setCriteriosCorreta(b); setErro(''); } })
      .catch(async e => { if (ativo) setErro(await mensagemErro(e)); });
    return () => { ativo = false; };
  }, [base, original.perfil, correta.perfil]);

  useEffect(() => {
    if (base === 'proveito_economico' || (base === 'valor_certo' && !atualizarValorCerto && !custasDespesas.length)) return;
    let ativo = true;
    obterCoberturaHonorarios().then(c => { if (ativo) setCobertura(c); })
      .catch(async e => { if (ativo) setErro(await mensagemErro(e)); });
    return () => { ativo = false; };
  }, [base, atualizarValorCerto, custasDespesas.length]);

  const catalogo = criteriosOriginal?.perfis || criteriosCorreta?.perfis;
  const perfis = opcoesPerfisCalculo(catalogo);
  const criteriosCorretaAplicaveis = correta.extincao_integral ? null : criteriosCorreta;
  const limiteHonorarios = detalhesLimiteHonorariosAutonomos(base, camposBase.indice, cobertura, criteriosOriginal, criteriosCorretaAplicaveis, custasDespesas.length > 0, atualizarValorCerto ? encargosValorCerto : null);
  const dataBaseMaxima = limiteHonorarios.data;
  const criterioLimite = base === 'proveito_economico'
    ? [criteriosOriginal, criteriosCorretaAplicaveis].find(item => item?.data_base_maxima === dataBaseMaxima)
    : null;
  const coberturaPronta = base === 'proveito_economico' ? Boolean(criteriosOriginal && (correta.extincao_integral || criteriosCorreta)) : base === 'valor_causa' || (base === 'valor_certo' && atualizarValorCerto) || custasDespesas.length > 0 ? Boolean(cobertura && (base !== 'valor_certo' || !atualizarValorCerto || encargosValorCerto.juros !== 'taxa_legal' || cobertura.taxa_legal)) : true;

  function atualizarDados(campo: keyof ReturnType<typeof dadosIniciais>, valor: string) {
    setDados(atual => ({ ...atual, [campo]: valor }));
    setResultado(null);
  }

  function atualizarOperacao(
    setter: React.Dispatch<React.SetStateAction<OperacaoDividaHonorarios>>,
    campo: CampoOperacao,
    valor: string | boolean | null,
  ) {
    setter(atual => {
      const proxima = { ...atual, [campo]: valor } as OperacaoDividaHonorarios;
      if (campo === 'perfil' && valor === 'selic_cjf_v1') {
        proxima.criterio_inicio_juros = 'vencimento';
        proxima.data_inicial_juros = null;
      }
      if (campo === 'criterio_inicio_juros' && valor === 'vencimento') proxima.data_inicial_juros = null;
      return proxima;
    });
    setResultado(null);
  }

  function atualizarParcela(
    setter: React.Dispatch<React.SetStateAction<OperacaoDividaHonorarios>>,
    indice: number,
    campo: CampoParcela,
    valor: string,
  ) {
    setter(atual => ({
      ...atual,
      parcelas: atual.parcelas.map((parcela, i) => i === indice ? { ...parcela, [campo]: valor } : parcela),
    }));
    setResultado(null);
  }

  function adicionarParcela(setter: React.Dispatch<React.SetStateAction<OperacaoDividaHonorarios>>) {
    setter(atual => ({ ...atual, parcelas: [...atual.parcelas, parcelaInicial(atual.parcelas.length + 1)] }));
    setResultado(null);
  }

  function removerParcela(
    setter: React.Dispatch<React.SetStateAction<OperacaoDividaHonorarios>>,
    indice: number,
  ) {
    setter(atual => atual.parcelas.length === 1 ? atual : {
      ...atual,
      parcelas: atual.parcelas.filter((_, i) => i !== indice).map((parcela, i) => ({ ...parcela, numero: i + 1 })),
    });
    setResultado(null);
  }

  function montarCalculo(): CalculoHonorariosProveito | CalculoHonorariosIsolados {
    if (base !== 'proveito_economico') return montarHonorariosIsolados(base, dados, camposBase, custasDespesas, escalonarFazenda, percentual, escalonamento, atualizarValorCerto ? encargosValorCerto : null);
    return {
      categoria: 'honorarios_sucumbenciais_proveito_economico',
      dados_gerais: dados,
      divida_original: original,
      divida_correta: prepararOperacaoDivida(correta),
      custas_despesas: custasDespesas,
      ...fixacaoHonorarios(escalonarFazenda, percentual, escalonamento),
    };
  }

  async function calcular(evento: FormEvent) {
    evento.preventDefault();
    setErro('');
    setErroRelatorio('');
    setCarregando(true);
    setResultado(null);
    try {
      const entrada = montarCalculo();
      setResultado(entrada.categoria === 'honorarios_sucumbenciais_proveito_economico'
        ? await executarHonorariosProveito(entrada) : await executarHonorariosIsolados(entrada));
    }
    catch (e) { setErro(await mensagemErro(e)); }
    finally { setCarregando(false); }
  }

  async function baixarRelatorio() {
    setGerandoRelatorio(true);
    setErroRelatorio('');
    try {
      const entrada = montarCalculo();
      const arquivo = entrada.categoria === 'honorarios_sucumbenciais_proveito_economico'
        ? await exportarPdfHonorarios(entrada) : await exportarPdfHonorariosIsolados(entrada);
      downloadBlob(arquivo, 'relatorio_honorarios_sucumbenciais.pdf');
    } catch (e) {
      setErroRelatorio(await mensagemErro(e));
    } finally {
      setGerandoRelatorio(false);
    }
  }

  function limpar() {
    setDados(dadosIniciais()); setOriginal(operacaoInicial()); setCorreta(operacaoInicial());
    setCustasDespesas([]); setPercentual(''); setResultado(null); setErro(''); setErroRelatorio('');
    setEscalonarFazenda(false); setEscalonamento(escalonamentoInicial());
    setBase('proveito_economico');
    setCamposBase({ valor_causa: null, data_protocolo: null, indice: 'ipcae', valor_certo: null });
    setAtualizarValorCerto(true); setEncargosValorCerto(encargosValorCertoIniciais());
  }

  return <div className="honorarios-page">
    <div className="page-intro"><p className="eyebrow">HONORÁRIOS SUCUMBENCIAIS</p><h1>Calcule os honorários sucumbenciais.</h1><p>Escolha a base: redução da dívida, valor da causa atualizado ou equidade. Percentual único e faixas da Fazenda Pública estão disponíveis para as bases percentuais.</p></div>
    <form onSubmit={calcular}>
      <fieldset disabled={carregando}>
        <section className="sheet-panel" aria-labelledby="honorarios-partes-titulo">
          <div className="section-heading"><h2 id="honorarios-partes-titulo">Partes e observações</h2><span className="count-label">Identificação</span></div>
          <div className="field-grid honorarios-partes-grid">
            <Input id="honorarios-processo" label="Número do processo (opcional)" value={dados.processo} onChange={e => atualizarDados('processo', e.target.value)} />
            <Input id="honorarios-requerente" label="Requerente" value={dados.requerente} onChange={e => atualizarDados('requerente', e.target.value)} />
            <Input id="honorarios-requerido" label="Requerido" value={dados.requerido} onChange={e => atualizarDados('requerido', e.target.value)} />
            <Input id="honorarios-classe" label="Classe" value={dados.classe} onChange={e => atualizarDados('classe', e.target.value)} />
            <Input id="honorarios-comarca" label="Comarca" value={dados.comarca} onChange={e => atualizarDados('comarca', e.target.value)} />
            <Input id="honorarios-vara" label="Vara" value={dados.vara} onChange={e => atualizarDados('vara', e.target.value)} />
          </div>
          <div className="honorarios-observacoes"><Textarea id="honorarios-observacoes" label="Observações" value={dados.observacoes} onChange={e => atualizarDados('observacoes', e.target.value)} /></div>
        </section>
        <section className="sheet-panel" aria-labelledby="honorarios-dados-titulo">
          <div className="section-heading"><h2 id="honorarios-dados-titulo">Dados do cálculo</h2><span className="count-label">Base e sentença</span></div>
          <div className="field-grid honorarios-base-grid">
            <Select id="honorarios-base-autonoma" label="Base dos honorários" value={base} options={[
              { value: 'proveito_economico', label: 'Proveito econômico · redução de dívida' },
              { value: 'valor_causa', label: 'Valor da causa atualizado' },
              { value: 'valor_certo', label: 'Equidade · valor certo' },
            ]} onChange={e => { setBase(e.target.value as BaseHonorariosAutonomos); setResultado(null); setErro(''); setErroRelatorio(''); }} />
          </div>
          <div className="mt-4">
          <div className="field-grid honorarios-partes-grid">
            <Input id="honorarios-data-base" label="Data-base" type="date" max={dataBaseMaxima} required value={dados.data_base} onChange={e => atualizarDados('data_base', e.target.value)} hint={dataBaseMaxima ? mensagemCoberturaSelecionada(dataBaseMaxima, limiteHonorarios.motivos, criterioLimite) : coberturaPronta ? undefined : 'Consultando a cobertura dos índices…'} />
            {base !== 'valor_certo' && <Select id="honorarios-fixacao" label="Forma de fixação" value={escalonarFazenda ? 'fazenda' : 'percentual'} options={[{ value: 'percentual', label: 'Percentual único' }, { value: 'fazenda', label: 'Faixas · Fazenda Pública (art. 85)' }]} onChange={e => { setEscalonarFazenda(e.target.value === 'fazenda'); setResultado(null); setErroRelatorio(''); }} />}
            {base !== 'valor_certo' && !escalonarFazenda && <Input id="honorarios-percentual" label="Percentual fixado na sentença (%)" type="number" min="0.0001" max="100" step="0.0001" required value={percentual} onChange={e => { setPercentual(e.target.value); setResultado(null); }} />}
            {base === 'valor_certo' && <Input id="honorarios-valor-certo" label={atualizarValorCerto ? 'Valor fixado dos honorários (R$)' : 'Valor certo na data-base (R$)'} type="number" min="0.01" step="0.01" required value={camposBase.valor_certo || ''} onChange={e => { setCamposBase(c => ({ ...c, valor_certo: e.target.value || null })); setResultado(null); }} />}
            {base === 'valor_certo' && <Select id="honorarios-valor-certo-situacao" label="Situação do valor" value={atualizarValorCerto ? 'fixado' : 'atualizado'} options={[{ value: 'fixado', label: 'Atualizar desde a fixação' }, { value: 'atualizado', label: 'Valor já na data-base' }]} onChange={e => { setAtualizarValorCerto(e.target.value === 'fixado'); setResultado(null); setErro(''); setErroRelatorio(''); }} />}
          </div>
          </div>
          {base === 'valor_causa' && <div className="mt-4"><HonorariosCausaCampos className="honorarios-partes-grid" config={camposBase} dataBase={dados.data_base} onChange={campos => { setCamposBase(c => ({ ...c, ...campos })); setResultado(null); }} /></div>}
          {base === 'valor_certo' && (atualizarValorCerto ? <HonorariosValorCertoCampos config={encargosValorCerto} dataBase={dados.data_base} onChange={config => { setEncargosValorCerto(config); setResultado(null); setErroRelatorio(''); }} /> : <p className="criteria-summary">Valor informado já na data-base: não aplicar os encargos novamente. O programa não arbitra o valor judicial.</p>)}
          {base === 'valor_causa' && <p className="criteria-summary">Correção exclusiva por IPCA-E ou IPCA desde o protocolo, sem juros. O valor da causa não é somado aos honorários.</p>}
          {base !== 'valor_certo' && escalonarFazenda && <EscalonamentoFazendaForm config={escalonamento} onChange={config => { setEscalonamento(config); setResultado(null); setErroRelatorio(''); }} />}
        </section>
        <CustasDespesasForm
          idPrefix="honorarios"
          itens={custasDespesas}
          dataBase={dados.data_base}
          onChange={itens => { setCustasDespesas(itens); setResultado(null); }}
        />
        {base === 'proveito_economico' && <div className="debt-grid">
          <OperacaoForm titulo="Dívida originalmente exigida" descricao="Todos os valores que compunham a cobrança antes da redução." prefixo="original" operacao={original} criterios={criteriosOriginal} perfis={perfis} dataBase={dados.data_base} onChange={(campo, valor) => atualizarOperacao(setOriginal, campo, valor)} onParcelaChange={(indice, campo, valor) => atualizarParcela(setOriginal, indice, campo, valor)} onAdicionar={() => adicionarParcela(setOriginal)} onRemover={indice => removerParcela(setOriginal, indice)} />
          <OperacaoForm titulo="Dívida correta" descricao="Todos os valores reconhecidos como efetivamente devidos." prefixo="correta" operacao={correta} criterios={criteriosCorreta} perfis={perfis} dataBase={dados.data_base} permiteExtincao onChange={(campo, valor) => atualizarOperacao(setCorreta, campo, valor)} onParcelaChange={(indice, campo, valor) => atualizarParcela(setCorreta, indice, campo, valor)} onAdicionar={() => adicionarParcela(setCorreta)} onRemover={indice => removerParcela(setCorreta, indice)} />
        </div>}
        {erro && <div role="alert" className="feedback-error">{erro}</div>}
        <div className="calculation-actions"><div className="result-actions"><Button type="button" variant="ghost" onClick={limpar}><RotateCcw size={16} />Limpar</Button><Button type="submit" disabled={carregando || !coberturaPronta || !dados.data_base}>{carregando ? 'Calculando…' : 'Calcular honorários'}<Calculator size={16} /></Button></div></div>
      </fieldset>
    </form>
    {resultado && <section className="honorarios-result" aria-label="Resultado dos honorários sucumbenciais">
      <div className="result-head"><div><h2>{resultado.custas_despesas.length ? 'Total geral' : 'Honorários sucumbenciais'}</h2><p className="result-total">{formatarMoeda(resultado.total_geral)}</p></div><div className="result-actions"><Button variant="outline" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>Editar dados</Button><Button disabled={gerandoRelatorio} onClick={baixarRelatorio}><Download size={16} />{gerandoRelatorio ? 'Gerando PDF…' : 'Baixar relatório PDF'}</Button></div></div>
      {erroRelatorio && <div role="alert" className="feedback-error">{erroRelatorio}</div>}
      {resultado.categoria === 'honorarios_sucumbenciais_proveito_economico' ? <div className="result-metrics honorarios-metrics">
        <div><p>Proveito econômico</p><strong>{formatarMoeda(resultado.proveito_economico)}</strong></div>
        <div><p>{resultado.escalonamento_fazenda ? 'Forma de fixação' : 'Percentual da sentença'}</p><strong>{resultado.escalonamento_fazenda ? 'Faixas · art. 85' : formatarPercentual(resultado.percentual_sentenca)}</strong></div>
        {resultado.custas_despesas.length ? <><div><p>Honorários sucumbenciais</p><strong>{formatarMoeda(resultado.honorarios_sucumbenciais)}</strong></div><div><p>Custas e despesas · IPCA-E</p><strong>{formatarMoeda(resultado.custas_despesas_valor_atualizado)}</strong></div></> : <div><p>Diferença apurada</p><strong>{formatarMoeda(resultado.diferenca_atualizada)}</strong></div>}
      </div> : <>{resultado.atualizacao_valor_certo ? <HonorariosValorCertoResultado resultado={resultado} /> : <><HonorariosPrincipaisResultado resultado={{ honorarios_sucumbenciais: resultado.apuracao }} /><p className="fees-note">{resultado.premissas.criterios[0]}</p></>}{resultado.custas_despesas.length > 0 && <div className="result-metrics"><div><p>Custas e despesas · IPCA-E</p><strong>{formatarMoeda(resultado.custas_despesas_valor_atualizado)}</strong></div></div>}</>}
      {resultado.alertas.map(alerta => <div className="feedback-error" role="alert" key={alerta}>{alerta}</div>)}
      <p className="result-explanation">{resultado.formula}</p>
      {resultado.escalonamento_fazenda && <EscalonamentoFazendaResultado resultado={resultado.escalonamento_fazenda} />}
      <CustasDespesasResultado itens={resultado.custas_despesas} />
      {resultado.categoria === 'honorarios_sucumbenciais_proveito_economico' && <>
        <div className="debt-result-grid"><ResultadoOperacao operacao={resultado.divida_original} /><ResultadoOperacao operacao={resultado.divida_correta} /></div>
        <div className="mt-7"><AuditoriaOperacao operacao={resultado.divida_original} /><AuditoriaOperacao operacao={resultado.divida_correta} /></div>
      </>}
    </section>}
  </div>;
}
