import { useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { Button } from '../components/ui';
import { mensagemErro } from '../services/api';
import { atualizarIndices, avisarIndicesAtualizados, nomeBaseIndices, obterCatalogoIndices, type CatalogoIndices, type SerieIndice } from '../services/indices';
import { formatarCompetencia, formatarData } from '../utils/formatters';
import { useIndicesVersion } from '../utils/useIndicesVersion';
import { guiaCriterios } from '../utils/guiaCriterios';

function Series({ series }: { series: SerieIndice[] }) {
  return <div className="result-table-wrap"><table className="result-table indices-table indices-series-table">
    <thead><tr><th>Índice</th><th>Primeiro registro</th><th>Último registro</th><th>Consulta da fonte</th></tr></thead>
    <tbody>{series.map(serie => <tr key={serie.id}>
      <td data-label="Índice"><div className="indices-series-title"><strong>{serie.nome}</strong>{serie.fonte && <a href={serie.fonte} target="_blank" rel="noreferrer" aria-label={`Consultar fonte oficial de ${serie.nome}`}>Fonte oficial</a>}</div><p className="indices-note">{serie.observacao}</p></td>
      <td data-label="Primeiro registro">{serie.unidade === 'competencia' ? formatarCompetencia(serie.inicio) : formatarData(serie.inicio)}</td>
      <td data-label="Último registro">{serie.unidade === 'competencia' ? formatarCompetencia(serie.fim) : formatarData(serie.fim)}</td>
      <td data-label="Consulta da fonte">{serie.consulta_em ? formatarData(serie.consulta_em) : 'Não registrada'}</td>
    </tr>)}</tbody>
  </table></div>;
}

export function Indices() {
  const [catalogo, setCatalogo] = useState<CatalogoIndices | null>(null);
  const [erro, setErro] = useState('');
  const [mensagem, setMensagem] = useState('');
  const [atualizando, setAtualizando] = useState(false);
  const [criterioSelecionado, setCriterioSelecionado] = useState('todos');
  const version = useIndicesVersion();
  useEffect(() => {
    let active = true;
    obterCatalogoIndices().then(c => { if (active) setCatalogo(c); }).catch(async e => {
      const message = await mensagemErro(e); if (active) setErro(message);
    });
    return () => { active = false; };
  }, [version]);

  async function verificar() {
    setAtualizando(true); setErro(''); setMensagem('');
    try {
      const result = await atualizarIndices();
      setCatalogo(await obterCatalogoIndices());
      setMensagem(result.atualizado ? 'Índices atualizados. Os próximos cálculos usarão a nova base.' : result.mensagem || 'Os índices disponíveis já estão em uso.');
      if (result.atualizado) avisarIndicesAtualizados();
    } catch (e) { setErro(await mensagemErro(e)); }
    finally { setAtualizando(false); }
  }

  return <div className="indices-page">
    <div className="page-intro"><p className="eyebrow">BASES ECONÔMICAS</p><h1>Índices disponíveis</h1><p>Consulte os períodos publicados e até quando cada padrão permite atualizar um cálculo.</p></div>
    <div className="indices-actions"><div><strong>{catalogo ? nomeBaseIndices(catalogo.base) : 'Carregando índices…'}</strong>
      <p className="indices-note">{catalogo?.ultima_verificacao ? `Última verificação: ${new Date(catalogo.ultima_verificacao).toLocaleString('pt-BR')}` : 'A consulta mostra os dados disponíveis neste computador.'}</p>
    </div><Button variant="ghost" onClick={verificar} disabled={atualizando || !catalogo?.atualizacoes_configuradas}><RefreshCw size={16} className={atualizando ? 'indices-spin' : ''} />{atualizando ? 'Verificando…' : 'Verificar e atualizar índices'}</Button></div>
    {mensagem && <p className="criteria-note" role="status">{mensagem}</p>}
    {erro && <p className="feedback-error" role="alert">{erro}</p>}
    {catalogo?.aviso && <p className="feedback-error" role="alert">{catalogo.aviso}</p>}
    {catalogo?.erro_atualizacao && !erro && <p className="criteria-note">{catalogo.erro_atualizacao}</p>}
    <section className="sheet-panel" aria-labelledby="guia-criterios-titulo">
      <div className="section-heading"><div><h2 id="guia-criterios-titulo">Critérios por período</h2><p>Compare como o programa aplica cada padrão antes de escolhê-lo.</p></div></div>
      <p className="indices-note">Confira o título judicial e as datas de início de cada encargo. Os períodos abaixo descrevem as regras do programa; a cobertura disponível pode limitar o cálculo. Nos padrões civis, correção e juros podem ter datas de início diferentes.</p>
      <div className="indices-filter"><label htmlFor="filtro-criterios">Exibir critério</label><select id="filtro-criterios" value={criterioSelecionado} onChange={e => setCriterioSelecionado(e.target.value)}><option value="todos">Todos os critérios</option>{guiaCriterios.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}</select></div>
      <div className="result-table-wrap" tabIndex={0} role="region" aria-label="Critérios de cálculo por período"><table className="result-table indices-table indices-criteria-table"><thead><tr><th scope="col">Critério</th><th scope="col">Períodos e regras aplicadas</th></tr></thead><tbody>
        {guiaCriterios.filter(c => criterioSelecionado === 'todos' || c.id === criterioSelecionado).map(c => <tr key={c.id}><td data-label="Critério"><strong>{c.nome}</strong></td><td data-label="Períodos e regras aplicadas"><ul className="indices-criteria-periods">{c.faixas.map(f => <li key={f.periodo}><strong>{f.periodo}:</strong> {f.regra}</li>)}</ul></td></tr>)}
      </tbody></table></div>
    </section>
    {catalogo && <>
      <section className="sheet-panel"><div className="section-heading"><h2>Séries oficiais</h2></div><Series series={catalogo.series.filter(s => !s.legado)} /></section>
      <section className="sheet-panel"><div className="section-heading"><h2>Limites para calcular</h2></div><p className="indices-note">A cobertura depende das séries exigidas por cada padrão. Custas e descontos podem reduzir o limite do cálculo.</p>
        <div className="result-table-wrap"><table className="result-table indices-table"><thead><tr><th>Padrão</th><th>Atualizar até</th><th>Observação</th></tr></thead><tbody>
          {catalogo.perfis.map(perfil => <tr key={perfil.id}><td data-label="Padrão">{perfil.nome}</td><td data-label="Atualizar até">{formatarData(perfil.data_base_maxima)}</td><td data-label="Observação">{perfil.ultima_competencia_selic ? `Última competência SELIC aplicável: ${formatarCompetencia(perfil.ultima_competencia_selic)}` : perfil.observacao || 'Conforme os critérios do padrão'}</td></tr>)}
        </tbody></table></div>
      </section>
      <p className="indices-note">A atualização dos índices preserva os cálculos já registrados. Para aplicar a nova base a um cálculo anterior, abra seus dados e calcule novamente.</p>
    </>}
  </div>;
}
