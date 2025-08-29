"""Tests for Vector Database Components."""

from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from vectordbs.chroma_store import ChromaDBStore
from vectordbs.data_types import Document, DocumentChunk, DocumentChunkMetadata, QueryWithEmbedding, Source
from vectordbs.elasticsearch_store import ElasticSearchStore
from vectordbs.error_types import CollectionError
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
def mock_vectordb_session():
    """Create a mock database session with context manager support."""
    mock_session = Mock()
    mock_session.begin_nested.return_value.__enter__.return_value = mock_session
    mock_session.begin_nested.return_value.__exit__.return_value = None
    mock_session.commit.return_value = None
    mock_session.rollback.return_value = None
    return mock_session


class TestVectorStores:
    """Consolidated test class for all vector store implementations."""

    @pytest.fixture(params=STORE_CONFIGS.keys())
    def store_type(self, request):
        """Parametrized fixture that provides each store type."""
        return request.param

    @pytest.fixture
    def store(self, request, store_type, mock_vectordb_session):  # noqa: ARG002
        """Dynamic fixture that returns the appropriate store instance."""
        store_config = STORE_CONFIGS[store_type]

        # Apply the appropriate pytest mark
        request.node.add_marker(store_config["mark"])

        # Get store instance through the factory
        store_instance = get_datastore(store_type)
        return store_instance

    def create_test_documents(self):
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
                        vectors=get_embeddings(text),
                        metadata=DocumentChunkMetadata(
                            source=Source.WEBSITE,
                            created_at=datetime.now().isoformat() + "Z",
                        ),
                    )
                ],
            )
            for i, text in enumerate(texts)
        ]

    def test_store_creation(self, store):
        """Test that store is created with correct type."""
        store_type = store.__class__.__name__.lower().replace("store", "").replace("data", "")
        assert any(store_type in config_name for config_name in STORE_CONFIGS)

    def test_basic_operations(self, store):
        """Test basic CRUD operations for documents."""
        # Add documents
        doc1 = {"id": "doc1", "text": "This is the first document."}
        doc2 = {"id": "doc2", "text": "This is the second document."}
        store.add_documents([doc1, doc2])

        # Retrieve document
        retrieved_doc1 = store.get_document_by_id("doc1")
        assert retrieved_doc1 == doc1

        # Search documents
        results = store.search("document", 1)
        assert len(results) == 1
        assert results[0]["id"] in ["doc1", "doc2"]

        # Delete document
        store.delete_document_by_id("doc1")
        results = store.search("document", 2)
        assert len(results) == 1
        assert results[0]["id"] == "doc2"

    def test_error_handling(self, store):
        """Test error handling for non-existent documents."""
        with pytest.raises(ValueError):
            store.get_document_by_id("non-existent-id")

        with pytest.raises(ValueError):
            store.delete_document_by_id("non-existent-id")

    def test_vector_operations(self, store):
        """Test vector-specific operations."""
        documents = self.create_test_documents()

        # Test adding documents
        with store as s:
            result = s.add_documents(s.collection_name, documents)
            assert len(result) == 3

        # Test querying documents
        with store as s:
            embeddings = get_embeddings("Hello world")
            query_result = s.query(
                s.collection_name,
                QueryWithEmbedding(text="Hello world", vectors=embeddings),
            )
            assert query_result is not None
            assert len(query_result) > 0

    def test_collection_management(self, store):
        """Test collection management operations."""
        # Create collection
        store.create_collection("test_collection")
        assert store.collection_name == "test_collection"

        # Add documents
        documents = self.create_test_documents()
        store.add_documents("test_collection", documents)

        # Delete collection
        store.delete_collection("test_collection")
        with pytest.raises(CollectionError):
            store.retrieve_documents("test query", "test_collection")

    @patch("vectordbs.utils.watsonx.get_embeddings")
    def test_embedding_integration(self, mock_get_embeddings, store):
        """Test integration with embedding functionality."""
        mock_get_embeddings.return_value = [0.1, 0.2, 0.3]

        # Test adding and retrieving vector data
        test_text = "test text"
        embeddings = get_embeddings(test_text)
        vector_data = DocumentChunk(
            chunk_id=str(uuid4()), text=test_text, vectors=embeddings, metadata={"text": test_text}
        )

        with store as s:
            s.add_vector(vector_data)
            retrieved = s.get_vector(vector_data.chunk_id)
            assert retrieved == vector_data

    def test_retrieve_documents_with_parameters(self, store):
        """Test document retrieval with various parameters."""
        with store as s:
            documents = self.create_test_documents()
            s.add_documents(s.collection_name, documents)

            # Test with specific number of results
            query_results = s.retrieve_documents("Hello", s.collection_name, number_of_results=2)
            assert query_results is not None
            assert len(query_results) == 1  # One QueryResult object
            assert len(query_results[0].data) == 2  # With two documents


if __name__ == "__main__":
    pytest.main([__file__])
