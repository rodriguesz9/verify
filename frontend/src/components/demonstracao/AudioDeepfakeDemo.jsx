import { useEffect, useRef, useState } from "react";
import { AudioLines, FileAudio, Mic, Play, ShieldAlert, Square, Upload, Volume2 } from "lucide-react";
import { verifyAudioQuick } from "../../services/api";
import { transcriptionPresentation, visibleDetectorScore, publicCoveragePresentation, isTechnicalReportText } from "../../utils/reportEvidence";
import { createMediaLifecycle } from "../../services/mediaLifecycle.js";

const SAMPLES = {
  cloned: {
    label: "Fala sintética · exemplo de pedido financeiro",
    filename: "demo-pedido-sintetico.wav",
    audioSrc: "/audio/demo-pedido-sintetico.wav",
    text: "Mãe, caí na rua e perdi meu celular. Faz um Pix urgente para o guincho, por favor.",
  },
  authentic: {
    label: "Fala sintética · exemplo de conversa cotidiana",
    filename: "demo-conversa-sintetica.wav",
    audioSrc: "/audio/demo-conversa-sintetica.wav",
    text: "Oi vó, tudo bem? Estou saindo da aula agora. Te vejo mais tarde para o café.",
  }
};

export default function AudioDeepfakeDemo() {
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [audioFile, setAudioFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [previewing, setPreviewing] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [loadingSample, setLoadingSample] = useState(false);
  const [requestingMicrophone, setRequestingMicrophone] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioPlayerRef = useRef(null);
  const microphoneRequestRef = useRef(null);
  const lifecycleRef = useRef(null);
  if (!lifecycleRef.current) lifecycleRef.current = createMediaLifecycle();
  const lifecycle = lifecycleRef.current;
  const inputBusy = analyzing || loadingSample || requestingMicrophone || isRecording;

  useEffect(() => {
    lifecycle.activate();
    return () => {
      lifecycle.dispose();
      const recorder = mediaRecorderRef.current;
      if (recorder) {
        recorder.onstop = null;
        recorder.ondataavailable = null;
        try { if (recorder.state !== "inactive") recorder.stop(); } catch { /* Already stopped. */ }
      }
      mediaRecorderRef.current = null;
      mediaStreamRef.current = null;
      audioChunksRef.current = [];
      audioPlayerRef.current?.pause();
    };
  }, [lifecycle]);

  useEffect(() => () => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
    }
    if (previewUrl && previewUrl.startsWith("blob:")) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const clearPreview = () => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
    }
    if (previewUrl && previewUrl.startsWith("blob:")) URL.revokeObjectURL(previewUrl);
    setPreviewUrl("");
  };

  const selectSample = async (scenario) => {
    if (inputBusy) return;
    const scope = lifecycle.capture();
    if (!lifecycle.isCurrent(scope)) return;
    setLoadingSample(true);
    setAudioFile(null);
    clearPreview();
    setError(""); setResult(null); setPreviewing(null); setSelectedScenario(scenario);
    try {
      const resp = await fetch(SAMPLES[scenario].audioSrc);
      if (!resp.ok) throw new Error("Amostra indisponível");
      const blob = await resp.blob();
      if (!lifecycle.isCurrent(scope)) return;
      const file = new File([blob], SAMPLES[scenario].filename, { type: "audio/wav" });
      setAudioFile(file);
      setPreviewUrl(SAMPLES[scenario].audioSrc);
    } catch {
      if (lifecycle.isCurrent(scope)) setError("Não foi possível carregar a amostra de fala.");
    } finally {
      if (lifecycle.isCurrent(scope)) setLoadingSample(false);
    }
  };

  const playSampleAudio = (scenario) => {
    const scope = lifecycle.capture();
    if (!lifecycle.isCurrent(scope)) return;
    if (previewing === scenario) {
      audioPlayerRef.current?.pause();
      setPreviewing(null);
      return;
    }
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
    }
    const audio = new Audio(SAMPLES[scenario].audioSrc);
    audioPlayerRef.current = audio;
    audio.onended = lifecycle.guard(scope, () => setPreviewing(null));
    audio.onerror = lifecycle.guard(scope, () => {
      setPreviewing(null);
      setError("Erro ao reproduzir o áudio.");
    });
    audio.play().then(lifecycle.guard(scope, () => setPreviewing(scenario))).catch(lifecycle.guard(scope, () => setPreviewing(null)));
  };

  const handleFileUpload = (event) => {
    if (inputBusy || !lifecycle.isCurrent(lifecycle.capture())) return;
    const file = event.target.files?.[0];
    if (!file) return;
    window.speechSynthesis?.cancel(); clearPreview();
    setPreviewUrl(URL.createObjectURL(file));
    setError(""); setResult(null); setPreviewing(null); setSelectedScenario("custom"); setAudioFile(file);
  };

  const startRecording = async () => {
    if (inputBusy || microphoneRequestRef.current !== null) return;
    const scope = lifecycle.capture();
    if (!lifecycle.isCurrent(scope)) return;
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError("Gravação não é compatível com este navegador. Envie um arquivo de áudio.");
      return;
    }
    microphoneRequestRef.current = scope;
    setRequestingMicrophone(true);
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!lifecycle.acceptStream(stream, scope)) return;
      mediaStreamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];
      recorder.ondataavailable = lifecycle.guard(scope, event => { if (event.data.size > 0) audioChunksRef.current.push(event.data); });
      recorder.onstop = lifecycle.guard(scope, () => {
        const mimeType = recorder.mimeType || "audio/webm";
        const extension = mimeType.includes("ogg") ? "ogg" : "webm";
        const blob = new Blob(audioChunksRef.current, { type: mimeType });
        const file = new File([blob], `gravacao_verify.${extension}`, { type: mimeType });
        clearPreview(); setPreviewUrl(URL.createObjectURL(file));
        setAudioFile(file); setSelectedScenario("custom");
        lifecycle.releaseStream(stream); mediaStreamRef.current = null;
      });
      recorder.start(); setIsRecording(true); setError(""); setResult(null);
    } catch {
      lifecycle.releaseStream(stream);
      if (lifecycle.isCurrent(scope)) setError("Permissão de microfone não concedida pelo navegador.");
    } finally {
      if (microphoneRequestRef.current === scope) microphoneRequestRef.current = null;
      if (lifecycle.isCurrent(scope)) setRequestingMicrophone(false);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop(); setIsRecording(false);
    }
  };

  const handleAnalyze = async () => {
    if (inputBusy) return;
    const scope = lifecycle.capture();
    if (!lifecycle.isCurrent(scope)) return;
    if (!audioFile) return setError("Selecione uma amostra, envie um arquivo ou grave sua voz.");
    setAnalyzing(true); setError(""); setResult(null);
    try {
      const data = await verifyAudioQuick(audioFile);
      if (lifecycle.isCurrent(scope)) setResult(data);
    } catch {
      if (lifecycle.isCurrent(scope)) setError("Não foi possível analisar este arquivo agora. Tente um áudio menor ou outro formato.");
    } finally {
      if (lifecycle.isCurrent(scope)) setAnalyzing(false);
    }
  };

  const isSynthetic = result?.verdict === "indicios_sintetica";
  const inconclusive = result?.analysis_status !== "partial" || !isSynthetic;
  const transcriptionState = transcriptionPresentation(result || {});
  const publicCoverage = publicCoveragePresentation({...result, content_type: "audio", analysis_status: inconclusive ? "inconclusive" : "partial"});
  const publicIndicators = Array.isArray(result?.indicators) ? result.indicators.filter((item) => typeof item === "string" && !isTechnicalReportText(item)) : [];
  return (
    <section className="mx-auto max-w-4xl rounded-3xl border border-[#132435] bg-[#0A1520] p-5 shadow-2xl sm:p-8">
      <header className="mb-8 text-center">
        <span className="mb-2 block font-mono text-[10px] font-bold uppercase tracking-[.2em] text-[#00D4FF]">Recurso 1 · demonstração de uso</span>
        <h2 className="font-syne text-2xl font-black tracking-tight text-[#CDE8F0] sm:text-4xl">Comparação de <span className="text-[#00FF87]">amostras de fala</span></h2>
        <p className="mx-auto mt-3 max-w-2xl font-mono text-xs leading-6 text-[#8BAAC0] sm:text-sm">As duas vozes são sintéticas, geradas para esta demonstração em português. Compare o conteúdo, não uma suposta voz verdadeira ou clonada. Confirme pedidos de Pix por outro canal.</p>
      </header>

      <div className="mb-5 grid gap-4 md:grid-cols-2">
        {Object.entries(SAMPLES).map(([scenario, sample]) => {
          const selected = selectedScenario === scenario;
          const danger = scenario === "cloned";
          return <article key={scenario} className={`rounded-2xl border p-5 transition-all ${selected ? (danger ? "border-[#FF3B5C] bg-[#FF3B5C]/10" : "border-[#00FF87] bg-[#00FF87]/10") : "border-[#132435] bg-[#060D14]"}`}>
            <div className="flex items-start justify-between gap-3"><div><span className={`font-mono text-[10px] font-bold uppercase tracking-widest ${danger ? "text-[#FF8195]" : "text-[#00FF87]"}`}>{sample.label}</span><h3 className="mt-2 font-syne text-base font-bold text-[#CDE8F0]">{danger ? "Pedido de Pix urgente" : "Conversa cotidiana"}</h3></div><AudioLines size={22} className={danger ? "text-[#FF8195]" : "text-[#00FF87]"} /></div>
            <p className="mt-3 min-h-12 font-mono text-xs leading-5 text-[#8BAAC0]">“{sample.text}”</p>
            <div className="mt-5 flex flex-wrap gap-2"><button type="button" disabled={inputBusy} onClick={() => selectSample(scenario)} className={`rounded-lg px-3 py-2 font-mono text-[10px] font-bold uppercase tracking-wider disabled:cursor-not-allowed disabled:opacity-50 ${danger ? "bg-[#FF3B5C] text-white" : "bg-[#00FF87] text-[#04080C]"}`}>Usar esta voz</button><button type="button" onClick={() => playSampleAudio(scenario)} className="inline-flex items-center gap-2 rounded-lg border border-[#284258] px-3 py-2 font-mono text-[10px] font-bold uppercase tracking-wider text-[#CDE8F0] hover:border-[#00D4FF] hover:text-[#00D4FF]">{previewing === scenario ? <Square size={12} /> : <Play size={12} />}{previewing === scenario ? "Pausar" : "Ouvir exemplo"}</button></div>
          </article>;
        })}
      </div>

      <div className="mb-6 rounded-2xl border border-[#132435] bg-[#060D14] p-4">
        <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
          <label className={`inline-flex items-center gap-2 rounded-xl border border-[#00D4FF]/30 bg-[#00D4FF]/10 px-4 py-3 font-mono text-xs font-bold text-[#00D4FF] ${inputBusy ? "cursor-not-allowed opacity-50" : "cursor-pointer hover:bg-[#00D4FF]/20"}`}><Upload size={15} /> Enviar áudio<input type="file" disabled={inputBusy} accept="audio/*,.mp3,.ogg,.wav,.m4a,.aac,.opus,.webm" onChange={handleFileUpload} className="hidden" /></label>
          {!isRecording ? <button type="button" disabled={inputBusy} onClick={startRecording} className="inline-flex items-center gap-2 rounded-xl border border-[#FFB800]/30 bg-[#FFB800]/10 px-4 py-3 font-mono text-xs font-bold text-[#FFCB55] hover:bg-[#FFB800]/20 disabled:cursor-not-allowed disabled:opacity-50"><Mic size={15} /> Gravar minha voz</button> : <button type="button" onClick={stopRecording} className="inline-flex animate-pulse items-center gap-2 rounded-xl bg-[#FF3B5C] px-4 py-3 font-mono text-xs font-bold text-white"><Square size={15} /> Parar gravação</button>}
        </div>
        {audioFile && <div className="mt-4 min-w-0 rounded-xl border border-[#00FF87]/20 bg-[#00FF87]/5 p-3"><p className="flex min-w-0 items-center justify-center gap-2 text-sm text-[#00FF87]"><FileAudio size={14} className="shrink-0" /> Pronto: <b className="min-w-0 break-all">{audioFile.name}</b></p>{previewUrl && <audio className="mt-3 w-full" controls src={previewUrl}>Seu navegador não suporta áudio.</audio>}</div>}
      </div>

      {error && <p role="alert" className="mb-5 rounded-xl border border-[#FF3B5C]/40 bg-[#FF3B5C]/10 p-3 text-center font-mono text-xs text-[#FFB2BF]">{error}</p>}

      <button type="button" disabled={inputBusy || !audioFile} onClick={handleAnalyze} className="flex w-full items-center justify-center gap-3 rounded-2xl bg-gradient-to-r from-[#00D4FF] via-[#00FF87] to-[#00D4FF] px-6 py-5 font-syne text-sm font-black uppercase tracking-wider text-[#04080C] shadow-[0_10px_35px_rgba(0,212,255,.25)] transition-transform enabled:hover:scale-[1.01] disabled:cursor-not-allowed disabled:bg-[#132435] disabled:text-[#5A7E94] sm:text-base"><ShieldAlert size={19} />{analyzing ? "Analisando arquivo…" : loadingSample ? "Carregando amostra…" : "Analisar áudio"}</button>

      {result && <section className={`mt-7 rounded-3xl border p-5 sm:p-7 ${inconclusive ? "border-[#FFCB55] bg-[#FFCB55]/10" : isSynthetic ? "border-[#FF3B5C] bg-[#FF3B5C]/10" : "border-[#00FF87] bg-[#00FF87]/10"}`} aria-live="polite">
        {result.isDemo && <p className="mb-5 rounded-lg border border-[#FFB800]/30 bg-[#FFB800]/10 p-3 text-center font-mono text-[10px] leading-5 text-[#FFDB85]">Resultado educativo da comparação. Para uma análise forense real, envie ou grave um áudio de verdade.</p>}
        <div className="border-b border-white/10 pb-5"><h3 className="font-syne text-2xl font-black text-[#FFCB55]">{inconclusive ? "Origem da voz inconclusiva" : "Indícios de fala sintética"}</h3></div>
        <p className="mt-3 text-sm text-[#8BAAC0]">Resultado acústico não comprova identidade nem falsidade da fala. Detectores podem errar.</p>
        <p className="mt-3 text-sm leading-6 text-[#A7BFCD]">{publicCoverage.detail}</p>
        <p className="mt-5 font-syne text-base font-bold leading-relaxed text-[#CDE8F0]">{transcriptionState.notice ? "A leitura da fala ainda não fornece texto para conferência. O resultado acústico é separado da transcrição." : isTechnicalReportText(result.short_explanation) ? "Confira as observações e a mensagem transcrita abaixo. Confirme pedidos de dinheiro por um canal que você já conhece." : result.short_explanation}</p>
        {transcriptionState.notice && <div role="status" aria-live="polite" aria-atomic="true" className="mt-4 rounded-xl border border-[#00D4FF]/40 bg-[#070F17] p-4">
          <h4 className="text-base font-bold text-[#CDE8F0]">{transcriptionState.message}</h4>
          <p className="mt-2 text-sm leading-6 text-[#A7BFCD]">{transcriptionState.detail}</p>
        </div>}
        {transcriptionState.text && <p className="mt-4 text-sm text-[#CDE8F0]">Transcrição: {transcriptionState.text}</p>}
        {publicIndicators.length > 0 && <ul className="mt-5 space-y-3">{publicIndicators.map((indicator, index) => <li key={index} className="flex min-w-0 gap-3 text-sm leading-6 text-[#CDE8F0]"><span aria-hidden="true" className="shrink-0 text-[#FFCB55]">•</span><span className="min-w-0 break-words">{indicator}</span></li>)}</ul>}
        {result.provider_coverage && <details className="mt-5 min-w-0 rounded-xl border border-[#284258] p-4">
          <summary className="cursor-pointer text-sm font-bold text-[#CDE8F0]">Detalhes técnicos da análise de áudio</summary>
          <p className="mt-3 text-sm leading-6 text-[#A7BFCD]">Pontuações dos serviços não são porcentagens de verdade ou de precisão. Tempo informado: {result.tempo_processamento_ms ?? "não disponível"} ms.</p>
          <ul className="mt-3 space-y-2 break-words text-sm leading-6 text-[#A7BFCD]">{Object.entries(result.provider_coverage).filter(([, layer]) => layer && typeof layer === "object").map(([name, layer]) => <li key={name}>{transcriptionState.notice && (name === "transcription" || layer.decision_role === "transcription_only") ? `${name}: ${transcriptionState.coverageLabel}` : `${name}: ${layer.status === "success" ? "respondeu" : "indisponível"}`}{visibleDetectorScore(layer) !== null ? ` · sinal ${(visibleDetectorScore(layer) * 100).toFixed(1)}% (não calibrado)` : ""}</li>)}</ul>
        </details>}
      </section>}
      <p className="mt-5 flex items-start gap-2 font-mono text-[10px] leading-5 text-[#5A7E94]"><Volume2 size={13} className="mt-1 shrink-0" />Amostras sintéticas educativas geradas por eSpeak NG. Não representam uma pessoa real nem um teste de clonagem. A verificação não substitui confirmação por outro canal.</p>
    </section>
  );
}
