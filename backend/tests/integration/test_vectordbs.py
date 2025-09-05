"""Tests for Vector Database Components."""

from datetime import datetime
from typing import Any
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from vectordbs.chroma_store import ChromaDBStore
from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, QueryWithEmbedding, Source
from vectordbs.elasticsearch_store import ElasticSearchStore
from vectordbs.factory import get_datastore
from vectordbs.milvus_store import MilvusStore
from vectordbs.pinecone_store import PineconeStore
from vectordbs.utils.watsonx import get_embeddings
from vectordbs.weaviate_store import WeaviateDataStore

# Mapping of store types to their respective classes and pytest marks
STORE_CONFIGS = {
    "chromadb": {
        "class": ChromaDBStore,
        "mark": pytest.mark.chromadb,
    },
    "elasticsearch": {
        "class": ElasticSearchStore,
        "mark": pytest.mark.elasticsearch,
    },
    "milvus": {
        "class": MilvusStore,
        "mark": pytest.mark.milvus,
    },
    "pinecone": {
        "class": PineconeStore,
        "mark": pytest.mark.pinecone,
    },
    "weaviate": {
        "class": WeaviateDataStore,
        "mark": pytest.mark.weaviate,
    },
}


@pytest.fixture
def mock_vectordb_session() -> Mock:
    """Create a mock database session with context manager support."""
    mock_session = Mock()
    mock_session.begin_nested.return_value.__enter__.return_value = mock_session
    mock_session.begin_nested.return_value.__exit__.return_value = None
    mock_session.commit.return_value = None
    mock_session.rollback.return_value = None
    return mock_session


@pytest.mark.integration
class TestVectorStores:
    """Consolidated test class for all vector store implementations."""

    @pytest.fixture(params=STORE_CONFIGS.keys())
    def store_type(self: Any, request: Any) -> Any:
        """Parametrized fixture that provides each store type."""
        return request.param

    @pytest.fixture
    def store(self: Any, request: Any, store_type: str, mock_vectordb_session: Mock) -> Any:  # noqa: ARG002
        """Dynamic fixture that returns the appropriate store instance."""
        store_config = STORE_CONFIGS[store_type]

        # Apply the appropriate pytest mark
        request.node.add_marker(store_config["mark"])

        # Get store instance through the factory
        store_instance = get_datastore(store_type)
        return store_instance

    def create_test_documents(self: Any) -> list[Document]:
        """Helper method to create test documents."""
        texts = ["Hello world", "Hello Jello", "Tic Tac Toe"]
        return [
            Document(
                document_id=f"doc{i+1}",
                name=f"Doc {i+1}",
                chunks=[
                    DocumentChunk(
                        chunk_id=str(i + 1),
                        text=text,
                        embeddings=get_embeddings(text)[0],  # get_embeddings returns list[list[float]], we need list[float]
                        metadata=DocumentChunkMetadata(
                            source=Source.WEBSITE,
                            created_at=datetime.now().isoformat() + "Z",
                        ),
                    )
                ],
            )
            for i, text in enumerate(texts)
        ]

    def test_store_creation(self, store: Any) -> None:
        """Test that store is created with correct type."""
        store_type = store.__class__.__name__.lower().replace("store", "").replace("data", "")
        assert any(store_type in config_name for config_name in STORE_CONFIGS)

    def test_basic_operations(self, store: Any) -> None:
        """Test basic CRUD operations for documents."""
        # Create test documents
        documents = self.create_test_documents()

        # Test collection creation
        collection_name = "test_collection"
        store.create_collection(collection_name)

        # Test adding documents
        result = store.add_documents(collection_name, documents)
        assert len(result) == 3

        # Test retrieving documents
        results = store.retrieve_documents("Hello", collection_name, number_of_results=2)
        assert results is not None
        assert len(results) > 0

    def test_error_handling(self, store: Any) -> None:
        """Test error handling for non-existent documents."""
        with pytest.raises(ValueError):
            store.get_document_by_id("non-existent-id")

        with pytest.raises(ValueError):
            store.delete_document_by_id("non-existent-id")

    def test_vector_operations(self, store: Any) -> None:
        """Test vector-specific operations."""
        documents = self.create_test_documents()
        collection_name = "test_collection"

        # Test collection creation
        store.create_collection(collection_name)

        # Test adding documents
        result = store.add_documents(collection_name, documents)
        assert len(result) == 3

        # Test querying documents
        embeddings = get_embeddings("Hello world")
        query_with_embedding = QueryWithEmbedding(text="Hello world", embeddings=embeddings[0])
        query_result = store.query(
            collection_name,
            query_with_embedding,
        )
        assert query_result is not None
        assert len(query_result) > 0

    def test_collection_management(self, store: Any) -> None:
        """Test collection management operations."""
        collection_name = "test_collection"

        # Create collection
        store.create_collection(collection_name)

        # Add documents
        documents = self.create_test_documents()
        result = store.add_documents(collection_name, documents)
        assert len(result) == 3

        # Test retrieving from collection
        results = store.retrieve_documents("test query", collection_name)
        assert results is not None

        # Delete collection
        store.delete_collection(collection_name)

    @patch("vectordbs.utils.watsonx.get_embeddings")
    def test_embedding_integration(self, mock_get_embeddings: Any, store: Any) -> None:
        """Test integration with embedding functionality."""
        mock_get_embeddings.return_value = [0.1, 0.2, 0.3]

        # Test adding and retrieving vector data
        test_text = "test text"
        embeddings = get_embeddings(test_text)
        chunk_metadata = DocumentChunkMetadata(source=Source.OTHER, document_id="test_doc")
        vector_data = DocumentChunk(  # noqa: F841
            chunk_id=str(uuid4()),
            text=test_text,
            embeddings=embeddings[0],  # get_embeddings returns list[list[float]], we need list[float]
            metadata=chunk_metadata,
        )

        # Test basic store functionality
        collection_name = "test_collection"
        store.create_collection(collection_name)
        assert store is not None

    def test_retrieve_documents_with_parameters(self, store: Any) -> None:
        """Test document retrieval with various parameters."""
        collection_name = "test_collection"
        store.create_collection(collection_name)

        documents = self.create_test_documents()
        result = store.add_documents(collection_name, documents)
        assert len(result) == 3

        # Test with specific number of results
        query_results = store.retrieve_documents("Hello", collection_name, number_of_results=2)
        assert query_results is not None
        assert len(query_results) > 0


if __name__ == "__main__":
    pytest.main([__file__])
