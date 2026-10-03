import os
import httpx
from urllib.parse import urlsplit
from app.core.sightengine_client import _score

HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN", "")
# A token alone does not provision a hosted detector. Require a tested endpoint.
API_URL = os.getenv("HUGGINGFACE_IMAGE_API_URL", "").strip()

async def check_ai_image_hf(file_bytes: bytes) -> dict:
    """
    Check for AI generated images using Hugging Face Inference API.
    """
    if not HUGGINGFACE_API_TOKEN:
        return {"available": False, "status": "not_configured", "reason": "Token Hugging Face não configurado."}
    if not API_URL:
        return {"available": False, "status": "not_configured", "reason": "Configure HUGGINGFACE_IMAGE_API_URL com um detector hospedado e validado."}
    try:
        endpoint = urlsplit(API_URL)
        host = (endpoint.hostname or "").lower()
        allowed = host in {"router.huggingface.co", "api-inference.huggingface.co"} or host.endswith(".endpoints.huggingface.cloud")
        if not allowed or endpoint.scheme != "https" or endpoint.username or endpoint.password or endpoint.port not in (None, 443):
            raise ValueError("Endpoint não autorizado")
    except ValueError:
        return {"available": False, "status": "invalid_configuration", "reason": "Use um endpoint HTTPS oficial do Hugging Face, sem credenciais na URL."}

    mime = "image/png" if file_bytes.startswith(b"\x89PNG") else "image/jpeg" if file_bytes.startswith(b"\xff\xd8") else "image/gif" if file_bytes.startswith(b"GIF") else "image/webp" if file_bytes.startswith(b"RIFF") else "application/octet-stream"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}", "Content-Type": mime}
    
    try:
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            response = await client.post(API_URL, headers=headers, content=file_bytes)
            # HF might return 503 if model is loading
            if response.status_code == 503:
                return {"available": False, "reason": "Model is loading on Hugging Face."}
            
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                return {"available": False, "status": "invalid_response", "reason": "Modelo não retornou uma lista de classes."}
            
            # Usually returns a list of classes with scores
            # [{'label': 'artificial', 'score': 0.99}, {'label': 'human', 'score': 0.01}]
            artificial_score = None
            ai_label = os.getenv("HUGGINGFACE_AI_LABEL", "artificial").strip().casefold()
            for entry in data:
                if isinstance(entry, dict) and ai_label and str(entry.get("label", "")).casefold() == ai_label:
                    artificial_score = _score(entry.get("score"))
            
            if artificial_score is None:
                return {"available": False, "status": "invalid_response", "reason": "Modelo não retornou a classe de IA esperada."}
            return {
                "available": True,
                "status": "success",
                "ai_probability": artificial_score,
                "is_likely_artificial": artificial_score > 0.8,
                "raw": data
            }
    except httpx.HTTPStatusError as exc:
        return {"available": False, "status": "error", "reason": f"Modelo Hugging Face indisponível (HTTP {exc.response.status_code})."}
    except Exception:
        return {"available": False, "status": "error", "reason": "Resposta Hugging Face indisponível ou inválida."}
