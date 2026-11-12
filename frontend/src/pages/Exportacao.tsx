import { useState } from 'react';
import { Download, FileCode2, FileSpreadsheet, FileText } from 'lucide-react';
import { Button } from '../components/ui';
import { exportarExcel, exportarCsv, exportarPdf, mensagemErro } from '../services/api';
import { useCalculo } from '../contexts/useCalculo';
import { formatarMoeda, formatarData, downloadBlob } from '../utils/formatters';
import { componentesResultado, indiceAcumulado, memoriaExibida } from '../utils/componentes';
export function Exportacao() {
  const { state, buildCalculoJudicial } = useCalculo();
  const [ocupado, setOcupado] = useState<'pdf' | 'excel' | 'csv' | null>(null);
  const [erro, setErro] = useState('');
  const r = state.resultado;
  if (!r) return null;
  const componentes = componentesResultado(r);
  async function baixar(tipo: 'pdf' | 'excel' | 'csv') {
    setOcupado(tipo); setErro('');
    const formatos = { pdf: [exportarPdf, 'relatorio_calculo.pdf'], excel: [exportarExcel, 'memoria_calculo.xlsx'], csv: [exportarCsv, 'memoria_calculo.zip'] } as const;
    const [exportar, nome] = formatos[tipo];
    try { downloadBlob(await exportar(buildCalculoJudicial(), r?.premissas.base_indices?.sha256), nome); }
    catch (e) { setErro(await mensagemErro(e)); }
    finally { setOcupado(null); }
  }
  function relatorio() {
    if (!r) return;
    const linhas = ['# Memória de cálculo judicial', '', `Processo: ${r.dados_gerais.processo || 'Não informado'}`, `Requerente: ${r.dados_gerais.requerente}`, `Requerido: ${r.dados_gerais.requerido}`, `Data-base: ${formatarData(r.dados_gerais.data_base)}`, '',
      `Principal apurado: ${formatarMoeda(r.resumo.principal_apurado)}`, ...componentes.map(c => `${c.nome} (${c.periodo}): ${formatarMoeda(r.resumo.totais_componentes[c.chave])}`), ...(r.custas_despesas.length ? [`Custas e despesas processuais (IPCA-E): ${formatarMoeda(r.resumo.custas)}`] : []), `Total: ${formatarMoeda(r.resumo.total_atualizado)}`, '', '## Índices por parcela', '',
      ...r.parcelas.flatMap(p => [`### Parcela ${p.numero}`, ...componentes.map(c => { const v = p.componentes[c.chave]; return `${c.nome}: ${v.data_inicial ? `${indiceAcumulado(v)}; ${formatarMoeda(v.valor)}; de ${formatarData(v.data_inicial)} a ${formatarData(v.data_final)}` : 'Não incide'}`; }), '']),
      ...(r.custas_despesas.length ? ['## Custas e despesas processuais', '', ...r.custas_despesas.flatMap(item => [`### ${item.numero}. ${item.nome}`, `Data: ${formatarData(item.data)}`, `Valor original: ${formatarMoeda(item.valor_original)}`, `Fator IPCA-E: ${Number(item.fator_ipcae).toFixed(8)}`, `Correção: ${formatarMoeda(item.correcao_monetaria)}`, `Valor atualizado: ${formatarMoeda(item.valor_atualizado)}`, ...item.memoria.map(m => `- ${m.competencia}: base ${formatarMoeda(m.valor_base)}; fator ${Number(m.fator_aplicado).toFixed(8)}; atualizado ${formatarMoeda(m.valor_corrigido)}. ${memoriaExibida(m.observacao)}`), ''])] : []),
      '## Critérios e metodologia', '', ...(r.premissas.criterios || []).map(x => `- ${x}`), ...(r.premissas.metodologia || []).map(x => `- ${x}`), '', '## Memória dos trechos', '',
      ...r.memoria_mensal.map(m => `- Parcela ${m.parcela} — ${m.competencia} — ${m.indice_aplicado}: base ${formatarMoeda(m.valor_base)}; fator ${Number(m.fator_aplicado).toFixed(4)}; atualizado ${formatarMoeda(m.valor_corrigido)}; juros ${formatarMoeda(m.juros_periodo)}. ${memoriaExibida(m.observacao)}`), '', '## Premissas completas e entradas', '', '```json', JSON.stringify(r.premissas, null, 2), '```'];
    downloadBlob(new Blob([linhas.join('\n')], { type: 'text/markdown;charset=utf-8' }), 'memoria_calculo.md');
  }
  return <div className="export-actions" aria-label="Exportar cálculo">
    <Button variant="outline" className="export-icon" aria-label="Baixar Excel" title="Baixar Excel" disabled={Boolean(ocupado)} onClick={() => baixar('excel')}><FileSpreadsheet size={17} aria-hidden="true" /></Button>
    <Button variant="outline" className="export-icon" aria-label="Baixar CSV" title="Baixar CSV" disabled={Boolean(ocupado)} onClick={() => baixar('csv')}><FileCode2 size={17} aria-hidden="true" /></Button>
    <Button variant="outline" className="export-icon" aria-label="Memória em texto" title="Memória em texto" disabled={Boolean(ocupado)} onClick={relatorio}><FileText size={17} aria-hidden="true" /></Button>
    <Button disabled={Boolean(ocupado)} onClick={() => baixar('pdf')}><Download size={16} />{ocupado === 'pdf' ? 'Gerando PDF…' : 'Baixar PDF'}</Button>
    {ocupado && <span role="status" className="sr-only">Gerando arquivo…</span>}{erro && <p role="alert" className="feedback-error">{erro}</p>}
  </div>;
}
