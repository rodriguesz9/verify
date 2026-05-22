import Footer from "../components/Footer";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { scoreColor, scoreLabel } from "../components/GaugeChart";

const MOCK = [
  { score: 82, verdict: "CONFIÁVEL", summary: "Notícia verificada por agências de checagem.", query: "BBC News Brasil – 2024", ts: "há 5 min" },
  { score: 44, verdict: "SUSPEITO",  summary: "Fonte desconhecida, domínio recente.", query: "urgente-verdade.xyz/post/123", ts: "há 12 min" },
  { score: 18, verdict: "FALSO",     summary: "Contradições factuais detectadas pelo Gemini.", query: "Foto mostra X acontecendo em SP...", ts: "há 1h" },
];

export default function Dashboard() {
  const navigate = useNavigate();
  const [items, setItems] = useState(MOCK);

  return (
    <div className="relative min-h-screen pb-20">
      <div className="pointer-events-none fixed inset-0"
        style={{
          backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)",
          backgroundSize: "48px 48px", opacity: .2,
        }}
      />

      <div className="relative z-10 max-w-4xl mx-auto px-5 pt-10">
        {/* header */}
        <div className="flex items-center justify-between mb-8 fade-1">
          <div>
            <h1 className="font-syne font-extrabold text-2xl tracking-wide mb-1" style={{ color: "#CDE8F0" }}>
              Dashboard
            </h1>
            <p className="font-mono text-[11px]" style={{ color: "#3A6070" }}>
              Histórico de análises desta sessão
            </p>
          </div>
          <button onClick={() => navigate("/app")}
            className="font-mono text-[10px] tracking-widest px-5 py-2.5 rounded-lg transition-all"
            style={{
              background: "linear-gradient(135deg,#00D4FF,#00FF87)",
              color: "#04080C", border: "none", cursor: "pointer",
              boxShadow: "0 0 20px rgba(0,212,255,.3)", fontWeight: 700,
            }}>
            + NOVA ANÁLISE
          </button>
        </div>

        {/* stats row */}
        <div className="grid grid-cols-3 gap-4 mb-8 fade-2">
          {[
            { label: "ANÁLISES",   value: items.length, col: "#00D4FF" },
            { label: "CONFIÁVEIS", value: items.filter(i => i.score >= 68).length, col: "#00FF87" },
            { label: "FALSOS",     value: items.filter(i => i.score <  38).length, col: "#FF3B5C" },
          ].map(({ label, value, col }) => (
            <div key={label} className="rounded-xl p-5 text-center"
              style={{ background: "#0A1520", border: "1px solid #132435" }}>
              <span className="font-syne font-extrabold text-4xl" style={{ color: col }}>{value}</span>
              <span className="font-mono text-[9px] tracking-widest block mt-1" style={{ color: "#3A6070" }}>
                {label}
              </span>
            </div>
          ))}
        </div>

        {/* table header */}
        <div className="grid grid-cols-[1fr_auto_auto] gap-4 px-4 mb-2 fade-3">
          {["CONTEÚDO ANALISADO","SCORE","VEREDICTO"].map(h => (
            <span key={h} className="font-mono text-[9px] tracking-widest" style={{ color: "#1A3A50" }}>
              {h}
            </span>
          ))}
        </div>

        {/* rows */}
        {items.map((item, i) => {
          const col = scoreColor(item.score);
          return (
            <div key={i}
              className={`grid grid-cols-[1fr_auto_auto] gap-4 items-center px-4 py-4 rounded-xl mb-2 transition-all cursor-pointer fade-${i + 3}`}
              style={{ background: "#0A1520", border: "1px solid #132435" }}
              onClick={() => navigate("/app")}
            >
              {/* content */}
              <div>
                <p className="font-syne font-semibold text-[13px] mb-1 truncate" style={{ color: "#CDE8F0", maxWidth: 400 }}>
                  {item.query}
                </p>
                <p className="font-mono text-[11px] leading-relaxed line-clamp-1" style={{ color: "#3A6070" }}>
                  {item.summary}
                </p>
                <span className="font-mono text-[9px]" style={{ color: "#1A3A50" }}>{item.ts}</span>
              </div>

              {/* score */}
              <div className="text-right">
                <span className="font-syne font-extrabold text-2xl" style={{ color: col }}>{item.score}</span>
                <span className="font-mono text-[9px] block" style={{ color: "#3A6070" }}>/100</span>
              </div>

              {/* badge */}
              <span className="font-mono text-[10px] tracking-wider px-3 py-1.5 rounded-full whitespace-nowrap"
                style={{ background: col + "18", border: `1px solid ${col}33`, color: col }}>
                {item.verdict}
              </span>
            </div>
          );
        })}

        <p className="font-mono text-[10px] text-center mt-6" style={{ color: "#1A3A50" }}>
          Os dados acima são de exemplo (MVP). Em produção, serão persistidos em banco de dados.
        </p>
      </div>
      <Footer />
    </div>
  );
}
