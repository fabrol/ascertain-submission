from sqlalchemy.orm import Session
from ..models.document import Document
from ..schemas.document import DocumentCreate


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, document_id: int) -> Document | None:
        return self.db.query(Document).filter(Document.id == document_id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Document]:
        return self.db.query(Document).offset(skip).limit(limit).all()

    def create(self, document: DocumentCreate) -> Document:
        db_document = Document(title=document.title, content=document.content)
        self.db.add(db_document)
        self.db.commit()
        self.db.refresh(db_document)
        return db_document
