// Keep complete pasted addresses visible. Never use input maxLength/slicing:
// a cut query/path could point to different content than the user's original.
export const MAX_ANALYSIS_URL_LENGTH = 512;

export function analysisUrlInput(value) {
  const input = typeof value === "string" ? value.trim() : "";
  const normalized = /^https?:\/\//i.test(input) ? input : `https://${input}`;
  const length = Array.from(input ? normalized : "").length;
  const tooLong = length > MAX_ANALYSIS_URL_LENGTH;
  return {
    normalized,
    length,
    valid: Array.from(input).length >= 5 && !tooLong,
    error: tooLong
      ? "O link pode ter até 512 caracteres, incluindo https://. Seu endereço foi mantido inteiro; cole um endereço direto mais curto para a mesma página."
      : "",
  };
}
