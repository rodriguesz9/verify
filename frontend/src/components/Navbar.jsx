import { useState, useEffect, useId, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Shield, Menu, X, LogOut, ArrowRight, Type, Wifi, WifiOff } from "lucide-react";
import { useAuth } from "../hooks/authContext";
import { useAccessibility } from "../hooks/useAccessibility";
import { getOfflineCount } from "../services/offlineCache";
import EasyModeButton from "./EasyModeButton";

const APP_LINKS = [{ to: "/app", label: "Checar" }, { to: "/dashboard", label: "Painel" }, { to: "/demo", label: "Demonstração" }, { to: "/mission", label: "Sobre nós" }];
const LANDING_LINKS = [{ href: "#como-funciona", label: "Como funciona" }, { href: "#protege", label: "Sua proteção" }, { to: "/demo", label: "Demonstração" }, { to: "/mission", label: "Sobre nós" }];
const MORE_LINKS = [{ to: "/limitacoes", label: "Limitações" }, { to: "/terms", label: "Termos de uso" }, { to: "/privacy", label: "Privacidade" }];

export default function Navbar({ variant = "app" }) {
  const { user, signOut } = useAuth();
  const { mode, easyMode, cycleTextSize } = useAccessibility();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [online, setOnline] = useState(navigator.onLine);
  const [offlineCount, setOfflineCount] = useState(0);
  const menuId = useId();
  const navRef = useRef(null);
  const menuButton = useRef(null);
  const links = variant === "landing" ? LANDING_LINKS : APP_LINKS;

  useEffect(() => {
    const update = () => { setOnline(navigator.onLine); setOfflineCount(getOfflineCount()); };
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => { window.removeEventListener("online", update); window.removeEventListener("offline", update); };
  }, []);
  useEffect(() => {
    if (!open) return;
    const keydown = (event) => {
      if (event.key === "Escape") { setOpen(false); menuButton.current?.focus(); }
    };
    const outside = (event) => { if (!navRef.current?.contains(event.target)) setOpen(false); };
    document.addEventListener("keydown", keydown);
    document.addEventListener("pointerdown", outside);
    return () => { document.removeEventListener("keydown", keydown); document.removeEventListener("pointerdown", outside); };
  }, [open]);
  const renderLink = ({ to, href, label }) => to
    ? <Link key={label} to={to} onClick={() => setOpen(false)}>{label}</Link>
    : <a key={label} href={href} onClick={() => setOpen(false)}>{label}</a>;
  const logout = () => { signOut(); setOpen(false); navigate("/"); };
  return (
    <nav className="site-nav" aria-label="Navegação principal" ref={navRef}>
      <div className="site-nav-inner">
        <Link to="/" className="site-brand" aria-label="Verify — página inicial">
          <span className="site-brand-icon"><Shield size={23} aria-hidden="true" /></span>
          <span><strong>VERIFY</strong><span className="site-brand-caption">Checagem fácil</span></span>
        </Link>
        <div className="site-nav-desktop">{links.map(renderLink)}</div>
        <div className="site-nav-actions">
          <EasyModeButton className="site-nav-easy-desktop" />
          {user ? <button type="button" className="site-nav-account" onClick={logout}><LogOut size={19} aria-hidden="true" /> Sair</button>
            : <Link to="/login" className="site-nav-account">Entrar <ArrowRight size={19} aria-hidden="true" /></Link>}
          <button ref={menuButton} type="button" className="site-nav-menu-toggle" aria-expanded={open} aria-controls={menuId} onClick={() => setOpen(!open)}>
            {open ? <X size={23} aria-hidden="true" /> : <Menu size={23} aria-hidden="true" />}<span>Menu</span>
          </button>
        </div>
      </div>
      <div className="site-nav-easy-mobile"><EasyModeButton /></div>
      <div className="site-nav-drawer" id={menuId} hidden={!open}>
        <div className="site-nav-drawer-links">{[...links, ...MORE_LINKS].map(renderLink)}</div>
        <div className="site-nav-drawer-tools">
          <button type="button" onClick={cycleTextSize} disabled={easyMode}><Type size={21} aria-hidden="true" />{easyMode ? "Letras grandes já ativas" : `Texto: ${{ normal: "padrão", large: "maior", xlarge: "extra grande" }[mode]}`}</button>
          {variant === "app" && <p className="site-connection">{online ? <Wifi size={20} aria-hidden="true" /> : <WifiOff size={20} aria-hidden="true" />}{online ? "Dispositivo conectado" : `Sem conexão${offlineCount ? ` · ${offlineCount} itens salvos` : ""}`}</p>}
          {user ? <button type="button" onClick={logout}><LogOut size={21} aria-hidden="true" /> Sair da conta</button> : <Link to="/login" onClick={() => setOpen(false)}>Entrar na conta <ArrowRight size={20} aria-hidden="true" /></Link>}
        </div>
      </div>
    </nav>
  );
}
