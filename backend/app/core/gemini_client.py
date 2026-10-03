"""Bounded Gemini REST calls, honoring explicit model configuration."""
import base64
import os
import httpx


class GeneratedText(str):
    model_name: str


async def generate_text(contents, *, system_instruction=None, temperature=.1, json_output=True):
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Gemini não configurado.")
    primary = os.getenv("GEMINI_MODEL_NAME", "gemini-3.7-flash").strip()
    fallback = [m.strip() for m in os.getenv("GEMINI_FALLBACK_MODELS", "").split(",") if m.strip()]
    models = list(dict.fromkeys([primary, *fallback]))[:2]
    parts = []
    for part in contents if isinstance(contents, list) else [contents]:
        if isinstance(part, str):
            parts.append({"text": part})
        elif "inline_data" in part:
            inline = part["inline_data"]
            parts.append({"inlineData": {"mimeType": inline["mime_type"], "data": base64.b64encode(inline["data"]).decode()}})
        else:
            parts.append(part)
    config = {"temperature": temperature, "maxOutputTokens": 4096}
    if json_output:
        config["responseMimeType"] = "application/json"
    body = {"contents": [{"role": "user", "parts": parts}], "generationConfig": config}
    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    async with httpx.AsyncClient(timeout=15) as client:
        for index, model in enumerate(models):
            try:
                response = await client.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                             headers={"x-goog-api-key": key}, json=body)
            except httpx.TimeoutException:
                if index + 1 < len(models):
                    continue
                raise RuntimeError("Tempo limite do Gemini atingido.") from None
            if response.status_code in {404, 429, 503} and index + 1 < len(models):
                continue
            if response.status_code != 200:
                raise RuntimeError(f"Gemini indisponível (HTTP {response.status_code}).")
            candidates = response.json().get("candidates", [])
            if not candidates or candidates[0].get("finishReason") not in {None, "STOP"}:
                raise RuntimeError("Gemini não retornou uma resposta completa.")
            value = "".join(p.get("text", "") for p in candidates[0].get("content", {}).get("parts", []) if not p.get("thought"))
            if not value:
                raise RuntimeError("Resposta vazia do Gemini.")
            text = GeneratedText(value)
            text.model_name = model
            return text
