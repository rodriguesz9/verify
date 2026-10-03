"""Bounded Gemini REST calls, honoring explicit model configuration."""
import base64
import os
import re
import httpx


class GeneratedText(str):
    model_name: str


class GeminiError(RuntimeError):
    def __init__(self, reason, status="error", http_status=None):
        self.status, self.http_status = status, http_status
        super().__init__(reason)


async def generate_text(contents, *, system_instruction=None, temperature=.1, json_output=True, max_tokens=2048, model_name=None, response_schema=None):
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise GeminiError("Gemini não configurado.", "not_configured")
    primary = model_name or os.getenv("GEMINI_MODEL_NAME", "gemini-3.7-flash").strip()
    fallback = [] if model_name else [m.strip() for m in os.getenv("GEMINI_FALLBACK_MODELS", "").split(",") if m.strip()]
    models = list(dict.fromkeys([primary, *fallback]))[:2]
    if any(not re.fullmatch(r"[a-zA-Z0-9._-]{1,120}", model) for model in models):
        raise GeminiError("Identificador de modelo Gemini inválido.", "invalid_configuration")
    parts = []
    for part in contents if isinstance(contents, list) else [contents]:
        if isinstance(part, str):
            parts.append({"text": part})
        elif "inline_data" in part:
            inline = part["inline_data"]
            parts.append({"inlineData": {"mimeType": inline["mime_type"], "data": base64.b64encode(inline["data"]).decode()}})
        else:
            parts.append(part)
    config = {"temperature": temperature, "maxOutputTokens": max(64, min(4096, max_tokens))}
    if json_output:
        config["responseMimeType"] = "application/json"
        if response_schema:
            config["responseSchema"] = response_schema
    body = {"contents": [{"role": "user", "parts": parts}], "generationConfig": config}
    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    async with httpx.AsyncClient(timeout=20, trust_env=False, follow_redirects=False) as client:
        for index, model in enumerate(models):
            # Simple extraction/OCR needs low latency, not default deep reasoning.
            # thinkingLevel is documented only for Gemini 3+; no legacy breakage.
            body["generationConfig"] = {**config, **({"thinkingConfig": {"thinkingLevel": "LOW"}} if model.startswith("gemini-3") else {})}
            try:
                response = await client.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                             headers={"x-goog-api-key": key}, json=body)
            except httpx.TimeoutException:
                if index + 1 < len(models):
                    continue
                raise GeminiError("Tempo limite do Gemini atingido.", "timeout") from None
            except httpx.HTTPError:
                raise GeminiError("Conexão Gemini indisponível.") from None
            if response.status_code in {404, 503} and index + 1 < len(models):
                continue
            if response.status_code != 200:
                raise GeminiError(f"Gemini indisponível (HTTP {response.status_code}).",
                                  "rate_limited" if response.status_code == 429 else "error", response.status_code)
            try:
                candidates = response.json().get("candidates", [])
                if not candidates or candidates[0].get("finishReason") not in {None, "STOP"}:
                    raise ValueError("incomplete")
                value = "".join(p.get("text", "") for p in candidates[0].get("content", {}).get("parts", []) if not p.get("thought"))
                if not value or len(value) > 30000:
                    raise ValueError("empty or oversized")
            except (ValueError, TypeError, KeyError, IndexError, AttributeError):
                raise GeminiError("Gemini não retornou uma resposta completa e válida.", "invalid_response") from None
            text = GeneratedText(value)
            text.model_name = model
            return text
