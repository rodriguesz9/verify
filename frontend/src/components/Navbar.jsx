import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function Navbar() {
  const { user, signOut } = useAuth();
  const [fontSize, setFontSize] = useState(() => localStorage.getItem("verify_font_size") || "normal");

  useEffect(() => {
    if (fontSize === "normal") {
      document.documentElement.removeAttribute("data-font-size");
    } else {
      document.documentElement.setAttribute("data-font-size", fontSize);
    }
    localStorage.setItem("verify_font_size", fontSize);
  }, [fontSize]);

  const toggleFontSize = () => {
    if (fontSize === "normal") setFontSize("large");
    else if (fontSize === "large") setFontSize("xlarge");
    else setFontSize("normal");
  };
  
  return (
    <nav className="sticky top-0 left-0 right-0 z-[100] border-b border-[#132435] backdrop-blur-xl" style={{ backgroundColor: "rgba(4, 8, 12, 0.85)" }}>
      <div className="max-w-7xl mx-auto px-5 sm:px-8 flex items-center justify-between h-20">
        <div className="flex items-center gap-6 sm:gap-10">
          <Link to="/" className="flex items-center gap-3 no-underline group">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center font-syne font-black text-base group-hover:scale-105 transition-transform shadow-[0_0_20px_#00D4FF66]"
                 style={{ backgroundColor: "#00D4FF", color: "#04080C" }}>
              ✓
            </div>
            <div className="flex flex-col">
              <span className="font-syne font-black text-2xl tracking-[4px] text-[#CDE8F0] leading-none">VERIFY</span>
              <span className="font-mono text-[9px] text-[#00FF87] tracking-widest uppercase font-bold mt-0.5">Checagem Fácil</span>
            </div>
          </Link>
          
          <div className="hidden md:flex items-center gap-8">
            <Link to="/app" className="font-mono text-[13px] tracking-[2px] text-[#CDE8F0] hover:text-[#00D4FF] font-bold no-underline transition-colors uppercase">
              🔍 Checar Notícia
            </Link>
            <Link to="/dashboard" className="font-mono text-[12px] tracking-[2px] text-[#3A6070] hover:text-[#00D4FF] no-underline transition-colors uppercase">
              Painel
            </Link>
            <Link to="/history" className="font-mono text-[12px] tracking-[2px] text-[#3A6070] hover:text-[#00D4FF] no-underline transition-colors uppercase">
              Histórico
            </Link>
            <Link to="/mission" className="font-mono text-[12px] tracking-[2px] text-[#3A6070] hover:text-[#00D4FF] no-underline transition-colors uppercase">
              Sobre Nós
            </Link>
          </div>
        </div>

        <div className="flex items-center gap-3 sm:gap-6">
          {/* Accessibility Font Size Toggle */}
          <button 
            onClick={toggleFontSize}
            title="Ajustar tamanho do texto para facilitar a leitura"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-[#132435] bg-[#0A1520] hover:border-[#00D4FF] transition-all text-[#CDE8F0] font-mono text-xs font-bold"
          >
            <span>👁️ Texto:</span>
            <span className="text-[#00D4FF]">
              {fontSize === "normal" ? "Padrão" : fontSize === "large" ? "Grande" : "Muito Grande"}
            </span>
          </button>

          {user ? (
            <div className="flex items-center gap-4 pl-4 sm:pl-6 border-l border-[#132435]">
              <div className="text-right hidden sm:block">
                <div className="font-mono text-[12px] text-[#CDE8F0] font-bold leading-none">{user.name}</div>
                <div className="font-mono text-[9px] text-[#00FF87] tracking-widest uppercase mt-1">Conectado</div>
              </div>
              <button onClick={signOut} className="font-mono text-[11px] px-4 py-2 rounded-xl hover:bg-[#FF3B5C22] transition-all uppercase font-bold"
                      style={{ color: "#FF3B5C", backgroundColor: "rgba(255, 59, 92, 0.07)", border: "1px solid rgba(255, 59, 92, 0.2)" }}>
                Sair
              </button>
            </div>
          ) : (
            <Link to="/login" className="font-mono text-[12px] tracking-[2px] px-6 sm:px-8 py-2.5 rounded-xl font-bold no-underline shadow-[0_0_20px_rgba(0,212,255,0.27)] hover:scale-105 transition-transform"
                  style={{ backgroundColor: "#00D4FF", color: "#04080C" }}>
              ENTRAR
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
