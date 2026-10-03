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
              Os índices são sinais heurísticos, não porcentagens de acerto comprovadas. Uma resposta sem sinais de IA
              não comprova autenticidade. Falhas ou ausência dos detectores devem produzir um resultado inconclusivo.
            </p>
          </section>

          <section>
            <h2 className="text-cyan mb-3 tracking-widest text-[11px] uppercase">Atraso de Indexação</h2>
            <p>
               A consulta depende das fontes configuradas e de sua disponibilidade. A apuração de boatos recentes pode
               levar tempo; ausência de uma publicação não prova que a informação seja verdadeira ou falsa.
            </p>
          </section>

          <section>
             <div className="p-6 rounded-xl bg-amber-500/5 border border-amber-500/20">
                <h3 className="text-amber-500 mb-2 uppercase text-[10px] tracking-widest">Aviso Importante</h3>
                <p className="italic">
                   Vídeos são avaliados por três quadros amostrados, sem análise temporal completa, sincronização labial ou
                   confirmação de identidade. Transcrição de áudio não detecta clonagem de voz. O selo SHA-256 verifica
                   igualdade dos bytes registrados, não a veracidade da cena, autoria ou uma assinatura C2PA confiável.
                </p>
             </div>
          </section>
        </div>
      </div>
      <Footer />
    </div>
  );
}
