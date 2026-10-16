import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/authContext";
import {
  FileText, Link2, Image, Mic, Upload, Search, Shield, CheckCircle,
  AlertTriangle, ArrowRight, Volume2, Phone, ChevronDown, ChevronUp,
  FileJson, Menu, X, Layers, Clipboard, Video,
} from "lucide-react";
import Footer from "../components/Footer";
import { analyzeText, analyzeUrl, analyzeUpload, analyzeTextBatch, analyzeReviewedText } from "../services/api";
import ExtractedTextReview from "../components/report/ExtractedTextReview.jsx";
import { textReviewState, textReviewError, withoutReviewCredential } from "../utils/textReview.js";
import { analysisUrlInput, MAX_ANALYSIS_URL_LENGTH } from "../utils/urlInput.js";
import { textInputState, analysisErrorMessage } from "../utils/analysisInput.js";
import { batchResultLabel } from "../utils/reportEvidence.js";
import { captureAnalysisScope, isAnalysisScopeCurrent, storeSessionReport, subscribeAnalysisReset } from "../services/privacyStorage.js";

const TABS = [
  { id: 0, label: "Texto", icon: FileText, desc: "Cole o texto da mensagem que você recebeu" },
  { id: 1, label: "Link", icon: Link2, desc: "Cole o link de uma notícia ou site duvidoso" },
  { id: 2, label: "Imagem", icon: Image, desc: "Envie uma foto ou print de tela" },
  { id: 3, label: "Áudio", icon: Mic, desc: "Envie um áudio de WhatsApp para checar" },
  { id: 4, label: "Vídeo", icon: Video, desc: "Quadros amostrados e áudio, quando disponível" },
];

const EXAMPLES = [
  {
    label: "Golpe do Resgate Pix",
    text: "URGENTE: Banco Central libera resgate de valores esquecidos do Pix acima de R$ 2.500 hoje. Pague a taxa de R$ 37 para receber imediatamente no site gov-pix-beneficios.site"
  },
  {
    label: "Boato sobre Saúde",
    text: "Médico de Harvard descobre que água com limão e bicarbonato quente elimina qualquer vírus em 24 horas e hospitais tentam esconder essa receita caseira milagrosa."
  },
  {
    label: "Mensagem sobre vacinação",
    text: "Ministério da Saúde inicia campanha nacional de vacinação contra a gripe em postos de saúde de todo o Brasil para grupos prioritários."
  }
];

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

function parseBatchText(raw) {
  return raw
    .split(/\n{2,}|---+|===+|mensagens?:/)
    .map((t) => t.trim())
    .filter((t) => t.length >= 10);
}

export default function Home() {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();

  const [tab, setTab] = useState(0);
  const [text, setText] = useState("");
  const textInput = textInputState(text);
  const [url, setUrl] = useState("");
  const urlInput = analysisUrlInput(url);
  const [imageFile, setImageFile] = useState(null);
  const [audioFile, setAudioFile] = useState(null);
  const [videoFile, setVideoFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState(0);
  const [error, setError] = useState("");
  const [pendingReview, setPendingReview] = useState(null);
  const [reviewBusy, setReviewBusy] = useState(false);
  const mounted = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const scopeCurrent = (scope) => mounted.current && isAnalysisScopeCurrent(scope);

  const [batchMode, setBatchMode] = useState(false);
  const [batchResults, setBatchResults] = useState(null);
  const [batchLoading, setBatchLoading] = useState(false);

  useEffect(() => subscribeAnalysisReset(() => {
    setText(""); setUrl(""); setImageFile(null); setAudioFile(null); setVideoFile(null);
    setBatchResults(null); setError(""); setLoading(false); setBatchLoading(false); setStage(0);
    setPendingReview(null); setReviewBusy(false);
  }), []);

  const canSubmit = () => {
    if (authLoading) return false;
    if (tab === 0) return textInput.valid;
    if (tab === 1) return urlInput.valid;
    if (tab === 2) return !!imageFile;
    if (tab === 3) return !!audioFile;
    if (tab === 4) return !!videoFile;
    return false;
  };

  const canBatchSubmit = () => {
    if (authLoading) return false;
    if (tab !== 0) return false;
    const msgs = parseBatchText(text);
    return msgs.length >= 2 && msgs.length <= 10 && msgs.every((message) => textInputState(message).valid);
  };

  const handleAnalyze = async () => {
    if (!canSubmit()) return;
    const scope = captureAnalysisScope();
    setError(""); setLoading(true); setStage(0);
    try {
      const selectedFile = tab === 2 ? imageFile : tab === 3 ? audioFile : tab === 4 ? videoFile : null;
      if (selectedFile && selectedFile.size > 25 * 1024 * 1024) throw new Error("Envie um arquivo de até 25 MB.");
      setStage(1);
      let result;
      let queryLabel = "";

      if (tab === 0) {
        result = await analyzeText(textInput.text);
        queryLabel = textInput.text;
      } else if (tab === 1) {
        result = await analyzeUrl(url);
        queryLabel = url;
      } else if (tab === 2) {
        result = await analyzeUpload(imageFile, { reviewText: true });
        queryLabel = imageFile?.name || "Foto enviada";
      } else if (tab === 3) {
        result = await analyzeUpload(audioFile, { reviewText: true });
        queryLabel = audioFile?.name || "Áudio enviado";
      } else if (tab === 4) {
        result = await analyzeUpload(videoFile, { reviewText: true });
        queryLabel = videoFile?.name || "Vídeo enviado";
      }

      if (!scopeCurrent(scope)) return;
      if (selectedFile && textReviewState(result) === "ready") {
        setPendingReview({ report: result, file: selectedFile, queryLabel, scope });
        return;
      }
      setStage(3); await sleep(400);
      if (!scopeCurrent(scope)) return;
      const report = { ...withoutReviewCredential(result), query_input: queryLabel };
      if (!storeSessionReport(report, queryLabel, scope)) throw new Error("report_storage_unavailable");
      navigate("/report");
    } catch (e) {
      if (!scopeCurrent(scope)) return;
      setError(analysisErrorMessage(e));
    } finally {
      if (scopeCurrent(scope)) { setLoading(false); setStage(0); }
    }
  };

  const handleReviewConfirm = async (reviewedText) => {
    if (!pendingReview || reviewBusy || !scopeCurrent(pendingReview.scope)) return;
    const { report, scope } = pendingReview;
    setError(""); setReviewBusy(true);
    try {
      const checked = await analyzeReviewedText(reviewedText, report.text_review_token);
      if (!scopeCurrent(scope)) return;
      if (!storeSessionReport(checked, checked.query_input || reviewedText, scope)) throw new Error("report_storage_unavailable");
      navigate("/report");
    } catch (err) {
      if (scopeCurrent(scope)) setError(textReviewError(err));
    } finally {
      if (scopeCurrent(scope)) setReviewBusy(false);
    }
  };

  const handleReviewSkip = () => {
    if (!pendingReview || reviewBusy || !scopeCurrent(pendingReview.scope)) return;
    const { report, queryLabel, scope } = pendingReview;
    if (storeSessionReport(withoutReviewCredential(report), queryLabel, scope)) navigate("/report");
    else setError("Não foi possível abrir os sinais da mídia. Sua conferência foi mantida.");
  };

  const handleBatchAnalyze = async () => {
    if (!canBatchSubmit()) return;
    const scope = captureAnalysisScope();
    const msgs = parseBatchText(text);
    setBatchLoading(true); setError(""); setBatchResults(null);
    try {
      const data = await analyzeTextBatch(msgs);
      if (!isAnalysisScopeCurrent(scope)) return;
      setBatchResults(data.results || []);
    } catch (e) {
      if (!isAnalysisScopeCurrent(scope)) return;
      setError(analysisErrorMessage(e));
    } finally {
      if (isAnalysisScopeCurrent(scope)) setBatchLoading(false);
    }
  };

  const VERDICT_COLORS = {
    Authentic: "#00FF87", False: "#FF3B5C", AI_Generated: "#00D4FF", Manipulated: "#FF3B5C",
    Out_Of_Context: "#FFB830", Suspicious: "#8AA2B4", Scam: "#FF3B5C",
  };

  const tabs = TABS;

  return (
    <div className="check-page relative min-h-screen bg-[#04080C] text-[#CDE8F0] pb-20">
      <div className="pointer-events-none fixed inset-0" style={{ backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)", backgroundSize: "48px 48px", opacity: .15 }}/>

      <div className="check-page-content relative z-10 max-w-3xl mx-auto px-4 sm:px-6 pt-20 sm:pt-28">

        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-md border border-[#00D4FF33] bg-[#00D4FF0D] text-[#00D4FF] font-mono text-[10px] font-bold uppercase tracking-widest mb-6">
            <Shield size={12} /> Proteção simples para toda a família
          </div>
          <h1 className="font-syne font-extrabold text-3xl sm:text-5xl text-[#CDE8F0] mb-4 leading-tight">
            Descubra se é <span className="text-[#00D4FF] underline decoration-[#00FF87] underline-offset-8">Verdade</span> ou <span className="text-[#FF3B5C]">Golpe</span>
          </h1>
          <p className="font-mono text-sm sm:text-base text-[#8AA2B4] max-w-xl mx-auto leading-relaxed">
            {user ? `Olá, ${user.name.split(" ")[0]}! ` : ""}Envie o conteúdo para consultar sinais de risco e fontes disponíveis. Quando faltarem evidências, o resultado será inconclusivo.
          </p>
        </div>

        {pendingReview ? <ExtractedTextReview report={pendingReview.report} file={pendingReview.file} busy={reviewBusy}
          error={error} onConfirm={handleReviewConfirm} onSkip={handleReviewSkip} /> : <div className="rounded-xl overflow-hidden shadow-2xl border border-[#132435] bg-[#0A1520] transition-all">

          <div className="check-type-options grid grid-cols-3 sm:grid-cols-5 border-b border-[#132435] bg-[#070F17]" role="group" aria-label="Tipo de conteúdo para checar">
            {tabs.map((t) => (
              <button
                key={t.id}
                aria-pressed={tab === t.id}
                onClick={() => { setTab(t.id); setError(""); setBatchResults(null); setBatchMode(false); }}
                className={`flex flex-col items-center justify-center gap-1.5 py-4 px-2 sm:px-4 text-center transition-all cursor-pointer ${
                  tab === t.id ? "bg-[#0F1E2E] text-[#00D4FF]" : "bg-[#070F17] text-[#5A7E94]"
                }`}
              >
                <t.icon size={tab === t.id ? 20 : 16} className="mb-1" />
                <span className="font-syne font-bold text-xs sm:text-sm">{t.label}</span>
              </button>
            ))}
          </div>

          <div className="check-description px-6 pt-5 pb-3 text-xs text-[#00FF87] font-mono font-bold flex items-center justify-between">
            <span className="flex items-center gap-2">
              <span className="inline-flex"><ArrowRight size={12} /></span> {tabs[tab].desc}
            </span>
            {tab === 0 && (
              <button
                onClick={() => { setBatchMode(!batchMode); setBatchResults(null); }}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-mono text-[10px] font-bold uppercase tracking-wider transition-all ${
                  batchMode
                    ? "bg-[#00D4FF] text-[#04080C]"
                    : "bg-[#132435] text-[#8AA2B4] hover:text-[#00D4FF]"
                }`}
              >
                <Layers size={12} /> Lote
              </button>
            )}
          </div>

          <div className="check-form-content p-6 sm:p-8 pt-2">

            {tab === 0 && (
              <div className="space-y-4">
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder={batchMode
                    ? "Cole várias mensagens separadas por linha dupla (Enter duplo):\n\nMensagem 1\n\nMensagem 2\n\nMensagem 3"
                    : "Cole aqui o texto da mensagem, boato ou notícia..."
                  }
                  rows={batchMode ? 10 : 5}
                  aria-describedby={batchMode ? undefined : "text-input-guidance"}
                  aria-invalid={!batchMode && textInput.length > 5000}
                  className="w-full font-mono text-sm sm:text-base leading-relaxed p-4 rounded-lg bg-[#04080C] border border-[#132435] text-[#CDE8F0] placeholder-[#3A6070] focus:border-[#00D4FF] focus:outline-none resize-none transition-all"
                />

                {!batchMode && (
                  <p id="text-input-guidance" className={`text-sm leading-relaxed ${textInput.length > 5000 ? "text-[#FF889D]" : "text-[#8AA2B4]"}`} aria-live="polite">
                    {textInput.length > 5000 ? textInput.message : `${textInput.length.toLocaleString("pt-BR")} de 5.000 caracteres · mínimo de 10. O texto não será cortado.`}
                  </p>
                )}

                {batchMode && (
                  <div className="flex items-center gap-2 text-[10px] font-mono text-[#5A7E94]">
                    <Clipboard size={12} />
                    {parseBatchText(text).length} de 10 mensagens detectadas
                    {parseBatchText(text).length > 10 && (
                      <span className="text-[#FF3B5C]">(máximo 10)</span>
                    )}
                  </div>
                )}

                <div className="flex flex-wrap items-center gap-2 pt-1">
                  <span className="text-xs text-[#5A7E94] font-mono">Testar exemplo:</span>
                  {EXAMPLES.map((ex, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setText(ex.text)}
                      className="text-xs px-3 py-1 rounded-md bg-[#132435] hover:bg-[#1A3A50] text-[#CDE8F0] border border-[#1A3A50] transition-colors cursor-pointer"
                    >
                      {ex.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {tab === 1 && (
              <div className="space-y-4">
                <label htmlFor="analysis-url" className="block text-sm text-[#CDE8F0]">Endereço da página</label>
                <div className="relative">
                  <Link2 size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#3A6070]" />
                  <input
                    id="analysis-url"
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    aria-describedby="analysis-url-count analysis-url-help analysis-url-error"
                    aria-invalid={Boolean(urlInput.error)}
                    placeholder="https://exemplo.com/noticia-para-verificar"
                    className="w-full font-mono text-sm sm:text-base p-4 pl-10 rounded-lg bg-[#04080C] border border-[#132435] text-[#CDE8F0] placeholder-[#3A6070] focus:border-[#00D4FF] focus:outline-none transition-all"
                  />
                </div>
                <p id="analysis-url-count" className="text-xs text-[#8AA2B4]">{urlInput.length} / {MAX_ANALYSIS_URL_LENGTH} caracteres, incluindo https:// quando necessário.</p>
                {urlInput.error && <p id="analysis-url-error" className="text-sm text-[#FFB830]" role="alert">{urlInput.error}</p>}
                <p id="analysis-url-help" className="text-xs text-[#8AA2B4] font-mono">
                  Analisamos o texto da página e sinais do endereço. Isso não comprova que o site é legítimo nem verifica a idade do domínio.
                </p>
              </div>
            )}

            {tab === 4 && <div className="space-y-4">
              <label htmlFor="video-upload" className="flex flex-col items-center border-2 border-dashed border-[#132435] rounded-lg p-8 cursor-pointer bg-[#04080C] text-center">
                <Video size={28} className="text-[#00D4FF] mb-3" />
                <span className="font-bold">Enviar vídeo</span>
                <input id="video-upload" type="file" accept="video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm" className="mt-4 max-w-full text-xs" onChange={e => setVideoFile(e.target.files?.[0] || null)} />
              </label>
              <p className="text-xs text-[#8AA2B4]">Até 25 MB e 2 minutos. Verifica quadros amostrados; não comprova identidade, voz ou sincronização labial.</p>
            </div>}

            {tab === 2 && (
              <div>
                <label htmlFor="image-upload" className="check-upload flex flex-col items-center justify-center border-2 border-dashed border-[#132435] hover:border-[#00D4FF] rounded-lg p-10 text-center cursor-pointer bg-[#04080C] transition-all">
                  <Upload size={28} className="text-[#00D4FF] mb-3" />
                  <span className="font-syne font-bold text-sm text-[#CDE8F0] mb-1">Clique para enviar a imagem</span>
                  <span className="text-xs text-[#5A7E94] font-mono">Formatos suportados: .jpg, .png, .webp, .gif</span>
                  <input id="image-upload" type="file" accept="image/*" className="mt-4 max-w-full text-xs" onChange={(e) => setImageFile(e.target.files[0] || null)} />
                </label>
                {imageFile && (
                  <div className="mt-3 p-3 rounded-lg bg-[#00D4FF10] border border-[#00D4FF30] text-xs text-[#00D4FF] flex items-center justify-between font-mono">
                    <span>Arquivo selecionado: <strong>{imageFile.name}</strong></span>
                    <button onClick={() => setImageFile(null)} className="text-red-400 hover:underline cursor-pointer">Remover</button>
                  </div>
                )}
              </div>
            )}

            {tab === 3 && (
              <div className="space-y-4">
                <label htmlFor="audio-upload" className="check-upload flex flex-col items-center border-2 border-dashed border-[#132435] hover:border-[#00D4FF] rounded-lg p-8 text-center cursor-pointer bg-[#04080C] transition-all">
                  <Mic size={28} className="text-[#00D4FF] mb-3 mx-auto" />
                  <div className="font-syne font-bold text-sm text-[#CDE8F0] mb-1">Clique para enviar o áudio do WhatsApp</div>
                  <div className="text-xs text-[#5A7E94] font-mono">Formatos suportados: .mp3, .ogg (WhatsApp), .m4a, .wav</div>
                  <input id="audio-upload" type="file" accept="audio/*,.mp3,.ogg,.wav,.m4a,.aac,.opus" onChange={(e) => setAudioFile(e.target.files[0] || null)} className="mt-4 max-w-full text-xs" />
                </label>

                {audioFile && (
                  <div className="p-4 rounded-lg bg-[#00FF8710] border border-[#00FF8730] text-sm text-[#00FF87] flex items-center justify-between font-mono">
                    <span>Áudio pronto para checagem: <strong>{audioFile.name}</strong></span>
                    <button onClick={() => setAudioFile(null)} className="text-red-400 hover:underline cursor-pointer">Remover</button>
                  </div>
                )}
              </div>
            )}

          </div>

          <div className="check-submit-area p-6 sm:p-8 bg-[#070F17] border-t border-[#132435] flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex flex-wrap items-center justify-center gap-3 text-xs font-mono text-[#5A7E94]">
              <span className="flex items-center gap-1 text-[#00D4FF]">
                <Shield size={16} aria-hidden="true" /> Fontes e sinais disponíveis
              </span>
              <span>•</span>
              <span className="text-[#00FF87]">Limites no relatório</span>
            </div>

            {batchMode ? (
              <button
                disabled={!canBatchSubmit() || batchLoading}
                onClick={handleBatchAnalyze}
                className="w-full sm:w-auto font-syne font-extrabold text-sm sm:text-base tracking-wider px-8 py-4 rounded-lg transition-all shadow-lg flex items-center justify-center gap-2 cursor-pointer"
                style={{
                  background: canBatchSubmit() && !batchLoading ? "linear-gradient(135deg,#00D4FF,#00FF87)" : "#132435",
                  color: canBatchSubmit() && !batchLoading ? "#04080C" : "#5A7E94",
                  cursor: canBatchSubmit() && !batchLoading ? "pointer" : "not-allowed",
                }}
              >
                <Layers size={16} />
                <span>{batchLoading ? "ANALISANDO LOTE..." : `VERIFICAR ${parseBatchText(text).length} MENSAGENS`}</span>
              </button>
            ) : (
              <button
                disabled={!canSubmit() || loading}
                onClick={handleAnalyze}
                className="w-full sm:w-auto font-syne font-extrabold text-sm sm:text-base tracking-wider px-8 py-4 rounded-lg transition-all shadow-lg flex items-center justify-center gap-2 cursor-pointer"
                style={{
                  background: canSubmit() && !loading ? "linear-gradient(135deg,#00D4FF,#00FF87)" : "#132435",
                  color: canSubmit() && !loading ? "#04080C" : "#5A7E94",
                  cursor: canSubmit() && !loading ? "pointer" : "not-allowed",
                }}
              >
                <Search size={16} />
                <span>{loading ? "ANALISANDO..." : "VERIFICAR AGORA"}</span>
              </button>
            )}
          </div>
        </div>}

        {(loading || batchLoading || reviewBusy) && (
          <p role="status" aria-live="polite" className="mt-4 text-base leading-relaxed text-[#9CC3D8] text-center">
            Algumas checagens de texto e link podem levar até quatro minutos. Aguarde sem enviar novamente.
          </p>
        )}

        {error && !pendingReview && (
          <div className="mt-6 p-4 rounded-lg bg-[#FF3B5C10] border border-[#FF3B5C30] text-[#FF3B5C] text-sm text-center font-mono flex items-center justify-center gap-2">
            <AlertTriangle size={14} /> <strong>Atenção:</strong> {error}
          </div>
        )}

        {batchResults && (
          <div className="mt-8 space-y-3">
            <div className="flex items-center gap-2 mb-4">
              <Layers size={16} className="text-[#00D4FF]" />
              <h3 className="font-syne font-bold text-lg text-[#CDE8F0]">Resultados do Lote</h3>
              <span className="font-mono text-[10px] text-[#8AA2B4]">({batchResults.length} mensagens)</span>
            </div>
            {batchResults.map((r, i) => {
              const color = VERDICT_COLORS[r.verdict] || "#8AA2B4";
              return (
                <button
                  type="button"
                  key={i}
                  className="w-full text-left rounded-lg border border-[#132435] bg-[#0A1520] p-4 hover:border-[#00D4FF]/50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#00D4FF] transition-colors cursor-pointer"
                  onClick={() => {
                    if (storeSessionReport(r, r.query_input || "")) navigate("/report");
                    else setError("Não foi possível abrir este relatório. Por favor, repita a checagem.");
                  }}
                >
                  <span className="flex items-start justify-between gap-3">
                    <span className="flex-1 min-w-0">
                      <span className="block font-mono text-xs text-[#CDE8F0] truncate">{r.query_input || `Mensagem ${i + 1}`}</span>
                      <span className="block font-mono text-[11px] text-[#8AA2B4] mt-1 line-clamp-2">{r.summary || r.plain_explanation || "—"}</span>
                    </span>
                    <span className="text-right max-w-[45%] break-words">
                      <span
                        className="font-mono text-[10px] font-bold uppercase tracking-wider"
                        style={{ color }}
                      >
                        {batchResultLabel(r)}
                      </span>
                      <span className="block font-mono text-xs mt-1" style={{ color }}>{r.analysis_status === "inconclusive" || r.score == null ? "Não determinado" : `${r.score}/100 · índice não calibrado`}</span>
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        )}

        <div className="mt-12 grid grid-cols-1 sm:grid-cols-3 gap-4 text-center">
          {[
            { n: "1", t: "Cole ou Envie", d: "Copie a mensagem recebida no WhatsApp e cole aqui com um toque." },
            { n: "2", t: "Consulta de Evidências", d: "Consultamos as fontes configuradas e mostramos quando elas não respondem." },
            { n: "3", t: "Resultado Fácil", d: "Veja os sinais e as limitações, ouça a explicação e confirme com a fonte original." },
          ].map(item => (
            <div key={item.n} className="p-5 rounded-lg bg-[#0A1520] border border-[#132435]">
              <div className="font-mono text-sm text-[#00D4FF] mb-2">{item.n}</div>
              <h4 className="font-syne font-bold text-sm text-[#CDE8F0] mb-1">{item.t}</h4>
              <p className="font-mono text-[11px] text-[#5A7E94] leading-relaxed">{item.d}</p>
            </div>
          ))}
        </div>

      </div>

      <Footer />
    </div>
  );
}
