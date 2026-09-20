import type { ResultadoCalculo } from '../services/api';
import { componentesResultado, indiceAcumulado, memoriaExibida } from '../utils/componentes';
import { formatarData, formatarMoeda } from '../utils/formatters';

export function DescontosResultado({ resultado }: { resultado: ResultadoCalculo | null | undefined }) {
  if (!resultado) return null;
  const componentes = componentesResultado(resultado);
  const poupanca = resultado.premissas.entrada.perfil === 'poupanca_deposito_v1';
  return <section className="discounts-result" aria-labelledby="descontos-resultado-titulo">
    <div className="section-heading"><h2 id="descontos-resultado-titulo">Descontos atualizados</h2><span className="count-label">{resultado.parcelas.length} lançamento{resultado.parcelas.length !== 1 ? 's' : ''}</span></div>
    <p className="component-legend">Operação separada: cada desconto parte da sua própria data e usa os encargos escolhidos.</p>
    {poupanca && <p className="component-legend">Remuneração estimada da conta judicial; confira o saldo real na efetiva liberação. O depósito não foi tratado como quitação da dívida.</p>}
    {(resultado.premissas.composicao_pagamentos || []).filter(item => Number(item.encargos_sem_atualizacao) > 0).map(item => <p className="component-legend" key={item.numero}>Lançamento {item.numero}: total {formatarMoeda(item.valor)}; base da atualização {formatarMoeda(Number(item.valor) - Number(item.encargos_sem_atualizacao))}; {poupanca ? 'parte fora da conta' : 'encargos já pagos'} {formatarMoeda(item.encargos_sem_atualizacao)}, abatidos nominalmente, sem nova incidência.</p>)}
    <div className="result-table-wrap" tabIndex={0} role="region" aria-label="Valores e índices dos descontos"><table className="result-table component-table"><thead><tr>
      {['Nº', 'Descrição', 'Data do desconto', 'Valor informado'].map(t => <th scope="col" key={t}>{t}</th>)}
      {componentes.map(c => <th scope="col" key={c.chave}>{c.nome}<small>{c.periodo}</small></th>)}<th scope="col">Atualizado</th>
    </tr></thead><tbody>{resultado.parcelas.map(item => <tr key={item.numero}>
      <td data-label="Nº">{item.numero}</td><td data-label="Descrição">{item.historico || '—'}</td><td data-label="Data do desconto">{formatarData(item.data_vencimento)}</td><td data-label="Valor informado">{formatarMoeda(item.valor_bruto)}</td>
      {componentes.map(c => { const v = item.componentes[c.chave]; return <td key={c.chave} data-label={`${c.nome} · ${c.periodo}`}>{v?.data_inicial ? <><small className="applied-index" title={`De ${formatarData(v.data_inicial)} a ${formatarData(v.data_final)}. Base: ${formatarMoeda(v.base_calculo)}.`}>{indiceAcumulado(v)}</small>{formatarMoeda(v.valor)}</> : <span className="not-applied">Não incide</span>}</td>; })}
      <td data-label="Desconto atualizado">{formatarMoeda(item.total_parcela)}</td>
    </tr>)}</tbody><tfoot><tr><td colSpan={3}>Total dos descontos</td>{[resultado.resumo.principal_original, ...componentes.map(c => resultado.resumo.totais_componentes[c.chave]), resultado.resumo.total_atualizado].map((v, i) => <td key={i}>{formatarMoeda(v)}</td>)}</tr></tfoot></table></div>
    <details className="audit-details"><summary>Critérios e memória dos descontos</summary><div className="audit-content">
      <ul>{[...(resultado.premissas.criterios || []), ...(resultado.premissas.metodologia || [])].map(t => <li key={t}>{t}</li>)}</ul>
      <div className="source-links">{Object.entries(resultado.premissas.fontes || {}).map(([nome, url]) => <a key={nome} href={url} target="_blank" rel="noreferrer">{nome.replaceAll('_', ' ')}</a>)}</div>
      <div className="result-table-wrap" tabIndex={0} role="region" aria-label="Memória mensal dos descontos"><table className="result-table"><thead><tr>{['Nº', 'Mês', 'Critério', 'Base', 'Fator', 'Atualizado', 'Juros', 'Memória do trecho'].map(t => <th scope="col" key={t}>{t}</th>)}</tr></thead><tbody>{resultado.memoria_mensal.map((m, i) => <tr key={i}><td data-label="Nº">{m.parcela}</td><td data-label="Mês">{m.competencia}</td><td data-label="Critério">{m.indice_aplicado}</td><td data-label="Base">{formatarMoeda(m.valor_base)}</td><td data-label="Fator">{Number(m.fator_aplicado).toLocaleString('pt-BR', { minimumFractionDigits: 4, maximumFractionDigits: 4 })}</td><td data-label="Atualizado">{formatarMoeda(m.valor_corrigido)}</td><td data-label="Juros">{formatarMoeda(m.juros_periodo)}</td><td data-label="Memória do trecho">{memoriaExibida(m.observacao)}</td></tr>)}</tbody></table></div>
    </div></details>
  </section>;
}
