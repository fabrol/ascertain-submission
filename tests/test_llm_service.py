import pytest
import pytest_asyncio
from src.services.llm_service import LLMService, LLMResponse
from src.models.llm_cache import LLMCache
from src.config import settings
from sqlalchemy.orm import Session


@pytest.fixture
def llm_service_with_db(db_session):
    """Fixture for LLM service with database connection."""
    return LLMService(db=db_session)


@pytest.fixture
def llm_service_without_db():
    """Fixture for LLM service without database connection."""
    return LLMService()


TEST_MODEL = "gpt-4o-mini"


@pytest.fixture
def sample_medical_note():
    return """
Patient: John Doe
Date: 2024-03-15

S: Patient presents for routine follow-up. Reports feeling well, no new complaints.
Denies chest pain, SOB, or dizziness. Reports good sleep and appetite.

O:
Vitals:
BP: 120/80 mmHg
HR: 72 bpm
RR: 16 breaths/min
Temp: 98.6°F

Physical Exam:
General: Well-appearing, NAD
CV: RRR, no murmurs
Lungs: CTA bilaterally
Abd: Soft, NT/ND

A: Stable, no acute issues
P: Continue current medications
Follow-up in 6 months

Signed:
Dr. Sarah Johnson, MD
"""


@pytest.mark.asyncio
@pytest.mark.integration
async def test_process_prompt(llm_service_without_db, sample_medical_note):
    """Test the LLM service with a real API call."""
    system_prompt = (
        "You are a medical note analyzer. Extract key information from the note."
    )
    result = await llm_service_without_db.process_prompt(
        system_prompt=system_prompt,
        user_prompt=sample_medical_note,
        model=TEST_MODEL,
    )

    # Basic response structure validation
    assert isinstance(result, LLMResponse)
    assert result.error is None, f"LLM service returned an error: {result.error}"
    assert isinstance(result.content, str)
    assert len(result.content) > 0, "Content should not be empty"


@pytest.mark.asyncio
async def test_process_prompt_with_error(llm_service_without_db):
    """Test error handling with invalid input."""
    system_prompt = "You are a medical note analyzer."
    result = await llm_service_without_db.process_prompt(
        system_prompt=system_prompt,
        user_prompt="",
        model=TEST_MODEL,
    )
    assert result.error is not None, "Empty input should result in an error"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_llm_cache_hit(llm_service_with_db, sample_medical_note, db_session):
    """Test that repeated calls with the same note use the cache."""
    system_prompt = "You are a medical note analyzer."
    # First call - should hit the API and create cache
    first_result = await llm_service_with_db.process_prompt(
        system_prompt=system_prompt,
        user_prompt=sample_medical_note,
        model=TEST_MODEL,
    )
    assert first_result.error is None

    # Second call - should use cache
    second_result = await llm_service_with_db.process_prompt(
        system_prompt=system_prompt,
        user_prompt=sample_medical_note,
        model=TEST_MODEL,
    )
    assert second_result.error is None

    # Results should be identical since second call uses cache
    assert first_result.content == second_result.content


@pytest.mark.asyncio
@pytest.mark.integration
async def test_llm_cache_version_mismatch(
    llm_service_with_db, sample_medical_note, db_session
):
    """Test cache behavior when version mismatches."""
    system_prompt = "You are a medical note analyzer."
    # First call with original version
    first_result = await llm_service_with_db.process_prompt(
        system_prompt=system_prompt,
        user_prompt=sample_medical_note,
        model=TEST_MODEL,
    )
    assert first_result.error is None

    # Modify cache version
    cache_entry = db_session.query(LLMCache).first()
    cache_entry.version = "0.0.1"
    db_session.commit()

    # Second call should not use cache due to version mismatch
    second_result = await llm_service_with_db.process_prompt(
        system_prompt=system_prompt,
        user_prompt=sample_medical_note,
        model="gpt-4o-mini",
    )
    assert second_result.error is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_llm_cache_different_notes(llm_service_with_db, db_session):
    """Test that different notes get different cache entries."""
    system_prompt = "You are a medical note analyzer."
    note1 = "Patient has a fever"
    note2 = "Patient has a cough"

    # Process first note
    result1 = await llm_service_with_db.process_prompt(
        system_prompt=system_prompt,
        user_prompt=note1,
        model=TEST_MODEL,
    )
    assert result1.error is None

    # Process second note
    result2 = await llm_service_with_db.process_prompt(
        system_prompt=system_prompt,
        user_prompt=note2,
        model=TEST_MODEL,
    )
    assert result2.error is None

    # Results should be different
    assert result1.content != result2.content


@pytest.mark.asyncio
@pytest.mark.integration
async def test_llm_cache_without_db(llm_service_without_db, sample_medical_note):
    """Test that service works without caching."""
    system_prompt = "You are a medical note analyzer."
    # Multiple calls should work but won't use cache
    result1 = await llm_service_without_db.process_prompt(
        system_prompt=system_prompt,
        user_prompt=sample_medical_note,
        model=TEST_MODEL,
    )
    result2 = await llm_service_without_db.process_prompt(
        system_prompt=system_prompt,
        user_prompt=sample_medical_note,
        model=TEST_MODEL,
    )

    assert result1.error is None
    assert result2.error is None
