from typing import Optional, Any, Dict, List
from openai import AsyncOpenAI
from pydantic import BaseModel
from textwrap import dedent
from sqlalchemy.orm import Session
import numpy as np
import logging

from src.config import settings
from src.repositories.llm_cache import LLMCacheRepository
from src.schemas.llm_cache import LLMCacheCreate

logger = logging.getLogger(__name__)


class LLMResponse(BaseModel):
    """Generic LLM response that can be extended for specific use cases."""

    content: Any
    error: Optional[str] = None


class LLMService:
    """Generic LLM service that handles caching and different types of prompts."""

    # Current schema version - increment this when the response structure changes
    CURRENT_VERSION = "1.0.0"
    
    # Default embedding model
    EMBEDDING_MODEL = "text-embedding-3-small"

    def __init__(self, db: Session | None = None):
        if not settings.is_openai_configured():
            raise ValueError(
                "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
            )

        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.cache_repo = LLMCacheRepository(db) if db else None

    async def process_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        response_format: Optional[Dict] = None,
        temperature: float = 0.3,
        cache_key: Optional[str] = None,
    ) -> LLMResponse:
        """Process a prompt with optional caching.

        Args:
            system_prompt: The system prompt to use
            user_prompt: The user prompt to use
            model: The model to use
            response_format: Optional format for the response (e.g., {"type": "json_object"})
            temperature: Temperature for the response (default: 0.3)
            cache_key: Optional key to use for caching. If not provided, the user_prompt is used.

        Returns:
            LLMResponse with the processed content
        """
        if not user_prompt or not user_prompt.strip():
            return LLMResponse(content=None, error="Prompt text cannot be empty.")

        # Use user_prompt as cache key if none provided
        cache_key = cache_key or user_prompt

        # Check cache if available
        if self.cache_repo:
            cached_response = self.cache_repo.get(cache_key)
            if cached_response:
                # Only use cache if the version matches
                if cached_response.version == self.CURRENT_VERSION:
                    return LLMResponse(content=cached_response.content)

                # If version mismatch, delete the old cache entry
                self.cache_repo.delete(cached_response.id)

        try:
            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Prepare completion parameters
            completion_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }

            # Add response format if provided
            if response_format:
                completion_params["response_format"] = response_format

            # Get response from OpenAI
            response = await self.client.chat.completions.create(**completion_params)
            content = response.choices[0].message.content

            # Cache the response if we have a database connection
            if self.cache_repo:
                note_hash = self.cache_repo._hash_note(cache_key)
                cache_entry = LLMCacheCreate(
                    note_hash=note_hash,
                    content=content,
                    version=self.CURRENT_VERSION,
                )
                self.cache_repo.create(cache_key, cache_entry)

            return LLMResponse(content=content)

        except Exception as e:
            return LLMResponse(content=None, error=str(e))
            
    async def generate_embeddings(
        self, 
        texts: List[str], 
        model: str = None
    ) -> List[np.ndarray]:
        """Generate embeddings for a list of texts using OpenAI's embedding API.
        
        Args:
            texts: List of texts to generate embeddings for
            model: Optional embedding model to use (defaults to text-embedding-3-small)
            
        Returns:
            List of numpy arrays containing the embeddings
        """
        if not texts:
            return []
            
        try:
            # Use default model if none provided
            embedding_model = model or self.EMBEDDING_MODEL
            
            # Call OpenAI embeddings API
            response = await self.client.embeddings.create(
                model=embedding_model,
                input=texts,
            )
            
            # Extract embeddings and convert to numpy arrays
            embeddings = [np.array(data.embedding, dtype=np.float32) for data in response.data]
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            # Return empty embeddings in case of error
            return [np.zeros(1536, dtype=np.float32) for _ in texts]
