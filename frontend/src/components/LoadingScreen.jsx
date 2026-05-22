const STAGES = [
  { icon: "⬡", label: "Consultando agências de checagem…" },
  { icon: "◈", label: "Analisando reputação da fonte…"    },
  { icon: "◎", label: "Escaneando padrões com IA Gemini…" },
];

export default function LoadingScreen({ stage = 0 }) {
  const pct = Math.min(100, Math.round(((stage) / STAGES.length) * 100) + 5);

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-bg">
      {/* grid bg */}
      <div className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)",
          backgroundSize: "48px 48px", opacity: .3,
        }}
      />

      {/* spinner */}
      <div className="relative w-28 h-28 mb-10" style={{ zIndex: 1 }}>
        <div className="absolute inset-0 rounded-full border-2 anim-spin-cw"
          style={{ borderColor: "transparent", borderTopColor: "#00D4FF", borderRightColor: "rgba(0,212,255,.4)" }} />
        <div className="absolute inset-3 rounded-full border anim-spin-ccw"
          style={{ borderColor: "transparent", borderTopColor: "#00FF87" }} />
        <svg className="absolute inset-0" width="112" height="112" viewBox="0 0 112 112">
          <polygon points="56,22 76,33 76,55 56,66 36,55 36,33"
            fill="none" stroke="#00D4FF" strokeWidth="1" opacity=".35" />
          <circle cx="56" cy="56" r="9" fill="#00D4FF" opacity=".8" />
        </svg>
      </div>

      <h2 className="font-syne font-extrabold text-xl tracking-wider text-text mb-1" style={{ zIndex: 1 }}>
        AUDITORIA EM PROGRESSO
      </h2>
      <p className="font-mono text-[11px] tracking-widest text-muted mb-10" style={{ zIndex: 1 }}>
        Processando 3 camadas de verificação…
      </p>

      {/* stage rows */}
      <div className="flex flex-col gap-2 w-full max-w-sm" style={{ zIndex: 1 }}>
        {STAGES.map((s, i) => {
          const status = i < stage ? "done" : i === stage ? "active" : "pending";
          const col = status === "done" ? "#00FF87" : status === "active" ? "#00D4FF" : "#1A3A50";
          return (
            <div key={i}
              className="flex items-center gap-4 px-4 py-3 rounded-r-lg transition-all"
              style={{
                borderLeft: `3px solid ${col}`,
                background: status === "active" ? "rgba(0,212,255,.05)" : "transparent",
              }}
            >
              <span className="font-mono text-lg w-5 text-center" style={{ color: col }}>
                {status === "done" ? "✓" : s.icon}
              </span>
              <span className="font-mono text-[11px] tracking-wide transition-all"
                style={{ color: status === "pending" ? "#1A3A50" : "#CDE8F0" }}>
                {s.label}
              </span>
              {status === "active" && (
                <span className="anim-blink ml-auto font-mono text-[10px]" style={{ color: "#00D4FF" }}>●</span>
              )}
            </div>
          );
        })}
      </div>

      {/* progress bar */}
      <div className="w-full max-w-sm h-[3px] rounded-full mt-7 overflow-hidden" style={{ background: "#1A3A50", zIndex: 1 }}>
        <div className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${pct}%`,
            background: "linear-gradient(90deg,#00D4FF,#00FF87)",
            boxShadow: "0 0 10px #00D4FF",
          }}
        />
      </div>
    </div>
  );
}
