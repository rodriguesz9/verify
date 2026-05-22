import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register, googleAuth, getMe } from "../services/api";
import { useAuth } from "../hooks/useAuth";

export default function RegisterPage() {
  const { signIn } = useAuth();
  const navigate   = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    if (!clientId) return;
    if (window.google) {
      google.accounts.id.initialize({ client_id: clientId, callback: handleGoogleCallback });
      google.accounts.id.renderButton(document.getElementById("google-reg-btn"), { theme: "dark", size: "large", width: "100%", type: "standard" });
    }
  }, []);

  const handleGoogleCallback = async (response) => {
    setLoading(true); setError("");
    try {
      const tokens = await googleAuth({ id_token: response.credential });
      localStorage.setItem("verifai_access", tokens.access_token);
      localStorage.setItem("verifai_refresh", tokens.refresh_token);
      const me = await getMe();
      signIn(tokens, me);
      navigate("/app");
    } catch (err) {
      setError("Falha ao entrar com Google.");
    } finally { setLoading(false); }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!form.name || !form.email || !form.password) { setError("Por favor, preencha todos os campos."); return; }
    setLoading(true);

    try {
      const tokens = await register(form);
      localStorage.setItem("verifai_access", tokens.access_token);
      localStorage.setItem("verifai_refresh", tokens.refresh_token);
      const me = await getMe();
      signIn(tokens, me);
      navigate("/app");
    } catch (err) {
      const data = err?.response?.data;
      if (data && data.detail) {
        setError(Array.isArray(data.detail) ? data.detail[0].msg : data.detail);
      } else {
        setError("Não foi possível conectar ao servidor. Tente novamente.");
      }
    } finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 flex items-center justify-center p-5 overflow-hidden" style={{ backgroundColor: "#04080C" }}>
      <div className="pointer-events-none absolute inset-0" style={{ backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)", backgroundSize: "48px 48px", opacity: .3 }}/>

      <Link to="/" className="fixed top-8 right-8 z-[100] w-12 h-12 flex items-center justify-center rounded-full" style={{ backgroundColor: "#0A1520", border: "1px solid #132435", color: "#CDE8F0" }}>
         <span className="font-syne font-bold">✕</span>
      </Link>

      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-10">
           <Link to="/" className="no-underline">
              <h1 className="font-syne font-black text-4xl tracking-[10px] text-[#CDE8F0] uppercase">VERIFY</h1>
           </Link>
           <p className="font-mono text-[11px] mt-2 tracking-[4px] text-[#3A6070] font-bold">Crie sua conta grátis</p>
        </div>

        <div className="rounded-[2.5rem] p-10" style={{ background: "#0A1520", border: "1px solid #132435", boxShadow: "0 40px 120px rgba(0,0,0,.7)" }}>
           <div id="google-reg-btn" className="mb-8 w-full"></div>

           <div className="flex items-center gap-4 opacity-20 mb-8">
              <div className="flex-1 h-px bg-white"/>
              <span className="font-mono text-[9px] tracking-[4px]" style={{ color: "white" }}>OU USE SEU E-MAIL</span>
              <div className="flex-1 h-px bg-white"/>
           </div>

           <form onSubmit={handleSubmit} className="flex flex-col gap-6">
              <div className="flex flex-col gap-2">
                 <label className="font-mono text-[11px] tracking-[2px] uppercase text-[#3A6070]">Seu Nome</label>
                 <input type="text" value={form.name} onChange={e => setForm({...form, name: e.target.value})} 
                        className="w-full font-mono text-[14px] px-6 py-4 rounded-2xl outline-none"
                        style={{ backgroundColor: "#0F1E2E", border: "1px solid #132435", color: "#CDE8F0" }}
                        placeholder="Ex: João Silva"/>
              </div>
              <div className="flex flex-col gap-2">
                 <label className="font-mono text-[11px] tracking-[2px] uppercase text-[#3A6070]">Seu E-mail</label>
                 <input type="email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} 
                        className="w-full font-mono text-[14px] px-6 py-4 rounded-2xl outline-none"
                        style={{ backgroundColor: "#0F1E2E", border: "1px solid #132435", color: "#CDE8F0" }}
                        placeholder="contato@exemplo.com"/>
              </div>
              <div className="flex flex-col gap-2">
                 <label className="font-mono text-[11px] tracking-[2px] uppercase text-[#3A6070]">Crie uma Senha</label>
                 <input type="password" value={form.password} onChange={e => setForm({...form, password: e.target.value})} 
                        className="w-full font-mono text-[14px] px-6 py-4 rounded-2xl outline-none"
                        style={{ backgroundColor: "#0F1E2E", border: "1px solid #132435", color: "#CDE8F0" }}
                        placeholder="Mín. 6 caracteres"/>
              </div>
              
              {error && (
                <div className="p-5 rounded-2xl" style={{ backgroundColor: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.2)", color: "#ef4444" }}>
                  <span className="font-mono text-[12px]">{error}</span>
                </div>
              )}
              
              <button type="submit" disabled={loading} className="w-full font-syne font-black text-[15px] tracking-[4px] py-6 rounded-3xl" 
                      style={{ background: "linear-gradient(135deg,#00FF87,#00D4FF)", color: "#04080C", cursor: loading ? "wait" : "pointer" }}>
                {loading ? "CARREGANDO..." : "CRIAR CONTA AGORA"}
              </button>
           </form>
        </div>
        <p className="text-center font-mono text-[12px] mt-8 text-[#3A6070] tracking-widest">
           Já tem uma conta? <Link to="/login" style={{ color: "#00FF87", fontWeight: 'bold' }}>Clique aqui para Entrar</Link>
        </p>
      </div>
    </div>
  );
}
