"""Executable local subset of the 30-case matrix. No API or accuracy claims."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch


async def run(output):
    backend = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend))
    import dotenv
    dotenv.load_dotenv = lambda *_args, **_kwargs: False
    for key in list(os.environ):
        if "API_KEY" in key or "API_TOKEN" in key or key in {"SIGHTENGINE_API_USER", "SIGHTENGINE_API_SECRET"}:
            os.environ.pop(key, None)
    os.environ.update({"OPENROUTER_ENABLED": "false", "HIVE_V3_MEDIA_TYPES": "", "HIVE_API_VERSION": "v3",
                       "SIGHTENGINE_AUDIO_ENABLED": "false", "WAYBACK_API_ENABLED": "false"})
    from app.services.claim_policy import text_report
    from app.core.scam_detector import analyze_scam_indicators
    from app.services.local_ocr import extract_local_text
    from app.services.media_validation import validate_media, extract_video_frames, extract_video_audio
    from app.services.media_analysis import analyze_media
    from app.api.check_url import fetch_page_text
    from app.services.public_fetch import FetchedResource
    from app.services.audio_service import analyze_audio_quick_for_demonstration
    from app.services.public_fetch import _validate_public_url
    from fastapi import HTTPException
    os.environ["LOCAL_OCR_ENABLED"] = "true"
    results = []
    base = "O município de Exemplo inaugurou a ponte em 2024"

    def review(rating="Verdadeiro", domain="aosfatos.org"):
        return {"claim_text": base, "rating": rating, "publisher": "FIXTURE, NOT A REAL CHECK",
                "url": f"https://{domain}/synthetic-fixture-not-a-real-check",
                "review_date": "2026-09-01T12:00:00Z", "retrieval_provider": "google_fact_check"}

    pair = [review(), review(domain="boatos.org")]
    rules = [
        ("TXT01", base, pair, "supported", "Authentic"),
        ("TXT02", base, [review("Falso"), review("Falso", "boatos.org")], "refuted", "False"),
        ("TXT03", "O município de Exemplo não inaugurou a ponte em 2024", pair, "unverified", "Suspicious"),
        ("TXT04", base, [review(domain="checamos.afp.com"), review(domain="factcheck.afp.com")], "unverified", "Suspicious"),
        ("TXT05", base, [*pair, review("Falso", "fullfact.org")], "conflicting", "Suspicious"),
        ("TXT06", "O município de Exemplo inaugurou a ponte em 2025 e cobrou R$ 500", pair, "unverified", "Suspicious"),
        ("TXT07", "Não pague uma taxa para liberar seu Pix.", [], "unverified", "Suspicious"),
        ("TXT08", "Pague uma taxa para liberar seu Pix.", [], "unverified", "Scam"),
    ]
    for case, text, sources, truth, verdict in rules:
        report = text_report(text, sources, analyze_scam_indicators(text))
        results.append({"case_id": case, "execution": "local_rule_simulated_evidence_NOT_UI_NOT_REAL_API",
                        "expected": {"veracity": truth, "verdict": verdict},
                        "observed": {"veracity": report["veracity_status"], "verdict": report["verdict"]},
                        "passed": report["veracity_status"] == truth and report["verdict"] == verdict})
    fixtures = backend / "tests/fixtures/validation/ocr"
    manifest = json.loads((fixtures / "manifest.json").read_text())
    ids = {"impresso-base.png": "OCR01", "afirmativo.png": "OCR02", "numeros.png": "OCR03",
           "datas.png": "OCR04", "sem-texto.png": "OCR06"}
    for item in manifest:
        data = (fixtures / item["file"]).read_bytes()
        report = await extract_local_text(data)
        expected = "\n".join(item["reference_lines"])
        actual = report.get("text", "")
        results.append({"case_id": ids[item["file"]], "execution": "local_tesseract_NOT_UI",
                        "sha256": hashlib.sha256(data).hexdigest(), "expected_text": expected,
                        "observed_text": actual, "status": report.get("status"),
                        "passed": actual == expected and (report.get("status") == "success" if expected else report.get("status") == "no_text")})
    extended = backend / "tests/fixtures/validation/extended"
    extended_manifest = json.loads((extended / "manifest.json").read_text(encoding="utf-8"))
    degraded = next(item for item in extended_manifest if item["case_id"] == "OCR05")
    data = (extended / degraded["file"]).read_bytes()
    ocr = await extract_local_text(data)
    expected = "\n".join(degraded["reference_lines"])
    actual = ocr.get("text", "")
    literal = ocr.get("status") == "success" and actual == expected
    abstained = ocr.get("status") in {"low_quality", "no_text"} and not actual
    results.append({"case_id": "OCR05", "execution": "local_tesseract_NOT_UI", "sha256": hashlib.sha256(data).hexdigest(),
                    "expected_text": expected, "observed_text": actual, "status": ocr.get("status"),
                    "literal_match": literal, "abstained": abstained, "passed": literal or abstained})
    html = (backend / "tests/fixtures/validation/links/pagina-controle.html").read_bytes()
    resource = FetchedResource(html, "text/html", "https://example.test/final", "utf-8")
    with patch("app.api.check_url.fetch_public_resource", new=AsyncMock(return_value=resource)):
        page = await fetch_page_text("https://example.test/control")
    reference = "CONTROLE FICTÍCIO. Não pague uma taxa para liberar seu Pix. Valor informado: R$ 123,45. Data informada: 03/10/2026."
    report = text_report(page["text"], [], analyze_scam_indicators(page["text"]))
    results.append({"case_id": "LNK10", "execution": "local_HTML_simulated_HTTP_NOT_PUBLIC_URL_NOT_UI",
                    "sha256": hashlib.sha256(html).hexdigest(), "expected_text": reference, "observed_text": page["text"],
                    "veracity_status": report["veracity_status"], "verdict": report["verdict"],
                    "passed": page["text"] == reference and report["veracity_status"] == "unverified" and report["verdict"] != "Scam"})
    silence = (backend / "tests/fixtures/recorder-no-duration.webm").read_bytes()
    # Fake key activates the local silence gate; mocked providers prove no call.
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only", "ASSEMBLYAI_API_KEY": "test-only"}), \
         patch("app.core.audio_checker.transcribe_and_extract_audio", new=AsyncMock()) as gemini, \
         patch("app.services.audio_service.transcribe_with_assemblyai", new=AsyncMock()) as assembly:
        media = await validate_media(silence, "silence.webm", "audio/webm")
        report = await analyze_audio_quick_for_demonstration(silence, "silence.webm", "audio/webm")
    results.append({"case_id": "AUD03", "execution": "local_ffmpeg_and_silence_gate_NOT_UI",
                    "duration_seconds": media.details["duration_seconds"], "status": report["transcription_detail"]["status"],
                    "remote_calls": gemini.await_count + assembly.await_count,
                    "passed": report["transcription"] == "" and report["transcription_detail"]["status"] == "no_speech" and gemini.await_count == assembly.await_count == 0})
    video = (backend / "tests/fixtures/synthetic-cafe.mp4").read_bytes()
    media = await validate_media(video, "synthetic-cafe.mp4", "video/mp4")
    frames = await extract_video_frames(media)
    results.append({"case_id": "VID01", "execution": "local_ffmpeg_sampling_NOT_UI_NOT_DETECTOR",
                    "duration_seconds": media.details["duration_seconds"], "sampled_frames": len(frames),
                    "timestamps_seconds": [t for t, _ in frames],
                    "passed": len(frames) > 0 and all(0 <= t <= media.details["duration_seconds"] and len(data) > 0 for t, data in frames)})
    av_item = next(item for item in extended_manifest if item["case_id"] == "VID-AUX01")
    av = (extended / av_item["file"]).read_bytes()
    media = await validate_media(av, av_item["file"], "video/mp4")
    frames = await extract_video_frames(media)
    track = await extract_video_audio(media)
    track_media = await validate_media(track, "track.wav", "audio/wav")
    report = await analyze_media(media, review_first=True)
    results.append({"case_id": "VID-AUX01", "execution": "local_ffmpeg_no_API_NOT_UI_NOT_ASR_NOT_HUMAN_MEDIA",
                    "sha256": hashlib.sha256(av).hexdigest(), "duration_seconds": media.details["duration_seconds"],
                    "has_audio": media.details["has_audio"], "sampled_frames": len(frames),
                    "track_duration_seconds": track_media.details["duration_seconds"],
                    "analysis_status": report["analysis_status"], "audio_analysis_status": report["audio_analysis"]["analysis_status"],
                    "transcription": report.get("transcription", ""),
                    "passed": bool(frames) and media.details["has_audio"] and track_media.kind == "audio"
                              and report["analysis_status"] == report["audio_analysis"]["analysis_status"] == "inconclusive"
                              and not report.get("transcription")})
    try:
        await _validate_public_url("http://127.0.0.1:8000/health")
        blocked = False
    except HTTPException as exc:
        blocked = exc.status_code == 400
    results.append({"case_id": "LNK09", "execution": "local_private_url_guard_NOT_UI", "passed": blocked})
    record = {"tested_at": datetime.now(timezone.utc).isoformat(),
              "scope": "Local controls; NOT 30-case completion, API validation or accuracy benchmark",
              "total": len(results), "passed": sum(r["passed"] for r in results), "results": results}
    Path(output).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False))
    return all(r["passed"] for r in results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    raise SystemExit(0 if asyncio.run(run(args.output)) else 1)
