from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import logging
from pydantic import BaseModel
from sqlalchemy.orm import Session
import faiss

from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class CodeExample(BaseModel):
    """A validated example of a medical code mapping."""
    text: str
    code: str
    description: str
    type: str  # "medication" or "condition"
    source: str = "manual"  # Where this example came from
    confidence: float = 1.0  # How confident we are in this mapping


class ExampleStore:
    """
    Stores and retrieves examples of medical code mappings using vector similarity.
    """

    def __init__(self, db: Optional[Session] = None, llm_service: Optional[LLMService] = None):
        """
        Initialize the example store.
        
        Args:
            db: Optional SQLAlchemy database session for persistence
            llm_service: Optional LLM service for generating embeddings
        """
        self.db = db
        self.llm_service = llm_service or LLMService(db=db)
        
        # OpenAI's text-embedding-3-small has 1536 dimensions
        self.embedding_dim = 1536
        
        # Initialize FAISS indexes for different example types
        self.medication_index = faiss.IndexFlatL2(self.embedding_dim)
        self.condition_index = faiss.IndexFlatL2(self.embedding_dim)
        
        # Storage for examples
        self.medication_examples: List[CodeExample] = []
        self.condition_examples: List[CodeExample] = []
        
        # We'll load initial examples when needed
        # Note: We can't await in __init__, so we'll initialize with empty examples
        # and load them when first needed

    async def _load_initial_examples(self) -> None:
        """Load initial examples from a predefined set or database."""
        # Add some common medication examples
        medication_examples = [
            CodeExample(
                text="lisinopril 10mg tablet daily",
                code="314076",
                description="Lisinopril 10 MG Oral Tablet",
                type="medication"
            ),
            CodeExample(
                text="metformin 500mg twice daily with meals",
                code="861004",
                description="Metformin Hydrochloride 500 MG",
                type="medication"
            ),
            CodeExample(
                text="atorvastatin 20mg daily at bedtime",
                code="617318",
                description="Atorvastatin 20 MG Oral Tablet",
                type="medication"
            ),
            CodeExample(
                text="amoxicillin 500mg capsule three times daily",
                code="308182",
                description="Amoxicillin 500 MG Oral Capsule",
                type="medication"
            ),
            # Add more examples as needed
        ]
        
        # Add some common condition examples
        condition_examples = [
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
            ),
            CodeExample(
                text="major depressive disorder",
                code="F32.9",
                description="Major depressive disorder, single episode, unspecified",
                type="condition"
            ),
            CodeExample(
                text="chronic obstructive pulmonary disease",
                code="J44.9",
                description="Chronic obstructive pulmonary disease, unspecified",
                type="condition"
            ),
            # Add more examples as needed
        ]
        
        # Generate all embeddings in a single batch for efficiency
        all_texts = [example.text for example in medication_examples + condition_examples]
        all_embeddings = await self.llm_service.generate_embeddings(all_texts)
        
        if len(all_embeddings) == len(all_texts):
            # Add medication examples
            for i, example in enumerate(medication_examples):
                embedding = all_embeddings[i]
                self.medication_index.add(np.array([embedding]))
                self.medication_examples.append(example)
                
            # Add condition examples
            for i, example in enumerate(condition_examples):
                embedding = all_embeddings[i + len(medication_examples)]
                self.condition_index.add(np.array([embedding]))
                self.condition_examples.append(example)
                
            logger.info(f"Loaded {len(medication_examples)} medication examples and {len(condition_examples)} condition examples")
        else:
            logger.error(f"Failed to generate embeddings for initial examples: expected {len(all_texts)}, got {len(all_embeddings)}")

    async def add_example(self, example: CodeExample) -> None:
        """
        Add a new example to the store.
        
        Args:
            example: The example to add
        """
        # Generate embedding for the example text
        embeddings = await self.llm_service.generate_embeddings([example.text])
        if not embeddings:
            logger.warning(f"Failed to generate embedding for example: {example.text}")
            return
            
        embedding = embeddings[0]
        
        # Add to the appropriate index and storage
        if example.type == "medication":
            self.medication_index.add(np.array([embedding]))
            self.medication_examples.append(example)
        elif example.type == "condition":
            self.condition_index.add(np.array([embedding]))
            self.condition_examples.append(example)
        else:
            logger.warning(f"Unknown example type: {example.type}")
            
        # TODO: If db is available, persist the example

    async def get_similar_examples(self, text: str, example_type: str, top_k: int = 3) -> List[CodeExample]:
        """
        Get similar examples for a given text.
        
        Args:
            text: The text to find similar examples for
            example_type: The type of examples to search ("medication" or "condition")
            top_k: The number of examples to return
            
        Returns:
            List of similar examples
        """
        # Load initial examples if needed
        if len(self.medication_examples) == 0 and len(self.condition_examples) == 0:
            await self._load_initial_examples()
        
        # Generate embedding for the query text
        embeddings = await self.llm_service.generate_embeddings([text])
        if not embeddings:
            logger.warning(f"Failed to generate embedding for query: {text}")
            return []
            
        query_embedding = embeddings[0]
        
        # Search the appropriate index
        if example_type == "medication":
            if len(self.medication_examples) == 0:
                return []
                
            D, I = self.medication_index.search(np.array([query_embedding]), min(top_k, len(self.medication_examples)))
            return [self.medication_examples[i] for i in I[0]]
            
        elif example_type == "condition":
            if len(self.condition_examples) == 0:
                return []
                
            D, I = self.condition_index.search(np.array([query_embedding]), min(top_k, len(self.condition_examples)))
            return [self.condition_examples[i] for i in I[0]]
            
        else:
            logger.warning(f"Unknown example type: {example_type}")
            return []
            
    async def format_examples_for_prompt(self, examples: List[CodeExample]) -> str:
        """
        Format examples for inclusion in an LLM prompt.
        
        Args:
            examples: The examples to format
            
        Returns:
            Formatted string of examples
        """
        if not examples:
            return "No similar examples found."
            
        formatted = []
        for i, example in enumerate(examples):
            formatted.append(f"Example {i+1}:")
            formatted.append(f"  Text: \"{example.text}\"")
            formatted.append(f"  Code: {example.code}")
            formatted.append(f"  Description: {example.description}")
            formatted.append("")
            
        return "\n".join(formatted)
