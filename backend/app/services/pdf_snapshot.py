"""Short-lived, signed report copies. Export never invokes an analysis provider.

The custom format deliberately is NOT a JWT. Anonymous copies are bearer
capabilities, not authentication tokens; keep them in memory, never in logs.
No media bytes or server-side snapshot storage are required.
"""

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from app.core.report_limits import MAX_SNAPSHOT_PAYLOAD_BYTES, MAX_SNAPSHOT_TOKEN_BYTES, MAX_SNAPSHOT_BODY_BYTES

SNAPSHOT_TTL_SECONDS = 3600
_PREFIX = "vpdf1"
_PURPOSE = "verify-pdf-export-v1"
_DOMAIN = b"Verify/pdf-export/signing-key/v1"
_configured_secret = os.getenv("HMAC_SECRET_KEY", "")
if len(_configured_secret) >= 32 and _configured_secret != "verify_local_demo_only":
    _master_key = _configured_secret.encode("utf-8")
elif os.getenv("APP_ENV", "development").lower() == "production":
    # Do not break analysis when export configuration is missing. Fail closed.
    _master_key = None
else:
    # Development snapshots intentionally expire when this process restarts.
    _master_key = secrets.token_bytes(48)
_SIGNING_KEY = hmac.new(_master_key, _DOMAIN, hashlib.sha256).digest() if _master_key else None


def _owner(user: Any) -> str | None:
    return str(user.id) if user is not None else None


def _unsigned_report(report: Any) -> dict:
    # History reads may already contain export fields. Never nest an old token.
    if not isinstance(report, dict) or not all(isinstance(key, str) for key in report):
        return {}
    return {key: value for key, value in report.items()
            if not key.startswith("pdf_") and key != "text_review_token"}


def _valid_report(report: Any) -> bool:
    if isinstance(report, dict) and report.get("content_type") in ("text", "url"):
        # Legacy records without preserved inputs/time cannot be reconstructed
        # by re-fetching a page or re-running models during export.
        try:
            analyzed_at = datetime.fromisoformat(report.get("analyzed_at", ""))
        except (TypeError, ValueError):
            return False
        valid = (analyzed_at.tzinfo is not None and not report.get("error")
                 and all(isinstance(report.get(key), str) and bool(report[key].strip())
                         for key in ("query_input", "verdict", "summary", "plain_explanation", "elderly_tip", "policy_version"))
                 and isinstance(report.get("claim_assessments"), list)
                 and isinstance(report.get("limitations"), list)
                 and isinstance(report.get("veracity_status"), str)
                 and report.get("veracity_status") in {"supported", "refuted", "conflicting", "mixed", "unverified", "probably_false"})
        if report["content_type"] == "url":
            valid = (valid and isinstance(report.get("source_url"), str)
                     and isinstance(report.get("source_text"), str) and bool(report["source_text"].strip())
                     and isinstance(report.get("source_extraction"), dict))
        return valid
    return (
        isinstance(report, dict)
        and isinstance(report.get("content_type"), str)
        and report.get("content_type") in {"image", "audio", "video"}
        and isinstance(report.get("filename"), str)
        and 0 < len(report["filename"]) <= 255
        and isinstance(report.get("file_hash_sha256"), str)
        and re.fullmatch(r"[a-f0-9]{64}", report["file_hash_sha256"]) is not None
        and isinstance(report.get("verdict"), str)
        and isinstance(report.get("summary"), str)
        and isinstance(report.get("plain_explanation"), str)
        and isinstance(report.get("elderly_tip"), str)
        and isinstance(report.get("forensics"), dict)
    )


def attach_pdf_snapshot(report: Any, user: Any = None, *, now: int | None = None) -> dict:
    """Return report plus export capability; do not mutate or persist a token."""
    clean = _unsigned_report(report)
    unavailable = {**clean, "pdf_export_status": "unavailable"}
    if _SIGNING_KEY is None:
        return {**unavailable, "pdf_export_reason": "Exportação indisponível: assinatura do servidor não configurada."}
    if not _valid_report(clean):
        return {**unavailable, "pdf_export_reason": "Esta análise não possui os dados originais necessários para exportação segura."}
    issued_at = int(time.time()) if now is None else int(now)
    expires_at = issued_at + SNAPSHOT_TTL_SECONDS
    snapshot = {"version": 1, "purpose": _PURPOSE, "iat": issued_at, "exp": expires_at,
                "owner": _owner(user), "report": clean}
    try:
        payload = json.dumps(snapshot, ensure_ascii=False, allow_nan=False,
                             sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, RecursionError):
        return {**unavailable, "pdf_export_reason": "O resultado não pode ser exportado com integridade."}
    if len(payload) > MAX_SNAPSHOT_PAYLOAD_BYTES:
        return {**unavailable, "pdf_export_reason": "O relatório excede o limite de exportação segura; nenhuma evidência foi truncada."}
    encoded = base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
    message = f"{_PREFIX}.{encoded}"
    signature = hmac.new(_SIGNING_KEY, message.encode("ascii"), hashlib.sha256).hexdigest()
    token = f"{message}.{signature}"
    if len(token) > MAX_SNAPSHOT_TOKEN_BYTES:
        return {**unavailable, "pdf_export_reason": "O relatório excede o limite de exportação segura."}
    return {**clean, "pdf_snapshot_token": token, "pdf_snapshot_expires_at": expires_at,
            "pdf_export_status": "ready"}


def verify_pdf_snapshot(token: Any, user: Any = None, *, now: int | None = None) -> dict:
    """Authenticate the immutable result BEFORE decoding JSON or rendering PDF."""
    if _SIGNING_KEY is None:
        raise HTTPException(503, "Exportação indisponível: assinatura do servidor não configurada.")
    invalid = HTTPException(422, "Cópia de relatório inválida. Exporte o resultado original da análise.")
    if not isinstance(token, str) or len(token) > MAX_SNAPSHOT_TOKEN_BYTES:
        raise invalid
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != _PREFIX:
        raise invalid
    encoded, signature = parts[1:]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", encoded) or not re.fullmatch(r"[a-f0-9]{64}", signature):
        raise invalid
    expected = hmac.new(_SIGNING_KEY, f"{_PREFIX}.{encoded}".encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise invalid
    try:
        payload = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
        if len(payload) > MAX_SNAPSHOT_PAYLOAD_BYTES:
            raise invalid
        snapshot = json.loads(payload)
        if not isinstance(snapshot, dict) or set(snapshot) != {"version", "purpose", "iat", "exp", "owner", "report"}:
            raise invalid
        if type(snapshot["version"]) is not int or snapshot["version"] != 1 or snapshot["purpose"] != _PURPOSE:
            raise invalid
        issued_at, expires_at = snapshot["iat"], snapshot["exp"]
        if type(issued_at) is not int or type(expires_at) is not int or expires_at - issued_at != SNAPSHOT_TTL_SECONDS:
            raise invalid
        current = int(time.time()) if now is None else int(now)
        if issued_at > current + 30:
            raise invalid
        if expires_at <= current:
            raise HTTPException(410, "A cópia para exportação expirou. Se a análise foi salva, abra-a no histórico para renovar a exportação sem nova análise. Análises anônimas não ficam salvas.")
        owner = snapshot["owner"]
        if owner is not None:
            if not isinstance(owner, str) or str(UUID(owner)) != owner:
                raise invalid
            if owner != _owner(user):
                raise HTTPException(403, "Este relatório pertence a outra sessão. Entre na conta que realizou a análise.")
        report = snapshot["report"]
        if not _valid_report(report) or any(key.startswith("pdf_") for key in report):
            raise invalid
        return report
    except HTTPException:
        raise
    except (ValueError, TypeError, RecursionError, UnicodeDecodeError):
        raise invalid
