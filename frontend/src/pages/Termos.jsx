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
              O VerifAI fornece uma plataforma de análise probabilística de arquivos, textos e links para identificação 
              de mídias sintéticas e desinformação. O serviço processa os dados enviados com base em parâmetros matemáticos 
              fornecidos por sistemas de inteligência integrados.
            </p>
          </section>

          <section>
            <h2 className="text-cyan mb-3 tracking-widest text-[11px] uppercase">2. Responsabilidade de Uso</h2>
            <p>
              O usuário retém os direitos autorais e a total responsabilidade legal sobre os arquivos enviados à plataforma. 
              É expressamente proibido utilizar o VerifAI para processar mídias obtidas por meios ilícitos que violem 
              a privacidade de terceiros.
            </p>
          </section>

          <section>
            <h2 className="text-cyan mb-3 tracking-widest text-[11px] uppercase">3. Natureza dos Relatórios</h2>
            <p>
              Os vereditos emitidos pela plataforma são relatórios técnicos de suporte analítico e não constituem pareceres 
              jurídicos definitivos ou testemunhos periciais absolutos.
            </p>
          </section>
        </div>
      </div>
      <Footer />
    </div>
  );
}
