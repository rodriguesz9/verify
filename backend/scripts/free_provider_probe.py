"""Opt-in, single-call smoke probes. No raw responses/keys or automatic retries.

Run from backend with PYTHONPATH=. and an existing private --env-file.
Hive ONLY runs with --hive-budget 0.01: exactly ONE image request ($0.006
at the price displayed in the official playground on 2026-10-03).
Never runs Hive audio/video, SerpAPI, TTS, AssemblyAI, or a paid HF endpoint.
"""
import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv


async def main(args):
    load_dotenv(args.env_file, override=False)
    from app.core.gemini_client import generate_text
    from app.core.openrouter_service import analyze_with_openrouter
    from app.services.hive_service import check_hive_media
    from app.core.sightengine_client import check_deepfake
    from app.core.serper_client import search_news
    from app.core.gemini_analyzer import extract_text_from_image
    from app.services.audio_service import analyze_audio_quick_for_demonstration
    fixture = Path(__file__).resolve().parents[1] / "tests/fixtures/synthetic-cafe.png"
    record = {"tested_at": datetime.now(timezone.utc).isoformat(), "scope": "Integration smoke test, NOT an accuracy benchmark", "providers": {}}
    for name in args.providers.split(","):
        name = name.strip()
        if name == "gemini":
            # Screenshot confirms this Google project is Free Tier. No fallback
            # / automatic model upgrade; exactly one configured-model call.
            os.environ["GEMINI_FALLBACK_MODELS"] = ""
            try:
                value = await generate_text('Responda apenas JSON {"ok": true}. Não avalie veracidade.', json_output=True, max_tokens=64)
                data = json.loads(value)
                result = {"available": data == {"ok": True}, "status": "success" if data == {"ok": True} else "invalid_response", "model_used": value.model_name}
            except Exception as exc:
                # Only our sanitized RuntimeError has a printable reason.
                result = {"available": False, "status": getattr(exc, "status", "error"), "reason": str(exc) if isinstance(exc, RuntimeError) else "Provedor indisponível ou resposta inválida."}
        elif name == "gemini_ocr":
            result = await extract_text_from_image(fixture.read_bytes(), "image/png")
            result = {**{key: result.get(key) for key in ("available", "status", "provider", "model_used", "reason")},
                      "text_characters": len(result.get("text", "")), "control": "synthetic cafe: no intentional text"}
        elif name == "gemini_audio":
            # Public demo recording, origin not audited; only transcription tested.
            os.environ["ASSEMBLYAI_API_KEY"] = ""
            audio = Path(__file__).resolve().parents[2] / "frontend/public/audio/voz_humana_real.mp3"
            result = await analyze_audio_quick_for_demonstration(audio.read_bytes(), "sample.mp3", "audio/mpeg")
            result = {key: result.get(key) for key in ("transcription_status", "transcription_provider", "transcription_detail", "verdict", "analysis_status", "tempo_processamento_ms")}
        elif name == "openrouter":
            result = await analyze_with_openrouter("O Brasil está na América do Sul.")
            result.pop("claims", None)
        elif name == "hive":
            if args.hive_budget != .01:
                raise ValueError("Hive requires the explicit authorized $0.01 test budget")
            os.environ["HIVE_API_VERSION"], os.environ["HIVE_V3_MEDIA_TYPES"] = "v3", "image"
            result = await check_hive_media(fixture.read_bytes(), "synthetic-control.png", "image", "image/png")
            result = {key: result.get(key) for key in ("available", "status", "reason", "api_version", "model_used", "ai_generated_score", "deepfake_score")}
            result.update(requests=1, estimated_cost_usd=.006, authorized_ceiling_usd=.01)
        elif name == "sightengine":
            result = await check_deepfake(fixture.read_bytes())
            result = {key: result.get(key) for key in ("available", "status", "reason", "genai_probability", "deepfake_probability")}
        elif name == "serper":
            result = await search_news("Brasil América do Sul")
            result = {"available": result.status in {"success", "no_results"}, "status": result.status, "reason": result.reason, "matches": len(result)}
        else:
            raise ValueError("Unsupported probe: no arbitrary endpoint or billable fallback")
        record["providers"][name] = result
        print(json.dumps({name: result}, ensure_ascii=False), flush=True)
    Path(args.output).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--providers", default="gemini,openrouter")
    parser.add_argument("--hive-budget", type=float, default=0)
    parser.add_argument("--output", required=True)
    asyncio.run(main(parser.parse_args()))
