import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import Footer from "../components/Footer";

/* ── Animated hex canvas ──────────────────────────────────────────────────── */
function HexCanvas() {
  const ref = useRef(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let raf;
    let t = 0;

    const resize = () => {
      canvas.width  = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const hexPath = (x, y, r) => {
      ctx.beginPath();
      for (let i = 0; i < 6; i++) {
        const a = (Math.PI / 3) * i - Math.PI / 6;
        const px = x + r * Math.cos(a);
        const py = y + r * Math.sin(a);
        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
      }
      ctx.closePath();
    };

    const ORBS = [
      { x: 0.72, y: 0.32, r: 120, color: "#00D4FF", speed: 0.4 },
      { x: 0.80, y: 0.65, r:  80, color: "#00FF87", speed: 0.6 },
      { x: 0.62, y: 0.55, r:  50, color: "#00D4FF", speed: 0.9 },
    ];

    const HEXES = [
      { x: 0.68, y: 0.25, r: 90,  rot: 0,   speed: 0.2  },
      { x: 0.82, y: 0.50, r: 60,  rot: 0.5, speed: -0.3 },
      { x: 0.58, y: 0.70, r: 45,  rot: 1,   speed: 0.4  },
      { x: 0.76, y: 0.78, r: 35,  rot: 0.2, speed: -0.5 },
      { x: 0.90, y: 0.30, r: 28,  rot: 0.8, speed: 0.7  },
    ];

    const draw = () => {
      const W = canvas.width, H = canvas.height;
      ctx.clearRect(0, 0, W, H);

      // Glowing orbs
      ORBS.forEach(o => {
        const ox = o.x * W + Math.sin(t * o.speed) * 18;
        const oy = o.y * H + Math.cos(t * o.speed * 0.7) * 12;
        const grad = ctx.createRadialGradient(ox, oy, 0, ox, oy, o.r);
        grad.addColorStop(0,   o.color + "28");
        grad.addColorStop(0.5, o.color + "10");
        grad.addColorStop(1,   "transparent");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(ox, oy, o.r, 0, Math.PI * 2);
        ctx.fill();
      });

      // Hexagons
      HEXES.forEach((h, i) => {
        const hx = h.x * W + Math.sin(t * h.speed + i) * 10;
        const hy = h.y * H + Math.cos(t * h.speed * 0.8 + i) * 8;
        ctx.save();
        ctx.translate(hx, hy);
        ctx.rotate(h.rot + t * h.speed * 0.2);

        // outer
        hexPath(0, 0, h.r);
        ctx.strokeStyle = (i % 2 === 0 ? "#00D4FF" : "#00FF87") + "55";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // inner
        hexPath(0, 0, h.r * 0.6);
        ctx.strokeStyle = (i % 2 === 0 ? "#00D4FF" : "#00FF87") + "30";
        ctx.lineWidth = 1;
        ctx.stroke();

        // center dot
        ctx.beginPath();
        ctx.arc(0, 0, 3, 0, Math.PI * 2);
        ctx.fillStyle = (i % 2 === 0 ? "#00D4FF" : "#00FF87") + "88";
        ctx.fill();

        ctx.restore();
      });

      // Connecting lines between hexes
      ctx.strokeStyle = "#00D4FF18";
      ctx.lineWidth = 0.8;
      for (let i = 0; i < HEXES.length - 1; i++) {
        const a = HEXES[i], b = HEXES[i + 1];
        ctx.beginPath();
        ctx.moveTo(a.x * W + Math.sin(t * a.speed + i) * 10, a.y * H + Math.cos(t * a.speed * 0.8 + i) * 8);
        ctx.lineTo(b.x * W + Math.sin(t * b.speed + i + 1) * 10, b.y * H + Math.cos(t * b.speed * 0.8 + i + 1) * 8);
        ctx.stroke();
      }

      t += 0.006;
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", resize); };
  }, []);

  return <canvas ref={ref} className="absolute inset-0 w-full h-full pointer-events-none" />;
}

/* ── Feature card ─────────────────────────────────────────────────────────── */
function FeatureCard({ num, title, desc, color = "#00D4FF", delay = 0 }) {
  return (
    <div className={`fade-${delay + 1} rounded-xl p-6 transition-all group`}
      style={{
        background: "#0A1520",
        border: "1px solid #132435",
        cursor: "default",
      }}
      onMouseOver={e => e.currentTarget.style.borderColor = color + "66"}
      onMouseOut={e => e.currentTarget.style.borderColor = "#132435"}
    >
      <div className="flex items-center gap-3 mb-4">
        <span className="font-mono text-[10px] tracking-widest px-2.5 py-1 rounded"
          style={{ background: color + "18", border: `1px solid ${color}44`, color }}>
          0{num}
        </span>
        <div className="h-px flex-1" style={{ background: `linear-gradient(90deg, ${color}44, transparent)` }} />
      </div>
      <h3 className="font-syne font-bold text-[16px] mb-2 text-text">{title}</h3>
      <p className="font-mono text-[11px] leading-relaxed" style={{ color: "#3A6070" }}>{desc}</p>
    </div>
  );
}

/* ── Step card ────────────────────────────────────────────────────────────── */
function StepCard({ num, title, desc, icon }) {
  return (
    <div className="flex flex-col items-center text-center px-4">
      <div className="relative mb-5">
        <div className="w-14 h-14 rounded-full flex items-center justify-center text-2xl"
          style={{ background: "rgba(0,212,255,.1)", border: "1px solid rgba(0,212,255,.3)" }}>
          {icon}
        </div>
        <span className="absolute -top-1 -right-1 font-mono text-[9px] font-bold w-5 h-5 rounded-full flex items-center justify-center"
          style={{ background: "#00D4FF", color: "#04080C" }}>
          {num}
        </span>
      </div>
      <h4 className="font-syne font-bold text-[15px] mb-2 text-text">{title}</h4>
      <p className="font-mono text-[11px] leading-relaxed" style={{ color: "#3A6070" }}>{desc}</p>
    </div>
  );
}

/* ── Stat pill ────────────────────────────────────────────────────────────── */
function Stat({ value, label, color }) {
  return (
    <div className="text-center">
      <div className="font-syne font-extrabold text-4xl mb-1" style={{ color }}>{value}</div>
      <div className="font-mono text-[10px] tracking-widest" style={{ color: "#3A6070" }}>{label}</div>
    </div>
  );
}

/* ── Main component ───────────────────────────────────────────────────────── */
export default function LandingPage() {
  return (
    <div style={{ background: "#04080C", minHeight: "100vh" }}>

      {/* ── NAVBAR (standalone, no auth links) ─────────────────────────────── */}
      <nav className="sticky top-0 z-50 border-b border-border backdrop-blur-md"
        style={{ background: "rgba(4,8,12,0.92)" }}>
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between h-14">
          <div className="flex items-center gap-2.5">
            <svg width="24" height="24" viewBox="0 0 28 28">
              <polygon points="14,2 26,8 26,20 14,26 2,20 2,8" fill="none" stroke="#00D4FF" strokeWidth="1.5" />
              <circle cx="14" cy="14" r="3" fill="#00D4FF" />
            </svg>
            <span className="font-syne font-extrabold text-base tracking-widest text-text">
              VERIF<span style={{ color: "#00D4FF" }}>AI</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Link to="/login"
              className="font-mono text-[10px] tracking-widest px-4 py-1.5 rounded-md"
              style={{ color: "#3A6070", border: "1px solid #132435", textDecoration: "none" }}>
              ENTRAR
            </Link>
            <Link to="/register"
              className="font-mono text-[10px] tracking-widest px-5 py-1.5 rounded-md font-bold"
              style={{ background: "linear-gradient(135deg,#00D4FF,#00FF87)", color: "#04080C", textDecoration: "none" }}>
              COMEÇAR GRÁTIS
            </Link>
          </div>
        </div>
      </nav>

      {/* ── HERO ───────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden" style={{ minHeight: "92vh", display: "flex", alignItems: "center" }}>
        {/* grid bg */}
        <div className="absolute inset-0"
          style={{
            backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)",
            backgroundSize: "48px 48px", opacity: .35,
          }} />
        {/* radial glow bottom-left */}
        <div className="absolute inset-0"
          style={{ background: "radial-gradient(ellipse 55% 60% at 15% 80%, rgba(0,212,255,.07), transparent)" }} />

        {/* canvas right side */}
        <div className="absolute inset-0">
          <HexCanvas />
        </div>

        {/* scanline */}
        <div className="absolute left-0 right-0 anim-scanline pointer-events-none"
          style={{ height: "8%", background: "linear-gradient(180deg,transparent,rgba(0,212,255,.05),transparent)" }} />

        <div className="relative z-10 max-w-6xl mx-auto px-6 py-24 grid gap-6"
          style={{ gridTemplateColumns: "1fr 1fr", alignItems: "center" }}>

          {/* left – text */}
          <div>
            <div className="flex items-center gap-2 mb-6 fade-1">
              <span className="w-2 h-2 rounded-full anim-blink" style={{ background: "#00FF87" }} />
              <span className="font-mono text-[10px] tracking-[3px]" style={{ color: "#00FF87" }}>
                SISTEMA ONLINE · MARÇO 2026
              </span>
            </div>

            <h1 className="font-syne font-extrabold leading-none mb-6 fade-2"
              style={{ fontSize: "clamp(38px,4.5vw,66px)" }}>
              <span style={{ color: "#CDE8F0" }}>A verdade</span>
              <br />
              <span style={{
                background: "linear-gradient(135deg, #00D4FF 0%, #00FF87 60%)",
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
              }}>não espera.</span>
              <br />
              <span style={{ color: "#CDE8F0" }}>Verifique agora.</span>
            </h1>

            <p className="font-mono text-[13px] leading-relaxed mb-8 fade-3" style={{ color: "#3A6070", maxWidth: 440 }}>
              VerifAI analisa textos, URLs e imagens em <strong style={{ color: "#CDE8F0" }}>3 camadas simultâneas</strong>:
              agências de checagem, reputação de domínio e análise semântica por IA —
              tudo em segundos.
            </p>

            <div className="flex gap-3 mb-10 fade-4">
              <Link to="/register"
                className="font-syne font-bold text-[13px] tracking-widest px-7 py-3.5 rounded-xl"
                style={{
                  background: "linear-gradient(135deg,#00D4FF,#00FF87)",
                  color: "#04080C", textDecoration: "none",
                  boxShadow: "0 0 32px rgba(0,212,255,.4)",
                }}>
                COMEÇAR GRÁTIS →
              </Link>
              <a href="#how"
                className="font-mono text-[12px] tracking-widest px-7 py-3.5 rounded-xl"
                style={{
                  color: "#3A6070", textDecoration: "none",
                  border: "1px solid #132435",
                }}>
                Ver como funciona
              </a>
            </div>

            {/* mini stats */}
            <div className="flex gap-8 fade-5">
              <Stat value="3"    label="CAMADAS DE ANÁLISE"  color="#00D4FF" />
              <Stat value="2.5"  label="GEMINI FLASH"        color="#00FF87" />
              <Stat value="100%" label="GRATUITO PARA COMEÇAR" color="#FFB830" />
            </div>
          </div>

          {/* right – visual box */}
          <div className="flex justify-center fade-3">
            <div className="relative w-full max-w-xs">
              {/* mock result card floating */}
              <div className="rounded-2xl p-6"
                style={{
                  background: "rgba(10,21,32,0.85)",
                  border: "1px solid rgba(0,212,255,.25)",
                  backdropFilter: "blur(12px)",
                  boxShadow: "0 0 60px rgba(0,212,255,.15), 0 40px 80px rgba(0,0,0,.6)",
                }}>
                {/* top bar */}
                <div className="flex items-center gap-2 mb-5">
                  <div className="w-2 h-2 rounded-full" style={{ background: "#FF3B5C" }} />
                  <div className="w-2 h-2 rounded-full" style={{ background: "#FFB830" }} />
                  <div className="w-2 h-2 rounded-full" style={{ background: "#00FF87" }} />
                  <span className="font-mono text-[9px] ml-2" style={{ color: "#1A3A50" }}>
                    verifai.app · análise
                  </span>
                </div>

                {/* fake gauge */}
                <div className="flex items-center gap-4 mb-5">
                  <svg width="80" height="80" viewBox="0 0 80 80">
                    <circle cx="40" cy="40" r="30" fill="none" stroke="#132435" strokeWidth="7" />
                    <circle cx="40" cy="40" r="30" fill="none" stroke="#00FF87" strokeWidth="7"
                      strokeLinecap="round"
                      strokeDasharray={`${2 * Math.PI * 30}`}
                      strokeDashoffset={`${2 * Math.PI * 30 * 0.18}`}
                      transform="rotate(-90 40 40)" />
                    <text x="40" y="44" textAnchor="middle" fill="#00FF87" fontSize="16" fontWeight="800" fontFamily="Syne">82</text>
                  </svg>
                  <div>
                    <div className="font-syne font-extrabold text-lg text-text">CONFIÁVEL</div>
                    <div className="font-mono text-[10px]" style={{ color: "#3A6070" }}>Score geral / 100</div>
                  </div>
                </div>

                {/* fake bars */}
                {[["SEMÂNTICA", 78, "#00D4FF"], ["REPUTAÇÃO", 88, "#00FF87"], ["ANTI-SENS.", 82, "#FFB830"]].map(([label, val, col]) => (
                  <div key={label} className="mb-3">
                    <div className="flex justify-between mb-1">
                      <span className="font-mono text-[9px] tracking-widest" style={{ color: "#3A6070" }}>{label}</span>
                      <span className="font-mono text-[9px]" style={{ color: col }}>{val}</span>
                    </div>
                    <div className="h-1 rounded-full overflow-hidden" style={{ background: "#132435" }}>
                      <div className="h-full rounded-full"
                        style={{ width: `${val}%`, background: col, boxShadow: `0 0 6px ${col}` }} />
                    </div>
                  </div>
                ))}

                {/* fake tags */}
                <div className="flex gap-2 mt-4 flex-wrap">
                  <span className="font-mono text-[9px] px-2 py-1 rounded"
                    style={{ background: "rgba(0,255,135,.1)", color: "#00FF87", border: "1px solid rgba(0,255,135,.2)" }}>
                    ✓ Fonte verificada
                  </span>
                  <span className="font-mono text-[9px] px-2 py-1 rounded"
                    style={{ background: "rgba(0,212,255,.1)", color: "#00D4FF", border: "1px solid rgba(0,212,255,.2)" }}>
                    ⬡ AosFatos · Lupa
                  </span>
                </div>
              </div>

              {/* floating badge */}
              <div className="absolute -top-4 -right-4 font-mono text-[9px] tracking-widest px-3 py-1.5 rounded-full"
                style={{
                  background: "#00D4FF", color: "#04080C", fontWeight: 700,
                  boxShadow: "0 0 20px rgba(0,212,255,.5)",
                }}>
                GEMINI 2.5 FLASH
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── FEATURES ───────────────────────────────────────────────────────── */}
      <section className="relative py-24 border-t" style={{ borderColor: "#132435" }}>
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-14">
            <span className="font-mono text-[10px] tracking-[3px] px-4 py-1.5 rounded-full inline-block mb-4"
              style={{ background: "rgba(0,212,255,.08)", border: "1px solid rgba(0,212,255,.2)", color: "#00D4FF" }}>
              DIFERENCIAIS
            </span>
            <h2 className="font-syne font-extrabold text-text mb-3"
              style={{ fontSize: "clamp(26px,4vw,42px)" }}>
              Mais que um detector.<br />
              <span style={{
                background: "linear-gradient(135deg,#00D4FF,#00FF87)",
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
              }}>Um tribunal técnico.</span>
            </h2>
            <p className="font-mono text-[12px]" style={{ color: "#3A6070" }}>
              Cada análise gera um laudo explicável com evidências — não apenas uma nota.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <FeatureCard num={1}
              title="Análise Multimodal"
              desc="Verifica textos, URLs e imagens. Para uploads, cruza a análise do Gemini Vision com a Hive Moderation API para detectar deepfakes e conteúdo gerado por IA."
              color="#00D4FF" delay={1} />
            <FeatureCard num={2}
              title="XAI — Score Explicável"
              desc="Não damos apenas uma nota. Decompomos o resultado em Semântica, Reputação de Fonte e Sensacionalismo, com alertas e falácias lógicas identificadas."
              color="#00FF87" delay={2} />
            <FeatureCard num={3}
              title="Verificação em Tempo Real"
              desc="Consultamos a Google Fact Check Explorer API ao vivo. Se agências como Lupa, AosFatos ou Reuters já verificaram, o resultado aparece imediatamente."
              color="#FFB830" delay={3} />
            <FeatureCard num={4}
              title="Histórico Persistido"
              desc="Cada análise é salva no seu histórico com score, veredicto e relatório completo. Consulte, compare e compartilhe resultados anteriores."
              color="#00D4FF" delay={4} />
          </div>

          {/* wide card */}
          <div className="rounded-xl p-7 flex items-center gap-8"
            style={{ background: "#0A1520", border: "1px solid rgba(0,212,255,.2)", borderLeft: "4px solid #00D4FF" }}>
            <div className="shrink-0 w-14 h-14 rounded-full flex items-center justify-center text-2xl"
              style={{ background: "rgba(0,212,255,.1)", border: "1px solid rgba(0,212,255,.25)" }}>
              🛡
            </div>
            <div>
              <h3 className="font-syne font-bold text-[16px] text-text mb-1">
                Segurança Máxima — Argon2 + JWT + Rate Limit
              </h3>
              <p className="font-mono text-[11px] leading-relaxed" style={{ color: "#3A6070" }}>
                Senhas com hash Argon2 (OWASP), tokens JWT com rotação automática, proteção contra XSS via Bleach,
                queries parametrizadas (zero SQL Injection) e bloqueio por IP após 5 tentativas de login.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ───────────────────────────────────────────────────── */}
      <section id="how" className="relative py-24 border-t" style={{ borderColor: "#132435" }}>
        <div className="absolute inset-0"
          style={{ background: "radial-gradient(ellipse 70% 50% at 50% 50%, rgba(0,212,255,.04), transparent)" }} />

        <div className="relative z-10 max-w-5xl mx-auto px-6">
          <div className="text-center mb-16">
            <span className="font-mono text-[10px] tracking-[3px] px-4 py-1.5 rounded-full inline-block mb-4"
              style={{ background: "rgba(0,255,135,.08)", border: "1px solid rgba(0,255,135,.2)", color: "#00FF87" }}>
              COMO FUNCIONA
            </span>
            <h2 className="font-syne font-extrabold text-text"
              style={{ fontSize: "clamp(24px,4vw,40px)" }}>
              Pipeline de 3 camadas em segundos
            </h2>
          </div>

          <div className="grid grid-cols-3 gap-8 relative">
            {/* connector line */}
            <div className="absolute top-7 left-[20%] right-[20%] h-px"
              style={{ background: "linear-gradient(90deg, transparent, #00D4FF44, #00FF8744, transparent)" }} />

            <StepCard num="1" icon="⬡"
              title="Cole o conteúdo"
              desc="Texto, URL ou upload de imagem/áudio. O sistema aceita até 5.000 caracteres de texto ou 10MB de arquivo." />
            <StepCard num="2" icon="◈"
              title="3 camadas analisam"
              desc="Fact Check API, verificação de domínio e Gemini 2.5 Flash rodam em paralelo enquanto você vê o progresso." />
            <StepCard num="3" icon="◎"
              title="Laudo explicável"
              desc="Score 0–100 decomposto, alertas, falácias, fontes recomendadas e detecção de deepfake no relatório completo." />
          </div>

          {/* pipeline visual */}
          <div className="mt-16 rounded-xl overflow-hidden border" style={{ borderColor: "#132435" }}>
            <div className="grid grid-cols-3 divide-x" style={{ borderColor: "#132435" }}>
              {[
                { label: "CAMADA 1", name: "Fact Check", icon: "⬡", col: "#00D4FF", api: "Google Fact Check API" },
                { label: "CAMADA 2", name: "Domínio",    icon: "◈", col: "#00FF87", api: "Heurística local" },
                { label: "CAMADA 3", name: "IA Semântica", icon: "◎", col: "#FFB830", api: "Gemini 2.5 Flash" },
              ].map(c => (
                <div key={c.name} className="p-6 text-center" style={{ background: "#0A1520", borderColor: "#132435" }}>
                  <span className="text-3xl block mb-3" style={{ color: c.col }}>{c.icon}</span>
                  <span className="font-mono text-[9px] tracking-widest block mb-1" style={{ color: c.col }}>
                    {c.label}
                  </span>
                  <span className="font-syne font-bold text-[15px] text-text block mb-1">{c.name}</span>
                  <span className="font-mono text-[10px]" style={{ color: "#3A6070" }}>{c.api}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── PLANS PREVIEW ──────────────────────────────────────────────────── */}
      <section className="py-24 border-t" style={{ borderColor: "#132435" }}>
        <div className="max-w-5xl mx-auto px-6 text-center">
          <span className="font-mono text-[10px] tracking-[3px] px-4 py-1.5 rounded-full inline-block mb-5"
            style={{ background: "rgba(255,184,48,.08)", border: "1px solid rgba(255,184,48,.2)", color: "#FFB830" }}>
            PLANOS
          </span>
          <h2 className="font-syne font-extrabold text-text mb-3"
            style={{ fontSize: "clamp(24px,4vw,40px)" }}>
            Comece grátis. Escale quando precisar.
          </h2>
          <p className="font-mono text-[12px] mb-10" style={{ color: "#3A6070" }}>
            O plano Free tem 3 análises/dia — suficiente para uso pessoal e testes.
          </p>
          <div className="grid grid-cols-3 gap-4 mb-8">
            {[
              { plan: "FREE",       price: "R$0",   limit: "3/dia",    col: "#3A6070" },
              { plan: "PRO",        price: "R$29",  limit: "100/dia",  col: "#00D4FF", highlight: true },
              { plan: "ENTERPRISE", price: "R$199", limit: "Ilimitado",col: "#00FF87" },
            ].map(p => (
              <div key={p.plan} className="rounded-xl p-6"
                style={{
                  background: p.highlight ? "rgba(0,212,255,.06)" : "#0A1520",
                  border: `1px solid ${p.highlight ? "rgba(0,212,255,.35)" : "#132435"}`,
                  boxShadow: p.highlight ? "0 0 30px rgba(0,212,255,.12)" : "none",
                }}>
                <span className="font-mono text-[10px] tracking-widest block mb-3" style={{ color: p.col }}>
                  {p.plan}
                </span>
                <div className="font-syne font-extrabold text-3xl text-text mb-1">{p.price}<span className="text-base font-normal" style={{ color: "#3A6070" }}>/mês</span></div>
                <div className="font-mono text-[11px] mb-4" style={{ color: "#3A6070" }}>{p.limit}</div>
                <Link to="/register"
                  className="block text-center font-mono text-[10px] tracking-widest py-2.5 rounded-lg"
                  style={{
                    background: p.highlight ? "linear-gradient(135deg,#00D4FF,#00FF87)" : "transparent",
                    color: p.highlight ? "#04080C" : p.col,
                    border: p.highlight ? "none" : `1px solid ${p.col}44`,
                    textDecoration: "none", fontWeight: p.highlight ? 700 : 400,
                  }}>
                  {p.plan === "FREE" ? "COMEÇAR GRÁTIS" : "ASSINAR"}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ────────────────────────────────────────────────────────────── */}
      <section className="py-24 border-t relative overflow-hidden" style={{ borderColor: "#132435" }}>
        <div className="absolute inset-0"
          style={{ background: "radial-gradient(ellipse 80% 60% at 50% 50%, rgba(0,212,255,.06), rgba(0,255,135,.04), transparent)" }} />
        <div className="relative z-10 max-w-2xl mx-auto px-6 text-center">
          <h2 className="font-syne font-extrabold mb-4"
            style={{ fontSize: "clamp(28px,5vw,52px)", color: "#CDE8F0" }}>
            Pronto para auditar<br />
            <span style={{
              background: "linear-gradient(135deg,#00D4FF,#00FF87)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
            }}>a informação?</span>
          </h2>
          <p className="font-mono text-[12px] mb-8" style={{ color: "#3A6070" }}>
            Crie sua conta grátis em 30 segundos. Sem cartão de crédito.
          </p>
          <Link to="/register"
            className="inline-block font-syne font-bold text-[14px] tracking-widest px-10 py-4 rounded-xl"
            style={{
              background: "linear-gradient(135deg,#00D4FF,#00FF87)",
              color: "#04080C", textDecoration: "none",
              boxShadow: "0 0 48px rgba(0,212,255,.4)",
            }}>
            COMEÇAR AGORA — É GRÁTIS →
          </Link>
          <p className="font-mono text-[10px] mt-4" style={{ color: "#1A3A50" }}>
            3 análises/dia grátis · Sem cartão · Cancel a qualquer momento
          </p>
        </div>
      </section>

      <Footer />
    </div>
  );
}
