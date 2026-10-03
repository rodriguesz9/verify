from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, JSON, Enum as SAEnum, Float, Boolean
from sqlalchemy.sql import func
from app.core.database import Base, GUID
import uuid
import enum


class ContentType(str, enum.Enum):
    TEXT   = "Text"
    IMAGE  = "Image"
    AUDIO  = "Audio"
    VIDEO  = "Video"


class VerdictLabel(str, enum.Enum):
    AUTHENTIC      = "Authentic"
    AI_GENERATED   = "AI_Generated"
    MANIPULATED    = "Manipulated"
    OUT_OF_CONTEXT = "Out_Of_Context"
    SUSPICIOUS     = "Suspicious"
    SCAM           = "Scam"
    FALSE          = "False"


class Verification(Base):
    __tablename__ = "verifications"

    id              = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id         = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    content_type    = Column(SAEnum(ContentType), nullable=False)
    source_url      = Column(String(512), nullable=True)
    file_hash_md5   = Column(String(32), nullable=True, index=True)

    verdict_score   = Column(Integer, nullable=False) # 0 to 100
    verdict_label   = Column(SAEnum(VerdictLabel), nullable=False)
    ai_summary      = Column(Text, nullable=True)
    
    # Full tech result for deep-dive
    raw_result      = Column(JSON, nullable=False)

    created_at      = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class AnalysisMetrics(Base):
    __tablename__ = "analysis_metrics"

    id                       = Column(GUID, primary_key=True, default=uuid.uuid4)
    verification_id          = Column(GUID, ForeignKey("verifications.id", ondelete="CASCADE"), nullable=False)

    sightengine_ai_score     = Column(Float, nullable=True)
    sightengine_deepfake_score = Column(Float, nullable=True)
    huggingface_model_score  = Column(Float, nullable=True)
    text_ai_probability      = Column(Float, nullable=True)
    
    earliest_known_date      = Column(DateTime(timezone=True), nullable=True)


class CacheRegistry(Base):
    __tablename__ = "cache_registry"

    file_hash_md5     = Column(String(32), primary_key=True)
    cached_verdict_id = Column(GUID, ForeignKey("verifications.id", ondelete="CASCADE"), nullable=False)
    expires_at        = Column(DateTime(timezone=True), nullable=False)


class AuthenticitySeal(Base):
    """
    Tamper-evident authenticity seal (C2PA caseiro).
    Binds media SHA-256 hash with cryptographic HMAC signature and server timestamp.
    """
    __tablename__ = "authenticity_seals"

    id               = Column(GUID, primary_key=True, default=uuid.uuid4)
    file_hash_sha256 = Column(String(64), unique=True, nullable=False, index=True)
    file_name        = Column(String(255), nullable=True)
    media_type       = Column(String(50), default="image")
    file_size_bytes  = Column(Integer, nullable=True)
    signature_hmac   = Column(String(64), nullable=False)
    captured_at      = Column(DateTime(timezone=True), server_default=func.now())
    metadata_json    = Column(JSON, nullable=True)


class WhatsAppConversation(Base):
    """
    Histórico anônimo das conversas do bot de WhatsApp (Módulo 2).
    Nenhum número de telefone bruto é persistido: apenas um hash SHA-256.
    """
    __tablename__ = "whatsapp_conversations"

    id              = Column(GUID, primary_key=True, default=uuid.uuid4)
    sender_hash     = Column(String(64), nullable=False, index=True)
    content_type    = Column(String(20), default="text")   # text, audio, image
    query_preview   = Column(Text, nullable=True)
    verdict_label   = Column(String(40), nullable=True)
    verdict_score   = Column(Integer, nullable=True)
    reply_text      = Column(Text, nullable=True)
    had_audio_reply = Column(Boolean, default=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now(), index=True)
