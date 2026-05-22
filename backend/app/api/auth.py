from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    sanitize, validate_password_strength, validate_email,
)
from app.core.auth import get_current_user, verify_google_id_token
from app.models.user import User, Plan, OAuthProvider

router = APIRouter(prefix="/auth")

# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterBody(BaseModel):
    name:     str
    email:    str
    password: str

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = sanitize(v.strip())
        if len(v) < 2 or len(v) > 100:
            raise ValueError("Nome deve ter 2–100 caracteres")
        return v

    @field_validator("email")
    @classmethod
    def clean_email(cls, v: str) -> str:
        v = sanitize(v.strip().lower())
        if not validate_email(v):
            raise ValueError("E-mail inválido")
        return v

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        if not validate_password_strength(v):
            raise ValueError(
                "Senha deve ter no mínimo 8 caracteres, "
                "uma maiúscula, uma minúscula e um número."
            )
        return v


class LoginBody(BaseModel):
    email:    str
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


class GoogleBody(BaseModel):
    id_token: str


class TokenOut(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"


def _user_to_dict(user: User) -> dict:
    return {
        "id":         str(user.id),
        "email":      user.email,
        "name":       user.name,
        "plan":       user.plan.value,
        "avatar_url": user.avatar_url,
        "oauth":      user.oauth_provider.value != "local",
    }


# ── Register ──────────────────────────────────────────────────────────────────
@router.post("/register", response_model=TokenOut, status_code=201)
async def register(body: RegisterBody, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="E-mail já cadastrado.")

    user = User(
        email=body.email,
        name=body.name,
        hashed_password=hash_password(body.password),
        oauth_provider=OAuthProvider.LOCAL,
        is_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return TokenOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


# ── Login ─────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenOut)
async def login(body: LoginBody, request: Request, db: AsyncSession = Depends(get_db)):
    # rate limit is applied at main.py via slowapi (5/15min per IP)
    email = sanitize(body.email.strip().lower())
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Constant-time comparison — always hash even if user not found
    dummy_hash = "$argon2id$v=19$m=65536,t=3,p=4$dummysalt1234567$dummyhash000000000000000000000000000"
    pwd_ok = verify_password(body.password, user.hashed_password if user else dummy_hash)

    if not user or not user.is_active or not pwd_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
        )
    if user.oauth_provider != OAuthProvider.LOCAL:
        raise HTTPException(
            status_code=400,
            detail="Esta conta usa login social. Use 'Entrar com Google'.",
        )

    return TokenOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


# ── Google OAuth ──────────────────────────────────────────────────────────────
@router.post("/google", response_model=TokenOut)
async def google_login(body: GoogleBody, db: AsyncSession = Depends(get_db)):
    info = verify_google_id_token(body.id_token)
    google_sub = info["sub"]
    email      = info.get("email", "").lower()
    name       = sanitize(info.get("name", email.split("@")[0])[:100])
    avatar     = info.get("picture")

    # Try find by oauth_id first, then by email
    result = await db.execute(
        select(User).where(User.oauth_provider == OAuthProvider.GOOGLE, User.oauth_id == google_sub)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Check if email exists with local account — link it
        res2 = await db.execute(select(User).where(User.email == email))
        user = res2.scalar_one_or_none()
        if user:
            user.oauth_provider = OAuthProvider.GOOGLE
            user.oauth_id = google_sub
            if avatar:
                user.avatar_url = avatar
        else:
            user = User(
                email=email,
                name=name,
                oauth_provider=OAuthProvider.GOOGLE,
                oauth_id=google_sub,
                avatar_url=avatar,
                is_verified=True,
            )
            db.add(user)

    await db.commit()
    await db.refresh(user)

    return TokenOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


# ── Refresh ───────────────────────────────────────────────────────────────────
@router.post("/refresh", response_model=TokenOut)
async def refresh(body: RefreshBody, db: AsyncSession = Depends(get_db)):
    from jose import JWTError
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError()
        user_id = payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Refresh token inválido.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")

    return TokenOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


# ── Me ────────────────────────────────────────────────────────────────────────
@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return _user_to_dict(user)
