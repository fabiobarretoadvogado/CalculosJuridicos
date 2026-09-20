import { Input, Select } from './ui';
import type { EscalonamentoFazendaHonorarios, ResultadoEscalonamentoFazenda } from '../services/api';
import { FAIXAS_FAZENDA } from '../utils/honorariosFazenda';
import { formatarData, formatarMoeda } from '../utils/formatters';

const numeroSM = (valor: string) => Number(valor).toLocaleString('pt-BR', { maximumFractionDigits: 0 });
const percentualFaixa = (valor: string) => `${Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}%`;

export function EscalonamentoFazendaForm({ config, onChange }: { config: EscalonamentoFazendaHonorarios; onChange: (config: EscalonamentoFazendaHonorarios) => void }) {
  return <div className="mt-4" aria-label="Faixas da Fazenda Pública">
    <div className="field-grid honorarios-partes-grid">
      <Select id="honorarios-marco-salario" label="Referência do salário mínimo" value={config.marco} onChange={e => onChange({ ...config, marco: e.target.value as EscalonamentoFazendaHonorarios['marco'] })} options={[
        { value: 'sentenca_liquida', label: 'Sentença líquida' },
        { value: 'decisao_liquidacao', label: 'Decisão de liquidação' },
      ]} />
      <Input id="honorarios-data-decisao" label={config.marco === 'sentenca_liquida' ? 'Data da sentença líquida' : 'Data da decisão de liquidação'} type="date" required value={config.data_decisao} onChange={e => onChange({ ...config, data_decisao: e.target.value })} />
      <Input id="honorarios-salario-minimo" label="Salário mínimo nessa data (R$)" type="number" min="0.01" step="0.01" required value={config.salario_minimo} onChange={e => onChange({ ...config, salario_minimo: e.target.value })} />
    </div>
    <p className="criteria-summary">Art. 85, § 4º, IV, CPC: use o salário mínimo vigente no marco escolhido, não o da data-base do cálculo. Os limites das faixas são múltiplos desse valor.</p>
    <div className="field-grid mt-4">
      {FAIXAS_FAZENDA.map((faixa, i) => <Input key={faixa.nome} id={`honorarios-faixa-${i+1}`} label={`${faixa.nome} · ${faixa.min}% a ${faixa.max}%`} type="number" min={faixa.min} max={faixa.max} step="0.0001" required value={config.percentuais_faixas[i]} onChange={e => onChange({ ...config, percentuais_faixas: config.percentuais_faixas.map((p, j) => i === j ? e.target.value : p) })} />)}
    </div>
    <p className="criteria-summary">Percentuais inicialmente preenchidos com os mínimos legais: confirme ou ajuste conforme a decisão. Aplicação progressiva sobre o excedente de cada faixa (art. 85, §§ 3º e 5º), sem custas ou despesas.</p>
  </div>;
}

export function EscalonamentoFazendaResultado({ resultado: r }: { resultado: ResultadoEscalonamentoFazenda }) {
  return <div className="fees-result" aria-labelledby="escalonamento-fazenda-titulo">
    <div className="section-heading"><h2 id="escalonamento-fazenda-titulo">Escalonamento · Fazenda Pública</h2></div>
    <p className="component-legend">Salário mínimo: {formatarMoeda(r.salario_minimo)} · {r.marco === 'sentenca_liquida' ? 'Sentença líquida' : 'Decisão de liquidação'} de {formatarData(r.data_decisao)}. Cada percentual incide somente na parcela da base dentro da faixa.</p>
    <div className="result-table-wrap" tabIndex={0} role="region" aria-label="Honorários por faixa"><table className="result-table"><thead><tr><th scope="col">Faixa (salários mínimos)</th><th scope="col">Base na faixa</th><th scope="col">Percentual</th><th scope="col">Honorários</th></tr></thead><tbody>
      {r.faixas.map(f => <tr key={f.ordem}><td data-label="Faixa">{f.ordem === 1 ? `Até ${numeroSM(f.limite_salarios_minimos!)} SM` : `Acima de ${numeroSM(f.limite_inferior_salarios_minimos)}${f.limite_salarios_minimos ? ` até ${numeroSM(f.limite_salarios_minimos)}` : ''} SM`}</td><td data-label="Base na faixa">{formatarMoeda(f.valor_incidente)}</td><td data-label="Percentual">{percentualFaixa(f.percentual_aplicado)}</td><td data-label="Honorários">{Number(f.valor_incidente) > 0 ? formatarMoeda(f.valor) : 'Não alcançada'}</td></tr>)}
    </tbody><tfoot><tr><td>Total</td><td>{formatarMoeda(r.base_calculo)}</td><td>—</td><td>{formatarMoeda(r.valor_total)}</td></tr></tfoot></table></div>
    <p className="component-legend">Arredondamento de cada faixa ao centavo; total igual à soma das faixas. Custas e despesas são somadas separadamente, sem integrar esta base. <a href={r.fonte} target="_blank" rel="noreferrer">Art. 85 do CPC</a>.</p>
  </div>;
}
