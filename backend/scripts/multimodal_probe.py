"""Explicit free-tier controls and public HF metadata, never a precision claim.

No Hive, endpoint provisioning or automatic retries. Credit-using detector/ASR
controls require explicit confirmation of free credits without paid overage.
Outputs only statuses and comparison metrics, not credentials/user media.
"""
import argparse
import asyncio
import io
import json
import os
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

OCR_LINES = ["CONTROLE DE TESTE", "Nao pague taxa para liberar seu Pix.", "Valor: R$ 123,45", "Data: 03/10/2026"]


def printed_control():
    image = Image.new("RGB", (1100, 340), "white")
    font = ImageFont.truetype("DejaVuSans.ttf", 42)
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(OCR_LINES):
        draw.text((30, 20 + index * 75), line, font=font, fill="black")
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def normalized(value):
    value = unicodedata.normalize("NFKD", value.casefold())
    return " ".join(re.findall(r"[a-z0-9]+", "".join(c for c in value if not unicodedata.combining(c))))


def word_error_rate(expected, actual):
    previous = list(range(len(actual) + 1))
    for i, word in enumerate(expected, 1):
        current = [i]
        for j, observed in enumerate(actual, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (word != observed)))
        previous = current
    return previous[-1] / max(1, len(expected))


async def probe(name):
    if name == "serpapi_account":
        key = os.getenv("SERPAPI_KEY", "").strip()
        if not key:
            return {"status": "not_configured"}
        try:
            async with httpx.AsyncClient(timeout=10, trust_env=False, follow_redirects=False) as client:
                response = await client.get("https://serpapi.com/account.json", params={"api_key": key})
                # Never print the HTTP exception, full response, account ID or key.
                return {"status": "authenticated" if response.status_code == 200 else "invalid_credentials" if response.status_code in {401, 403} else "unavailable", "http_status": response.status_code}
        except Exception:
            return {"status": "unavailable"}
    if name == "sightengine_negative":
        from app.core.sightengine_client import check_deepfake
        value = await check_deepfake(printed_control())
        return {**{k: value.get(k) for k in ("available", "status", "reason", "genai_probability", "deepfake_probability")},
                "control_scope": "locally rendered text, known non-AI; NOT a natural human-photo control"}
    if name in {"gemini_pt", "assembly_pt", "gemini_silence"}:
        from app.services.audio_service import analyze_audio_quick_for_demonstration, transcribe_with_assemblyai
        import wave
        expected_text = "Oi vó, tudo bem? Estou saindo da aula agora. Te vejo mais tarde para o café."
        if name == "gemini_silence":
            output = io.BytesIO()
            with wave.open(output, "wb") as audio:
                audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
                audio.writeframes(b"\0\0" * 16000)
            data, expected_text = output.getvalue(), ""
        else:
            data = (Path(__file__).resolve().parents[2] / "frontend/public/audio/demo-conversa-sintetica.wav").read_bytes()
        if name == "assembly_pt":
            result = await transcribe_with_assemblyai(data)
            detail = {k: result.get(k) for k in ("available", "status", "reason", "model_used")}
        else:
            key = os.environ.pop("ASSEMBLYAI_API_KEY", None)
            try:
                result = await analyze_audio_quick_for_demonstration(data, "control.wav", "audio/wav")
            finally:
                if key is not None:
                    os.environ["ASSEMBLYAI_API_KEY"] = key
            detail = result.get("transcription_detail", {})
        expected, actual = normalized(expected_text).split(), normalized(result.get("transcription", "")).split()
        return {**detail, "exact_reference_match": actual == expected, "word_error_rate": word_error_rate(expected, actual),
                "expected_words": len(expected), "transcribed_words": len(actual), "scope": "known synthetic Portuguese speech or silence, NOT voice cloning detection"}
    if name == "gemini_models":
        key = os.getenv("GEMINI_API_KEY", "").strip()
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            response = await client.get("https://generativelanguage.googleapis.com/v1beta/models", headers={"x-goog-api-key": key})
            data = response.json()
            return {"http_status": response.status_code, "flash_models": [m["name"].removeprefix("models/") for m in data.get("models", [])
                if "flash" in m.get("name", "") and "tts" not in m["name"] and "generateContent" in m.get("supportedGenerationMethods", [])]}
    if name == "hf_metadata":
        # Hub metadata GETs do not create/provision/bill an inference endpoint.
        output = {}
        async with httpx.AsyncClient(timeout=15, trust_env=False, follow_redirects=False) as client:
            for model in ("Ateeqq/ai-vs-human-image-detector", "umm-maybe/AI-image-detector"):
                try:
                    response = await client.get(f"https://huggingface.co/api/models/{model}", params={"expand[]": "inferenceProviderMapping"})
                    data = response.json()
                    mapping = data.get("inferenceProviderMapping", {}) if isinstance(data, dict) else {}
                    config = await client.get(f"https://huggingface.co/{model}/resolve/main/config.json", follow_redirects=True)
                    labels = config.json().get("id2label", {}) if config.status_code == 200 else {}
                    output[model] = {"http_status": response.status_code, "providers": mapping, "labels": labels}
                except Exception:
                    output[model] = {"status": "metadata_unavailable"}
            token = os.getenv("HUGGINGFACE_API_TOKEN", "").strip()
            if token:
                try:
                    response = await client.get("https://huggingface.co/api/whoami-v2", headers={"Authorization": f"Bearer {token}"})
                    output["token"] = {"authenticated": response.status_code == 200, "http_status": response.status_code}
                except Exception:
                    output["token"] = {"authenticated": False, "status": "unavailable"}
        return output
    if name == "hf_image":
        from app.core import huggingface_client as hf
        hf.API_URL = "https://router.huggingface.co/hf-inference/models/Ateeqq/ai-vs-human-image-detector"
        os.environ["HUGGINGFACE_AI_LABEL"] = "ai"
        value = await hf.check_ai_image_hf((Path(__file__).resolve().parents[1] / "tests/fixtures/synthetic-cafe.png").read_bytes())
        return {k: value.get(k) for k in ("available", "status", "reason", "ai_probability", "model_used")}
    if name == "sightengine_image":
        from app.core.sightengine_client import check_deepfake
        value = await check_deepfake((Path(__file__).resolve().parents[1] / "tests/fixtures/synthetic-cafe.png").read_bytes())
        return {k: value.get(k) for k in ("available", "status", "reason", "genai_probability", "deepfake_probability")}
    if name == "assembly_audio":
        from app.services.audio_service import transcribe_with_assemblyai
        audio = Path(__file__).resolve().parents[2] / "frontend/public/audio/voz_humana_real.mp3"
        value = await transcribe_with_assemblyai(audio.read_bytes())
        expected = normalized("Oi vó, tudo bem? Estou saindo da aula agora. Te vejo mais tarde para o café.").split()
        actual = normalized(value.get("transcription", "")).split()
        return {**{k: value.get(k) for k in ("available", "status", "reason", "model_used")},
                "reference_word_recall": sum(word in actual for word in expected) / len(expected),
                "exact_reference_match": actual == expected, "transcribed_words": len(actual)}
    if name in {"gemini_ocr", "local_ocr"}:
        if name == "local_ocr":
            from app.services.local_ocr import extract_local_text
            value = await extract_local_text(printed_control())
        else:
            from app.core.gemini_analyzer import _extract_image_text_remote
            value = await _extract_image_text_remote(printed_control(), "image/png")
        actual = normalized(value.get("text", ""))
        return {**{k: value.get(k) for k in ("available", "status", "provider", "model_used", "reason")},
                "matched_control_lines": sum(normalized(line) in actual for line in OCR_LINES), "expected_lines": len(OCR_LINES)}
    if name == "gemini_audio":
        from app.services.audio_service import analyze_audio_quick_for_demonstration
        assembly_key = os.environ.pop("ASSEMBLYAI_API_KEY", None)
        audio = Path(__file__).resolve().parents[2] / "frontend/public/audio/voz_humana_real.mp3"
        try:
            value = await analyze_audio_quick_for_demonstration(audio.read_bytes(), "control.mp3", "audio/mpeg")
        finally:
            if assembly_key is not None:
                os.environ["ASSEMBLYAI_API_KEY"] = assembly_key
        expected = normalized("Oi vó, tudo bem? Estou saindo da aula agora. Te vejo mais tarde para o café.").split()
        actual = normalized(value.get("transcription", "")).split()
        return {**{k: value.get(k) for k in ("transcription_status", "transcription_provider", "transcription_detail")},
                "reference_word_recall": sum(word in actual for word in expected) / len(expected),
                "exact_reference_match": actual == expected, "transcribed_words": len(actual),
                "public_control_transcript": value.get("transcription", "")[:300],
                "reference_scope": "demo presentation text, recording origin unaudited; not a voice-authenticity label"}
    raise ValueError("Unsupported control")


async def main(args):
    load_dotenv(args.env_file)
    controls = [name.strip() for name in args.controls.split(",")]
    allowed = {"hf_metadata", "hf_image", "local_ocr", "gemini_ocr", "gemini_audio", "gemini_models", "gemini_pt", "gemini_silence",
               "sightengine_image", "sightengine_negative", "assembly_audio", "assembly_pt", "serpapi_account"}
    if not controls or any(name not in allowed for name in controls):
        raise ValueError("Unsupported control")
    if any(name in controls for name in ("hf_image", "sightengine_image", "sightengine_negative", "assembly_audio", "assembly_pt")) and not args.free_credits_confirmed:
        raise ValueError("Confirm free credits and no automatic paid overage before running these controls")
    os.environ["GEMINI_FALLBACK_MODELS"] = ""
    record = {"tested_at": datetime.now(timezone.utc).isoformat(), "scope": "Operational controls, NOT an accuracy benchmark", "results": {}}
    for name in controls:
        start = time.monotonic()
        value = await probe(name)
        value["elapsed_seconds"] = round(time.monotonic() - start, 2)
        record["results"][name] = value
        print(json.dumps({name: value}, ensure_ascii=False), flush=True)
    Path(args.output).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--controls", default="hf_metadata")
    parser.add_argument("--output", required=True)
    parser.add_argument("--free-credits-confirmed", action="store_true")
    asyncio.run(main(parser.parse_args()))
