import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Dropzone from "../components/Dropzone";
import LoadingScreen from "../components/LoadingScreen";
import { analyzeText, analyzeUrl, analyzeUpload } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import Footer from "../components/Footer";

const TABS  = ["TEXTO", "LINK / SITE", "IMAGEM"];
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

export default function Home() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [tab,       setTab]       = useState(0);
  const [text,      setText]      = useState("");
  const [url,       setUrl]       = useState("");
  const [imageFile, setImageFile] = useState(null);
  const [loading,   setLoading]   = useState(false);
  const [stage,     setStage]     = useState(0);
  const [error,     setError]     = useState("");

  const canSubmit = () => {
    if (tab === 0) return text.trim().length > 10;
    if (tab === 1) return url.trim().length > 5;
    if (tab === 2) return !!imageFile;
    return false;
  };

  const handleAnalyze = async () => {
    setError(""); setLoading(true); setStage(0);
    try {
      await sleep(1000); setStage(1);
      await sleep(1000); setStage(2);
      let result;
      if (tab === 0)      result = await analyzeText(text);
      else if (tab === 1) result = await analyzeUrl(url);
      else                result = await analyzeUpload(imageFile);
      setStage(3); await sleep(500);
      sessionStorage.setItem("verifai_result", JSON.stringify(result));
      sessionStorage.setItem("verifai_query",  tab === 0 ? text : tab === 1 ? url : imageFile?.name || "");
      navigate("/report");
    } catch (e) {
      console.error("Analysis error:", e);
      const detail = e?.response?.data?.detail;
      if (detail && typeof detail === "object" && detail.error === "limite_diario") {
        setError("Seu limite diário acabou. Que tal mudar para o plano Protetor?");
      } else {
        setError("Ocorreu um erro na checagem. Tente novamente em instantes.");
      }
    } finally { setLoading(false); setStage(0); }
  };

  if (loading) return <LoadingScreen stage={stage}/>;

  return (
    <div className="relative min-h-screen overflow-hidden pb-20">
      <div className="pointer-events-none fixed inset-0" style={{ backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)", backgroundSize: "48px 48px", opacity: .3 }}/>
      
      <div className="relative z-10 max-w-2xl mx-auto px-5 pt-32">
        <div className="text-center mb-10">
          <h1 className="font-syne font-black text-4xl md:text-5xl text-[#CDE8F0] mb-4 uppercase tracking-tighter">
            O que você quer <span className="text-cyan italic">checar</span> hoje?
          </h1>
          <p className="font-mono text-[13px] text-[#3A6070] uppercase tracking-widest font-bold">
            Olá, {user?.name?.split(" ")[0]}! Cole o conteúdo abaixo para saber se é verdade.
          </p>
        </div>

        <div className="rounded-[2.5rem] overflow-hidden shadow-2xl tilt-card" style={{ background: "#0A1520", border: "1px solid #132435" }}>
          <div className="flex border-b border-[#132435] px-6">
            {TABS.map((t, i) => (
              <button key={t} onClick={() => setTab(i)}
                className="font-mono text-[11px] tracking-[3px] px-6 py-5 transition-all outline-none uppercase font-bold"
                style={{
                  color: tab === i ? "#00D4FF" : "#1A3A50",
                  borderBottom: tab === i ? "2px solid #00D4FF" : "2px solid transparent",
                  marginBottom: -1, background: "transparent"
                }}>
                {t}
              </button>
            ))}
          </div>

          <div className="p-8 pb-4">
            {tab === 0 && (
              <div className="relative">
                <textarea value={text} onChange={e => setText(e.target.value)}
                  placeholder="Cole aqui o texto ou notícia que você recebeu no WhatsApp ou redes sociais..." rows={6}
                  className="w-full font-mono text-[16px] leading-relaxed resize-none bg-transparent border-none text-[#CDE8F0] outline-none"
                />
              </div>
            )}
            {tab === 1 && (
              <input type="url" value={url} onChange={e => setUrl(e.target.value)}
                placeholder="Cole aqui o link do site (ex: https://site.com/...)"
                className="w-full font-mono text-[16px] py-6 bg-transparent border-none text-[#CDE8F0] outline-none"
              />
            )}
            {tab === 2 && <Dropzone onFile={setImageFile} />}
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between px-8 py-6 border-t border-[#132435] bg-[#0F1E2E] gap-4">
            <div className="flex gap-4">
               <span className="flex items-center gap-2 font-mono text-[10px] text-[#3A6070] font-bold uppercase">
                  <span className="w-2 h-2 rounded-full bg-cyan shadow-[0_0_8px_#00D4FF]" /> Buscando Fatos
               </span>
               <span className="flex items-center gap-2 font-mono text-[10px] text-[#3A6070] font-bold uppercase">
                  <span className="w-2 h-2 rounded-full bg-green shadow-[0_0_8px_#00FF87]" /> Inteligência Verify
               </span>
            </div>
            <button disabled={!canSubmit()} onClick={handleAnalyze}
              className="w-full sm:w-auto font-syne font-black text-[13px] tracking-[4px] px-10 py-4 rounded-2xl transition-all shadow-xl"
              style={{
                background: canSubmit() ? "linear-gradient(135deg,#00D4FF,#00FF87)" : "#132435",
                color: canSubmit() ? "#04080C" : "#3A6070",
                cursor: canSubmit() ? "pointer" : "not-allowed"
              }}>
              VERIFICAR AGORA
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-6 p-5 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-500 font-mono text-[12px] text-center animate-fade-in shadow-xl">
             <span className="font-bold mr-2">!</span> {error}
             {error.includes("limite") && (
               <button onClick={() => navigate("/plans")} className="ml-2 underline text-cyan font-bold">Ver Planos</button>
             )}
          </div>
        )}
      </div>
      <Footer />
    </div>
  );
}
