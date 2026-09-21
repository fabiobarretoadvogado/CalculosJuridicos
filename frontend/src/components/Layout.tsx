import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { Calculator, KeyRound, Scale } from 'lucide-react';
import { UpdateStatus } from './UpdateStatus';
import { mensagemErro, recuperarCalculo } from '../services/api';

export function Layout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const main = useRef<HTMLElement>(null);
  const [chave, setChave] = useState('');
  const [recuperando, setRecuperando] = useState(false);
  const [erroRecuperacao, setErroRecuperacao] = useState('');
  const [statusRecuperacao, setStatusRecuperacao] = useState('');
  useEffect(() => {
    window.scrollTo(0, 0);
    main.current?.focus({ preventScroll: true });
  }, [location.pathname]);

  async function recuperar(evento: FormEvent) {
    evento.preventDefault();
    if (!chave.trim()) return;
    setRecuperando(true);
    setErroRecuperacao('');
    setStatusRecuperacao('');
    try {
      const calculoRecuperado = await recuperarCalculo(chave);
      const destino = calculoRecuperado.categoria === 'calculo_principal'
        ? '/processamento' : '/honorarios-sucumbenciais';
      setChave(calculoRecuperado.chave_recuperacao);
      setStatusRecuperacao('Cálculo recuperado. Os campos estão prontos para edição.');
      navigate(destino, { state: { calculoRecuperado } });
    } catch (erro) {
      setErroRecuperacao(await mensagemErro(erro));
    } finally {
      setRecuperando(false);
    }
  }
  return <div className="office-app">
    <a className="skip-link" href="#conteudo">Ir para o conteúdo</a>
    <aside className="office-sidebar">
      <NavLink to="/processamento" className="office-brand" aria-label="Cálculos Jurídicos">
        <img src="/app-logo.png" alt="Cálculos Jurídicos" width="1254" height="1254" />
      </NavLink>
      <div className="sidebar-label">CÁLCULOS JUDICIAIS</div>
      <nav className="office-nav" aria-label="Cálculos disponíveis">
        <NavLink to="/processamento"><Calculator size={18} /><span>Principal e honorários</span></NavLink>
        <NavLink to="/honorarios-sucumbenciais"><Scale size={18} /><span>Honorários</span></NavLink>
      </nav>
      <details className="recovery-panel">
        <summary><KeyRound size={16} /><span>Recuperar cálculo</span></summary>
        <form onSubmit={recuperar}>
          <label htmlFor="chave-recuperacao">Chave impressa no PDF</label>
          <p className="recovery-help">Disponível no mesmo computador e usuário em que o cálculo foi criado.</p>
          <input id="chave-recuperacao" value={chave} onChange={e => setChave(e.target.value.toUpperCase())} placeholder="CJ1-0000-0000-0000-0000-0000" autoComplete="off" spellCheck={false} />
          <button type="submit" disabled={recuperando || !chave.trim()}>{recuperando ? 'Recuperando…' : 'Abrir para editar'}</button>
          {erroRecuperacao && <p className="recovery-error" role="alert">{erroRecuperacao}</p>}
          {statusRecuperacao && <p className="recovery-success" role="status">{statusRecuperacao}</p>}
        </form>
      </details>
      <div className="sidebar-foot">
        <UpdateStatus />
        <span className="brand-rule" />
        <p>Barreto Fontes<br />Sociedade de Advogados</p>
      </div>
    </aside>
    <div className="office-workspace">
      <header className="office-topbar"><span>Escritório <span className="breadcrumb-divider">/</span> Cálculos judiciais</span><span className="topbar-label">LIQUIDAÇÃO DE SENTENÇA</span></header>
      <main ref={main} id="conteudo" tabIndex={-1} className="office-content">{children}</main>
    </div>
  </div>;
}
