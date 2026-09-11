import { useEffect, useRef, useState } from "react";
import { AudioLines, FileAudio, Mic, Play, ShieldAlert, Square, Upload, Volume2 } from "lucide-react";
import { verifyAudioQuick } from "../../services/api";

const SAMPLES = {
  cloned: {
    label: "Amostra de golpe",
    filename: "amostra_golpe_de_pix.wav",
    text: "Mãe, caí na rua e perdi meu celular. Faz um Pix urgente para o guincho, por favor.",
    result: {
      verdict: "sintetica", score_percent: 96, tempo_processamento_ms: 380,
      short_explanation: "Esta é uma amostra educativa que combina pedido urgente de Pix e sinais típicos de voz sintetizada.",
      indicators: [
        "Pedido financeiro urgente usando vínculo familiar",
        "Ritmo muito regular, usado aqui para representar síntese de voz",
        "Ausência de uma confirmação por outro canal"
      ]
    }
  },
  authentic: {
    label: "Amostra de conversa",
    filename: "amostra_conversa_cotidiana.wav",
    text: "Oi vó, tudo bem? Estou saindo da aula agora. Te vejo mais tarde para o café.",
    result: {
      verdict: "autentica", score_percent: 89, tempo_processamento_ms: 360,
      short_explanation: "Esta é uma amostra educativa de conversa cotidiana, sem pedido financeiro nem sinal de urgência.",
      indicators: [
        "Tom de conversa cotidiana, sem pressão emocional",
        "Não há pedido de senha, código ou transferência",
        "Confirmação por outro canal continua sendo recomendada"
      ]
    }
  }
};

function createDemoAudioFile(name) {
  // A valid WAV keeps sample selection compatible with uploads. Audible preview
  // uses SpeechSynthesis below, so a voice is never faked with a beep.
  const sampleRate = 16000;
  const durationSeconds = 2;
  const samples = sampleRate * durationSeconds;
  const buffer = new ArrayBuffer(44 + samples * 2);
  const view = new DataView(buffer);
  const write = (offset, value) => [...value].forEach((character, index) => view.setUint8(offset + index, character.charCodeAt(0)));
  write(0, "RIFF"); view.setUint32(4, 36 + samples * 2, true); write(8, "WAVE"); write(12, "fmt ");
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true); write(36, "data"); view.setUint32(40, samples * 2, true);
  for (let index = 0; index < samples; index += 1) {
    const time = index / sampleRate;
    const envelope = Math.min(1, time * 10, (durationSeconds - time) * 10);
    const wave = Math.sin(2 * Math.PI * 145 * time) + 0.45 * Math.sin(2 * Math.PI * 530 * time) + 0.2 * Math.sin(2 * Math.PI * 1550 * time);
    view.setInt16(44 + index * 2, Math.max(-32767, Math.min(32767, wave * envelope * 4800)), true);
  }
  return new File([buffer], name, { type: "audio/wav" });
}

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

  useEffect(() => () => {
    window.speechSynthesis?.cancel();
    mediaStreamRef.current?.getTracks().forEach(track => track.stop());
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const clearPreview = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl("");
  };

  const selectSample = (scenario) => {
    window.speechSynthesis?.cancel();
    clearPreview();
    setError(""); setResult(null); setPreviewing(null); setSelectedScenario(scenario);
    setAudioFile(createDemoAudioFile(SAMPLES[scenario].filename));
  };

  const speakSample = (scenario) => {
    const synth = window.speechSynthesis;
    if (!synth) {
      setError("Este navegador não oferece prévia falada. Você ainda pode enviar ou gravar um áudio.");
      return;
    }
    if (previewing === scenario) {
      synth.cancel(); setPreviewing(null); return;
    }
    synth.cancel();
    const utterance = new SpeechSynthesisUtterance(SAMPLES[scenario].text);
    const voices = synth.getVoices();
    utterance.voice = voices.find(voice => voice.lang.toLowerCase().startsWith("pt-br")) || voices.find(voice => voice.lang.toLowerCase().startsWith("pt")) || null;
    utterance.lang = "pt-BR";
    utterance.rate = scenario === "cloned" ? 1.12 : 0.95;
    utterance.pitch = scenario === "cloned" ? 1.25 : 1;
    utterance.onend = () => setPreviewing(current => current === scenario ? null : current);
    utterance.onerror = () => setPreviewing(null);
    setPreviewing(scenario); synth.speak(utterance);
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
      if (selectedScenario === "cloned" || selectedScenario === "authentic") {
        await new Promise(resolve => window.setTimeout(resolve, 700));
        setResult({ ...SAMPLES[selectedScenario].result, isDemo: true });
      } else {
        setResult({ ...(await verifyAudioQuick(audioFile)), isDemo: false });
      }
    } catch {
      setError("Não foi possível analisar este arquivo agora. Tente um áudio menor ou outro formato.");
    } finally {
      setAnalyzing(false);
    }
  };

  const isSynthetic = result?.verdict === "sintetica";
  return (
    <section className="mx-auto max-w-4xl rounded-3xl border border-[#132435] bg-[#0A1520] p-5 shadow-2xl sm:p-8">
      <header className="mb-8 text-center">
        <span className="mb-2 block font-mono text-[10px] font-bold uppercase tracking-[.2em] text-[#00D4FF]">Recurso 1 · demonstração de uso</span>
        <h2 className="font-syne text-2xl font-black tracking-tight text-[#CDE8F0] sm:text-4xl">Detecção de voz clonada <span className="text-[#FF8195]">e golpes de urgência</span></h2>
        <p className="mx-auto mt-3 max-w-2xl font-mono text-xs leading-6 text-[#8BAAC0] sm:text-sm">Ouça uma fala de exemplo, envie um áudio ou grave uma mensagem. Em qualquer pedido de Pix, confirme a pessoa por outro canal antes de agir.</p>
      </header>

      <div className="mb-5 grid gap-4 md:grid-cols-2">
        {Object.entries(SAMPLES).map(([scenario, sample]) => {
          const selected = selectedScenario === scenario;
          const danger = scenario === "cloned";
          return <article key={scenario} className={`rounded-2xl border p-5 transition-all ${selected ? (danger ? "border-[#FF3B5C] bg-[#FF3B5C]/10" : "border-[#00FF87] bg-[#00FF87]/10") : "border-[#132435] bg-[#060D14]"}`}>
            <div className="flex items-start justify-between gap-3"><div><span className={`font-mono text-[10px] font-bold uppercase tracking-widest ${danger ? "text-[#FF8195]" : "text-[#00FF87]"}`}>{sample.label}</span><h3 className="mt-2 font-syne text-base font-bold text-[#CDE8F0]">{danger ? "Pedido urgente de Pix" : "Conversa cotidiana"}</h3></div><AudioLines size={22} className={danger ? "text-[#FF8195]" : "text-[#00FF87]"} /></div>
            <p className="mt-3 min-h-12 font-mono text-xs leading-5 text-[#8BAAC0]">“{sample.text}”</p>
            <div className="mt-5 flex flex-wrap gap-2"><button type="button" onClick={() => selectSample(scenario)} className={`rounded-lg px-3 py-2 font-mono text-[10px] font-bold uppercase tracking-wider ${danger ? "bg-[#FF3B5C] text-white" : "bg-[#00FF87] text-[#04080C]"}`}>Usar amostra</button><button type="button" onClick={() => speakSample(scenario)} className="inline-flex items-center gap-2 rounded-lg border border-[#284258] px-3 py-2 font-mono text-[10px] font-bold uppercase tracking-wider text-[#CDE8F0] hover:border-[#00D4FF] hover:text-[#00D4FF]">{previewing === scenario ? <Square size={12} /> : <Play size={12} />}{previewing === scenario ? "Parar" : "Ouvir voz"}</button></div>
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

      {result && <section className={`mt-7 rounded-3xl border p-5 sm:p-7 ${isSynthetic ? "border-[#FF3B5C] bg-[#FF3B5C]/10" : "border-[#00FF87] bg-[#00FF87]/10"}`} aria-live="polite">
        {result.isDemo && <p className="mb-5 rounded-lg border border-[#FFB800]/30 bg-[#FFB800]/10 p-3 text-center font-mono text-[10px] leading-5 text-[#FFDB85]">Resultado educativo da amostra. Para uma análise forense, envie ou grave um áudio real.</p>}
        <div className="flex flex-col gap-4 border-b border-white/10 pb-5 sm:flex-row sm:items-center sm:justify-between"><div><span className="font-mono text-[10px] font-bold uppercase tracking-widest text-[#8BAAC0]">Processamento: {result.tempo_processamento_ms || 320} ms</span><h3 className={`mt-2 font-syne text-2xl font-black sm:text-3xl ${isSynthetic ? "text-[#FF8195]" : "text-[#00FF87]"}`}>{isSynthetic ? "Alerta: voz sintética ou golpe" : "Sem alerta crítico nesta análise"}</h3></div><div className={`text-4xl font-black ${isSynthetic ? "text-[#FF8195]" : "text-[#00FF87]"}`}>{result.score_percent || Math.round((result.confidence || 0) * 100)}<span className="ml-1 text-lg">%</span></div></div>
        <p className="mt-5 font-syne text-base font-bold leading-relaxed text-[#CDE8F0]">{result.short_explanation}</p>
        {result.indicators?.length > 0 && <ul className="mt-5 space-y-3">{result.indicators.map((indicator, index) => <li key={index} className="flex gap-3 font-mono text-xs leading-5 text-[#CDE8F0]"><span className={isSynthetic ? "text-[#FF8195]" : "text-[#00FF87]"}>{isSynthetic ? "!" : "✓"}</span>{indicator}</li>)}</ul>}
      </section>}
      <p className="mt-5 flex items-start gap-2 font-mono text-[10px] leading-5 text-[#5A7E94]"><Volume2 size={13} className="mt-1 shrink-0" />A prévia usa a voz disponível no navegador. A verificação de um arquivo enviado depende das fontes configuradas no servidor e não substitui confirmação com a pessoa por outro canal.</p>
    </section>
  );
}
