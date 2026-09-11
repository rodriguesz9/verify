import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import Footer from "../components/Footer";

function HexCanvas() {
  const ref = useRef(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let raf, t = 0;
    const resize = () => { canvas.width = window.innerWidth; canvas.height = window.innerHeight; };
    resize();
    window.addEventListener("resize", resize);
    const particles = Array.from({ length: 40 }, () => ({
      x: Math.random(), y: Math.random(), s: Math.random() * 0.8 + 0.2, v: Math.random() * 0.4 + 0.1
    }));
    const draw = () => {
      const W = canvas.width, H = canvas.height;
      ctx.clearRect(0, 0, W, H);
      particles.forEach(p => {
        ctx.fillStyle = "#00D4FF11";
        ctx.beginPath();
        const px = (p.x * W + t * 30 * p.v) % W;
        const py = (p.y * H + Math.sin(t + p.x) * 20) % H;
        ctx.arc(px, py, p.s * 4, 0, Math.PI * 2);
        ctx.fill();
      });
      t += 0.005;
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", resize); };
  }, []);
  return <canvas ref={ref} className="fixed inset-0 w-full h-full pointer-events-none opacity-40 z-0" />;
}

function SectionTitle({ overline, title, center }) {
  return (
    <div className={`mb-16 ${center ? 'text-center' : ''}`}>
      <span className="font-mono text-[10px] tracking-[6px] text-[#00D4FF] uppercase mb-4 block animate-fade-in">{overline}</span>
      <h2 className="font-syne font-black text-4xl md:text-6xl text-[#CDE8F0] uppercase tracking-tight leading-none">{title}</h2>
    </div>
  );
}

function FeatureCard({ title, desc, icon }) {
  return (
    <div className="group p-10 rounded-3xl bg-[#0A1520] border border-[#132435] hover:border-[#00D4FF33] transition-all duration-500 perspective-1000 shadow-xl">
      <div className="tilt-card h-full">
        <div className="text-5xl mb-6 group-hover:scale-110 transition-transform inline-block">{icon}</div>
        <h3 className="font-syne font-bold text-xl text-[#CDE8F0] mb-4 uppercase tracking-wider">{title}</h3>
        <p className="font-mono text-[13px] leading-relaxed text-[#3A6070]">{desc}</p>
      </div>
    </div>
  );
}

function StepCard({ num, title, desc }) {
  return (
    <div className="flex gap-6 items-start p-8 rounded-3xl bg-[#0A1520] border border-[#132435] hover:bg-[#0F1E2E] transition-all">
      <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-[#00D4FF] to-[#00FF87] flex items-center justify-center font-syne font-black text-[#04080C] text-xl shrink-0 shadow-lg">
        {num}
      </div>
      <div>
        <h4 className="font-syne font-bold text-lg text-[#CDE8F0] mb-2 uppercase tracking-wide">{title}</h4>
        <p className="font-mono text-[12px] text-[#3A6070] leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

function FloatingInfo({ icon, text, style }) {
  return (
    <div className="absolute hidden lg:flex items-center gap-3 px-4 py-2.5 rounded-2xl border border-white/5 bg-[#0A1520]/80 backdrop-blur-md shadow-2xl animate-float-slow z-0" style={style}>
       <span className="text-lg">{icon}</span>
       <span className="font-mono text-[10px] text-[#3A6070] tracking-widest uppercase font-bold">{text}</span>
    </div>
  );
}

function PlanCard({ tier, price, features, highlighted }) {
  const { user } = useAuth();
  return (
    <div className={`p-10 rounded-[3rem] border transition-all duration-500 flex flex-col h-full ${highlighted ? 'bg-[#0F1E2E] border-[#00D4FF44] shadow-[0_30px_70px_rgba(0,212,255,0.15)] scale-105 z-10' : 'bg-[#0A1520] border-[#132435]'}`}>
      <span className="font-mono text-[10px] tracking-[5px] text-[#3A6070] uppercase block mb-6">{tier}</span>
      <div className="flex items-baseline gap-1 mb-10">
        <span className="font-syne font-black text-6xl text-[#CDE8F0]">R${price}</span>
        <span className="font-mono text-[14px] text-[#1A3A50] font-bold">/mês</span>
      </div>
      <ul className="space-y-4 mb-12 flex-1">
        {features.map((f, i) => (
          <li key={i} className="flex items-center gap-4 font-mono text-[13px] text-[#CDE8F0] list-none">
            <span className="text-[#00D4FF] text-lg">✓</span> {f}
          </li>
        ))}
      </ul>
      <Link to={user ? "/app" : "/register"} className={`block text-center py-6 rounded-2xl font-syne font-black text-[14px] tracking-[4px] transition-all no-underline ${highlighted ? 'bg-gradient-to-r from-[#00D4FF] to-[#00FF87] text-[#04080C] shadow-lg' : 'border-2 border-[#132435] text-[#CDE8F0] hover:bg-white/5'}`}>
        {user ? "IR PARA O APP" : "ESCOLHER ESTE"}
      </Link>
    </div>
  );
}

export default function LandingPage() {
  const { user, signOut } = useAuth();

  return (
    <div className="relative" style={{ background: "#04080C", minHeight: "100vh" }}>
      <HexCanvas />
      
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-[100] border-b border-[#132435] backdrop-blur-xl bg-[rgba(4,8,12,0.8)]">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-20">
          <Link to="/" className="flex items-center gap-3 no-underline group">
             <div className="w-9 h-9 rounded-lg bg-[#00D4FF] flex items-center justify-center font-syne font-black text-[#04080C] group-hover:rotate-12 transition-transform shadow-[0_0_20px_#00D4FF66]">V</div>
             <span className="font-syne font-black text-2xl tracking-[6px] text-[#CDE8F0]">VERIFY</span>
          </Link>
          <div className="hidden md:flex items-center gap-12">
             {["O que é?", "Como funciona", "Planos", "Sobre"].map(item => (
               <a key={item} href={`#${item.toLowerCase().replace(' ', '-').replace('?', '')}`} className="font-mono text-[11px] tracking-[4px] text-[#3A6070] no-underline hover:text-[#00D4FF] uppercase transition-all">{item}</a>
             ))}
             {user ? (
               <div className="flex items-center gap-6">
                 <Link to="/app" className="font-mono text-[11px] tracking-[4px] text-white no-underline border-2 border-[#00D4FF44] px-8 py-2.5 rounded-full hover:bg-[#00D4FF22] hover:border-[#00D4FF] transition-all font-bold">IR PARA O APP</Link>
                 <button onClick={signOut} className="font-mono text-[11px] tracking-[4px] text-[#FF3B5C] no-underline border-2 border-[#FF3B5C33] px-6 py-2.5 rounded-full hover:bg-[#FF3B5C11] transition-all font-bold bg-transparent cursor-pointer">SAIR</button>
               </div>
             ) : (
               <Link to="/login" className="font-mono text-[11px] tracking-[4px] text-white no-underline border-2 border-[#132435] px-8 py-2.5 rounded-full hover:bg-white hover:text-[#04080C] hover:border-white transition-all font-bold">ENTRAR</Link>
             )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section id="o-que-é" className="relative min-h-screen flex items-center pt-32 pb-32 overflow-hidden z-10 px-6">
        <div className="max-w-7xl mx-auto w-full grid md:grid-cols-2 gap-16 items-center">
          <div className="animate-fade-in">
            <div className="inline-flex items-center gap-3 px-4 py-2 rounded-full border border-[#00D4FF33] bg-[#00D4FF0D] mb-8">
               <div className="w-2 h-2 rounded-full bg-[#00D4FF] animate-pulse shadow-[0_0_10px_#00D4FF]" />
               <span className="font-mono text-[10px] tracking-[5px] text-[#00D4FF] uppercase font-bold">A verdade ao seu alcance</span>
            </div>
            <h1 className="font-syne font-black leading-[1.1] mb-10 text-[56px] md:text-[92px] text-[#CDE8F0] uppercase tracking-tighter">
              Saiba se é <span className="text-[#00D4FF] italic transition-all hover:text-[#00FF87]">verdade</span> na hora.
            </h1>
            <p className="font-mono text-[18px] md:text-[20px] leading-relaxed mb-12 text-[#3A6070] max-w-xl">
              Não se deixe enganar. O Verify usa inteligência artificial para checar notícias, sites e fotos para você, rápido e fácil.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <Link to="/app" className="px-10 py-5 rounded-2xl bg-gradient-to-r from-[#00D4FF] to-[#00FF87] text-[#04080C] font-syne font-black text-sm tracking-[3px] shadow-[0_20px_50px_rgba(0,212,255,0.3)] hover:scale-105 active:scale-95 transition-all text-center no-underline">
                {user ? "IR PARA O APP →" : "🔍 CHECAR NOTÍCIA GRÁTIS →"}
              </Link>
              <a href="#como-funciona" className="px-8 py-5 rounded-2xl bg-[#0A1520] border border-[#132435] text-[#CDE8F0] font-mono font-bold text-xs tracking-widest hover:border-[#00D4FF] transition-all text-center no-underline flex items-center justify-center gap-2">
                <span>💬</span> Usar no WhatsApp
              </a>
            </div>
          </div>

          <div className="relative hidden md:flex justify-end p-10">
             {/* Floating Info Snippets behind the card */}
             <FloatingInfo icon="🛡️" text="Anti-Scam active" style={{ top: '0', left: '-20px', animationDelay: '0s' }} />
             <FloatingInfo icon="📸" text="Deepfake Guard" style={{ bottom: '10%', left: '-80px', animationDelay: '2s' }} />
             <FloatingInfo icon="🔍" text="Fact Check 3.1" style={{ top: '30%', right: '-40px', animationDelay: '1s' }} />
             <FloatingInfo icon="✅" text="Trusted Node" style={{ bottom: '-20px', right: '40px', animationDelay: '3s' }} />

             <div className="relative tilt-card z-10 rounded-[3rem] p-12 bg-[#0A1520] border border-white/10 backdrop-blur-3xl shadow-[0_50px_100px_rgba(0,0,0,0.5)] w-full max-w-[440px]">
                <div className="flex justify-between items-center mb-12">
                   <div className="flex gap-3">
                      <div className="w-4 h-4 rounded-full bg-[#FF3B5C] shadow-inner" />
                      <div className="w-4 h-4 rounded-full bg-[#FFB830] shadow-inner" />
                      <div className="w-4 h-4 rounded-full bg-[#00D4FF] shadow-[0_0_15px_#00D4FF]" />
                   </div>
                   <span className="font-mono text-[10px] text-[#3A6070] tracking-[8px] font-bold">VERIFY_3.1</span>
                </div>
                <div className="flex items-center gap-10 mb-14">
                   <div className="relative">
                      <svg width="120" height="120" viewBox="0 0 100 100">
                         <circle cx="50" cy="50" r="45" fill="none" stroke="#132435" strokeWidth="12" />
                         <circle cx="50" cy="50" r="45" fill="none" stroke="url(#g_v)" strokeWidth="12" strokeDasharray="230 282" strokeLinecap="round" transform="rotate(-90 50 50)" />
                         <defs><linearGradient id="g_v"><stop stopColor="#00D4FF" /><stop offset="1" stopColor="#00FF87" /></linearGradient></defs>
                      </svg>
                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                         <span className="font-syne font-black text-4xl text-[#CDE8F0]">100%</span>
                      </div>
                   </div>
                   <div>
                      <h4 className="font-syne font-black text-2xl text-[#CDE8F0] mb-2 italic uppercase underline decoration-[#00FF87] decoration-2 underline-offset-4">É Verdade!</h4>
                      <p className="font-mono text-[11px] text-[#3A6070] uppercase leading-tight tracking-wider font-bold">Informação verificada com sucesso em nossa rede global.</p>
                   </div>
                </div>
                <div className="space-y-8">
                   {[["CONFIANÇA", 95], ["FONTES", 99], ["ANÁLISE", 88]].map(([l, v]) => (
                     <div key={l}>
                        <div className="flex justify-between font-mono text-[10px] mb-3 uppercase tracking-[4px] font-bold text-[#3A6070]">
                           <span>{l}</span><span>{v}%</span>
                        </div>
                        <div className="h-2 bg-[#04080C] rounded-full overflow-hidden border border-white/5">
                           <div className="h-full bg-gradient-to-r from-[#00D4FF] to-[#00FF87] shadow-[0_0_10px_rgba(0,212,255,0.4)]" style={{ width: `${v}%` }} />
                        </div>
                     </div>
                   ))}
                </div>
             </div>
          </div>
        </div>
      </section>

      {/* How it Works Section */}
      <section id="como-funciona" className="py-40 relative border-t border-[#132435] z-10 px-6 bg-[#060C1233]">
         <div className="max-w-7xl mx-auto">
            <SectionTitle overline="Utilidade" title="O que o Verify faz por você?" />
            <div className="grid md:grid-cols-3 gap-10">
               <FeatureCard icon="🧑‍🦳" title="Fácil para idosos" desc="Não precisa ser mestre em tecnologia. Se você sabe copiar um texto, você sabe usar o Verify." />
               <FeatureCard icon="🔎" title="Busca Instantânea" desc="Nosso motor pesquisa em milhares de sites confiáveis ao mesmo tempo para te dar o resultado." />
               <FeatureCard icon="🛡️" title="Sua Segurança" desc="Seus dados estão protegidos. Nós verificamos a informação sem guardar o que você pesquisou." />
            </div>
            
            <div className="mt-20 grid md:grid-cols-2 gap-12">
               <StepCard num="1" title="Você envia" desc="Cole o texto, o link do site ou envie uma foto que você recebeu no WhatsApp." />
               <StepCard num="2" title="Nós pesquisamos" desc="Nossa inteligência artificial analisa cada detalhe em segundos." />
               <StepCard num="3" title="Você fica tranquilo" desc="Te damos uma resposta clara: É verdade ou é enganação. Simples assim." />
               <StepCard num="4" title="Proteja a Família" desc="Lute contra golpes e notícias falsas compartilhando resultados reais." />
            </div>
         </div>
      </section>

      {/* Utility / Why use it SECTION */}
      <section id="sobre" className="py-40 z-10 px-6 border-t border-[#132435]">
         <div className="max-w-7xl mx-auto grid md:grid-cols-2 gap-24 items-center">
            <div>
               <SectionTitle overline="Missão" title="Resgatando a Confiança." />
               <p className="font-mono text-[16px] leading-relaxed text-[#3A6070] mb-10">
                  Vivemos em uma era de muita informação e pouca certeza. O Verify nasceu para ser o seu escudo digital, garantindo que você tome decisões baseadas em fatos, não em mentiras.
               </p>
               <div className="grid grid-cols-1 gap-6">
                  {[
                    { t: "Proteção de Pais e Avós", d: "Criamos ferramentas pensadas em quem não nasceu na era digital." },
                    { t: "Combate a Deepfakes", d: "Identificamos fotos e vídeos criados por computador para enganar." },
                    { t: "Checagem de Saúde", d: "Verificamos boatos de saúde e remédios milagrosos antes que você arrisque." }
                  ].map(item => (
                    <div key={item.t} className="flex gap-4 p-6 rounded-2xl bg-[#0A1520] border border-[#132435] hover:border-[#00D4FF22] transition-all">
                       <span className="text-2xl text-[#00D4FF]">✓</span>
                       <div>
                          <h5 className="font-syne font-bold text-[#CDE8F0] uppercase text-[14px] mb-1 tracking-wider">{item.t}</h5>
                          <p className="font-mono text-[11px] text-[#3A6070] uppercase leading-tight">{item.d}</p>
                       </div>
                    </div>
                  ))}
               </div>
            </div>
            <div className="grid grid-cols-2 gap-6">
               {[["Checagens", "Personalizadas"], ["Precisão", "Total"], ["Rede de IA", "Global"], ["Status", "100% Online"]].map(([l, v]) => (
                 <div key={l} className="p-10 rounded-2xl border border-[#132435] text-center bg-[#010203] hover:border-cyan/30 transition-all group">
                    <div className="font-syne font-black text-2xl text-text mb-2 group-hover:scale-110 transition-transform uppercase tracking-tighter">{v}</div>
                    <div className="font-mono text-[10px] text-[#1A3A50] uppercase tracking-[4px] font-bold">{l}</div>
                 </div>
               ))}
            </div>
         </div>
      </section>

      {/* Plans Section */}
      <section id="planos" className="py-40 bg-[#060C12] border-y border-[#132435] z-10 px-6">
         <div className="max-w-7xl mx-auto">
            <SectionTitle overline="Acesso" title="Escolha como quer se proteger" center />
            <div className="grid md:grid-cols-3 gap-10">
               <PlanCard tier="Iniciante" price="0" features={["Até 3 checagens por dia", "Relatórios fáceis", "Uso no celular"]} />
               <PlanCard highlighted tier="Protetor" price="49" features={["Checagens ilimitadas", "Prioridade nas buscas", "Suporte VIP", "Deepfake Guard"]} />
               <PlanCard tier="Família" price="149" features={["Para 5 pessoas", "Controle de segurança", "Alertas automáticos", "Gestor exclusivo"]} />
            </div>
         </div>
      </section>

      <Footer />
    </div>
  );
}
