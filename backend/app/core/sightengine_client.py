import os
import httpx

SIGHTENGINE_API_USER = os.getenv("SIGHTENGINE_API_USER", "")
SIGHTENGINE_API_SECRET = os.getenv("SIGHTENGINE_API_SECRET", "")
ENDPOINT = "https://api.sightengine.com/1.0/check.json"

async def check_deepfake(file_bytes: bytes) -> dict:
    """
    Check for deepfakes and AI generated images using Sightengine.
    Models used: 'deepfake', 'genai'
    """
    if not SIGHTENGINE_API_USER or not SIGHTENGINE_API_SECRET:
        return {"available": False, "reason": "Sightengine API keys not configured."}

    params = {
        "models": "deepfake,genai",
        "api_user": SIGHTENGINE_API_USER,
        "api_secret": SIGHTENGINE_API_SECRET,
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            files = {"media": ("media", file_bytes)}
            response = await client.post(ENDPOINT, params=params, files=files)
            response.raise_for_status()
            data = response.json()
            
            # Extract scores
            deepfake_score = data.get("deepfake", {}).get("probability", 0)
            genai_score = data.get("genai", {}).get("score", 0)
            
            return {
                "available": True,
                "deepfake_probability": deepfake_score,
                "genai_probability": genai_score,
                "is_likely_fake": deepfake_score > 0.6 or genai_score > 0.8,
                "raw": data
            }
    except Exception as e:
        return {"available": False, "reason": str(e)}
