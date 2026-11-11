import { useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { Button } from '../components/ui';
import { mensagemErro } from '../services/api';
import { atualizarIndices, avisarIndicesAtualizados, nomeBaseIndices, obterCatalogoIndices, type CatalogoIndices, type SerieIndice } from '../services/indices';
import { formatarCompetencia, formatarData } from '../utils/formatters';
import { useIndicesVersion } from '../utils/useIndicesVersion';

function Series({ series }: { series: SerieIndice[] }) {
  return <div className="result-table-wrap"><table className="result-table indices-table">
    <thead><tr><th>Índice</th><th>Primeiro registro</th><th>Último registro</th><th>Consulta da fonte</th></tr></thead>
    <tbody>{series.map(serie => <tr key={serie.id}>
      <td data-label="Índice"><strong>{serie.nome}</strong><p className="indices-note">{serie.observacao}</p>{serie.fonte && <a href={serie.fonte} target="_blank" rel="noreferrer">Consultar fonte oficial</a>}</td>
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
