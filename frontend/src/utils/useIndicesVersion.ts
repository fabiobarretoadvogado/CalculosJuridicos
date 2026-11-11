import { useEffect, useState } from 'react';

/** Recarrega critérios sem apagar os campos quando a base de dados muda. */
export function useIndicesVersion() {
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const changed = () => setVersion(v => v + 1);
    window.addEventListener('indices-atualizados', changed);
    return () => window.removeEventListener('indices-atualizados', changed);
  }, []);
  return version;
}
