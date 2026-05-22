import Footer from "../components/Footer";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getHistory, getStats } from "../services/api";
import { scoreColor, scoreLabel } from "../components/GaugeChart";

export default function HistoryPage() {
  const navigate = useNavigate();
  const [items,   setItems]   = useState([]);
  const [stats,   setStats]   = useState(null);
  const [page,    setPage]    = useState(1);
  const [total,   setTotal]   = useState(0);
  const [loading, setLoading] = useState(true);

  const LIMIT = 20;

  useEffect(() => {
    setLoading(true);
    Promise.all([getHistory(page), getStats()])
      .then(([hist, st]) => {
        setItems(hist.items || []);
        setTotal(hist.total || 0);
        setStats(st);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [page]);

  const TYPE_ICON = { text: "T", url: "U", image: "I", audio: "A", video: "V" };

  return (
    <div className="relative min-h-screen pb-20">
      <div className="pointer-events-none fixed inset-0"
        style={{
          backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)",
          backgroundSize: "48px 48px", opacity: .18,
        }}/>

      <div className="relative z-10 max-w-4xl mx-auto px-5 pt-10">
        {/* header */}
        <div className="flex items-center justify-between mb-8 fade-1">
          <div>
            <h1 className="font-syne font-extrabold text-2xl tracking-wide mb-1 text-text">Histórico</h1>
            <p className="font-mono text-[11px]" style={{ color: "#3A6070" }}>
              Todas as suas análises salvas no banco de dados
            </p>
          </div>
          <button onClick={() => navigate("/app")}
            className="font-syne font-bold text-[12px] tracking-widest px-5 py-2.5 rounded-lg transition-all"
            style={{ 
              background: "linear-gradient(135deg,#00D4FF,#00FF87)", 
              color: "#04080C", border: "none", cursor: "pointer",
              boxShadow: "0 0 20px rgba(0,212,255,.3)"
            }}>
            + NOVA ANÁLISE
          </button>
        </div>

        {/* stats strip */}
        {stats && (
          <div className="grid grid-cols-4 gap-3 mb-8 fade-2">
            {[
              { label: "TOTAL",       value: stats.total,      col: "#00D4FF" },
              { label: "HOJE",        value: `${stats.daily_used}/${stats.daily_limit}`, col: stats.daily_used >= stats.daily_limit ? "#FF3B5C" : "#00FF87" },
              { label: "SCORE MÉDIO", value: stats.avg_score ? `${stats.avg_score}` : "—", col: stats.avg_score ? scoreColor(stats.avg_score) : "#3A6070" },
              { label: "PLANO",       value: stats.plan,       col: stats.plan === "PRO" ? "#00D4FF" : "#3A6070" },
            ].map(({ label, value, col }) => (
              <div key={label} className="rounded-xl p-4 text-center"
                style={{ background: "#0A1520", border: "1px solid #132435" }}>
                <span className="font-syne font-extrabold text-2xl" style={{ color: col }}>{value}</span>
                <span className="font-mono text-[9px] tracking-widest block mt-1" style={{ color: "#3A6070" }}>{label}</span>
              </div>
            ))}
          </div>
        )}

        {/* table */}
        {loading ? (
          <div className="flex justify-center py-20">
            <div className="anim-spin-cw w-8 h-8 rounded-full border-2"
              style={{ borderColor: "transparent", borderTopColor: "#00D4FF" }}/>
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-20 fade-2">
            <span className="font-mono text-[11px]" style={{ color: "#1A3A50" }}>
              Nenhuma análise ainda. Faça sua primeira verificação!
            </span>
          </div>
        ) : (
          <>
            {/* column headers */}
            <div className="grid px-4 mb-2 fade-3"
              style={{ gridTemplateColumns: "32px 1fr 80px 90px 100px" }}>
              {["", "CONTEÚDO", "TIPO", "SCORE", "VEREDICTO"].map(h => (
                <span key={h} className="font-mono text-[9px] tracking-widest" style={{ color: "#1A3A50" }}>{h}</span>
              ))}
            </div>

            {items.map((item, i) => {
              const col = scoreColor(item.score);
              const dt  = new Date(item.created_at).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
              return (
                <div key={item.id}
                  className={`grid items-center px-4 py-4 rounded-xl mb-2 cursor-pointer transition-all fade-${Math.min(i + 3, 7)}`}
                  style={{
                    gridTemplateColumns: "32px 1fr 80px 90px 100px",
                    background: "#0A1520", border: "1px solid #132435",
                  }}
                  onClick={() => navigate(`/report/${item.id}`)}
                >
                  {/* type badge */}
                  <span className="font-mono text-[10px] font-bold w-6 h-6 rounded flex items-center justify-center"
                    style={{ background: "#0F1E2E", color: "#3A6070", border: "1px solid #132435" }}>
                    {TYPE_ICON[item.query_type] || "?"}
                  </span>

                  {/* content */}
                  <div className="min-w-0 px-3">
                    <p className="font-syne font-semibold text-[13px] truncate" style={{ color: "#CDE8F0" }}>
                      {item.query_input}
                    </p>
                    <p className="font-mono text-[10px]" style={{ color: "#1A3A50" }}>{dt}</p>
                  </div>

                  {/* query type */}
                  <span className="font-mono text-[9px] tracking-widest uppercase" style={{ color: "#3A6070" }}>
                    {item.query_type}
                  </span>

                  {/* score */}
                  <span className="font-syne font-extrabold text-xl" style={{ color: col }}>
                    {item.score}
                    <span className="font-mono font-normal text-[10px] ml-0.5" style={{ color: "#3A6070" }}>/100</span>
                  </span>

                  {/* verdict */}
                  <span className="font-mono text-[9px] tracking-wider px-2.5 py-1 rounded-full text-center"
                    style={{ background: col + "18", color: col, border: `1px solid ${col}33` }}>
                    {item.verdict}
                  </span>
                </div>
              );
            })}

            {/* pagination */}
            {total > LIMIT && (
              <div className="flex items-center justify-center gap-3 mt-6">
                <button disabled={page === 1} onClick={() => setPage(p => p - 1)}
                  className="font-mono text-[10px] tracking-widest px-4 py-2 rounded-lg"
                  style={{ background: "#0A1520", border: "1px solid #132435", color: page === 1 ? "#1A3A50" : "#3A6070", cursor: page === 1 ? "not-allowed" : "pointer" }}>
                  ← ANTERIOR
                </button>
                <span className="font-mono text-[10px]" style={{ color: "#3A6070" }}>
                  {page} / {Math.ceil(total / LIMIT)}
                </span>
                <button disabled={page * LIMIT >= total} onClick={() => setPage(p => p + 1)}
                  className="font-mono text-[10px] tracking-widest px-4 py-2 rounded-lg"
                  style={{ background: "#0A1520", border: "1px solid #132435", color: page * LIMIT >= total ? "#1A3A50" : "#3A6070", cursor: page * LIMIT >= total ? "not-allowed" : "pointer" }}>
                  PRÓXIMA →
                </button>
              </div>
            )}
          </>
        )}
      </div>
      <Footer />
    </div>
  );
}
