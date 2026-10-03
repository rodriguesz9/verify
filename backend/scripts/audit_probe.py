"""Opt-in HTTP controls. Never claims measured deepfake detection accuracy."""
import argparse
import asyncio
import json
import time
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
    parser.add_argument("--local-auth", action="store_true")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    if args.local_auth and urlsplit(base).hostname not in {"localhost", "127.0.0.1"}:
        parser.error("Account/history writes are restricted to localhost.")
    records = []
    async with httpx.AsyncClient(base_url=base, timeout=90) as client:
        async def check(name, method, path, expected=200, **kwargs):
            started = time.monotonic()
            try:
                response = await client.request(method, path, **kwargs)
                try:
                    data = response.json()
                except ValueError:
                    data = {"content_type": response.headers.get("content-type"), "pdf_valid": response.content.startswith(b"%PDF")}
                # No tokens, cookies, API keys, raw provider payloads or private history.
                fields = ("verdict", "analysis_status", "score", "confidence", "transcription", "summary",
                          "short_explanation", "content_type", "pdf_valid", "status", "integridade_verificada")
                safe = {key: data[key] for key in fields if isinstance(data, dict) and key in data}
                if isinstance(data, dict) and "results" in data:
                    safe["batch_results"] = [{key: row.get(key) for key in ("verdict", "analysis_status", "error")} for row in data["results"]]
                if isinstance(data, dict) and "provider_coverage" in data:
                    safe["coverage"] = {key: row.get("status") for key, row in data["provider_coverage"].items()}
                record = {"case": name, "http_status": response.status_code, "expected_status": expected,
                          "http_ok": response.status_code == expected, "seconds": round(time.monotonic() - started, 2), "result": safe}
            except httpx.HTTPError as exc:
                record = {"case": name, "http_ok": False, "error_type": type(exc).__name__}
                data = {}
            records.append(record)
            print(json.dumps(record, ensure_ascii=False), flush=True)
            return data

        await check("health", "GET", "/health")
        await check("anonymous_history", "GET", "/api/history", 401)
        await check("private_url_rejected", "POST", "/api/check-url", 400, json={"url": "http://127.0.0.1:22"})
        await check("empty_image_rejected", "POST", "/api/upload", 422, files={"file": ("empty.png", b"", "image/png")})
        await check("corrupt_image_rejected", "POST", "/api/verificar/completo", 422,
                    files={"file": ("corrupt.png", b"\x89PNG\r\n\x1a\nnot pixels", "image/png")})
        await check("synthetic_image_control", "POST", "/api/upload",
                    files={"file": ("sample.png", (FIXTURES / "synthetic-cafe.png").read_bytes(), "image/png")})
        await check("synthetic_video_control", "POST", "/api/upload",
                    files={"file": ("sample.mp4", (FIXTURES / "synthetic-cafe.mp4").read_bytes(), "video/mp4")})
        audio = (ROOT / "frontend/public/audio/voz_humana_real.mp3").read_bytes()
        first = await check("same_audio_neutral_name", "POST", "/api/verificar/audio-rapido", files={"file": ("sample.mp3", audio, "audio/mpeg")})
        second = await check("same_audio_fake_name", "POST", "/api/verificar/audio-rapido", files={"file": ("fake_clonado.mp3", audio, "audio/mpeg")})
        records.append({"case": "audio_filename_invariance", "behavior_ok": first.get("verdict") == second.get("verdict") and first.get("transcription") == second.get("transcription")})
        await check("scam_text", "POST", "/api/check-text", json={"text": "Pague uma taxa de 37 reais para liberar seu Pix no gov-pix-beneficios.site. Faça o Pix agora!"})
        await check("batch_text", "POST", "/api/check-text-batch", json={"texts": ["O céu está bonito hoje.", "Pague uma taxa para receber seu prêmio via Pix urgente!"]})
        await check("whatsapp_simulator", "POST", "/api/whatsapp/simulate", json={"message": "Pague uma taxa para receber seu prêmio via Pix urgente!"})
        await check("pdf", "POST", "/api/verificar/relatorio-pdf", files={"file": ("sample.png", (FIXTURES / "synthetic-cafe.png").read_bytes(), "image/png")})
        if args.local_auth:
            identity = {"name": "Auditoria local", "email": f"audit-{int(time.time())}@example.com", "password": "Local-Test-Only-938!"}
            await check("local_register", "POST", "/api/auth/register", json=identity)
            await check("local_login", "POST", "/api/auth/login", json={"email": identity["email"], "password": identity["password"]})
            await check("local_profile", "GET", "/api/auth/me")
            await check("local_authenticated_batch", "POST", "/api/check-text-batch", json={"texts": ["Teste de notícia sem confirmação.", "Mensagem de demonstração local."]})
            await check("local_saved_image", "POST", "/api/upload", files={"file": ("saved.png", (FIXTURES / "synthetic-cafe.png").read_bytes(), "image/png")})
            await check("local_history", "GET", "/api/history")
            await check("local_refresh", "POST", "/api/auth/refresh")
            await check("local_seal_capture", "POST", "/api/capturar/selo", files={"file": ("sample.png", (FIXTURES / "synthetic-cafe.png").read_bytes(), "image/png")})
            await check("local_seal_verify", "POST", "/api/verificar/selo", files={"file": ("sample.png", (FIXTURES / "synthetic-cafe.png").read_bytes(), "image/png")})
            await check("local_logout", "POST", "/api/auth/logout", 204)
            await check("local_profile_after_logout", "GET", "/api/auth/me", 401)
    output = {"tested_at": datetime.now(timezone.utc).isoformat(), "base_url": base,
              "scope": "HTTP controls, not a calibrated accuracy benchmark", "cases": records}
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
