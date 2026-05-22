from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base
import uuid
import enum


class QueryType(str, enum.Enum):
    TEXT   = "text"
    URL    = "url"
    IMAGE  = "image"
    AUDIO  = "audio"
    VIDEO  = "video"


class VerificationLog(Base):
    __tablename__ = "verification_logs"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    query_type   = Column(SAEnum(QueryType), nullable=False)
    query_input  = Column(Text, nullable=False)           # sanitized input text / url / filename

    # Full result stored as JSONB
    result       = Column(JSON, nullable=False)

    # Quick-access fields (denormalized for dashboard queries)
    score        = Column(Integer, nullable=False)
    verdict      = Column(String(20), nullable=False)
    summary      = Column(Text, nullable=True)

    created_at   = Column(DateTime(timezone=True), server_default=func.now(), index=True)
