import Footer from "../components/Footer";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const PLANS = [
  {
    id: "FREE",
    name: "Free",
    price: "R$0",
    period: "/mês",
    color: "#3A6070",
    border: "#132435",
    badge: null,
    features: [
      { label: "3 análises de texto/URL por dia", ok: true  },
      { label: "1 análise de mídia/deepfake por dia", ok: true },
      { label: "Google Fact Check",              ok: true  },
      { label: "Análise Gemini 1.5 Flash",       ok: true  },
      { label: "Histórico (últimos 7 dias)",     ok: true  },
      { label: "Relatório de Auditoria",         ok: true  },
      { label: "Detecção Hive (mídia)",          ok: true  },
      { label: "Análise de imagens",             ok: true  },
      { label: "Análise de áudio/vídeo",         ok: true  },
      { label: "API Access",                     ok: false },
    ],
  },
  {
    id: "PRO",
    name: "Pro",
    price: "R$29",
    period: "/mês",
    color: "#00D4FF",
    border: "rgba(0,212,255,.3)",
    badge: "MAIS POPULAR",
    features: [
      { label: "100 análises por dia",           ok: true  },
      { label: "Texto, URL e Mídia ilimitado*",  ok: true  },
      { label: "Google Fact Check",              ok: true  },
      { label: "Análise Gemini 1.5 Flash",       ok: true  },
      { label: "Histórico completo",             ok: true  },
      { label: "Detecção Hive (prioritário)",    ok: true  },
      { label: "Relatórios PDF exportáveis",     ok: true  },
      { label: "Suporte prioritário",            ok: true  },
      { label: "API Access",                     ok: false },
    ],
  },
  {
    id: "ENTERPRISE",
    name: "Enterprise",
    price: "R$199",
    period: "/mês",
    color: "#00FF87",
    border: "rgba(0,255,135,.25)",
    badge: null,
    features: [
      { label: "Análises ilimitadas",            ok: true  },
      { label: "Todos os tipos de mídia",        ok: true  },
      { label: "Google Fact Check",              ok: true  },
      { label: "Análise Gemini 1.5 Flash",       ok: true  },
      { label: "Histórico completo",             ok: true  },
      { label: "Detecção Hive + Custom Models",  ok: true  },
      { label: "Relatórios Customizados",        ok: true  },
      { label: "API Access + Webhooks",          ok: true  },
      { label: "Gerente de conta dedicado",      ok: true  },
    ],
  },
];

export default function PricingPage() {
  const { user }   = useAuth();
  const navigate   = useNavigate();

  return (
    <div className="relative min-h-screen pb-24">
      <div className="pointer-events-none fixed inset-0"
        style={{
          backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)",
          backgroundSize: "48px 48px", opacity: .2,
        }}/>
      <div className="pointer-events-none fixed inset-0"
        style={{
          background: "radial-gradient(ellipse 60% 40% at 50% 0%, rgba(0,212,255,.06), transparent)",
        }}/>

      <div className="relative z-10 max-w-5xl mx-auto px-5 pt-16">
        {/* header */}
        <div className="text-center mb-14 fade-1">
          <span className="font-mono text-[10px] tracking-[3px] px-4 py-1.5 rounded-full mb-4 inline-block"
            style={{ background: "rgba(0,212,255,.1)", border: "1px solid rgba(0,212,255,.25)", color: "#00D4FF" }}>
            PLANOS E PREÇOS
          </span>
          <h1 className="font-syne font-extrabold text-text mb-3"
            style={{ fontSize: "clamp(28px,5vw,48px)" }}>
            Escolha seu plano
          </h1>
          <p className="font-mono text-[12px] leading-relaxed" style={{ color: "#3A6070" }}>
            Plano Free para começar · PRO para profissionais · Enterprise para equipes.
            <br/>O limite no Free protege os custos de processamento de IA e Deepfakes.
          </p>
        </div>

        {/* cards */}
        <div className="grid grid-cols-3 gap-5 fade-2" style={{ alignItems: "start" }}>
          {PLANS.map((plan) => {
            const isCurrent = user?.plan === plan.id;
            const isPro = plan.id === "PRO";
            return (
              <div key={plan.id} className="rounded-2xl overflow-hidden flex flex-col"
                style={{
                  background: "#0A1520",
                  border: `1px solid ${plan.border}`,
                  boxShadow: isPro ? `0 0 40px ${plan.color}18` : "none",
                  transform: isPro ? "scale(1.02)" : "none",
                }}>

                {/* badge */}
                {plan.badge ? (
                  <div className="text-center py-2 font-mono text-[9px] tracking-[3px]"
                    style={{ background: plan.color, color: "#04080C" }}>
                    {plan.badge}
                  </div>
                ) : <div className="py-2"/>}

                <div className="p-6 flex flex-col flex-1">
                  {/* plan name + price */}
                  <div className="mb-6">
                    <span className="font-mono text-[10px] tracking-widest block mb-2" style={{ color: plan.color }}>
                      {plan.id}
                    </span>
                    <div className="flex items-end gap-1">
                      <span className="font-syne font-extrabold text-4xl" style={{ color: "#CDE8F0" }}>
                        {plan.price}
                      </span>
                      <span className="font-mono text-[12px] mb-1" style={{ color: "#3A6070" }}>
                        {plan.period}
                      </span>
                    </div>
                  </div>

                  {/* features */}
                  <ul className="flex flex-col gap-2.5 flex-1 mb-6">
                    {plan.features.map((f) => (
                      <li key={f.label} className="flex items-start gap-2.5">
                        <span style={{ color: f.ok ? plan.color : "#1A3A50", fontSize: 14, lineHeight: 1.4 }}>
                          {f.ok ? "✓" : "✗"}
                        </span>
                        <span className="font-mono text-[11px] leading-relaxed"
                          style={{ color: f.ok ? "#CDE8F0" : "#1A3A50" }}>
                          {f.label}
                        </span>
                      </li>
                    ))}
                  </ul>

                  {/* CTA */}
                  {isCurrent ? (
                    <div className="text-center py-2.5 rounded-lg font-mono text-[11px] tracking-widest"
                      style={{ background: plan.color + "18", border: `1px solid ${plan.color}44`, color: plan.color }}>
                      ✓ SEU PLANO ATUAL
                    </div>
                  ) : (
                    <button
                      onClick={() => alert(`Integração de pagamento em breve! (Plano ${plan.name})`)}
                      className="w-full py-3 rounded-lg font-syne font-bold text-[12px] tracking-widest transition-all"
                      style={{
                        background: isPro ? `linear-gradient(135deg, ${plan.color}, #00FF87)` : "transparent",
                        color: isPro ? "#04080C" : plan.color,
                        border: isPro ? "none" : `1px solid ${plan.border}`,
                        cursor: "pointer",
                        boxShadow: isPro ? `0 0 20px ${plan.color}44` : "none",
                      }}>
                      {plan.id === "FREE" ? "COMEÇAR GRÁTIS →" : `ASSINAR ${plan.name.toUpperCase()} →`}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* disclaimer */}
        <p className="text-center font-mono text-[10px] mt-12 leading-relaxed fade-3" style={{ color: "#1A3A50" }}>
          Pagamentos processados de forma segura · Cancele a qualquer momento<br/>
          O limite de análises no plano Free existe para preservar o sistema contra abusos.
        </p>
      </div>
      <Footer />
    </div>
  );
}
