"""Local-only security/webhook smoke controls. No real WhatsApp delivery."""
import argparse
import asyncio
import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "backend/tests/fixtures"


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if urlsplit(args.base_url).hostname not in {"localhost", "127.0.0.1"}:
        parser.error("This probe is restricted to localhost.")
    secret = os.getenv("VERIFY_AUDIT_WEBHOOK_SECRET", "")
    if len(secret) < 32:
        parser.error("Set VERIFY_AUDIT_WEBHOOK_SECRET to the local test server secret.")
    records = []
    async with httpx.AsyncClient(base_url=args.base_url, timeout=30) as client:
        async def check(name, path, body, expected=200, expected_state=None, headers=None):
            response = await client.post(path, json=body, headers=headers)
            data = response.json()
            state = data.get("status") if isinstance(data, dict) else None
            records.append({
                "case": name, "http_status": response.status_code,
                "passed": response.status_code == expected and (
                    expected_state is None or state == expected_state
                ),
                "state": state,
            })
        await check("untrusted_browser_origin", "/api/check-text", {"text": "Mensagem fictícia de controle"},
                    403, headers={"Origin": "https://unrelated.vercel.app"})
        await check("credential_url", "/api/check-url", {"url": "https://user:secret@example.com"}, 400)
        await check("oversized_url", "/api/check-url", {"url": "https://example.com/" + "x" * 4096}, 422)
        await check("unauthenticated_webhook", "/api/whatsapp/webhook", {"message": "Mensagem fictícia"}, 401)
        auth = {"X-Verify-Webhook-Secret": secret}
        await check("invalid_webhook_shape", "/api/whatsapp/webhook", [], 422, headers=auth)
        await check("self_message_ignored", "/api/whatsapp/webhook",
                    {"data": {"key": {"fromMe": True}, "message": {"conversation": "Mensagem própria fictícia"}}},
                    expected_state="ignored", headers=auth)
        await check("other_event_ignored", "/api/whatsapp/webhook", {"event": "SEND_MESSAGE"},
                    expected_state="ignored", headers=auth)
        await check("invalid_base64", "/api/whatsapp/webhook",
                    {"base64": "@@@", "media_type": "image/png"}, 422, headers=auth)
        for name, data, mime in (
            ("image", (FIXTURES / "synthetic-cafe.png").read_bytes(), "image/png"),
            ("video", (FIXTURES / "synthetic-cafe.mp4").read_bytes(), "video/mp4"),
            ("audio", (ROOT / "frontend/public/audio/voz_humana_real.mp3").read_bytes(), "audio/mpeg"),
        ):
            await check("base64_" + name, "/api/whatsapp/webhook", {
                "base64": base64.b64encode(data).decode(), "media_type": mime,
            }, expected_state="success", headers=auth)
        message_id = "local-security-" + datetime.now(timezone.utc).isoformat()
        body = {"message_id": message_id, "message": "Mensagem fictícia para controle de repetição."}
        await check("first_message", "/api/whatsapp/webhook", body, expected_state="success", headers=auth)
        await check("duplicate_message", "/api/whatsapp/webhook", body, expected_state="duplicate", headers=auth)
    output = {
        "tested_at": datetime.now(timezone.utc).isoformat(),
        "scope": "local HTTP security controls; no real delivery or accuracy benchmark",
        "cases": records,
    }
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"controls": len(records), "passed": sum(row["passed"] for row in records)}))
    if not all(row["passed"] for row in records):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
