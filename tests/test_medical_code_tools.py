import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from src.services.medical_code_service import MedicalCodeService, MedicalCodeResult
from src.services.example_store import ExampleStore, CodeExample
from src.services.llm_service import LLMService
from src.config import settings
from sqlalchemy.orm import Session


class TestMedicalCodeTools:
    """Test cases for the medical code lookup tools."""

    @pytest.fixture
    def mock_example_store(self):
        """Fixture for a mocked ExampleStore."""
        mock_store = AsyncMock(spec=ExampleStore)
        
        # Mock the get_similar_examples method to return empty list by default
        mock_store.get_similar_examples.return_value = []
        
        # Mock the format_examples_for_prompt method
        mock_store.format_examples_for_prompt.return_value = "No similar examples found."
        
        # Mock the add_example method
        mock_store.add_example.return_value = None
        
        # Mock the _load_initial_examples method
        mock_store._load_initial_examples = AsyncMock(return_value=None)
        
        return mock_store
        
    @pytest.fixture
    def medical_code_service(self, db_session, mock_example_store):
        """Fixture for MedicalCodeService with database connection and mocked ExampleStore."""
        service = MedicalCodeService(db=db_session)
        service.example_store = mock_example_store
        return service

    @pytest.mark.asyncio
    async def test_rxnorm_lookup_not_found(self, medical_code_service, mock_example_store):
        """Test RxNorm lookup when code is not found."""
        # Arrange
        medication = "Unknown medication that does not exist"

        # Act - make real API call to RxNav
        result = await medical_code_service.lookup_rxnorm(medication)

        # Assert
        # We expect result to be None when no match is found
        # This matches the behavior expected in clinical_note_agent.py
        assert result is None

    @pytest.mark.asyncio
    async def test_rxnorm_lookup_multiple_medications(self, medical_code_service, mock_example_store):
        """Test RxNorm lookup for multiple common medications."""
        # Common medications with their expected RxNorm codes
        medications = [
            {
                "input": "Metformin 500mg",
                "expected_code": "860974",  # Metformin
                "expected_name": "metformin",
            },
            {
                "input": "atorvastatin 20mg tablet",
                "expected_codes": [
                    "617310",
                    "597966",
                ],  # Atorvastatin - both codes are valid
                "expected_name": "atorvastatin",
            },
            {
                "input": "Lisinopril 10mg",
                "expected_code": "316151",  # Lisinopril
                "expected_name": "lisinopril",
            },
            {
                "input": "Amoxicillin 500mg",
                "expected_code": "317616",  # Amoxicillin
                "expected_name": "amoxicillin",
            },
            {
                "input": "Ibuprofen 200mg",
                "expected_code": "316074",  # Ibuprofen
                "expected_name": "ibuprofen",
            },
        ]

        # Test each medication
        for med in medications:
            result = await medical_code_service.lookup_rxnorm(med["input"])

            # Assert the result
            assert result is not None, f"Failed to get result for {med['input']}"
            if "expected_codes" in med:
                assert (
                    result.code in med["expected_codes"]
                ), f"Wrong code for {med['input']}. Expected one of {med['expected_codes']}, got {result.code}"
            else:
                assert (
                    result.code == med["expected_code"]
                ), f"Wrong code for {med['input']}. Expected {med['expected_code']}, got {result.code}"
            assert (
                med["expected_name"] in result.description.lower()
            ), f"Wrong description for {med['input']}. Expected {med['expected_name']}, got {result.description}"

    @pytest.mark.asyncio
    async def test_icd10_lookup_not_found(self, medical_code_service, mock_example_store):
        """Test ICD-10 lookup when code is not found."""
        # Arrange
        condition = "Unknown condition that does not exist"

        # Act - make real API call to NLM Clinical Tables API
        result = await medical_code_service.lookup_icd10(condition)

        # Assert
        # We expect result to be None when no match is found
        # This matches the behavior expected in clinical_note_agent.py
        assert result is None

    @pytest.mark.asyncio
    async def test_icd10_lookup_multiple_conditions(self, medical_code_service, mock_example_store):
        """Test ICD-10 lookup for multiple common conditions."""
        # Common conditions with their expected ICD-10 codes
        conditions = [
            {
                "input": "Type 2 diabetes mellitus unspecified",
                "expected_code": "E11.8",  # Type 2 diabetes without complications
                "expected_name": "diabetes",
            },
            {
                "input": "Essential hypertension",
                "expected_code": "I10",  # Essential (primary) hypertension
                "expected_name": "hypertension",
            },
            {
                "input": "Asthma unspecified",
                "expected_code": "J45.909",  # Unspecified asthma, uncomplicated
                "expected_name": "asthma",
            },
        ]

        # Test each condition
        for condition in conditions:
            result = await medical_code_service.lookup_icd10(condition["input"])

            # Assert the result
            assert result is not None, f"Failed to get result for {condition['input']}"
            assert (
                result.code == condition["expected_code"]
            ), f"Wrong code for {condition['input']}. Expected {condition['expected_code']}, got {result.code}"
            assert (
                condition["expected_name"] in result.description.lower()
            ), f"Wrong description for {condition['input']}. Expected {condition['expected_name']}, got {result.description}"
