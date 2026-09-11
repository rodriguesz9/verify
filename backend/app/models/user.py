from sqlalchemy import Column, String, DateTime, Enum as SAEnum, Boolean
from sqlalchemy.sql import func
from app.core.database import Base, GUID
import uuid
import enum


class UserTier(str, enum.Enum):
    STANDARD   = "Standard"
    PREMIUM    = "Premium"
    ENTERPRISE = "Enterprise"


class User(Base):
    __tablename__ = "users"

    id              = Column(GUID, primary_key=True, default=uuid.uuid4, index=True)
    google_id       = Column(String(255), nullable=True, index=True) 
    email           = Column(String(254), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True) # Allowed null for OAuth only users
    name            = Column(String(120), nullable=False)
    avatar_url      = Column(String(512), nullable=True)
    
    tier            = Column(SAEnum(UserTier), default=UserTier.STANDARD, nullable=False)
    is_active       = Column(Boolean, default=True, nullable=False)
    
    last_login      = Column(DateTime(timezone=True), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
