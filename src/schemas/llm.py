from pydantic import BaseModel
from typing import Dict, Optional


class MedicalNote(BaseModel):
    """Schema for medical note input."""

    text: str


class LLMResponse(BaseModel):
    """Schema for LLM service response."""

    summary: str
    vitals: Dict[str, str]
    doctor: str
    error: Optional[str] = None
