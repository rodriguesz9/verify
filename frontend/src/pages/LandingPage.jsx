import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import Footer from "../components/Footer";
import {
  AlertTriangle,
  ArrowRight,
  BadgeCheck,
  CheckCircle2,
  FileSearch,
  Image,
  Link2,
  LogOut,
  Menu,
  MessageCircle,
  Mic,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  Volume2,
  X,
} from "lucide-react";

/* ─── Static data ─────────────────────────────────────────────────── */

const STEPS = [
  {
    number: "01",
    title: "Envie o conteúdo",
    text: "Cole uma mensagem, um link ou envie uma imagem e um áudio suspeito.",
    color: "#00D4FF",
  },
  {
    number: "02",
    title: "Veja os sinais",
    text: "O Verify aponta alertas, contexto e referências para você conferir.",
    color: "#00FF87",
  },
  {
    number: "03",
    title: "Decida com calma",
    text: "Receba uma explicação clara e uma orientação prática antes de compartilhar.",
    color: "#FFB800",
  },
];

const FEATURES = [
  {
    icon: MessageCircle,
    title: "Linguagem direta",
    text: "Sem jargão: o resultado explica o risco em palavras simples e sugere o próximo passo.",
    color: "#00D4FF",
  },
  {
    icon: ScanSearch,
    title: "Mais contexto",
    text: "A análise reúne sinais de fraude, checagens e informações de apoio.",
    color: "#00FF87",
  },
  {
    icon: ShieldCheck,
    title: "Proteção compartilhável",
    text: "Transforme a orientação em uma mensagem simples para proteger sua família.",
    color: "#FFB800",
  },
];

const MEDIA_TYPES = [
  { icon: MessageCircle, label: "Mensagens" },
  { icon: Link2, label: "Links" },
  { icon: Image, label: "Imagens" },
  { icon: Mic, label: "Áudios" },
];

/* ─── Sub-components ──────────────────────────────────────────────── */

function SignalCard({ icon: Icon, label, value, tone = "cyan" }) {
  const colors =
    tone === "red"
      ? "border-[#FF3B5C]/35 bg-[#FF3B5C]/10 text-[#FF9CAF]"
      : tone === "green"
      ? "border-[#00FF87]/35 bg-[#00FF87]/10 text-[#6DFFB4]"
      : "border-[#00D4FF]/35 bg-[#00D4FF]/10 text-[#63E4FF]";

  return (
    <div className={`flex items-center gap-3 rounded-xl border p-3 ${colors}`}>
      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[#04080C]/55">
        <Icon size={18} />
      </span>
      <div className="min-w-0">
        <p className="font-mono text-[9px] font-bold uppercase tracking-[.16em] opacity-75">
          {label}
        </p>
        <p className="mt-0.5 truncate font-syne text-sm font-bold">{value}</p>
      </div>
    </div>
  );
}

/* ─── Main component ──────────────────────────────────────────────── */

export default function LandingPage() {
  const { user, signOut } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  const appPath = user ? "/app" : "/register";
  const closeMenu = () => setMenuOpen(false);

  return (
    <div className="min-h-screen overflow-x-clip bg-[#04080C] text-[#CDE8F0]">
      {/* ── NAVBAR ──────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-[100] border-b border-[#132435] bg-[#04080C]/90 backdrop-blur-xl">
        <div className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-5 sm:px-8">
          {/* Logo */}
          <Link
            to="/"
            className="flex items-center gap-3"
            aria-label="Verify, página inicial"
          >
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#00D4FF] text-[#04080C] shadow-[0_0_25px_#00D4FF55]">
              <ShieldCheck size={21} />
            </span>
            <span className="font-syne text-xl font-black tracking-[.2em] sm:text-2xl">
              VERIFY
            </span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden items-center gap-7 md:flex">
            <a
              href="#como-funciona"
              className="font-mono text-[10px] font-bold uppercase tracking-[.15em] text-[#8AA2B4] hover:text-[#00D4FF] transition-colors"
            >
              Como funciona
            </a>
            <a
              href="#protege"
              className="font-mono text-[10px] font-bold uppercase tracking-[.15em] text-[#8AA2B4] hover:text-[#00D4FF] transition-colors"
            >
              Proteção
            </a>
            <Link
              to="/demo"
              className="font-mono text-[10px] font-bold uppercase tracking-[.15em] text-[#8AA2B4] hover:text-[#00D4FF] transition-colors"
            >
              Demonstração
            </Link>
            {user ? (
              <>
                <Link
                  to="/app"
                  className="font-mono text-[10px] font-bold uppercase tracking-[.15em] text-[#00D4FF]"
                >
                  Abrir Verify
                </Link>
                <button
                  onClick={signOut}
                  className="inline-flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-[.15em] text-[#FF8195] hover:text-[#FF3B5C] transition-colors"
                >
                  <LogOut size={14} /> Sair
                </button>
              </>
            ) : (
              <Link
                to="/login"
                className="rounded-lg border border-[#00D4FF55] px-4 py-2 font-mono text-[10px] font-bold uppercase tracking-[.15em] hover:bg-[#00D4FF] hover:text-[#04080C] transition-colors"
              >
                Entrar
              </Link>
            )}
          </div>

          {/* Mobile menu toggle */}
          <div className="flex items-center gap-2 md:hidden">
            <Link
              to={appPath}
              className="rounded-lg bg-[#00D4FF] px-3 py-2 font-mono text-[10px] font-bold uppercase text-[#04080C]"
            >
              Começar
            </Link>
            <button
              type="button"
              onClick={() => setMenuOpen((o) => !o)}
              aria-expanded={menuOpen}
              aria-label="Abrir navegação"
              className="rounded-lg border border-[#284258] p-2 text-[#CDE8F0]"
            >
              {menuOpen ? <X size={19} /> : <Menu size={19} />}
            </button>
          </div>
        </div>

        {/* Mobile dropdown */}
        {menuOpen && (
          <div className="border-t border-[#132435] bg-[#07111A] px-5 py-4 md:hidden">
            <div className="mx-auto flex max-w-7xl flex-col gap-1">
              <a
                onClick={() => setMenuOpen(false)}
                href="#como-funciona"
                className="rounded-lg px-3 py-3 font-mono text-xs font-bold uppercase tracking-wider text-[#CDE8F0] hover:bg-[#0A1520]"
              >
                Como funciona
              </a>
              <a
                onClick={() => setMenuOpen(false)}
                href="#protege"
                className="rounded-lg px-3 py-3 font-mono text-xs font-bold uppercase tracking-wider text-[#CDE8F0] hover:bg-[#0A1520]"
              >
                Proteção
              </a>
              <Link
                onClick={() => setMenuOpen(false)}
                to="/demo"
                className="rounded-lg px-3 py-3 font-mono text-xs font-bold uppercase tracking-wider text-[#CDE8F0] hover:bg-[#0A1520]"
              >
                Ver demonstração
              </Link>
              {!user && (
                <Link
                  onClick={() => setMenuOpen(false)}
                  to="/login"
                  className="rounded-lg px-3 py-3 font-mono text-xs font-bold uppercase tracking-wider text-[#00D4FF] hover:bg-[#0A1520]"
                >
                  Entrar
                </Link>
              )}
            </div>
          </div>
        )}
      </nav>

      <main>
        {/* ── HERO ───────────────────────────────────────────────── */}
        <section className="relative isolate overflow-hidden border-b border-[#132435] px-5 pb-20 pt-16 sm:px-8 sm:pb-28 sm:pt-24">
          {/* Background gradients */}
          <div
            aria-hidden="true"
            className="absolute inset-0 -z-10 opacity-70"
            style={{
              backgroundImage:
                "radial-gradient(circle at 78% 24%, rgba(0,212,255,.16), transparent 27rem)," +
                "radial-gradient(circle at 25% 82%, rgba(0,255,135,.1), transparent 22rem)," +
                "linear-gradient(rgba(19,36,53,.6) 1px, transparent 1px)," +
                "linear-gradient(90deg, rgba(19,36,53,.6) 1px, transparent 1px)",
              backgroundSize: "auto, auto, 48px 48px, 48px 48px",
            }}
          />

          <div className="mx-auto grid max-w-7xl items-center gap-14 lg:grid-cols-[1.05fr_.95fr] lg:gap-20">
            {/* Left: headline */}
            <div className="max-w-3xl">
              {/* Badge */}
              <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-[#00D4FF33] bg-[#00D4FF0D] px-4 py-2 font-mono text-[10px] font-bold uppercase tracking-[.16em] text-[#00D4FF]">
                <Sparkles size={13} /> Verificação digital para todos
              </div>

              <h1 className="font-syne text-4xl font-black leading-[1.06] tracking-tight sm:text-6xl xl:text-7xl">
                Antes de compartilhar,{" "}
                <span className="text-[#00D4FF]">verifique.</span>
              </h1>

              <p className="mt-7 max-w-2xl font-mono text-sm leading-8 text-[#9BB3C4] sm:text-base">
                O Verify ajuda você a entender mensagens suspeitas, golpes e
                conteúdo manipulado. Você recebe uma explicação clara para
                decidir com mais segurança.
              </p>

              {/* CTAs */}
              <div className="mt-9 flex flex-col gap-4 sm:flex-row">
                <Link
                  to={appPath}
                  className="inline-flex min-h-14 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#00D4FF] to-[#00FF87] px-7 font-syne text-sm font-black uppercase tracking-wider text-[#04080C] shadow-[0_12px_35px_rgba(0,212,255,.22)] transition-transform hover:-translate-y-0.5"
                >
                  <FileSearch size={18} />
                  {user ? "Fazer uma checagem" : "Começar agora"}
                  <ArrowRight size={17} />
                </Link>

                <Link
                  to="/demo"
                  className="inline-flex min-h-14 items-center justify-center gap-2 rounded-xl border border-[#284258] bg-[#091622]/80 px-7 font-mono text-xs font-bold uppercase tracking-wider text-[#CDE8F0] transition-colors hover:border-[#00D4FF] hover:text-[#00D4FF]"
                >
                  <Volume2 size={16} /> Ver demonstração
                </Link>
              </div>

              <p className="mt-5 flex items-center gap-2 font-mono text-[10px] leading-5 text-[#6F8B9F]">
                <CheckCircle2 size={13} className="shrink-0 text-[#00FF87]" />
                A demonstração é aberta. Crie uma conta quando quiser guardar o
                histórico.
              </p>
            </div>

            {/* Right: mock analysis card */}
            <div className="relative mx-auto w-full max-w-[540px]">
              <div
                aria-hidden="true"
                className="absolute -inset-4 -z-10 rounded-[2.4rem] bg-[#00D4FF]/10 blur-3xl"
              />
              <div className="overflow-hidden rounded-[1.8rem] border border-[#2A5269] bg-[#07111A]/95 p-5 shadow-[0_25px_80px_rgba(0,0,0,.45)] sm:p-7">
                {/* Window bar */}
                <div className="flex items-center justify-between border-b border-[#183347] pb-4">
                  <div className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 rounded-full bg-[#FF3B5C]" />
                    <span className="h-2.5 w-2.5 rounded-full bg-[#FFB800]" />
                    <span className="h-2.5 w-2.5 rounded-full bg-[#00FF87]" />
                  </div>
                  <span className="font-mono text-[9px] font-bold uppercase tracking-[.2em] text-[#00D4FF]">
                    Análise em foco
                  </span>
                </div>

                {/* Alert card */}
                <div className="mt-5 rounded-2xl border border-[#FF3B5C]/35 bg-gradient-to-br from-[#FF3B5C]/15 to-[#0A1520] p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-mono text-[10px] font-bold uppercase tracking-[.16em] text-[#FF9CAF]">
                        Mensagem recebida
                      </p>
                      <p className="mt-3 font-syne text-lg font-bold leading-snug text-white">
                        "Pague uma taxa agora para liberar seu Pix."
                      </p>
                    </div>
                    <AlertTriangle className="shrink-0 text-[#FF8195]" size={25} />
                  </div>

                  {/* Risk bar */}
                  <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-[#132435]">
                    <div className="h-full w-[84%] rounded-full bg-gradient-to-r from-[#FFB800] to-[#FF3B5C]" />
                  </div>
                  <p className="mt-2 font-mono text-[10px] text-[#FFB2BF]">
                    Sinais de risco identificados — 84%
                  </p>
                </div>

                {/* Signal cards */}
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  <SignalCard icon={ShieldCheck} label="Orientação" value="Não envie Pix" tone="red" />
                  <SignalCard icon={BadgeCheck} label="Contexto" value="Fonte oficial" tone="cyan" />
                  <SignalCard icon={MessageCircle} label="Próximo passo" value="Avisar família" tone="green" />
                </div>

                {/* Media types bar */}
                <div className="mt-5 flex items-center justify-center gap-3 rounded-xl border border-[#1B3A4B] bg-[#04080C] p-3">
                  <FileSearch size={16} className="text-[#00D4FF]" />
                  <span className="font-mono text-[10px] uppercase tracking-[.12em] text-[#8AA2B4]">
                    Texto · links · imagens · áudio
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── MEDIA TYPES BANNER ─────────────────────────────────── */}
        <section className="border-b border-[#132435] bg-[#07111A] px-5 py-6 sm:px-8">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-center gap-x-10 gap-y-4 text-center">
            {MEDIA_TYPES.map(({ icon: Icon, label }) => (
              <span
                key={label}
                className="inline-flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-[.14em] text-[#8AA2B4]"
              >
                <Icon size={15} className="text-[#00D4FF]" />
                {label}
              </span>
            ))}
          </div>
        </section>

        {/* ── HOW IT WORKS ───────────────────────────────────────── */}
        <section
          id="como-funciona"
          className="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-28"
        >
          {/* Header */}
          <div className="mb-12 max-w-2xl">
            <span className="font-mono text-[10px] font-bold uppercase tracking-[.2em] text-[#00D4FF]">
              Processo simples
            </span>
            <h2 className="mt-4 font-syne text-3xl font-black leading-tight tracking-tight sm:text-5xl">
              Três passos para checar com mais segurança.
            </h2>
          </div>

          {/* Step cards */}
          <div className="grid gap-6 md:grid-cols-3">
            {STEPS.map(({ number, title, text, color }) => (
              <article
                key={number}
                className="group rounded-3xl border border-[#132435] bg-[#0A1520] p-8 transition-colors hover:border-[#00D4FF]/50"
              >
                <span
                  className="font-mono text-sm font-bold"
                  style={{ color }}
                >
                  {number}
                </span>
                <h3 className="mt-10 font-syne text-xl font-bold">{title}</h3>
                <p className="mt-4 font-mono text-sm leading-7 text-[#8AA2B4]">
                  {text}
                </p>
                <ArrowRight
                  size={18}
                  className="mt-8 transition-transform group-hover:translate-x-1"
                  style={{ color }}
                />
              </article>
            ))}
          </div>
        </section>

        {/* ── PROTECTION ─────────────────────────────────────────── */}
        <section
          id="protege"
          className="border-y border-[#132435] bg-[#08131D] px-5 py-20 sm:px-8 sm:py-28"
        >
          <div className="mx-auto grid max-w-7xl gap-12 lg:grid-cols-[.75fr_1.25fr] lg:items-start">
            {/* Left: text */}
            <div>
              <span className="font-mono text-[10px] font-bold uppercase tracking-[.2em] text-[#00FF87]">
                Proteção prática
              </span>
              <h2 className="mt-4 font-syne text-3xl font-black leading-tight tracking-tight sm:text-5xl">
                Mais contexto antes de uma decisão.
              </h2>
              <p className="mt-6 font-mono text-sm leading-8 text-[#8AA2B4]">
                A melhor proteção é uma pausa: não pagar, não clicar e
                confirmar a informação em uma fonte independente.
              </p>
            </div>

            {/* Right: feature cards */}
            <div className="grid gap-5 sm:grid-cols-3">
              {FEATURES.map(({ icon: Icon, title, text, color }) => (
                <article
                  key={title}
                  className="rounded-3xl border border-[#183347] bg-[#0A1520] p-7"
                >
                  <Icon size={26} style={{ color }} />
                  <h3 className="mt-7 font-syne text-base font-bold">{title}</h3>
                  <p className="mt-3 font-mono text-xs leading-6 text-[#8AA2B4]">
                    {text}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* ── CTA ────────────────────────────────────────────────── */}
        <section className="px-5 py-20 sm:px-8 sm:py-28">
          <div className="mx-auto max-w-5xl overflow-hidden rounded-3xl border border-[#00D4FF]/30 bg-gradient-to-br from-[#0E2A3A] via-[#0A1520] to-[#0A3324] p-10 text-center shadow-[0_20px_70px_rgba(0,212,255,.09)] sm:p-16">
            <div className="mx-auto mb-6 grid h-16 w-16 place-items-center rounded-2xl bg-[#00D4FF]/15 text-[#00D4FF]">
              <ShieldCheck size={32} />
            </div>
            <h2 className="font-syne text-3xl font-black sm:text-5xl">
              Recebeu algo suspeito?
            </h2>
            <p className="mx-auto mt-6 max-w-xl font-mono text-sm leading-8 text-[#A6C0CE]">
              Faça uma checagem antes de compartilhar. Leva poucos passos e
              pode evitar que um golpe se espalhe pela sua família.
            </p>
            <Link
              to={appPath}
              className="mt-10 inline-flex min-h-14 items-center gap-2 rounded-xl bg-[#00D4FF] px-8 font-syne text-sm font-black uppercase tracking-wider text-[#04080C] transition-transform hover:-translate-y-0.5"
            >
              Checar agora <ArrowRight size={17} />
            </Link>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}