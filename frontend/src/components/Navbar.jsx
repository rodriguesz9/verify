import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/authContext";
import { Search, LayoutDashboard, Info, Zap, LogOut, Menu, X, Shield, MessageCircle, ChevronDown, Wifi, WifiOff, Accessibility, Volume2, Eye } from "lucide-react";
import { getOfflineCount } from "../services/offlineCache";

const NAV_LINKS = [
  { to: "/app", label: "Checar", icon: Search },
  { to: "/dashboard", label: "Painel", icon: LayoutDashboard },
  { to: "/demo", label: "Demonstração", icon: Zap },
  { to: "/mission", label: "Sobre Nós", icon: Info },
  { to: "/limitacoes", label: "Limitações", icon: Menu },
];

const DROPDOWN_ITEMS = [
  { to: "/limitacoes", label: "Limitações de Uso" },
  { to: "/termos", label: "Termos de Serviço" },
  { to: "/privacidade", label: "Política de Privacidade" },
];

export default function Navbar() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [fontSize, setFontSize] = useState(() => localStorage.getItem("verify_font_size") || "normal");
  const [isElderlyMode, setIsElderlyMode] = useState(() => {
    const saved = localStorage.getItem("verify_elderly_mode");
    return saved === "true";
  });
  const [menuOpen, setMenuOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [offlineCount, setOfflineCount] = useState(0);

  useEffect(() => {
    if (fontSize === "normal") {
      document.documentElement.removeAttribute("data-font-size");
      document.documentElement.removeAttribute("data-elderly-mode");
    } else if (fontSize === "elderly") {
      document.documentElement.setAttribute("data-font-size", "elderly");
      document.documentElement.setAttribute("data-elderly-mode", "true");
    } else {
      document.documentElement.setAttribute("data-font-size", fontSize);
      document.documentElement.removeAttribute("data-elderly-mode");
    }
    localStorage.setItem("verify_font_size", fontSize);
  }, [fontSize]);

  useEffect(() => {
    if (isElderlyMode && fontSize !== "elderly") {
      setFontSize("elderly");
    }
    localStorage.setItem("verify_elderly_mode", isElderlyMode);
    if (!isElderlyMode) {
      document.documentElement.removeAttribute("data-elderly-mode");
    }
  }, [isElderlyMode]);

  useEffect(() => {
    const handleElderlyChange = (e) => {
      setIsElderlyMode(e.detail === true);
    };
    window.addEventListener("elderly-mode-change", handleElderlyChange);
    return () => window.removeEventListener("elderly-mode-change", handleElderlyChange);
  }, []);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    setOfflineCount(getOfflineCount());
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  const toggleFontSize = () => {
    if (fontSize === "normal") setFontSize("large");
    else if (fontSize === "large") setFontSize("xlarge");
    else setFontSize("normal");
  };

  const handleLogout = () => {
    signOut();
    navigate("/");
  };

  return (
    <nav className="sticky top-0 left-0 right-0 z-[100] border-b border-[#132435] backdrop-blur-xl bg-[rgba(4,8,12,0.9)]">
      <div className="max-w-7xl mx-auto px-5 sm:px-8 flex items-center justify-between h-20">
        <Link to="/" className="flex items-center gap-3 no-underline group">
          <div className="w-10 h-10 rounded-lg bg-[#00D4FF] flex items-center justify-center font-syne font-black text-base group-hover:scale-105 transition-transform shadow-[0_0_20px_#00D4FF66]">
            <Shield size={20} />
          </div>
          <div className="flex flex-col">
            <span className="font-syne font-black text-2xl tracking-[4px] text-[#CDE8F0] leading-none">VERIFY</span>
            <span className="font-mono text-[9px] text-[#00FF87] tracking-widest uppercase font-bold mt-0.5">Checagem Fácil</span>
          </div>
        </Link>

        <div className="hidden md:flex items-center gap-8">
          {NAV_LINKS.map(({ to, label, icon: Icon }) => (
            <Link key={to} to={to} className="font-mono text-[13px] tracking-[2px] text-[#CDE8F0] hover:text-[#00D4FF] font-bold no-underline transition-colors uppercase flex items-center gap-2">
              <Icon size={14} /> {label}
            </Link>
          ))}

          {/* Offline indicator */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-mono font-bold uppercase tracking-wider"
            style={{
              color: isOnline ? "#00FF87" : "#FFB830",
              backgroundColor: isOnline ? "rgba(0,255,135,0.08)" : "rgba(255,184,48,0.12)",
              border: `1px solid ${isOnline ? "rgba(0,255,135,0.2)" : "rgba(255,184,48,0.3)"}`,
            }}>
            {isOnline ? <Wifi size={12} /> : <WifiOff size={12} />}
{isOnline ? "Online" : `Offline${offlineCount > 0 ? ` (${offlineCount})` : ""}`}
           </div>

           {isElderlyMode ? (
             <button
               onClick={() => setIsElderlyMode(false)}
               className="flex items-center gap-2 rounded-lg px-3 py-1.5 font-mono text-[10px] font-bold uppercase tracking-wider bg-[#00FF87]/20 text-[#00FF87] hover:bg-[#00FF87]/30 transition-colors"
             >
               <Eye size={12} /> Modo Idoso
             </button>
           ) : (
             <button
               onClick={() => setIsElderlyMode(true)}
               className="flex items-center gap-2 rounded-lg px-3 py-1.5 font-mono text-[10px] font-bold uppercase tracking-wider bg-[#00D4FF]/20 text-[#00D4FF] hover:bg-[#00D4FF]/30 transition-colors"
             >
               <Accessibility size={12} /> Modo Fácil
             </button>
           )}

           {user ? (
            <div className="flex items-center gap-4 pl-6 border-l border-[#132435]">
              <div className="text-right hidden sm:block">
                <div className="font-mono text-[12px] text-[#CDE8F0] font-bold leading-none">{user.name}</div>
                <div className="font-mono text-[9px] text-[#00FF87] tracking-widest uppercase mt-1">Conectado</div>
              </div>
              <button onClick={handleLogout} className="font-mono text-[11px] px-4 py-2 rounded-xl hover:bg-[#FF3B5C22] transition-all uppercase font-bold flex items-center gap-2 cursor-pointer"
                style={{ color: "#FF3B5C", backgroundColor: "rgba(255,59,92,0.07)", border: "1px solid rgba(255,59,92,0.2)" }}>
                <LogOut size={12} /> Sair
              </button>
            </div>
          ) : (
            <Link to="/login" className="font-mono text-[12px] tracking-[2px] px-6 py-2.5 rounded-xl font-bold no-underline shadow-[0_0_20px_rgba(0,212,255,0.27)] hover:scale-105 transition-transform flex items-center gap-2"
              style={{ backgroundColor: "#00D4FF", color: "#04080C" }}>
              <MessageCircle size={12} /> ENTRAR
            </Link>
          )}
        </div>

        <button onClick={() => setMenuOpen(!menuOpen)} className="md:hidden text-[#CDE8F0] cursor-pointer">
          {menuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {menuOpen && (
        <div className="md:hidden border-t border-[#132435] bg-[#0A1520] p-6 flex flex-col gap-4">
          {NAV_LINKS.map(({ to, label, icon: Icon }) => (
            <Link key={to} to={to} onClick={() => setMenuOpen(false)} className="font-mono text-[13px] tracking-[2px] text-[#CDE8F0] hover:text-[#00D4FF] font-bold no-underline uppercase flex items-center gap-3">
              <Icon size={16} /> {label}
            </Link>
          ))}
<div className="flex items-center gap-2 px-3 py-2 rounded-lg text-[11px] font-mono font-bold uppercase"
            style={{ color: isOnline ? "#00FF87" : "#FFB830" }}>
            {isOnline ? <Wifi size={14} /> : <WifiOff size={14} />}
            {isOnline ? "Online" : `Offline${offlineCount > 0 ? ` (${offlineCount})` : ""}`}
          </div>
          {isElderlyMode ? (
            <button
              onClick={() => setIsElderlyMode(false)}
              className="flex items-center gap-2 rounded-lg px-4 py-2 font-mono text-[11px] font-bold uppercase bg-[#00FF87]/20 text-[#00FF87] hover:bg-[#00FF87]/30 transition-colors"
            >
              <Eye size={14} /> Modo Idoso
            </button>
          ) : (
            <button
              onClick={() => setIsElderlyMode(true)}
              className="flex items-center gap-2 rounded-lg px-4 py-2 font-mono text-[11px] font-bold uppercase bg-[#00D4FF]/20 text-[#00D4FF] hover:bg-[#00D4FF]/30 transition-colors"
            >
              <Accessibility size={14} /> Modo Fácil
            </button>
          )}
          <button onClick={toggleFontSize} className="font-mono text-[11px] text-[#00D4FF] uppercase text-left">
            Ajustar Texto
          </button>
        </div>
      )}
    </nav>
  );
}
