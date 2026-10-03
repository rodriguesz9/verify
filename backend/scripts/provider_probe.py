"""Explicit, small live-provider smoke test. Never prints credentials or raw replies."""
import argparse
import asyncio
import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv


async def main(args):
    if args.env_file:
        load_dotenv(args.env_file)
    from app.services.media_validation import validate_media
    from app.services.media_analysis import analyze_media
    from app.services.gemini_service import get_ai_voice_speech
    fixture = Path(__file__).resolve().parents[1] / "tests/fixtures/synthetic-cafe.png"
    media = await validate_media(fixture.read_bytes(), "sample.png", "image/png")
    report = await analyze_media(media)
    record = {"tested_at": datetime.now(timezone.utc).isoformat(), "scope": "Single synthetic image, not an accuracy benchmark",
              "verdict": report["verdict"], "analysis_status": report["analysis_status"],
              "providers": {name: {"available": result.get("available"), "status": result.get("status", "unavailable"),
                                   "reason": result.get("reason"), "ai_score": report["provider_coverage"].get(name, {}).get("ai_score")}
                            for name, result in report["forensics"].items() if name in {"sightengine", "huggingface", "hive", "ocr", "gemini_vision"}}}
    if args.tts:
        speech = await get_ai_voice_speech("Esta é uma demonstração do Verify. Confirme a origem antes de compartilhar.")
        record["tts"] = {key: speech.get(key) for key in ("available", "status", "model_used", "duration_sec")}
        if speech.get("available"):
            data = base64.b64decode(speech["audio_data"])
            checked = await validate_media(data, "generated-demo.wav", "audio/wav")
            record["tts"]["decoded"] = checked.kind == "audio"
            Path(args.output).with_suffix(".wav").write_bytes(data)
    Path(args.output).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file")
    parser.add_argument("--output", required=True)
    parser.add_argument("--tts", action="store_true")
    asyncio.run(main(parser.parse_args()))
