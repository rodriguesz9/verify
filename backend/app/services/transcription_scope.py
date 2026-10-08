"""Request-local ownership for short-lived ASR jobs; never an auth credential.

Anonymous resumption requires a random, memory-only tab nonce AND identical
audio. Verified accounts always override that header. Missing scope disables
cross-request reuse. No namespace/job identifiers belong in public reports.
"""

from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import hmac
import re
import secrets

_scope: ContextVar[str | None] = ContextVar("verify_transcription_scope", default=None)
_secret = secrets.token_bytes(32)
SCOPE_HEADER = "X-Verify-Analysis-Scope"


def _opaque(value: str) -> str:
    return hmac.new(_secret, value.encode(), hashlib.sha256).hexdigest()


def request_transcription_scope(request, user=None) -> str | None:
    # user is resolved by get_optional_user, never supplied in a request body.
    if user is not None and getattr(user, "id", None) is not None:
        return _opaque("account\0" + str(user.id))
    nonce = request.headers.get(SCOPE_HEADER, "")
    if isinstance(nonce, str) and re.fullmatch(r"[a-f0-9]{32}", nonce):
        return _opaque("anonymous-tab\0" + nonce)
    return None


def webhook_transcription_scope(authenticated_receipt: str) -> str | None:
    # Caller MUST first authenticate the gateway and parse its receipt. Public
    # simulator from_number is deliberately never used as an ownership proof.
    if re.fullmatch(r"[a-f0-9]{64}", authenticated_receipt or ""):
        return _opaque("authenticated-webhook\0" + authenticated_receipt)
    return None


def current_transcription_scope() -> str | None:
    return _scope.get()


@contextmanager
def transcription_scope(namespace: str | None):
    token = _scope.set(namespace)
    try:
        yield
    finally:
        _scope.reset(token)


PENDING_STATUSES = frozenset({"pending", "in_progress", "blocked_uncertain", "blocked_expired"})


def has_pending_transcription(report: dict) -> bool:
    """Only ASR status, not detector/visual pending state, controls resumption."""
    if not isinstance(report, dict):
        return False
    track = report.get("audio_analysis", {})
    track = track if isinstance(track, dict) else {}
    audio = report.get("forensics", {}).get("audio", {}) if isinstance(report.get("forensics"), dict) else {}
    track_audio = track.get("forensics", {}).get("audio", {}) if isinstance(track.get("forensics"), dict) else {}
    for payload in (report, audio, track, track_audio):
        if not isinstance(payload, dict):
            continue
        detail = payload.get("transcription_detail", {})
        if isinstance(detail, dict) and detail.get("status") in PENDING_STATUSES:
            return True
    return False
