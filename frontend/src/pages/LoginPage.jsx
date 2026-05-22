import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login, getMe } from "../services/api";
import { useAuth } from "../hooks/useAuth";

const MAX_ATTEMPTS = 5;
const BLOCK_MS = 15 * 60 * 1000;

export default function LoginPage() {
  const { signIn }    = useAuth();
  const navigate      = useNavigate();

  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [error,    setError]    = useState("");
  const [loading,  setLoading]  = useState(false);
  const [attempts, setAttempts] = useState(0);
  const [blocked,  setBlocked]  = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (blocked) return;
    setError("");
    if (!email.trim() || !password) { setError("Preencha e-mail e senha."); return; }
    setLoading(true);

    try {
      const tokens = await login({ email: email.trim().toLowerCase(), password });

      localStorage.setItem("verifai_access", tokens.access_token);
      localStorage.setItem("verifai_refresh", tokens.refresh_token);

      const me = await getMe();

      signIn(tokens, me);
      navigate("/app");
    } catch (err) {
      const newAttempts = attempts + 1;
      setAttempts(newAttempts);

      if (newAttempts >= MAX_ATTEMPTS) {
        setBlocked(true);
        setError("Muitas tentativas. Aguarde 15 minutos antes de tentar novamente.");
        setTimeout(() => { setBlocked(false); setAttempts(0); setError(""); }, BLOCK_MS);
      } else {
        const detail = err?.response?.data?.detail;
        const msg = typeof detail === "string"
          ? detail
          : "E-mail ou senha incorretos.";
        setError(`${msg} (tentativa ${newAttempts}/${MAX_ATTEMPTS})`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center px-5">
      <div className="pointer-events-none fixed inset-0" style={{
        backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)",
        backgroundSize: "48px 48px", opacity: .3 }}/>

      <div className="w-full max-w-md relative z-10">
        {/* brand */}
        <div className="text-center mb-8 fade-1">
          <Link to="/" style={{ textDecoration: "none" }}>
            <div className="flex justify-center mb-3">
              <svg width="40" height="40" viewBox="0 0 28 28">
                <polygon points="14,2 26,8 26,20 14,26 2,20 2,8" fill="none" stroke="#00D4FF" strokeWidth="1.5"/>
                <circle cx="14" cy="14" r="4" fill="#00D4FF" opacity=".8"/>
              </svg>
            </div>
            <h1 className="font-syne font-extrabold text-2xl tracking-widest text-text">
              VERIF<span style={{ color: "#00D4FF" }}>AI</span>
            </h1>
          </Link>
          <p className="font-mono text-[11px] mt-1" style={{ color: "#3A6070" }}>AUDITORIA DIGITAL · LOGIN</p>
        </div>

        <div className="rounded-2xl overflow-hidden fade-2"
          style={{ background: "#0A1520", border: "1px solid #132435", boxShadow: "0 40px 80px rgba(0,0,0,.5)" }}>

          {/* Google OAuth button */}
          <div className="p-6 pb-4">
            <button type="button"
              onClick={() => alert("Configure VITE_GOOGLE_CLIENT_ID no .env do frontend para ativar o OAuth Google.")}
              className="w-full flex items-center justify-center gap-3 font-mono text-[12px] tracking-wide py-3 rounded-lg transition-all"
              style={{ background: "#0F1E2E", border: "1px solid #132435", color: "#CDE8F0", cursor: "pointer" }}>
              <svg width="16" height="16" viewBox="0 0 48 48">
                <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.35-8.16 2.35-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
              </svg>
              Entrar com Google
            </button>
          </div>

          <div className="flex items-center gap-3 px-6 mb-4">
            <div className="flex-1 h-px" style={{ background: "#132435" }}/>
            <span className="font-mono text-[10px]" style={{ color: "#1A3A50" }}>OU</span>
            <div className="flex-1 h-px" style={{ background: "#132435" }}/>
          </div>

          <form onSubmit={handleSubmit} className="px-6 pb-6" noValidate>
            {/* email */}
            <div className="mb-4">
              <label className="font-mono text-[10px] tracking-widest block mb-2" style={{ color: "#3A6070" }}>E-MAIL</label>
              <input type="email" required autoComplete="email"
                value={email} onChange={e => setEmail(e.target.value)}
                placeholder="seu@email.com"
                disabled={blocked}
                className="w-full font-mono text-[13px] px-4 py-3 rounded-lg"
                style={{ background: "#0F1E2E", border: "1px solid #132435", color: "#CDE8F0", outline: "none",
                  opacity: blocked ? .5 : 1 }}/>
            </div>

            {/* password */}
            <div className="mb-5">
              <label className="font-mono text-[10px] tracking-widest block mb-2" style={{ color: "#3A6070" }}>SENHA</label>
              <input type="password" required autoComplete="current-password"
                value={password} onChange={e => setPassword(e.target.value)}
                placeholder="Sua senha"
                disabled={blocked}
                className="w-full font-mono text-[13px] px-4 py-3 rounded-lg"
                style={{ background: "#0F1E2E", border: "1px solid #132435", color: "#CDE8F0", outline: "none",
                  opacity: blocked ? .5 : 1 }}/>
            </div>

            {/* attempt bar */}
            {attempts > 0 && !blocked && (
              <div className="flex gap-1 mb-4">
                {Array.from({ length: MAX_ATTEMPTS }).map((_, i) => (
                  <div key={i} className="h-1 flex-1 rounded-full transition-all"
                    style={{ background: i < attempts ? "#FF3B5C" : "#1A3A50" }}/>
                ))}
              </div>
            )}

            {/* error */}
            {error && (
              <div className="mb-4 px-3 py-2.5 rounded-lg font-mono text-[11px] leading-relaxed"
                style={{ background: "rgba(255,59,92,.1)", border: "1px solid rgba(255,59,92,.3)", color: "#FF3B5C" }}>
                ✗ {error}
              </div>
            )}

            <button type="submit" disabled={loading || blocked}
              className="w-full font-syne font-bold text-[13px] tracking-widest py-3 rounded-lg transition-all"
              style={{
                background: blocked ? "#132435" : loading ? "#0A1520" : "linear-gradient(135deg,#00D4FF,#00FF87)",
                color: blocked || loading ? "#3A6070" : "#04080C",
                border: "none", cursor: blocked || loading ? "not-allowed" : "pointer",
                boxShadow: !blocked && !loading ? "0 0 24px rgba(0,212,255,.3)" : "none",
              }}>
              {loading ? "VERIFICANDO…" : blocked ? "BLOQUEADO (15 MIN)" : "ENTRAR →"}
            </button>
          </form>
        </div>

        <p className="text-center font-mono text-[11px] mt-5 fade-3" style={{ color: "#3A6070" }}>
          Não tem conta?{" "}
          <Link to="/register" style={{ color: "#00D4FF", textDecoration: "none" }}>Cadastre-se grátis</Link>
          {" · "}
          <Link to="/" style={{ color: "#3A6070", textDecoration: "none" }}>← Voltar ao início</Link>
        </p>
      </div>
    </div>
  );
}
