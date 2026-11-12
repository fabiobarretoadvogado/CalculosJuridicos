import { useEffect, useRef } from 'react';
import { useCalculo } from '../contexts/useCalculo';
import { formatarMoeda, formatarData, formatarCompetencia } from '../utils/formatters';
import { Exportacao } from '../pages/Exportacao';
import { DescontosResultado } from './DescontosResultado';
import { HonorariosPrincipaisResultado } from './HonorariosPrincipaisResultado';
import { formatarValorOrigem } from '../utils/moedasHistoricas';

export function ResultadoPrincipal() {
  const { state } = useCalculo();
  const section = useRef<HTMLElement>(null);
  const r = state.resultado;
  const resultadoAnterior = useRef(r);
  useEffect(() => {
    const resultadoNovo = r !== resultadoAnterior.current;
    resultadoAnterior.current = r;
    if (!r || !resultadoNovo) return;
    section.current?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
    section.current?.focus({ preventScroll: true });
  }, [r]);
  if (!r) return null;
  const referenciaSelic = r.premissas.entrada.perfil === 'selic_cjf_v1' ? r.premissas.data_referencia_selic : undefined;
  const outrasOperacoes = r.custas_despesas.length > 0 || Boolean(r.honorarios_sucumbenciais?.data_protocolo) || Boolean(r.descontos && r.descontos.premissas.entrada?.perfil !== 'selic_cjf_v1');
  return <section ref={section} className="principal-result" tabIndex={-1} aria-labelledby="principal-resultado-titulo">
    <div className="section-heading"><div><h2 id="principal-resultado-titulo">Resultado do cálculo</h2><p>{r.parcelas.length} parcela{r.parcelas.length !== 1 ? 's' : ''} · Data-base{referenciaSelic ? ' SELIC' : ''} {formatarData(referenciaSelic || r.dados_gerais.data_base)}{referenciaSelic ? ` · Último índice aplicado: ${formatarCompetencia(r.premissas.ultima_competencia_selic)}` : ''}{r.dados_gerais.processo ? ` · Processo ${r.dados_gerais.processo}` : ''}{r.chave_recuperacao && <span className="result-recovery-key"> · Chave para reeditar este cálculo: <strong>{r.chave_recuperacao}</strong></span>}</p>{referenciaSelic && outrasOperacoes && referenciaSelic !== r.dados_gerais.data_base && <p>Data final das demais operações: {formatarData(r.dados_gerais.data_base)}.</p>}</div></div>
    <section aria-label="Resumo do cálculo">
      <div className="result-head"><div><h2>Total atualizado</h2><p className="result-total">{formatarMoeda(r.resumo.total_atualizado)}</p></div><div className="result-actions"><Exportacao /></div></div>
    </section>
    {r.alertas.length > 0 && <div className="feedback-error" role="status">{r.alertas.map(alerta => <p key={alerta}>{alerta}</p>)}</div>}
    <DescontosResultado resultado={r.descontos} />
    {(r.premissas.selecao_descontos || []).filter(item => item.aplicar === false).map(item => <p className="component-legend" key={item.numero}>Não abatido · {item.descricao || `Pagamento ${item.numero}`} · {item.data ? formatarData(item.data) : 'data não informada'} · {item.valor ? formatarValorOrigem(Number(item.valor), item.data || '') : 'valor não informado'}.</p>)}
    <HonorariosPrincipaisResultado resultado={r} />
    {r.dados_gerais.observacoes && <p className="report-note whitespace-pre-line">{r.dados_gerais.observacoes}</p>}
  </section>;
}
