import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import UsageBar from "./UsageBar";

const HexLogo = () => (
  <svg width="26" height="26" viewBox="0 0 28 28">
    <polygon points="14,2 26,8 26,20 14,26 2,20 2,8" fill="none" stroke="#00D4FF" strokeWidth="1.5"/>
    <polygon points="14,7 21,11 21,17 14,21 7,17 7,11" fill="none" stroke="#00D4FF" strokeWidth="1" opacity=".45"/>
    <circle cx="14" cy="14" r="3" fill="#00D4FF"/>
  </svg>
);

export default function Navbar() {
  const { pathname } = useLocation();
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  const authedLinks = [
    { to: "/app",          label: "ANÁLISE"   },
    { to: "/dashboard", label: "DASHBOARD" },
    { to: "/history",   label: "HISTÓRICO" },
    { to: "/plans",     label: "PLANOS"    },
    { to: "/mission",   label: "MISSÃO"    },
    { to: "/suggestions", label: "SUGESTÕES" },
  ];

  return (
    <nav className="sticky top-0 z-50 border-b border-border backdrop-blur-md"
      style={{ background: "rgba(4,8,12,0.92)" }}>
      <div className="max-w-6xl mx-auto px-5 flex items-center justify-between h-14 gap-4">
        {/* brand */}
        <Link to="/" className="flex items-center gap-2 no-underline shrink-0">
          <HexLogo/>
          <span className="font-syne font-extrabold text-base tracking-widest text-text">
            VERIF<span className="text-cyan">AI</span>
          </span>
        </Link>

        {/* links */}
        {user && (
          <div className="flex items-center gap-1 overflow-x-auto">
            {authedLinks.map(({ to, label }) => {
              const active = pathname === to;
              return (
                <Link key={to} to={to}
                  className="font-mono text-[10px] tracking-widest px-3.5 py-1.5 rounded-md transition-all whitespace-nowrap"
                  style={{
                    color: active ? "#00D4FF" : "#3A6070",
                    background: active ? "rgba(0,212,255,.1)" : "transparent",
                    border: active ? "1px solid rgba(0,212,255,.25)" : "1px solid transparent",
                    textDecoration: "none",
                  }}>
                  {label}
                </Link>
              );
            })}
          </div>
        )}

        {/* right */}
        <div className="flex items-center gap-2 shrink-0">
          {user ? (
            <>
              <UsageBar/>
              <div className="flex items-center gap-2">
                {user.avatar_url
                  ? <img src={user.avatar_url} alt="" className="w-7 h-7 rounded-full border border-border"/>
                  : (
                    <div className="w-7 h-7 rounded-full flex items-center justify-center font-syne font-bold text-xs"
                      style={{ background: "rgba(0,212,255,.15)", color: "#00D4FF", border: "1px solid rgba(0,212,255,.3)" }}>
                      {user.name?.[0]?.toUpperCase()}
                    </div>
                  )}
                <span className="font-mono text-[10px]" style={{ color: "#3A6070" }}>
                  {user.name?.split(" ")[0]}
                </span>
                <button onClick={signOut}
                  className="font-mono text-[10px] tracking-widest px-3 py-1.5 rounded-md transition-all"
                  style={{ background: "transparent", border: "1px solid #132435", color: "#3A6070", cursor: "pointer" }}>
                  SAIR
                </button>
              </div>
            </>
          ) : (
            <div className="flex gap-2">
              <Link to="/login"
                className="font-mono text-[10px] tracking-widest px-4 py-1.5 rounded-md"
                style={{ color: "#3A6070", border: "1px solid #132435", textDecoration: "none" }}>
                ENTRAR
              </Link>
              <Link to="/register"
                className="font-mono text-[10px] tracking-widest px-4 py-1.5 rounded-md"
                style={{ background: "linear-gradient(135deg,#00D4FF,#00FF87)", color: "#04080C", textDecoration: "none", fontWeight: 700 }}>
                CADASTRAR
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
