"""Collection management fixtures for pytest."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from core.config import settings
from core.logging_utils import get_logger
from rag_solution.generation.providers.base import LLMBase
from rag_solution.models.question import SuggestedQuestion
from rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput, CollectionStatus
from rag_solution.schemas.file_schema import FileOutput
from rag_solution.schemas.question_schema import QuestionInput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.question_service import QuestionService
from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, Source
from vectordbs.milvus_store import MilvusStore

logger = get_logger("tests.fixtures.collections")


@pytest.fixture(scope="session")
def base_collection(collection_service: CollectionService, base_user: UserOutput) -> CollectionOutput:
    """Create a base collection using service."""
    collection_input = CollectionInput(
        name="Test Collection",
        is_private=False,
        users=[base_user.id],
        status=CollectionStatus.COMPLETED,
    )
    return collection_service.create_collection(collection_input)


@pytest.fixture(scope="session")
def base_suggested_question(question_service: QuestionService, base_collection: CollectionOutput) -> SuggestedQuestion:
    """Create a base suggested question using service."""
    question_text = f"Test Question {uuid4()}?"
    question_input = QuestionInput(collection_id=base_collection.id, question=question_text, question_metadata={"is_valid": True})
    return question_service.create_question(question_input)


@pytest.fixture(scope="session")
def vector_store() -> MilvusStore:
    """Initialize vector store for testing."""
    store = MilvusStore()
    store._connect(settings.milvus_host, settings.milvus_port)
    yield store


@pytest.fixture(scope="session")
def indexed_documents(
    vector_store: MilvusStore,
    base_collection: CollectionOutput,
    base_file: FileOutput,
    get_watsonx: LLMBase,
) -> str:
    """Add documents to vector store and return collection name."""

    text = "Sample text from the file."

    mock_embeddings = [[0.1, 0.2, 0.3, 0.4, 0.5]]
    with patch.object(get_watsonx, "get_embeddings", return_value=mock_embeddings):
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
                        end_index=len(text),
                    ),
                )
            ],
        )

    vector_store.delete_collection(base_collection.vector_db_name)
    vector_store.create_collection(
        base_collection.vector_db_name,
        {"embedding_model": settings.embedding_model},
    )
    vector_store.add_documents(base_collection.vector_db_name, [document])

    yield base_collection.vector_db_name

    vector_store.delete_collection(base_collection.vector_db_name)
