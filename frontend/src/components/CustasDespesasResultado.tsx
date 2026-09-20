import type { ResultadoCustaDespesaProcessual } from '../services/api';
import { formatarData, formatarMoeda } from '../utils/formatters';

export function CustasDespesasResultado({ itens }: { itens: ResultadoCustaDespesaProcessual[] }) {
  if (!itens.length) return null;
  const totalOriginal = itens.reduce((soma, item) => soma + Number(item.valor_original), 0);
  const totalCorrecao = itens.reduce((soma, item) => soma + Number(item.correcao_monetaria), 0);
  const totalAtualizado = itens.reduce((soma, item) => soma + Number(item.valor_atualizado), 0);

  return <section className="costs-result" aria-labelledby="custas-resultado-titulo">
    <div className="section-heading">
      <div><h2 id="custas-resultado-titulo">Custas e despesas processuais</h2><p>Atualização exclusiva pelo IPCA-E, sem juros.</p></div>
      <span className="count-label">{itens.length} {itens.length === 1 ? 'lançamento' : 'lançamentos'}</span>
    </div>
    <div className="result-table-wrap" tabIndex={0} role="region" aria-label="Custas e despesas processuais atualizadas">
      <table className="result-table costs-result-table">
        <thead><tr><th scope="col">Nº</th><th scope="col">Nome</th><th scope="col">Data</th><th scope="col">Valor original</th><th scope="col">Fator IPCA-E</th><th scope="col">Correção</th><th scope="col">Valor atualizado</th></tr></thead>
        <tbody>{itens.map(item => <tr key={item.numero}>
          <td data-label="Nº">{item.numero}</td>
          <td data-label="Nome">{item.nome}</td>
          <td data-label="Data">{formatarData(item.data)}</td>
          <td data-label="Valor original">{formatarMoeda(item.valor_original)}</td>
          <td data-label="Fator IPCA-E">{Number(item.fator_ipcae).toLocaleString('pt-BR', { minimumFractionDigits: 4, maximumFractionDigits: 4 })}</td>
          <td data-label="Correção">{formatarMoeda(item.correcao_monetaria)}</td>
          <td data-label="Valor atualizado">{formatarMoeda(item.valor_atualizado)}</td>
        </tr>)}</tbody>
        <tfoot><tr><td colSpan={3}>Total</td><td>{formatarMoeda(totalOriginal)}</td><td>—</td><td>{formatarMoeda(totalCorrecao)}</td><td>{formatarMoeda(totalAtualizado)}</td></tr></tfoot>
      </table>
    </div>
  </section>;
}
