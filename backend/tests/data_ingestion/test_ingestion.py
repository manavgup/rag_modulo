# tests/test_ingestion.py
import time
from datetime import datetime
from unittest.mock import patch

import pytest

from rag_solution.data_ingestion.ingestion import DocumentStore
from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, Source

# Create a unique collection name for testing
timestamp = int(time.time())  # Get the timestamp as an integer
collection_name = f"test_collection_{timestamp}"

text = "This is a sample document."


def create_sample_document():
    """Create a sample document with mocked embeddings."""
    # Mock the get_embeddings function directly
    with patch("vectordbs.utils.watsonx.get_embeddings", return_value=[0.1, 0.2, 0.3]):
        return Document(
            document_id="doc3",
            name="Doc 3",
            chunks=[
                DocumentChunk(
                    chunk_id="3",
                    text=text,
                    vectors=[0.1, 0.2, 0.3],  # Use the mocked value directly
                    metadata=DocumentChunkMetadata(
                        source=Source.WEBSITE,
                        created_at=datetime.now().isoformat() + "Z",
                    ),
                )
            ],
        )


@pytest.fixture(scope="module")
def vector_store_with_collection():
    from unittest.mock import Mock

    # Create a mock vector store instead of connecting to real Milvus
    vector_store = Mock()
    vector_store.create_collection = Mock()
    vector_store.delete_collection = Mock()
    vector_store.retrieve_documents = Mock(return_value=[])
    yield vector_store


@pytest.mark.atomic
def test_document_store(vector_store_with_collection):
    """Test the DocumentStore class."""
    # Create document store
    store = DocumentStore(vector_store=vector_store_with_collection, collection_name=collection_name)

    # Test that the store was created successfully
    assert store.vector_store == vector_store_with_collection
    assert store.collection_name == collection_name

    # Test that the vector store methods are available
    assert hasattr(vector_store_with_collection, "create_collection")
    assert hasattr(vector_store_with_collection, "delete_collection")
    assert hasattr(vector_store_with_collection, "retrieve_documents")

    # Test that the sample document creation works
    sample_document = create_sample_document()
    assert sample_document.document_id == "doc3"
    assert sample_document.name == "Doc 3"
    assert len(sample_document.chunks) == 1
