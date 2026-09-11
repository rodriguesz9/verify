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
              A detecção de conteúdos gerados por IA e checagem de fatos é baseada em modelos matemáticos e bases de jornalismo. 
              O Verify fornece um índice de confiabilidade e alertas claros, mas incentivamos sempre a prudência e a busca por fontes oficiais.
            </p>
          </section>

          <section>
            <h2 className="text-cyan mb-3 tracking-widest text-[11px] uppercase">Atraso de Indexação</h2>
            <p>
               Embora o sistema utilize busca em tempo real, a apuração de boatos muito recentes por agências de checagem pode levar alguns minutos ou horas.
            </p>
          </section>

          <section>
             <div className="p-6 rounded-xl bg-amber-500/5 border border-amber-500/20">
                <h3 className="text-amber-500 mb-2 uppercase text-[10px] tracking-widest">Aviso Importante</h3>
                <p className="italic">
                   As análises do Verify devem ser utilizadas como uma ferramenta de suporte e esclarecimento contra fraudes, protegendo seu bem-estar digital.
                </p>
             </div>
          </section>
        </div>
      </div>
      <Footer />
    </div>
  );
}
