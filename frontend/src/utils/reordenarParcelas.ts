/** Move somente a posição, conservando a identidade e todos os campos da parcela. */
export function reordenarParcelas<T>(parcelas: T[], origem: number, destino: number): T[] {
  if (!Number.isInteger(origem) || !Number.isInteger(destino)
    || origem < 0 || destino < 0 || origem >= parcelas.length || destino >= parcelas.length
    || origem === destino) return parcelas;
  const ordenadas = [...parcelas];
  const [parcela] = ordenadas.splice(origem, 1);
  ordenadas.splice(destino, 0, parcela);
  return ordenadas;
}

/** A linha de inserção considera a lista antes de retirar a parcela arrastada. */
export function destinoDaInsercao(origem: number, insercao: number): number {
  return insercao > origem ? insercao - 1 : insercao;
}

/** O número apresentado e exportado acompanha a posição atual na lista. */
export function numerarParcelas<T extends { numero: number }>(parcelas: T[]): T[] {
  return parcelas.map((parcela, indice) => parcela.numero === indice + 1
    ? parcela : { ...parcela, numero: indice + 1 });
}
