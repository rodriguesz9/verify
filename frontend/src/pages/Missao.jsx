import Footer from "../components/Footer";

export default function Missao() {
  return (
    <div className="relative min-h-screen pb-20">
      <div className="pointer-events-none fixed inset-0"
        style={{
          backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)",
          backgroundSize: "48px 48px", opacity: .18,
        }}/>

      <div className="relative z-10 max-w-4xl mx-auto px-5 pt-16">
        <div className="text-center mb-16 fade-1">
          <span className="font-mono text-[10px] tracking-[3px] px-4 py-1.5 rounded-full mb-4 inline-block"
            style={{ background: "rgba(0,212,255,.1)", border: "1px solid rgba(0,212,255,.25)", color: "#00D4FF" }}>
            NOSSA MISSÃO
          </span>
          <h1 className="font-syne font-extrabold text-text mb-6"
            style={{ fontSize: "clamp(32px,6vw,64px)" }}>
            A Verdade em <span className="text-cyan">Código-Fonte</span>
          </h1>
          <p className="font-mono text-[14px] max-w-2xl mx-auto leading-relaxed" style={{ color: "#3A6070" }}>
            O Verify nasceu da necessidade urgente de restaurar a confiança no ecossistema digital e proteger a população contra golpes e fake news. 
            Em um mundo inundado por boatos, fraudes no WhatsApp e conteúdos gerados por IA, nossa missão é democratizar 
            a checagem de fatos com uma linguagem simples e acessível para todos.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-8 mb-20 fade-2">
          <div className="rounded-2xl p-8" style={{ background: "#0A1520", border: "1px solid #132435" }}>
            <h3 className="font-syne font-bold text-xl text-cyan mb-4">Transparência</h3>
            <p className="font-mono text-[12px] leading-relaxed" style={{ color: "#3A6070" }}>
              Utilizamos modelos de ponta (Gemini 3.1 Flash-Lite) e ferramentas de verificação aberta para garantir 
              que cada relatório seja fundamentado em dados técnicos auditáveis.
            </p>
          </div>
          <div className="rounded-2xl p-8" style={{ background: "#0A1520", border: "1px solid #132435" }}>
            <h3 className="font-syne font-bold text-xl text-cyan mb-4">Integridade</h3>
            <p className="font-mono text-[12px] leading-relaxed" style={{ color: "#3A6070" }}>
              Nossa tecnologia de busca reversa e detecção de perplexidade textual expõe a origem e a manipulação 
              de conteúdos, independentemente da fonte.
            </p>
          </div>
        </div>

        <div className="text-center fade-3">
          <p className="font-mono text-[11px] uppercase tracking-widest mb-4" style={{ color: "#1A3A50" }}>
            Desenvolvido por profissionais dedicados à segurança da informação.
          </p>
          <div className="flex justify-center gap-6">
             <span className="text-cyan opacity-50 font-mono text-[10px]">#ANTI-PROPAGANDA</span>
             <span className="text-cyan opacity-50 font-mono text-[10px]">#FORENSIC-FIRST</span>
             <span className="text-cyan opacity-50 font-mono text-[10px]">#TRUTH-INDEX</span>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
