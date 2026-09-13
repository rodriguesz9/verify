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

export default function RegisterPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [showGoogle, setShowGoogle] = useState(false);
  const update = key => event => setForm(current => ({ ...current, [key]: event.target.value }));
  const completeRegistration = async () => { signIn(await getMe()); navigate("/app"); };

  // Separate Google auth function
  const handleGoogleSignIn = async () => {
    setGoogleLoading(true); setError("");
    try {
      const { google } = window;
      if (!google) return setError("Google auth não disponível");
      const { credential } = await new Promise(resolve => {
        google.accounts.id.prompt(async (notification) => {
          if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            resolve({ credential: null });
          }
          if (notification.isDismissedMoment()) {
            resolve({ credential: null });
          }
        });
        if (google.accounts.id.hasOwnProperty('prompt')) {
          google.accounts.id.prompt(async (notification) => {
            if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
              resolve({ credential: null });
            }
            if (notification.isDismissedMoment()) {
              resolve({ credential: null });
            }
            if (notification.isSuccess()) {
              const authResponse = google.accounts.oauth2.getAuthResponse(true);
              resolve({ credential: authResponse.access_token });
            }
          });
        } else {
          google.accounts.id.renderButton(document.getElementById("google-reg-btn"), { theme: "filled_black", size: "large", width: "100%", shape: "rectangular" });
        }
      });
      if (!credential) {
        google.accounts.id.prompt();
        return;
      }
      await googleAuth({ id_token: credential });
      await completeRegistration();
    } catch (e) {
      setError("Não foi possível criar a conta com Google.");
    } finally {
      setGoogleLoading(false);
    }
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
          {/* Google Sign In Option */}
          <div className="mb-6">
            <GoogleSignInButton
              onClick={handleGoogleSignIn}
              loading={googleLoading}
              disabled={loading}
              className="w-full mb-3"
            />
            {showGoogle && !googleLoading && (
              <p className="text-xs text-[#8AA2B4] text-center mt-2">
                Entre com sua conta Google para criar uma conta Verify automaticamente.
              </p>
            )}
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