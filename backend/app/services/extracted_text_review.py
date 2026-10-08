"""Short-lived provenance for a NEW, user-reviewed text check.

Not authentication or a PDF capability. No media bytes, truth claim or detector
result is accepted from the browser. Anonymous tokens are bearer capabilities;
keep them out of logs/history/copyable JSON. Reuse still consumes normal quota.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from uuid import UUID

from fastapi import HTTPException

REVIEW_TTL_SECONDS = 900
MAX_REVIEW_TOKEN_BYTES = 32 * 1024
MAX_REVIEW_BODY_BYTES = 64 * 1024
_PREFIX = "vrev1"
_PURPOSE = "verify-extracted-text-review-v1"
_secret = os.getenv("HMAC_SECRET_KEY", "")
_master = (_secret.encode() if len(_secret) >= 32 and _secret != "verify_local_demo_only"
           else None if os.getenv("APP_ENV", "development").lower() == "production"
           else secrets.token_bytes(48))
_KEY = hmac.new(_master, b"Verify/text-review/signing-key/v1", hashlib.sha256).digest() if _master else None


def extracted_text_source(report: dict) -> dict:
    kind = report.get("content_type")
    if kind == "image":
        layer = report.get("forensics", {}).get("ocr", {})
        text, method, provider = layer.get("text", ""), "ocr", layer.get("provider")
    else:
        text, method = report.get("transcription", ""), "transcription"
        coverage = report.get("audio_analysis", report).get("provider_coverage", {})
        provider = coverage.get("transcription", {}).get("provider")
    return {"content_type": kind, "method": method, "provider": provider if isinstance(provider, str) else None,
            "original_text": text if isinstance(text, str) else "",
            "filename": report.get("filename"), "file_hash_sha256": report.get("file_hash_sha256"),
            "analyzed_at": report.get("analyzed_at")}


def _valid_source(source) -> bool:
    return (isinstance(source, dict)
            and set(source) == {"content_type", "method", "provider", "original_text", "filename", "file_hash_sha256", "analyzed_at"}
            and source["content_type"] in {"image", "audio", "video"}
            and source["method"] == ("ocr" if source["content_type"] == "image" else "transcription")
            and (source["provider"] is None or isinstance(source["provider"], str) and len(source["provider"]) <= 100)
            and isinstance(source["original_text"], str) and 10 <= len(source["original_text"].strip()) <= 5000
            and isinstance(source["filename"], str) and 0 < len(source["filename"]) <= 255
            and isinstance(source["file_hash_sha256"], str) and re.fullmatch(r"[a-f0-9]{64}", source["file_hash_sha256"]) is not None
            and isinstance(source["analyzed_at"], str) and 0 < len(source["analyzed_at"]) <= 100)


def attach_text_review(report: dict, user=None, *, now=None) -> dict:
    """Attach AFTER history/PDF signing so the review credential is not nested."""
    unavailable = {**report, "text_review_status": "unavailable"}
    source = extracted_text_source(report)
    if not _valid_source(source):
        return {**unavailable, "text_review_reason": "Não há texto extraído entre 10 e 5000 caracteres para conferir. Nenhuma palavra foi inventada."}
    if _KEY is None:
        return {**unavailable, "text_review_reason": "Conferência vinculada indisponível: assinatura do servidor não configurada. Você pode fazer uma nova checagem de texto."}
    issued = int(time.time()) if now is None else int(now)
    payload = {"purpose": _PURPOSE, "iat": issued, "exp": issued + REVIEW_TTL_SECONDS,
               "owner": str(user.id) if user is not None else None, "source": source}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, ensure_ascii=False, allow_nan=False,
                         sort_keys=True, separators=(",", ":")).encode()).rstrip(b"=").decode()
    message = f"{_PREFIX}.{encoded}"
    token = f"{message}.{hmac.new(_KEY, message.encode(), hashlib.sha256).hexdigest()}"
    if len(token) > MAX_REVIEW_TOKEN_BYTES:
        return {**unavailable, "text_review_reason": "Texto excede o limite da conferência vinculada; a leitura original foi preservada."}
    return {**report, "text_review_status": "ready", "text_review_token": token,
            "text_review_expires_at": payload["exp"]}


def verify_text_review(token, user=None, *, now=None) -> dict:
    if _KEY is None:
        raise HTTPException(503, "Conferência vinculada indisponível: assinatura do servidor não configurada.")
    invalid = HTTPException(422, "Conferência inválida. Envie o arquivo novamente ou faça uma nova checagem de texto.")
    if not isinstance(token, str) or len(token) > MAX_REVIEW_TOKEN_BYTES:
        raise invalid
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != _PREFIX:
        raise invalid
    encoded, signature = parts[1:]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", encoded) or not re.fullmatch(r"[a-f0-9]{64}", signature):
        raise invalid
    expected = hmac.new(_KEY, f"{_PREFIX}.{encoded}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise invalid
    try:
        payload = json.loads(base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True))
        if not isinstance(payload, dict) or set(payload) != {"purpose", "iat", "exp", "owner", "source"} or payload["purpose"] != _PURPOSE:
            raise invalid
        issued, expires = payload["iat"], payload["exp"]
        if type(issued) is not int or type(expires) is not int or expires - issued != REVIEW_TTL_SECONDS:
            raise invalid
        current = int(time.time()) if now is None else int(now)
        if issued > current + 30:
            raise invalid
        if expires <= current:
            raise HTTPException(410, "O prazo para conferir terminou. Faça uma nova checagem de texto ou envie o arquivo novamente.")
        owner = payload["owner"]
        if owner is not None:
            if not isinstance(owner, str) or str(UUID(owner)) != owner:
                raise invalid
            if user is None or owner != str(user.id):
                raise HTTPException(403, "Esta leitura pertence a outra conta. Entre na conta que enviou o arquivo.")
        if not _valid_source(payload["source"]):
            raise invalid
        return payload["source"]
    except HTTPException:
        raise
    except (TypeError, ValueError, RecursionError, UnicodeDecodeError):
        raise invalid
