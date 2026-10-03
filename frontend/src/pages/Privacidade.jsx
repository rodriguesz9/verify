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
            <h2 className="text-cyan mb-3 tracking-widest text-[11px] uppercase">2. Processamento e Armazenamento</h2>
            <p>
               As camadas habilitadas podem enviar textos, imagens, quadros de vídeo ou áudio a provedores externos,
               como Google, OpenRouter e seus fornecedores de modelos, Sightengine, Hive, Hugging Face e AssemblyAI.
               As regras de retenção desses serviços também se aplicam. Ofertas gratuitas podem permitir uso
               do conteúdo para melhoria de modelos; não são uma garantia de processamento privado.
               O histórico pode armazenar o conteúdo consultado e o relatório; o registro de integridade usa SHA-256.
               Evite enviar senhas, documentos pessoais, dados bancários e mídias privadas de terceiros.
            </p>
          </section>

          <section>
            <h2 className="text-cyan mb-3 tracking-widest text-[11px] uppercase">3. Direitos do Titular</h2>
            <p>
              A exclusão automática de conta e histórico ainda não está disponível nesta versão. O responsável pela
              aplicação deve disponibilizar um canal de contato e uma política de retenção antes de oferecer o serviço em produção.
            </p>
          </section>
        </div>
      </div>
      <Footer />
    </div>
  );
}
