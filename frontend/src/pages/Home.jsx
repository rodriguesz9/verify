import { useState, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import {
  FileText, Link2, Image, Mic, Upload, Search, Shield, CheckCircle,
  AlertTriangle, ArrowRight, Volume2, Phone, ChevronDown, ChevronUp,
  FileJson, Menu, X, Layers, Clipboard,
} from "lucide-react";
import Footer from "../components/Footer";
import { analyzeText, analyzeUrl, analyzeUpload, analyzeTextBatch } from "../services/api";
import { saveToOfflineCache } from "../services/offlineCache";

const TABS = [
  { id: 0, label: "Texto", icon: FileText, desc: "Cole o texto da mensagem que você recebeu" },
  { id: 1, label: "Link", icon: Link2, desc: "Cole o link de uma notícia ou site duvidoso" },
  { id: 2, label: "Imagem", icon: Image, desc: "Envie uma foto ou print de tela" },
  { id: 3, label: "Áudio", icon: Mic, desc: "Envie um áudio de WhatsApp para checar" },
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
    label: "Notícia Confiável",
    text: "Ministério da Saúde inicia campanha nacional de vacinação contra a gripe em postos de saúde de todo o Brasil para grupos prioritários."
  }
];

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

function parseBatchText(raw) {
  return raw
    .split(/\n{2,}|---+|===+|mensagens?:/)
    .map((t) => t.trim())
    .filter((t) => t.length >= 8);
}

export default function Home() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const audioInputRef = useRef(null);

  const [tab, setTab] = useState(0);
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [imageFile, setImageFile] = useState(null);
  const [audioFile, setAudioFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState(0);
  const [error, setError] = useState("");

  const [batchMode, setBatchMode] = useState(false);
  const [batchResults, setBatchResults] = useState(null);
  const [batchLoading, setBatchLoading] = useState(false);

  const canSubmit = () => {
    if (tab === 0) return text.trim().length >= 8;
    if (tab === 1) return url.trim().length >= 5;
    if (tab === 2) return !!imageFile;
    if (tab === 3) return !!audioFile;
    return false;
  };

  const canBatchSubmit = () => {
    if (tab !== 0) return false;
    const msgs = parseBatchText(text);
    return msgs.length >= 2 && msgs.length <= 10;
  };

  const handleAnalyze = async () => {
    setError(""); setLoading(true); setStage(0);
    try {
      await sleep(800); setStage(1);
      await sleep(800); setStage(2);
      let result;
      let queryLabel = "";

      if (tab === 0) {
        result = await analyzeText(text);
        queryLabel = text;
      } else if (tab === 1) {
        result = await analyzeUrl(url);
        queryLabel = url;
      } else if (tab === 2) {
        result = await analyzeUpload(imageFile);
        queryLabel = imageFile?.name || "Foto enviada";
      } else if (tab === 3) {
        result = await analyzeUpload(audioFile);
        queryLabel = audioFile?.name || "Áudio enviado";
      }

      setStage(3); await sleep(400);
      result.query_input = queryLabel;
      saveToOfflineCache(result);
      sessionStorage.setItem("verify_result", JSON.stringify(result));
      sessionStorage.setItem("verify_query", queryLabel);
      sessionStorage.setItem("verifai_result", JSON.stringify(result));
      sessionStorage.setItem("verifai_query", queryLabel);
      navigate("/report");
    } catch (e) {
      console.error("Analysis error:", e);
      const detail = e?.response?.data?.detail;
      if (detail && typeof detail === "object" && detail.error === "limite_diario") {
        setError("Seu limite diário de consultas gratuitas foi atingido hoje.");
      } else {
        setError("Não foi possível concluir a checagem no momento. Por favor, tente novamente.");
      }
    } finally {
      setLoading(false);
      setStage(0);
    }
  };

  const handleBatchAnalyze = async () => {
    if (!canBatchSubmit()) return;
    const msgs = parseBatchText(text);
    setBatchLoading(true); setError(""); setBatchResults(null);
    try {
      const data = await analyzeTextBatch(msgs);
      setBatchResults(data.results || []);
    } catch (e) {
      console.error("Batch error:", e);
      setError("Erro ao analisar mensagens em lote. Tente novamente.");
    } finally {
      setBatchLoading(false);
    }
  };

  const VERDICT_COLORS = {
    Authentic: "#00FF87", AI_Generated: "#00D4FF", Manipulated: "#FF3B5C",
    Out_Of_Context: "#FFB830", Suspicious: "#8AA2B4", Scam: "#FF3B5C",
  };

  const tabs = TABS;

  return (
    <div className="relative min-h-screen bg-[#04080C] text-[#CDE8F0] overflow-hidden pb-20">
      <div className="pointer-events-none fixed inset-0" style={{ backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)", backgroundSize: "48px 48px", opacity: .15 }}/>

      <div className="relative z-10 max-w-3xl mx-auto px-4 sm:px-6 pt-20 sm:pt-28">

        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-md border border-[#00D4FF33] bg-[#00D4FF0D] text-[#00D4FF] font-mono text-[10px] font-bold uppercase tracking-widest mb-6">
            <Shield size={12} /> Proteção simples para toda a família
          </div>
          <h1 className="font-syne font-extrabold text-3xl sm:text-5xl text-[#CDE8F0] mb-4 leading-tight">
            Descubra se é <span className="text-[#00D4FF] underline decoration-[#00FF87] underline-offset-8">Verdade</span> ou <span className="text-[#FF3B5C]">Golpe</span>
          </h1>
          <p className="font-mono text-sm sm:text-base text-[#8AA2B4] max-w-xl mx-auto leading-relaxed">
            {user ? `Olá, ${user.name.split(" ")[0]}! ` : ""}Cole abaixo a mensagem recebida para checarmos com jornais e especialistas em tempo real.
          </p>
        </div>

        <div className="rounded-xl overflow-hidden shadow-2xl border border-[#132435] bg-[#0A1520] transition-all">

          <div className="grid grid-cols-2 sm:grid-cols-4 border-b border-[#132435] bg-[#070F17]">
            {tabs.map((t) => (
              <button
                key={t.id}
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

          <div className="px-6 pt-5 pb-3 text-xs text-[#00FF87] font-mono font-bold flex items-center justify-between">
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

          <div className="p-6 sm:p-8 pt-2">

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
                  className="w-full font-mono text-sm sm:text-base leading-relaxed p-4 rounded-lg bg-[#04080C] border border-[#132435] text-[#CDE8F0] placeholder-[#3A6070] focus:border-[#00D4FF] focus:outline-none resize-none transition-all"
                />

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
                <div className="relative">
                  <Link2 size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#3A6070]" />
                  <input
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://exemplo.com/noticia-para-verificar"
                    className="w-full font-mono text-sm sm:text-base p-4 pl-10 rounded-lg bg-[#04080C] border border-[#132435] text-[#CDE8F0] placeholder-[#3A6070] focus:border-[#00D4FF] focus:outline-none transition-all"
                  />
                </div>
                <p className="text-xs text-[#5A7E94] font-mono">
                  Checamos se o site é verdadeiro, se foi criado recentemente para aplicar golpes ou se imita páginas do governo e bancos.
                </p>
              </div>
            )}

            {tab === 2 && (
              <div>
                <label htmlFor="image-upload" className="flex flex-col items-center justify-center border-2 border-dashed border-[#132435] hover:border-[#00D4FF] rounded-lg p-10 text-center cursor-pointer bg-[#04080C] transition-all">
                  <input id="image-upload" type="file" accept="image/*" className="hidden" onChange={(e) => setImageFile(e.target.files[0])} />
                  <Upload size={28} className="text-[#00D4FF] mb-3" />
                  <span className="font-syne font-bold text-sm text-[#CDE8F0] mb-1">Clique para enviar a imagem</span>
                  <span className="text-xs text-[#5A7E94] font-mono">Formatos suportados: .jpg, .png, .webp, .gif</span>
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
                <div
                  onClick={() => audioInputRef.current?.click()}
                  className="border-2 border-dashed border-[#132435] hover:border-[#00D4FF] rounded-lg p-8 text-center cursor-pointer bg-[#04080C] transition-all"
                >
                  <input
                    ref={audioInputRef}
                    type="file"
                    accept="audio/*,.mp3,.ogg,.wav,.m4a,.aac,.opus"
                    onChange={(e) => setAudioFile(e.target.files[0])}
                    className="hidden"
                  />
                  <Mic size={28} className="text-[#00D4FF] mb-3 mx-auto" />
                  <div className="font-syne font-bold text-sm text-[#CDE8F0] mb-1">Clique para enviar o áudio do WhatsApp</div>
                  <div className="text-xs text-[#5A7E94] font-mono">Formatos suportados: .mp3, .ogg (WhatsApp), .m4a, .wav</div>
                </div>

                {audioFile && (
                  <div className="p-4 rounded-lg bg-[#00FF8710] border border-[#00FF8730] text-sm text-[#00FF87] flex items-center justify-between font-mono">
                    <span>Áudio pronto para checagem: <strong>{audioFile.name}</strong></span>
                    <button onClick={() => setAudioFile(null)} className="text-red-400 hover:underline cursor-pointer">Remover</button>
                  </div>
                )}
              </div>
            )}

          </div>

          <div className="p-6 sm:p-8 bg-[#070F17] border-t border-[#132435] flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3 text-xs font-mono text-[#5A7E94]">
              <span className="flex items-center gap-1 text-[#00D4FF]">
                <span className="w-2.5 h-2.5 rounded-full bg-[#00D4FF] animate-pulse" /> Busca em Tempo Real
              </span>
              <span>•</span>
              <span className="text-[#00FF87]">Inteligência Verify</span>
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
        </div>

        {error && (
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
                <div
                  key={i}
                  className="rounded-lg border border-[#132435] bg-[#0A1520] p-4 hover:border-[#00D4FF]/50 transition-colors cursor-pointer"
                  onClick={() => {
                    sessionStorage.setItem("verify_result", JSON.stringify(r));
                    sessionStorage.setItem("verify_query", r.query_input || "");
                    navigate("/report");
                  }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="font-mono text-xs text-[#CDE8F0] truncate">{r.query_input || `Mensagem ${i + 1}`}</p>
                      <p className="font-mono text-[11px] text-[#8AA2B4] mt-1 line-clamp-2">{r.summary || r.plain_explanation || "—"}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <span
                        className="font-mono text-[10px] font-bold uppercase tracking-wider"
                        style={{ color }}
                      >
                        {r.verdict || "—"}
                      </span>
                      <div className="font-mono text-xs mt-1" style={{ color }}>{r.score ?? "—"}%</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-12 grid grid-cols-1 sm:grid-cols-3 gap-4 text-center">
          {[
            { n: "1", t: "Cole ou Envie", d: "Copie a mensagem recebida no WhatsApp e cole aqui com um toque." },
            { n: "2", t: "Checagem Rápida", d: "Cruzamos a informação com agências sérias de jornalismo e bancos de dados." },
            { n: "3", t: "Resultado Fácil", d: "Você vê se é verdade, ouve a explicação e avisa a família sem complicações." },
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
