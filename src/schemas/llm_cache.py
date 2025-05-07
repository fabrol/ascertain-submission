from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class LLMCacheBase(BaseModel):
    note_hash: str
    content: str
    version: str


class LLMCacheCreate(LLMCacheBase):
    pass


class LLMCache(LLMCacheBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
