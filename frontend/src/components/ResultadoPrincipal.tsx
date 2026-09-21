import { useEffect, useRef } from 'react';
import { Button, DataTable, type Column } from './ui';
import { useCalculo } from '../contexts/useCalculo';
import { formatarMoeda, formatarData, formatarCompetencia } from '../utils/formatters';
import type { MemoriaMensal } from '../services/api';
import { Exportacao } from '../pages/Exportacao';
import { componentesResultado, indiceAcumulado, memoriaExibida } from '../utils/componentes';
import { CustasDespesasResultado } from './CustasDespesasResultado';
import { DescontosResultado } from './DescontosResultado';
import { HonorariosPrincipaisResultado } from './HonorariosPrincipaisResultado';

export function ResultadoPrincipal() {
  const { state } = useCalculo();
  const section = useRef<HTMLElement>(null);
  const r = state.resultado;
  useEffect(() => {
    if (!r) return;
    section.current?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
    section.current?.focus({ preventScroll: true });
  }, [r]);
  if (!r) return null;
  const civil1 = r.premissas.entrada.perfil === 'ipca_taxa_legal_v1';
  const civil2 = r.premissas.entrada.perfil === 'civil_2_v1';
  const datasIndependentes = civil1 || civil2;
  const cjf = r.premissas.entrada.perfil === 'selic_cjf_v1';
  const referenciaSelic = cjf ? r.premissas.data_referencia_selic : undefined;
  const outrasOperacoes = r.custas_despesas.length > 0 || Boolean(r.honorarios_sucumbenciais?.data_protocolo) || Boolean(r.descontos && r.descontos.premissas.entrada?.perfil !== 'selic_cjf_v1');
  const componentes = componentesResultado(r);
  const subtotalParcelas = r.parcelas.reduce((soma, parcela) => soma + Number(parcela.total_parcela), 0);
  const columns: Column<MemoriaMensal>[] = [
    { key: 'parcela', header: 'Parcela', render: m => m.parcela },
    { key: 'competencia', header: 'Mês', render: m => m.competencia },
    { key: 'indice', header: 'Critério', render: m => m.indice_aplicado },
    { key: 'base', header: 'Base', align: 'right', render: m => formatarMoeda(m.valor_base) },
    { key: 'fator', header: 'Fator', render: m => Number(m.fator_aplicado).toLocaleString('pt-BR', { minimumFractionDigits: 4, maximumFractionDigits: 4 }) },
    { key: 'corrigido', header: 'Atualizado', align: 'right', render: m => formatarMoeda(m.valor_corrigido) },
    { key: 'juros', header: 'Juros', align: 'right', render: m => formatarMoeda(m.juros_periodo) },
    { key: 'observacao', header: 'Memória do trecho', render: m => <span className="block min-w-60 whitespace-normal">{datasIndependentes ? m.observacao : memoriaExibida(m.observacao)}</span> },
  ];
  return <section ref={section} className="principal-result" tabIndex={-1} aria-labelledby="principal-resultado-titulo">
    <div className="section-heading"><div><h2 id="principal-resultado-titulo">Resultado do cálculo</h2><p>{r.parcelas.length} parcela{r.parcelas.length !== 1 ? 's' : ''} · Data-base{referenciaSelic ? ' SELIC' : ''} {formatarData(referenciaSelic || r.dados_gerais.data_base)}{referenciaSelic ? ` · Último índice aplicado: ${formatarCompetencia(r.premissas.ultima_competencia_selic)}` : ''}{r.dados_gerais.processo ? ` · Processo ${r.dados_gerais.processo}` : ''}</p>{referenciaSelic && outrasOperacoes && referenciaSelic !== r.dados_gerais.data_base && <p>Data final das demais operações: {formatarData(r.dados_gerais.data_base)}.</p>}</div></div>
    {r.chave_recuperacao && <p className="recovery-key"><span>Chave para reeditar este cálculo</span><strong>{r.chave_recuperacao}</strong></p>}
    <section aria-label="Resumo do cálculo">
      <div className="result-head"><div><h2>Total atualizado</h2><p className="result-total">{formatarMoeda(r.resumo.total_atualizado)}</p></div><div className="result-actions"><Button variant="outline" onClick={() => { window.scrollTo({ top: 0, behavior: 'smooth' }); document.getElementById('processo')?.focus({ preventScroll: true }); }}>Editar dados</Button><Exportacao pdfOnly /></div></div>
      <div className="result-metrics">{[
        ['Principal apurado', r.resumo.principal_apurado],
        ...componentes.map(c => [`${c.nome} · ${c.periodo.toLowerCase()}`, r.resumo.totais_componentes[c.chave]]),
        ...(r.descontos ? [['Descontos abatidos · atualizados', `-${r.resumo.abatimentos}`]] : []),
        ...(r.honorarios_sucumbenciais ? [['Honorários sucumbenciais', r.honorarios_sucumbenciais.valor]] : []),
        ...(r.cumprimento_sentenca?.aplicar_multa ? [['Multa · art. 523', r.cumprimento_sentenca.multa]] : []),
        ...(r.cumprimento_sentenca?.aplicar_honorarios ? [['Honorários · art. 523', r.cumprimento_sentenca.honorarios]] : []),
        ...(r.custas_despesas.length ? [['Custas e despesas · IPCA-E', r.resumo.custas]] : []),
      ].map(([label, valor]) => <div key={label}><p>{label}</p><strong>{formatarMoeda(valor)}</strong></div>)}</div>
      <p className="result-explanation">{civil1 ? 'Civil 1: IPCA e Taxa Legal oficial em períodos independentes. Juros simples sobre o principal corrigido, sem SELIC integral adicional. Inclui o início e exclui a data-base.' : civil2 ? 'Civil 2: IPCA e juros de mora simples de 1% ao mês em períodos independentes. Os juros incidem sobre o principal corrigido. Inclui o início e exclui a data-base.' : cjf ? 'SELIC mensal simples: a taxa de cada competência é computada no mês seguinte. A data-base SELIC identifica o primeiro dia desse mês; não representa atualização diária até o seu último dia.' : r.premissas.entrada.perfil === 'fazenda_publica_1_v1' ? 'Fazenda Pública 1: IPCA-E e poupança desde 01/07/2009, sem troca de regime.' : r.premissas.entrada.perfil === 'fazenda_publica_2_v1' ? 'Fazenda Pública 2: IPCA-E e poupança até 08/12/2021; SELIC como índice único a partir de 09/12/2021.' : r.premissas.entrada.perfil === 'selic_ipcae_2aa_v1' ? 'Fazenda Pública 4: IPCA-E e poupança até 08/12/2021; SELIC de 09/12/2021 a 09/09/2025; depois IPCA-E com juros simples de 2% ao ano, limitado à SELIC quando inferior.' : 'Fazenda Pública 3: IPCA-E e poupança até 08/12/2021; SELIC de 09/12/2021 a 09/09/2025; depois IPCA-E e poupança.'}{r.custas_despesas.length ? ' As custas e despesas são corrigidas separadamente apenas pelo IPCA-E e somadas ao total final.' : ''}</p>
    </section>
    {r.descontos && <p className="result-explanation">Parcelas atualizadas {formatarMoeda(subtotalParcelas)} − descontos abatidos {formatarMoeda(r.resumo.abatimentos)} = crédito líquido {formatarMoeda(subtotalParcelas - Number(r.resumo.abatimentos))}, antes dos honorários, acréscimos do cumprimento e custas.</p>}
    {r.alertas.length > 0 && <div className="feedback-error" role="status">{r.alertas.map(alerta => <p key={alerta}>{alerta}</p>)}</div>}
    <div className="section-heading"><h2>Valores por parcela</h2><span className="count-label">{r.parcelas.length} registro{r.parcelas.length !== 1 ? 's' : ''}</span></div>
    <p className="component-legend">{civil1 ? 'IPCA: fator multiplicador. Taxa Legal: taxa acumulada simples com seis casas decimais. As datas de cada encargo são exibidas separadamente.' : civil2 ? 'IPCA: fator multiplicador. Juros de 1% ao mês: taxa acumulada simples com seis casas decimais. As datas de cada encargo são exibidas separadamente.' : 'Cada período mostra o índice acumulado e o acréscimo em reais. IPCA-E usa fator multiplicador; SELIC e poupança usam taxa acumulada simples.'} “Não incide” indica um período fora das datas da parcela.</p>
    <div className="result-table-wrap" tabIndex={0} role="region" aria-label="Valores e índices por parcela"><table className="result-table component-table"><thead><tr>
      {['Nº', 'Descrição', datasIndependentes ? 'Correção desde' : 'Vencimento', 'Principal'].map(t => <th scope="col" key={t}>{t}</th>)}
      {componentes.map(c => <th scope="col" key={c.chave}>{c.nome}<small>{c.periodo}</small></th>)}
      <th scope="col">Total</th>
    </tr></thead><tbody>{r.parcelas.map(p => <tr key={p.numero}>
      <td data-label="Nº">{p.numero}</td><td data-label="Descrição">{p.historico || '—'}</td>
      <td data-label={datasIndependentes ? 'Correção desde' : 'Vencimento'}>{formatarData(p.data_vencimento)}</td><td data-label="Principal">{formatarMoeda(p.valor_apurado)}</td>
      {componentes.map(c => { const valor = p.componentes[c.chave]; return <td key={c.chave} data-label={`${c.nome} · ${c.periodo}`}>
        {valor.data_inicial ? <>
          {datasIndependentes && <small className="applied-index">{formatarData(valor.data_inicial)} a {formatarData(valor.data_final)}</small>}
          <small className="applied-index" title={`De ${formatarData(valor.data_inicial)} a ${formatarData(valor.data_final)}. Base: ${formatarMoeda(valor.base_calculo)}.`}>{indiceAcumulado(valor, ['taxa_legal', 'juros_1am'].includes(c.chave) ? 6 : 4)}</small>
          {formatarMoeda(valor.valor)}
          {c.chave === 'multa_parcela' && p.multa_detalhes && <small className="applied-index">Nominal: {formatarMoeda(p.multa_detalhes.valor_original)} · Atualização: {formatarMoeda(p.multa_detalhes.correcao_monetaria)} · Juros: {formatarMoeda(p.multa_detalhes.juros_mora)}</small>}
        </> : <span className="not-applied">Não incide</span>}
      </td>; })}
      <td data-label="Total da parcela">{formatarMoeda(p.total_parcela)}</td>
    </tr>)}</tbody><tfoot><tr><td colSpan={3}>Total das parcelas</td>{[r.resumo.principal_apurado, ...componentes.map(c => r.resumo.totais_componentes[c.chave]), subtotalParcelas].map((v,i)=><td key={i}>{formatarMoeda(v)}</td>)}</tr></tfoot></table></div>
    <p className="component-legend">{datasIndependentes ? `${civil1 ? 'Taxa Legal' : 'Juros de 1% ao mês'} com seis casas decimais; fatores e bases com precisão integral no cálculo.` : 'Índices exibidos com quatro casas decimais.'} O cálculo conserva a precisão integral e concilia os centavos entre as colunas. As bases e os períodos efetivos constam na memória mensal.</p>
    <DescontosResultado resultado={r.descontos} />
    {(r.premissas.selecao_descontos || []).filter(item => item.aplicar === false).map(item => <p className="component-legend" key={item.numero}>Não abatido · {item.descricao || `Pagamento ${item.numero}`} · {item.data ? formatarData(item.data) : 'data não informada'} · {item.valor ? formatarMoeda(item.valor) : 'valor não informado'}.</p>)}
    <HonorariosPrincipaisResultado resultado={r} />
    <CustasDespesasResultado itens={r.custas_despesas} />
    {r.dados_gerais.observacoes && <p className="report-note whitespace-pre-line">{r.dados_gerais.observacoes}</p>}
    <div className="mt-7">
      <details className="audit-details"><summary>Critérios e fontes</summary><div className="audit-content"><ul>{[...(r.premissas.criterios || []), ...(r.premissas.metodologia || [])].map(t => <li key={t}>{t}</li>)}</ul><div className="source-links">{Object.entries(r.premissas.fontes || {}).map(([nome, url]) => <a key={nome} href={url} target="_blank" rel="noreferrer">{nome.replaceAll('_', ' ')}</a>)}</div></div></details>
      <details className="audit-details"><summary>Conferir a memória mensal</summary><div className="audit-content"><DataTable columns={columns} data={r.memoria_mensal} /></div></details>
      <Exportacao />
    </div>
  </section>;
}
