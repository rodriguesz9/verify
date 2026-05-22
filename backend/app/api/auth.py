from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, field_validator
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
from app.models.user import User, UserTier

router = APIRouter(prefix="/auth")

# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterBody(BaseModel):
    email:    str
    password: str
    name:     str

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
    email:    str
    password: str


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
        "tier":       user.tier.value,
        "avatar_url": user.avatar_url,
    }


# ── Auth Endpoints ─────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenOut)
async def register(body: RegisterBody, db: AsyncSession = Depends(get_db)):
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
    except Exception as e:
        print(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Erro ao salvar no banco de dados. Tente novamente.")

    return TokenOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/login", response_model=TokenOut)
async def login(body: LoginBody, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.email == body.email.lower()))
    user = res.scalar_one_or_none()
    
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="E-mail ou senha não encontrados.")
    
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Senha incorreta.")

    user.last_login = datetime.utcnow()
    await db.commit()

    return TokenOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/google", response_model=TokenOut)
async def google_login(body: GoogleBody, db: AsyncSession = Depends(get_db)):
    try:
        info = verify_google_id_token(body.id_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Falha na verificação com o Google.")
        
    google_sub = info["sub"]
    email      = info.get("email", "").lower()
    name       = sanitize(info.get("name", email.split("@")[0])[:100])
    avatar     = info.get("picture")

    if not email:
        raise HTTPException(status_code=400, detail="O Google não forneceu um e-mail.")

    result = await db.execute(select(User).where(User.google_id == google_sub))
    user = result.scalar_one_or_none()

    if not user:
        # Check if email exists
        res2 = await db.execute(select(User).where(User.email == email))
        user = res2.scalar_one_or_none()
        if user:
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

    return TokenOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenOut)
async def refresh(body: dict, db: AsyncSession = Depends(get_db)):
    refresh_token = body.get("refresh_token")
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

    return TokenOut(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return _user_to_dict(user)
