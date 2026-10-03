import { ShieldCheck, MessageCircle, TriangleAlert, Landmark, ArrowRight } from "lucide-react";

export default function MessageExample() {
  return (
    <aside className="message-example" aria-labelledby="message-example-title">
      <div className="example-heading">
        <span className="example-seal"><ShieldCheck size={26} aria-hidden="true" /></span>
        <div><p className="landing-eyebrow">Um exemplo do dia a dia</p><h2 id="message-example-title">Uma pausa pode proteger você.</h2></div>
      </div>
      <div className="example-message">
        <p><MessageCircle size={19} aria-hidden="true" /> Mensagem recebida</p>
        <blockquote>“Pague uma taxa agora para liberar seu Pix.”</blockquote>
      </div>
      <ol className="example-guidance">
        <li><span className="example-alert"><TriangleAlert size={23} aria-hidden="true" /></span><div><h3>O que merece atenção</h3><p>A mensagem pede dinheiro e pressiona você a agir. São sinais de possível golpe.</p></div></li>
        <li><span className="example-safe"><Landmark size={23} aria-hidden="true" /></span><div><h3>O próximo passo</h3><p>Não pague pela mensagem. Confirme pelo aplicativo ou telefone oficial do seu banco.</p></div></li>
      </ol>
      <a href="#como-funciona" className="example-link">Entenda como checar <ArrowRight size={20} aria-hidden="true" /></a>
      <p className="example-disclaimer">Exemplo inventado, não uma análise real. Sem evidências suficientes, o resultado será inconclusivo.</p>
    </aside>
  );
}
