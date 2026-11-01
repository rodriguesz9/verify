import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { downloadPdfReport, getLog } from "../services/api";
import { readSessionReport, subscribeAnalysisReset } from "../services/privacyStorage";
import { useAuth } from "../hooks/authContext";
import Footer from "../components/Footer";
import AnimatedScore from "../components/report/AnimatedScore";
import EvidenceExplanation from "../components/report/EvidenceExplanation";
import { visibleDetectorScore, reportMediaHeadline, reportSourceHeadline, reportFactualHeadline, publicMediaRiskNotice, providerCoveragePresentation, publicCoveragePresentation, transcriptionPresentation, isTechnicalReportText, groundedReportExplanation } from "../utils/reportEvidence";
import { pdfExportError, pdfExportState, publicReportDetails } from "../utils/reportExport";
import { Shield, AlertTriangle, ArrowRight, Volume2, Phone, ChevronDown, ChevronUp, FileJson, Download } from "lucide-react";

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
  const { user, loading: authLoading } = useAuth();
  const [result, setResult] = useState(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState("simple");
  const [technicalOpen, setTechnicalOpen] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [pdfDownloading, setPdfDownloading] = useState(false);
  const [pdfError, setPdfError] = useState("");
  const [pdfNotice, setPdfNotice] = useState("");
  const [exportNow, setExportNow] = useState(Date.now);
  const reportEpoch = useRef(0);
  const hasDisplayedReport = Boolean(result) && !loading;

  useEffect(() => subscribeAnalysisReset(() => {
    reportEpoch.current += 1;
    setResult(null);
    setQuery("");
    setPdfError("");
    setPdfNotice("");
    setPdfDownloading(false);
    setSpeaking(false);
    window.speechSynthesis?.cancel();
    // An anonymous reset may not change auth dependencies; do not leave a blank report.
    // Initial auth hydration has no displayed result and must keep /report/:id intact.
    if (hasDisplayedReport) navigate("/app", { replace: true });
  }), [hasDisplayedReport, navigate]);

  useEffect(() => {
    const expires = result?.pdf_snapshot_expires_at;
    setExportNow(Date.now());
    if (!Number.isSafeInteger(expires)) return;
    const timer = setTimeout(() => setExportNow(Date.now()), Math.min(2147483647, Math.max(0, expires * 1000 - Date.now() + 1)));
    return () => clearTimeout(timer);
  }, [result]);

  useEffect(() => () => {
    window.speechSynthesis?.cancel();
  }, []);

  useEffect(() => {
    let active = true;
    const epoch = ++reportEpoch.current;
    const isCurrent = () => active && reportEpoch.current === epoch;
    setResult(null);
    setQuery("");
    setLoading(true);
    setPdfError("");
    setPdfNotice("");
    setPdfDownloading(false);
    const cancel = () => {
      active = false;
      if (reportEpoch.current === epoch) reportEpoch.current += 1;
    };
    if (authLoading) return cancel;
    if (id) {
      getLog(id)
        .then((log) => {
          if (!isCurrent()) return;
          setResult(log.raw_result || log.result);
          setQuery(log.query_input || "");
        })
        .catch(() => { if (isCurrent()) navigate("/dashboard"); })
        .finally(() => { if (isCurrent()) setLoading(false); });
    } else {
      const stored = readSessionReport();
      if (!stored) { navigate("/app"); return cancel; }
      setResult(stored.result);
      setQuery(stored.query || "");
      setLoading(false);
    }
    return cancel;
  }, [id, navigate, authLoading, user?.id]);

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
  const probablyFalse = result.veracity_status === "probably_false";
  const exportState = pdfExportState(result, exportNow);
  const inconclusive = result.analysis_status === "inconclusive";
  const publicCoverage = publicCoveragePresentation(result);
  const transcriptionState = transcriptionPresentation(result);
  const publicLimitations = [...new Set([...publicCoverage.limitations,
    ...(Array.isArray(result.limitations) ? result.limitations.filter((item) => typeof item === "string" && !isTechnicalReportText(item)) : [])])];
  const defaultBadge = probablyFalse ? {
    title: "PROVAVELMENTE FALSA / SEM FUNDAMENTO",
    color: "#FFB830", bg: "rgba(255,184,48,0.06)", border: "rgba(255,184,48,0.25)",
    headline: result.content_classification?.explanation || "A reputação da fonte e o teor do conteúdo apresentam sinais de risco; consulte os fundamentos desta avaliação.",
  } : inconclusive && verdict !== "Scam" ? {
    title: "ANÁLISE INCONCLUSIVA", color: "#FFCB55", bg: "rgba(255,203,85,.06)",
    border: "rgba(255,203,85,.3)", headline: "Análise inconclusiva. Confira abaixo o que as buscas encontraram e o que ainda ficou sem confirmação."
  } : BADGE_STYLES[verdict] || BADGE_STYLES.Suspicious;
  const mediaHeadline = reportMediaHeadline(result);
  const diagnosisHeadline = mediaHeadline || reportFactualHeadline(result) || reportSourceHeadline(result);
  const badge = !probablyFalse && diagnosisHeadline ? {...defaultBadge, ...diagnosisHeadline} : defaultBadge;
  const publicSummary = !probablyFalse && diagnosisHeadline?.diagnostic ? [badge.headline, publicMediaRiskNotice(result)].filter(Boolean).join(" ")
    : typeof result.summary === "string" && !isTechnicalReportText(result.summary) ? result.summary : publicCoverage.detail;
  const publicExplanation = groundedReportExplanation(result)?.text || (
    !diagnosisHeadline?.diagnostic && typeof result.plain_explanation === "string"
      && !isTechnicalReportText(result.plain_explanation) ? result.plain_explanation : "");
  const publicRedFlags = Array.isArray(result.red_flags)
    ? result.red_flags.filter((flag) => typeof flag === "string" && !isTechnicalReportText(flag)) : [];

  const shareText = !diagnosisHeadline?.diagnostic && typeof result.whatsapp_share_text === "string"
    && !isTechnicalReportText(result.whatsapp_share_text) ? result.whatsapp_share_text :
    `⚠️ *Alerta do Verify:* Resultado: ${badge.title}.\n\n📝 *Resumo:* ${publicSummary}\n\n🛡️ *Checado em:* ${typeof window === "undefined" ? "" : window.location.origin}`;

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
    const textToRead = `${badge.headline}. O que você precisa saber: ${publicSummary}. ${publicExplanation}. Dica de segurança: ${result.elderly_tip || ""}`;
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

  const handleDownloadPdf = async () => {
    if (pdfDownloading || pdfExportState(result) !== "ready") return;
    const epoch = reportEpoch.current;
    setPdfDownloading(true);
    setPdfError("");
    setPdfNotice("");
    try {
      const blob = await downloadPdfReport(result.pdf_snapshot_token);
      if (reportEpoch.current !== epoch) return;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      const hash = /^[a-f0-9]{64}$/i.test(result.file_hash_sha256 || "") ? result.file_hash_sha256.slice(0, 8) : "analise";
      anchor.href = url;
      anchor.download = `Relatorio_Verify_${hash}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setPdfNotice("PDF preparado. Se o arquivo não aparecer, confira a lista de downloads do navegador.");
      setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (error) {
      const message = await pdfExportError(error);
      if (reportEpoch.current === epoch) setPdfError(message);
    } finally {
      if (reportEpoch.current === epoch) setPdfDownloading(false);
    }
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

          <div className="report-view-switch rounded-lg p-1 bg-[#0A1520] border border-[#132435]" role="group" aria-label="Detalhamento do relatório">
            <button
              onClick={() => setViewMode("simple")}
              aria-pressed={viewMode === "simple"}
              className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all ${viewMode === "simple" ? "bg-[#00D4FF] text-[#04080C]" : "text-[#5A7E94]"}`}
            >
              Visão Simples
            </button>
            <button
              onClick={() => setViewMode("technical")}
              aria-pressed={viewMode === "technical"}
              className={`px-4 py-1.5 rounded-md text-xs font-bold transition-all ${viewMode === "technical" ? "bg-[#00D4FF] text-[#04080C]" : "text-[#5A7E94]"}`}
            >
              Visão Técnica
            </button>
          </div>
        </div>

        <div className="report-result-card min-w-0 break-words p-6 sm:p-8 rounded-xl border mb-8" style={{ backgroundColor: badge.bg, borderColor: badge.border }}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
            <div className="min-w-0">
              <span className="text-[10px] font-mono tracking-[8px] uppercase font-bold text-[#8AA2B4] block mb-2">Resultado da Checagem</span>
              <h2 className="report-result-title font-syne font-black text-2xl sm:text-3xl" style={{ color: badge.color }}>
                {badge.title}
              </h2>
            </div>
            <AnimatedScore value={inconclusive || diagnosisHeadline?.diagnostic ? null : result.score} color={badge.color} />
          </div>
          <p className="text-base text-[#CDE8F0] leading-relaxed mt-2">{badge.headline}</p>

          {result.provider_coverage && <section className="mt-5 border-t border-white/10 pt-4" aria-label="Cobertura da análise">
            <h3 className="font-bold text-base mb-2">{publicCoverage.title}</h3>
            <p className="text-sm leading-6 text-[#A7BFCD]">{publicCoverage.detail}</p>
            {transcriptionState.notice && <div role="status" aria-live="polite" aria-atomic="true" className="mt-4 rounded-xl border border-[#00D4FF]/40 bg-[#070F17] p-4">
              <h4 className="text-base font-bold text-[#CDE8F0]">Transcrição da fala · {providerCoveragePresentation("transcription", {status: transcriptionState.status}, result).label}</h4>
              <p className="mt-2 text-sm leading-6 text-[#A7BFCD]">{transcriptionState.detail}</p>
            </div>}
            <details className="mt-4 min-w-0 rounded-xl border border-[#1D3B4D] p-4">
              <summary className="cursor-pointer font-bold text-sm">Detalhes técnicos da cobertura</summary>
              <p className="mt-3 text-sm leading-6 text-[#A7BFCD]">Informações para auditoria, não porcentagens de verdade ou de precisão.</p>
            <div className="mt-3 grid min-w-0 gap-3 sm:grid-cols-2">{Object.entries(result.provider_coverage).filter(([, layer]) => layer && typeof layer === "object").map(([name, layer]) => {
              const coverage = providerCoveragePresentation(name, layer, result);
              return <div key={name} className="min-w-0 rounded-lg bg-[#04080C] p-3 text-sm leading-6 break-words">
                <strong className="capitalize">{name === "transcription" ? "Transcrição da fala" : name}</strong>
                <p className="mt-1">{coverage.label}</p>
                {coverage.detail && <p className="mt-2 text-[#8AA2B4]">{coverage.detail}</p>}
                {visibleDetectorScore(layer) !== null && <p>Sinal de IA: {(visibleDetectorScore(layer) * 100).toFixed(1)}% · não calibrado</p>}
                {visibleDetectorScore(layer, "deepfake_score") !== null && <p>Sinal de manipulação facial: {(visibleDetectorScore(layer, "deepfake_score") * 100).toFixed(1)}% · não calibrado</p>}
              </div>;
            })}</div>
            </details>
          </section>}
          {result.media_details?.duration_seconds && <p className="mt-4 text-sm">Duração: {result.media_details.duration_seconds.toFixed(1)} s. {result.content_type === "video" ? `Análise de ${result.forensics?.video?.sampled_frames ?? "alguns"} quadros amostrados, não do vídeo inteiro.` : ""}</p>}
          {publicLimitations.length > 0 && <details className="mt-4 text-sm text-[#FFCB55]">
            <summary className="cursor-pointer font-bold">Limitações desta checagem</summary>
            <ul className="mt-3 list-disc pl-5 space-y-2">{publicLimitations.map((item, index) => <li key={index}>{item}</li>)}</ul>
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
            <button
              type="button"
              onClick={handleDownloadPdf}
              disabled={pdfDownloading || exportState !== "ready"}
              aria-describedby="pdf-export-help"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#0A1520] border border-[#8AA2B4] text-[#CDE8F0] hover:border-[#00D4FF] font-mono text-xs font-bold uppercase tracking-wider transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Download size={16} aria-hidden="true" />
              {pdfDownloading ? "Preparando PDF..." : "Baixar relatório PDF"}
            </button>
          </div>
          <p id="pdf-export-help" className="mt-3 text-sm text-[#8AA2B4]">
            {exportState === "ready" ? "O PDF usa este mesmo resultado, sem refazer a análise. Evite compartilhar dados pessoais presentes no relatório."
              : exportState === "expired" ? "O prazo para baixar terminou. Se esta análise foi salva, abra-a pelo histórico para exportar o mesmo resultado."
              : "PDF indisponível para esta análise: faltam dados originais ou configuração de assinatura. Resultados antigos não serão refeitos automaticamente."}
          </p>
          {pdfError && <p role="alert" className="mt-3 text-sm text-[#FFCB55]">{pdfError}</p>}
          {pdfNotice && <p role="status" className="mt-3 text-sm text-[#CDE8F0]">{pdfNotice}</p>}
        </div>

        <EvidenceExplanation result={result} query={query} />

        {/* Actionable Steps for Seniors */}
        <div className="mb-8">
          {probablyFalse ? (
            <div className="p-6 rounded-2xl bg-[#FFB830]/10 border border-[#FFB830]/30 text-[#CDE8F0]">
              <h4 className="font-bold mb-2">Como interpretar esta classificação</h4>
              <p className="text-sm leading-6">A fonte tem reputação baixa ou não classificada e o conteúdo corresponde a uma categoria de risco. Isso indica provável falta de fundamento; não é refutação factual nem prova de intenção. Não compartilhe como fato confirmado.</p>
            </div>
          ) : inconclusive && verdict !== "Scam" ? (
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
            type="button"
            onClick={() => setTechnicalOpen(!technicalOpen)}
            aria-expanded={technicalOpen}
            aria-controls="report-technical-details"
            className="w-full flex items-center justify-between p-4 rounded-lg bg-[#0A1520] border border-[#132435] text-[#CDE8F0] hover:border-[#00D4FF] transition-all cursor-pointer"
          >
            <span className="font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-2">
              <FileJson size={14} /> Detalhes Técnicos
            </span>
            {technicalOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          {technicalOpen && (
            <div id="report-technical-details" className="min-w-0 p-4 rounded-lg bg-[#0A1520] border border-[#132435] font-mono text-[11px] text-[#8AA2B4] leading-relaxed overflow-x-auto">
              <pre className="whitespace-pre-wrap text-[10px]">
                {JSON.stringify(publicReportDetails(result), null, 2)}
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
                "{publicSummary}"
              </p>
              {publicExplanation && (
                <p className="text-sm text-[#8AA2B4] leading-relaxed whitespace-pre-wrap break-words pt-3 border-t border-[#132435]">
                  {publicExplanation}
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

            {publicRedFlags.length > 0 && (
              <div className="p-6 rounded-xl bg-[#0A1520] border border-[#132435]">
                <h4 className="text-[10px] font-mono uppercase tracking-[8px] text-[#FF3B5C] font-bold mb-4 flex items-center gap-2">
                  <AlertTriangle size={14} /> Sinais de Alerta Detectados
                </h4>
                <div className="space-y-3">
                  {publicRedFlags.map((flag, idx) => (
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
