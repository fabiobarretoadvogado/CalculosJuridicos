import { useEffect, useState, type FormEvent } from 'react';
import { Plus, Trash2, ArrowRight, Rows3, FileSpreadsheet } from 'lucide-react';
import { Button, Input, Textarea, Select } from '../components/ui';
import { executarCalculo, obterCriterios, mensagemErro, type CriteriosPublicos, type CalculoSimplificado } from '../services/api';
import { useCalculo } from '../contexts/useCalculo';
import { formatarData, formatarMoeda, formatarCompetencia } from '../utils/formatters';
import { Importacao } from './Importacao';
import { CustasDespesasForm } from '../components/CustasDespesasForm';
import { ResultadoPrincipal } from '../components/ResultadoPrincipal';
import { DescontosForm } from '../components/DescontosForm';
import { HonorariosPrincipaisForm, CumprimentoSentencaForm, DestaquesForm } from '../components/HonorariosPrincipaisForm';
import { obterCoberturaHonorarios, type CoberturaHonorarios } from '../services/api';
import { opcoesPerfisCalculo } from '../utils/perfisCalculo';

export function Processamento() {
  const { state, dispatch, buildCalculoJudicial } = useCalculo();
  const [criterios, setCriterios] = useState<CriteriosPublicos | null>(null);
  const [criteriosDescontos, setCriteriosDescontos] = useState<CriteriosPublicos | null>(null);
  const [erro, setErro] = useState('');
  const [carregando, setCarregando] = useState(false);
  const [importacaoAberta, setImportacaoAberta] = useState(false);
  const [coberturaHonorarios, setCoberturaHonorarios] = useState<CoberturaHonorarios | null>(null);
  const causaAtiva = state.honorariosSucumbenciais.aplicar && state.honorariosSucumbenciais.base === 'valor_causa';
  useEffect(() => {
    let ativo = true;
    if (!causaAtiva) return;
    obterCoberturaHonorarios().then(c => { if (ativo) setCoberturaHonorarios(c); }).catch(async e => { const msg = await mensagemErro(e); if (ativo) setErro(msg); });
    return () => { ativo = false; };
  }, [causaAtiva]);
  useEffect(() => {
    let ativo = true;
    obterCriterios(state.perfil).then(c => { if (ativo) setCriterios(c); }).catch(async e => { const msg = await mensagemErro(e); if (ativo) setErro(msg); });
    return () => { ativo = false; };
  }, [state.perfil]);
  const perfilDescontos = state.descontos.perfil || state.perfil;
  const descontosAtivos = state.descontos.itens.filter(item => item.aplicar !== false);
  useEffect(() => {
    let ativo = true;
    if (!descontosAtivos.length) return;
    obterCriterios(perfilDescontos).then(c => { if (ativo) setCriteriosDescontos(c); }).catch(async e => { const msg = await mensagemErro(e); if (ativo) setErro(msg); });
    return () => { ativo = false; };
  }, [perfilDescontos, descontosAtivos.length]);
  const coberturaDescontos = !descontosAtivos.length || criteriosDescontos?.perfil === perfilDescontos;
  const cobertura = criterios?.perfil === state.perfil ? criterios : null;
  const limiteDataBase = criterios
    ? [criterios.data_base_maxima, ...(state.custasDespesas.length ? [criterios.data_base_maxima_ipcae] : []),
        ...(descontosAtivos.length && criteriosDescontos?.perfil === perfilDescontos ? [criteriosDescontos.data_base_maxima] : []),
        ...(causaAtiva && coberturaHonorarios ? [coberturaHonorarios[state.honorariosSucumbenciais.indice].data_base_maxima] : [])].sort()[0]
    : undefined;
  const novo = state.perfil === 'selic_ipcae_2aa_v1';
  const fazenda1 = state.perfil === 'fazenda_publica_1_v1';
  const fazenda2 = state.perfil === 'fazenda_publica_2_v1';
  const cjf = state.perfil === 'selic_cjf_v1';
  const civil1 = state.perfil === 'ipca_taxa_legal_v1';
  const civil2 = state.perfil === 'civil_2_v1';
  const datasIndependentes = civil1 || civil2;
  const dataJurosNecessaria = !cjf && ['citacao', 'data_fixa'].includes(state.dadosGerais.criterio_inicio_juros);
  function atualizarParcela(index: number, campo: string, valor: string | null) {
    dispatch({ type: 'SET_PARCELAS', payload: state.parcelas.map((p, i) => i === index ? { ...p, [campo]: valor } : p) });
  }
  function geral(campo: string, valor: string | null) {
    dispatch({ type: 'SET_DADOS_GERAIS', payload: { ...state.dadosGerais, [campo]: valor } });
  }
  async function calcular(e: FormEvent) {
    e.preventDefault(); setErro('');
    if (!criterios || !cobertura || !coberturaDescontos || (causaAtiva && !coberturaHonorarios)) { setErro('Aguarde a consulta dos índices antes de calcular.'); return; }
    if (limiteDataBase && state.dadosGerais.data_base > limiteDataBase) { setErro(`Escolha uma data até ${formatarData(limiteDataBase)}.`); return; }
    if (!state.parcelas.length) { setErro('Adicione pelo menos uma parcela.'); return; }
    setCarregando(true);
    dispatch({ type: 'SET_RESULTADO', payload: null });
    try {
      const resultado = await executarCalculo(buildCalculoJudicial());
      dispatch({ type: 'SET_RESULTADO', payload: resultado });
    } catch (e) { setErro(await mensagemErro(e)); }
    finally { setCarregando(false); }
  }
  const principal = state.parcelas.reduce((s, p) => s + (Number(p.valor_bruto) || 0) - (Number(p.valor_pago_na_data) || 0), 0);
  const custasInformadas = state.custasDespesas.reduce((s, item) => s + (Number(item.valor) || 0), 0);
  const descontosInformados = descontosAtivos.reduce((s, item) => s + (Number(item.valor) || 0), 0);
  return <div className="processamento-page">
    <div className="page-intro"><p className="eyebrow">PRINCIPAL E HONORÁRIOS</p><h1>Atualize as parcelas.</h1><p>Informe a data final e os valores. Os critérios são aplicados automaticamente.</p></div>
    <form onSubmit={calcular} onInvalid={e => { const details = (e.target as HTMLElement).closest('details'); if (details) details.open = true; }}>
      <fieldset disabled={carregando}>
        <section className="sheet-panel" aria-labelledby="partes-titulo">
          <div className="section-heading"><h2 id="partes-titulo">Partes e observações</h2><span className="count-label">Identificação</span></div>
          <div className="field-grid processamento-partes-grid">
            <Input id="processo" label="Número do processo (opcional)" placeholder="Identifique o cálculo" value={state.dadosGerais.processo} onChange={e => geral('processo', e.target.value)} />
            <Input id="requerente" label="Requerente" value={state.dadosGerais.requerente} onChange={e => geral('requerente', e.target.value)} />
            <Input id="requerido" label="Requerido" value={state.dadosGerais.requerido} onChange={e => geral('requerido', e.target.value)} />
            <Input id="classe" label="Classe" value={state.dadosGerais.classe} onChange={e => geral('classe', e.target.value)} />
            <Input id="comarca" label="Comarca" value={state.dadosGerais.comarca} onChange={e => geral('comarca', e.target.value)} />
            <Input id="vara" label="Vara" value={state.dadosGerais.vara} onChange={e => geral('vara', e.target.value)} />
          </div>
          <div className="processamento-observacoes"><Textarea id="observacoes" label="Observações" placeholder="Informações que devem aparecer no PDF" value={state.dadosGerais.observacoes} onChange={e => geral('observacoes', e.target.value)} /></div>
        </section>
        <section className="sheet-panel processamento-dados" aria-labelledby="dados-titulo">
          <div className="section-heading"><h2 id="dados-titulo">Dados do cálculo</h2><span className="count-label">Base e critérios</span></div>
          <div className={`field-grid processamento-base-grid${cjf ? ' processamento-base-selic' : dataJurosNecessaria ? ' processamento-base-com-data' : ''}`}>
            <Input id="data-base" label="Atualizar até" type="date" min={criterios?.inicio} max={limiteDataBase} disabled={!cobertura} required value={state.dadosGerais.data_base} onChange={e => geral('data_base', e.target.value)} error={limiteDataBase && state.dadosGerais.data_base > limiteDataBase ? `Data máxima: ${formatarData(limiteDataBase)}.` : undefined} />
            <Select id="padrao-calculo" label="Padrão do cálculo" value={state.perfil} onChange={e => dispatch({ type: 'SET_PERFIL', payload: e.target.value as CalculoSimplificado['perfil'] })} options={opcoesPerfisCalculo(criterios?.perfis)} />
            {!cjf && <>
            <Select id="inicio-juros" label="Início dos juros" value={state.dadosGerais.criterio_inicio_juros} onChange={e => geral('criterio_inicio_juros', e.target.value)} options={[
              { value: 'vencimento', label: datasIndependentes ? 'Mesmo início da correção' : 'Vencimento de cada parcela' },
              { value: 'citacao', label: 'Citação' },
              { value: 'data_fixa', label: 'Data específica' },
              { value: 'por_parcela', label: 'Definir por parcela' },
            ]} />
            {dataJurosNecessaria && <Input id="data-inicio-juros" label={state.dadosGerais.criterio_inicio_juros === 'citacao' ? 'Data da citação' : 'Data de início dos juros'} type="date" required value={state.dadosGerais.data_inicial_juros || ''} onChange={e => geral('data_inicial_juros', e.target.value || null)} />}
            </>}
          </div>
          <details className="quiet-details criteria-note"><summary>Ver os critérios aplicados</summary>
            <p id="indices-disponiveis">{cjf && cobertura?.data_referencia_selic_maxima ? `SELIC disponível para a data-base de ${formatarData(cobertura.data_referencia_selic_maxima)}. Última competência disponível: ${formatarCompetencia(cobertura.ultima_competencia_selic_disponivel)}.` : limiteDataBase ? `Índices completos até ${formatarData(limiteDataBase)}.` : 'Consultando os índices…'}</p>
            {cjf && state.dadosGerais.data_base && <p>Data-base SELIC: {formatarData(`${state.dadosGerais.data_base.slice(0, 7)}-01`)}. Referência mensal, sem atualização diária dentro do mês. Custas e demais operações usam a data final informada no campo acima.</p>}
            {datasIndependentes ? <p>Juros e correção têm datas independentes: os juros podem começar antes da correção. O campo da data de cada parcela indica o início da correção pelo IPCA.</p> : !cjf && <p>Início dos juros: aplica-se {novo ? 'à poupança até 08/12/2021 e aos juros de 2% ao ano a partir de 10/09/2025' : 'à poupança nos períodos em que ela incide'}, respeitado o vencimento da parcela. Não altera os períodos do IPCA-E ou da SELIC.</p>}
            {civil1 ? <p>IPCA: fatores mensais geométricos. Taxa Legal: taxas oficiais do Banco Central, acumuladas de forma simples, sobre o principal corrigido. Não há SELIC integral adicional nem subtração direta de percentuais.</p> : civil2 ? <p>IPCA: fatores mensais geométricos. Juros de mora: 1% ao mês, de forma simples e proporcional aos dias, sobre o principal corrigido.</p> : cjf ? <p>SELIC simples por competência: atualização e juros em todo o período. A taxa do mês é aplicada no mês seguinte (Manual de Cálculos da Justiça Federal).</p> : fazenda1 ? <ul className="criteria-list">
              <li><strong>A partir de 01/07/2009:</strong> IPCA-E e poupança.</li>
            </ul> : fazenda2 ? <ul className="criteria-list">
              <li><strong>01/07/2009 a 08/12/2021:</strong> IPCA-E e poupança.</li>
              <li><strong>A partir de 09/12/2021:</strong> SELIC (atualização e juros).</li>
            </ul> : novo ? <ul className="criteria-list">
              <li><strong>01/07/2009 a 08/12/2021:</strong> IPCA-E e poupança.</li>
              <li><strong>09/12/2021 a 09/09/2025:</strong> SELIC (atualização e juros).</li>
              <li><strong>A partir de 10/09/2025:</strong> IPCA-E + juros simples de 2% ao ano, limitado à SELIC quando inferior.</li>
            </ul> : <ul className="criteria-list">
              <li><strong>01/07/2009 a 08/12/2021:</strong> IPCA-E e poupança (Tema 905).</li>
              <li><strong>09/12/2021 a 09/09/2025:</strong> SELIC (atualização e juros).</li>
              <li><strong>A partir de 10/09/2025:</strong> IPCA-E oficial do IBGE, formado pelo IPCA-15, e poupança.</li>
            </ul>}
            <p>{civil1 ? 'Dias corridos: inclui o início e exclui a data-base, conforme a Calculadora do Cidadão. Meses parciais são proporcionais; taxas legais com seis casas decimais. Não estimar IPCA ainda não publicado.' : civil2 ? 'Dias corridos: inclui o início e exclui a data-base. Meses parciais são proporcionais; os juros não são capitalizados. Não estimar IPCA ainda não publicado.' : cjf ? 'Meses futuros ou sem índices completos permanecem bloqueados.' : 'Meses parciais: proporcionais aos dias corridos, com divisão nas transições. Meses sem índices completos permanecem bloqueados.'}</p>
            <p>Multa: percentual sobre o saldo após pagamento no vencimento. Recebe a mesma atualização e os mesmos juros da parcela. O saldo do formulário não inclui multa ou encargos.</p>
            {criterios && <p>Base consultada em {formatarData(criterios.atualizado_em)}. <a className="underline" href={civil1 ? criterios.fontes.resolucao_taxa_legal : civil2 ? criterios.fontes.ipca : cjf ? criterios.fontes.manual_cjf : criterios.fontes.ipcae_ibge || criterios.fontes.ipcae} target="_blank" rel="noreferrer">{civil1 ? 'Metodologia oficial da Taxa Legal' : civil2 ? 'IPCA oficial do Banco Central' : cjf ? 'Manual de Cálculos da Justiça Federal' : 'IPCA-E oficial do IBGE'}</a>.</p>}
          </details>
        </section>
        <section className="sheet-panel" aria-labelledby="parcelas-titulo">
          <div className="section-heading"><div><h2 id="parcelas-titulo">Parcelas</h2><p>{datasIndependentes ? 'Informe o início da correção pelo IPCA. O início dos juros é informado separadamente, mesmo que anterior.' : 'Uma data e um valor para cada vencimento.'}</p></div><span className="count-label">{state.parcelas.length} parcela{state.parcelas.length !== 1 ? 's' : ''}</span></div>
          {!state.parcelas.length && <div className="costs-empty"><Rows3 size={20} /><span>Adicione a primeira parcela ou importe uma planilha.</span></div>}
          {state.parcelas.map((p, i) => <div key={p.numero} className="parcel-line">
            <div className="parcel-main">
              <span className="parcel-number" aria-label={`Parcela ${p.numero}`}>{String(p.numero).padStart(2, '0')}</span>
              <Input id={`historico-${p.numero}`} label="Descrição" value={p.historico} onChange={e => atualizarParcela(i, 'historico', e.target.value)} />
              <Input id={`vencimento-${p.numero}`} label={datasIndependentes ? 'Início da correção' : 'Vencimento'} type="date" required min={criterios?.inicio} max={state.dadosGerais.data_base || undefined} value={p.data_vencimento} onChange={e => atualizarParcela(i, 'data_vencimento', e.target.value)} />
              <Input id={`valor-${p.numero}`} label="Valor original (R$)" type="number" required min="0.01" step="0.01" placeholder="0,00" value={p.valor_bruto} onChange={e => atualizarParcela(i, 'valor_bruto', e.target.value)} />
              <Input id={`pago-${p.numero}`} label="Pago no vencimento (R$)" type="number" required min="0" max={p.valor_bruto || undefined} step="0.01" value={p.valor_pago_na_data} onChange={e => atualizarParcela(i, 'valor_pago_na_data', e.target.value)} />
              <Input id={`saldo-${p.numero}`} label="Saldo (R$)" readOnly className="parcel-balance" value={p.valor_bruto ? formatarMoeda((Number(p.valor_bruto) || 0) - (Number(p.valor_pago_na_data) || 0)) : '—'} />
              <Input id={`multa-${p.numero}`} label="Multa (%)" type="number" min="0" max="100" step="0.0001" value={p.multa_percentual ?? '0'} onChange={e => atualizarParcela(i, 'multa_percentual', e.target.value || '0')} />
              <button type="button" className="icon-button" aria-label={`Remover parcela ${p.numero}`} onClick={() => dispatch({ type: 'SET_PARCELAS', payload: state.parcelas.filter((_, j) => i !== j) })}><Trash2 size={17} /></button>
            </div>
            {state.dadosGerais.criterio_inicio_juros === 'por_parcela' && <div className="parcel-interest"><Input id={`juros-${p.numero}`} label="Início dos juros (opcional)" type="date" value={p.data_inicial_juros || ''} onChange={e => atualizarParcela(i, 'data_inicial_juros', e.target.value || null)} hint={datasIndependentes ? 'Pode ser anterior à correção. Em branco: mesmo início da correção.' : 'Em branco: vencimento da parcela.'} /></div>}
          </div>)}
          <div className="parcel-toolbar" role="group" aria-label="Adicionar parcelas">
            <Button type="button" variant="ghost" size="sm" onClick={() => dispatch({ type: 'SET_PARCELAS', payload: [...state.parcelas, { numero: Math.max(0, ...state.parcelas.map(p => p.numero)) + 1, historico: '', data_vencimento: '', valor_bruto: '', valor_pago_na_data: '0', multa_percentual: '0', data_inicial_juros: null }] })}><Plus size={15} />Adicionar parcela</Button>
            <Button type="button" variant="ghost" size="sm" aria-expanded={importacaoAberta} aria-controls="importacao-parcelas" onClick={() => setImportacaoAberta(aberta => !aberta)}><FileSpreadsheet size={15} />Importar Excel</Button>
          </div>
          <Importacao aberto={importacaoAberta} />
        </section>
        <DescontosForm operacao={state.descontos} perfilPrincipal={state.perfil} dataBase={state.dadosGerais.data_base}
          inicio={criteriosDescontos?.perfil === perfilDescontos ? criteriosDescontos.inicio : undefined}
          onChange={payload => dispatch({ type: 'SET_DESCONTOS', payload })} />
        <HonorariosPrincipaisForm config={state.honorariosSucumbenciais} dataBase={state.dadosGerais.data_base} onChange={payload => dispatch({ type: 'SET_HONORARIOS', payload })} />
        <CumprimentoSentencaForm config={state.cumprimentoSentenca} onChange={payload => dispatch({ type: 'SET_CUMPRIMENTO', payload })} />
        <DestaquesForm config={state.cumprimentoSentenca} onChange={payload => dispatch({ type: 'SET_CUMPRIMENTO', payload })} />
        <CustasDespesasForm
          idPrefix="principal"
          itens={state.custasDespesas}
          dataBase={state.dadosGerais.data_base}
          onChange={itens => dispatch({ type: 'SET_CUSTAS_DESPESAS', payload: itens })}
        />
        {erro && <div role="alert" className="feedback-error">{erro}</div>}
        <div className="calculation-actions"><div className="calculation-totals"><p>Principal após pagamentos<strong>{formatarMoeda(principal)}</strong></p>{state.descontos.itens.length > 0 && <p>Descontos informados<strong>− {formatarMoeda(descontosInformados)}</strong></p>}{state.custasDespesas.length > 0 && <p>Custas e despesas informadas<strong>{formatarMoeda(custasInformadas)}</strong></p>}</div><Button type="submit" disabled={carregando || !cobertura || !coberturaDescontos || !criterios || (causaAtiva && !coberturaHonorarios) || !state.parcelas.length || Boolean(limiteDataBase && state.dadosGerais.data_base > limiteDataBase)}>{carregando ? 'Calculando…' : 'Calcular atualização'}<ArrowRight size={17} /></Button></div>
      </fieldset>
    </form>
    <ResultadoPrincipal />
  </div>;
}

