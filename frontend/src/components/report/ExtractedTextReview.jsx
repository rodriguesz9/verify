import { useEffect, useRef, useState } from "react";
import { Check, FileText } from "lucide-react";
import { extractedReviewText, reviewedTextValid, textReviewState } from "../../utils/textReview.js";

export default function ExtractedTextReview({ report, file, busy, error, onConfirm, onSkip }) {
  const original = extractedReviewText(report);
  const [text, setText] = useState(original);
  const [confirmed, setConfirmed] = useState(false);
  const [previewUrl, setPreviewUrl] = useState("");
  const [now, setNow] = useState(Date.now);
  const heading = useRef(null);
  const state = textReviewState(report, now);
  const method = report.content_type === "image" ? "OCR" : "transcrição";
  const coverage = report.content_type === "video" ? report.audio_analysis?.provider_coverage : report.provider_coverage;
  const provider = report.content_type === "image" ? report.forensics?.ocr?.provider : coverage?.transcription?.provider;
  useEffect(() => { heading.current?.focus(); }, []);
  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  useEffect(() => {
    const delay = Math.max(0, report.text_review_expires_at * 1000 - Date.now() + 1);
    const timer = setTimeout(() => setNow(Date.now()), Math.min(delay, 2147483647));
    return () => clearTimeout(timer);
  }, [report.text_review_expires_at]);

  return <section className="text-review-panel min-w-0 rounded-xl border border-[#00D4FF]/40 bg-[#0A1520] p-5 sm:p-8" aria-labelledby="review-heading" aria-busy={busy}>
    <p className="text-[#00D4FF] text-sm mb-3 flex items-center gap-2"><FileText size={18} aria-hidden="true" /> Etapa 2: confira a leitura</p>
    <h2 id="review-heading" ref={heading} tabIndex={-1} className="font-syne font-bold text-2xl outline-none">O texto está igual ao arquivo?</h2>
    <p id="review-help" className="mt-3 text-base leading-7 text-[#A7BFCD]">A leitura automática pode errar. Confira principalmente <strong>“não”, valores, datas e pedidos de dinheiro</strong>. Corrija no campo abaixo. Ainda não consultamos fontes para checar essas afirmações.</p>
    <p className="mt-3 text-sm text-[#8AA2B4] break-words">{file?.name || report.filename} · {method}{provider ? ` por ${provider}` : ""}</p>
    {previewUrl ? <div className="mt-4 rounded-lg bg-[#04080C] p-3">
      {report.content_type === "image" ? <img src={previewUrl} alt="Arquivo enviado, para comparar com a leitura" className="max-h-72 max-w-full mx-auto object-contain" />
        : report.content_type === "video" ? <video controls preload="metadata" src={previewUrl} className="max-h-72 w-full" aria-label="Vídeo enviado para conferência" />
        : <audio controls preload="metadata" src={previewUrl} className="w-full" aria-label="Áudio enviado para conferência" />}
    </div> : null}
    <label htmlFor="reviewed-text" className="block mt-5 mb-2 font-bold text-base">Texto para checar</label>
    <textarea id="reviewed-text" value={text} disabled={busy} maxLength={5000} rows={6} aria-describedby="review-help review-count"
      onChange={(event) => { setText(event.target.value); setConfirmed(false); }}
      className="w-full min-w-0 rounded-lg bg-[#04080C] border border-[#325A70] focus:border-[#00D4FF] focus:ring-2 focus:ring-[#00D4FF]/40 p-4 text-base leading-7 resize-y text-[#CDE8F0]" />
    <p id="review-count" className="mt-2 text-sm text-[#A7BFCD]">{text.trim().length} de 5000 caracteres · mínimo de 10.</p>
    <details className="mt-4 rounded-lg border border-[#325A70] p-3 text-sm">
      <summary className="cursor-pointer font-bold">Comparar com a leitura automática original</summary>
      <blockquote className="mt-3 whitespace-pre-wrap break-words max-h-56 overflow-y-auto pr-2 leading-6">{original}</blockquote>
    </details>
    <label className="mt-5 flex items-start gap-3 text-base leading-7 cursor-pointer">
      <input type="checkbox" checked={confirmed} disabled={busy} onChange={(event) => setConfirmed(event.target.checked)} className="mt-1.5 h-5 w-5 shrink-0 accent-[#00D4FF]" />
      <span>Conferi o texto com o arquivo. Quero checar este texto.</span>
    </label>
    <p className="mt-3 text-sm leading-6 text-[#A7BFCD]">Será uma nova checagem de texto, com sua edição identificada. A análise original de imagem/voz não muda. Confirmar a leitura não confirma que a mensagem seja verdadeira. A consulta usa o limite diário de texto.</p>
    {state === "expired" ? <p role="status" className="mt-4 text-[#FFCB55] text-base">O prazo de 15 minutos terminou. Copie seu texto e faça uma nova checagem na opção Texto.</p> : null}
    {error ? <p role="alert" className="mt-4 text-[#FFCB55] text-base leading-7">{error}</p> : null}
    <div className="mt-6 flex flex-col gap-3 sm:flex-row">
      <button type="button" disabled={busy || state !== "ready" || !reviewedTextValid(text, confirmed)} onClick={() => onConfirm(text.trim())}
        className="min-h-12 px-5 py-3 rounded-lg bg-[#00D4FF] text-[#04080C] font-bold flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed focus-visible:ring-2 focus-visible:ring-white">
        <Check size={18} aria-hidden="true" /> {busy ? "Consultando fontes..." : "Checar texto conferido"}
      </button>
      <button type="button" disabled={busy} onClick={onSkip} className="min-h-12 px-5 py-3 rounded-lg border border-[#325A70] text-[#CDE8F0] font-bold disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-[#00D4FF]">Ver só sinais da mídia</button>
    </div>
  </section>;
}
