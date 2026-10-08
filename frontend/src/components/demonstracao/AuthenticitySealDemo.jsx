import { useState, useRef, useEffect } from "react";
import { captureSeal, verifySeal } from "../../services/api";
import { createMediaLifecycle } from "../../services/mediaLifecycle.js";

export default function AuthenticitySealDemo() {
  const [step, setStep] = useState(1); // 1: Captura, 2: Selado, 3: Verificado
  const [streamActive, setStreamActive] = useState(false);
  const [capturedBlob, setCapturedBlob] = useState(null);
  const [capturedPreview, setCapturedPreview] = useState(null);
  const [tamperedBlob, setTamperedBlob] = useState(null);
  const [sealData, setSealData] = useState(null);
  const [verificationResult, setVerificationResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const cameraRequestRef = useRef(null);
  const lifecycleRef = useRef(null);
  if (!lifecycleRef.current) lifecycleRef.current = createMediaLifecycle();
  const lifecycle = lifecycleRef.current;

  const startCamera = async () => {
    const scope = lifecycle.capture();
    if (cameraRequestRef.current !== null || !lifecycle.isCurrent(scope)) return;
    cameraRequestRef.current = scope;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
      if (!lifecycle.acceptStream(stream, scope)) return;
      if (!videoRef.current) { lifecycle.releaseStream(stream); return; }
      videoRef.current.srcObject = stream;
      videoRef.current.play().catch(() => {});
      setStreamActive(true);
      setError("");
    } catch (err) {
      if (!lifecycle.isCurrent(scope)) return;
      // Fallback: draw a synthesized photo on the canvas if webcam not permitted
      drawFallbackCanvas("Foto da Demonstração");
      setStreamActive(false);
    } finally {
      if (cameraRequestRef.current === scope) cameraRequestRef.current = null;
    }
  };

  const stopCamera = () => {
    const mounted = lifecycle.isCurrent(lifecycle.capture());
    lifecycle.invalidate();
    cameraRequestRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    if (mounted) setStreamActive(false);
  };

  useEffect(() => {
    lifecycle.activate();
    drawFallbackCanvas("Imagem educativa — não é uma foto real");
    return () => { lifecycle.dispose(); stopCamera(); };
  }, [lifecycle]);

  const drawFallbackCanvas = (label) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    canvas.width = 640;
    canvas.height = 480;

    // Background gradient
    const grad = ctx.createLinearGradient(0, 0, 640, 480);
    grad.addColorStop(0, "#0A1520");
    grad.addColorStop(1, "#002B44");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 640, 480);

    // Text & graphics
    ctx.fillStyle = "#00D4FF";
    ctx.font = "bold 28px sans-serif";
    ctx.fillText("VERIFY — FOTO OFICIAL", 40, 80);

    ctx.fillStyle = "#CDE8F0";
    ctx.font = "20px monospace";
    ctx.fillText(label, 40, 140);
    ctx.fillText(`Timestamp: ${new Date().toLocaleTimeString()}`, 40, 180);

    // Some shapes
    ctx.strokeStyle = "#00FF87";
    ctx.lineWidth = 4;
    ctx.strokeRect(40, 220, 200, 200);
    ctx.fillStyle = "#00FF87";
    ctx.fillText("ÁREA DE PROVA", 50, 330);
  };

  // Step 1: Capture Photo
  const handleCapture = async () => {
    const scope = lifecycle.capture();
    if (!lifecycle.isCurrent(scope)) return;
    setLoading(true);
    setError("");
    setVerificationResult(null);

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    if (streamActive && videoRef.current) {
      canvas.width = videoRef.current.videoWidth || 640;
      canvas.height = videoRef.current.videoHeight || 480;
      ctx.drawImage(videoRef.current, 0, 0);
    } else {
      drawFallbackCanvas("Foto da Demonstração");
    }

    canvas.toBlob(async (blob) => {
      if (!lifecycle.isCurrent(scope)) return;
      if (!blob) { setError("Não foi possível capturar a imagem."); setLoading(false); return; }
      const file = new File([blob], "captura_original.jpg", { type: "image/jpeg" });
      setCapturedBlob(file);
      setCapturedPreview(canvas.toDataURL("image/jpeg"));

      try {
        const seal = await captureSeal(file);
        if (!lifecycle.isCurrent(scope)) return;
        setSealData(seal);
        setStep(2);
      } catch (err) {
        if (lifecycle.isCurrent(scope)) setError("Erro ao gerar selo de autenticidade.");
      } finally {
        if (lifecycle.isCurrent(scope)) setLoading(false);
      }
    }, "image/jpeg", 0.92);
  };

  // Step 2A: Verify Original Photo
  const handleVerifyOriginal = async () => {
    if (!capturedBlob) return;
    const scope = lifecycle.capture();
    if (!lifecycle.isCurrent(scope)) return;
    setLoading(true);
    setError("");
    try {
      const res = await verifySeal(capturedBlob);
      if (!lifecycle.isCurrent(scope)) return;
      setVerificationResult(res);
      setStep(3);
    } catch (err) {
      if (lifecycle.isCurrent(scope)) setError("Erro ao verificar selo.");
    } finally {
      if (lifecycle.isCurrent(scope)) setLoading(false);
    }
  };

  // Step 2B: Tamper 1 single pixel and verify
  const handleSimulateTamper = async () => {
    if (!capturedPreview) return;
    const scope = lifecycle.capture();
    if (!lifecycle.isCurrent(scope)) return;
    setLoading(true);
    setError("");

    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    const img = new Image();

    img.onload = () => {
      if (!lifecycle.isCurrent(scope)) return;
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);

      // Alter exactly 1 pixel color to demonstrate cryptographic hash sensitivity
      const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      imgData.data[0] = (imgData.data[0] + 50) % 255; // alter red channel of pixel (0,0)
      ctx.putImageData(imgData, 0, 0);

      canvas.toBlob(async (blob) => {
        if (!lifecycle.isCurrent(scope)) return;
        if (!blob) { setError("Não foi possível preparar a imagem."); setLoading(false); return; }
        const tamperedFile = new File([blob], "foto_alterada_1pixel.jpg", { type: "image/jpeg" });
        setTamperedBlob(tamperedFile);

        try {
          const res = await verifySeal(tamperedFile);
          if (!lifecycle.isCurrent(scope)) return;
          setVerificationResult(res);
          setStep(3);
        } catch (err) {
          if (lifecycle.isCurrent(scope)) setError("Erro na verificação de adulteração.");
        } finally {
          if (lifecycle.isCurrent(scope)) setLoading(false);
        }
      }, "image/jpeg", 0.92);
    };
    img.src = capturedPreview;
  };

  const handleReset = () => {
    setStep(1);
    setCapturedBlob(null);
    setCapturedPreview(null);
    setTamperedBlob(null);
    setSealData(null);
    setVerificationResult(null);
    setError("");
    setLoading(false);
    stopCamera();
    drawFallbackCanvas("Imagem educativa — não é uma foto real");
  };

  return (
    <div className="bg-[#0A1520] border border-[#132435] rounded-3xl p-8 max-w-4xl mx-auto shadow-2xl">
      {/* Header */}
      <div className="text-center mb-8">
        <span className="font-mono text-xs text-[#00FF87] tracking-widest uppercase font-bold block mb-2">
          RECURSO 2 • REGISTRO DE INTEGRIDADE SHA-256
        </span>
        <h2 className="font-syne font-black text-3xl md:text-4xl text-[#CDE8F0] uppercase tracking-tight">
          Registro de Integridade <span className="text-[#00D4FF]">(SHA-256)</span>
        </h2>
        <p className="font-mono text-sm text-[#3A6070] mt-3 max-w-2xl mx-auto">
          Registra os bytes do arquivo para comparar versões. Qualquer mudança de bytes, incluindo metadados ou recompressão, muda o hash. Não comprova que a cena seja real e não é uma credencial C2PA.
        </p>
      </div>

      {/* 3-Step Progress Indicators */}
      <button type="button" onClick={startCamera} className="mb-5 rounded-xl border border-[#00D4FF] p-3 text-sm text-[#00D4FF]">Ativar câmera (opcional)</button>
      <div className="flex flex-wrap items-center justify-center gap-2 mb-8">
        {[
          { num: 1, label: "1. Captura" },
          { num: 2, label: "2. Selo Digital" },
          { num: 3, label: "3. Teste de Violação" }
        ].map((s) => (
          <div
            key={s.num}
            className={`flex items-center gap-2 font-mono text-xs font-bold px-4 py-2 rounded-full border ${
              step >= s.num
                ? "bg-[#00D4FF]/20 border-[#00D4FF] text-[#00D4FF]"
                : "bg-[#060D14] border-[#132435] text-[#3A6070]"
            }`}
          >
            <span>{s.num}.</span>
            <span>{s.label}</span>
          </div>
        ))}
      </div>

      {/* Step 1: Camera / Capture View */}
      {step === 1 && (
        <div className="space-y-6">
          <div className="relative rounded-3xl overflow-hidden bg-black aspect-video flex items-center justify-center border border-[#132435]">
            <video
              ref={videoRef}
              playsInline
              autoPlay
              muted
              className={`w-full h-full object-cover ${streamActive ? "block" : "hidden"}`}
            />
            <canvas ref={canvasRef} className={`w-full h-full object-cover ${streamActive ? "hidden" : "block"}`} />

            <div className="absolute top-4 left-4 px-3 py-1 rounded-full bg-black/60 border border-white/10 font-mono text-[11px] text-[#00FF87] flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#00FF87] animate-ping" />
              {streamActive ? "Câmera ao Vivo Ativa" : "Modo Simulação Gráfica"}
            </div>
          </div>

          <button
            type="button"
            disabled={loading}
            onClick={handleCapture}
            className="w-full py-5 rounded-2xl bg-gradient-to-r from-[#00D4FF] to-[#00FF87] text-[#04080C] font-syne font-black text-lg tracking-widest uppercase hover:scale-[1.02] active:scale-[0.98] transition-all cursor-pointer shadow-xl"
          >
            {loading ? "GERANDO SELO CRIPTOGRÁFICO..." : "📸 TIRAR FOTO E EMITIR SELO DE AUTENTICIDADE"}
          </button>
        </div>
      )}

      {/* Step 2: Seal Generated + Choose Verification Route */}
      {step === 2 && sealData && (
        <div className="space-y-6 animate-fade-in">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            {/* Captured Photo */}
            <div className="rounded-2xl overflow-hidden border border-[#00FF87] shadow-[0_0_30px_rgba(0,255,135,0.2)]">
              <img src={capturedPreview} alt="Captura" className="w-full h-auto object-cover" />
            </div>

            {/* Seal Certificate Box */}
            <div className="p-6 rounded-2xl bg-[#060D14] border border-[#00FF87]/50 space-y-4">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#00FF87]/20 border border-[#00FF87] font-mono text-xs text-[#00FF87] font-bold">
                ✓ SELO EMITIDO COM SUCESSO
              </div>

              <div>
                <span className="font-mono text-[10px] text-[#8BAAC0] uppercase block font-bold">
                  HASH SHA-256 DO ARQUIVO:
                </span>
                <code className="font-mono text-xs text-[#00D4FF] break-all bg-black/50 p-2 rounded block mt-1">
                  {sealData.file_hash_sha256}
                </code>
              </div>

              <div>
                <span className="font-mono text-[10px] text-[#8BAAC0] uppercase block font-bold">
                  TIMESTAMP OFICIAL DO SERVIDOR (UTC):
                </span>
                <span className="font-mono text-xs text-[#CDE8F0] block mt-1">{sealData.captured_at}</span>
              </div>

              <div>
                <span className="font-mono text-[10px] text-[#8BAAC0] uppercase block font-bold">
                  ASSINATURA HMAC-SHA256:
                </span>
                <code className="font-mono text-[11px] text-[#FFB800] break-all bg-black/50 p-1 rounded block mt-1">
                  {sealData.signature_hmac?.slice(0, 32)}...
                </code>
              </div>
            </div>
          </div>

          {/* Controles de teste da demonstração */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
            <button
              type="button"
              disabled={loading}
              onClick={handleVerifyOriginal}
              className="p-5 rounded-2xl bg-[#00FF87]/15 border border-[#00FF87] text-[#00FF87] font-syne font-black text-sm tracking-wider uppercase hover:bg-[#00FF87]/25 transition-all cursor-pointer text-center"
            >
              ✅ TESTE 1: VERIFICAR FOTO ORIGINAL (DEVE PASSAR)
            </button>

            <button
              type="button"
              disabled={loading}
              onClick={handleSimulateTamper}
              className="p-5 rounded-2xl bg-[#FF3B5C]/15 border border-[#FF3B5C] text-[#FF3B5C] font-syne font-black text-sm tracking-wider uppercase hover:bg-[#FF3B5C]/25 transition-all cursor-pointer text-center"
            >
              🚨 TESTE 2: ADULTERAR 1 PIXEL (DEVE VIOLAR O SELO)
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Result of Verification */}
      {step === 3 && verificationResult && (
        <div className="space-y-6 animate-fade-in">
          <div
            className={`p-8 rounded-3xl border text-center ${
              verificationResult.integridade_verificada
                ? "bg-[#00FF87]/10 border-[#00FF87] shadow-[0_0_50px_rgba(0,255,135,0.3)]"
                : "bg-[#FF3B5C]/10 border-[#FF3B5C] shadow-[0_0_50px_rgba(255,59,92,0.3)]"
            }`}
          >
            <span className="text-6xl block mb-4">{verificationResult.integridade_verificada ? "🛡️" : "🚨"}</span>

            <h3
              className={`font-syne font-black text-2xl md:text-3xl uppercase mb-3 ${
                verificationResult.integridade_verificada ? "text-[#00FF87]" : "text-[#FF3B5C]"
              }`}
            >
              {verificationResult.integridade_verificada ? "BYTES CORRESPONDEM AO REGISTRO" : "BYTES DIFERENTES OU SEM REGISTRO"}
            </h3>

            <p className="font-mono text-sm text-[#CDE8F0] max-w-xl mx-auto leading-relaxed">
              {verificationResult.mensagem}
            </p>

            <div className="mt-6 p-4 rounded-xl bg-black/50 border border-white/10 max-w-lg mx-auto text-left font-mono text-xs">
              <span className="text-[#8BAAC0] block mb-1">Status Criptográfico:</span>
              <span className={verificationResult.integridade_verificada ? "text-[#00FF87] font-bold" : "text-[#FF3B5C] font-bold"}>
                {verificationResult.status}
              </span>
            </div>
          </div>

          <div className="flex justify-center gap-4">
            <button
              type="button"
              onClick={handleReset}
              className="px-8 py-4 rounded-xl bg-[#132435] text-[#CDE8F0] font-syne font-bold text-xs uppercase tracking-widest hover:bg-[#1C364F] transition-all cursor-pointer"
            >
              REINICIAR DEMONSTRAÇÃO DO SELO
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 mt-6 rounded-2xl bg-[#FF3B5C]/15 border border-[#FF3B5C] text-[#FF3B5C] font-mono text-xs text-center">
          {error}
        </div>
      )}
    </div>
  );
}
