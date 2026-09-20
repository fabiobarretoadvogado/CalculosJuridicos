import { Minus, Plus, Trash2 } from 'lucide-react';
import { Button, Input, Select } from './ui';
import type { OperacaoDescontos, PerfilCalculo, PerfilDescontos } from '../services/api';
import { opcoesPerfisCalculo } from '../utils/perfisCalculo';

interface Props {
  operacao: OperacaoDescontos;
  perfilPrincipal: PerfilCalculo;
  dataBase: string;
  inicio?: string;
  onChange: (operacao: OperacaoDescontos) => void;
}

export function DescontosForm({ operacao, perfilPrincipal, dataBase, inicio, onChange }: Props) {
  const cjf = (operacao.perfil || perfilPrincipal) === 'selic_cjf_v1';
  const poupanca = operacao.perfil === 'poupanca_deposito_v1';
  const ativos = operacao.itens.filter(item => item.aplicar !== false);
  function atualizar(index: number, campo: 'descricao' | 'data' | 'valor' | 'encargos_sem_atualizacao', valor: string) {
    onChange({ ...operacao, itens: operacao.itens.map((item, i) => i === index ? { ...item, [campo]: valor } : item) });
  }
  return <section className="sheet-panel discounts-section" aria-labelledby="descontos-titulo">
    <div className="section-heading"><div><h2 id="descontos-titulo">Descontos</h2><p>Pagamentos e créditos com data própria. Marque os valores a abater.</p></div><span className="count-label">{ativos.length} de {operacao.itens.length} selecionados</span></div>
    {!operacao.itens.length ? <div className="costs-empty"><Minus size={20} /><span>Nenhum desconto informado.</span></div> : <>
      <div className="field-grid discounts-settings">
        <Select id="descontos-perfil" label="Encargos dos descontos" value={operacao.perfil || ''} onChange={e => onChange({ ...operacao, perfil: (e.target.value || null) as PerfilDescontos | null })} options={[
          { value: '', label: 'Mesmo padrão das parcelas' },
          { value: 'poupanca_deposito_v1', label: 'Poupança — remuneração da conta' },
          ...opcoesPerfisCalculo(),
        ]} />
        {!cjf && !poupanca && <Select id="descontos-inicio-juros" label="Início dos juros" value={operacao.criterio_inicio_juros} onChange={e => onChange({ ...operacao, criterio_inicio_juros: e.target.value as OperacaoDescontos['criterio_inicio_juros'] })} options={[
          { value: 'vencimento', label: 'Data de cada desconto' }, { value: 'citacao', label: 'Citação' }, { value: 'data_fixa', label: 'Data específica' },
        ]} />}
        {!cjf && !poupanca && operacao.criterio_inicio_juros !== 'vencimento' && <Input id="descontos-data-juros" label={operacao.criterio_inicio_juros === 'citacao' ? 'Data da citação' : 'Data de início dos juros'} type="date" required={ativos.length > 0} value={operacao.data_inicial_juros || ''} onChange={e => onChange({ ...operacao, data_inicial_juros: e.target.value || null })} />}
      </div>
      <p className="discounts-note">Atualizados desde cada data até a data-base e abatidos do total das parcelas, antes das custas.</p>
      {poupanca && <p className="discounts-note">Remuneração da conta por aniversários completos, sem IPCA ou SELIC adicionais. Não significa quitação no depósito: confira o saldo real no extrato na efetiva liberação. Informe o valor depositado; se incluir IR ou outra parte fora da conta no total, exclua-a da remuneração na composição abaixo.</p>}
    </>}
    {operacao.itens.map((item, i) => <div className="discount-entry" key={item.numero}>
      <label className="fee-toggle discount-select"><input type="checkbox" checked={item.aplicar !== false} aria-label={`Abater desconto ${item.numero}`} onChange={e => onChange({ ...operacao, itens: operacao.itens.map((p, j) => j === i ? { ...p, aplicar: e.target.checked } : p) })} />Abater este pagamento</label>
      <div className="cost-line">
      <span className="cost-number" aria-label={`Desconto ${item.numero}`}>{String(item.numero).padStart(2, '0')}</span>
      <Input id={`desconto-descricao-${item.numero}`} label="Descrição" maxLength={240} placeholder="Ex.: pagamento parcial ou crédito" value={item.descricao} onChange={e => atualizar(i, 'descricao', e.target.value)} />
      <Input id={`desconto-data-${item.numero}`} label={poupanca ? 'Data do depósito' : 'Data do pagamento'} type="date" required={item.aplicar !== false} min={item.aplicar !== false ? inicio : undefined} max={item.aplicar !== false ? dataBase || undefined : undefined} value={item.data || ''} onChange={e => atualizar(i, 'data', e.target.value)} />
      <Input id={`desconto-valor-${item.numero}`} label="Valor total pago (R$)" type="number" required={item.aplicar !== false} min="0.01" step="0.01" placeholder="0,00" value={item.valor || ''} onChange={e => atualizar(i, 'valor', e.target.value)} />
      <button type="button" className="icon-button cost-remove" aria-label={`Remover desconto ${item.numero}`} onClick={() => onChange({ ...operacao, itens: operacao.itens.filter((_, j) => i !== j) })}><Trash2 size={17} /></button>
      </div>
      <details className="discount-composition"><summary>Composição do pagamento (opcional)</summary><div className="field-grid discounts-settings">
        <Input id={`desconto-encargos-${item.numero}`} label={poupanca ? 'Parte fora da conta, sem remuneração (R$)' : 'Encargos já pagos, sem nova incidência (R$)'} type="number" min="0" max={item.valor || undefined} step="0.01" value={item.encargos_sem_atualizacao || '0'} onChange={e => atualizar(i, 'encargos_sem_atualizacao', e.target.value)} />
        <Input id={`desconto-base-${item.numero}`} label="Base da atualização (R$)" readOnly className="parcel-balance" value={item.valor ? Number(item.encargos_sem_atualizacao || 0) <= Number(item.valor) ? Number(Number(item.valor) - Number(item.encargos_sem_atualizacao || 0)).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : 'Revise a composição' : '—'} />
      </div><p className="discounts-note">Use somente quando parte do pagamento não deve receber novos encargos. Essa parte será abatida nominalmente; os encargos escolhidos incidem sobre o restante. Em branco ou zero: atualiza o valor total pago.</p></details>
    </div>)}
    <Button type="button" variant="ghost" size="sm" onClick={() => onChange({ ...operacao, itens: [...operacao.itens, { numero: Math.max(0, ...operacao.itens.map(item => item.numero)) + 1, aplicar: true, descricao: '', data: '', valor: '', encargos_sem_atualizacao: '0' }] })}><Plus size={15} />Adicionar pagamento ou desconto</Button>
  </section>;
}
