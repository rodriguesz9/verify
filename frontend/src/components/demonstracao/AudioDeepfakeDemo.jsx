import { useEffect, useRef, useState } from "react";
import { AudioLines, FileAudio, Mic, Play, ShieldAlert, Square, Upload, Volume2 } from "lucide-react";
import { verifyAudioQuick } from "../../services/api";

const SAMPLES = {
  cloned: {
    label: "Amostra de pedido financeiro (origem não auditada)",
    filename: "voz_golpe_clonado.mp3",
    audioSrc: "/audio/voz_golpe_clonado.mp3",
    text: "Mãe, caí na rua e perdi meu celular. Faz um Pix urgente para o guincho, por favor.",
  },
  authentic: {
    label: "Amostra de conversa cotidiana (origem não auditada)",
    filename: "voz_humana_real.mp3",
    audioSrc: "/audio/voz_humana_real.mp3",
    text: "Oi vó, tudo bem? Estou saindo da aula agora. Te vejo mais tarde para o café.",
  }
};

export default function AudioDeepfakeDemo() {
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [audioFile, setAudioFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [previewing, setPreviewing] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioPlayerRef = useRef(null);

  useEffect(() => () => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
    }
    mediaStreamRef.current?.getTracks().forEach(track => track.stop());
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
    clearPreview();
    setError(""); setResult(null); setPreviewing(null); setSelectedScenario(scenario);
    try {
      const resp = await fetch(SAMPLES[scenario].audioSrc);
      if (!resp.ok) throw new Error("Amostra indisponível");
      const blob = await resp.blob();
      const file = new File([blob], SAMPLES[scenario].filename, { type: "audio/mpeg" });
      setAudioFile(file);
      setPreviewUrl(SAMPLES[scenario].audioSrc);
    } catch {
      setError("Não foi possível carregar o arquivo de áudio real.");
    }
  };

  const playSampleAudio = (scenario) => {
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
    audio.onended = () => setPreviewing(null);
    audio.onerror = () => {
      setPreviewing(null);
      setError("Erro ao reproduzir o áudio.");
    };
    audio.play().then(() => setPreviewing(scenario)).catch(() => setPreviewing(null));
  };

  const handleFileUpload = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    window.speechSynthesis?.cancel(); clearPreview();
    setPreviewUrl(URL.createObjectURL(file));
    setError(""); setResult(null); setPreviewing(null); setSelectedScenario("custom"); setAudioFile(file);
  };

  const startRecording = async () => {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError("Gravação não é compatível com este navegador. Envie um arquivo de áudio.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];
      recorder.ondataavailable = event => { if (event.data.size > 0) audioChunksRef.current.push(event.data); };
      recorder.onstop = () => {
        const mimeType = recorder.mimeType || "audio/webm";
        const extension = mimeType.includes("ogg") ? "ogg" : "webm";
        const blob = new Blob(audioChunksRef.current, { type: mimeType });
        const file = new File([blob], `gravacao_verify.${extension}`, { type: mimeType });
        clearPreview(); setPreviewUrl(URL.createObjectURL(file));
        setAudioFile(file); setSelectedScenario("custom");
        stream.getTracks().forEach(track => track.stop()); mediaStreamRef.current = null;
      };
      recorder.start(); setIsRecording(true); setError(""); setResult(null);
    } catch {
      setError("Permissão de microfone não concedida pelo navegador.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop(); setIsRecording(false);
    }
  };

  const handleAnalyze = async () => {
    if (!audioFile) return setError("Selecione uma amostra, envie um arquivo ou grave sua voz.");
    setAnalyzing(true); setError(""); setResult(null);
    try {
      const data = await verifyAudioQuick(audioFile);
      setResult(data);
    } catch {
      setError("Não foi possível analisar este arquivo agora. Tente um áudio menor ou outro formato.");
    } finally {
      setAnalyzing(false);
    }
  };

  const isSynthetic = result?.verdict === "indicios_sintetica";
  const inconclusive = result?.analysis_status === "inconclusive";
  return (
    <section className="mx-auto max-w-4xl rounded-3xl border border-[#132435] bg-[#0A1520] p-5 shadow-2xl sm:p-8">
      <header className="mb-8 text-center">
        <span className="mb-2 block font-mono text-[10px] font-bold uppercase tracking-[.2em] text-[#00D4FF]">Recurso 1 · demonstração de uso</span>
        <h2 className="font-syne text-2xl font-black tracking-tight text-[#CDE8F0] sm:text-4xl">Comparação de <span className="text-[#00FF87]">amostras de fala</span></h2>
        <p className="mx-auto mt-3 max-w-2xl font-mono text-xs leading-6 text-[#8BAAC0] sm:text-sm">Compare duas amostras educativas de fala. A transcrição ajuda a reconhecer pedidos suspeitos, mas não prova se a voz foi clonada. Confirme pedidos de Pix por outro canal.</p>
      </header>

      <div className="mb-5 grid gap-4 md:grid-cols-2">
        {Object.entries(SAMPLES).map(([scenario, sample]) => {
          const selected = selectedScenario === scenario;
          const danger = scenario === "cloned";
          return <article key={scenario} className={`rounded-2xl border p-5 transition-all ${selected ? (danger ? "border-[#FF3B5C] bg-[#FF3B5C]/10" : "border-[#00FF87] bg-[#00FF87]/10") : "border-[#132435] bg-[#060D14]"}`}>
            <div className="flex items-start justify-between gap-3"><div><span className={`font-mono text-[10px] font-bold uppercase tracking-widest ${danger ? "text-[#FF8195]" : "text-[#00FF87]"}`}>{sample.label}</span><h3 className="mt-2 font-syne text-base font-bold text-[#CDE8F0]">{danger ? "Pedido de Pix urgente" : "Conversa cotidiana"}</h3></div><AudioLines size={22} className={danger ? "text-[#FF8195]" : "text-[#00FF87]"} /></div>
            <p className="mt-3 min-h-12 font-mono text-xs leading-5 text-[#8BAAC0]">“{sample.text}”</p>
            <div className="mt-5 flex flex-wrap gap-2"><button type="button" onClick={() => selectSample(scenario)} className={`rounded-lg px-3 py-2 font-mono text-[10px] font-bold uppercase tracking-wider ${danger ? "bg-[#FF3B5C] text-white" : "bg-[#00FF87] text-[#04080C]"}`}>Usar esta voz</button><button type="button" onClick={() => playSampleAudio(scenario)} className="inline-flex items-center gap-2 rounded-lg border border-[#284258] px-3 py-2 font-mono text-[10px] font-bold uppercase tracking-wider text-[#CDE8F0] hover:border-[#00D4FF] hover:text-[#00D4FF]">{previewing === scenario ? <Square size={12} /> : <Play size={12} />}{previewing === scenario ? "Pausar" : "Ouvir gravação real"}</button></div>
          </article>;
        })}
      </div>

      <div className="mb-6 rounded-2xl border border-[#132435] bg-[#060D14] p-4">
        <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-[#00D4FF]/30 bg-[#00D4FF]/10 px-4 py-3 font-mono text-xs font-bold text-[#00D4FF] hover:bg-[#00D4FF]/20"><Upload size={15} /> Enviar áudio<input type="file" accept="audio/*,.mp3,.ogg,.wav,.m4a,.aac,.opus,.webm" onChange={handleFileUpload} className="hidden" /></label>
          {!isRecording ? <button type="button" onClick={startRecording} className="inline-flex items-center gap-2 rounded-xl border border-[#FFB800]/30 bg-[#FFB800]/10 px-4 py-3 font-mono text-xs font-bold text-[#FFCB55] hover:bg-[#FFB800]/20"><Mic size={15} /> Gravar minha voz</button> : <button type="button" onClick={stopRecording} className="inline-flex animate-pulse items-center gap-2 rounded-xl bg-[#FF3B5C] px-4 py-3 font-mono text-xs font-bold text-white"><Square size={15} /> Parar gravação</button>}
        </div>
        {audioFile && <div className="mt-4 rounded-xl border border-[#00FF87]/20 bg-[#00FF87]/5 p-3"><p className="flex items-center justify-center gap-2 font-mono text-xs text-[#00FF87]"><FileAudio size={14} /> Pronto: <b>{audioFile.name}</b></p>{previewUrl && <audio className="mt-3 w-full" controls src={previewUrl}>Seu navegador não suporta áudio.</audio>}</div>}
      </div>

      {error && <p role="alert" className="mb-5 rounded-xl border border-[#FF3B5C]/40 bg-[#FF3B5C]/10 p-3 text-center font-mono text-xs text-[#FFB2BF]">{error}</p>}

      <button type="button" disabled={analyzing || !audioFile} onClick={handleAnalyze} className="flex w-full items-center justify-center gap-3 rounded-2xl bg-gradient-to-r from-[#00D4FF] via-[#00FF87] to-[#00D4FF] px-6 py-5 font-syne text-sm font-black uppercase tracking-wider text-[#04080C] shadow-[0_10px_35px_rgba(0,212,255,.25)] transition-transform enabled:hover:scale-[1.01] disabled:cursor-not-allowed disabled:bg-[#132435] disabled:text-[#5A7E94] sm:text-base"><ShieldAlert size={19} />{analyzing ? "Analisando arquivo…" : "Analisar áudio"}</button>

      {result && <section className={`mt-7 rounded-3xl border p-5 sm:p-7 ${inconclusive ? "border-[#FFCB55] bg-[#FFCB55]/10" : isSynthetic ? "border-[#FF3B5C] bg-[#FF3B5C]/10" : "border-[#00FF87] bg-[#00FF87]/10"}`} aria-live="polite">
        {result.isDemo && <p className="mb-5 rounded-lg border border-[#FFB800]/30 bg-[#FFB800]/10 p-3 text-center font-mono text-[10px] leading-5 text-[#FFDB85]">Resultado educativo da comparação. Para uma análise forense real, envie ou grave um áudio de verdade.</p>}
        <div className="border-b border-white/10 pb-5"><span className="font-mono text-[10px] text-[#8BAAC0]">Processamento da transcrição: {result.tempo_processamento_ms ?? 0} ms</span><h3 className="mt-2 font-syne text-2xl font-black text-[#FFCB55]">{inconclusive ? "Origem da voz inconclusiva" : "Indícios de fala sintética"}</h3></div>
        <p className="mt-3 text-sm text-[#8BAAC0]">Resultado acústico não comprova identidade nem falsidade da fala. Detectores podem errar.</p>
        {result.provider_coverage && <ul className="mt-3 text-xs text-[#8BAAC0] space-y-2">{Object.entries(result.provider_coverage).map(([name, layer]) => <li key={name}>{name}: {layer.status === "success" ? "respondeu" : "indisponível"}{typeof layer.ai_score === "number" ? ` · sinal ${(layer.ai_score * 100).toFixed(1)}% (não calibrado)` : ""}</li>)}</ul>}
        <p className="mt-5 font-syne text-base font-bold leading-relaxed text-[#CDE8F0]">{result.short_explanation}</p>
        {result.transcription && <p className="mt-4 text-sm text-[#CDE8F0]">Transcrição: {result.transcription}</p>}
        {result.indicators?.length > 0 && <ul className="mt-5 space-y-3">{result.indicators.map((indicator, index) => <li key={index} className="flex gap-3 font-mono text-xs leading-5 text-[#CDE8F0]"><span className={isSynthetic ? "text-[#FF8195]" : "text-[#00FF87]"}>{isSynthetic ? "!" : "✓"}</span>{indicator}</li>)}</ul>}
      </section>}
      <p className="mt-5 flex items-start gap-2 font-mono text-[10px] leading-5 text-[#5A7E94]"><Volume2 size={13} className="mt-1 shrink-0" />A prévia reproduz os arquivos de demonstração, cuja origem não foi certificada. A verificação depende das fontes configuradas no servidor e não substitui confirmação com a pessoa por outro canal.</p>
    </section>
  );
}
