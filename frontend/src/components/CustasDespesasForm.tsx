import { Plus, ReceiptText, Trash2 } from 'lucide-react';
import { Button, Input } from './ui';
import type { CustaDespesaProcessual } from '../services/api';

interface CustasDespesasFormProps {
  idPrefix: string;
  itens: CustaDespesaProcessual[];
  dataBase?: string;
  onChange: (itens: CustaDespesaProcessual[]) => void;
}

export function CustasDespesasForm({ idPrefix, itens, dataBase, onChange }: CustasDespesasFormProps) {
  function atualizar(indice: number, campo: 'nome' | 'data' | 'valor', valor: string) {
    onChange(itens.map((item, i) => i === indice ? { ...item, [campo]: valor } : item));
  }

  function adicionar() {
    onChange([...itens, {
      numero: Math.max(0, ...itens.map(item => item.numero)) + 1,
      nome: '',
      data: '',
      valor: '',
    }]);
  }

  function remover(indice: number) {
    onChange(itens.filter((_, i) => i !== indice).map((item, i) => ({ ...item, numero: i + 1 })));
  }

  return <section className="sheet-panel costs-section" aria-labelledby={`${idPrefix}-custas-titulo`}>
    <div className="section-heading">
      <div>
        <h2 id={`${idPrefix}-custas-titulo`}>Custas e despesas processuais</h2>
        <p>Cada lançamento será corrigido exclusivamente pelo IPCA-E até a data-base.</p>
      </div>
      <span className="count-label">{itens.length} {itens.length === 1 ? 'lançamento' : 'lançamentos'}</span>
    </div>
    {!itens.length && <div className="costs-empty"><ReceiptText size={20} /><span>Nenhuma custa ou despesa informada.</span></div>}
    <div className="costs-list">
      {itens.map((item, indice) => <div className="cost-line" key={item.numero}>
        <span className="cost-number" aria-label={`Lançamento ${indice + 1}`}>{String(indice + 1).padStart(2, '0')}</span>
        <Input id={`${idPrefix}-custa-nome-${indice}`} label="Nome" placeholder="Ex.: taxa judiciária ou honorários periciais" required value={item.nome} onChange={e => atualizar(indice, 'nome', e.target.value)} />
        <Input id={`${idPrefix}-custa-data-${indice}`} label="Data" type="date" min="2009-07-01" max={dataBase || undefined} required value={item.data} onChange={e => atualizar(indice, 'data', e.target.value)} />
        <Input id={`${idPrefix}-custa-valor-${indice}`} label="Valor (R$)" type="number" min="0.01" step="0.01" placeholder="0,00" required value={item.valor} onChange={e => atualizar(indice, 'valor', e.target.value)} />
        <button type="button" className="icon-button cost-remove" aria-label={`Remover lançamento ${indice + 1}`} title={`Remover lançamento ${indice + 1}`} onClick={() => remover(indice)}><Trash2 size={16} /></button>
      </div>)}
    </div>
    <Button type="button" variant="ghost" size="sm" className="cost-add" onClick={adicionar}><Plus size={15} />Adicionar custa ou despesa</Button>
  </section>;
}
