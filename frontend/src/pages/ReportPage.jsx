import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import GaugeChart, { scoreColor } from "../components/GaugeChart";
import MetricBar from "../components/MetricBar";
import { getLog } from "../services/api";
import Footer from "../components/Footer";

function Card({ children, style = {} }) {
  return (
    <div className="rounded-xl border p-5"
      style={{ background: "#0A1520", borderColor: "#132435", ...style }}>
      {children}
    </div>
  );
}
function Lbl({ children, color = "#3A6070" }) {
  return <span className="font-mono text-[9px] tracking-[3px] block mb-3" style={{ color }}>{children}</span>;
}
function Flag({ text, type }) {
  const col  = type === "red" ? "#FF3B5C" : type === "amber" ? "#FFB830" : "#00FF87";
  const icon = type === "red" ? "X" : type === "amber" ? "!" : "V";
  return (
    <div className="flex items-start gap-2 mb-2">
      <span className="font-bold text-sm mt-0.5" style={{ color: col }}>{icon}</span>
      <span className="font-mono text-[11px] leading-relaxed" style={{ color: "#CDE8F0" }}>{text}</span>
    </div>
  );
}
function FactCard({ claim }) {
  const rating  = claim.rating || "N/D";
  const isFalse = /falso|false|incorreto|mislead|enganoso/i.test(rating);
  const isTrue  = /verdadeiro|true|correto|accurate|confirmado/i.test(rating);
  const col     = isTrue ? "#00FF87" : isFalse ? "#FF3B5C" : "#FFB830";
  return (
    <div className="p-4 rounded-lg mb-3"
      style={{ background:"#0F1E2E", border:"1px solid #132435", borderLeft:`3px solid ${col}` }}>
      <p className="font-syne text-[13px] leading-relaxed mb-3" style={{ color:"#CDE8F0" }}>
        {(claim.claim_text||"").slice(0,200)}{(claim.claim_text||"").length>200?"...":""}
      </p>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="font-mono text-[10px] px-2.5 py-1 rounded"
          style={{ background:col+"22", color:col, fontWeight:600 }}>{rating.toUpperCase()}</span>
        <span className="font-mono text-[10px]" style={{ color:"#3A6070" }}>{claim.publisher}</span>
        {claim.url && <a href={claim.url} target="_blank" rel="noopener noreferrer"
          className="font-mono text-[10px] ml-auto" style={{ color:"#00D4FF" }}>ver fonte</a>}
      </div>
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
      getLog(id).then(log => { setResult(log.result); setQuery(log.query_input); })
        .catch(() => navigate("/history")).finally(() => setLoading(false));
    } else {
      const r = sessionStorage.getItem("verifai_result");
      const q = sessionStorage.getItem("verifai_query");
      if (!r) { navigate("/"); return; }
      setResult(JSON.parse(r)); setQuery(q||""); setLoading(false);
    }
  }, [id, navigate]);

  if (loading) return <div className="fixed inset-0 bg-bg flex items-center justify-center">
    <div className="anim-spin-cw w-8 h-8 rounded-full border-2"
      style={{ borderColor:"transparent", borderTopColor:"#00D4FF" }}/></div>;
  if (!result) return null;

  const col  = scoreColor(result.score);
  const hive = result.hive_result;

  return (
    <div className="relative min-h-screen pb-20">
      <div className="pointer-events-none fixed inset-0" style={{
        backgroundImage:"linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)",
        backgroundSize:"48px 48px", opacity:.2 }}/>
      <div className="relative z-10 max-w-4xl mx-auto px-5 pt-8">
        <div className="flex items-center justify-between mb-6 fade-1">
          <div className="flex items-center gap-3">
            <span className="font-mono text-[10px] tracking-widest px-3 py-1.5 rounded-full"
              style={{ background:col+"20", border:`1px solid ${col}44`, color:col }}>{result.verdict}</span>
            <span className="font-mono text-[10px]" style={{ color:"#3A6070" }}>RELATÓRIO DE AUDITORIA</span>
          </div>
          <button onClick={() => id ? navigate("/history") : navigate("/")}
            className="font-mono text-[10px] tracking-widest px-4 py-2 rounded-lg"
            style={{ background:"transparent", border:"1px solid #132435", color:"#3A6070", cursor:"pointer" }}>
            {id ? "HISTORICO" : "NOVA ANALISE"}
          </button>
        </div>
        <Card style={{ display:"flex", gap:12, marginBottom:16 }}>
          <span className="font-mono text-[9px] tracking-widest mt-0.5" style={{ color:"#3A6070" }}>INPUT</span>
          <p className="font-mono text-[12px] leading-relaxed flex-1" style={{ color:"#3A6070" }}>
            {query.slice(0,250)}{query.length>250?"...":""}
          </p>
        </Card>
        <div className="grid gap-4 mb-4" style={{ gridTemplateColumns:"220px 1fr" }}>
          <Card style={{ display:"flex", flexDirection:"column", alignItems:"center", paddingTop:28, borderTop:`3px solid ${col}` }}>
            <Lbl>INDICE DE CREDIBILIDADE</Lbl>
            <GaugeChart score={result.score} size={200}/>
            <div className="mt-4 w-full text-center px-4 py-2 rounded-lg"
              style={{ background:col+"15", border:`1px solid ${col}33` }}>
              <span className="font-mono text-[10px] tracking-widest" style={{ color:col }}>{result.verdict}</span>
            </div>
          </Card>
          <div className="flex flex-col gap-4">
            <Card>
              <Lbl>LAUDO TECNICO</Lbl>
              <p className="font-syne font-semibold text-[14px] leading-relaxed mb-3" style={{ color:"#CDE8F0" }}>{result.summary}</p>
              {result.emotional_triggers && <span className="inline-flex items-center gap-1.5 font-mono text-[10px] px-3 py-1.5 rounded-full"
                style={{ background:"rgba(255,184,48,.12)", border:"1px solid rgba(255,184,48,.3)", color:"#FFB830" }}>
                GATILHOS EMOCIONAIS DETECTADOS</span>}
            </Card>
            <Card>
              <Lbl>DECOMPOSICAO DO SCORE</Lbl>
              <MetricBar label="SEMANTICA"           value={result.semantic_score}       delay={0.2}/>
              <MetricBar label="REPUTACAO DA FONTE"  value={result.domain_score}         delay={0.4}/>
              <MetricBar label="ANTI-SENSACIONALISMO" value={100-result.sensationalism}  delay={0.6}/>
            </Card>
          </div>
        </div>
        {hive && hive.available && (
          <Card style={{ marginBottom:16 }}>
            <Lbl color="#00D4FF">ANALISE HIVE - DETECCAO DE IA / DEEPFAKE</Lbl>
            <div className="flex items-center gap-5">
              <div>
                <span className="font-syne font-extrabold text-3xl"
                  style={{ color: hive.ai_probability>0.65?"#FF3B5C":"#00FF87" }}>
                  {Math.round((hive.ai_probability||0)*100)}%</span>
                <span className="font-mono text-[10px] block" style={{ color:"#3A6070" }}>PROBABILIDADE DE IA</span>
              </div>
              <span className="font-mono text-[10px] tracking-widest px-3 py-1.5 rounded-full"
                style={{
                  background: hive.is_ai_generated?"rgba(255,59,92,.15)":"rgba(0,255,135,.15)",
                  color:      hive.is_ai_generated?"#FF3B5C":"#00FF87",
                  border:`1px solid ${hive.is_ai_generated?"rgba(255,59,92,.3)":"rgba(0,255,135,.3)"}`,
                }}>
                {hive.is_ai_generated?"IA DETECTADA":"APARENTA AUTENTICO"}
              </span>
            </div>
          </Card>
        )}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <Card>
            <Lbl color="#FF3B5C">ALERTAS</Lbl>
            {result.red_flags?.length ? result.red_flags.map((f,i)=><Flag key={i} text={f} type="red"/>)
              : <p className="font-mono text-[11px]" style={{ color:"#1A3A50" }}>Nenhum alerta.</p>}
          </Card>
          <Card>
            <Lbl color="#00FF87">SINAIS POSITIVOS</Lbl>
            {result.positive_signals?.length ? result.positive_signals.map((f,i)=><Flag key={i} text={f} type="green"/>)
              : <p className="font-mono text-[11px]" style={{ color:"#1A3A50" }}>Nenhum.</p>}
            {result.logical_fallacies?.length>0&&<>
              <Lbl color="#FFB830" style={{ marginTop:12 }}>FALACIAS LOGICAS</Lbl>
              {result.logical_fallacies.map((f,i)=><Flag key={i} text={f} type="amber"/>)}
            </>}
          </Card>
        </div>
        {result.recommended_sources?.length>0&&(
          <Card style={{ marginBottom:16 }}>
            <Lbl color="#00D4FF">FONTES RECOMENDADAS</Lbl>
            <div className="flex flex-wrap gap-2">
              {result.recommended_sources.map((s,i)=>(
                <span key={i} className="font-mono text-[11px] px-3 py-1.5 rounded-lg"
                  style={{ background:"rgba(0,212,255,.08)", border:"1px solid rgba(0,212,255,.2)", color:"#00D4FF" }}>
                  {s}</span>
              ))}
            </div>
          </Card>
        )}
        {result.fact_checks?.length>0&&(
          <Card style={{ marginBottom:16 }}>
            <Lbl color="#00D4FF">CHECAGENS DE AGENCIAS ({result.fact_checks.length})</Lbl>
            {result.fact_checks.slice(0,5).map((fc,i)=><FactCard key={i} claim={fc}/>)}
          </Card>
        )}
        <Card style={{ display:"flex", alignItems:"center", gap:16 }}>
          <span style={{ color:"#00D4FF", fontSize:20 }}>*</span>
          <div><Lbl>ANALISE DE FONTE</Lbl>
            <span className="font-mono text-[11px]" style={{ color:"#CDE8F0" }}>{result.domain_note}</span>
          </div>
          <div className="ml-auto text-right">
            <span className="font-syne font-bold text-2xl" style={{ color:scoreColor(result.domain_score) }}>
              {result.domain_score}</span>
            <span className="font-mono text-[9px] block" style={{ color:"#3A6070" }}>REPUTACAO</span>
          </div>
        </Card>
        <p className="font-mono text-[10px] text-center mt-8" style={{ color:"#1A3A50" }}>
          VerifAI MVP - Resultado gerado por IA, nao substitui verificacao profissional.
        </p>
      </div>
      <Footer />
    </div>
  );
}
