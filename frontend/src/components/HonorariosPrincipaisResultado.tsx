import type { ResultadoCalculo } from '../services/api';
import { formatarMoeda, formatarData } from '../utils/formatters';

export function HonorariosPrincipaisResultado({ resultado: r }: { resultado: Partial<Pick<ResultadoCalculo, 'honorarios_sucumbenciais' | 'cumprimento_sentenca' | 'destaque_contratuais'>> }) {
  const h = r.honorarios_sucumbenciais, c = r.cumprimento_sentenca, d = r.destaque_contratuais;
  const percentual = (v: string) => `${Number(v).toLocaleString('pt-BR', { maximumFractionDigits: 4 })}%`;
  return <>
    {h && <section className="fees-result" aria-label="Apuração dos honorários sucumbenciais">
      <div className="section-heading"><h2>Honorários sucumbenciais</h2></div>
      <p className="fees-note">{h.descricao_base}{h.data_protocolo ? ` · Protocolo ${formatarData(h.data_protocolo)} · ${h.indice === 'ipcae' ? 'IPCA-E' : 'IPCA'} · Sem juros` : ''}</p>
      <div className="result-metrics">
        {h.data_protocolo && <><div><p>Valor no protocolo</p><strong>{formatarMoeda(h.valor_original)}</strong></div><div><p>Correção · fator {Number(h.fator_acumulado).toLocaleString('pt-BR', { minimumFractionDigits: 4, maximumFractionDigits: 4 })}</p><strong>{formatarMoeda(h.correcao_monetaria)}</strong></div></>}
        {h.percentual && <div><p>Base atualizada × {percentual(h.percentual)}</p><strong>{formatarMoeda(h.base_atualizada)}</strong></div>}
        <div><p>Honorários apurados</p><strong>{formatarMoeda(h.valor)}</strong></div>
      </div>
      {h.memoria.length > 0 && <details className="audit-details"><summary>Memória da correção do valor da causa</summary><div className="audit-content">
        <div className="result-table-wrap"><table className="result-table"><thead><tr>{['Mês', 'Base', 'Índice', 'Fator', 'Valor corrigido', 'Período e critério'].map(t => <th key={t}>{t}</th>)}</tr></thead><tbody>{h.memoria.map((m, i) => <tr key={i}>
          <td data-label="Mês">{m.competencia}</td><td data-label="Base">{formatarMoeda(m.valor_base)}</td><td data-label="Índice">{m.indice_aplicado}</td><td data-label="Fator">{Number(m.fator_aplicado).toLocaleString('pt-BR', { minimumFractionDigits: 4, maximumFractionDigits: 4 })}</td><td data-label="Valor corrigido">{formatarMoeda(m.valor_corrigido)}</td><td data-label="Período e critério">{m.observacao}</td>
        </tr>)}</tbody></table></div>{h.fonte && <a href={h.fonte} target="_blank" rel="noreferrer">Fonte oficial da correção</a>}
      </div></details>}
    </section>}
    {c && <section className="fees-result" aria-label="Acréscimos do cumprimento de sentença">
      <div className="section-heading"><h2>Cumprimento de sentença</h2></div>
      <p className="fees-note">Base comum: {formatarMoeda(c.base_calculo)} · parcelas atualizadas após descontos, sem honorários da sentença, custas ou despesas.</p>
      <div className="result-metrics">{c.aplicar_multa && <div><p>Multa · art. 523 · 10%</p><strong>{formatarMoeda(c.multa)}</strong></div>}{c.aplicar_honorarios && <div><p>Honorários · art. 523 · 10%</p><strong>{formatarMoeda(c.honorarios)}</strong></div>}</div>
    </section>}
    {d && <section className="contractual-result" aria-label="Destaque contratual sem acréscimo à dívida">
      <h3>Destaque de honorários contratuais · {percentual(d.percentual)}</h3>
      <p className="fees-note">{d.descricao_base}. Apenas divisão do crédito: não altera o total devido.</p>
      <dl><div><dt>Base do destaque</dt><dd>{formatarMoeda(d.base_calculo)}</dd></div><div><dt>Honorários contratuais destacados</dt><dd>{formatarMoeda(d.valor)}</dd></div><div><dt>Saldo dessa base após destaque</dt><dd>{formatarMoeda(d.saldo_apos_destaque)}</dd></div></dl>
    </section>}
  </>;
}
