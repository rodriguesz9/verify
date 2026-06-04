import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function Navbar() {
  const { user, signOut } = useAuth();
  
  return (
    <nav className="sticky top-0 left-0 right-0 z-[100] border-b border-[#132435] backdrop-blur-xl" style={{ backgroundColor: "rgba(4, 8, 12, 0.8)" }}>
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-20">
        <div className="flex items-center" style={{ gap: "3rem" }}>
          <Link to="/" className="flex items-center gap-3 no-underline group translate-y-[-2px]">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center font-syne font-black text-sm group-hover:rotate-12 transition-transform shadow-[0_0_15px_#00D4FF66]"
                 style={{ backgroundColor: "#00D4FF", color: "#04080C" }}>V</div>
            <span className="font-syne font-black text-xl tracking-[5px] text-[#CDE8F0]">VERIFAI</span>
          </Link>
          
          <div className="hidden md:flex items-center" style={{ gap: "2.5rem" }}>
            <Link to="/app" className="font-mono text-[11px] tracking-[3px] text-[#3A6070] no-underline hover:text-[#00D4FF] transition-colors uppercase">Verificar</Link>
            <Link to="/dashboard" className="font-mono text-[11px] tracking-[3px] text-[#3A6070] no-underline hover:text-[#00D4FF] transition-colors uppercase">Meu Painel</Link>
            <Link to="/history" className="font-mono text-[11px] tracking-[3px] text-[#3A6070] no-underline hover:text-[#00D4FF] transition-colors uppercase">Histórico</Link>
            <Link to="/plans" className="font-mono text-[11px] tracking-[3px] text-[#3A6070] no-underline hover:text-[#00D4FF] transition-colors uppercase">Planos</Link>
          </div>
        </div>

        <div className="flex items-center gap-6">
          {user ? (
            <div className="flex items-center gap-4 pl-6 border-l border-[#132435]">
              <div className="text-right hidden sm:block">
                <div className="font-mono text-[11px] text-[#CDE8F0] font-bold leading-none">{user.name}</div>
                <div className="font-mono text-[9px] text-[#00FF87] tracking-widest uppercase mt-1">Conta Ativa</div>
              </div>
              <button onClick={signOut} className="font-mono text-[10px] px-4 py-1.5 rounded-full hover:bg-[#FF3B5C22] transition-all uppercase font-bold"
                      style={{ color: "#FF3B5C", backgroundColor: "rgba(255, 59, 92, 0.07)", border: "1px solid rgba(255, 59, 92, 0.2)" }}>Sair</button>
            </div>
          ) : (
            <Link to="/login" className="font-mono text-[11px] tracking-[3px] px-8 py-2.5 rounded-full font-bold no-underline shadow-[0_0_20px_rgba(0,212,255,0.27)]"
                  style={{ backgroundColor: "#00D4FF", color: "#04080C" }}>ENTRAR</Link>
          )}
        </div>
      </div>
    </nav>
  );
}
