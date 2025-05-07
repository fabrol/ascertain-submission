from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from .models.base import Base
from .models.document import Document
from .schemas.document import Document as DocumentSchema, DocumentCreate
from .schemas.llm import MedicalNote, LLMResponse
from .schemas.clinical_note import ClinicalNoteRequest, ClinicalNoteResponse
from .services.clinical_note_agent import ClinicalNoteAgent
from .services.fhir_conversion_service import FHIRConversionService
from .database import engine, get_db
from .repositories.document import DocumentRepository
from .config import settings
from .dependencies import (
    get_clinical_note_agent,
)
import logging

logger = logging.getLogger(__name__)

# Initialize services
app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Medical Document Analysis API"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/documents/", response_model=DocumentSchema)
def create_document(document: DocumentCreate, db: Session = Depends(get_db)):
    repo = DocumentRepository(db)
    return repo.create(document)


@app.get("/documents/", response_model=List[DocumentSchema])
def read_documents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    repo = DocumentRepository(db)
    return repo.get_all(skip=skip, limit=limit)


@app.get("/documents/{document_id}", response_model=DocumentSchema)
def read_document(document_id: int, db: Session = Depends(get_db)):
    repo = DocumentRepository(db)
    db_document = repo.get(document_id)
    if db_document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return db_document


@app.post("/analyze-note", response_model=ClinicalNoteResponse)
async def analyze_note(
    request: ClinicalNoteRequest,
    clinical_note_agent: ClinicalNoteAgent = Depends(get_clinical_note_agent),
) -> ClinicalNoteResponse:
    """Analyze a clinical note and extract structured information."""
    try:
        return await clinical_note_agent.process_clinical_note(request.note_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract-structured", response_model=ClinicalNoteResponse)
async def extract_structured(
    request: ClinicalNoteRequest,
    clinical_note_agent: ClinicalNoteAgent = Depends(get_clinical_note_agent),
) -> ClinicalNoteResponse:
    """Extract structured information from a clinical note."""
    try:
        return await clinical_note_agent.process_clinical_note(request.note_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/to_fhir", response_model=dict)
async def convert_to_fhir(clinical_note: ClinicalNoteResponse):
    """Convert clinical note data to FHIR format.

    Args:
        clinical_note: The structured clinical note data

    Returns:
        Dictionary containing FHIR resources
    """
    try:
        fhir_service = FHIRConversionService()
        fhir_resources = fhir_service.convert_to_fhir(clinical_note)
        return fhir_resources
    except Exception as e:
        logger.error(f"Error converting to FHIR format: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
