"""
Auth helpers for Antigravity Core.
"""

import os
from datetime import datetime, timezone, date

from fastapi import Depends, HTTPException, status, Request
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserTier
from app.models.history import Verification, ContentType

_GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
_ACCESS_COOKIES = ["verify_access", "verifai_access"]

def _extract_token_from_request(request: Request) -> str | None:
    # 1. Cookie
    for c_name in _ACCESS_COOKIES:
        tok = request.cookies.get(c_name)
        if tok:
            return tok
    # 2. Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return None

# Tiers-based DAILY LIMITS
DAILY_LIMITS = {
    UserTier.STANDARD:   {"TEXTUAL": 300, "MEDIA": 100},
    UserTier.PREMIUM:    {"TEXTUAL": 10000, "MEDIA": 5000},
    UserTier.ENTERPRISE: {"TEXTUAL": 9999, "MEDIA": 9999},
}


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    token = _extract_token_from_request(request)
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id: str = payload.get("sub")
        if not user_id:
            return None
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            return None
        return user
    except Exception:
        return None


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão inválida ou expirada.",
    )
    token = _extract_token_from_request(request)
    if not token:
        raise cred_exc
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise cred_exc
        user_id: str = payload.get("sub")
        if not user_id:
            raise cred_exc
    except JWTError:
        raise cred_exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise cred_exc
    return user


async def verify_limit(user: User | None, db: AsyncSession, category: str, requested: int = 1):
    """
    Checks daily usage limits based on user tier. If user is None (guest), allow up to 30 requests.
    """
    if not user:
        return # Free guest quota

    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    
    # Filter by content type category
    if category == "TEXTUAL":
        q_types = [ContentType.TEXT]
    else:
        q_types = [ContentType.IMAGE, ContentType.AUDIO, ContentType.VIDEO]
    
    count_result = await db.execute(
        select(func.count(Verification.id)).where(
            Verification.user_id == user.id,
            Verification.created_at >= today_start,
            Verification.content_type.in_(q_types)
        )
    )
    daily_count = count_result.scalar_one() or 0
    
    tier_limits = DAILY_LIMITS.get(user.tier, DAILY_LIMITS[UserTier.STANDARD])
    limit = tier_limits.get(category, 0)

    if daily_count + requested > limit:
        cat_name = "texto/URL" if category == "TEXTUAL" else "mídia"
        raise HTTPException(
            status_code=429,
            detail={
                "error": "limite_diario",
                "message": f"Limite diário atingido ({limit}/{cat_name}). Tente novamente amanhã.",
            },
        )


def verify_google_id_token(token: str) -> dict:
    try:
        return google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            _GOOGLE_CLIENT_ID,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token Google inválido: {str(e)[:80]}",
        )
