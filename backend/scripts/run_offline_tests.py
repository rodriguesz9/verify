"""Run regression tests with disposable DBs, no .env and no real HTTP calls.

Default: owned temporary SQLite DBs. PostgreSQL opt-in: only a loopback test
database supplied explicitly; integration tests recreate its tables. This is
not an accuracy benchmark or a production/deployment readiness certificate.
"""
import argparse
from contextlib import ExitStack
import os
from pathlib import Path
import secrets
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch


def postgres_test_url(value):
    from sqlalchemy.engine import make_url
    try:
        url = make_url(value)
    except Exception as exc:
        raise argparse.ArgumentTypeError("Invalid disposable PostgreSQL test URL.") from exc
    # Never print the URL; even invalid input could contain a real credential.
    if (url.drivername != "postgresql+asyncpg" or url.host not in {"localhost", "127.0.0.1", "::1"}
            or not url.database or "test" not in url.database.lower() or url.query):
        raise argparse.ArgumentTypeError("Use postgresql+asyncpg on loopback, a database named test, and no query options.")
    return value


def configure_test_environment(runtime, postgres_url=None):
    # Ignore inherited production credentials/configuration before importing app.
    for key in list(os.environ):
        if "API_KEY" in key or "API_TOKEN" in key or key in {"SIGHTENGINE_API_USER", "SIGHTENGINE_API_SECRET", "GOOGLE_CLIENT_ID"}:
            os.environ[key] = ""
    os.environ.update({
        "DATABASE_URL": f"sqlite+aiosqlite:///{runtime / 'app-test.db'}",
        "TEST_DATABASE_URL": postgres_url or f"sqlite+aiosqlite:///{runtime / 'query-test.db'}",
        "APP_ENV": "development", "JWT_SECRET": secrets.token_urlsafe(48),
        "HMAC_SECRET_KEY": secrets.token_urlsafe(48), "JWT_ALGORITHM": "HS256",
        "COOKIE_SECURE": "false", "COOKIE_SAME_SITE": "lax",
        "CORS_ORIGINS": "http://localhost:5173", "CORS_ORIGIN_REGEX": "",
        "PYTHON_DOTENV_DISABLED": "1", "SIGHTENGINE_AUDIO_ENABLED": "false",
        "LOCAL_OCR_ENABLED": "false", "EXIFTOOL_ENABLED": "false",
        "WAYBACK_API_ENABLED": "false", "C2PATOOL_ENABLED": "false",
        "WHATSAPP_HISTORY_ENABLED": "false", "WHATSAPP_WEBHOOK_SECRET": "",
        "WHATSAPP_HASH_SECRET": "", "GOOGLE_CLIENT_ID": "",
        "HIVE_V3_MEDIA_TYPES": "", "HIVE_API_VERSION": "v2",
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-test-url", type=postgres_test_url,
                        help="EXPLICIT disposable PostgreSQL database; tables are recreated.")
    args = parser.parse_args()
    required = ("ffmpeg", "ffprobe", "pdftotext", "pdftoppm")
    missing = [tool for tool in required if not shutil.which(tool)]
    if missing:
        parser.error("Required test tools missing: " + ", ".join(missing))
    backend = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend))
    sys.path.insert(0, str(backend / "tests"))
    with tempfile.TemporaryDirectory(prefix="verify-offline-tests-") as directory:
        configure_test_environment(Path(directory), args.postgres_test_url)
        import dotenv
        import httpx
        blocked = []

        def block_http(*_args, **_kwargs):
            blocked.append("sync_http")
            raise RuntimeError("Real HTTP blocked by offline test runner.")

        async def block_async_http(*_args, **_kwargs):
            blocked.append("async_http")
            raise RuntimeError("Real HTTP blocked by offline test runner.")

        # TestClient uses its in-process ASGI transport; individual mocks still
        # work. Count unexpected real HTTP even if application catches the error.
        with ExitStack() as stack:
            stack.enter_context(patch.object(dotenv, "load_dotenv", return_value=False))
            stack.enter_context(patch.object(httpx.HTTPTransport, "handle_request", block_http))
            stack.enter_context(patch.object(httpx.AsyncHTTPTransport, "handle_async_request", block_async_http))
            suite = unittest.defaultTestLoader.discover(str(backend / "tests"))
            result = unittest.TextTestRunner(verbosity=1).run(suite)
        if blocked:
            print(f"FAIL: {len(blocked)} unexpected HTTP attempts blocked; no URL/content recorded.", file=sys.stderr)
        if result.skipped:
            print(f"FAIL: {len(result.skipped)} skipped tests; CI requires full offline suite.", file=sys.stderr)
        return 0 if result.wasSuccessful() and not blocked and not result.skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
