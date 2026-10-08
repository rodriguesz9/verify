export function extractedReviewText(report) {
  if (report?.content_type === "image") return typeof report.forensics?.ocr?.text === "string" ? report.forensics.ocr.text : "";
  return typeof report?.transcription === "string" ? report.transcription : "";
}

export function textReviewState(report, now = Date.now()) {
  const token = report?.text_review_token;
  const text = textInputState(extractedReviewText(report));
  if (report?.text_review_status !== "ready" || typeof token !== "string" || !token.startsWith("vrev1.") || token.length > 32 * 1024
    || !Number.isSafeInteger(report.text_review_expires_at) || !text.valid) return "unavailable";
  return report.text_review_expires_at * 1000 <= now ? "expired" : "ready";
}

export function reviewedTextValid(text, confirmed) {
  return confirmed === true && textInputState(text).valid;
}

export function withoutReviewCredential(report) {
  const { text_review_token: _token, ...rest } = report;
  return rest;
}

export function textReviewError(error) {
  const status = error?.response?.status;
  if (status === 410) return "O prazo para conferir terminou. Copie seu texto e faça uma nova checagem na opção Texto.";
  if (status === 401 || status === 403) return "Entre na mesma conta que enviou o arquivo para concluir a conferência.";
  if (status === 422) return "Confira um texto de 10 a 5000 caracteres. Se o vínculo expirou, faça uma nova checagem na opção Texto.";
  if (status === 429) return "Limite de consultas atingido. Seu texto continua aqui; aguarde antes de tentar novamente.";
  return "Não foi possível checar o texto agora. Sua edição foi mantida; tente novamente mais tarde.";
}
import {textInputState} from "./analysisInput.js";
