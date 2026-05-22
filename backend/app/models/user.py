from sqlalchemy import Column, String, DateTime, Enum as SAEnum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base
import uuid
import enum


class Plan(str, enum.Enum):
    FREE       = "FREE"
    PRO        = "PRO"
    ENTERPRISE = "ENTERPRISE"


class OAuthProvider(str, enum.Enum):
    LOCAL  = "local"
    GOOGLE = "google"


class User(Base):
    __tablename__ = "users"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email           = Column(String(254), unique=True, nullable=False, index=True)
    name            = Column(String(120), nullable=False)
    hashed_password = Column(String(512), nullable=True)          # null for OAuth users
    plan            = Column(SAEnum(Plan), default=Plan.FREE, nullable=False)
    is_active       = Column(Boolean, default=True, nullable=False)
    is_verified     = Column(Boolean, default=False, nullable=False)

    # OAuth
    oauth_provider  = Column(SAEnum(OAuthProvider), default=OAuthProvider.LOCAL, nullable=False)
    oauth_id        = Column(String(255), nullable=True, index=True)
    avatar_url      = Column(String(512), nullable=True)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
