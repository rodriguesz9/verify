// Count Unicode characters as the API does; never silently truncate a claim.
export function textInputState(value) {
  const text = typeof value === "string" ? value.trim() : "";
  const length = Array.from(text).length;
  const valid = length >= 10 && length <= 5000;
  return {text, length, valid, message: length > 5000
    ? "A mensagem pode ter até 5.000 caracteres. Escolha um trecho completo para analisar; seu texto não foi cortado."
    : "Cole uma mensagem com pelo menos 10 caracteres para fazer a checagem."};
}

export function analysisErrorMessage(error) {
  const detail = error?.response?.data?.detail;
  if (detail && typeof detail === "object" && detail.error === "limite_diario") return "Seu limite diário de consultas foi atingido hoje.";
  if (error?.response?.status === 422) {
    const fields = Array.isArray(detail) ? detail : [];
    const text = fields.find((item) => Array.isArray(item?.loc) && ["text", "texts"].some((key) => item.loc.includes(key)));
    if (text?.type === "string_too_long") return "A mensagem pode ter até 5.000 caracteres. Seu texto não foi cortado; escolha um trecho completo e tente novamente.";
    if (text?.type === "string_too_short") return "Cole uma mensagem com pelo menos 10 caracteres para fazer a checagem.";
    return typeof detail === "string" ? detail : "Confira o conteúdo enviado: cada mensagem precisa ter de 10 a 5.000 caracteres. Nenhuma análise foi concluída.";
  }
  if (typeof detail === "string") return detail;
  if (error?.message === "Envie um arquivo de até 25 MB.") return error.message;
  if (["ECONNABORTED", "ETIMEDOUT"].includes(error?.code)) return "A análise demorou mais do que o esperado. Não foi possível confirmar sua conclusão. Aguarde antes de tentar novamente.";
  if (error?.code === "ERR_NETWORK") return "Não foi possível conectar ao serviço de checagem. Confira sua conexão e tente novamente mais tarde.";
  return "Não foi possível concluir a checagem no momento. Nenhuma conclusão sobre o conteúdo foi produzida. Tente novamente mais tarde.";
}
