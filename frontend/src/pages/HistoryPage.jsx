import Footer from "../components/Footer";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getHistory, getStats } from "../services/api";
import { scoreColor } from "../components/GaugeChart";

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

  const TYPE_ICON = { text: "💬", url: "🔗", image: "🖼️", audio: "🎙️", video: "📺" };

  return (
    <div className="relative min-h-screen pb-20">
      <div className="pointer-events-none fixed inset-0 opacity-10"
        style={{
          backgroundImage: "linear-gradient(#00D4FF 1px,transparent 1px),linear-gradient(90deg,#00D4FF 1px,transparent 1px)",
          backgroundSize: "60px 60px",
        }}/>

      <div className="relative z-10 max-w-4xl mx-auto px-5 pt-10">
        <div className="flex items-center justify-between mb-12">
          <div>
            <h1 className="font-syne font-extrabold text-3xl tracking-tight mb-2 text-[#CDE8F0]">Histórico de Verificações</h1>
            <p className="font-mono text-[11px] text-[#3A6070] uppercase tracking-[4px] font-bold">
              Todas as suas descobertas salvas
            </p>
          </div>
          <button onClick={() => navigate("/app")}
            className="font-syne font-bold text-[12px] tracking-[4px] px-8 py-3.5 rounded-2xl transition-all shadow-[0_10px_30px_rgba(0,212,255,0.2)] uppercase"
            style={{ 
              background: "linear-gradient(135deg,#00D4FF,#00FF87)", 
              color: "#04080C", border: "none", cursor: "pointer",
            }}>
            + VERIFICAR NOVO
          </button>
        </div>

        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
            {[
              { label: "TOTAL",       value: stats.total,      col: "#CDE8F0" },
              { label: "HOJE",        value: `${stats.daily_used}/${stats.daily_limit}`, col: stats.daily_used >= stats.daily_limit ? "#FF3B5C" : "#00FF87" },
              { label: "PRECISÃO",    value: stats.avg_score ? `${stats.avg_score}%` : "—", col: "#00D4FF" },
              { label: "PLANO",       value: stats.plan || "GRÁTIS", col: "#FFB830" },
            ].map(({ label, value, col }) => (
              <div key={label} className="rounded-2xl p-6 text-center border border-[#132435] bg-[#0A1520] shadow-sm">
                <span className="font-syne font-black text-3xl block mb-1" style={{ color: col }}>{value}</span>
                <span className="font-mono text-[9px] tracking-[5px] block font-bold uppercase text-[#3A6070]">{label}</span>
              </div>
            ))}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-24 opacity-20">
            <div className="anim-spin-cw w-10 h-10 rounded-full border-2"
              style={{ borderColor: "transparent", borderTopColor: "#00D4FF" }}/>
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-32 bg-[#0A1520] rounded-[2rem] border border-[#132435]">
            <p className="font-mono text-[12px] text-[#1A3A50] tracking-widest font-bold">
              Sua lista está vazia. Que tal fazer uma checagem?
            </p>
          </div>
        ) : (
          <div className="space-y-4">
             {items.map((item, i) => {
               const col = scoreColor(item.score);
               const dt  = new Date(item.created_at).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "2-digit" });
               return (
                 <div key={item.id}
                   className="p-5 rounded-2xl bg-[#0A1520] border border-[#132435] flex items-center gap-6 hover:bg-[#0F1E2E] hover:border-white/10 transition-all cursor-pointer group"
                   onClick={() => navigate(`/report/${item.id}`)}
                 >
                   <div className="w-12 h-12 rounded-xl bg-[#04080C] flex items-center justify-center text-2xl group-hover:scale-110 transition-transform shadow-inner">
                     {TYPE_ICON[item.query_type] || "📄"}
                   </div>

                   <div className="flex-1 min-w-0">
                     <div className="flex items-center gap-3 mb-2">
                        <span className="font-mono text-[10px] text-[#1A3A50] font-bold">{dt}</span>
                        <span className="font-mono text-[9px] font-bold px-2.5 py-0.5 rounded border border-[#132435] text-[#3A6070] uppercase">
                          {item.query_type}
                        </span>
                     </div>
                     <p className="font-mono text-[14px] font-black text-[#CDE8F0] truncate tracking-tight">
                       {item.query_input}
                     </p>
                   </div>

                   <div className="text-right">
                     <span className="font-mono text-[9px] tracking-widest px-3 py-1 rounded-full font-bold uppercase mb-2 inline-block"
                       style={{ background: col + "18", color: col, border: `1px solid ${col}33` }}>
                       {item.verdict}
                     </span>
                     <div className="font-syne font-black text-3xl tracking-tighter" style={{ color: col }}>
                       {item.score}%
                     </div>
                   </div>
                 </div>
               );
             })}

             {/* pagination */}
             {total > LIMIT && (
               <div className="flex items-center justify-center gap-6 mt-12 bg-[#0A1520] p-4 rounded-2xl border border-[#132435]">
                 <button disabled={page === 1} onClick={() => setPage(p => p - 1)}
                   className="font-mono text-[10px] tracking-widest px-6 py-2 rounded-xl transition-all"
                   style={{ background: "#04080C", border: "1px solid #132435", color: page === 1 ? "#1A3A50" : "#CDE8F0", cursor: page === 1 ? "not-allowed" : "pointer" }}>
                   ← ANTERIOR
                 </button>
                 <span className="font-mono text-[12px] font-bold text-[#3A6070]">
                   {page} de {Math.ceil(total / LIMIT)}
                 </span>
                 <button disabled={page * LIMIT >= total} onClick={() => setPage(p => p + 1)}
                   className="font-mono text-[10px] tracking-widest px-6 py-2 rounded-xl transition-all"
                   style={{ background: "#04080C", border: "1px solid #132435", color: page * LIMIT >= total ? "#1A3A50" : "#CDE8F0", cursor: page * LIMIT >= total ? "not-allowed" : "pointer" }}>
                   PRÓXIMA →
                 </button>
               </div>
             )}
          </div>
        )}
      </div>
      <Footer />
    </div>
  );
}
