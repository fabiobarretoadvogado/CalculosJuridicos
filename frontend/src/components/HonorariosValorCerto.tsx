import { Input, Select } from './ui';
import type { EncargosValorCerto, ResultadoHonorariosIsolados } from '../services/api';
import { formatarData, formatarMoeda } from '../utils/formatters';

export function HonorariosValorCertoCampos({ config, dataBase, onChange }: { config: EncargosValorCerto; dataBase: string; onChange: (c: EncargosValorCerto) => void }) {
  function mudar<K extends keyof EncargosValorCerto>(campo: K, valor: EncargosValorCerto[K]) { onChange({ ...config, [campo]: valor }); }
  return <>
    <div className="field-grid honorarios-partes-grid mt-4">
      <Input id="valor-certo-data-fixacao" label="Data da fixação" type="date" min="2009-07-01" max={dataBase || undefined} required value={config.data_fixacao} onChange={e => mudar('data_fixacao', e.target.value)} />
      <Select id="valor-certo-indice" label="Correção monetária" value={config.indice} options={[{ value: 'ipcae', label: 'IPCA-E · IBGE / SGS 7478' }, { value: 'ipca', label: 'IPCA · IBGE' }]} onChange={e => mudar('indice', e.target.value as EncargosValorCerto['indice'])} />
      <Select id="valor-certo-regime-juros" label="Juros de mora" value={config.juros} options={[{ value: 'simples', label: 'Percentual mensal simples' }, { value: 'taxa_legal', label: 'Taxa Legal · BCB' }, { value: 'sem_juros', label: 'Não incluir juros' }]} onChange={e => mudar('juros', e.target.value as EncargosValorCerto['juros'])} />
      {config.juros !== 'sem_juros' && <Input id="valor-certo-data-juros" label="Trânsito em julgado / início dos juros" type="date" min={config.juros === 'taxa_legal' ? [config.data_fixacao, '2024-08-30'].sort().at(-1) : config.data_fixacao || undefined} max={dataBase || undefined} required value={config.data_inicio_juros || ''} onChange={e => mudar('data_inicio_juros', e.target.value || null)} />}
      {config.juros === 'simples' && <>
        <Input id="valor-certo-percentual-mensal" label="Juros simples (% ao mês)" type="number" min="0.000001" max="100" step="0.000001" required value={config.percentual_mensal || ''} onChange={e => mudar('percentual_mensal', e.target.value || null)} />
        <Select id="valor-certo-contagem" label="Contagem dos juros simples" value={config.contagem_mes_cheio ? 'inteiros' : 'proporcional'} options={[{ value: 'proporcional', label: 'Dias corridos ÷ 30,4368' }, { value: 'inteiros', label: 'Meses inteiros' }]} onChange={e => mudar('contagem_mes_cheio', e.target.value === 'inteiros')} />
      </>}
    </div>
    <p className="criteria-summary">Correção desde a fixação. O art. 85, § 16, prevê juros desde o trânsito em julgado; informe o marco conforme a decisão, sem presumir essa data. Taxa Legal oficial disponível desde 30/08/2024. Custas não integram esta operação.</p>
  </>;
}

export function HonorariosValorCertoResultado({ resultado }: { resultado: ResultadoHonorariosIsolados }) {
  const r = resultado.atualizacao_valor_certo;
  if (!r) return null;
  const numero = (v: string | null, casas = 4) => v === null ? '—' : Number(v).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
  return <section className="fees-result" aria-label="Atualização dos honorários em valor certo">
    <div className="section-heading"><h2>Valor certo · correção e juros</h2></div>
    <div className="result-metrics">
      <div><p>Valor fixado</p><strong>{formatarMoeda(r.valor_bruto)}</strong></div>
      <div><p>Correção monetária</p><strong>{formatarMoeda(r.correcao_monetaria)}</strong></div>
      <div><p>Juros de mora</p><strong>{formatarMoeda(r.juros_mora)}</strong></div>
      <div><p>Honorários atualizados</p><strong>{formatarMoeda(r.total_parcela)}</strong></div>
    </div>
    <div className="result-table-wrap"><table className="result-table"><thead><tr>{['Encargo', 'Início', 'Fim', 'Base', 'Fator', 'Taxa acumulada', 'Valor'].map(t => <th key={t}>{t}</th>)}</tr></thead><tbody>{Object.entries(r.componentes).map(([nome, c]) => <tr key={nome}>
      <td data-label="Encargo">{nome === 'juros' ? 'Juros de mora' : nome === 'ipcae' ? 'IPCA-E' : 'IPCA'}</td><td data-label="Início">{c.data_inicial ? formatarData(c.data_inicial) : '—'}</td><td data-label="Fim">{c.data_final ? formatarData(c.data_final) : '—'}</td><td data-label="Base">R$ {numero(c.base_calculo)}</td><td data-label="Fator">{numero(c.fator_acumulado)}</td><td data-label="Taxa acumulada">{c.taxa_acumulada_percentual === null ? '—' : `${numero(c.taxa_acumulada_percentual, 6)}%`}</td><td data-label="Valor">{formatarMoeda(c.valor)}</td>
    </tr>)}</tbody></table></div>
    {([['Correção monetária', r.memoria_correcao], ['Juros de mora', r.memoria_juros]] as const).map(([titulo, memoria]) => memoria.length > 0 && <details className="audit-details" key={titulo}><summary>Memória · {titulo}</summary><div className="audit-content"><div className="result-table-wrap"><table className="result-table"><thead><tr>{['Mês', 'Índice', 'Base', 'Fator / taxa', 'Juros no período', 'Período e critério'].map(t => <th key={t}>{t}</th>)}</tr></thead><tbody>{memoria.map((m, i) => <tr key={i}>
      <td data-label="Mês">{m.competencia}</td><td data-label="Índice">{m.indice_aplicado}</td><td data-label="Base">R$ {numero(m.valor_base)}</td><td data-label="Fator / taxa">{numero(m.fator_aplicado, titulo === 'Juros de mora' ? 6 : 4)}</td><td data-label="Juros no período">{formatarMoeda(m.juros_periodo)}</td><td data-label="Período e critério">{m.observacao}</td>
    </tr>)}</tbody></table></div></div></details>)}
    <p className="fees-note">{resultado.premissas.criterios[0]}</p>
    {resultado.premissas.metodologia.map((m, i) => <p className="fees-note" key={i}>{m}</p>)}
    {Object.entries(resultado.premissas.fontes).map(([nome, url]) => <p className="fees-note" key={nome}><a href={url} target="_blank" rel="noreferrer">{nome.replaceAll('_', ' ')}</a></p>)}
  </section>;
}
