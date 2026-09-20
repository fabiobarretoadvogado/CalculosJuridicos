import { useEffect, useRef, type ReactNode } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Calculator, Scale } from 'lucide-react';
import { UpdateStatus } from './UpdateStatus';

export function Layout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const main = useRef<HTMLElement>(null);
  useEffect(() => {
    window.scrollTo(0, 0);
    main.current?.focus({ preventScroll: true });
  }, [location.pathname]);
  return <div className="office-app">
    <a className="skip-link" href="#conteudo">Ir para o conteúdo</a>
    <aside className="office-sidebar">
      <NavLink to="/processamento" className="office-brand" aria-label="Barreto Fontes - Cálculos judiciais">
        <img src="/logo-barreto-fontes.png" alt="Barreto Fontes Sociedade de Advogados" width="1856" height="754" />
      </NavLink>
      <div className="sidebar-label">CÁLCULOS JUDICIAIS</div>
      <nav className="office-nav" aria-label="Cálculos disponíveis">
        <NavLink to="/processamento"><Calculator size={18} /><span>Principal e honorários</span></NavLink>
        <NavLink to="/honorarios-sucumbenciais"><Scale size={18} /><span>Honorários</span></NavLink>
      </nav>
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
