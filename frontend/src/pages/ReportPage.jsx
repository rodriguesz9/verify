import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import GaugeChart, { scoreColor } from "../components/GaugeChart";
import MetricBar from "../components/MetricBar";
import { getLog } from "../services/api";
import Footer from "../components/Footer";

export default function ReportPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [result, setResult] = useState(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [copied, setCopied] = useState(false);
  const [viewMode, setViewMode] = useState("simple"); // "simple" or "technical"

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
      if (!r) {
        navigate("/app");
        return;
      }
      try {
        setResult(JSON.parse(r));
        setQuery(q || "");
      } catch {
        navigate("/app");
      }
      setLoading(false);
    }
  }, [id, navigate]);

  // Stop TTS if user leaves page
  useEffect(() => {
    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  if (loading) {
    return (
      <div className="fixed inset-0 bg-[#04080C] flex flex-col items-center justify-center font-mono text-cyan gap-4">
        <div className="w-12 h-12 border-4 border-[#00D4FF] border-t-transparent rounded-full animate-spin" />
        <span className="text-sm tracking-widest animate-pulse">ANALISANDO INFORMAÇÕES...</span>
      </div>
    );
  }

  if (!result) return null;

  const verdict = result.verdict || "Suspicious";
  const score = result.score !== undefined ? result.score : 50;

  // Visual categorization
  let badgeConfig = {
    title: "SUSPEITO / NÃO CONFIRMADO",
    icon: "⚠️",
    color: "#FFB800",
    bg: "rgba(255, 184, 0, 0.12)",
    border: "rgba(255, 184, 0, 0.3)",
    headline: "Cuidado: Não encontramos confirmação dessa notícia em fontes oficiais.",
  };

  if (verdict === "Authentic" || score >= 80) {
    badgeConfig = {
      title: "VERDADEIRO / NOTÍCIA REAL",
      icon: "✅",
      color: "#00FF87",
      bg: "rgba(0, 255, 135, 0.12)",
      border: "rgba(0, 255, 135, 0.3)",
      headline: "Esta informação foi confirmada e é autêntica.",
    };
  } else if (verdict === "Scam") {
    badgeConfig = {
      title: "CUIDADO: ALERTA DE GOLPE",
      icon: "🚨",
      color: "#FF3B5C",
      bg: "rgba(255, 59, 92, 0.15)",
      border: "rgba(255, 59, 92, 0.4)",
      headline: "ATENÇÃO: Trata-se de uma tentativa de golpe ou roubo de dinheiro/dados!",
    };
  } else if (verdict === "Manipulated" || verdict === "AI_Generated" || score <= 35) {
    badgeConfig = {
      title: "FALSO / CONTEÚDO ENGANOSO",
      icon: "❌",
      color: "#FF3B5C",
      bg: "rgba(255, 59, 92, 0.12)",
      border: "rgba(255, 59, 92, 0.3)",
      headline: "Esta mensagem é falsa ou foi manipulada para enganar.",
    };
  } else if (verdict === "Out_Of_Context") {
    badgeConfig = {
      title: "FORA DE CONTEXTO",
      icon: "🔍",
      color: "#FF9900",
      bg: "rgba(255, 153, 0, 0.12)",
      border: "rgba(255, 153, 0, 0.3)",
      headline: "Notícia ou imagem real que está sendo compartilhada com data ou história errada.",
    };
  }

  // Text-To-Speech (Ouvir Explicação)
  const handleToggleSpeak = () => {
    if (!window.speechSynthesis) {
      alert("Seu navegador não suporta leitura de voz.");
      return;
    }

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    const textToRead = `Veredito do Verify: ${badgeConfig.title}. ${result.summary || ""}. Dica de segurança: ${result.elderly_tip || ""}`;
    const utterance = new SpeechSynthesisUtterance(textToRead);
    utterance.lang = "pt-BR";
    utterance.rate = 0.95; // slightly slower for elderly clarity
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
    setIsSpeaking(true);
  };

  // WhatsApp Share Message
  const shareText = result.whatsapp_share_text || 
    `⚠️ *Alerta do Verify:* Verifiquei essa mensagem e o resultado foi: *${badgeConfig.title}*.\n\n📝 *Resumo:* ${result.summary}\n\n🛡️ *Checado em:* https://verify.vercel.app`;

  const handleShareWhatsApp = () => {
    const encoded = encodeURIComponent(shareText);
    window.open(`https://api.whatsapp.com/send?text=${encoded}`, "_blank");
  };

  const handleCopyText = () => {
    navigator.clipboard.writeText(shareText);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  return (
    <div className="relative min-h-screen pb-20">
      {/* Subtle background */}
      <div className="pointer-events-none fixed inset-0" style={{ backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)", backgroundSize: "48px 48px", opacity: .2 }}/>

      <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 pt-10 sm:pt-14">
        
        {/* Top bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <button
            onClick={() => navigate("/app")}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#0A1520] border border-[#132435] text-[#CDE8F0] hover:border-[#00D4FF] transition-all text-xs font-mono font-bold uppercase cursor-pointer"
          >
            <span>←</span> Fazer Nova Checagem
          </button>

          {/* Mode Switcher */}
          <div className="flex rounded-xl p-1 bg-[#0A1520] border border-[#132435]">
            <button
              onClick={() => setViewMode("simple")}
              className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${viewMode === "simple" ? "bg-[#00D4FF] text-[#04080C]" : "text-[#5A7E94]"}`}
            >
              😊 Visão Fácil
            </button>
            <button
              onClick={() => setViewMode("technical")}
              className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${viewMode === "technical" ? "bg-[#00D4FF] text-[#04080C]" : "text-[#5A7E94]"}`}
            >
              🔬 Visão Detalhada
            </button>
          </div>
        </div>

        {/* Big Verdict Header Card */}
        <div
          className="p-6 sm:p-8 rounded-3xl mb-8 transition-all shadow-2xl"
          style={{
            backgroundColor: badgeConfig.bg,
            border: `2px solid ${badgeConfig.border}`,
          }}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
            <div className="flex items-center gap-3">
              <span className="text-4xl sm:text-5xl">{badgeConfig.icon}</span>
              <div>
                <span className="text-xs font-mono tracking-widest uppercase font-bold text-[#8AA2B4] block">
                  Resultado da Checagem
                </span>
                <h2 className="text-2xl sm:text-3xl font-syne font-black" style={{ color: badgeConfig.color }}>
                  {badgeConfig.title}
                </h2>
              </div>
            </div>

            <div className="sm:text-right bg-[#04080C88] px-4 py-2 rounded-2xl border border-white/5 inline-block sm:block">
              <span className="text-xs font-mono text-[#8AA2B4] block">Índice de Confiança</span>
              <span className="text-2xl font-syne font-black" style={{ color: badgeConfig.color }}>
                {score}%
              </span>
            </div>
          </div>

          <p className="text-base sm:text-lg text-[#CDE8F0] font-medium leading-relaxed mt-2">
            {badgeConfig.headline}
          </p>
        </div>

        {/* Quick Actions (Audio & WhatsApp) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
          <button
            onClick={handleToggleSpeak}
            className="flex items-center justify-center gap-3 p-4 rounded-2xl bg-[#0A1520] hover:bg-[#132435] border border-[#132435] hover:border-[#00D4FF] text-[#CDE8F0] transition-all font-bold text-sm sm:text-base cursor-pointer shadow-lg"
          >
            <span className="text-2xl">{isSpeaking ? "⏹️" : "🔊"}</span>
            <span>{isSpeaking ? "Parar Leitura de Voz" : "Ouvir Explicação em Voz Alta"}</span>
          </button>

          <button
            onClick={handleShareWhatsApp}
            className="flex items-center justify-center gap-3 p-4 rounded-2xl bg-[#00FF8715] hover:bg-[#00FF8725] border border-[#00FF8740] text-[#00FF87] transition-all font-bold text-sm sm:text-base cursor-pointer shadow-lg"
          >
            <span className="text-2xl">💬</span>
            <span>Avisar a Família no WhatsApp</span>
          </button>
        </div>

        {/* SIMPLE VIEW */}
        {viewMode === "simple" && (
          <div className="space-y-6">
            
            {/* Summary Explanation */}
            <div className="p-6 sm:p-8 rounded-3xl bg-[#0A1520] border border-[#132435]">
              <h3 className="text-xs font-mono uppercase tracking-widest text-[#00D4FF] font-bold mb-3 flex items-center gap-2">
                <span>📖</span> O Que Você Precisa Saber
              </h3>
              <p className="text-lg sm:text-xl text-[#CDE8F0] font-syne font-bold leading-relaxed mb-4">
                "{result.summary}"
              </p>
              {result.plain_explanation && (
                <p className="text-sm sm:text-base text-[#8AA2B4] leading-relaxed pt-3 border-t border-[#132435]">
                  {result.plain_explanation}
                </p>
              )}
            </div>

            {/* Elderly Protection Tip */}
            {result.elderly_tip && (
              <div className="p-6 rounded-3xl bg-[#00D4FF10] border border-[#00D4FF30]">
                <h4 className="text-xs font-mono uppercase tracking-widest text-[#00D4FF] font-bold mb-2 flex items-center gap-2">
                  <span>💡</span> Dica de Segurança Importante
                </h4>
                <p className="text-base text-[#CDE8F0] leading-relaxed">
                  {result.elderly_tip}
                </p>
              </div>
            )}

            {/* Warnings List */}
            {result.red_flags && result.red_flags.length > 0 && (
              <div className="p-6 rounded-3xl bg-[#0A1520] border border-[#132435]">
                <h4 className="text-xs font-mono uppercase tracking-widest text-[#FF3B5C] font-bold mb-4 flex items-center gap-2">
                  <span>⚠️</span> Sinais de Alerta Detectados
                </h4>
                <div className="space-y-3">
                  {result.red_flags.map((flag, idx) => (
                    <div key={idx} className="flex items-start gap-3 text-sm text-[#CDE8F0]">
                      <span className="text-[#FF3B5C] font-bold">✗</span>
                      <span>{flag}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Ready-to-copy WhatsApp Message Box */}
            <div className="p-6 rounded-3xl bg-[#070F17] border border-[#132435]">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-xs font-mono uppercase tracking-widest text-[#00FF87] font-bold flex items-center gap-2">
                  <span>📱</span> Mensagem Pronta para o WhatsApp
                </h4>
                <button
                  onClick={handleCopyText}
                  className="text-xs px-3 py-1 rounded-lg bg-[#132435] text-[#CDE8F0] hover:bg-[#00D4FF] hover:text-[#04080C] transition-all font-mono"
                >
                  {copied ? "✓ Copiado!" : "Copiar Texto"}
                </button>
              </div>
              <div className="p-4 rounded-2xl bg-[#04080C] border border-[#132435] text-xs sm:text-sm text-[#8AA2B4] font-mono whitespace-pre-wrap leading-relaxed">
                {shareText}
              </div>
            </div>

          </div>
        )}

        {/* TECHNICAL / DETAILED VIEW */}
        {viewMode === "technical" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
              
              <div className="md:col-span-8 p-6 rounded-3xl bg-[#0A1520] border border-[#132435]">
                <h3 className="text-xs font-mono uppercase tracking-widest text-[#3A6070] font-bold mb-4">
                  Métricas de Análise Forense
                </h3>
                <div className="space-y-4">
                  <MetricBar label="PRECISÃO SEMÂNTICA" value={result.semantic_score || score} delay={0.1} />
                  <MetricBar label="CONFIABILIDADE DO DOMÍNIO" value={result.domain_score || 50} delay={0.2} />
                  <MetricBar label="ÍNDICE DE NEUTRALIDADE" value={100 - (result.sensationalism || 50)} delay={0.3} />
                </div>
              </div>

              <div className="md:col-span-4 p-6 rounded-3xl bg-[#0A1520] border border-[#132435] flex flex-col items-center justify-center">
                <GaugeChart score={score} size={150} />
                <div className="mt-3 font-mono text-xs font-bold" style={{ color: badgeConfig.color }}>
                  {verdict.toUpperCase()}
                </div>
              </div>

            </div>

            {/* Fact-check and News sources */}
            {result.fact_check_evidence && result.fact_check_evidence.length > 0 && (
              <div className="p-6 rounded-3xl bg-[#0A1520] border border-[#132435]">
                <h4 className="text-xs font-mono uppercase tracking-widest text-[#00D4FF] font-bold mb-4">
                  Checagens de Agências Oficiais Encontradas
                </h4>
                <div className="space-y-3">
                  {result.fact_check_evidence.map((fc, i) => (
                    <div key={i} className="p-3 rounded-xl bg-[#04080C] border border-[#132435] text-xs">
                      <div className="flex justify-between font-bold text-[#CDE8F0] mb-1">
                        <span>{fc.publisher || "Agência de Checagem"}</span>
                        <span className="text-[#FFB800]">{fc.rating || "Avaliação"}</span>
                      </div>
                      <p className="text-[#8AA2B4]">{fc.claim_text}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Queried content */}
            {query && (
              <div className="p-6 rounded-3xl bg-[#070F17] border border-[#132435]">
                <h4 className="text-xs font-mono uppercase tracking-widest text-[#3A6070] font-bold mb-2">
                  Conteúdo Auditado
                </h4>
                <p className="text-xs font-mono text-[#8AA2B4] break-words line-clamp-4">
                  {query}
                </p>
              </div>
            )}

          </div>
        )}

        {/* Bottom CTA */}
        <div className="mt-12 text-center">
          <button
            onClick={() => navigate("/app")}
            className="px-8 py-4 rounded-2xl bg-[#00D4FF] hover:bg-[#00FF87] text-[#04080C] font-syne font-black text-sm tracking-widest transition-all uppercase shadow-xl hover:scale-105"
          >
            🔍 Checar Outra Notícia
          </button>
        </div>

      </div>

      <Footer />
    </div>
  );
}
