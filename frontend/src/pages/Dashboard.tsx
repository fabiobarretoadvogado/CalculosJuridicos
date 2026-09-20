import { useEffect, useState } from 'react';
import {
  Wifi,
  WifiOff,
} from 'lucide-react';
import { Card } from '../components/ui';
import { Badge } from '../components/ui';
import { checkApiHealth } from '../services/api';

export function Dashboard() {
  const [apiStatus, setApiStatus] = useState<'checking' | 'online' | 'offline'>('checking');

  useEffect(() => {
    let active = true;
    checkApiHealth()
      .then(() => active && setApiStatus('online'))
      .catch(() => active && setApiStatus('offline'));
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-6">
      {/* Welcome + API status */}
      <Card>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-800">Bem-vindo ao Sistema de Cálculos Jurídicos</h2>
            <p className="text-sm text-slate-500 mt-1 max-w-2xl">
              Ferramenta profissional para liquidação de sentença judicial — correção monetária, juros,
              honorários, multa CPC 523 e abatimentos, com memória de cálculo completa.
            </p>
          </div>
          <div className="flex-shrink-0">
            {apiStatus === 'checking' && <Badge variant="default">Verificando API…</Badge>}
            {apiStatus === 'online' && (
              <Badge variant="success" className="flex items-center gap-1.5">
                <Wifi className="w-3.5 h-3.5" /> API Online
              </Badge>
            )}
            {apiStatus === 'offline' && (
              <Badge variant="error" className="flex items-center gap-1.5">
                <WifiOff className="w-3.5 h-3.5" /> API Offline
              </Badge>
            )}
          </div>
        </div>
      </Card>

      {/* API offline warning */}
      {apiStatus === 'offline' && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <p className="font-semibold mb-1">Não foi possível conectar à API em http://127.0.0.1:8000</p>
          <p>
            Inicie o backend com:{' '}
            <code className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-900">
              cd backend && python -m uvicorn liquidacao_custom.api.main:app --reload
            </code>
          </p>
        </div>
      )}

    </div>
  );
}
