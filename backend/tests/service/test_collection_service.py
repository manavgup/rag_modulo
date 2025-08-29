"""Integration tests for CollectionService."""

import tempfile
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks, HTTPException, UploadFile
from sqlalchemy.orm import Session

from rag_solution.models.collection import Collection
from rag_solution.models.user import User
from rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput, CollectionStatus
from rag_solution.services.collection_service import CollectionService
from vectordbs.data_types import Document, DocumentChunk


@pytest.fixture
def test_file_content() -> str:
    """Create test file content."""
    return """
    The Python programming language was created by Guido van Rossum in 1991.
    Python is known for its simplicity and readability.
    Python supports multiple programming paradigms, including:
    - Procedural programming
    - Object-oriented programming
    - Functional programming
    """


@pytest.fixture
def test_file(test_file_content) -> str:
    """Create a temporary test file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(test_file_content)
        return f.name


@pytest.fixture
def upload_file(test_file) -> UploadFile:
    """Create an UploadFile instance for testing."""
    return UploadFile(filename="test.txt", file=open(test_file, "rb"))


@pytest.mark.atomic
def test_create_collection_success(db_session: Session, base_user: User):
    """Test successful collection creation."""
    collection_service = CollectionService(db_session)
    collection_input = CollectionInput(
        name="Test Collection", is_private=False, users=[base_user.id], status=CollectionStatus.CREATED
    )

    result = collection_service.create_collection(collection_input)

    assert isinstance(result, CollectionOutput)
    assert result.name == collection_input.name
    assert result.is_private == collection_input.is_private
    assert result.status == CollectionStatus.CREATED


@pytest.mark.atomic
def test_create_collection_duplicate_name(db_session: Session, base_user: User, base_collection: Collection):
    """Test creating collection with duplicate name."""
    collection_service = CollectionService(db_session)
    collection_input = CollectionInput(
        name=base_collection.name, is_private=False, users=[base_user.id], status=CollectionStatus.CREATED
    )

    with pytest.raises(HTTPException) as exc_info:
        collection_service.create_collection(collection_input)
    assert exc_info.value.status_code == 400
    assert "Collection name already exists" in str(exc_info.value.detail)


@pytest.mark.atomic
def test_get_collection_success(db_session: Session, base_collection: Collection):
    """Test successful collection retrieval."""
    collection_service = CollectionService(db_session)

    result = collection_service.get_collection(base_collection.id)

    assert isinstance(result, CollectionOutput)
    assert result.id == base_collection.id
    assert result.name == base_collection.name


@pytest.mark.atomic
def test_get_collection_not_found(db_session: Session):
    """Test collection retrieval when not found."""
    collection_service = CollectionService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        collection_service.get_collection(uuid4())
    assert exc_info.value.status_code == 404
    assert "Collection not found" in str(exc_info.value.detail)


@pytest.mark.atomic
def test_update_collection_success(db_session: Session, base_collection: Collection, base_user: User):
    """Test successful collection update."""
    collection_service = CollectionService(db_session)
    update_input = CollectionInput(
        name="Updated Collection", is_private=True, users=[base_user.id], status=CollectionStatus.COMPLETED
    )

    result = collection_service.update_collection(base_collection.id, update_input)

    assert isinstance(result, CollectionOutput)
    assert result.name == update_input.name
    assert result.is_private == update_input.is_private


@pytest.mark.atomic
def test_delete_collection_success(db_session: Session, base_collection: Collection):
    """Test successful collection deletion."""
    collection_service = CollectionService(db_session)

    result = collection_service.delete_collection(base_collection.id)

    assert result is True
    # Verify collection is deleted
    assert collection_service.collection_repository.get(base_collection.id) is None


@pytest.mark.atomic
def test_get_user_collections(db_session: Session, base_user: User, base_collection: Collection):
    """Test retrieving user collections."""
    collection_service = CollectionService(db_session)

    result = collection_service.get_user_collections(base_user.id)

    assert len(result) > 0
    assert any(c.id == base_collection.id for c in result)


@pytest.mark.atomic
@pytest.mark.asyncio
async def test_create_collection_with_documents(db_session: Session, base_user: User, upload_file: UploadFile):
    """Test creating collection with documents."""
    collection_service = CollectionService(db_session)
    background_tasks = BackgroundTasks()

    result = collection_service.create_collection_with_documents(
        collection_name="Test Collection",
        is_private=False,
        user_id=base_user.id,
        files=[upload_file],
        background_tasks=background_tasks,
    )

    assert isinstance(result, CollectionOutput)
    assert result.name == "Test Collection"
    assert result.status == CollectionStatus.CREATED

    # Clean up
    if upload_file.file:
        upload_file.file.close()


@pytest.mark.atomic
@pytest.mark.asyncio
async def test_process_documents(db_session: Session, base_collection: Collection, base_user: User, test_file: str):
    """Test document processing."""
    collection_service = CollectionService(db_session)

    await collection_service.process_documents(
        file_paths=[test_file],
        collection_id=base_collection.id,
        vector_db_name=base_collection.vector_db_name,
        document_ids=["test_doc"],
        user_id=base_user.id,
    )

    # Verify collection status is updated
    updated_collection = collection_service.get_collection(base_collection.id)
    assert updated_collection.status == CollectionStatus.COMPLETED


@pytest.mark.atomic
def test_update_collection_status(db_session: Session, base_collection: Collection):
    """Test collection status update."""
    collection_service = CollectionService(db_session)

    collection_service.update_collection_status(base_collection.id, CollectionStatus.PROCESSING)

    updated_collection = collection_service.get_collection(base_collection.id)
    assert updated_collection.status == CollectionStatus.PROCESSING


@pytest.mark.atomic
def test_generate_valid_collection_name(db_session: Session):
    """Test generation of valid collection names."""
    collection_service = CollectionService(db_session)

    name = collection_service._generate_valid_collection_name()

    assert name.startswith("collection_")
    assert name.replace("collection_", "").isalnum()
    assert len(name) > len("collection_")


def test_store_documents_success(db_session: Session, base_collection: Collection):
    """Test successful document storage."""
    collection_service = CollectionService(db_session)
    documents = [
        Document(
            document_id="test_doc", name="test.txt", chunks=[DocumentChunk(chunk_id="chunk1", text="test content")]
        )
    ]

    # This should not raise any exceptions
    collection_service.store_documents_in_vector_store(documents, base_collection.vector_db_name)


if __name__ == "__main__":
    pytest.main([__file__])
