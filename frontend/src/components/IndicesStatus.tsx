import { useEffect, useRef } from 'react';
import { avisarIndicesAtualizados, obterCatalogoIndices } from '../services/indices';

export function IndicesStatus() {
  const previous = useRef('');
  useEffect(() => {
    let active = true;
    let pending = false;
    const refresh = async () => {
      if (pending) return;
      pending = true;
      try {
        const catalog = await obterCatalogoIndices();
        if (!active) return;
        if (previous.current !== catalog.base.sha256) {
          previous.current = catalog.base.sha256;
          avisarIndicesAtualizados();
        }
      } catch {
        // Uma falha de consulta não altera a última base conhecida.
      } finally { pending = false; }
    };
    void refresh();
    const timer = window.setInterval(refresh, 30000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);
  return null;
}
