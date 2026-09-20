import { useState } from 'react';
import { Button } from '../components/ui';
import { importarExcel, obterTemplateModelo, mensagemErro, type ParcelaSimplificada } from '../services/api';
import { useCalculo } from '../contexts/useCalculo';
import { downloadBlob } from '../utils/formatters';

export function Importacao({ aberto }: { aberto: boolean }) {
  const { state, dispatch } = useCalculo();
  const [erro, setErro] = useState('');
  const [ocupado, setOcupado] = useState(false);
  const [sucesso, setSucesso] = useState('');
  async function importar(file?: File) {
    if (!file) return;
    setOcupado(true); setErro(''); setSucesso('');
    try {
      const data = await importarExcel(file) as { parcelas: ParcelaSimplificada[] };
      const offset = Math.max(0, ...state.parcelas.map(p => p.numero));
      dispatch({ type: 'SET_PARCELAS', payload: [...state.parcelas, ...data.parcelas.map((p, i) => ({ ...p, numero: offset + i + 1 }))] });
      const temJurosInformados = data.parcelas.some(p => p.data_inicial_juros);
      if (temJurosInformados && state.dadosGerais.criterio_inicio_juros === 'vencimento') {
        dispatch({ type: 'SET_DADOS_GERAIS', payload: { ...state.dadosGerais, criterio_inicio_juros: 'por_parcela' } });
      }
      setSucesso(`${data.parcelas.length} parcela(s) adicionada(s). Confira as datas antes de calcular.${temJurosInformados ? ' A planilha contém datas de juros por parcela; confira a opção em Critérios do cálculo.' : ''}`);
    } catch (e) { setErro(await mensagemErro(e)); }
    finally { setOcupado(false); }
  }
  async function modelo() {
    setErro(''); setOcupado(true);
    try { downloadBlob(await obterTemplateModelo(), 'modelo_parcelas.xlsx'); }
    catch (e) { setErro(await mensagemErro(e)); }
    finally { setOcupado(false); }
  }
  return <section id="importacao-parcelas" className="parcel-import text-sm" hidden={!aberto} aria-labelledby="importacao-titulo" aria-busy={ocupado}>
    <h3 id="importacao-titulo">Importação de parcelas</h3>
    <p className="parcel-import-note">Preencha o modelo e selecione a planilha. As parcelas serão adicionadas às já cadastradas.</p>
    <div className="parcel-import-actions">
      <Button type="button" variant="outline" size="sm" disabled={ocupado} onClick={modelo}>Baixar modelo</Button>
      <label htmlFor="importacao-arquivo">{ocupado ? 'Aguarde…' : 'Selecionar planilha (.xlsx)'}<input id="importacao-arquivo" type="file" accept=".xlsx" disabled={ocupado} onChange={e => { void importar(e.target.files?.[0]); e.target.value = ''; }} /></label>
    </div>
    {erro && <p role="alert" className="text-red-700 whitespace-pre-line mt-3">{erro}</p>}
    {sucesso && <p role="status" className="text-green-800 mt-3">{sucesso}</p>}
  </section>;
}
