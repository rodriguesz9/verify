import os
import math
import httpx

SIGHTENGINE_API_USER = os.getenv("SIGHTENGINE_API_USER", "")
SIGHTENGINE_API_SECRET = os.getenv("SIGHTENGINE_API_SECRET", "")
ENDPOINT = "https://api.sightengine.com/1.0/check.json"


def _score(value):
    return float(value) if not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and 0 <= value <= 1 else None

async def check_deepfake(file_bytes: bytes) -> dict:
    """
    Check for deepfakes and AI generated images using Sightengine.
    Models used: 'deepfake', 'genai'
    """
    if not SIGHTENGINE_API_USER or not SIGHTENGINE_API_SECRET:
        return {"available": False, "status": "not_configured", "reason": "Credenciais Sightengine não configuradas."}

    params = {
        "models": "deepfake,genai",
        "api_user": SIGHTENGINE_API_USER,
        "api_secret": SIGHTENGINE_API_SECRET,
    }
    
    try:
        async with httpx.AsyncClient(timeout=15, trust_env=False, follow_redirects=False) as client:
            files = {"media": ("media", file_bytes)}
            # Credentials belong in the form, not URL query strings or access logs.
            response = await client.post(ENDPOINT, data=params, files=files)
            response.raise_for_status()
            data = response.json()
            
            # Extract scores
            deepfake_score = _score(data.get("type", {}).get("deepfake"))
            genai_score = _score(data.get("type", {}).get("ai_generated"))
            if data.get("status") != "success" or (genai_score is None and deepfake_score is None):
                return {"available": False, "status": "invalid_response", "reason": "Sightengine não retornou pontuações válidas."}
            
            return {
                "available": True,
                "status": "success",
                "deepfake_probability": deepfake_score,
                "genai_probability": genai_score,
                "is_likely_fake": (deepfake_score or 0) > 0.6 or (genai_score or 0) > 0.8,
                "raw": data
            }
    except httpx.HTTPStatusError as exc:
        status = {401: "invalid_credentials", 403: "access_denied", 402: "quota_exhausted",
                  429: "rate_limited", 503: "unavailable"}.get(exc.response.status_code, "error")
        return {"available": False, "status": status, "reason": f"Sightengine indisponível (HTTP {exc.response.status_code})."}
    except httpx.TimeoutException:
        return {"available": False, "status": "timeout", "reason": "Tempo limite do detector de imagem Sightengine atingido."}
    except Exception:
        return {"available": False, "status": "error", "reason": "Não foi possível obter resposta do Sightengine."}
