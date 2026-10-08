"""Explicit existing-credit Hive v3 control: two fixed images, no retries.

Transport and parser only, NOT application/UI/end-to-end verification or an
accuracy benchmark. Nominal two-image price ceiling: USD 0.012, not a billing
statement. No balance queries, audio, paid fallback, environment injection,
database imports, raw provider output or automatic refill.
"""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

from dotenv import dotenv_values
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.hive_service import HIVE_V3_API_URL, parse_hive_v3_scores


DEADLINE_SECONDS = 15
MAX_RESPONSE_BYTES = 256 * 1024
CONTROLS = (
    {"case": "nasa_source_photo", "path": "internet-real-2026-10-07/nasa-zinnia-iss046e009018.jpg",
     "filename": "nasa-zinnia-iss046e009018.jpg", "mime_type": "image/jpeg",
     "sha256": "0263876f57ff9cf1ee94e27335b7e68af592e3f7f3fbff76fa97f374a31cbb2d"},
    {"case": "known_ai_generated_plant", "path": "generated-2026-10-07/ai-plant-windowsill.png",
     "filename": "ai-plant-windowsill.png", "mime_type": "image/png",
     "sha256": "5a8dbdf2e0c69a7ca57420fd50032f62b11163685c280951a1bf988b06db8b21"},
)
PUBLIC_STATUSES = {"success", "partial", "invalid_response", "pending", "rate_limited",
                   "provider_error", "timeout", "transport_error", "response_size_limit"}


def load_controls():
    base = Path(__file__).resolve().parents[1] / "tests/fixtures/validation"
    controls = []
    for control in CONTROLS:
        data = (base / control["path"]).read_bytes()
        if not 0 < len(data) <= 10 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != control["sha256"]:
            raise ValueError("A fixed control changed; no unreviewed media may be sent.")
        controls.append({**control, "data": data})
    return controls


def summarize(result):
    status = result.get("status")
    record = {"available": result.get("available") is True,
              "status": status if isinstance(status, str) and status in PUBLIC_STATUSES else "invalid_response"}
    for name in ("ai_generated_score", "deepfake_score"):
        value = result.get(name)
        record[name] = (float(value) if not isinstance(value, bool) and isinstance(value, (int, float))
                        and math.isfinite(value) and 0 <= value <= 1 else None)
    return record


async def probe_once(key, control):
    # Reject direct reuse with an arbitrary caller-provided file or name.
    approved = next((value for value in CONTROLS if value["case"] == control.get("case")), None)
    data = control.get("data")
    if (approved is None or not isinstance(data, bytes)
            or hashlib.sha256(data).hexdigest() != approved["sha256"]):
        raise ValueError("Only an unchanged fixed diagnostic control may be sent.")
    started = time.monotonic()
    record = {"case": approved["case"], "available": False, "status": "transport_error",
              "http_status": None, "ai_generated_score": None, "deepfake_score": None}
    try:
        async with asyncio.timeout(DEADLINE_SECONDS):
            async with httpx.AsyncClient(timeout=httpx.Timeout(DEADLINE_SECONDS, connect=5, write=10, pool=3),
                                         trust_env=False, follow_redirects=False) as client:
                async with client.stream("POST", HIVE_V3_API_URL,
                        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
                        files={"media": (approved["filename"], data, approved["mime_type"])}) as remote:
                    record["http_status"] = remote.status_code
                    chunks, size = [], 0
                    async for chunk in remote.aiter_bytes(chunk_size=8192):
                        size += len(chunk)
                        if size > MAX_RESPONSE_BYTES:
                            record["status"] = "response_size_limit"
                            return record
                        chunks.append(chunk)
        if record["http_status"] == 202:
            record["status"] = "pending"
        elif record["http_status"] != 200:
            record["status"] = "rate_limited" if record["http_status"] in {402, 429} else "provider_error"
        else:
            record.update(summarize(parse_hive_v3_scores(json.loads(b"".join(chunks)), "image")))
    except (httpx.TimeoutException, TimeoutError):
        record["status"] = "timeout"
    except httpx.HTTPError:
        record["status"] = "transport_error"
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        record["status"] = "invalid_response"
    finally:
        record["duration_ms"] = round((time.monotonic() - started) * 1000)
    return record


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--existing-credit-confirmed", action="store_true",
                       help="Explicit authorization for at most two Hive image calls from existing credit only.")
    value.add_argument("--env-file", required=True, help="Private backend dotenv path; never printed or injected into environment.")
    value.add_argument("--output", required=True, help="New .json artifact in an owned non-public temporary directory under /tmp.")
    return value


async def main(args):
    if args.existing_credit_confirmed is not True:
        raise ValueError("Explicit existing-credit authorization is required.")
    requested = Path(args.output)
    if not requested.is_absolute():
        raise ValueError("An absolute output path is required.")
    parent = requested.parent.resolve(strict=True)
    mode = parent.stat()
    if (requested.parent != parent or parent == Path("/tmp") or not parent.is_relative_to(Path("/tmp"))
            or not parent.is_dir() or mode.st_uid != os.getuid() or mode.st_mode & 0o077
            or requested.suffix != ".json" or os.path.lexists(requested)):
        raise ValueError("Use a new JSON artifact in an owned private temporary folder.")
    ledger_path = parent / "hive-request-ledger.json"
    if os.path.lexists(ledger_path):
        raise ValueError("Two calls were already reserved in this folder; no automatic rerun.")
    controls = load_controls()
    values = dotenv_values(args.env_file, interpolate=False)
    key = values.get("HIVE_V3_API_KEY") or values.get("HIVE_API_KEY", "")
    del values
    if (not isinstance(key, str) or not 1 <= len(key.strip()) <= 1024
            or any(not 33 <= ord(character) <= 126 for character in key.strip())):
        raise ValueError("A private Hive v3 Secret Key is required; no request started.")
    key = key.strip()
    ledger = {"provider": "hive", "api_version": "v3", "media_types": ["image"],
              "image_requests_reserved": 2, "audio_seconds_reserved": 0, "requests_started": 0,
              "existing_credit_confirmed": True, "no_retries": True, "no_fallback": True,
              "nominal_price_ceiling_usd": .012, "price_is_not_a_billing_statement": True}
    # Exclusive files claim the folder before any network request. The retained
    # ledger descriptor is updated in place, not reopened through a new path.
    with ledger_path.open("x", encoding="utf-8") as ledger_file, requested.open("x", encoding="utf-8") as output_file:
        def persist_ledger():
            ledger_file.seek(0)
            json.dump(ledger, ledger_file, indent=2)
            ledger_file.truncate()
            ledger_file.flush()
            os.fsync(ledger_file.fileno())

        persist_ledger()
        results = []
        for control in controls:
            ledger["requests_started"] += 1
            persist_ledger()
            results.append(await probe_once(key, control))
        record = {"tested_at": datetime.now(timezone.utc).isoformat(),
                  "scope": "Fixed two-image Hive v3 transport/parser controls; not UI, end-to-end verification or an accuracy benchmark.",
                  "request_accounting": ledger, "controls": results,
                  "pricing_reference": "https://thehive.ai/pricing"}
        json.dump(record, output_file, ensure_ascii=False, indent=2)
        output_file.flush()
        os.fsync(output_file.fileno())
    print(json.dumps(record, ensure_ascii=False))
    return record


if __name__ == "__main__":
    arguments = parser().parse_args()
    try:
        asyncio.run(main(arguments))
    except Exception:
        raise SystemExit("Probe refused or could not write its owned artifact; no private error details emitted.")
