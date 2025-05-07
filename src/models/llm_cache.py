from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from .base import Base


class LLMCache(Base):
    __tablename__ = "llm_cache"

    id = Column(Integer, primary_key=True, index=True)
    note_hash = Column(String(64), unique=True, index=True)  # SHA-256 hash of the note
    content = Column(Text)  # The actual cached content
    version = Column(
        String(32), nullable=False
    )  # Schema version for cache invalidation
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
