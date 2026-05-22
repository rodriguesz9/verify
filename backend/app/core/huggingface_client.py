import os
import httpx

HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN", "")
# Example model: umm-maybe/AI-image-detector
API_URL = "https://api-inference.huggingface.co/models/umm-maybe/AI-image-detector"

async def check_ai_image_hf(file_bytes: bytes) -> dict:
    """
    Check for AI generated images using Hugging Face Inference API.
    """
    if not HUGGINGFACE_API_TOKEN:
        return {"available": False, "reason": "Hugging Face token not configured."}

    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(API_URL, headers=headers, content=file_bytes)
            # HF might return 503 if model is loading
            if response.status_code == 503:
                return {"available": False, "reason": "Model is loading on Hugging Face."}
            
            response.raise_for_status()
            data = response.json()
            
            # Usually returns a list of classes with scores
            # [{'label': 'artificial', 'score': 0.99}, {'label': 'human', 'score': 0.01}]
            artificial_score = 0
            for entry in data:
                if entry.get("label") == "artificial":
                    artificial_score = entry.get("score", 0)
            
            return {
                "available": True,
                "ai_probability": artificial_score,
                "is_likely_artificial": artificial_score > 0.8,
                "raw": data
            }
    except Exception as e:
        return {"available": False, "reason": str(e)}
