import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import Dropzone from "../components/Dropzone";
import LoadingScreen from "../components/LoadingScreen";
import { analyzeText, analyzeUrl, analyzeUpload } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import Footer from "../components/Footer";

const TABS = [
  { id: 0, label: "Texto / WhatsApp", icon: "📝", desc: "Cole o texto da mensagem que você recebeu" },
  { id: 1, label: "Link de Site",      icon: "🔗", desc: "Cole o link de uma notícia ou site duvidoso" },
  { id: 2, label: "Foto / Imagem",     icon: "🖼️", desc: "Envie uma foto ou print de tela" },
  { id: 3, label: "Áudio de Voz",      icon: "🎙️", desc: "Envie um áudio de WhatsApp para checar" },
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

  const canSubmit = () => {
    if (tab === 0) return text.trim().length >= 8;
    if (tab === 1) return url.trim().length >= 5;
    if (tab === 2) return !!imageFile;
    if (tab === 3) return !!audioFile;
    return false;
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
      sessionStorage.setItem("verify_result", JSON.stringify(result));
      sessionStorage.setItem("verify_query", queryLabel);
      // Legacy fallback
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

  return (
    <div className="relative min-h-screen overflow-hidden pb-20">
      {/* Background grid */}
      <div className="pointer-events-none fixed inset-0" style={{ backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)", backgroundSize: "48px 48px", opacity: .25 }}/>
      
      <div className="relative z-10 max-w-3xl mx-auto px-4 sm:px-6 pt-16 sm:pt-24">
        
        {/* Header Friendly */}
        <div className="text-center mb-8 sm:mb-10">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#00D4FF15] border border-[#00D4FF33] text-[#00D4FF] font-mono text-xs font-bold uppercase tracking-widest mb-4">
            🛡️ Proteção simples para toda a família
          </div>
          <h1 className="font-syne font-extrabold text-3xl sm:text-5xl text-[#CDE8F0] mb-3 leading-tight">
            Descubra se é <span className="text-[#00D4FF] underline decoration-[#00FF87] underline-offset-8">Verdade</span> ou <span className="text-[#FF3B5C]">Golpe</span>
          </h1>
          <p className="text-base sm:text-lg text-[#8AA2B4] max-w-xl mx-auto leading-relaxed">
            {user ? `Olá, ${user.name.split(" ")[0]}! ` : ""}Cole abaixo a mensagem recebida para checarmos com jornais e especialistas em tempo real.
          </p>
        </div>

        {/* Main Box */}
        <div className="rounded-3xl overflow-hidden shadow-2xl border border-[#132435] bg-[#0A1520] transition-all">
          
          {/* Navigation Tabs */}
          <div className="grid grid-cols-2 sm:grid-cols-4 border-b border-[#132435] bg-[#070F17]">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => { setTab(t.id); setError(""); }}
                className="flex flex-col items-center justify-center gap-1.5 py-4 px-2 sm:px-4 text-center transition-all cursor-pointer"
                style={{
                  color: tab === t.id ? "#00D4FF" : "#5A7E94",
                  backgroundColor: tab === t.id ? "#0A1520" : "transparent",
                  borderBottom: tab === t.id ? "3px solid #00D4FF" : "3px solid transparent",
                  fontWeight: tab === t.id ? "bold" : "normal"
                }}
              >
                <span className="text-2xl">{t.icon}</span>
                <span className="text-xs sm:text-sm font-syne">{t.label}</span>
              </button>
            ))}
          </div>

          {/* Tab Description Helper */}
          <div className="px-6 pt-5 pb-2 text-xs text-[#00FF87] font-mono font-bold flex items-center gap-2">
            <span>👉</span> {TABS[tab].desc}
          </div>

          {/* Form Content */}
          <div className="p-6 sm:p-8 pt-2">
            
            {/* Tab 0: Text */}
            {tab === 0 && (
              <div className="space-y-4">
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Cole aqui o texto da mensagem, boato ou notícia..."
                  rows={5}
                  className="w-full text-base sm:text-lg leading-relaxed p-4 rounded-2xl bg-[#04080C] border border-[#132435] text-[#CDE8F0] placeholder-[#3A6070] focus:border-[#00D4FF] focus:outline-none resize-none transition-all"
                />
                
                {/* Example Pills */}
                <div className="flex flex-wrap items-center gap-2 pt-1">
                  <span className="text-xs text-[#5A7E94] font-mono">Testar exemplo:</span>
                  {EXAMPLES.map((ex, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setText(ex.text)}
                      className="text-xs px-3 py-1 rounded-full bg-[#132435] hover:bg-[#1A3A50] text-[#CDE8F0] border border-[#1A3A50] transition-colors"
                    >
                      {ex.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Tab 1: Link */}
            {tab === 1 && (
              <div className="space-y-4">
                <div className="relative">
                  <input
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://exemplo.com/noticia-para-verificar"
                    className="w-full text-base sm:text-lg p-4 pl-4 rounded-2xl bg-[#04080C] border border-[#132435] text-[#CDE8F0] placeholder-[#3A6070] focus:border-[#00D4FF] focus:outline-none transition-all"
                  />
                </div>
                <p className="text-xs text-[#5A7E94]">
                  💡 Dica: Verificamos se o site é verdadeiro, se foi criado recentemente para aplicar golpes ou se imita páginas do governo e bancos.
                </p>
              </div>
            )}

            {/* Tab 2: Image */}
            {tab === 2 && (
              <div>
                <Dropzone onFile={setImageFile} />
                {imageFile && (
                  <div className="mt-3 p-3 rounded-xl bg-[#00D4FF10] border border-[#00D4FF30] text-xs text-[#00D4FF] flex items-center justify-between">
                    <span>🖼️ Arquivo selecionado: <strong>{imageFile.name}</strong></span>
                    <button onClick={() => setImageFile(null)} className="text-red-400 hover:underline">Remover</button>
                  </div>
                )}
              </div>
            )}

            {/* Tab 3: Audio */}
            {tab === 3 && (
              <div className="space-y-4">
                <div
                  onClick={() => audioInputRef.current?.click()}
                  className="border-2 border-dashed border-[#132435] hover:border-[#00D4FF] rounded-2xl p-8 text-center cursor-pointer bg-[#04080C] transition-all"
                >
                  <input
                    type="file"
                    ref={audioInputRef}
                    accept="audio/*,.mp3,.ogg,.wav,.m4a,.aac,.opus"
                    onChange={(e) => setAudioFile(e.target.files[0])}
                    className="hidden"
                  />
                  <div className="text-4xl mb-3">🎙️</div>
                  <div className="font-syne font-bold text-base text-[#CDE8F0] mb-1">
                    Clique para enviar o áudio do WhatsApp
                  </div>
                  <div className="text-xs text-[#5A7E94] font-mono">
                    Formatos suportados: .mp3, .ogg (áudio do WhatsApp), .m4a, .wav
                  </div>
                </div>

                {audioFile && (
                  <div className="p-4 rounded-xl bg-[#00FF8710] border border-[#00FF8730] text-sm text-[#00FF87] flex items-center justify-between">
                    <span>🎵 Áudio pronto para checagem: <strong>{audioFile.name}</strong></span>
                    <button onClick={() => setAudioFile(null)} className="text-red-400 hover:underline">Remover</button>
                  </div>
                )}
              </div>
            )}

          </div>

          {/* Action Footer */}
          <div className="p-6 sm:p-8 bg-[#070F17] border-t border-[#132435] flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3 text-xs font-mono text-[#5A7E94]">
              <span className="flex items-center gap-1 text-[#00D4FF]">
                <span className="w-2.5 h-2.5 rounded-full bg-[#00D4FF] animate-pulse" />
                Busca em Tempo Real
              </span>
              <span>•</span>
              <span className="text-[#00FF87]">Inteligência Verify</span>
            </div>

            <button
              disabled={!canSubmit()}
              onClick={handleAnalyze}
              className="w-full sm:w-auto font-syne font-extrabold text-sm sm:text-base tracking-wider px-8 py-4 rounded-2xl transition-all shadow-lg flex items-center justify-center gap-2"
              style={{
                background: canSubmit() ? "linear-gradient(135deg,#00D4FF,#00FF87)" : "#132435",
                color: canSubmit() ? "#04080C" : "#5A7E94",
                cursor: canSubmit() ? "pointer" : "not-allowed",
                transform: canSubmit() ? "scale(1.02)" : "scale(1)"
              }}
            >
              <span>🔍</span>
              <span>VERIFICAR AGORA</span>
            </button>
          </div>
        </div>

        {/* Error Notification */}
        {error && (
          <div className="mt-6 p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm text-center">
            <strong>⚠️ Atenção:</strong> {error}
          </div>
        )}

        {/* How it works simple cards for seniors */}
        <div className="mt-12 grid grid-cols-1 sm:grid-cols-3 gap-4 text-center">
          <div className="p-5 rounded-2xl bg-[#0A1520] border border-[#132435]">
            <div className="text-2xl mb-2">1️⃣</div>
            <h4 className="font-bold text-sm text-[#CDE8F0] mb-1">Cole ou Envie</h4>
            <p className="text-xs text-[#5A7E94]">Copie a mensagem recebida no WhatsApp e cole aqui com um toque.</p>
          </div>
          <div className="p-5 rounded-2xl bg-[#0A1520] border border-[#132435]">
            <div className="text-2xl mb-2">2️⃣</div>
            <h4 className="font-bold text-sm text-[#CDE8F0] mb-1">Checagem Rápida</h4>
            <p className="text-xs text-[#5A7E94]">Cruzamos a informação com agências sérias de jornalismo e bancos de dados.</p>
          </div>
          <div className="p-5 rounded-2xl bg-[#0A1520] border border-[#132435]">
            <div className="text-2xl mb-2">3️⃣</div>
            <h4 className="font-bold text-sm text-[#CDE8F0] mb-1">Resultado Fácil</h4>
            <p className="text-xs text-[#5A7E94]">Você vê se é verdade, ouve a explicação e avisa a família sem complicações.</p>
          </div>
        </div>

      </div>

      <Footer />
      {loading && <LoadingScreen stage={stage} />}
    </div>
  );
}
