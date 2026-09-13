import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, LockKeyhole, Mail, ShieldCheck, X } from "lucide-react";
import { login, getMe, googleAuth } from "../services/api";
import { useAuth } from "../hooks/useAuth";

const MAX_ATTEMPTS = 5;
const BLOCK_MS = 15 * 60 * 1000;

function GoogleSignInButton({ onClick, loading, disabled, className, size = "large", variant = "primary" }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading || disabled}
      className={`flex items-center justify-center gap-2 rounded-lg border border-[#4285F4]/30 bg-[#4285F4]/10 px-4 py-3 font-mono text-sm font-medium uppercase tracking-wider text-[#4285F4] transition-all hover:bg-[#4285F4]/20 ${className} ${loading || disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
    >
      <svg width="20" height="20" viewBox="0 0 24 24">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.3-4.75 3.3-8.09z" />
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.96 23 12 23z" />
        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" />
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.96 1 4.32 3.42 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
      </svg>
      <span>{loading ? 'Entrando...' : 'Google'}</span>
    </button>
  );
}

export default function LoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();

  // Keep form state isolated from auth context to avoid re-renders on every keystroke
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [attempts, setAttempts] = useState(0);
  const [blocked, setBlocked] = useState(false);

  // useRef so the Google callback closure is always fresh without re-registering the button
  const completeLoginRef = useRef(null);
  completeLoginRef.current = async () => {
    const me = await getMe();
    signIn(me);
    navigate("/app");
  };

  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!clientId || !window.google) return;

    google.accounts.id.initialize({
      client_id: clientId,
      callback: async (response) => {
        setGoogleLoading(true);
        setError("");
        try {
          await googleAuth({ id_token: response.credential });
          await completeLoginRef.current();
        } catch {
          setError("Não foi possível entrar com Google.");
          setGoogleLoading(false);
        }
      },
    });

    google.accounts.id.renderButton(document.getElementById("google-btn"), {
      theme: "filled_black",
      size: "large",
      width: "100%",
      shape: "rectangular",
    });
  }, []); // run once — callback always uses the ref

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (blocked) return;
    setError("");
    if (!email.trim() || !password) {
      setError("Informe seu e-mail e sua senha.");
      return;
    }
    setLoading(true);
    try {
      await login({ email: email.trim().toLowerCase(), password });
      await completeLoginRef.current();
    } catch (err) {
      const nextAttempts = attempts + 1;
      setAttempts(nextAttempts);
      if (nextAttempts >= MAX_ATTEMPTS) {
        setBlocked(true);
        setError("Muitas tentativas. Aguarde 15 minutos para tentar novamente.");
        setTimeout(() => {
          setBlocked(false);
          setAttempts(0);
          setError("");
        }, BLOCK_MS);
      } else {
        setError(
          typeof err?.response?.data?.detail === "string"
            ? err.response.data.detail
            : "E-mail ou senha incorretos."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative grid min-h-screen place-items-center overflow-hidden bg-[#04080C] px-5 py-10 text-[#CDE8F0]">
      {/* Grid background */}
      <div
        className="pointer-events-none absolute inset-0 opacity-20"
        style={{
          backgroundImage:
            "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />

      {/* Close button */}
      <Link
        aria-label="Voltar à página inicial"
        to="/"
        className="absolute right-5 top-5 z-10 rounded-lg border border-[#132435] bg-[#0A1520] p-3 text-[#CDE8F0] hover:border-[#00D4FF] transition-colors"
      >
        <X size={17} />
      </Link>

      <main className="relative z-10 w-full max-w-md">
        {/* Logo */}
        <header className="mb-8 text-center">
          <Link to="/" className="inline-flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-[#00D4FF] text-[#04080C] shadow-[0_0_20px_#00D4FF44]">
              <ShieldCheck size={20} />
            </span>
            <span className="font-syne text-3xl font-black tracking-[5px]">VERIFY</span>
          </Link>
          <p className="mt-4 font-mono text-[11px] uppercase tracking-[3px] text-[#8AA2B4]">
            Acesse sua conta
          </p>
        </header>

        <section className="rounded-2xl border border-[#132435] bg-[#0A1520] p-6 shadow-2xl sm:p-8">
          {/* Google button */}
          <div id="google-btn" className="w-full mb-3" />
          <p className="text-xs text-[#8AA2B4] text-center mb-4">
            Entrar com sua conta Google para acesso rápido e seguro.
          </p>

          <div className="my-6 flex items-center gap-3">
            <span className="h-px flex-1 bg-[#132435]" />
            <span className="font-mono text-[9px] uppercase tracking-wider text-[#8AA2B4]">
              ou por e-mail
            </span>
            <span className="h-px flex-1 bg-[#132435]" />
          </div>

          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            {/* Email */}
            <label className="block">
              <span className="mb-2 flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-wider text-[#8AA2B4]">
                <Mail size={13} /> E-mail
              </span>
              <input
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={blocked}
                placeholder="voce@exemplo.com"
                className="w-full rounded-lg border border-[#132435] bg-[#04080C] px-4 py-3 font-mono text-sm outline-none placeholder:text-[#5A7E94] focus:border-[#00D4FF] transition-colors disabled:opacity-50"
              />
            </label>

            {/* Password */}
            <label className="block">
              <span className="mb-2 flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-wider text-[#8AA2B4]">
                <LockKeyhole size={13} /> Senha
              </span>
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={blocked}
                placeholder="Sua senha"
                className="w-full rounded-lg border border-[#132435] bg-[#04080C] px-4 py-3 font-mono text-sm outline-none placeholder:text-[#5A7E94] focus:border-[#00D4FF] transition-colors disabled:opacity-50"
              />
            </label>

            {/* Error */}
            {error && (
              <p className="rounded-lg border border-[#FF3B5C44] bg-[#FF3B5C11] p-3 font-mono text-xs text-[#FF8195]">
                {error}
              </p>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || blocked}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-[#00D4FF] to-[#00FF87] px-5 py-4 font-syne text-sm font-black uppercase tracking-wider text-[#04080C] disabled:opacity-50 transition-opacity"
            >
              {loading
                ? "Entrando..."
                : blocked
                ? "Acesso temporariamente bloqueado"
                : (<>Entrar <ArrowRight size={16} /></>)}
            </button>
          </form>
        </section>

        <p className="mt-6 text-center font-mono text-xs text-[#8AA2B4]">
          Ainda não tem conta?{" "}
          <Link to="/register" className="font-bold text-[#00D4FF] hover:underline">
            Criar conta
          </Link>
        </p>
      </main>
    </div>
  );
}