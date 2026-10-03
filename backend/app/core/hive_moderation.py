"""Legacy Hive interface sharing the same validated parser and transport."""
from app.services.hive_service import check_hive_media, parse_hive_scores


def _parse_hive_response(data: dict) -> dict:
    report = parse_hive_scores(data)
    return {**report, "ai_probability": report.get("ai_generated_score"),
            "is_ai_generated": report.get("is_ai_detected") if report["available"] else None,
            "confidence": "uncalibrated", "classes": report.get("raw_classes", {})}


async def analyze_media_hive(file_bytes: bytes, content_type: str) -> dict:
    media_type = "audio" if content_type.startswith("audio/") else "video" if content_type.startswith("video/") else "image"
    report = await check_hive_media(file_bytes, "evidence", media_type)
    return {**report, "ai_probability": report.get("ai_generated_score"),
            "is_ai_generated": report.get("is_ai_detected") if report["available"] else None}
