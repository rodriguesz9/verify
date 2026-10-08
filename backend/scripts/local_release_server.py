"""Local-only release controls: disposable DB, fake history, no provider calls.

Run from backend with the normal application dependencies installed.
Never loads a private .env, accepts a production DB, or listens remotely.
This is a verification fixture server, NOT a deploy configuration.
"""

import argparse
import asyncio
import os
from pathlib import Path
import secrets
import sys
import tempfile
from datetime import datetime, timedelta, timezone
import hashlib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8026)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Use a local unprivileged port between 1024 and 65535.")
    backend = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend))
    runtime = Path(tempfile.mkdtemp(prefix="verify-release-local-"))
    os.environ.update({
        "DATABASE_URL": f"sqlite+aiosqlite:///{runtime / 'release_test.db'}",
        "APP_ENV": "development", "COOKIE_SECURE": "false", "COOKIE_SAME_SITE": "lax",
        "JWT_SECRET": secrets.token_urlsafe(48), "HMAC_SECRET_KEY": secrets.token_urlsafe(48),
        "CORS_ORIGINS": "http://127.0.0.1:5176,http://localhost:5176,http://127.0.0.1:8026",
        "CORS_ORIGIN_REGEX": "", "ANALYSIS_REQUESTS_PER_MINUTE": "2000",
        "ANALYSIS_GLOBAL_REQUESTS_PER_MINUTE": "4000", "SIGHTENGINE_AUDIO_ENABLED": "false",
        "LOCAL_OCR_ENABLED": "false", "OPENROUTER_ENABLED": "false",
        "HIVE_V3_MEDIA_TYPES": "", "HIVE_API_VERSION": "v2", "GOOGLE_CLIENT_ID": "",
        "WAYBACK_API_ENABLED": "false", "EXIFTOOL_ENABLED": "false", "C2PATOOL_ENABLED": "false",
        "PYTHON_DOTENV_DISABLED": "1",
    })
    for key in ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "GOOGLE_FACT_CHECK_KEY", "SERPERAPI_KEY",
                "SERPAPI_KEY", "SIGHTENGINE_API_USER", "SIGHTENGINE_API_SECRET", "HIVE_API_KEY",
                "HUGGINGFACE_API_TOKEN", "GPTZERO_API_KEY", "ASSEMBLYAI_API_KEY", "TINEYE_API_KEY",
                "HIVE_DEEPFAKE_API_KEY", "HIVE_IMAGE_API_KEY", "HIVE_VIDEO_API_KEY", "HIVE_AUDIO_API_KEY",
                "HIVE_TEXT_API_KEY", "HIVE_V3_API_KEY"):
        os.environ[key] = ""
    # Older python-dotenv versions may not support PYTHON_DOTENV_DISABLED.
    import dotenv
    dotenv.load_dotenv = lambda *_args, **_kwargs: False

    from app.main import app
    from app.core.database import init_db, AsyncSessionLocal
    from app.core.security import hash_password
    from app.models.user import User, UserTier
    from app.models.history import Verification, ContentType, VerdictLabel
    import uvicorn

    async def seed():
        await init_db()
        async with AsyncSessionLocal() as db:
            users = []
            for label in ("a", "b"):
                user = User(email=f"release-{label}@example.test", name=f"Controle local {label.upper()}",
                            hashed_password=hash_password("Local-Test-Only-938!"), tier=UserTier.ENTERPRISE)
                db.add(user)
                users.append(user)
            await db.flush()
            fixture = backend / "tests/fixtures/synthetic-cafe.png"
            digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
            now = datetime.now(timezone.utc)
            kinds = (ContentType.TEXT, ContentType.IMAGE, ContentType.AUDIO, ContentType.VIDEO, ContentType.TEXT)
            for index in range(45):
                kind = kinds[index % len(kinds)]
                query = f"Controle fictício {index + 1:02d} — conta A"
                if index == 37:
                    query += " marcador-fora-primeira-pagina"
                report = {
                    "content_type": kind.value.lower(), "query_input": query,
                    "verdict": "Suspicious", "score": 0, "analysis_status": "inconclusive",
                    "veracity_status": "inconclusive", "authenticity_status": "inconclusive",
                    "summary": "Controle fictício de interface. Não é resultado de um detector.",
                    "plain_explanation": "Nenhuma afirmação factual é avaliada neste registro de teste.",
                    "elderly_tip": "Este exemplo serve apenas para testar navegação e privacidade.",
                    "forensics": {}, "provider_coverage": {}, "limitations": ["Dados fictícios de teste local."],
                    "claim_assessments": [], "policy_version": "local-fixture-v1",
                    "analyzed_at": (now - timedelta(seconds=index)).isoformat(),
                }
                if kind == ContentType.IMAGE:
                    report.update(filename=f"controle-{index + 1}.png", file_hash_sha256=digest)
                db.add(Verification(user_id=users[0].id, content_type=kind,
                    source_url=f"https://example.org/controle-{index + 1}" if index % 5 == 4 else None,
                    verdict_score=0, verdict_label=VerdictLabel.SUSPICIOUS,
                    ai_summary=report["summary"], raw_result=report,
                    created_at=now - timedelta(seconds=index)))
            db.add(Verification(user_id=users[1].id, content_type=ContentType.TEXT,
                verdict_score=0, verdict_label=VerdictLabel.SUSPICIOUS,
                ai_summary="Registro fictício exclusivo da conta B",
                raw_result={"query_input": "SOMENTE-CONTA-B", "analysis_status": "inconclusive"}, created_at=now))
            await db.commit()

    asyncio.run(seed())
    print(f"Local fixture server: 127.0.0.1:{args.port}; providers disabled; disposable DB: {runtime}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


if __name__ == "__main__":
    main()
