import { useEffect, useState } from 'react';
import { Download, RefreshCw } from 'lucide-react';
import {
  baixarAtualizacao,
  instalarAtualizacao,
  obterInformacoesApp,
  verificarAtualizacao,
  type AppInfo,
  type AtualizacaoDisponivel,
} from '../services/api';

type Estado = 'consultando' | 'atualizado' | 'disponivel' | 'baixando' | 'instalando' | 'indisponivel';

async function consultarServidor() {
  const info = await obterInformacoesApp();
  if (!info.empacotado || !info.atualizacoes_configuradas) {
    return { info, atualizacao: null, estado: 'indisponivel' as Estado, erro: '' };
  }
  try {
    const atualizacao = await verificarAtualizacao();
    return {
      info,
      atualizacao,
      estado: atualizacao.disponivel ? 'disponivel' as Estado : 'atualizado' as Estado,
      erro: '',
    };
  } catch {
    return {
      info,
      atualizacao: null,
      estado: 'indisponivel' as Estado,
      erro: 'Não foi possível consultar atualizações. Verifique a conexão e tente novamente.',
    };
  }
}

export function UpdateStatusView({
  info,
  atualizacao,
  estado,
  erro,
  onConsultar,
  onAtualizar,
}: {
  info: AppInfo | null;
  atualizacao: AtualizacaoDisponivel | null;
  estado: Estado;
  erro: string;
  onConsultar: () => void;
  onAtualizar: () => void;
}) {
  const podeConsultar = !info || (info.empacotado && info.atualizacoes_configuradas);
  return (
    <div className="update-status" aria-live="polite" aria-busy={estado === 'consultando' || estado === 'baixando' || estado === 'instalando'}>
      <span className="update-version">{info ? `Versão ${info.edicao}` : 'Versão do aplicativo'}</span>
      {estado === 'atualizado' && <>
        <span className="update-note">Versão mais recente instalada.</span>
        <button type="button" className="update-action" onClick={onConsultar}>
          <RefreshCw size={14} aria-hidden="true" /> Verificar atualização
        </button>
      </>}
      {estado === 'disponivel' && atualizacao?.nova_edicao && (
        <button type="button" className="update-action" onClick={onAtualizar}>
          <Download size={14} aria-hidden="true" /> Atualizar para {atualizacao.nova_edicao}
        </button>
      )}
      {estado === 'consultando' && <span className="update-progress"><RefreshCw size={14} aria-hidden="true" /> Verificando atualização…</span>}
      {estado === 'baixando' && <span className="update-progress"><RefreshCw size={14} aria-hidden="true" /> Baixando atualização…</span>}
      {estado === 'instalando' && <span className="update-progress"><RefreshCw size={14} aria-hidden="true" /> Reiniciando para atualizar…</span>}
      {estado === 'indisponivel' && podeConsultar && (
        <button type="button" className="update-action" onClick={onConsultar}>
          <RefreshCw size={14} aria-hidden="true" /> Tentar novamente
        </button>
      )}
      {estado === 'indisponivel' && !podeConsultar && <span className="update-note">Atualizações disponíveis no programa instalado.</span>}
      {erro && <span className="update-error" role="alert">{erro}</span>}
    </div>
  );
}

export function UpdateStatus() {
  const [info, setInfo] = useState<AppInfo | null>(null);
  const [atualizacao, setAtualizacao] = useState<AtualizacaoDisponivel | null>(null);
  const [estado, setEstado] = useState<Estado>('consultando');
  const [erro, setErro] = useState('');

  useEffect(() => {
    let ativo = true;
    async function consultar() {
      try {
        const dados = await consultarServidor();
        if (!ativo) return;
        setInfo(dados.info);
        setAtualizacao(dados.atualizacao);
        setEstado(dados.estado);
        setErro(dados.erro);
      } catch {
        if (ativo) {
          setEstado('indisponivel');
          setErro('Não foi possível consultar atualizações. Verifique a conexão e tente novamente.');
        }
      }
    }
    void consultar();
    return () => { ativo = false; };
  }, []);

  async function consultarNovamente() {
    setErro('');
    setEstado('consultando');
    try {
      const dados = await consultarServidor();
      setInfo(dados.info);
      setAtualizacao(dados.atualizacao);
      setEstado(dados.estado);
      setErro(dados.erro);
    } catch {
      setEstado('indisponivel');
      setErro('Não foi possível consultar atualizações. Verifique a conexão e tente novamente.');
    }
  }

  async function atualizar() {
    setErro('');
    setEstado('baixando');
    try {
      await baixarAtualizacao();
      setEstado('instalando');
      await instalarAtualizacao();
    } catch {
      setEstado('disponivel');
      setErro('Não foi possível concluir a atualização. Tente novamente quando a conexão estiver estável.');
    }
  }

  return <UpdateStatusView
    info={info}
    atualizacao={atualizacao}
    estado={estado}
    erro={erro}
    onConsultar={() => { void consultarNovamente(); }}
    onAtualizar={() => { void atualizar(); }}
  />;
}
