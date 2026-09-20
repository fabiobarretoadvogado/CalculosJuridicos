import { Plus, ReceiptText, Trash2 } from 'lucide-react';
import { Button, Input, Select } from './ui';
import type { HonorariosPrincipais, CumprimentoSentenca } from '../services/api';

export function HonorariosCausaCampos({ config, dataBase, onChange, className = '' }: {
  config: Pick<HonorariosPrincipais, 'valor_causa' | 'data_protocolo' | 'indice'>;
  dataBase: string;
  className?: string;
  onChange: (config: Pick<HonorariosPrincipais, 'valor_causa' | 'data_protocolo' | 'indice'>) => void;
}) {
  return <div className={`field-grid fees-causa-grid ${className}`}>
    <Input id="honorarios-valor-causa" label="Valor da causa no protocolo (R$)" type="number" min="0.01" step="0.01" required value={config.valor_causa || ''} onChange={e => onChange({ ...config, valor_causa: e.target.value || null })} />
    <Input id="honorarios-protocolo" label="Data do protocolo" type="date" min="2009-07-01" max={dataBase || undefined} required value={config.data_protocolo || ''} onChange={e => onChange({ ...config, data_protocolo: e.target.value || null })} />
    <Select id="honorarios-indice" label="Correção monetária" value={config.indice} onChange={e => onChange({ ...config, indice: e.target.value as HonorariosPrincipais['indice'] })} options={[{ value: 'ipcae', label: 'IPCA-E · IBGE / SGS 7478' }, { value: 'ipca', label: 'IPCA · IBGE / Banco Central' }]} />
  </div>;
}

export function HonorariosPrincipaisForm({ config, dataBase, onChange }: {
  config: HonorariosPrincipais; dataBase: string; onChange: (config: HonorariosPrincipais) => void;
}) {
  const causa = config.base === 'valor_causa';
  const certo = config.base === 'valor_certo';
  return <section className="sheet-panel" aria-labelledby="honorarios-principais-titulo">
    <div className="section-heading"><h2 id="honorarios-principais-titulo">Honorários sucumbenciais</h2><span className="count-label">Sentença</span></div>
    {!config.aplicar && <div className="costs-empty"><ReceiptText size={20} aria-hidden="true" /><span>Honorários sucumbenciais não incluídos.</span></div>}
    {config.aplicar && <div id="honorarios-principais-campos">
      <div className="field-grid fees-base-grid">
        <Select id="honorarios-base" label="Base dos honorários" value={config.base} onChange={e => onChange({ ...config, base: e.target.value as HonorariosPrincipais['base'] })} options={[
          { value: 'proveito_economico', label: 'Valor do proveito econômico' },
          { value: 'valor_causa', label: 'Valor da causa atualizado' },
          { value: 'valor_certo', label: 'Valor certo' },
        ]} />
        {certo ? <Input id="honorarios-valor-certo" label="Valor certo na data-base (R$)" type="number" min="0.01" step="0.01" required value={config.valor_certo || ''} onChange={e => onChange({ ...config, valor_certo: e.target.value || null })} />
          : <Input id="honorarios-percentual" label="Percentual fixado (%)" type="number" min="0.0001" max="100" step="0.0001" required value={config.percentual || ''} onChange={e => onChange({ ...config, percentual: e.target.value || null })} />}
      </div>
      {causa && <HonorariosCausaCampos config={config} dataBase={dataBase} onChange={campos => onChange({ ...config, ...campos })} />}
      <p className="fees-note">{causa ? 'Correção desde o protocolo até a data-base, sem juros. Depois, aplica-se o percentual fixado.' : certo ? 'Informe o valor dos honorários já na data-base. Não recebe nova correção automática.' : 'Base: total atualizado das parcelas, incluindo a multa individual, após descontos e sem custas ou despesas.'}</p>
    </div>}
    <Button type="button" variant="ghost" size="sm" className="cost-add" aria-expanded={config.aplicar} aria-controls={config.aplicar ? 'honorarios-principais-campos' : undefined} onClick={() => onChange({ ...config, aplicar: !config.aplicar })}>
      {config.aplicar ? <><Trash2 size={15} aria-hidden="true" />Remover honorários sucumbenciais</> : <><Plus size={15} aria-hidden="true" />Adicionar honorários sucumbenciais</>}
    </Button>
  </section>;
}

export function CumprimentoSentencaForm({ config, onChange }: {
  config: CumprimentoSentenca; onChange: (config: CumprimentoSentenca) => void;
}) {
  const aplicar = config.aplicar_multa || config.aplicar_honorarios;
  return <section className="sheet-panel" aria-labelledby="cumprimento-titulo">
    <div className="section-heading"><h2 id="cumprimento-titulo">Cumprimento de sentença</h2><span className="count-label">Acréscimos</span></div>
    <div className="fee-options">
      <label className="fee-toggle"><input type="checkbox" checked={config.aplicar_multa} onChange={e => onChange({ ...config, aplicar_multa: e.target.checked })} /><span>Multa de 10%<small>Art. 523, § 1º, CPC/2015 · antigo art. 475-J, CPC/1976</small></span></label>
      <label className="fee-toggle"><input type="checkbox" checked={config.aplicar_honorarios} onChange={e => onChange({ ...config, aplicar_honorarios: e.target.checked })} /><span>Honorários advocatícios de 10%<small>Art. 523, § 1º, CPC/2015</small></span></label>
    </div>
    {aplicar && <p className="fees-note">Base dos dois acréscimos: parcelas atualizadas após descontos, sem honorários da sentença, custas ou despesas. Os honorários de 10% não incidem sobre a multa do art. 523. Confirme o prazo para pagamento voluntário e o saldo não pago; não utilizar contra a Fazenda Pública.</p>}
  </section>;
}

export function DestaquesForm({ config, onChange }: {
  config: CumprimentoSentenca; onChange: (config: CumprimentoSentenca) => void;
}) {
  return <section className="sheet-panel" aria-labelledby="destaques-titulo">
    <div className="section-heading"><h2 id="destaques-titulo">Destaques</h2><span className="count-label">Divisão do crédito</span></div>
      <label className="fee-toggle"><input type="checkbox" checked={config.destacar_contratuais} onChange={e => onChange({ ...config, destacar_contratuais: e.target.checked })} />Destacar honorários contratuais</label>
      {config.destacar_contratuais && <div className="field-grid fees-contract-grid">
        <Input id="contratuais-percentual" label="Destaque contratual (%)" type="number" min="0.0001" max="100" step="0.0001" required value={config.percentual_contratuais || ''} onChange={e => onChange({ ...config, percentual_contratuais: e.target.value || null })} />
        <Select id="contratuais-base" label="Base do destaque" value={config.base_contratuais} onChange={e => onChange({ ...config, base_contratuais: e.target.value as CumprimentoSentenca['base_contratuais'] })} options={[
          { value: 'credito_parte', label: 'Crédito da parte · sem honorários judiciais' },
          { value: 'total_sem_custas', label: 'Total devido · sem custas e despesas' },
        ]} />
      </div>}
      <p className="fees-note">Apenas divisão do crédito: não acresce ao cálculo e nunca incide sobre custas ou despesas.{config.destacar_contratuais && config.base_contratuais === 'credito_parte' ? ' Inclui a multa do art. 523, se selecionada; exclui os honorários sucumbenciais e do art. 523.' : ''}</p>
  </section>;
}
