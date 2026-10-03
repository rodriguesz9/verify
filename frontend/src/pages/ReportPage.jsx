import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getLog } from "../services/api";
import Footer from "../components/Footer";
import AnimatedScore from "../components/report/AnimatedScore";
import EvidenceExplanation from "../components/report/EvidenceExplanation";
import { Shield, AlertTriangle, ArrowRight, Volume2, Phone, ChevronDown, ChevronUp, FileJson } from "lucide-react";

const BADGE_STYLES = {
  False: {
    title: "AFIRMAÇÃO REFUTADA",
    color: "#FF3B5C", bg: "rgba(255,59,92,0.06)", border: "rgba(255,59,92,0.2)",
    headline: "Checagens editoriais distintas refutam a mesma afirmação. Consulte os argumentos, a data e o contexto nas fontes originais.",
  },
  Authentic: {
    title: "INFORMAÇÃO CORROBORADA",
    color: "#00FF87",
    bg: "rgba(0,255,135,0.06)",
    border: "rgba(0,255,135,0.2)",
    headline: "As fontes consultadas corroboram a informação. Confira as referências; isso não garante que uma mídia seja autêntica.",
  },
  AI_Generated: {
    title: "INDÍCIOS DE IA",
    color: "#00D4FF",
    bg: "rgba(0,212,255,0.06)",
    border: "rgba(0,212,255,0.2)",
    headline: "Há indícios de geração por IA nas camadas disponíveis. Confira as evidências e limitações.",
  },
  Manipulated: {
    title: "INDÍCIOS DE MANIPULAÇÃO",
    color: "#FF3B5C",
    bg: "rgba(255,59,92,0.06)",
    border: "rgba(255,59,92,0.2)",
    headline: "Há indícios de possível manipulação nas camadas disponíveis. Isso não comprova intenção de enganar.",
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
    headline: "Os sinais disponíveis exigem revisão. Consulte a fonte original e as limitações desta análise.",
  },
  Scam: {
    title: "ALERTA: SINAIS DE GOLPE",
    color: "#FF3B5C",
    bg: "rgba(255,59,92,0.1)",
    border: "rgba(255,59,92,0.3)",
    headline: "Há padrões de possível golpe ou fraude. Confirme pelo canal oficial antes de agir.",
  },
};

export default function ReportPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [result, setResult] = useState(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState("simple");
  const [technicalOpen, setTechnicalOpen] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => () => {
    window.speechSynthesis?.cancel();
  }, []);

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
  const inconclusive = result.analysis_status === "inconclusive";
  const badge = inconclusive ? {
    title: "ANÁLISE INCONCLUSIVA", color: "#FFCB55", bg: "rgba(255,203,85,.06)",
    border: "rgba(255,203,85,.3)", headline: "Não há evidência suficiente para concluir. Isso não significa que o conteúdo seja falso ou autêntico."
  } : BADGE_STYLES[verdict] || BADGE_STYLES.Suspicious;

  const shareText = result.whatsapp_share_text ||
    `⚠️ *Alerta do Verify:* Resultado: ${badge.title}.\n\n📝 *Resumo:* ${result.summary || ""}\n\n🛡️ *Checado em:* ${window.location.origin}`;

  const handleCopyText = () => {
    navigator.clipboard.writeText(shareText);
  };

  const handleSpeak = () => {
    if (!window.speechSynthesis) return;
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    window.speechSynthesis.cancel();
    const textToRead = `${badge.headline}. O que você precisa saber: ${result.summary || ""}. ${result.plain_explanation || ""}. Dica de segurança: ${result.elderly_tip || ""}`;
    const utterance = new SpeechSynthesisUtterance(textToRead);
    utterance.lang = "pt-BR";
    utterance.rate = 0.92;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  const handleShareWhatsAppDirect = () => {
    const url = `https://api.whatsapp.com/send?text=${encodeURIComponent(shareText)}`;
    window.open(url, "_blank");
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
              Visão Simples (Idosos e Família)
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
            <AnimatedScore value={inconclusive ? null : result.score} color={badge.color} />
          </div>
          <p className="text-base text-[#CDE8F0] leading-relaxed mt-2">{badge.headline}</p>

          {result.provider_coverage && <section className="mt-5 border-t border-white/10 pt-4" aria-label="Cobertura da análise">
            <h3 className="font-bold text-sm mb-3">O que realmente foi verificado</h3>
            <div className="grid gap-2 sm:grid-cols-3">{Object.entries(result.provider_coverage).map(([name, layer]) =>
              <div key={name} className="rounded-lg bg-[#04080C] p-3 text-xs break-words">
                <strong className="capitalize">{name}</strong>
                <p className="mt-1">{layer.status === "success" ? "Respondeu" : layer.status === "partial" ? "Cobertura parcial" : layer.status === "no_results" ? "Consulta sem resultados" : "Não disponível"}</p>
                {typeof layer.reason === "string" && <p className="mt-2 text-[#8AA2B4]">{layer.reason}</p>}
                {typeof layer.ai_score === "number" && <p>Sinal de IA: {(layer.ai_score * 100).toFixed(1)}% · não calibrado</p>}
                {typeof layer.deepfake_score === "number" && <p>Sinal de manipulação facial: {(layer.deepfake_score * 100).toFixed(1)}% · não calibrado</p>}
              </div>)}</div>
          </section>}
          {result.media_details?.duration_seconds && <p className="mt-4 text-sm">Duração: {result.media_details.duration_seconds.toFixed(1)} s. {result.content_type === "video" ? `Análise de ${result.forensics?.video?.sampled_frames ?? "alguns"} quadros amostrados, não do vídeo inteiro.` : ""}</p>}
          {result.limitations?.length > 0 && <details className="mt-4 text-sm text-[#FFCB55]">
            <summary className="cursor-pointer font-bold">Limitações desta checagem</summary>
            <ul className="mt-3 list-disc pl-5 space-y-2">{result.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul>
          </details>}

          <div className="mt-5 flex flex-wrap gap-3 pt-4 border-t border-white/10">
            <button
              type="button"
              onClick={handleSpeak}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#00D4FF]/20 border border-[#00D4FF] text-[#00D4FF] hover:bg-[#00D4FF]/30 font-mono text-xs font-bold uppercase tracking-wider transition-all cursor-pointer"
            >
              <Volume2 size={16} className={speaking ? "animate-pulse text-[#00FF87]" : ""} />
              {speaking ? "Parar leitura de voz" : "🔊 Ouvir explicação em voz alta"}
            </button>
            <button
              type="button"
              onClick={handleShareWhatsAppDirect}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#25D366]/20 border border-[#25D366] text-[#25D366] hover:bg-[#25D366]/30 font-mono text-xs font-bold uppercase tracking-wider transition-all cursor-pointer"
            >
              <Phone size={15} />
              Avisar família no WhatsApp
            </button>
          </div>
        </div>

        <EvidenceExplanation result={result} query={query} />

        {/* Actionable Steps for Seniors */}
        <div className="mb-8">
          {inconclusive ? (
            <div className="p-6 rounded-2xl bg-[#FFCB55]/10 border border-[#FFCB55]/30 text-[#CDE8F0]">
              <h4 className="font-bold mb-2">Próximo passo: confirme a fonte</h4>
              <p className="text-sm leading-6">Não use este resultado como prova de falsidade ou autenticidade. Procure o arquivo original e confirme a informação por um canal independente.</p>
            </div>
          ) : verdict === "Scam" || verdict === "Manipulated" || verdict === "Suspicious" ? (
            <div className="p-6 rounded-2xl bg-[#FF3B5C]/10 border border-[#FF3B5C]/30 text-[#CDE8F0]">
              <h4 className="font-syne font-bold text-base text-[#FF8195] mb-3 flex items-center gap-2">
                <AlertTriangle size={18} /> O QUE VOCÊ DEVE FAZER AGORA:
              </h4>
              <ol className="space-y-2.5 font-mono text-sm leading-6 list-decimal list-inside text-[#CDE8F0]">
                <li><strong>Não envie dinheiro</strong> com base apenas nesta mensagem; confirme a identidade por outro canal.</li>
                <li><strong>NÃO clique em links</strong> nem forneça senhas ou códigos recebidos por SMS.</li>
                <li><strong>Se disseram que é um parente ou filho</strong>, ligue para o número de telefone antigo dele para confirmar.</li>
                <li><strong>Compartilhe este aviso</strong> no grupo da família para proteger outras pessoas.</li>
              </ol>
            </div>
          ) : (
            <div className="p-6 rounded-2xl bg-[#00FF87]/10 border border-[#00FF87]/30 text-[#CDE8F0]">
              <h4 className="font-syne font-bold text-base text-[#00FF87] mb-2 flex items-center gap-2">
                <Shield size={18} /> CONFIRA O CONTEXTO:
              </h4>
              <p className="font-mono text-sm leading-6 text-[#CDE8F0]">
                Leia as fontes e limitações antes de compartilhar. Um conteúdo gerado por IA não é necessariamente um golpe, e nenhum resultado garante que uma informação seja verdadeira.
              </p>
            </div>
          )}
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
                  { label: "Sinal semântico · heurístico", value: result.semantic_score },
                  { label: "Reputação do domínio · heurística", value: result.domain_score },
                  { label: "Neutralidade do texto · heurística", value: typeof result.sensationalism === "number" ? 100 - result.sensationalism : null },
                ].map(item => (
                  <div key={item.label} className="mb-6">
                    <AnimatedScore value={inconclusive ? null : item.value} label={item.label} compact />
                  </div>
                ))}
              </div>

              <div className="p-6 rounded-xl bg-[#0A1520] border border-[#132435] flex flex-col items-center justify-center">
                <Shield size={56} className="text-[#00D4FF] mb-4" aria-hidden="true" />
                <div className="font-mono text-xs font-bold" style={{ color: badge.color }}>
                  {verdict.toUpperCase()}
                </div>
              </div>
            </div>

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
