import { Navigate } from 'react-router-dom';
import { ResultadoPrincipal } from '../components/ResultadoPrincipal';
import { useCalculo } from '../contexts/useCalculo';


export function Conferencia() {
  const { state } = useCalculo();
  if (!state.resultado) {
    return <Navigate to="/processamento" replace />;
  }
  return <ResultadoPrincipal />;
}
