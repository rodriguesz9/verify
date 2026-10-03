import os
import asyncio
import re
import httpx

GPTZERO_API_KEY = os.getenv("GPTZERO_API_KEY", "")
ENDPOINT = "https://api.gptzero.me/v2/predict/text"


def _sentence_count(text: str) -> int:
    return max(1, len(re.findall(r"[.!?…]+", text)))


def _lexical_diversity(text: str) -> float:
    words = re.findall(r"[\wÀ-ÿ]+", text.lower())
    if not words:
        return 0.0
    return len(set(words)) / len(words)


def _repetition_score(text: str) -> float:
    sentences = [s.strip() for s in re.split(r"[.!?…]+", text.lower()) if s.strip()]
    if len(sentences) < 2:
        return 0.0
    repeated = 0
    for i, left in enumerate(sentences):
        left_words = set(left.split())
        for right in sentences[i + 1:]:
            right_words = set(right.split())
            overlap = len(left_words & right_words) / max(1, min(len(left_words), len(right_words)))
            if overlap > 0.6:
                repeated += 1
    return repeated / max(1, len(sentences) * (len(sentences) - 1) / 2)


def _punctuation_pattern_score(text: str) -> float:
    if not text:
        return 0.0
    exclamations = text.count("!")
    questions = text.count("?")
    ellipses = text.count("...")
    return min(1.0, (exclamations + questions * 0.5 + ellipses * 0.5) / max(1, len(text) / 120))


def heuristic_ai_markers(text: str) -> dict:
    """Detect linguistic markers often associated with AI-generated text."""
    words = re.findall(r"[\wÀ-ÿ]+", text.lower())
    sentences = [s.strip() for s in re.split(r"[.!?…]+", text) if s.strip()]
    if len(words) < 20 or len(sentences) < 2:
        return {"available": False, "reason": "Texto curto demais para análise linguística."}

    avg_sentence = len(words) / len(sentences)
    diversity = _lexical_diversity(text)
    repetition = _repetition_score(text)
    punctuation_score = _punctuation_pattern_score(text)

    # AI text often has uniform sentence length and high lexical diversity
    uniformity = 1 - min(1.0, abs(avg_sentence - 18) / 30)
    ai_probability = (
        0.35 * uniformity
        + 0.25 * (1 - diversity)
        + 0.20 * repetition
        + 0.20 * punctuation_score
    )
    ai_probability = max(0.0, min(1.0, ai_probability))

    return {
        "available": True,
        "ai_probability": round(ai_probability, 3),
        "is_likely_ai": ai_probability > 0.7,
        "markers": {
            "average_sentence_length": round(avg_sentence, 2),
            "lexical_diversity": round(diversity, 3),
            "repetition_score": round(repetition, 3),
            "punctuation_pattern_score": round(punctuation_score, 3),
            "word_count": len(words),
            "sentence_count": len(sentences),
        },
        "note": "Marcadores linguísticos heurísticos; use como evidência complementar.",
    }


async def detect_ai_text(text: str) -> dict:
    """Detect AI-written text using GPTZero plus local heuristics."""
    async def gptzero():
        if not GPTZERO_API_KEY:
            return {"available": False, "reason": "GPTZero API key not configured.", "source": "gptzero"}
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
                doc = data.get("documents", [{}])[0]
                prob = doc.get("completely_generated_prob", 0)
                return {
                    "available": True,
                    "ai_probability": prob,
                    "is_likely_ai": prob > 0.7,
                    "raw": data,
                    "source": "gptzero",
                }
        except Exception as e:
            return {"available": False, "reason": str(e), "source": "gptzero"}

    async def heuristic():
        return heuristic_ai_markers(text)

    results = await asyncio.gather(gptzero(), heuristic())
    gptzero_result, heuristic_result = results

    available = [gptzero_result] if gptzero_result.get("available") else []
    if not available:
        return {"available": False, "ai_probability": None, "reason": "Detector de texto indisponível; marcadores linguísticos não determinam autoria.", "markers": heuristic_result.get("markers", {})}

    combined_probability = gptzero_result.get("ai_probability", 0)
    combined_probability = max(0.0, min(1.0, combined_probability))
    return {
        "available": True,
        "ai_probability": round(combined_probability, 3),
        "is_likely_ai": combined_probability > 0.7,
        "sources": [r.get("source") for r in available if r.get("source")],
        "markers": heuristic_result.get("markers", {}),
        "note": "Probabilidade combinada entre GPTZero e marcadores linguísticos.",
    }
