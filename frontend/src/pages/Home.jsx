import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Dropzone from "../components/Dropzone";
import LoadingScreen from "../components/LoadingScreen";
import { analyzeText, analyzeUrl, analyzeUpload } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import Footer from "../components/Footer";

const TABS   = ["TEXTO", "URL", "MÍDIA"];
const sleep  = ms => new Promise(r => setTimeout(r, ms));

const SOURCE_OPTIONS = [
  { value: "",           label: "Onde você viu/recebeu?"      },
  { value: "whatsapp",   label: "WhatsApp"                    },
  { value: "instagram",  label: "Instagram"                   },
  { value: "facebook",   label: "Facebook"                    },
  { value: "twitter",    label: "Twitter / X"                 },
  { value: "telegram",   label: "Telegram"                    },
  { value: "tiktok",     label: "TikTok"                      },
  { value: "youtube",    label: "YouTube"                     },
  { value: "email",      label: "E-mail"                      },
  { value: "sms",        label: "SMS"                         },
  { value: "site",       label: "Site / Portal de notícias"   },
  { value: "tv",         label: "TV / Rádio"                  },
  { value: "amigo",      label: "Amigo / Familiar"            },
  { value: "outro",      label: "Outro"                       },
];

export default function Home() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [tab,       setTab]       = useState(0);
  const [text,      setText]      = useState("");
  const [url,       setUrl]       = useState("");
  const [mediaFile, setMediaFile] = useState(null);
  const [source,    setSource]    = useState("");
  const [context,   setContext]   = useState("");
  const [loading,   setLoading]   = useState(false);
  const [stage,     setStage]     = useState(0);
  const [error,     setError]     = useState("");

  const MIN_TEXT = 20;

  const canSubmit = () => {
    if (tab === 0) return text.trim().length >= MIN_TEXT;
    if (tab === 1) return url.trim().length > 5;
    if (tab === 2) return !!mediaFile;
    return false;
  };

  const handleAnalyze = async () => {
    setError(""); setLoading(true); setStage(0);
    try {
      await sleep(700); setStage(1);
      await sleep(700); setStage(2);

      const sourceNote = source ? `\n\n[Fonte: ${source}${context ? ` – "${context}"` : ""}]` : "";

      let result;
      if (tab === 0)      result = await analyzeText(text + sourceNote);
      else if (tab === 1) result = await analyzeUrl(url);
      else                result = await analyzeUpload(mediaFile);

      setStage(3); await sleep(250);
      sessionStorage.setItem("verifai_result", JSON.stringify(result));
      sessionStorage.setItem("verifai_query",
        tab === 0 ? text.slice(0, 100)
        : tab === 1 ? url
        : mediaFile?.name || "Arquivo de Mídia");
      navigate("/report");
    } catch (e) {
      const detail = e?.response?.data?.detail;
      if (detail && typeof detail === "object" && detail.error === "limite_diario") {
        setError(detail.message);
      } else if (typeof detail === "string") {
        setError(detail);
      } else {
        setError(e.message || "Erro de conexão com o backend.");
      }
    } finally { setLoading(false); setStage(0); }
  };

  if (loading) return <LoadingScreen stage={stage}/>;

  return (
    <div style={{ background: "#04080C", minHeight: "100vh" }}>
      <div className="relative overflow-hidden">
        <div className="pointer-events-none fixed inset-0" style={{
          backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)",
          backgroundSize: "48px 48px", opacity: .4 }}/>
        
        <div className="relative z-10 max-w-2xl mx-auto px-5 pt-10 pb-10">
          {/* welcome */}
          <div className="text-center mb-8 fade-1">
            <div className="flex justify-center mb-3">
              <span className="font-mono text-[10px] tracking-[3px] px-4 py-1.5 rounded-full"
                style={{ background:"rgba(0,212,255,.1)", border:"1px solid rgba(0,212,255,.25)", color:"#00D4FF" }}>
                OLÁ, {user?.name?.split(" ")[0]?.toUpperCase()} · AUDITORIA FORENSE DIGITAL
              </span>
            </div>
            <h1 className="font-syne font-extrabold leading-none mb-3 fade-2"
              style={{ fontSize:"clamp(28px,5vw,48px)" }}>
              <span style={{ color:"#CDE8F0" }}>Analise de </span>
              <span style={{ background:"linear-gradient(135deg,#00D4FF,#00FF87)", WebkitBackgroundClip:"text", WebkitTextFillColor:"transparent" }}>
                Mídia e Fatos
              </span>
            </h1>
            <p className="font-mono text-[11px]" style={{ color:"#3A6070" }}>
              Camadas de Verificação · Gemini 3.1 Flash-Lite · Fact Check API · Deepfake Detection
            </p>
          </div>

          {/* main card */}
          <div className="rounded-2xl overflow-hidden fade-3" style={{
            background:"#0A1520", border:"1px solid #132435",
            boxShadow:"0 40px 80px rgba(0,0,0,.5)" }}>

            {/* tabs */}
            <div className="flex border-b" style={{ borderColor:"#132435", padding:"0 20px" }}>
              {TABS.map((t, i) => (
                <button key={t} onClick={() => setTab(i)}
                  className="font-mono text-[10px] tracking-[2px] px-5 py-3.5 transition-all"
                  style={{
                    color: tab===i ? "#00D4FF" : "#1A3A50",
                    borderBottom: tab===i ? "2px solid #00D4FF" : "2px solid transparent",
                    background: "transparent", cursor: "pointer" }}>
                  {t}
                </button>
              ))}
            </div>

            {/* input area */}
            <div className="p-5">
              {tab === 0 && (
                <div className="relative">
                  <textarea value={text} onChange={e => setText(e.target.value)}
                    placeholder="Cole aqui o texto, manchete ou afirmação suspeita..."
                    rows={6}
                    className="w-full font-mono text-[13px] leading-relaxed resize-none"
                    style={{ background:"transparent", border:"none", color:"#CDE8F0" }}/>
                </div>
              )}
              {tab === 1 && (
                <input type="url" value={url} onChange={e => setUrl(e.target.value)}
                  placeholder="https://link-da-noticia-ou-video.com/..."
                  className="w-full font-mono text-[13px] py-4"
                  style={{ background:"transparent", border:"none", color:"#CDE8F0", outline:"none" }}/>
              )}
              {tab === 2 && <Dropzone onFile={setMediaFile}/>}
            </div>

            {/* source section */}
            <div className="border-t px-5 py-4" style={{ borderColor:"#132435" }}>
              <span className="font-mono text-[9px] tracking-widest block mb-3" style={{ color:"#1A3A50" }}>
                ONDE VOCÊ VIU ISSO? (OPCIONAL)
              </span>
              <div className="flex gap-3">
                <select value={source} onChange={e => setSource(e.target.value)}
                  className="font-mono text-[11px] px-3 py-2 rounded-lg flex-1"
                  style={{ background:"#0F1E2E", border:"1px solid #132435", color:"#CDE8F0" }}>
                  {SOURCE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                {source && (
                  <input type="text" value={context} onChange={e => setContext(e.target.value)}
                    placeholder="Contexto..."
                    className="font-mono text-[11px] px-3 py-2 rounded-lg flex-1"
                    style={{ background:"#0F1E2E", border:"1px solid #132435", color:"#CDE8F0" }}/>
                )}
              </div>
            </div>

            {/* footer buttons */}
            <div className="flex items-center justify-between px-5 py-4 border-t"
              style={{ borderColor:"#132435", background:"#0F1E2E" }}>
              <div className="flex gap-4">
                <span className="font-mono text-[9px]" style={{ color:"#3A6070" }}>
                  <span style={{ color:"#00D4FF" }}>●</span> GEMINI 3.1
                </span>
                <span className="font-mono text-[9px]" style={{ color:"#3A6070" }}>
                  <span style={{ color:"#00FF87" }}>●</span> HIVE AI
                </span>
              </div>
              <button disabled={!canSubmit()} onClick={handleAnalyze}
                className="font-syne font-bold text-[12px] tracking-widest px-8 py-2.5 rounded-lg transition-all"
                style={{
                  background: canSubmit() ? "linear-gradient(135deg,#00D4FF,#00FF87)" : "#132435",
                  color: canSubmit() ? "#04080C" : "#3A6070",
                  cursor: canSubmit() ? "pointer" : "not-allowed" }}>
                ANALISAR AGORA →
              </button>
            </div>
          </div>

          {/* error box */}
          {error && (
            <div className="mt-4 px-4 py-3 rounded-lg font-mono text-[11px]"
              style={{ background:"rgba(255,59,92,.1)", border:"1px solid rgba(255,59,92,.3)", color:"#FF3B5C" }}>
              {error}
              {error.toLowerCase().includes("limite") && (
                <button onClick={() => navigate("/plans")} className="ml-3 underline text-cyan">Upgrade</button>
              )}
            </div>
          )}
        </div>
      </div>
      <Footer />
    </div>
  );
}
