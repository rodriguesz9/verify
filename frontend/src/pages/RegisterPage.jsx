import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, LockKeyhole, Mail, ShieldCheck, UserRound, X } from "lucide-react";
import { register, googleAuth, getMe } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import GoogleButton from "../components/GoogleButton";

function Field({ label, icon: Icon, type, value, onChange, placeholder }) {
  return (
    <label className="block">
      <span className="mb-2 flex items-center gap-2 font-mono text-[10px] font-bold uppercase tracking-wider text-[#8AA2B4]">
        <Icon size={13} /> {label}
      </span>
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="w-full rounded-lg border border-[#132435] bg-[#04080C] px-4 py-3 font-mono text-sm outline-none placeholder:text-[#5A7E94] focus:border-[#00D4FF]"
      />
    </label>
  );
}

export default function RegisterPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const update = key => event => setForm(current => ({ ...current, [key]: event.target.value }));
  const completeRegistration = async () => { signIn(await getMe()); navigate("/app"); };

  const handleGoogleSuccess = async (credential) => {
    await googleAuth({ id_token: credential });
    await completeRegistration();
  };

  const handleSubmit = async event => {
    event.preventDefault(); setError("");
    if (!form.name || !form.email || !form.password) return setError("Preencha todos os campos para continuar.");
    setLoading(true);
    try {
      await register(form);
      await completeRegistration();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(Array.isArray(detail) ? detail[0].msg : detail || "Não foi possível criar sua conta. Tente novamente.");
    } finally { setLoading(false); }
  };

  return (
    <div className="relative grid min-h-screen place-items-center overflow-hidden bg-[#04080C] px-5 py-10 text-[#CDE8F0]">
      <div className="pointer-events-none absolute inset-0 opacity-20" style={{ backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)", backgroundSize: "48px 48px" }} />
      <Link aria-label="Voltar à página inicial" to="/" className="absolute right-5 top-5 z-10 rounded-lg border border-[#132435] bg-[#0A1520] p-3 text-[#CDE8F0] hover:border-[#00D4FF]"><X size={17} /></Link>

      <main className="relative z-10 w-full max-w-md">
        <header className="mb-8 text-center">
          <Link to="/" className="inline-flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-lg bg-[#00D4FF] text-[#04080C]"><ShieldCheck size={20} /></span><span className="font-syne text-3xl font-black tracking-[5px]">VERIFY</span></Link>
          <p className="mt-4 font-mono text-[11px] uppercase tracking-[3px] text-[#8AA2B4]">Crie sua conta</p>
        </header>

        <section className="rounded-2xl border border-[#132435] bg-[#0A1520] p-6 shadow-2xl sm:p-8">
          <div className="mb-4">
            <GoogleButton onSuccess={handleGoogleSuccess} onError={(msg) => setError(msg)} />
          </div>

          <div className="mb-6 flex items-center gap-3">
            <span className="h-px flex-1 bg-[#132435]" /><span className="font-mono text-[9px] uppercase tracking-wider text-[#8AA2B4]">ou por e-mail</span><span className="h-px flex-1 bg-[#132435]" />
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <Field label="Nome" icon={UserRound} type="text" value={form.name} onChange={update("name")} placeholder="Seu nome" />
            <Field label="E-mail" icon={Mail} type="email" value={form.email} onChange={update("email")} placeholder="voce@exemplo.com" />
            <Field label="Senha" icon={LockKeyhole} type="password" value={form.password} onChange={update("password")} placeholder="Mínimo de 6 caracteres" />
            {error && (<p className="rounded-lg border border-[#FF3B5C44] bg-[#FF3B5C11] p-3 font-mono text-xs text-[#FF8195]">{error}</p>)}
            <button type="submit" disabled={loading} className="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-[#00D4FF] to-[#00FF87] px-5 py-4 font-syne text-sm font-black uppercase tracking-wider text-[#04080C] transition-opacity disabled:opacity-50">{loading ? "Criando conta..." : (<>Criar conta <ArrowRight size={17} /></>)}</button>
          </form>
        </section>

        <p className="mt-6 text-center font-mono text-xs text-[#8AA2B4]">Já tem conta? <Link to="/login" className="font-bold text-[#00D4FF] hover:underline">Entrar</Link></p>
      </main>
    </div>
  );
}