"""
Hive Moderation API – free developer tier.
Detects AI-generated images, videos and audio.
Docs: https://docs.thehive.ai/
"""

import os
import httpx

HIVE_API_KEY = os.getenv("HIVE_API_KEY", "")
HIVE_ENDPOINT = "https://api.thehive.ai/api/v2/task/sync"

# Model IDs for each media type
HIVE_MODELS = {
    "image": "ai_generated_image_detection",  # detects Stable Diffusion, Midjourney, DALL-E
    "video": "ai_generated_video_detection",
    "audio": "ai_generated_voice_detection",
}


def _parse_hive_response(data: dict) -> dict:
    """
    Extract the most relevant score from Hive's response.
    Returns: { "ai_probability": float, "classes": [...], "raw": dict }
    """
    try:
        output = data.get("status", [{}])[0].get("response", {}).get("output", [{}])[0]
        classes = output.get("classes", [])

        # Find "ai-generated" or similar class
        ai_score = 0.0
        for cls in classes:
            name = cls.get("class", "").lower()
            if any(k in name for k in ["ai", "generated", "synthetic", "fake", "deepfake"]):
                ai_score = max(ai_score, cls.get("score", 0.0))

        # If no clear class found, take highest score
        if ai_score == 0.0 and classes:
            ai_score = max(c.get("score", 0.0) for c in classes)

        return {
            "ai_probability": round(ai_score, 4),
            "is_ai_generated": ai_score > 0.7,
            "confidence": "high" if ai_score > 0.85 else "medium" if ai_score > 0.6 else "low",
            "classes": classes[:5],
        }
    except Exception:
        return {"ai_probability": None, "is_ai_generated": None, "confidence": "unknown", "classes": []}


async def analyze_media_hive(file_bytes: bytes, content_type: str) -> dict:
    """
    Send media to Hive for AI-generation detection.
    Returns parsed result dict.
    """
    if not HIVE_API_KEY:
        return {
            "available": False,
            "reason": "HIVE_API_KEY não configurada.",
            "ai_probability": None,
        }

    # Pick model based on content type
    if "video" in content_type:
        model = HIVE_MODELS["video"]
    elif "audio" in content_type or "mpeg" in content_type or "wav" in content_type:
        model = HIVE_MODELS["audio"]
    else:
        model = HIVE_MODELS["image"]

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                HIVE_ENDPOINT,
                headers={"Authorization": f"token {HIVE_API_KEY}"},
                files={"media": ("upload", file_bytes, content_type)},
                data={"model": model},
            )
            response.raise_for_status()
            data = response.json()

        result = _parse_hive_response(data)
        result["available"] = True
        result["model"] = model
        return result

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 402:
            return {"available": False, "reason": "Limite da Hive API atingido.", "ai_probability": None}
        return {"available": False, "reason": f"Hive API error {e.response.status_code}", "ai_probability": None}
    except Exception as e:
        return {"available": False, "reason": str(e)[:80], "ai_probability": None}
