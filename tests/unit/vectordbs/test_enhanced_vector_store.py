"""Unit tests for enhanced VectorStore abstract base class (Issue #212)."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from backend.vectordbs.data_types import (
    CollectionConfig,
    Document,
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentIngestionRequest,
    EmbeddedChunk,
    QueryResult,
    Source,
    VectorDBResponse,
    VectorSearchRequest,
)
from backend.vectordbs.error_types import CollectionError
from backend.vectordbs.vector_store import VectorStore
from core.config import Settings


class MockVectorStore(VectorStore):
    """Mock implementation of VectorStore for testing."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self.collections: dict[str, dict[str, Any]] = {}
        self.documents: dict[str, list[EmbeddedChunk]] = {}

    def _health_check_impl(self, timeout: float) -> dict[str, Any]:
        """Mock health check implementation."""
        return {"status": "healthy", "connected": self._connected}

    def _get_collection_stats_impl(self, collection_name: str) -> dict[str, Any]:
        """Mock collection stats implementation."""
        if collection_name not in self.collections:
            raise CollectionError(f"Collection {collection_name} not found")
        return {"name": collection_name, "document_count": len(self.documents.get(collection_name, []))}

    def _create_collection_impl(self, config: CollectionConfig) -> dict[str, Any]:
        """Mock collection creation implementation."""
        self.collections[config.name] = {"config": config}
        self.documents[config.name] = []
        return {"name": config.name, "created": True}

    def _add_documents_impl(self, collection_name: str, chunks: list[EmbeddedChunk]) -> list[str]:
        """Mock document addition implementation."""
        if collection_name not in self.collections:
            raise CollectionError(f"Collection {collection_name} not found")
        self.documents[collection_name].extend(chunks)
        return [chunk.chunk_id for chunk in chunks]

    def _search_impl(self, request: VectorSearchRequest) -> list[QueryResult]:
        """Mock search implementation."""
        # Return empty results for simplicity
        return []

    def _delete_collection_impl(self, collection_name: str) -> None:
        """Mock collection deletion implementation."""
        if collection_name not in self.collections:
            raise CollectionError(f"Collection {collection_name} not found")
        del self.collections[collection_name]
        del self.documents[collection_name]

    # Backward compatibility methods (required by abstract base class)
    def create_collection(self, collection_name: str, metadata: dict | None = None) -> None:
        """Legacy create collection method."""
        config = CollectionConfig(name=collection_name, dimension=self.settings.embedding_dim, metadata_schema=metadata)
        self._create_collection_impl(config)

    def add_documents(self, collection_name: str, documents: list[Document]) -> list[str]:
        """Legacy add documents method."""
        chunks = []
        for doc in documents:
            for chunk in doc.chunks:
                if chunk.embeddings and chunk.chunk_id:
                    chunks.append(EmbeddedChunk.from_chunk(chunk))
        return self._add_documents_impl(collection_name, chunks)

    def retrieve_documents(self, query: str, collection_name: str, number_of_results: int = 10) -> list[QueryResult]:
        """Legacy retrieve documents method."""
        request = VectorSearchRequest(collection_name=collection_name, query=query, number_of_results=number_of_results)
        return self._search_impl(request)

    def query(
        self, collection_name: str, query: Any, number_of_results: int = 10, filter: Any = None
    ) -> list[QueryResult]:
        """Legacy query method."""
        request = VectorSearchRequest(
            collection_name=collection_name, query=query, number_of_results=number_of_results, metadata_filter=filter
        )
        return self._search_impl(request)

    def delete_collection(self, collection_name: str) -> None:
        """Legacy delete collection method."""
        self._delete_collection_impl(collection_name)

    def delete_documents(self, collection_name: str, document_ids: list[str]) -> None:
        """Legacy delete documents method."""
        pass

    def count_document_chunks(self, collection_name: str, document_id: str) -> int:
        """Legacy count document chunks method."""
        return 0


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(embedding_dim=768)


@pytest.fixture
def vector_store(settings):
    """Create mock vector store for testing."""
    return MockVectorStore(settings)


class TestConnectionManagement:
    """Test connection management features."""

    def test_initial_connection_state(self, vector_store):
        """Test that vector store starts disconnected."""
        assert not vector_store.is_connected

    def test_connect(self, vector_store):
        """Test connecting to vector store."""
        vector_store.connect()
        assert vector_store.is_connected
        assert "connected_at" in vector_store._connection_metadata

    def test_disconnect(self, vector_store):
        """Test disconnecting from vector store."""
        vector_store.connect()
        vector_store.disconnect()
        assert not vector_store.is_connected
        assert "disconnected_at" in vector_store._connection_metadata

    def test_connection_context(self, vector_store):
        """Test connection context manager."""
        assert not vector_store.is_connected

        with vector_store.connection_context():
            assert vector_store.is_connected

        assert not vector_store.is_connected

    @pytest.mark.asyncio
    async def test_async_connection_context(self, vector_store):
        """Test async connection context manager."""
        assert not vector_store.is_connected

        async with vector_store.async_connection_context():
            assert vector_store.is_connected

        assert not vector_store.is_connected


class TestHealthCheckAndStats:
    """Test health check and statistics features."""

    def test_health_check_success(self, vector_store):
        """Test successful health check."""
        response = vector_store.health_check()
        assert response.success is True
        assert response.data["status"] == "healthy"
        assert "elapsed_seconds" in response.metadata

    def test_health_check_with_timeout(self, vector_store):
        """Test health check with custom timeout."""
        response = vector_store.health_check(timeout=10.0)
        assert response.success is True

    def test_get_collection_stats_success(self, vector_store):
        """Test getting collection statistics."""
        # Create collection first
        config = CollectionConfig(name="test_collection", dimension=768)
        vector_store.create_collection(config.name)

        response = vector_store.get_collection_stats("test_collection")
        assert response.success is True
        assert response.data["name"] == "test_collection"

    def test_get_collection_stats_not_found(self, vector_store):
        """Test getting stats for non-existent collection."""
        response = vector_store.get_collection_stats("nonexistent")
        assert response.success is False
        assert "not found" in response.error.lower()


class TestCommonUtilities:
    """Test common utility methods."""

    def test_collection_exists_true(self, vector_store):
        """Test checking if collection exists."""
        config = CollectionConfig(name="test_collection", dimension=768)
        vector_store.create_collection(config.name)

        assert vector_store._collection_exists("test_collection")

    def test_collection_exists_false(self, vector_store):
        """Test checking if collection doesn't exist."""
        assert not vector_store._collection_exists("nonexistent")

    def test_batch_chunks(self, vector_store):
        """Test batching chunks."""
        chunks = [EmbeddedChunk(chunk_id=f"chunk_{i}", text=f"Text {i}", embeddings=[0.1, 0.2, 0.3]) for i in range(10)]

        batches = vector_store._batch_chunks(chunks, batch_size=3)
        assert len(batches) == 4
        assert len(batches[0]) == 3
        assert len(batches[1]) == 3
        assert len(batches[2]) == 3
        assert len(batches[3]) == 1

    def test_batch_chunks_invalid_size(self, vector_store):
        """Test batching with invalid batch size."""
        chunks = [EmbeddedChunk(chunk_id="chunk_1", text="Text", embeddings=[0.1, 0.2, 0.3])]

        with pytest.raises(ValueError, match="Batch size must be positive"):
            vector_store._batch_chunks(chunks, batch_size=0)

    def test_validate_collection_config(self, vector_store, settings):
        """Test collection config validation."""
        config = CollectionConfig(name="test_collection", dimension=768)
        # Should not raise
        vector_store._validate_collection_config(config)

    def test_validate_collection_config_dimension_mismatch(self, vector_store, caplog):
        """Test warning when dimensions don't match."""
        config = CollectionConfig(name="test_collection", dimension=1024)
        vector_store._validate_collection_config(config)
        assert "doesn't match" in caplog.text


class TestEnhancedInternalMethods:
    """Test enhanced internal methods with pydantic integration."""

    def test_create_collection_impl(self, vector_store):
        """Test internal collection creation with CollectionConfig."""
        config = CollectionConfig(name="test_collection", dimension=768)
        result = vector_store._create_collection_impl(config)

        assert result["created"] is True
        assert vector_store._collection_exists("test_collection")

    def test_add_documents_impl(self, vector_store):
        """Test internal document addition with EmbeddedChunk."""
        # Create collection first
        vector_store.create_collection("test_collection")

        # Create embedded chunks
        chunks = [
            EmbeddedChunk(chunk_id="chunk_1", text="Test text 1", embeddings=[0.1, 0.2, 0.3]),
            EmbeddedChunk(chunk_id="chunk_2", text="Test text 2", embeddings=[0.4, 0.5, 0.6]),
        ]

        document_ids = vector_store._add_documents_impl("test_collection", chunks)
        assert len(document_ids) == 2
        assert document_ids == ["chunk_1", "chunk_2"]

    def test_search_impl(self, vector_store):
        """Test internal search with VectorSearchRequest."""
        # Create collection first
        vector_store.create_collection("test_collection")

        request = VectorSearchRequest(collection_name="test_collection", query="test query", number_of_results=5)
        results = vector_store._search_impl(request)

        assert isinstance(results, list)

    def test_delete_collection_impl(self, vector_store):
        """Test internal collection deletion."""
        # Create collection first
        vector_store.create_collection("test_collection")

        vector_store._delete_collection_impl("test_collection")
        assert not vector_store._collection_exists("test_collection")


class TestBackwardCompatibility:
    """Test backward compatibility with legacy methods."""

    def test_legacy_create_collection(self, vector_store):
        """Test legacy create_collection method."""
        vector_store.create_collection("test_collection")
        assert vector_store._collection_exists("test_collection")

    def test_legacy_add_documents(self, vector_store):
        """Test legacy add_documents method."""
        vector_store.create_collection("test_collection")

        chunk = DocumentChunk(
            chunk_id="chunk_1",
            text="Test text",
            embeddings=[0.1, 0.2, 0.3],
        )
        doc = Document(document_id="doc_1", name="test.pdf", chunks=[chunk])

        document_ids = vector_store.add_documents("test_collection", [doc])
        assert len(document_ids) == 1

    def test_legacy_retrieve_documents(self, vector_store):
        """Test legacy retrieve_documents method."""
        vector_store.create_collection("test_collection")
        results = vector_store.retrieve_documents("test query", "test_collection")
        assert isinstance(results, list)

    def test_legacy_delete_collection(self, vector_store):
        """Test legacy delete_collection method."""
        vector_store.create_collection("test_collection")
        vector_store.delete_collection("test_collection")
        assert not vector_store._collection_exists("test_collection")
