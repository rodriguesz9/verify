import Footer from "../components/Footer";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getHistory, getStats } from "../services/api";

const TYPE_ICON = { Text: "📝", Image: "🖼️", Video: "🎬", Audio: "🎵" };
const VERDICT_COLORS = {
  Authentic: "#00FF87",
  AI_Generated: "#00D4FF",
  Manipulated: "#FF3B5C",
  Out_Of_Context: "#FFB830",
  Suspicious: "#3A6070"
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getHistory(1), getStats()])
      .then(([hist, st]) => { setItems(hist.items || []); setStats(st); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="relative min-h-screen pb-20">
      <div className="relative z-10 max-w-4xl mx-auto px-5 pt-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="font-syne font-extrabold text-2xl text-[#CDE8F0] tracking-widest uppercase">Meu Painel</h1>
            <p className="font-mono text-[10px] text-[#3A6070] uppercase tracking-widest">Resumo das suas verificações</p>
          </div>
          <button onClick={() => navigate("/app")} className="font-syne font-bold text-[12px] tracking-[3px] px-8 py-3 rounded-xl border-none cursor-pointer shadow-lg hover:scale-105 transition-all uppercase" style={{ background: "linear-gradient(135deg,#00D4FF,#00FF87)", color: "#04080C" }}>
            + NOVA CHECAGEM
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
           {[{l: "TOTAL", v: stats?.total}, {l: "PRECISÃO", v: (stats?.avg_score || 0) + "%"}, {l: "USO HOJE", v: stats?.daily_used}, {l: "PLANO", v: stats?.plan || "GRÁTIS"}].map(s => (
             <div key={s.l} className="p-6 rounded-2xl bg-[#0A1520] border border-[#132435] text-center shadow-inner group hover:border-[#00D4FF44] transition-all">
                <span className="font-syne font-black text-3xl text-[#CDE8F0] block mb-1 group-hover:scale-110 transition-transform">{s.v || 0}</span>
                <span className="font-mono text-[9px] text-[#3A6070] tracking-[4px] uppercase font-bold">{s.l}</span>
             </div>
           ))}
        </div>

        <div className="space-y-4">
          <div className="px-2 mb-4 font-mono text-[11px] text-[#1A3A50] tracking-[5px] uppercase font-bold border-l-2 border-[#00D4FF] ml-2 pl-4">Últimas Verificações</div>
          {loading ? <div className="text-center font-mono text-[10px] opacity-20 py-20 animate-pulse tracking-[8px]">SINCRONIZANDO...</div> : items.length === 0 ? (
            <div className="bg-[#0A1520] rounded-2xl p-20 border border-[#132435] text-center">
              <p className="font-mono text-[12px] text-[#1A3A50]">Nenhuma verificação feita ainda.</p>
            </div>
          ) : items.map((item) => {
            const col = VERDICT_COLORS[item.verdict_label] || "#3A6070";
            return (
              <div key={item.id} className="p-5 rounded-2xl bg-[#0A1520] border border-[#132435] flex items-center gap-6 hover:border-white/10 hover:bg-[#0F1E2E] transition-all cursor-pointer shadow-sm group" onClick={() => navigate(`/report/${item.id}`)}>
                <div className="w-12 h-12 rounded-xl bg-[#04080C] flex items-center justify-center text-2xl shadow-inner group-hover:rotate-6 transition-transform">{TYPE_ICON[item.content_type] || "❓"}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="font-mono text-[9px] px-3 py-1 rounded-full border font-bold tracking-widest uppercase" style={{ borderColor: col, color: col, background: col + "11" }}>{item.verdict_label}</span>
                    <span className="font-mono text-[10px] text-[#1A3A50] font-bold">{new Date(item.created_at).toLocaleDateString()}</span>
                  </div>
                  <p className="font-mono text-[13px] text-[#CDE8F0] truncate font-black tracking-tight">{item.query_input}</p>
                </div>
                <div className="text-right">
                  <div className="font-syne font-black text-2xl tracking-tighter" style={{ color: col }}>{item.verdict_score}%</div>
                  <div className="font-mono text-[8px] text-[#3A6070] font-bold uppercase tracking-widest">Certeza</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <Footer />
    </div>
  );
}
