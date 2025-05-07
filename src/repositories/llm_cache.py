from sqlalchemy.orm import Session
from ..models.llm_cache import LLMCache
from ..schemas.llm_cache import LLMCacheCreate
import hashlib


class LLMCacheRepository:
    def __init__(self, db: Session):
        self.db = db

    def _hash_note(self, note_text: str) -> str:
        """Generate a SHA-256 hash of the note text."""
        return hashlib.sha256(note_text.encode()).hexdigest()

    def get(self, note_text: str) -> LLMCache | None:
        """Get cached response for a note."""
        note_hash = self._hash_note(note_text)
        return self.db.query(LLMCache).filter(LLMCache.note_hash == note_hash).first()

    def create(self, note_text: str, response: LLMCacheCreate) -> LLMCache:
        """Create a new cache entry."""
        note_hash = self._hash_note(note_text)
        db_cache = LLMCache(
            note_hash=note_hash,
            content=response.content,
            version=response.version,
        )
        self.db.add(db_cache)
        self.db.commit()
        self.db.refresh(db_cache)
        return db_cache

    def delete(self, cache_id: int) -> None:
        """Delete a cache entry by ID."""
        self.db.query(LLMCache).filter(LLMCache.id == cache_id).delete()
        self.db.commit()
