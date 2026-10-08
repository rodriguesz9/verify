"""Disposable UI validation server; not a deploy configuration.

Only explicitly selected free-credit providers receive public test content.
Private .env is parsed through an allowlist: production DB/auth/Hive keys are
never imported. Outbound caps include failures; unknown providers are blocked.
Use --container only with Docker bound to 127.0.0.1 on the host.
"""
import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import json
import ipaddress
import os
from pathlib import Path
import secrets
import sys
import tempfile

KEYS = {
    "gemini": ("GEMINI_API_KEY",), "openrouter": ("OPENROUTER_API_KEY",),
    "facts": ("GOOGLE_FACT_CHECK_KEY",), "news": ("SERPERAPI_KEY",),
    "assemblyai": ("ASSEMBLYAI_API_KEY",),
    "sightengine": ("SIGHTENGINE_API_USER", "SIGHTENGINE_API_SECRET"),
    "hf": ("HUGGINGFACE_API_TOKEN",),
    "public_fetch": (),
}
CAPS = {"gemini": 12, "openrouter": 8, "facts": 40, "news": 16,
        "assemblyai": 40, "sightengine": 3, "hf": 2, "public_fetch": 4}
HOSTS = {"generativelanguage.googleapis.com": "gemini", "openrouter.ai": "openrouter",
         "factchecktools.googleapis.com": "facts", "google.serper.dev": "news",
         "api.assemblyai.com": "assemblyai", "api.sightengine.com": "sightengine",
         "router.huggingface.co": "hf", "www.nasa.gov": "public_fetch", "science.nasa.gov": "public_fetch"}
LOCAL_PAGE_CONTROL_URL = "https://example.test/controle.html"


def local_page_control_fetch(original):
    """Explicit QA-only HTTP simulation. All other URLs keep the SSRF defense."""
    async def fetch(url, **kwargs):
        if url != LOCAL_PAGE_CONTROL_URL:
            return await original(url, **kwargs)
        from fastapi import HTTPException
        from app.services.public_fetch import FetchedResource
        fixture = Path(__file__).resolve().parents[1] / "tests/fixtures/validation/links/pagina-controle.html"
        data = fixture.read_bytes()
        if len(data) > kwargs["max_bytes"]:
            raise HTTPException(413, "Controle local excede limite.")
        if kwargs.get("allowed_types") and "text/html" not in kwargs["allowed_types"]:
            raise HTTPException(415, "Controle local é HTML.")
        return FetchedResource(data, "text/html", LOCAL_PAGE_CONTROL_URL, "utf-8")
    return fetch


def request_provider(request):
    provider = HOSTS.get(request.url.host)
    if provider:
        return provider
    # The application's SSRF defense connects to a validated, pinned IP.
    # Recognize only our public fixture hosts; do not remove IP pinning or TLS.
    sni = request.extensions.get("sni_hostname")
    if isinstance(sni, bytes):
        sni = sni.decode("ascii", errors="ignore")
    if sni not in {"www.nasa.gov", "science.nasa.gov"} or request.headers.get("host") != sni:
        return None
    try:
        if request.url.scheme == "https" and request.url.port in {None, 443} and ipaddress.ip_address(request.url.host).is_global:
            return "public_fetch"
    except ValueError:
        pass
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--providers", default="")
    parser.add_argument("--free-credits-confirmed", action="store_true")
    parser.add_argument("--gemini-model", default="gemini-3.7-flash")
    parser.add_argument("--media-model", default="gemini-3.1-flash-lite")
    parser.add_argument("--gemini-request-cap", type=int, choices=range(13), default=12,
                        help="Optional stricter ceiling when separate diagnostics already consumed budget.")
    parser.add_argument("--transcription", choices=("assemblyai", "gemini"), default="assemblyai")
    parser.add_argument("--local-ocr", choices=("true", "false"), default="true")
    parser.add_argument("--local-page-control", action="store_true", help="Simulate retrieval of example.test control only; NOT public fetch validation.")
    parser.add_argument("--container", action="store_true")
    parser.add_argument("--port", type=int, default=8027)
    parser.add_argument("--record-dir", required=True)
    args = parser.parse_args()
    selected = {p.strip() for p in args.providers.split(",") if p.strip()}
    if not selected <= KEYS.keys() or not 1024 <= args.port <= 65535:
        parser.error("Unsupported provider/port.")
    if selected and not args.free_credits_confirmed:
        parser.error("Confirm free credits without automatic paid overage first.")
    approved_models = {"gemini-3.7-flash", "gemini-3.1-flash-lite", "gemini-3.8-flash"}
    if args.gemini_model not in approved_models or args.media_model not in approved_models:
        parser.error("Only explicitly verified free-tier Gemini models are allowed by this test runner.")
    backend = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend))
    import dotenv
    private = dotenv.dotenv_values(args.env_file, interpolate=False)
    # Clear inherited secrets before importing any clients with static config.
    for key in list(os.environ):
        if "API_KEY" in key or "API_TOKEN" in key or key in {"SIGHTENGINE_API_USER", "SIGHTENGINE_API_SECRET"}:
            os.environ.pop(key, None)
    for name in selected:
        for key in KEYS[name]:
            os.environ[key] = private.get(key) or ""
    dotenv.load_dotenv = lambda *_args, **_kwargs: False
    private.clear()
    runtime = Path(tempfile.mkdtemp(prefix="verify-ui-validation-"))
    record_dir = Path(args.record_dir)
    record_dir.mkdir(parents=True, exist_ok=True)
    os.environ.update({
        "DATABASE_URL": f"sqlite+aiosqlite:///{runtime / 'validation.db'}",
        "APP_ENV": "development", "COOKIE_SECURE": "false", "COOKIE_SAME_SITE": "lax",
        "JWT_SECRET": secrets.token_urlsafe(48), "HMAC_SECRET_KEY": secrets.token_urlsafe(48),
        "CORS_ORIGINS": "http://127.0.0.1:5176,http://localhost:5176",
        "CORS_ORIGIN_REGEX": "", "PYTHON_DOTENV_DISABLED": "1",
        "ANALYSIS_REQUESTS_PER_MINUTE": "100", "ANALYSIS_GLOBAL_REQUESTS_PER_MINUTE": "200",
        "GEMINI_MODEL_NAME": args.gemini_model, "GEMINI_MEDIA_MODEL_NAME": args.media_model,
        "GEMINI_FALLBACK_MODELS": "", "OPENROUTER_MODEL": "openrouter/free",
        "OPENROUTER_FALLBACK_MODELS": "", "OPENROUTER_DAILY_LIMIT": "8",
        "OPENROUTER_ENABLED": "true" if "openrouter" in selected else "false",
        "AUDIO_TRANSCRIPTION_PROVIDER": args.transcription, "LOCAL_OCR_ENABLED": args.local_ocr,
        "HIVE_API_VERSION": "v3", "HIVE_V3_MEDIA_TYPES": "", "SIGHTENGINE_AUDIO_ENABLED": "false",
        "GOOGLE_CLIENT_ID": "", "WAYBACK_API_ENABLED": "false", "C2PATOOL_ENABLED": "false",
        "HUGGINGFACE_IMAGE_API_URL": "https://router.huggingface.co/hf-inference/models/Ateeqq/ai-vs-human-image-detector" if "hf" in selected else "",
        "HUGGINGFACE_AI_LABEL": "ai", "EXIFTOOL_ENABLED": "true",
    })
    import httpx
    original_send = httpx.AsyncClient.send
    journal = record_dir / "provider-transport.json"
    existing = json.loads(journal.read_text()) if journal.exists() else {}
    counts = Counter(existing.get("counts", {}))
    events = existing.get("events", [])
    caps = {**CAPS, "gemini": args.gemini_request_cap}
    # Retain session budgets across controlled restarts/model comparisons.
    old_posts = sum(e.get("provider") == "assemblyai" and e.get("method") == "POST" for e in events)
    jobs = Counter(existing.get("asr_jobs", {"upload": (old_posts + 1) // 2, "job": old_posts // 2}))

    async def bounded_send(client, request, *pos, **kw):
        provider = request_provider(request)
        if provider is None or provider not in selected:
            raise httpx.RequestError("Validation outbound provider blocked", request=request)
        if counts[provider] >= caps[provider]:
            raise httpx.RequestError("Validation free request cap reached", request=request)
        if provider == "assemblyai" and request.method == "POST":
            # At most two audio uploads/jobs. Polling cannot create new jobs.
            category = "upload" if request.url.path.endswith("/upload") else "job"
            if jobs[category] >= 2:
                raise httpx.RequestError("Validation ASR job cap reached", request=request)
            jobs[category] += 1
        counts[provider] += 1
        event = {"provider": provider, "request_number": counts[provider], "method": request.method}
        events.append(event)
        try:
            response = await original_send(client, request, *pos, **kw)
            event["http_status"] = response.status_code
            return response
        except BaseException:
            event["transport_status"] = "incomplete"
            raise
        finally:
            # No URL/query/headers, identifiers, response bodies or credentials.
            (record_dir / "provider-transport.json").write_text(json.dumps({
                "scope": "transport, NOT accuracy", "events": events,
                "counts": dict(counts), "caps": caps, "asr_jobs": dict(jobs),
            }, ensure_ascii=False, indent=2), encoding="utf-8")

    httpx.AsyncClient.send = bounded_send
    from app.main import app
    # QA boundary evidence only: never capture bodies, query strings, cookies,
    # account identifiers or signed capabilities. Not installed in production.
    http_events = []
    observed_paths = {"/api/check-text", "/api/check-url", "/api/check-extracted-text",
                      "/api/upload", "/api/verificar/relatorio-pdf"}

    @app.middleware("http")
    async def record_validation_boundary(request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path in observed_paths:
            http_events.append({"path": path, "method": request.method, "status": response.status_code,
                                "content_type": response.headers.get("content-type", ""),
                                "cache_control": response.headers.get("cache-control", "")})
            (record_dir / "http-boundaries.json").write_text(json.dumps({
                "scope": "local UI HTTP boundaries, NOT provider accuracy", "events": http_events,
            }, indent=2), encoding="utf-8")
        return response

    if args.local_page_control:
        from app.api import check_url
        check_url.fetch_public_resource = local_page_control_fetch(check_url.fetch_public_resource)
    from app.core.database import init_db, AsyncSessionLocal
    from app.core.security import hash_password
    from app.models.user import User, UserTier
    import uvicorn

    async def seed():
        await init_db()
        async with AsyncSessionLocal() as db:
            db.add(User(email="validation@example.test", name="Validação local",
                        hashed_password=hash_password("Local-Test-Only-938!"), tier=UserTier.ENTERPRISE))
            await db.commit()

    asyncio.run(seed())
    (record_dir / "configuration.json").write_text(json.dumps({
        "started_at": datetime.now(timezone.utc).isoformat(), "providers": sorted(selected),
        "gemini_model": args.gemini_model, "media_model": args.media_model,
        "transcription": args.transcription, "local_ocr": args.local_ocr,
        "hive": "disabled_no_paid_calls", "database": "disposable_local",
        "local_page_control": {"enabled": args.local_page_control, "url": LOCAL_PAGE_CONTROL_URL,
                               "scope": "simulated HTTP from local fixture, NOT a public HTTPS integration"},
    }, indent=2), encoding="utf-8")
    print("UI validation: disposable DB, curated providers, hard outbound caps, no Hive.", flush=True)
    uvicorn.run(app, host="0.0.0.0" if args.container else "127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
