"""Opt-in Sightengine ai_speech. Requires provider entitlement, not just a key."""
import os
import httpx
from app.core.sightengine_client import _score

ENDPOINT = "https://api.sightengine.com/1.0/audio/check.json"


async def detect_synthetic_speech(data: bytes, mime_type="audio/wav") -> dict:
    if os.getenv("SIGHTENGINE_AUDIO_ENABLED", "false").lower() != "true":
        return {"available": False, "status": "disabled", "reason": "Detector acústico Sightengine não habilitado; exige acesso ao modelo ai_speech."}
    user, secret = os.getenv("SIGHTENGINE_API_USER", ""), os.getenv("SIGHTENGINE_API_SECRET", "")
    if not user or not secret:
        return {"available": False, "status": "not_configured", "reason": "Credenciais Sightengine ausentes."}
    suffix = {"audio/wav": "wav", "audio/mpeg": "mp3", "audio/ogg": "ogg", "audio/webm": "webm",
              "audio/flac": "flac", "audio/mp4": "m4a", "audio/aac": "aac"}.get(mime_type, "wav")
    try:
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            response = await client.post(ENDPOINT, data={"models": "ai_speech", "api_user": user, "api_secret": secret},
                                         files={"audio": (f"evidence.{suffix}", data, mime_type)})
        if response.status_code != 200:
            return {"available": False, "status": "error", "reason": f"Sightengine áudio indisponível (HTTP {response.status_code}); confira acesso/quota do modelo."}
        payload = response.json()
        score = _score(payload.get("type", {}).get("ai_speech"))
        if payload.get("status") != "success" or score is None:
            raise ValueError("Invalid score")
        return {"available": True, "status": "success", "ai_speech_score": score, "model": "ai_speech"}
    except httpx.TimeoutException:
        return {"available": False, "status": "timeout", "reason": "Tempo limite do detector acústico."}
    except Exception:
        return {"available": False, "status": "invalid_response", "reason": "Resposta acústica inválida; não há conclusão."}
