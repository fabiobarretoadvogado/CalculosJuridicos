/**
 * Formata um valor numérico para moeda brasileira (R$ 1.234,56).
 */
export function formatarMoeda(valor: string | number | null | undefined): string {
  if (valor === null || valor === undefined || valor === '') return 'R$ 0,00';
  const num = typeof valor === 'string' ? parseFloat(valor) : valor;
  if (isNaN(num)) return 'R$ 0,00';
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

/**
 * Formata uma data ISO (YYYY-MM-DD) para o padrão brasileiro (DD/MM/YYYY).
 */
export function formatarData(data: string | null | undefined): string {
  if (!data) return '—';
  const partes = data.split('-');
  if (partes.length !== 3) return data;
  return `${partes[2]}/${partes[1]}/${partes[0]}`;
}

/**
 * Formata um valor percentual (ex: 10 → "10,00%").
 */
export function formatarPercentual(valor: string | number | null | undefined): string {
  if (valor === null || valor === undefined || valor === '') return '0,00%';
  const num = typeof valor === 'string' ? parseFloat(valor) : valor;
  if (isNaN(num)) return '0,00%';
  return `${num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

/** Formata a competência ISO (YYYY-MM) sem inventar um dia de aplicação. */
export function formatarCompetencia(competencia: string | null | undefined): string {
  if (!competencia) return 'nenhum';
  const partes = competencia.split('-');
  return partes.length === 2 ? `${partes[1]}/${partes[0]}` : competencia;
}

/**
 * Formata um número com separadores brasileiros (1.234,56).
 */
export function formatarNumero(valor: string | number | null | undefined): string {
  if (valor === null || valor === undefined || valor === '') return '0,00';
  const num = typeof valor === 'string' ? parseFloat(valor) : valor;
  if (isNaN(num)) return '0,00';
  return num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
}

/**
 * Converte data brasileira (DD/MM/YYYY) para ISO (YYYY-MM-DD).
 */
export function converterDataParaISO(data: string): string {
  const partes = data.split('/');
  if (partes.length === 3) {
    return `${partes[2]}-${partes[1]}-${partes[0]}`;
  }
  return data;
}

/**
 * Converte string para number de forma segura.
 */
export function toNumber(valor: string | number | null | undefined): number {
  if (valor === null || valor === undefined || valor === '') return 0;
  const num = typeof valor === 'string' ? parseFloat(valor) : valor;
  return isNaN(num) ? 0 : num;
}

/**
 * Gera string de data atual no formato YYYY-MM-DD.
 */
export function dataAtualISO(): string {
  return new Date().toISOString().split('T')[0];
}

/**
 * Trigger download de um Blob como arquivo.
 */
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
