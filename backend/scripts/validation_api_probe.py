"""One explicit public control through a disposable local API, NOT a UI test.

No direct provider calls or automatic repeats. Run against validation_ui_server
with its persistent caps. Signed capabilities stay only in memory. Outputs are
diagnostics for these fixed controls, not measured general model accuracy.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import mimetypes
from pathlib import Path
import time
from urllib.parse import urlsplit

import httpx


CONTROLS = {
    "queen_true": {"text": "Elizabeth II morreu em 8 de setembro de 2022.",
                   "expected_veracity": "supported", "provenance": "Public Royal Household and Brasil Escola bodies."},
    "queen_false": {"text": "Elizabeth II morreu em 9 de setembro de 2022.",
                    "expected_veracity": "refuted", "provenance": "Authored false date control; not a published fake-news sample."},
    "apollo_true": {"text": "A missão Apollo 11 foi lançada em 16 de julho de 1969.",
                    "expected_veracity": "supported", "provenance": "Public NASA and Mundo Educação bodies."},
    "moon_false": {"text": "O homem nunca pisou na Lua.", "expected_veracity": "refuted",
                   "provenance": "Normalized documented moon-hoax rumor, not a literal social-media posting."},
    "queen_link": {"url": "https://brasilescola.uol.com.br/historia/elizabeth-ii.htm",
                   "expected_veracity": "not_prespecified", "provenance": "Full public article contains multiple claims; one date does not verify whole article."},
    "real_image": {"fixture": "backend/tests/fixtures/validation/internet-real-2026-10-07/nasa-zinnia-iss046e009018.jpg",
                   "provenance": "Published NASA photograph; this provenance is not cryptographic capture authentication."},
    "ai_image": {"fixture": "backend/tests/fixtures/validation/generated-2026-10-07/ai-plant-windowsill.png",
                 "provenance": "Known generated plant control."},
    "printed_ocr": {"fixture": "backend/tests/fixtures/validation/ocr/impresso-base.png",
                    "provenance": "Programmatically printed text with negation, amount and date; OCR control, not a photo-origin control."},
    "synthetic_audio": {"provenance": "Explicit derived five-second eSpeak conventional synthesis; no voice cloning or real-human control."},
    "silent_video": {"fixture": "backend/tests/fixtures/synthetic-cafe.mp4",
                     "provenance": "Known AI still repeated in a short silent video; not a real capture or temporal deepfake benchmark."},
}
REPORT_FIELDS = {"content_type", "verdict", "score", "score_semantics", "analysis_status", "summary", "plain_explanation",
                 "veracity_status", "veracity_reason", "veracity_decision_basis", "veracity_decision_coverage_complete",
                 "authenticity_status", "dimensions", "coverage", "source_attribution", "source_corroboration",
                 "claims", "claim_decisions", "forensics", "limitations", "extracted_text", "transcript", "ocr",
                 "transcription", "text_review", "model_used", "error"}
REPORT_FIELDS |= {"provider_coverage", "content_analysis", "audio_analysis", "text_review_status", "claim_assessments"}


def sanitize(value):
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()
                if not any(secret in key.casefold().replace("_", "") for secret in
                           ("token", "secret", "password", "cookie", "apikey", "authorization", "credentials"))
                and key.casefold() not in {"raw", "raw_preview", "headers", "request"}}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8027")
    parser.add_argument("--case", choices=CONTROLS, required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--audio-fixture", help="Only a task-owned derived WAV file for synthetic_audio.")
    parser.add_argument("--export-pdf", action="store_true")
    args = parser.parse_args()
    target = urlsplit(args.base_url)
    if (target.scheme != "http" or target.hostname not in {"127.0.0.1", "localhost"}
            or target.port != 8027 or target.username or target.password or target.query or target.fragment or target.path not in {"", "/"}):
        parser.error("Only a local HTTP API is allowed.")
    control = CONTROLS[args.case]
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    destination = output / f"{args.case}.json"
    if destination.exists() or (output / f"{args.case}.pdf").exists():
        parser.error("Existing control record: choose a new explicitly approved attempt folder; no automatic repeats.")
    started = time.monotonic()
    record = {"scope": "live local API control, NOT browser/UI or general accuracy",
              "case": args.case, "timestamp": datetime.now(timezone.utc).isoformat(), **control}
    destination.write_text(json.dumps({**record, "attempt_status": "started"}, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        async with httpx.AsyncClient(base_url=args.base_url, timeout=240, trust_env=False, follow_redirects=False) as client:
            if "text" in control:
                response = await client.post("/api/check-text", json={"text": control["text"]})
            elif "url" in control:
                response = await client.post("/api/check-url", json={"url": control["url"]})
            else:
                root = Path(__file__).resolve().parents[2]
                path = (root / control["fixture"]).resolve() if "fixture" in control else Path(args.audio_fixture or "").resolve()
                if not path.is_file() or (args.case == "synthetic_audio" and (path.parent != output or path.suffix.lower() != ".wav")):
                    parser.error("A documented task-owned WAV inside the output directory is required for the audio control.")
                data = path.read_bytes()
                record["fixture_sha256"] = hashlib.sha256(data).hexdigest()
                response = await client.post("/api/upload", files={"file": (path.name, data, mimetypes.guess_type(path.name)[0] or "application/octet-stream")},
                                             data={"review_text": "true"})
            record["http_status"] = response.status_code
            body = response.json()
            if not isinstance(body, dict):
                raise ValueError("Non-object response.")
            record["report"] = sanitize({key: value for key, value in body.items() if key in REPORT_FIELDS})
            if args.export_pdf and response.status_code == 200 and body.get("pdf_snapshot_token"):
                exported = await client.post("/api/verificar/relatorio-pdf", json={"snapshot_token": body["pdf_snapshot_token"]})
                record["pdf"] = {"http_status": exported.status_code, "valid_header": exported.content.startswith(b"%PDF"),
                                 "cache_control": exported.headers.get("cache-control")}
                if exported.status_code == 200 and exported.content.startswith(b"%PDF"):
                    (output / f"{args.case}.pdf").write_bytes(exported.content)
    except (httpx.HTTPError, ValueError):
        record["transport_status"] = "local_request_failed_or_invalid_json"
    record["elapsed_seconds"] = round(time.monotonic() - started, 2)
    report = record.get("report", {})
    comparison = report.get("source_corroboration") if isinstance(report.get("source_corroboration"), dict) else {}
    record["expected_label_observed"] = (report.get("veracity_status") == control["expected_veracity"]
                                          if control.get("expected_veracity") in {"supported", "refuted"} else None)
    destination.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: record.get(key) for key in ("case", "http_status", "elapsed_seconds", "expected_label_observed", "transport_status")}
                     | {"veracity_status": report.get("veracity_status"), "verdict": report.get("verdict"),
                        "comparison_status": comparison.get("status"),
                        "comparison_state": comparison.get("state"),
                        "coverage": report.get("coverage")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
