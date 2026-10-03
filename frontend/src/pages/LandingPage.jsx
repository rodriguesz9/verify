import { useId, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, ShieldCheck, MessageCircle, Search, FileText, Link2, Image, AudioLines, Video, TriangleAlert, HeartHandshake, LockKeyhole, ChevronDown, Check } from "lucide-react";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import EasyModeButton from "../components/EasyModeButton";
import MessageExample from "../components/MessageExample";
import Reveal from "../components/Reveal";
import "./landing.css";

const STEPS = [
  { icon: MessageCircle, title: "Envie o que recebeu", text: "Cole uma mensagem ou um link. Você também pode enviar uma imagem, um áudio ou um vídeo." },
  { icon: Search, title: "Veja os sinais e as fontes", text: "O Verify procura evidências disponíveis e informa quais verificações conseguiu realizar." },
  { icon: ShieldCheck, title: "Decida com mais cuidado", text: "Leia a explicação e os próximos passos. Se faltar informação, o resultado será inconclusivo." },
];
const PROTECTION = [
  { icon: TriangleAlert, title: "Mensagens que pedem dinheiro", text: "Pressa, ameaças e taxas inesperadas merecem atenção. Confirme com a instituição por um canal oficial." },
  { icon: Search, title: "Notícias fora de contexto", text: "Uma publicação antiga pode circular como nova. Consulte a data, a origem e as checagens encontradas." },
  { icon: HeartHandshake, title: "Conteúdo que parece real", text: "Imagens e vozes podem ser alteradas. Os detectores ajudam a encontrar indícios, mas também podem errar." },
];
const QUESTIONS = [
  ["Preciso entender de tecnologia?", "Não. Comece pelo botão “Começar agora” e escolha o tipo de conteúdo. O Modo Fácil aumenta as letras, mantém botões grandes e desliga animações decorativas."],
  ["O Verify sempre sabe se algo é falso?", "Não. Nenhum detector acerta sempre. Uma checagem pode ser parcial ou inconclusiva. O relatório explica as evidências, as limitações e as verificações que não puderam ser realizadas."],
  ["Posso analisar um vídeo inteiro?", "O sistema examina quadros amostrados e, quando disponível, a faixa de áudio. Isso não equivale a examinar todos os instantes do vídeo e não garante encontrar toda alteração."],
  ["Os arquivos são enviados para outras empresas?", "Algumas análises usam fornecedores externos. Evite enviar documentos, fotos ou áudios com dados pessoais sensíveis. Consulte a Política de Privacidade antes de usar."],
  ["O que faço quando não há uma conclusão?", "Não trate a ausência de evidências como prova de verdade. Procure a fonte original ou peça ajuda a alguém de confiança antes de pagar, enviar dados ou compartilhar."],
];

function Question({ question, answer, open, onToggle }) {
  const id = useId();
  return <div className="landing-question"><h3><button type="button" aria-expanded={open} aria-controls={id} onClick={onToggle}>{question}<ChevronDown size={23} aria-hidden="true" /></button></h3><p id={id} hidden={!open}>{answer}</p></div>;
}

export default function LandingPage() {
  const [openQuestion, setOpenQuestion] = useState(null);
  return (
    <div className="landing-shell">
      <Navbar variant="landing" />
      <main>
        <section className="landing-hero landing-container" aria-labelledby="landing-title">
          <Reveal className="landing-hero-copy">
            <p className="landing-eyebrow"><ShieldCheck size={20} aria-hidden="true" /> Mais calma. Mais informação.</p>
            <h1 id="landing-title">Antes de compartilhar,<br /><span>vale a pena checar.</span></h1>
            <p className="landing-lead">Recebeu uma mensagem suspeita? O Verify ajuda você a entender os sinais de risco e encontrar evidências, com uma explicação simples.</p>
            <div className="landing-actions"><Link className="landing-primary" to="/app">Começar agora <ArrowRight size={22} aria-hidden="true" /></Link><Link className="landing-secondary" to="/demo">Ver demonstração</Link></div>
            <div className="landing-easy-hint"><EasyModeButton /><p>Prefere letras maiores e menos movimento? Ative o Modo Fácil.</p></div>
            <p className="landing-honest"><Check size={19} aria-hidden="true" /> Sem certeza inventada: se faltar evidência, a gente informa.</p>
          </Reveal>
          <Reveal className="landing-hero-example" delay={100}><MessageExample /></Reveal>
        </section>

        <div className="landing-container"><div className="landing-formats" aria-label="Tipos de conteúdo aceitos"><p>Checar o que chega até você</p><ul>{[[FileText, "Textos"], [Link2, "Links"], [Image, "Imagens"], [AudioLines, "Áudios"], [Video, "Vídeos"]].map(([Icon, label]) => <li key={label}><Icon size={22} aria-hidden="true" />{label}</li>)}</ul></div></div>

        <section id="como-funciona" className="landing-section landing-container" aria-labelledby="how-title">
          <Reveal className="landing-section-heading"><p className="landing-eyebrow">Um passo de cada vez</p><h2 id="how-title">Checar pode ser simples.</h2><p>Você não precisa interpretar gráficos complicados. Comece pelo conteúdo que recebeu.</p></Reveal>
          <div className="landing-card-grid">{STEPS.map(({ icon: Icon, title, text }, index) => <Reveal as="article" className="landing-step" delay={index * 70} key={title}><div className="landing-step-top"><span className="landing-icon"><Icon size={26} aria-hidden="true" /></span><span className="landing-step-number">0{index + 1}</span></div><h3>{title}</h3><p>{text}</p></Reveal>)}</div>
        </section>

        <section id="protege" className="landing-protection" aria-labelledby="protection-title"><div className="landing-container landing-section">
          <Reveal className="landing-section-heading"><p className="landing-eyebrow">Cuidado no dia a dia</p><h2 id="protection-title">Uma segunda olhada faz diferença.</h2><p>Há mensagens que parecem urgentes e conteúdos que parecem verdadeiros. Pare um momento antes de agir.</p></Reveal>
          <div className="landing-card-grid">{PROTECTION.map(({ icon: Icon, title, text }, index) => <Reveal as="article" className="landing-protection-card" delay={index * 70} key={title}><Icon size={28} aria-hidden="true" /><h3>{title}</h3><p>{text}</p></Reveal>)}</div>
          <Reveal className="landing-limit-note"><ShieldCheck size={26} aria-hidden="true" /><div><h3>Indícios não são uma prova definitiva.</h3><p>Um conteúdo feito com IA não é necessariamente uma mentira. E uma foto real pode acompanhar uma afirmação falsa.</p><Link to="/limitacoes">Conheça os limites das verificações <ArrowRight size={19} aria-hidden="true" /></Link></div></Reveal>
        </div></section>

        <section className="landing-section landing-container landing-privacy" aria-labelledby="privacy-title">
          <Reveal><p className="landing-eyebrow"><LockKeyhole size={20} aria-hidden="true" /> Você merece clareza</p><h2 id="privacy-title">Proteja também seus dados.</h2><p className="landing-lead">Envie apenas o necessário para checar. Não compartilhe senhas, códigos de acesso ou documentos pessoais.</p><Link className="landing-text-link" to="/privacy">Leia nossa Política de Privacidade <ArrowRight size={20} aria-hidden="true" /></Link></Reveal>
          <Reveal className="landing-privacy-note"><h3>Na dúvida, confirme fora da mensagem.</h3><p>Abra o aplicativo oficial ou procure o telefone da instituição por conta própria. Não use um contato enviado na mensagem suspeita.</p><p>Para assuntos de saúde, dinheiro ou segurança, procure também uma pessoa ou profissional de confiança.</p></Reveal>
        </section>

        <section className="landing-section landing-container landing-faq" aria-labelledby="faq-title"><Reveal className="landing-section-heading"><p className="landing-eyebrow">Sem complicação</p><h2 id="faq-title">Dúvidas comuns.</h2></Reveal><div>{QUESTIONS.map(([question, answer], index) => <Question key={question} question={question} answer={answer} open={openQuestion === index} onToggle={() => setOpenQuestion(openQuestion === index ? null : index)} />)}</div></section>

        <section className="landing-container landing-final"><Reveal><ShieldCheck size={35} aria-hidden="true" /><h2>Uma pausa antes de agir.<br />Um cuidado a mais com você.</h2><p>Comece com uma mensagem, um link ou um arquivo.</p><Link className="landing-primary" to="/app">Quero checar um conteúdo <ArrowRight size={22} aria-hidden="true" /></Link></Reveal></section>
      </main>
      <Footer />
    </div>
  );
}
