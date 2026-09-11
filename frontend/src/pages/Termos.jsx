import Footer from "../components/Footer";

export default function Termos() {
  return (
    <div className="relative min-h-screen pb-20">
      <div className="pointer-events-none fixed inset-0"
        style={{
          backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)",
          backgroundSize: "48px 48px", opacity: .1,
        }}/>
      <div className="relative z-10 max-w-3xl mx-auto px-5 pt-20">
        <h1 className="font-syne font-extrabold text-3xl text-text mb-8">Termos de Serviço</h1>
        
        <div className="space-y-8 font-mono text-[13px] leading-relaxed" style={{ color: "#3A6070" }}>
          <section>
            <h2 className="text-cyan mb-3 tracking-widest text-[11px] uppercase">1. Escopo do Serviço</h2>
            <p>
              O Verify fornece uma plataforma de análise probabilística de arquivos, textos, links e áudios para identificação 
              de fraudes, golpes e desinformação, auxiliando na proteção digital do cidadão.
            </p>
          </section>

          <section>
            <h2 className="text-cyan mb-3 tracking-widest text-[11px] uppercase">2. Responsabilidade de Uso</h2>
            <p>
              O usuário retém os direitos e a total responsabilidade legal sobre os conteúdos enviados à plataforma para checagem.
            </p>
          </section>

          <section>
            <h2 className="text-cyan mb-3 tracking-widest text-[11px] uppercase">3. Natureza dos Relatórios</h2>
            <p>
              Os relatórios e vereditos emitidos pela plataforma têm caráter informativo e preventivo para conscientização sobre fraudes e fake news.
            </p>
          </section>
        </div>
      </div>
      <Footer />
    </div>
  );
}
