import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../services/api";

function strengthScore(p) {
  let s = 0;
  if (p.length >= 8)         s++;
  if (/[A-Z]/.test(p))       s++;
  if (/[0-9]/.test(p))       s++;
  if (/[^A-Za-z0-9]/.test(p)) s++;
  return s;
}

const LABELS = ["", "FRACA", "RAZOÁVEL", "BOA", "FORTE"];
const COLORS = ["", "#FF3B5C", "#FFB830", "#00D4FF", "#00FF87"];

export default function RegisterPage() {
  const navigate = useNavigate();
  const [name,     setName]     = useState("");
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [confirm,  setConfirm]  = useState("");
  const [error,    setError]    = useState("");
  const [loading,  setLoading]  = useState(false);
  const [success,  setSuccess]  = useState(false);

  const strength    = strengthScore(password);
  const colStrength = COLORS[strength] || "#1A3A50";
  const pwMatch     = password && confirm && password === confirm;
  const pwNoMatch   = confirm && password !== confirm;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (password !== confirm)  { setError("As senhas não coincidem."); return; }
    if (strength < 2)           { setError("Senha muito fraca. Use maiúsculas e números."); return; }

    setLoading(true);
    try {
      await register({ name: name.trim(), email: email.trim().toLowerCase(), password });
      // ── SUCCESS: show message then redirect to LOGIN (not home) ──────────
      setSuccess(true);
      setTimeout(() => navigate("/login"), 2000);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map(d => d.msg).join(" · "));
      } else if (typeof detail === "object" && detail !== null) {
        setError(JSON.stringify(detail));
      } else {
        setError(typeof detail === "string" ? detail : "Erro ao criar conta. Tente novamente.");
      }
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg">
        <div className="text-center fade-1">
          <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-5"
            style={{ background: "rgba(0,255,135,.15)", border: "2px solid #00FF87" }}>
            <span style={{ color: "#00FF87", fontSize: 28 }}>✓</span>
          </div>
          <h2 className="font-syne font-extrabold text-xl text-text mb-2">Conta criada!</h2>
          <p className="font-mono text-[12px]" style={{ color: "#3A6070" }}>
            Redirecionando para o login…
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen flex items-center justify-center px-5 py-10">
      <div className="pointer-events-none fixed inset-0" style={{
        backgroundImage: "linear-gradient(#132435 1px,transparent 1px),linear-gradient(90deg,#132435 1px,transparent 1px)",
        backgroundSize: "48px 48px", opacity: .3 }}/>

      <div className="w-full max-w-md relative z-10">
        {/* brand */}
        <div className="text-center mb-8 fade-1">
          <Link to="/" style={{ textDecoration: "none" }}>
            <div className="flex justify-center mb-3">
              <svg width="40" height="40" viewBox="0 0 28 28">
                <polygon points="14,2 26,8 26,20 14,26 2,20 2,8" fill="none" stroke="#00FF87" strokeWidth="1.5"/>
                <circle cx="14" cy="14" r="4" fill="#00FF87" opacity=".8"/>
              </svg>
            </div>
            <h1 className="font-syne font-extrabold text-2xl tracking-widest text-text">
              VERIF<span style={{ color: "#00D4FF" }}>AI</span>
            </h1>
          </Link>
          <p className="font-mono text-[11px] mt-1" style={{ color: "#3A6070" }}>CRIAR CONTA GRÁTIS</p>
        </div>

        <div className="rounded-2xl overflow-hidden fade-2"
          style={{ background: "#0A1520", border: "1px solid #132435", boxShadow: "0 40px 80px rgba(0,0,0,.5)" }}>
          <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-4">

            {/* Name */}
            <div>
              <label className="font-mono text-[10px] tracking-widest block mb-2" style={{ color: "#3A6070" }}>NOME COMPLETO</label>
              <input type="text" required value={name} onChange={e => setName(e.target.value)}
                placeholder="Seu nome"
                className="w-full font-mono text-[13px] px-4 py-3 rounded-lg"
                style={{ background: "#0F1E2E", border: "1px solid #132435", color: "#CDE8F0", outline: "none" }}/>
            </div>

            {/* Email */}
            <div>
              <label className="font-mono text-[10px] tracking-widest block mb-2" style={{ color: "#3A6070" }}>E-MAIL</label>
              <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
                placeholder="seu@email.com" autoComplete="email"
                className="w-full font-mono text-[13px] px-4 py-3 rounded-lg"
                style={{ background: "#0F1E2E", border: "1px solid #132435", color: "#CDE8F0", outline: "none" }}/>
            </div>

            {/* Password */}
            <div>
              <label className="font-mono text-[10px] tracking-widest block mb-2" style={{ color: "#3A6070" }}>SENHA</label>
              <input type="password" required value={password} onChange={e => setPassword(e.target.value)}
                placeholder="Mínimo 8 caracteres" autoComplete="new-password"
                className="w-full font-mono text-[13px] px-4 py-3 rounded-lg"
                style={{ background: "#0F1E2E", border: "1px solid #132435", color: "#CDE8F0", outline: "none" }}/>
              {password && (
                <div className="mt-2 flex items-center gap-2">
                  <div className="flex gap-1 flex-1">
                    {[1,2,3,4].map(i => (
                      <div key={i} className="h-1 flex-1 rounded-full transition-all"
                        style={{ background: i <= strength ? colStrength : "#1A3A50" }}/>
                    ))}
                  </div>
                  <span className="font-mono text-[9px] tracking-widest" style={{ color: colStrength }}>
                    {LABELS[strength]}
                  </span>
                </div>
              )}
              <p className="font-mono text-[10px] mt-1.5" style={{ color: "#1A3A50" }}>
                Mín. 8 chars · 1 maiúscula · 1 número
              </p>
            </div>

            {/* Confirm */}
            <div>
              <label className="font-mono text-[10px] tracking-widest block mb-2" style={{ color: "#3A6070" }}>CONFIRMAR SENHA</label>
              <input type="password" required value={confirm} onChange={e => setConfirm(e.target.value)}
                placeholder="Repita a senha" autoComplete="new-password"
                className="w-full font-mono text-[13px] px-4 py-3 rounded-lg"
                style={{
                  background: "#0F1E2E",
                  border: `1px solid ${pwNoMatch ? "#FF3B5C" : pwMatch ? "#00FF87" : "#132435"}`,
                  color: "#CDE8F0", outline: "none",
                }}/>
              {pwMatch   && <p className="font-mono text-[10px] mt-1" style={{ color: "#00FF87" }}>✓ Senhas coincidem</p>}
              {pwNoMatch && <p className="font-mono text-[10px] mt-1" style={{ color: "#FF3B5C" }}>✗ Senhas não coincidem</p>}
            </div>

            {error && (
              <div className="px-3 py-2.5 rounded-lg font-mono text-[11px]"
                style={{ background: "rgba(255,59,92,.1)", border: "1px solid rgba(255,59,92,.3)", color: "#FF3B5C" }}>
                ✗ {error}
              </div>
            )}

            {/* plan info */}
            <div className="flex items-center gap-2 py-2 px-3 rounded-lg"
              style={{ background: "rgba(0,212,255,.05)", border: "1px solid rgba(0,212,255,.15)" }}>
              <span className="font-mono text-[9px] tracking-widest px-2 py-0.5 rounded"
                style={{ background: "rgba(0,212,255,.15)", color: "#00D4FF" }}>FREE</span>
              <span className="font-mono text-[10px]" style={{ color: "#3A6070" }}>
                3 análises/dia · Upgrade disponível
              </span>
            </div>

            <button type="submit" disabled={loading}
              className="w-full font-syne font-bold text-[13px] tracking-widest py-3 rounded-lg transition-all mt-1"
              style={{
                background: loading ? "#0A1520" : "linear-gradient(135deg,#00D4FF,#00FF87)",
                color: loading ? "#3A6070" : "#04080C",
                border: "none", cursor: loading ? "not-allowed" : "pointer",
                boxShadow: !loading ? "0 0 24px rgba(0,212,255,.3)" : "none",
              }}>
              {loading ? "CRIANDO CONTA…" : "CRIAR CONTA GRÁTIS →"}
            </button>
          </form>
        </div>

        <p className="text-center font-mono text-[11px] mt-5 fade-3" style={{ color: "#3A6070" }}>
          Já tem conta?{" "}
          <Link to="/login" style={{ color: "#00D4FF", textDecoration: "none" }}>Fazer login</Link>
        </p>
      </div>
    </div>
  );
}
