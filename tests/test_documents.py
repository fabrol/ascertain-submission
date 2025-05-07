import pytest
from src.models.document import Document
from src.schemas.document import DocumentCreate
from src.config import settings
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

pytestmark = pytest.mark.usefixtures("setup_test_database")


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_document(client, db_session):
    # Test successful creation
    document_data = {
        "title": "Test Document",
        "content": "This is a test document",
    }
    response = client.post("/documents/", json=document_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == document_data["title"]
    assert data["content"] == document_data["content"]
    assert "id" in data

    # Verify document was created in database
    db_document = db_session.query(Document).filter(Document.id == data["id"]).first()
    assert db_document is not None
    assert db_document.title == document_data["title"]
    assert db_document.content == document_data["content"]


def test_create_document_validation(client):
    # Test missing required fields
    response = client.post("/documents/", json={})
    assert response.status_code == 422

    # Test missing title
    response = client.post("/documents/", json={"content": "Test"})
    assert response.status_code == 422

    # Test missing content
    response = client.post("/documents/", json={"title": "Test"})
    assert response.status_code == 422


def test_read_documents(client, db_session):
    # Create test documents
    documents = [
        Document(title="Test Document 1", content="Content 1"),
        Document(title="Test Document 2", content="Content 2"),
    ]
    for doc in documents:
        db_session.add(doc)
    db_session.commit()

    # Test without pagination
    response = client.get("/documents/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2  # Could be more if other tests created documents
    titles = [doc["title"] for doc in data]
    assert "Test Document 1" in titles
    assert "Test Document 2" in titles

    # Test with pagination
    response = client.get("/documents/?skip=1&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


def test_read_single_document(client, db_session):
    # Create test document
    document = Document(title="Test Document", content="Test Content")
    db_session.add(document)
    db_session.commit()

    response = client.get(f"/documents/{document.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == document.id
    assert data["title"] == document.title
    assert data["content"] == document.content


def test_read_nonexistent_document(client):
    response = client.get("/documents/999999")
    assert response.status_code == 404


def test_database_error_handling(client, db_session):
    # Create a document
    document_data = {
        "title": "Test Document",
        "content": "This is a test document",
    }
    response = client.post("/documents/", json=document_data)
    assert response.status_code == 200
    first_doc_id = response.json()["id"]

    # Create another document with the same title (should be allowed)
    response = client.post("/documents/", json=document_data)
    assert response.status_code == 200
    second_doc_id = response.json()["id"]

    # Verify both documents exist and have different IDs
    assert first_doc_id != second_doc_id
    first_doc = db_session.query(Document).filter(Document.id == first_doc_id).first()
    second_doc = db_session.query(Document).filter(Document.id == second_doc_id).first()
    assert first_doc is not None
    assert second_doc is not None
    assert first_doc.title == second_doc.title
