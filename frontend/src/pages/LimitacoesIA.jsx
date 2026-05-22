import Footer from "../components/Footer";

export default function LimitacoesIA() {
  return (
    <div className="relative min-h-screen pb-20">
      <div className="pointer-events-none fixed inset-0"
        style={{
          backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)",
          backgroundSize: "48px 48px", opacity: .1,
        }}/>
      <div className="relative z-10 max-w-3xl mx-auto px-5 pt-20">
        <h1 className="font-syne font-extrabold text-3xl text-text mb-8">Limitações e Isenções</h1>
        
        <div className="space-y-8 font-mono text-[13px] leading-relaxed" style={{ color: "#3A6070" }}>
          <section>
            <h2 className="text-cyan mb-3 tracking-widest text-[11px] uppercase">Natureza Probabilística</h2>
            <p>
              A detecção de conteúdos gerados por IA (Deepfakes) é baseada em modelos matemáticos probabilísticos. 
              O VerifAI fornece um "Score de Integridade" que indica a chance de manipulação, mas não garante 100% de 
              certeza absoluta, dado que as tecnologias de geração evoluem constantemente.
            </p>
          </section>

          <section>
            <h2 className="text-cyan mb-3 tracking-widest text-[11px] uppercase">Atraso de Indexação</h2>
            <p>
               Embora o sistema utilize o mecanismo Antianacronismo para contexto temporal, a indexação de bases de dados 
               globais de Fact-Checking pode ter um atraso de algumas horas em relação aos acontecimentos em tempo real.
            </p>
          </section>

          <section>
             <div className="p-6 rounded-xl bg-amber-500/5 border border-amber-500/20">
                <h3 className="text-amber-500 mb-2 uppercase text-[10px] tracking-widest">Aviso Importante</h3>
                <p className="italic">
                   As análises do VerifAI devem ser utilizadas como uma ferramenta de suporte ao julgamento humano e não como 
                   verdade única em processos legais ou decisões críticas.
                </p>
             </div>
          </section>
        </div>
      </div>
      <Footer />
    </div>
  );
}
