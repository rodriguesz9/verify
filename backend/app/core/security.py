"""
Security utilities:
  - Argon2 password hashing  (argon2-cffi)
  - JWT access / refresh tokens  (python-jose)
  - Input sanitization to prevent XSS  (bleach)
  - Input length / pattern validation
"""

import os
import re
import bleach
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from jose import JWTError, jwt

# ── Argon2 configuration (OWASP recommended parameters) ───────────────────────
_ph = PasswordHasher(
    time_cost=3,        # iterations
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

def hash_password(plain: str) -> str:
    return _ph.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False

# ── JWT ───────────────────────────────────────────────────────────────────────
_SECRET    = os.getenv("JWT_SECRET", "change_me_please_32_chars_minimum!")
_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
_ACCESS_EXP  = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
_REFRESH_EXP = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS",  "7"))


def create_access_token(subject: str, extra: dict | None = None) -> str:
    payload: dict[str, Any] = {
        "sub":  subject,
        "type": "access",
        "exp":  datetime.now(timezone.utc) + timedelta(minutes=_ACCESS_EXP),
        "iat":  datetime.now(timezone.utc),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    payload = {
        "sub":  subject,
        "type": "refresh",
        "exp":  datetime.now(timezone.utc) + timedelta(days=_REFRESH_EXP),
        "iat":  datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """Raises JWTError if invalid or expired."""
    return jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])


# ── XSS / Injection sanitization ─────────────────────────────────────────────
# No HTML allowed in API inputs — strip everything.
_ALLOWED_TAGS: list[str] = []
_ALLOWED_ATTRS: dict = {}

def sanitize(value: str) -> str:
    """Strip all HTML tags and attributes to prevent XSS."""
    cleaned = bleach.clean(value, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS, strip=True)
    return cleaned.strip()


# ── Password strength ─────────────────────────────────────────────────────────
_PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,128}$")

def validate_password_strength(password: str) -> bool:
    """Min 8 chars, at least 1 uppercase, 1 lowercase, 1 digit."""
    return bool(_PASSWORD_RE.match(password))


# ── Email validation ──────────────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

def validate_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email)) and len(email) <= 254
