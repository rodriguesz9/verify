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
        if not allowed or endpoint.scheme != "https" or endpoint.username or endpoint.password or endpoint.port not in (None, 443) or endpoint.query or endpoint.fragment:
            raise ValueError("Endpoint não autorizado")
    except ValueError:
        return {"available": False, "status": "invalid_configuration", "reason": "Use um endpoint HTTPS oficial do Hugging Face, sem credenciais na URL."}

    mime = "image/png" if file_bytes.startswith(b"\x89PNG") else "image/jpeg" if file_bytes.startswith(b"\xff\xd8") else "image/gif" if file_bytes.startswith(b"GIF") else "image/webp" if file_bytes.startswith(b"RIFF") else "application/octet-stream"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}", "Content-Type": mime}
    
    try:
        async with httpx.AsyncClient(timeout=15, trust_env=False, follow_redirects=False) as client:
            response = await client.post(API_URL, headers=headers, content=file_bytes)
            # HF might return 503 if model is loading
            if response.status_code == 503:
                return {"available": False, "status": "unavailable", "reason": "Modelo Hugging Face indisponível ou carregando."}
            
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
                    if artificial_score is not None:
                        return {"available": False, "status": "invalid_response", "reason": "Modelo retornou classes positivas duplicadas."}
                    artificial_score = _score(entry.get("score"))
            
            if artificial_score is None:
                return {"available": False, "status": "invalid_response", "reason": "Modelo não retornou a classe de IA esperada."}
            return {
                "available": True,
                "status": "success",
                "ai_probability": artificial_score,
                "is_likely_artificial": artificial_score > 0.8,
                "model_used": endpoint.path.removeprefix("/hf-inference/models/")[:150],
                "decision_role": "experimental_signal",
                "voting_eligible": False,
                "reason": "Detector experimental: sinal não calibrado, não participa do veredito. Não detecta manipulação facial nem comprova autenticidade."
            }
    except httpx.HTTPStatusError as exc:
        status = {401: "invalid_credentials", 403: "access_denied", 402: "quota_exhausted", 429: "rate_limited"}.get(exc.response.status_code, "error")
        return {"available": False, "status": status, "reason": f"Modelo Hugging Face indisponível (HTTP {exc.response.status_code}); sem reenvio ou contratação automática."}
    except httpx.TimeoutException:
        return {"available": False, "status": "timeout", "reason": "Modelo Hugging Face excedeu o prazo."}
    except Exception:
        return {"available": False, "status": "error", "reason": "Resposta Hugging Face indisponível ou inválida."}
