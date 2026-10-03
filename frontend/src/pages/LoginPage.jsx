import { useCallback, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, LockKeyhole, Mail, ShieldCheck, X } from "lucide-react";
import { login, getMe, googleAuth } from "../services/api";
import { useAuth } from "../hooks/authContext";
import GoogleButton from "../components/GoogleButton";

const MAX_ATTEMPTS = 5;
const BLOCK_MS = 15 * 60 * 1000;

export default function LoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [attempts, setAttempts] = useState(0);
  const [blocked, setBlocked] = useState(false);

  const completeLogin = useCallback(async () => {
    const me = await getMe();
    signIn(me);
    navigate("/app");
  }, []);

  const handleGoogleSuccess = useCallback(async (credential) => {
    try {
      await googleAuth({ id_token: credential });
      await completeLogin();
    } catch {
      setError("Não foi possível entrar com Google.");
    }
  }, []);

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
      await completeLogin();
    } catch (err) {
      const nextAttempts = attempts + 1;
      setAttempts(nextAttempts);
      if (nextAttempts >= MAX_ATTEMPTS) {
        setBlocked(true);
        setError("Muitas tentativas. Aguarde 15 minutos para tentar novamente.");
        setTimeout(() => { setBlocked(false); setAttempts(0); setError(""); }, BLOCK_MS);
      } else {
        setError(
          typeof err?.response?.data?.detail === "string"
            ? err.response.data.detail
            : "E-mail ou senha incorretos."
        );
      }
    } finally { setLoading(false); }
  };

  return (
    <div className="relative grid min-h-screen place-items-center overflow-hidden bg-[#04080C] px-5 py-10 text-[#CDE8F0]">
      <div className="pointer-events-none absolute inset-0 opacity-20" style={{ backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)", backgroundSize: "48px 48px" }} />
      <Link aria-label="Voltar à página inicial" to="/" className="absolute right-5 top-5 z-10 rounded-lg border border-[#132435] bg-[#0A1520] p-3 text-[#CDE8F0] hover:border-[#00D4FF] transition-colors"><X size={17} /></Link>

      <main className="relative z-10 w-full max-w-md">
        <header className="mb-8 text-center">
          <Link to="/" className="inline-flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-lg bg-[#00D4FF] text-[#04080C] shadow-[0_0_20px_#00D4FF44]"><ShieldCheck size={20} /></span><span className="font-syne text-3xl font-black tracking-[5px]">VERIFY</span></Link>
          <p className="mt-4 font-mono text-[11px] uppercase tracking-[3px] text-[#8AA2B4]">Acesse sua conta</p>
        </header>

        <section className="rounded-2xl border border-[#132435] bg-[#0A1520] p-6 shadow-2xl sm:p-8">
          <div className="mb-4">
            <GoogleButton onSuccess={handleGoogleSuccess} onError={(msg) => setError(msg)} />
          </div>

          <div className="my-6 flex items-center gap-3">
            <span className="h-px flex-1 bg-[#132435]" /><span className="font-mono text-[9px] uppercase tracking-wider text-[#8AA2B4]">ou por e-mail</span><span className="h-px flex-1 bg-[#132435]" />
          </div>

          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            <label className="block"><span className="mb-2 flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-wider text-[#8AA2B4]"><Mail size={13} /> E-mail</span>
              <input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} disabled={blocked} placeholder="voce@exemplo.com" className="w-full rounded-lg border border-[#132435] bg-[#04080C] px-4 py-3 font-mono text-sm outline-none placeholder:text-[#5A7E94] focus:border-[#00D4FF] transition-colors disabled:opacity-50" /></label>
            <label className="block"><span className="mb-2 flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-wider text-[#8AA2B4]"><LockKeyhole size={13} /> Senha</span>
              <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} disabled={blocked} placeholder="Sua senha" className="w-full rounded-lg border border-[#132435] bg-[#04080C] px-4 py-3 font-mono text-sm outline-none placeholder:text-[#5A7E94] focus:border-[#00D4FF] transition-colors disabled:opacity-50" /></label>
            {error && (<p className="rounded-lg border border-[#FF3B5C44] bg-[#FF3B5C11] p-3 font-mono text-xs text-[#FF8195]">{error}</p>)}
            <button type="submit" disabled={loading || blocked} className="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-[#00D4FF] to-[#00FF87] px-5 py-4 font-syne text-sm font-black uppercase tracking-wider text-[#04080C] disabled:opacity-50 transition-opacity">{loading ? "Entrando..." : blocked ? "Acesso temporariamente bloqueado" : (<>Entrar <ArrowRight size={16} /></>)}</button>
          </form>
        </section>

        <p className="mt-6 text-center font-mono text-xs text-[#8AA2B4]">Ainda não tem conta?{" "}<Link to="/register" className="font-bold text-[#00D4FF] hover:underline">Criar conta</Link></p>
      </main>
    </div>
  );
}
