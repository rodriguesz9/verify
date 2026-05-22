import { Link } from "react-router-dom";

const HexLogo = () => (
  <svg width="22" height="22" viewBox="0 0 28 28">
    <polygon points="14,2 26,8 26,20 14,26 2,20 2,8" fill="none" stroke="#00D4FF" strokeWidth="1.5" />
    <polygon points="14,7 21,11 21,17 14,21 7,17 7,11" fill="none" stroke="#00D4FF" strokeWidth="1" opacity=".45" />
    <circle cx="14" cy="14" r="3" fill="#00D4FF" />
  </svg>
);

const LINKS = [
  {
    title: "Produto",
    items: [
      { label: "Como funciona", to: "/#how" },
      { label: "Planos",        to: "/plans" },
      { label: "Dashboard",     to: "/dashboard" },
      { label: "Histórico",     to: "/history" },
    ],
  },
  {
    title: "APIs Utilizadas",
    items: [
      { label: "Google Fact Check",  href: "https://developers.google.com/fact-check/tools/api" },
      { label: "Gemini 2.5 Flash",   href: "https://aistudio.google.com" },
      { label: "Hive Moderation",    href: "https://thehive.ai" },
      { label: "Google OAuth",       href: "https://console.cloud.google.com" },
    ],
  },
  {
    title: "Legal",
    items: [
      { label: "Termos de uso",       to: "/" },
      { label: "Privacidade",         to: "/" },
      { label: "Limitações da IA",    to: "/" },
    ],
  },
];

export default function Footer() {
  return (
    <footer style={{ background: "#04080C", borderTop: "1px solid #132435", position: "relative", overflow: "hidden" }}>
      {/* subtle grid */}
      <div className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)",
          backgroundSize: "48px 48px", opacity: .25,
        }} />

      <div className="relative z-10 max-w-6xl mx-auto px-6 pt-14 pb-8">
        {/* top row */}
        <div className="grid gap-10 mb-12"
          style={{ gridTemplateColumns: "2fr 1fr 1fr 1fr" }}>

          {/* brand col */}
          <div>
            <div className="flex items-center gap-2.5 mb-4">
              <HexLogo />
              <span className="font-syne font-extrabold text-base tracking-widest text-text">
                VERIF<span style={{ color: "#00D4FF" }}>AI</span>
              </span>
            </div>
            <p className="font-mono text-[12px] leading-relaxed mb-5" style={{ color: "#3A6070" }}>
              Sistema de auditoria digital e combate à desinformação.
              3 camadas de verificação em tempo real, powered by Gemini 2.5 Flash.
            </p>
            {/* badges */}
            <div className="flex gap-2 flex-wrap">
              {["Gemini 2.5", "Hive API", "Fact Check", "OAuth"].map(b => (
                <span key={b} className="font-mono text-[9px] tracking-widest px-2.5 py-1 rounded"
                  style={{ background: "rgba(0,212,255,.08)", border: "1px solid rgba(0,212,255,.18)", color: "#00D4FF" }}>
                  {b}
                </span>
              ))}
            </div>
          </div>

          {/* link cols */}
          {LINKS.map(col => (
            <div key={col.title}>
              <span className="font-mono text-[9px] tracking-[3px] block mb-4" style={{ color: "#1A3A50" }}>
                {col.title.toUpperCase()}
              </span>
              <ul className="flex flex-col gap-2.5">
                {col.items.map(item => (
                  <li key={item.label}>
                    {item.href ? (
                      <a href={item.href} target="_blank" rel="noopener noreferrer"
                        className="font-mono text-[11px] transition-colors"
                        style={{ color: "#3A6070", textDecoration: "none" }}
                        onMouseOver={e => e.target.style.color = "#00D4FF"}
                        onMouseOut={e => e.target.style.color = "#3A6070"}>
                        {item.label} ↗
                      </a>
                    ) : (
                      <Link to={item.to}
                        className="font-mono text-[11px] transition-colors"
                        style={{ color: "#3A6070", textDecoration: "none" }}>
                        {item.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* divider */}
        <div className="h-px mb-6" style={{ background: "#132435" }} />

        {/* bottom row */}
        <div className="flex items-center justify-between">
          <p className="font-mono text-[10px]" style={{ color: "#1A3A50" }}>
            © 2026 VerifAI · Projeto acadêmico/MVP · Resultado de IA não substitui verificação jornalística profissional.
          </p>
          <div className="flex items-center gap-4">
            <span className="font-mono text-[9px] tracking-widest px-2.5 py-1 rounded"
              style={{ background: "rgba(0,255,135,.08)", border: "1px solid rgba(0,255,135,.2)", color: "#00FF87" }}>
              MVP v0.2
            </span>
            <span className="font-mono text-[10px]" style={{ color: "#1A3A50" }}>
              Built with FastAPI + React + Gemini
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
