"""Local UI fixture: real app/upload, fake AssemblyAI transport, disposable DB.

Does NOT evaluate transcription fidelity. Input is a generated decoding tone,
while returned text/status are controlled. Never loads keys or a private .env.
All external providers are disabled; any unmocked HTTP transport is refused.
"""

import argparse
import asyncio
import io
import json
import math
import os
from pathlib import Path
import secrets
import struct
import sys
import tempfile
import wave


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8027)
    parser.add_argument("--control-directory", required=True)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Use an unprivileged local port.")
    directory = Path(args.control_directory).resolve()
    if not directory.is_dir() or directory == Path("/"):
        parser.error("Use an existing dedicated temporary control directory.")
    backend = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend))
    runtime = Path(tempfile.mkdtemp(prefix="verify-asr-local-"))
    os.environ.update({
        "DATABASE_URL": f"sqlite+aiosqlite:///{runtime / 'control.db'}",
        "APP_ENV": "development", "COOKIE_SECURE": "false", "COOKIE_SAME_SITE": "lax",
        "JWT_SECRET": secrets.token_urlsafe(48), "HMAC_SECRET_KEY": secrets.token_urlsafe(48),
        "CORS_ORIGINS": "http://127.0.0.1:5176,http://localhost:5176,http://127.0.0.1:8027",
        "CORS_ORIGIN_REGEX": "", "ANALYSIS_REQUESTS_PER_MINUTE": "2000",
        "ANALYSIS_GLOBAL_REQUESTS_PER_MINUTE": "4000", "SIGHTENGINE_AUDIO_ENABLED": "false",
        "LOCAL_OCR_ENABLED": "false", "OPENROUTER_ENABLED": "false",
        "HIVE_V3_MEDIA_TYPES": "", "HIVE_API_VERSION": "v2", "GOOGLE_CLIENT_ID": "",
        "WAYBACK_API_ENABLED": "false", "EXIFTOOL_ENABLED": "false", "C2PATOOL_ENABLED": "false",
        "PYTHON_DOTENV_DISABLED": "1", "AUDIO_TRANSCRIPTION_PROVIDER": "assemblyai",
    })
    for key in ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "GOOGLE_FACT_CHECK_KEY", "SERPERAPI_KEY",
                "SERPAPI_KEY", "SIGHTENGINE_API_USER", "SIGHTENGINE_API_SECRET", "HIVE_API_KEY",
                "HUGGINGFACE_API_TOKEN", "GPTZERO_API_KEY", "TINEYE_API_KEY", "HIVE_DEEPFAKE_API_KEY",
                "HIVE_IMAGE_API_KEY", "HIVE_VIDEO_API_KEY", "HIVE_AUDIO_API_KEY", "HIVE_TEXT_API_KEY",
                "HIVE_V3_API_KEY", "WHATSAPP_WEBHOOK_SECRET", "WHATSAPP_HASH_SECRET"):
        os.environ[key] = ""
    os.environ["ASSEMBLYAI_API_KEY"] = "local-fixture-not-a-provider-key"
    import dotenv
    dotenv.load_dotenv = lambda *_args, **_kwargs: False
    import httpx
    from app.services import audio_service
    from app.main import app
    from app.core.database import init_db
    import uvicorn

    counts = {"upload": 0, "submit": 0, "poll": 0}
    polls = {}
    literal = "CONTROLE SIMULADO. Não envie dinheiro. Valor R$ 123,45. Data 03/10/2026."

    def transport(request):
        if request.url.host != "api.assemblyai.com":
            raise RuntimeError("External provider request blocked by local fixture")
        path = request.url.path
        if request.method == "POST" and path == "/v2/upload":
            counts["upload"] += 1
            return httpx.Response(200, json={"upload_url": "https://cdn.assemblyai.com/upload/local-control"})
        if request.method == "POST" and path == "/v2/transcript":
            counts["submit"] += 1
            job = f"private-fixture-job-{counts['submit']}"
            polls[job] = 0
            return httpx.Response(200, json={"id": job})
        if request.method == "GET" and path.startswith("/v2/transcript/"):
            job = path.rsplit("/", 1)[-1]
            if job not in polls:
                return httpx.Response(404)
            counts["poll"] += 1
            polls[job] += 1
            if polls[job] == 1:
                return httpx.Response(200, json={"status": "processing"})
            return httpx.Response(200, json={"status": "completed", "text": literal,
                                            "confidence": .8, "words": [], "audio_duration": 1})
        raise RuntimeError("Unexpected local fixture provider operation")

    audio_service.assemblyai_jobs.transport = httpx.MockTransport(transport)
    audio_service.assemblyai_jobs.max_polls = 1
    # The production manager receives its transport explicitly. All other HTTP
    # clients are barred, including an accidentally enabled auxiliary service.
    async def refuse(*_args, **_kwargs):
        raise RuntimeError("Real HTTP is disabled in this local fixture")
    httpx.AsyncHTTPTransport.handle_async_request = refuse

    @app.get("/local-control/asr-counts", include_in_schema=False)
    async def controlled_counts():
        return {"fixture": "simulated-not-accuracy-benchmark", "counts": dict(counts)}

    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * t / 16000))) for t in range(16000)))
    # Generated media, not a text/source edit or a human speech recording.
    (directory / "decoding-tone-not-human.wav").write_bytes(output.getvalue())
    asyncio.run(init_db())
    print("Local simulated ASR fixture; no real provider calls; disposable database.", flush=True)
    try:
        uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)
    finally:
        # JSON is output from a test run, not application source/configuration.
        (directory / "asr-counts.json").write_text(json.dumps({"fixture": "simulated-not-accuracy-benchmark", "counts": counts}, indent=2))


if __name__ == "__main__":
    main()
