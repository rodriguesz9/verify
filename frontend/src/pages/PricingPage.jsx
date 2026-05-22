import Footer from "../components/Footer";
import { Link } from "react-router-dom";

function PricingCard({ tier, price, desc, features, highlighted, cta }) {
  return (
    <div className={`p-10 rounded-[2.5rem] border transition-all duration-500 flex flex-col h-full ${highlighted ? 'bg-[#0F1E2E] border-[#00D4FF44] shadow-[0_30px_70px_rgba(0,212,255,0.15)] scale-105 z-10' : 'bg-[#0A1520] border-[#132435]'}`}>
      <div className="mb-10">
        <span className="font-mono text-[10px] tracking-[5px] text-[#3A6070] uppercase block mb-4 font-bold">{tier}</span>
        <div className="flex items-baseline gap-1 mb-4">
          <span className="font-syne font-black text-6xl text-[#CDE8F0]">R${price}</span>
          <span className="font-mono text-[14px] text-[#1A3A50] font-bold">/mês</span>
        </div>
        <p className="font-mono text-[11px] text-[#3A6070] uppercase font-bold tracking-wider leading-relaxed">{desc}</p>
      </div>
      
      <ul className="space-y-4 mb-12 flex-1">
        {features.map((f, i) => (
          <li key={i} className="flex items-center gap-4 font-mono text-[13px] text-[#CDE8F0] list-none">
            <span className="text-[#00D4FF] text-lg">✓</span> {f}
          </li>
        ))}
      </ul>

      <Link to="/register" className={`block text-center py-6 rounded-2xl font-syne font-black text-[13px] tracking-[4px] transition-all no-underline shadow-lg ${highlighted ? 'bg-gradient-to-r from-[#00D4FF] to-[#00FF87] text-[#04080C]' : 'border-2 border-[#132435] text-[#CDE8F0] hover:bg-white/5 uppercase'}`}>
        {cta || "COMEÇAR AGORA"}
      </Link>
    </div>
  );
}

export default function PricingPage() {
  return (
    <div className="relative min-h-screen pb-20">
      <div className="fixed inset-0 pointer-events-none opacity-5"
        style={{
          backgroundImage: "radial-gradient(circle at 2px 2px, #00D4FF 1.5px, transparent 0)",
          backgroundSize: "40px 40px",
        }}/>

      <div className="relative z-10 max-w-6xl mx-auto px-6 pt-20">
        <div className="text-center mb-24">
          <span className="font-mono text-[11px] tracking-[6px] text-[#00D4FF] uppercase mb-4 block font-bold">Planos de Proteção</span>
          <h1 className="font-syne font-black text-5xl md:text-7xl text-[#CDE8F0] uppercase tracking-tighter mb-8 italic">
            Escolha sua <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#00D4FF] to-[#00FF87]">Segurança</span>.
          </h1>
          <p className="font-mono text-[16px] text-[#3A6070] uppercase tracking-widest max-w-2xl mx-auto font-bold leading-relaxed">
            Temos o plano ideal para você, sua família ou sua empresa. Proteja-se contra a mentira digital hoje mesmo.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-10 items-stretch">
          <PricingCard 
            tier="Básico" 
            price="0" 
            desc="Para quem quer começar a se proteger e checar notícias do dia a dia."
            features={[
              "3 verificações por dia",
              "Relatórios simplificados",
              "Busca em bases públicas",
              "Acesso pelo celular"
            ]}
          />
          <PricingCard 
            highlighted
            tier="Protetor" 
            price="49" 
            desc="O plano favorito. Verificações ilimitadas e proteção avançada contra golpes."
            features={[
              "Verificações Ilimitadas",
              "Prioridade nas buscas",
              "Detecção de Deepfakes",
              "Suporte especializado 24h",
              "Relatórios detalhados"
            ]}
            cta="RECOMENDADO"
          />
          <PricingCard 
            tier="Família" 
            price="149" 
            desc="Proteja quem você ama. Plano para até 5 pessoas com gestão centralizada."
            features={[
              "Tudo do plano Protetor",
              "Até 5 usuários inclusos",
              "Dashboard familiar",
              "Treinamento anti-golpe",
              "Alertas de segurança via SMS"
            ]}
          />
        </div>

        <div className="mt-32 p-12 rounded-[3.5rem] bg-[#0A1520] border border-[#132435] text-center shadow-2xl">
          <h2 className="font-syne font-black text-3xl text-[#CDE8F0] mb-6 uppercase italic tracking-tighter">Precisa de algo maior?</h2>
          <p className="font-mono text-[14px] text-[#3A6070] mb-10 max-w-xl mx-auto font-bold uppercase tracking-widest">
            Oferecemos planos corporativos para empresas, auditores e agências de notícias.
          </p>
          <a href="mailto:contato@verify.ia" className="font-syne font-bold text-[12px] tracking-[4px] text-[#00D4FF] border border-[#00D4FF44] px-10 py-4 rounded-2xl hover:bg-[#00D4FF] hover:text-[#04080C] transition-all no-underline">
            FALAR COM ESPECIALISTA
          </a>
        </div>
      </div>
      <Footer />
    </div>
  );
}
