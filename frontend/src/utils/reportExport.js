const TOKEN_MAX_LENGTH = 512 * 1024;

// This is only an interface guard. Signature, expiry and ownership are checked
// again by the server; browser fields are never evidence of authenticity.
export function pdfExportState(result, now = Date.now()) {
  if (!result || typeof result !== "object") return "unavailable";
  const token = result.pdf_snapshot_token;
  if (typeof token !== "string" || !token.startsWith("vpdf1.") || token.length > TOKEN_MAX_LENGTH) {
    return "unavailable";
  }
  const expires = result.pdf_snapshot_expires_at;
  if (!Number.isSafeInteger(expires) || expires <= 0) return "unavailable";
  return expires * 1000 <= now ? "expired" : "ready";
}

export function publicReportDetails(result) {
  if (!result || typeof result !== "object") return result;
  // Do not expose a bearer export credential in copyable technical details.
  const { pdf_snapshot_token: _token, text_review_token: _reviewToken, ...details } = result;
  return details;
}

export async function pdfExportError(error) {
  const status = error?.response?.status;
  if (status === 410) return "O prazo para exportar terminou. Se a análise foi salva, abra-a pelo histórico para baixar o mesmo resultado.";
  if (status === 401 || status === 403) return "Entre na mesma conta que fez a análise para baixar este relatório.";
  if (status === 429) return "Muitos pedidos de exportação. Aguarde e tente novamente; a análise não será refeita.";
  return "Não foi possível baixar o PDF. Tente novamente. Isso não refaz a análise nem chama os detectores.";
}
