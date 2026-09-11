import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login, getMe, googleAuth } from "../services/api";
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

  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!clientId) return;
    if (window.google) {
      google.accounts.id.initialize({ client_id: clientId, callback: handleGoogleCallback });
      google.accounts.id.renderButton(document.getElementById("google-btn"), { theme: "dark", size: "large", width: "100%", type: "standard", shape: "rectangular" });
    }
  }, []);

  const handleGoogleCallback = async (response) => {
    setLoading(true); setError("");
    try {
      const tokens = await googleAuth({ id_token: response.credential });
      if (tokens?.access_token) {
        localStorage.setItem("verify_access", tokens.access_token);
        localStorage.setItem("verify_refresh", tokens.refresh_token);
      }
      const me = await getMe();
      signIn(tokens, me);
      navigate("/app");
    } catch (err) {
      setError("Falha ao entrar com Google.");
    } finally { setLoading(false); }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (blocked) return;
    setError("");
    if (!email.trim() || !password) { setError("Por favor, preencha seu e-mail e sua senha."); return; }
    setLoading(true);

    try {
      const tokens = await login({ email: email.trim().toLowerCase(), password });
      if (tokens?.access_token) {
        localStorage.setItem("verify_access", tokens.access_token);
        localStorage.setItem("verify_refresh", tokens.refresh_token);
      }
      const me = await getMe();
      signIn(tokens, me);
      navigate("/app");
    } catch (err) {
      console.error("Login error:", err);
      const newAttempts = attempts + 1;
      setAttempts(newAttempts);
      if (newAttempts >= MAX_ATTEMPTS) {
        setBlocked(true);
        setError("Muitas tentativas erradas. Por segurança, aguarde 15 minutos.");
        setTimeout(() => { setBlocked(false); setAttempts(0); setError(""); }, BLOCK_MS);
      } else {
        const detail = err?.response?.data?.detail;
        setError(`${typeof detail === "string" ? detail : "E-mail ou senha incorretos."}`);
      }
    } finally { setLoading(false); }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center px-5 overflow-hidden">
      <div className="pointer-events-none fixed inset-0" style={{ backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)", backgroundSize: "48px 48px", opacity: .3 }}/>

      <Link to="/" className="fixed top-8 right-8 z-[100] w-12 h-12 flex items-center justify-center rounded-full bg-[#0A1520] border border-[#132435] text-text no-underline hover:bg-white/10 transition-colors">
         <span className="font-syne font-bold">✕</span>
      </Link>

      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-10">
          <Link to="/" style={{ textDecoration: "none" }}>
            <h1 className="font-syne font-black text-4xl tracking-[10px] text-text uppercase">VERIFY</h1>
          </Link>
          <p className="font-mono text-[11px] mt-2 tracking-[4px] text-[#3A6070] font-bold">Acesse sua conta</p>
        </div>

        <div className="rounded-[2.5rem] p-10" style={{ background: "#0A1520", border: "1px solid #132435", boxShadow: "0 40px 100px rgba(0,0,0,.6)" }}>
          <div className="p-0 pb-4">
             <div id="google-btn" className="w-full"></div>
          </div>

          <div className="flex items-center gap-4 opacity-20 mb-8 mt-4">
            <div className="flex-1 h-px bg-white"/>
            <span className="font-mono text-[9px] tracking-[4px]">OU USE SEU E-MAIL</span>
            <div className="flex-1 h-px bg-white"/>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-6" noValidate>
            <div>
              <label className="font-mono text-[11px] block mb-2 text-[#3A6070] tracking-[2px] uppercase">E-MAIL</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} disabled={blocked}
                className="w-full font-mono text-[14px] px-6 py-4 rounded-2xl bg-[#0F1E2E] border border-[#132435] text-[#CDE8F0] outline-none focus:border-cyan transition-all"
                placeholder="seu@email.com"/>
            </div>
            <div>
              <label className="font-mono text-[11px] block mb-2 text-[#3A6070] tracking-[2px] uppercase">SENHA</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} disabled={blocked}
                className="w-full font-mono text-[14px] px-6 py-4 rounded-2xl bg-[#0F1E2E] border border-[#132435] text-[#CDE8F0] outline-none focus:border-cyan transition-all"
                placeholder="sua senha"/>
            </div>
            
            {error && <div className="p-5 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 font-mono text-[12px]"> <span className="font-bold mr-1">!</span> {error}</div>}
            
            <button type="submit" disabled={loading || blocked} className="w-full font-syne font-black text-[15px] tracking-[4px] py-6 rounded-3xl transition-all shadow-xl" 
                    style={{ 
                      background: blocked ? "#132435" : "linear-gradient(135deg,#00D4FF,#00FF87)", 
                      color: "#04080C", border: "none", 
                      opacity: (loading || blocked) ? 0.7 : 1
                    }}>
              {loading ? "ENTRANDO..." : blocked ? "BLOQUEADO" : "ENTRAR AGORA"}
            </button>
          </form>
        </div>
        
        <p className="text-center font-mono text-[12px] mt-8 text-[#3A6070] tracking-[4px] uppercase font-medium">
          Ainda não tem conta? <Link to="/register" style={{ color: "#00D4FF", textDecoration: 'none', fontWeight: 'bold' }}>Cadastre-se aqui</Link>
        </p>
      </div>
    </div>
  );
}
