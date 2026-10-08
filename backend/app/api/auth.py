import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database import get_db
from app.core.security import (
    create_access_token, create_refresh_token, decode_token,
    hash_password, verify_password,
    sanitize, validate_email, validate_password_strength
)
from app.core.auth import get_current_user, verify_google_id_token
from app.core.rate_limit import limiter
from app.models.user import User, UserTier

router = APIRouter(prefix="/auth")
_LOGIN_ERROR = "E-mail ou senha inválidos."
_GOOGLE_ERROR = "Não foi possível entrar com o Google. Use e-mail e senha ou tente novamente."

# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterBody(BaseModel):
    email:    str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=6, max_length=128)
    name:     str = Field(min_length=1, max_length=100)

    @field_validator("email")
    def email_valid(cls, v):
        if not validate_email(v): raise ValueError("E-mail parece inválido.")
        return v.lower()

    @field_validator("password")
    def password_valid(cls, v):
        # We simplify for seniors but keep a minimum
        if len(v) < 6:
            raise ValueError("A senha deve ter pelo menos 6 letras ou números.")
        return v


class LoginBody(BaseModel):
    email:    str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class GoogleBody(BaseModel):
    id_token: str = Field(min_length=10, max_length=10000)


class AuthOut(BaseModel):
    detail: str = "Sessão iniciada."


_ACCESS_COOKIE = "verifai_access"
_REFRESH_COOKIE = "verifai_refresh"
_ACCESS_MAX_AGE = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")) * 60
_REFRESH_MAX_AGE = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")) * 24 * 60 * 60
_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
_COOKIE_SAME_SITE = os.getenv("COOKIE_SAME_SITE", "lax").lower()
if _COOKIE_SAME_SITE not in {"lax", "strict", "none"}:
    _COOKIE_SAME_SITE = "lax"


def _set_auth_cookies(response: Response, user_id: str) -> None:
    """Issue tokens only as same-site, HTTP-only cookies."""
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(
        key=_ACCESS_COOKIE,
        value=create_access_token(user_id),
        max_age=_ACCESS_MAX_AGE,
        path="/",
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAME_SITE,
    )
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=create_refresh_token(user_id),
        max_age=_REFRESH_MAX_AGE,
        path="/api/auth/refresh",
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite=_COOKIE_SAME_SITE,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    for cookie_name, path in [(_ACCESS_COOKIE, "/"), (_REFRESH_COOKIE, "/api/auth/refresh")]:
        response.delete_cookie(
            cookie_name,
            path=path,
            secure=_COOKIE_SECURE,
            samesite=_COOKIE_SAME_SITE,
        )


def _user_to_dict(user: User) -> dict:
    return {
        "id":         str(user.id),
        "email":      user.email,
        "name":       user.name,
        "tier":       user.tier.value,
        "avatar_url": user.avatar_url,
    }


# ── Auth Endpoints ─────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthOut)
async def register(body: RegisterBody, response: Response, db: AsyncSession = Depends(get_db)):
    # Check email
    res = await db.execute(select(User).where(User.email == body.email))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Este e-mail já está sendo usado.")

    try:
        user = User(
            email=body.email,
            hashed_password=hash_password(body.password),
            name=sanitize(body.name),
            tier=UserTier.STANDARD
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao salvar no banco de dados. Tente novamente.")

    _set_auth_cookies(response, str(user.id))
    return AuthOut()


@router.post("/login", response_model=AuthOut)
@limiter.limit("5/15minutes")
async def login(request: Request, body: LoginBody, response: Response, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.email == body.email.lower()))
    user = res.scalar_one_or_none()
    
    # Refused credentials must not expose account existence or start a session.
    if (not user or not user.is_active or not user.hashed_password
            or not verify_password(body.password, user.hashed_password)):
        raise HTTPException(status_code=401, detail=_LOGIN_ERROR)

    user.last_login = datetime.utcnow()
    await db.commit()

    _set_auth_cookies(response, str(user.id))
    return AuthOut()


@router.post("/google", response_model=AuthOut)
async def google_login(body: GoogleBody, response: Response, db: AsyncSession = Depends(get_db)):
    try:
        info = verify_google_id_token(body.id_token)
    except Exception:
        raise HTTPException(status_code=401, detail=_GOOGLE_ERROR)

    # Signature/audience/issuer/expiry are verified by google-auth; validate the
    # identity claims before any lookup or mutation. A truthy string is not a
    # verified email. OIDC subjects are opaque, case-sensitive ASCII identifiers.
    if not isinstance(info, dict):
        raise HTTPException(status_code=401, detail=_GOOGLE_ERROR)
    google_sub = info.get("sub")
    email_claim = info.get("email")
    if (not isinstance(google_sub, str) or not 1 <= len(google_sub) <= 255
            or not all(33 <= ord(char) <= 126 for char in google_sub)
            or info.get("email_verified") is not True
            or not isinstance(email_claim, str) or not validate_email(email_claim)):
        raise HTTPException(status_code=401, detail=_GOOGLE_ERROR)
    email = email_claim.lower()
    name_claim = info.get("name")
    name = sanitize(name_claim[:100]) if isinstance(name_claim, str) else ""
    name = name or email.split("@")[0][:100]
    picture_claim = info.get("picture")
    avatar = picture_claim if isinstance(picture_claim, str) and len(picture_claim) <= 512 else None

    # The current schema has no unique Google-subject constraint. Fail closed
    # for ambiguous legacy bindings rather than authenticating an arbitrary row.
    result = await db.execute(select(User).where(User.google_id == google_sub).limit(2))
    matches = result.scalars().all()
    if len(matches) > 1:
        raise HTTPException(status_code=401, detail=_GOOGLE_ERROR)
    user = matches[0] if matches else None
    if user and not user.is_active:
        raise HTTPException(status_code=401, detail=_GOOGLE_ERROR)

    if not user:
        # Subject remains the identity. Email may only link an unbound account
        # when Google is authoritative (Gmail or a signed Workspace hd claim).
        # Third-party email_verified alone does not prove current ownership:
        # https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
        res2 = await db.execute(select(User).where(User.email == email).with_for_update())
        user = res2.scalar_one_or_none()
        if user:
            hosted_domain = info.get("hd")
            authoritative_email = (
                email.endswith("@gmail.com")
                or (isinstance(hosted_domain, str) and bool(hosted_domain.strip()))
            )
            if (not user.is_active or user.google_id not in {None, google_sub}
                    or not authoritative_email):
                raise HTTPException(status_code=401, detail=_GOOGLE_ERROR)
            user.google_id = google_sub
            if avatar: user.avatar_url = avatar
        else:
            user = User(
                email=email,
                name=name,
                google_id=google_sub,
                avatar_url=avatar,
                tier=UserTier.STANDARD
            )
            db.add(user)

    user.last_login = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    _set_auth_cookies(response, str(user.id))
    return AuthOut()


@router.post("/refresh", response_model=AuthOut)
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get(_REFRESH_COOKIE)
    if not refresh_token:
        raise HTTPException(status_code=401)
    
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh": raise ValueError()
        user_id = payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401)

    _set_auth_cookies(response, str(user.id))
    return AuthOut()


@router.post("/logout", status_code=204)
async def logout(response: Response):
    _clear_auth_cookies(response)


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return _user_to_dict(user)
