import { useState } from "react";
import Footer from "../components/Footer";

export default function Sugestoes() {
  const [sent, setSent] = useState(false);
  const [msg, setMsg] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!msg.trim()) return;
    setSent(true);
    // Simulation
    setTimeout(() => {
      setSent(false);
      setMsg("");
    }, 3000);
  };

  return (
    <div className="relative min-h-screen pb-20">
      <div className="pointer-events-none fixed inset-0"
        style={{
          backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)",
          backgroundSize: "48px 48px", opacity: .18,
        }}/>

      <div className="relative z-10 max-w-2xl mx-auto px-5 pt-16">
        <div className="text-center mb-12 fade-1">
          <span className="font-mono text-[10px] tracking-[3px] px-4 py-1.5 rounded-full mb-4 inline-block"
            style={{ background: "rgba(0,212,255,.1)", border: "1px solid rgba(0,212,255,.25)", color: "#00D4FF" }}>
            CONTRIBUA COM O PROJETO
          </span>
          <h1 className="font-syne font-extrabold text-text mb-4" style={{ fontSize: "clamp(28px,5vw,48px)" }}>
            Sugestões e <span className="text-cyan">Melhorias</span>
          </h1>
          <p className="font-mono text-[12px] leading-relaxed" style={{ color: "#3A6070" }}>
            Sua opinião é fundamental para o aprimoramento do Antigravity Core. 
            Encontrou um bug? Tem uma ideia de nova API de detecção? Nos avise abaixo.
          </p>
        </div>

        <div className="rounded-2xl overflow-hidden fade-2" 
          style={{ background: "#0A1520", border: "1px solid #132435", boxShadow: "0 40px 80px rgba(0,0,0,.5)" }}>
          <form onSubmit={handleSubmit} className="p-8 flex flex-col gap-6">
            <div>
              <label className="font-mono text-[10px] tracking-widest block mb-3" style={{ color: "#3A6070" }}>
                SUA MENSAGEM OU SUGESTÃO TÉCNICA
              </label>
              <textarea 
                value={msg} 
                onChange={e => setMsg(e.target.value)}
                placeholder="Ex: Gostaria de ver integração com a API da Deepware..."
                rows={6}
                className="w-full font-mono text-[13px] px-4 py-3 rounded-lg resize-none"
                style={{ background: "#0F1E2E", border: "1px solid #132435", color: "#CDE8F0", outline: "none" }}
              />
            </div>
            
            <button 
              type="submit"
              disabled={sent || !msg.trim()}
              className="w-full font-syne font-bold text-[13px] tracking-widest py-3 rounded-lg transition-all"
              style={{
                background: sent ? "#132435" : "linear-gradient(135deg,#00D4FF,#00FF87)",
                color: sent ? "#3A6070" : "#04080C",
                border: "none", cursor: sent ? "not-allowed" : "pointer",
                boxShadow: !sent ? "0 0 24px rgba(0,212,255,.3)" : "none"
              }}
            >
              {sent ? "SUGESTÃO ENVIADA!" : "ENVIAR FEEDBACK →"}
            </button>
          </form>
        </div>

        <p className="text-center font-mono text-[10px] mt-10" style={{ color: "#1A3A50" }}>
          Todas as sugestões são lidas pela equipe de desenvolvimento e priorizadas no roadmap oficial.
        </p>
      </div>
      <Footer />
    </div>
  );
}
