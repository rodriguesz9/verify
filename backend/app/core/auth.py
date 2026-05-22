"""
Auth helpers:
  - get_current_user FastAPI dependency
  - Google ID-token verification
  - Daily usage limit check (plan middleware)
"""

import os
from datetime import datetime, timezone, date

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.models.history import VerificationLog, QueryType

_bearer = HTTPBearer(auto_error=True)
_GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

# Limits per query type category
# Category: "TEXTUAL" (text, url)
# Category: "MEDIA"   (image, audio, video)
DAILY_LIMITS = {
    "FREE":       {"TEXTUAL": 3, "MEDIA": 1},
    "PRO":        {"TEXTUAL": 100, "MEDIA": 50},
    "ENTERPRISE": {"TEXTUAL": 9999, "MEDIA": 9999},
}


# ── Current user dependency ───────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
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


# ── Optional user ────────────────────────────────────────────────────────────

_optional_bearer = HTTPBearer(auto_error=False)

async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except Exception:
        return None


# ── Daily usage check ─────────────────────────────────────────────────────────

async def check_daily_limit(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Checks if the user has reached their daily limit for the category of the request.
    Note: Since this is a dependency injected into specific routes, 
    it needs to know the context. However, to keep it simple, we check both 
    and the caller (route) might just trust it or we can pass a parameter.
    
    Actually, let's keep it simple: any verification check increments a counter.
    But the user wants 3 for text and 1 for media.
    """
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)

    # Get counts for different types
    textual_types = [QueryType.TEXT, QueryType.URL]
    media_types   = [QueryType.IMAGE, QueryType.AUDIO, QueryType.VIDEO]

    # This check is called BEFORE the action.
    # We don't know yet if it's textual or media here unless we use a factory or check request path.
    # To keep it generic, we'll return user and the route handler will check specific sub-limit.
    # OR we can just check if ANY limit is remaining.
    
    # Better: the route handler itself should check the limit using a helper.
    return user


async def verify_limit(user: User, db: AsyncSession, category: str):
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    
    q_types = [QueryType.TEXT, QueryType.URL] if category == "TEXTUAL" else [QueryType.IMAGE, QueryType.AUDIO, QueryType.VIDEO]
    
    count_result = await db.execute(
        select(func.count(VerificationLog.id)).where(
            VerificationLog.user_id == user.id,
            VerificationLog.created_at >= today_start,
            VerificationLog.query_type.in_(q_types)
        )
    )
    daily_count = count_result.scalar_one()
    plan_limits = DAILY_LIMITS.get(user.plan.value, DAILY_LIMITS["FREE"])
    limit = plan_limits.get(category, 0)

    if daily_count >= limit:
        cat_name = "texto/URL" if category == "TEXTUAL" else "mídia (imagem/vídeo/áudio)"
        raise HTTPException(
            status_code=429,
            detail={
                "error": "limite_diario",
                "message": f"Limite diário de {limit} análises de {cat_name} atingido. Faça upgrade para o plano PRO!",
                "used": daily_count,
                "limit": limit,
                "plan": user.plan.value,
                "category": category
            },
        )


# ── Google OAuth verification ───────────────────────────────────────────────

def verify_google_id_token(token: str) -> dict:
    try:
        idinfo = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            _GOOGLE_CLIENT_ID,
        )
        return idinfo
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token Google inválido: {str(e)[:80]}",
        )
