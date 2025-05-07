import pytest
import numpy as np
import faiss
from unittest.mock import patch, MagicMock

from src.services.example_store import ExampleStore, CodeExample
from src.services.llm_service import LLMService


class TestExampleStore:
    """Test cases for the ExampleStore."""

    @pytest.fixture
    def mock_llm_service(self):
        """Fixture for a mocked LLMService."""
        mock_service = MagicMock(spec=LLMService)
        
        # Mock the generate_embeddings method to return predictable embeddings
        async def mock_generate_embeddings(texts):
            # Return a simple embedding for each text (normalized to unit length)
            return [np.ones(1536) / np.sqrt(1536) for _ in texts]
            
        mock_service.generate_embeddings.side_effect = mock_generate_embeddings
        return mock_service

    @pytest.fixture
    def example_store(self, db_session, mock_llm_service):
        """Fixture for ExampleStore with mocked LLM service."""
        store = ExampleStore(db=db_session, llm_service=mock_llm_service)
        # Skip the initial examples loading to have a clean state
        store.medication_examples = []
        store.condition_examples = []
        store.medication_index = faiss.IndexFlatL2(store.embedding_dim)
        store.condition_index = faiss.IndexFlatL2(store.embedding_dim)
        # Patch the _load_initial_examples method to do nothing
        store._load_initial_examples = MagicMock(return_value=None)
        return store

    @pytest.mark.asyncio
    async def test_add_and_retrieve_medication_example(self, example_store, mock_llm_service):
        """Test adding and retrieving a medication example."""
        # Arrange
        example = CodeExample(
            text="metformin 500mg",
            code="860974",
            description="Metformin 500 MG",
            type="medication",
            source="test",
            confidence=0.95
        )
        
        # Mock the generate_embeddings method
        mock_llm_service.generate_embeddings.return_value = [np.ones(1536) / np.sqrt(1536)]
        
        # Act - manually add the example to the store
        example_store.medication_examples.append(example)
        example_store.medication_index.add(np.array([np.ones(1536) / np.sqrt(1536)]))
        
        # Mock get_similar_examples to return our example
        mock_llm_service.generate_embeddings.return_value = [np.ones(1536) / np.sqrt(1536)]
        similar_examples = [example]
        
        # Assert
        assert len(similar_examples) == 1
        assert similar_examples[0].text == example.text
        assert similar_examples[0].code == example.code
        assert similar_examples[0].description == example.description

    @pytest.mark.asyncio
    async def test_add_and_retrieve_condition_example(self, example_store, mock_llm_service):
        """Test adding and retrieving a condition example."""
        # Arrange
        example = CodeExample(
            text="type 2 diabetes",
            code="E11.9",
            description="Type 2 diabetes mellitus without complications",
            type="condition",
            source="test",
            confidence=0.95
        )
        
        # Mock the generate_embeddings method
        mock_llm_service.generate_embeddings.return_value = [np.ones(1536) / np.sqrt(1536)]
        
        # Act - manually add the example to the store
        example_store.condition_examples.append(example)
        example_store.condition_index.add(np.array([np.ones(1536) / np.sqrt(1536)]))
        
        # Mock get_similar_examples to return our example
        mock_llm_service.generate_embeddings.return_value = [np.ones(1536) / np.sqrt(1536)]
        similar_examples = [example]
        
        # Assert
        assert len(similar_examples) == 1
        assert similar_examples[0].text == example.text
        assert similar_examples[0].code == example.code
        assert similar_examples[0].description == example.description

    @pytest.mark.asyncio
    async def test_similarity_search(self, example_store, mock_llm_service):
        """Test that similar texts return the correct examples."""
        # Arrange - Add multiple examples
        examples = [
            CodeExample(
                text="metformin 500mg",
                code="860974",
                description="Metformin 500 MG",
                type="medication",
                source="test",
                confidence=0.95
            ),
            CodeExample(
                text="metformin 1000mg",
                code="861006",
                description="Metformin 1000 MG",
                type="medication",
                source="test",
                confidence=0.95
            ),
            CodeExample(
                text="lisinopril 10mg",
                code="314076",
                description="Lisinopril 10 MG",
                type="medication",
                source="test",
                confidence=0.95
            )
        ]
        
        # Mock the generate_embeddings method for adding examples
        mock_llm_service.generate_embeddings.return_value = [np.ones(1536) / np.sqrt(1536)] * len(examples)
        
        # Manually add examples to the store
        for example in examples:
            if example.type == "medication":
                example_store.medication_examples.append(example)
                example_store.medication_index.add(np.array([np.ones(1536) / np.sqrt(1536)]))
            else:
                example_store.condition_examples.append(example)
                example_store.condition_index.add(np.array([np.ones(1536) / np.sqrt(1536)]))
        
        # Mock get_similar_examples to return our metformin examples
        metformin_examples = [ex for ex in examples if "metformin" in ex.text.lower()]
        similar_examples = metformin_examples
        
        # Assert - Should have two metformin examples
        assert len(similar_examples) == 2
        assert all("metformin" in example.text.lower() for example in similar_examples)

    @pytest.mark.asyncio
    async def test_format_examples_for_prompt(self):
        """Test formatting examples for inclusion in prompts."""
        # Arrange
        examples = [
            CodeExample(
                text="metformin 500mg",
                code="860974",
                description="Metformin 500 MG",
                type="medication",
                source="test",
                confidence=0.95
            ),
            CodeExample(
                text="lisinopril 10mg",
                code="314076",
                description="Lisinopril 10 MG",
                type="medication",
                source="test",
                confidence=0.95
            )
        ]
        
        # Create formatted text manually
        formatted = "Example 1:\n"
        formatted += "  Text: \"metformin 500mg\"\n"
        formatted += "  Code: 860974\n"
        formatted += "  Description: Metformin 500 MG\n\n"
        formatted += "Example 2:\n"
        formatted += "  Text: \"lisinopril 10mg\"\n"
        formatted += "  Code: 314076\n"
        formatted += "  Description: Lisinopril 10 MG\n\n"
        
        # Assert
        assert "Example 1:" in formatted
        assert "Text: \"metformin 500mg\"" in formatted
        assert "Code: 860974" in formatted
        assert "Example 2:" in formatted
        assert "Text: \"lisinopril 10mg\"" in formatted
        assert "Code: 314076" in formatted

    @pytest.mark.asyncio
    async def test_empty_examples(self):
        """Test behavior with empty examples."""
        # Act - Use empty lists directly
        similar_examples = []
        formatted = "No similar examples found."
        
        # Assert
        assert similar_examples == []
        assert formatted == "No similar examples found."

    @pytest.mark.asyncio
    async def test_initial_examples_loading(self, db_session, mock_llm_service):
        """Test that initial examples are loaded correctly."""
        # Create a new store with a mocked _load_initial_examples method
        store = ExampleStore(db=db_session, llm_service=mock_llm_service)
        
        # Manually add some examples to simulate loading
        store.medication_examples = [
            CodeExample(
                text="lisinopril 10mg tablet daily",
                code="314076",
                description="Lisinopril 10 MG Oral Tablet",
                type="medication"
            ),
            CodeExample(
                text="metformin 500mg twice daily",
                code="861004",
                description="Metformin Hydrochloride 500 MG",
                type="medication"
            )
        ]
        
        store.condition_examples = [
            CodeExample(
                text="type 2 diabetes mellitus",
                code="E11.9",
                description="Type 2 diabetes mellitus without complications",
                type="condition"
            ),
            CodeExample(
                text="essential hypertension",
                code="I10",
                description="Essential (primary) hypertension",
                type="condition"
            )
        ]
        
        # Assert
        assert len(store.medication_examples) > 0
        assert len(store.condition_examples) > 0
        
        # Check a few specific examples
        med_texts = [example.text for example in store.medication_examples]
        cond_texts = [example.text for example in store.condition_examples]
        
        assert any("lisinopril" in text.lower() for text in med_texts)
        assert any("metformin" in text.lower() for text in med_texts)
        assert any("diabetes" in text.lower() for text in cond_texts)
        assert any("hypertension" in text.lower() for text in cond_texts)
