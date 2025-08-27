"""Collection management fixtures for pytest."""

from uuid import uuid4
import pytest
from core.config import settings
from core.logging_utils import get_logger
from rag_solution.schemas.collection_schema import CollectionInput, CollectionStatus
from rag_solution.services.collection_service import CollectionService
from rag_solution.schemas.user_schema import UserOutput

logger = get_logger("tests.fixtures.collections")

@pytest.fixture(scope="session")
def base_collection(collection_service: CollectionService, base_user: UserOutput):
    """Create a base collection using service."""
    collection_input = CollectionInput(
        name="Test Collection",
        is_private=False,
        users=[base_user.id],
        status=CollectionStatus.COMPLETED
    )
    return collection_service.create_collection(collection_input)

@pytest.fixture(scope="session")
def base_suggested_question(question_service, base_collection):
    """Create a base suggested question using service."""
    question = f"Test Question {uuid4()}"
    return question_service.create_question({
        "collection_id": base_collection.id,
        "question": question,
        "is_valid": True
    })

@pytest.fixture(scope="session")
def vector_store():
    """Initialize vector store for testing."""
    from vectordbs.milvus_store import MilvusStore
    
    store = MilvusStore()
    store._connect(settings.milvus_host, settings.milvus_port)
    yield store

@pytest.fixture(scope="session")
def indexed_documents(vector_store, base_collection, base_file, get_watsonx):
    """Add documents to vector store and return collection name."""
    from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, Source

    # Create document from base_file
    text = "Sample text from the file."
    document = Document(
        document_id=base_file.document_id or str(uuid4()),
        name=base_file.filename,
        chunks=[
            DocumentChunk(
                chunk_id=f"chunk_{base_file.filename}",
                text=text,
                embeddings=get_watsonx.get_embeddings([text])[0],
                metadata=DocumentChunkMetadata(
                    source=Source.OTHER,
                    document_id=base_file.document_id or str(uuid4()),
                    page_number=1,
                    chunk_number=1,
                    start_index=0,
                    end_index=len(text)
                )
            )
        ]
    )

    # Set up vector store
    vector_store.delete_collection(base_collection.vector_db_name)
    vector_store.create_collection(base_collection.vector_db_name, {
        "embedding_model": settings.embedding_model
    })
    vector_store.add_documents(base_collection.vector_db_name, [document])

    yield base_collection.vector_db_name

    # Cleanup
    vector_store.delete_collection(base_collection.vector_db_name)