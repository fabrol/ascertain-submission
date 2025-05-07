from fastapi import Depends
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.llm_service import LLMService
from src.services.medical_code_service import MedicalCodeService
from src.services.clinical_note_agent import ClinicalNoteAgent


async def get_llm_service(db: Session = Depends(get_db)) -> LLMService:
    """Dependency to get a single LLM service instance per request."""
    return LLMService(db=db)


async def get_medical_code_service(
    db: Session = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service),
) -> MedicalCodeService:
    """Dependency to get a single medical code service instance per request."""
    return MedicalCodeService(db, llm_service)


async def get_clinical_note_agent(
    db: Session = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service),
    medical_code_service: MedicalCodeService = Depends(get_medical_code_service),
) -> ClinicalNoteAgent:
    """Dependency to get a single clinical note agent instance per request."""
    return ClinicalNoteAgent(db, llm_service)
