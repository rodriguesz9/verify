"""Compatibility consolidation and optional real speech generation."""
import base64
import io
import os
import wave
import httpx
from app.services.evidence_policy import media_report, forensic_contract


async def consolidate_forensic_report(filename, metadata_res, c2pa_res, detection_res, context_res, audio_res=None):
    # A language model is not allowed to invent new detector evidence or certainty.
    layers = {**detection_res, "metadata": metadata_res, "c2pa": c2pa_res, "context": context_res}
    return forensic_contract(media_report(layers, "audio" if audio_res else "image"))


async def get_ai_voice_speech(text="Olá! Esta é uma demonstração de fala gerada por IA."):
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return {"available": False, "status": "no_api_key", "message": "Gemini não configurado."}
    model = os.getenv("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
    try:
        async with httpx.AsyncClient(timeout=20, trust_env=False, follow_redirects=False) as client:
            response = await client.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": key}, json={
                    "contents": [{"parts": [{"text": f"Leia em português do Brasil: {text[:1500]}"}]}],
                    "generationConfig": {"responseModalities": ["AUDIO"],
                        "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}}}}})
        response.raise_for_status()
        parts = response.json()["candidates"][0]["content"]["parts"]
        inline = next(part["inlineData"] for part in parts if "inlineData" in part)
        raw = base64.b64decode(inline["data"])
        # Gemini returns mono 16-bit PCM, not MP3. Package actual samples as WAV.
        if not inline.get("mimeType", "").startswith("audio/L16"):
            raise ValueError("Formato de áudio inesperado")
        output = io.BytesIO()
        with wave.open(output, "wb") as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(24000); wav.writeframes(raw)
        return {"available": True, "status": "success", "mime_type": "audio/wav",
                "audio_data": base64.b64encode(output.getvalue()).decode(),
                "duration_sec": len(raw) / (24000 * 2), "model_used": model}
    except Exception:
        return {"available": False, "status": "error", "message": "Fala indisponível no provedor. Nenhum áudio simulado foi produzido."}
