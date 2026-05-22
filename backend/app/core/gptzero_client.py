import os
import httpx

GPTZERO_API_KEY = os.getenv("GPTZERO_API_KEY", "")
ENDPOINT = "https://api.gptzero.me/v2/predict/text"

async def detect_ai_text(text: str) -> dict:
    """
    Detect AI-written text using GPTZero API.
    """
    if not GPTZERO_API_KEY:
        return {"available": False, "reason": "GPTZero API key not configured."}

    headers = {
        "x-api-key": GPTZERO_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "document": text,
        "version": "2024-01-09"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(ENDPOINT, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # documents: [{ 'completely_generated_prob': 0.99, ... }]
            doc = data.get("documents", [{}])[0]
            prob = doc.get("completely_generated_prob", 0)
            
            return {
                "available": True,
                "ai_probability": prob,
                "is_likely_ai": prob > 0.7,
                "raw": data
            }
    except Exception as e:
        return {"available": False, "reason": str(e)}
