import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import GaugeChart, { scoreColor } from "../components/GaugeChart";
import MetricBar from "../components/MetricBar";
import { getLog } from "../services/api";
import Footer from "../components/Footer";

function Card({ children, style = {}, title }) {
  return (
    <div className="rounded-xl border p-5 flex flex-col h-full"
      style={{ background: "#0A1520", borderColor: "#132435", ...style }}>
      {title && <span className="font-mono text-[9px] tracking-[4px] block mb-4 text-[#3A6070] uppercase">{title}</span>}
      {children}
    </div>
  );
}

export default function ReportPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [result, setResult] = useState(null);
  const [query,  setQuery]  = useState("");
  const [loading,setLoading]= useState(true);

  useEffect(() => {
    if (id) {
      getLog(id).then(log => { 
        setResult(log.raw_result || log.result); 
        setQuery(log.query_input); 
      })
      .catch(() => navigate("/dashboard"))
      .finally(() => setLoading(false));
    } else {
      const r = sessionStorage.getItem("verifai_result");
      const q = sessionStorage.getItem("verifai_query");
      if (!r) { navigate("/app"); return; }
      setResult(JSON.parse(r)); setQuery(q||""); setLoading(false);
    }
  }, [id, navigate]);

  if (loading) return <div className="fixed inset-0 bg-[#04080C] flex items-center justify-center font-mono text-[10px] text-cyan animate-pulse tracking-[5px]">PROCESSANDO LAUDO...</div>;
  if (!result) return null;

  const col = scoreColor(result.score);
  const serp = result.serpapi || {};

  return (
    <div className="relative min-h-screen pb-20">
      <div className="relative z-10 max-w-4xl mx-auto px-5 pt-8">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
             <span className="font-mono text-[10px] tracking-widest px-3 py-1 rounded bg-[#132435] text-cyan uppercase font-bold">Veredito VerifAI</span>
             <span className="text-[#1A3A50] font-mono text-[9px] uppercase tracking-widest">ID: {id?.slice(0,8) || "TEMP"}</span>
          </div>
          <button onClick={() => navigate("/app")} className="font-mono text-[10px] tracking-widest px-4 py-2 rounded-lg border border-[#132435] text-[#3A6070] cursor-pointer bg-transparent uppercase">Nova Auditoria</button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-5 mb-5">
           <div className="md:col-span-8">
              <Card title="Laudo Técnico – Gemini 3.1 Orchestrator">
                 <p className="font-syne font-bold text-lg leading-relaxed mb-6 text-[#CDE8F0]">"{result.summary}"</p>
                 <div className="grid grid-cols-3 gap-6 pt-5 border-t border-[#132435]">
                    <div><span className="font-mono text-[8px] text-[#3A6070] block mb-1">SCORE</span><div className="font-syne font-black text-2xl" style={{ color: col }}>{result.score}%</div></div>
                    <div><span className="font-mono text-[8px] text-[#3A6070] block mb-1">SEMÂNTICA</span><div className="font-syne font-black text-2xl text-cyan">{result.semantic_score}%</div></div>
                    <div><span className="font-mono text-[8px] text-[#3A6070] block mb-1">SENSACIONALISMO</span><div className="font-syne font-black text-2xl text-amber-500">{result.sensationalism}%</div></div>
                 </div>
              </Card>
           </div>
           <div className="md:col-span-4">
              <Card style={{ alignItems: 'center', justifyContent: 'center' }}>
                 <GaugeChart score={result.score} size={160}/>
                 <div className="mt-4 font-mono text-[11px] font-bold" style={{ color: col }}>{result.verdict?.toUpperCase()}</div>
              </Card>
           </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
           <div className="md:col-span-4 flex flex-col gap-5">
              <Card title="Alertas do Sistema">
                 {result.red_flags?.map((f, i) => <div key={i} className="font-mono text-[11px] text-[#FF3B5C] mb-2">✗ {f}</div>)}
                 {result.red_flags?.length === 0 && <p className="font-mono text-[11px] text-[#1A3A50]">Nenhum alerta crítico.</p>}
              </Card>
              <Card title="Métricas Forenses">
                 <MetricBar label="PRECISÃO" value={result.semantic_score} delay={0.1}/>
                 <MetricBar label="REPUTAÇÃO" value={result.domain_score} delay={0.2}/>
                 <MetricBar label="NEUTRALIDADE" value={100 - result.sensationalism} delay={0.3}/>
              </Card>
           </div>
           <div className="md:col-span-8">
              <Card title="Painel de Proveniência (SerpApi)">
                 {serp.available ? (
                   <div className="space-y-4">
                      <div className="p-3 bg-cyan/5 rounded-lg border border-cyan/10">
                         <span className="font-mono text-[9px] text-cyan block mb-1">ORIGEM CRONOLÓGICA</span>
                         <p className="font-syne font-bold text-[#CDE8F0]">{serp.earliest_known_date || "Data recente registrada"}</p>
                      </div>
                   </div>
                 ) : (
                   <p className="font-mono text-[11px] text-[#3A6070] italic leading-relaxed">Conteúdo analisado em tempo real. Nenhuma indexação anterior detectada.</p>
                 )}
              </Card>
           </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
