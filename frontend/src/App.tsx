import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { CalculoProvider } from './contexts/CalculoContext';
import { Layout } from './components/Layout';
import { Processamento } from './pages/Processamento';
import { HonorariosSucumbenciais } from './pages/HonorariosSucumbenciais';

function App() {
  return (
    <CalculoProvider>
      <HashRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/processamento" replace />} />
            <Route path="/importacao" element={<Navigate to="/processamento" replace />} />
            <Route path="/processamento" element={<Processamento />} />
            <Route path="/conferencia" element={<Navigate to="/processamento" replace />} />
            <Route path="/honorarios-sucumbenciais" element={<HonorariosSucumbenciais />} />
            <Route path="/exportacao" element={<Navigate to="/processamento" replace />} />
          </Routes>
        </Layout>
      </HashRouter>
    </CalculoProvider>
  );
}

export default App;
