import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getLog } from "../services/api";
import Footer from "../components/Footer";
import { Search, Shield, AlertTriangle, ArrowRight, Volume2, Phone, ChevronDown, ChevronUp, FileJson } from "lucide-react";

const BADGE_STYLES = {
  Authentic: {
    title: "AUTÊNTICO",
    color: "#00FF87",
    bg: "rgba(0,255,135,0.06)",
    border: "rgba(0,255,135,0.2)",
    headline: "Esta informação foi confirmada e é autêntica.",
  },
  AI_Generated: {
    title: "GERADO POR IA",
    color: "#00D4FF",
    bg: "rgba(0,212,255,0.06)",
    border: "rgba(0,212,255,0.2)",
    headline: "Este conteúdo foi identificado como produzido por inteligência artificial.",
  },
  Manipulated: {
    title: "MANIPULADO",
    color: "#FF3B5C",
    bg: "rgba(255,59,92,0.06)",
    border: "rgba(255,59,92,0.2)",
    headline: "Este conteúdo foi manipulado para enganar.",
  },
  Out_Of_Context: {
    title: "FORA DE CONTEXTO",
    color: "#FFB830",
    bg: "rgba(255,184,48,0.06)",
    border: "rgba(255,184,48,0.2)",
    headline: "Conteúdo real compartilhado com data ou história errada.",
  },
  Suspicious: {
    title: "SUSPEITO",
    color: "#5A7E94",
    bg: "rgba(90,126,148,0.06)",
    border: "rgba(90,126,148,0.2)",
    headline: "Não encontramos confirmação dessa informação em fontes oficiais.",
  },
  Scam: {
    title: "ALERTA: GOLPE",
    color: "#FF3B5C",
    bg: "rgba(255,59,92,0.1)",
    border: "rgba(255,59,92,0.3)",
    headline: "ATENÇÃO: Trata-se de uma tentativa de golpe ou fraude.",
  },
};

function formatTimestamp(ts) {
  if (!ts) return "—";
  return new Date(ts).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "2-digit",
    hour: "2-digit", minute: "2-digit"
  });
}

function formatScore(score) {
  return typeof score === "number" ? score : 50;
}

function truncate(str, len = 120) {
  if (!str) return "";
  return str.length > len ? str.slice(0, len) + "..." : str;
}

export default function ReportPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [result, setResult] = useState(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState("simple");
  const [technicalOpen, setTechnicalOpen] = useState(false);

  useEffect(() => {
    if (id) {
      getLog(id)
        .then((log) => {
          setResult(log.raw_result || log.result);
          setQuery(log.query_input);
        })
        .catch(() => navigate("/dashboard"))
        .finally(() => setLoading(false));
    } else {
      const r = sessionStorage.getItem("verify_result") || sessionStorage.getItem("verifai_result");
      const q = sessionStorage.getItem("verify_query") || sessionStorage.getItem("verifai_query");
      if (!r) { navigate("/app"); return; }
      try {
        setResult(JSON.parse(r));
        setQuery(q || "");
      } catch { navigate("/app"); }
      setLoading(false);
    }
  }, [id, navigate]);

  if (loading) {
    return (
      <div className="fixed inset-0 bg-[#04080C] flex flex-col items-center justify-center font-mono text-[#00D4FF] gap-4">
        <div className="w-8 h-8 border-3 border-[#00D4FF] border-t-transparent rounded-full animate-spin" />
        <span className="text-xs tracking-widest">ANALISANDO INFORMAÇÕES...</span>
      </div>
    );
  }

  if (!result) return null;

  const verdict = result.verdict || "Suspicious";
  const score = formatScore(result.score);
  const badge = BADGE_STYLES[verdict] || BADGE_STYLES.Suspicious;

  const shareText = result.whatsapp_share_text ||
    `⚠️ *Alerta do Verify:* Verifiquei essa mensagem e o resultado foi: ${badge.title}.\n\n📝 *Resumo:* ${result.summary || ""}\n\n🛡️ *Checado em:* https://verify.vercel.app`;

  const handleCopyText = () => {
    navigator.clipboard.writeText(shareText);
  };

  return (
    <div className="relative min-h-screen bg-[#04080C] text-[#CDE8F0] pb-20">
      <div className="pointer-events-none fixed inset-0" style={{ backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)", backgroundSize: "48px 48px", opacity: .15 }}/>

      <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 pt-10 sm:pt-14">

        <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
          <button
            onClick={() => navigate("/app")}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#0A1520] border border-[#132435] text-[#CDE8F0] hover:border-[#00D4FF] transition-all text-xs font-mono font-bold uppercase cursor-pointer"
          >
            <ArrowRight size={14} /> Nova Checagem
          </button>

          <div className="flex rounded-lg p-1 bg-[#0A1520] border border-[#132435]">
            <button
              onClick={() => setViewMode("simple")}
              className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all ${viewMode === "simple" ? "bg-[#00D4FF] text-[#04080C]" : "text-[#5A7E94]"}`}
            >
              Visão Simples
            </button>
            <button
              onClick={() => setViewMode("technical")}
              className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all ${viewMode === "technical" ? "bg-[#00D4FF] text-[#04080C]" : "text-[#5A7E94]"}`}
            >
              Visão Técnica
            </button>
          </div>
        </div>

        <div className="p-6 sm:p-8 rounded-xl border mb-8" style={{ backgroundColor: badge.bg, borderColor: badge.border }}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
            <div>
              <span className="text-[10px] font-mono tracking-[8px] uppercase font-bold text-[#8AA2B4] block mb-2">Resultado da Checagem</span>
              <h2 className="font-syne font-black text-2xl sm:text-3xl" style={{ color: badge.color }}>
                {badge.title}
              </h2>
            </div>
            <div className="bg-[#04080C88] px-4 py-3 rounded-lg border border-white/5 inline-block sm:block">
              <span className="text-[10px] font-mono text-[#8AA2B4] uppercase tracking-wider block">Índice de Confiança</span>
              <span className="font-syne font-black text-3xl" style={{ color: badge.color }}>{score}%</span>
            </div>
          </div>
          <p className="text-base text-[#CDE8F0] leading-relaxed mt-2">{badge.headline}</p>
        </div>

        <div className="space-y-4 mb-8">
          <button
            onClick={() => setTechnicalOpen(!technicalOpen)}
            className="w-full flex items-center justify-between p-4 rounded-lg bg-[#0A1520] border border-[#132435] text-[#CDE8F0] hover:border-[#00D4FF] transition-all cursor-pointer"
          >
            <span className="font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-2">
              <FileJson size={14} /> Detalhes Técnicos
            </span>
            {technicalOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          {technicalOpen && (
            <div className="p-4 rounded-lg bg-[#0A1520] border border-[#132435] font-mono text-[11px] text-[#8AA2B4] leading-relaxed overflow-x-auto">
              <pre className="whitespace-pre-wrap text-[10px]">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {viewMode === "simple" && (
          <div className="space-y-6">
            <div className="p-6 sm:p-8 rounded-xl bg-[#0A1520] border border-[#132435]">
              <h3 className="text-[10px] font-mono uppercase tracking-[8px] text-[#00D4FF] font-bold mb-4 flex items-center gap-2">
                <Shield size={14} /> O Que Você Precisa Saber
              </h3>
              <p className="text-lg text-[#CDE8F0] font-syne font-bold leading-relaxed mb-3">
                "{result.summary}"
              </p>
              {result.plain_explanation && (
                <p className="text-sm text-[#8AA2B4] leading-relaxed pt-3 border-t border-[#132435]">
                  {result.plain_explanation}
                </p>
              )}
            </div>

            {result.elderly_tip && (
              <div className="p-6 rounded-xl bg-[#00D4FF08] border border-[#00D4FF20]">
                <h4 className="text-[10px] font-mono uppercase tracking-[8px] text-[#00D4FF] font-bold mb-2 flex items-center gap-2">
                  <Shield size={14} /> Dica de Segurança Importante
                </h4>
                <p className="text-base text-[#CDE8F0] leading-relaxed">{result.elderly_tip}</p>
              </div>
            )}

            {result.red_flags && result.red_flags.length > 0 && (
              <div className="p-6 rounded-xl bg-[#0A1520] border border-[#132435]">
                <h4 className="text-[10px] font-mono uppercase tracking-[8px] text-[#FF3B5C] font-bold mb-4 flex items-center gap-2">
                  <AlertTriangle size={14} /> Sinais de Alerta Detectados
                </h4>
                <div className="space-y-3">
                  {result.red_flags.map((flag, idx) => (
                    <div key={idx} className="flex items-start gap-3 text-sm text-[#CDE8F0]">
                      <span className="text-[#FF3B5C] font-bold">✕</span>
                      <span>{flag}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="p-6 rounded-xl bg-[#070F17] border border-[#132435]">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-[10px] font-mono uppercase tracking-[8px] text-[#00FF87] font-bold flex items-center gap-2">
                  <Phone size={14} /> Mensagem Pronta para o WhatsApp
                </h4>
                <button
                  onClick={handleCopyText}
                  className="text-xs px-3 py-1 rounded-md bg-[#132435] text-[#CDE8F0] hover:bg-[#00D4FF] hover:text-[#04080C] transition-all font-mono cursor-pointer"
                >
                  Copiar
                </button>
              </div>
              <div className="p-4 rounded-lg bg-[#04080C] border border-[#132435] text-xs text-[#8AA2B4] font-mono whitespace-pre-wrap leading-relaxed">
                {shareText}
              </div>
            </div>
          </div>
        )}

        {viewMode === "technical" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div className="md:col-span-2 p-6 rounded-xl bg-[#0A1520] border border-[#132435]">
                <h3 className="text-[10px] font-mono uppercase tracking-[8px] text-[#3A6070] font-bold mb-4">Métricas de Análise</h3>
                {[
                  { label: "Semantic Score", value: result.semantic_score || score },
                  { label: "Domain Score", value: result.domain_score || 50 },
                  { label: "Neutrality Index", value: 100 - (result.sensationalism || 50) },
                ].map(item => (
                  <div key={item.label} className="mb-6">
                    <div className="flex justify-between font-mono text-[10px] mb-2 text-[#3A6070] uppercase tracking-widest">
                      <span>{item.label}</span>
                      <span className="text-[#CDE8F0]">{item.value}</span>
                    </div>
                    <div className="h-1.5 bg-[#04080C] rounded-full overflow-hidden border border-white/5">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{ width: `${Math.min(100, Math.max(0, item.value))}%`, backgroundColor: "#00D4FF" }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="p-6 rounded-xl bg-[#0A1520] border border-[#132435] flex flex-col items-center justify-center">
                <div className="w-24 h-24 rounded-full border-4 border-[#00D4FF] border-t-transparent animate-spin mb-4" />
                <div className="font-mono text-xs font-bold" style={{ color: badge.color }}>
                  {verdict.toUpperCase()}
                </div>
              </div>
            </div>

            {result.fact_check_evidence && result.fact_check_evidence.length > 0 && (
              <div className="p-6 rounded-xl bg-[#0A1520] border border-[#132435]">
                <h4 className="text-[10px] font-mono uppercase tracking-[8px] text-[#00D4FF] font-bold mb-4">Checagens de Agências Oficiais</h4>
                <div className="space-y-3">
                  {result.fact_check_evidence.map((fc, i) => (
                    <div key={i} className="p-3 rounded-md bg-[#04080C] border border-[#132435]">
                      <div className="flex justify-between font-bold text-[#CDE8F0] mb-1">
                        <span>{fc.publisher || "Agência de Checagem"}</span>
                        <span className="text-[#FFB800]">{fc.rating || "Avaliação"}</span>
                      </div>
                      <p className="text-[#8AA2B4] text-xs">{fc.claim_text}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <div className="mt-12 text-center">
          <button
            onClick={() => navigate("/app")}
            className="px-8 py-4 rounded-lg bg-[#00D4FF] hover:bg-[#00FF87] text-[#04080C] font-syne font-black text-sm tracking-widest transition-all uppercase shadow-xl hover:scale-105 cursor-pointer"
          >
            Checar Outra Notícia
          </button>
        </div>

      </div>
      <Footer />
    </div>
  );
}