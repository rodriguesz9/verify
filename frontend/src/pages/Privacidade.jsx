import Footer from "../components/Footer";

export default function Privacidade() {
  return (
    <div className="relative min-h-screen pb-20">
      <div className="pointer-events-none fixed inset-0"
        style={{
          backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)",
          backgroundSize: "48px 48px", opacity: .1,
        }}/>
      <div className="relative z-10 max-w-3xl mx-auto px-5 pt-20">
        <h1 className="font-syne font-extrabold text-3xl text-text mb-8">Política de Privacidade</h1>
        
        <div className="space-y-8 font-mono text-[13px] leading-relaxed" style={{ color: "#3A6070" }}>
          <section>
            <h2 className="text-cyan mb-3 tracking-widest text-[11px] uppercase">1. Coleta de Dados</h2>
            <p>
              O Verify coleta apenas informações essenciais para a autenticação (quando você opta por criar conta) e os dados submetidos 
              voluntariamente para checagem. Não comercializamos dados de usuários com terceiros e respeitamos sua privacidade.
            </p>
          </section>

          <section>
            <h2 className="text-cyan mb-3 tracking-widest text-[11px] uppercase">2. Armazenamento Forense</h2>
            <p>
               Para garantir a integridade do sistema e evitar abusos, mantemos registros de auditoria das submissões. 
               Os arquivos de mídia originais são processados e podem ser descartados após a geração do MD5 e do relatório correspondente.
            </p>
          </section>

          <section>
            <h2 className="text-cyan mb-3 tracking-widest text-[11px] uppercase">3. Direitos do Titular</h2>
            <p>
              Você pode solicitar a exclusão de sua conta e de todo o seu histórico de auditoria a qualquer momento através do 
              painel de configurações de conta.
            </p>
          </section>
        </div>
      </div>
      <Footer />
    </div>
  );
}
