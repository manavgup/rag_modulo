"""Unit tests for VectorStore base class functionality.

Tests the abstract base class utilities, connection management, and default implementations
without requiring concrete vector database implementations.
"""

from unittest.mock import MagicMock

import pytest

from backend.vectordbs.data_types import (
    CollectionConfig,
    Document,
    DocumentMetadataFilter,
    EmbeddedChunk,
    QueryResult,
    QueryWithEmbedding,
)
from backend.vectordbs.error_types import CollectionError, VectorStoreError
from backend.vectordbs.vector_store import VectorStore
from core.config import Settings


class MockVectorStore(VectorStore):
    """Mock implementation for testing base class functionality."""

    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.collections: dict[str, dict] = {}

    def _get_collection_stats_impl(self, collection_name: str) -> dict:
        """Mock implementation that returns stats for test collections."""
        if collection_name not in self.collections:
            raise CollectionError(f"Collection '{collection_name}' not found")
        return self.collections[collection_name]

    # Implement required abstract implementation methods
    def _create_collection_impl(self, config: CollectionConfig) -> dict:
        """Mock collection creation implementation."""
        return {"status": "created"}

    def _add_documents_impl(self, collection_name: str, chunks: list[EmbeddedChunk]) -> list[str]:
        """Mock document addition implementation."""
        return [f"chunk_{i}" for i in range(len(chunks))]

    def _search_impl(self, request) -> list[QueryResult]:
        """Mock search implementation."""
        return []

    def _delete_collection_impl(self, collection_name: str) -> None:
        """Mock collection deletion implementation."""
        if collection_name in self.collections:
            del self.collections[collection_name]

    # Implement required abstract methods with minimal functionality
    def create_collection(self, collection_name: str, metadata: dict | None = None) -> None:
        """Mock collection creation."""
        self.collections[collection_name] = {"count": 0, "dimension": 768}

    def add_documents(self, collection_name: str, documents: list[Document]) -> list[str]:
        """Mock document addition."""
        return [f"doc_{i}" for i in range(len(documents))]

    def retrieve_documents(self, query: str, collection_name: str, number_of_results: int = 10) -> list[QueryResult]:
        """Mock document retrieval."""
        return []

    def query(
        self,
        collection_name: str,
        query: QueryWithEmbedding,
        number_of_results: int = 10,
        filter: DocumentMetadataFilter | None = None,
    ) -> list[QueryResult]:
        """Mock query."""
        return []

    def delete_collection(self, collection_name: str) -> None:
        """Mock collection deletion."""
        if collection_name in self.collections:
            del self.collections[collection_name]

    def delete_documents(self, collection_name: str, document_ids: list[str]) -> None:
        """Mock document deletion."""

    def count_document_chunks(self, collection_name: str, document_id: str) -> int:
        """Mock chunk counting."""
        return 0


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.embedding_dim = 768
    return settings


@pytest.fixture
def vector_store(mock_settings):
    """Create a mock vector store instance."""
    return MockVectorStore(mock_settings)


class TestConnectionManagement:
    """Test connection lifecycle management."""

    def test_initial_state_disconnected(self, vector_store):
        """Test that vector store starts disconnected."""
        assert not vector_store.is_connected

    def test_connect_sets_flag(self, vector_store):
        """Test that connect() sets the connection flag."""
        vector_store.connect()
        assert vector_store.is_connected

    def test_disconnect_clears_flag(self, vector_store):
        """Test that disconnect() clears the connection flag."""
        vector_store.connect()
        vector_store.disconnect()
        assert not vector_store.is_connected

    def test_connection_context_without_existing_connection(self, vector_store):
        """Test context manager connects and disconnects when no connection exists."""
        assert not vector_store.is_connected

        with vector_store.connection_context():
            assert vector_store.is_connected

        # Should disconnect after context exit
        assert not vector_store.is_connected

    def test_connection_context_with_existing_connection(self, vector_store):
        """Test context manager preserves existing connections."""
        # Manually connect before using context manager
        vector_store.connect()
        assert vector_store.is_connected

        with vector_store.connection_context():
            assert vector_store.is_connected

        # Should NOT disconnect after context exit (we didn't create it)
        assert vector_store.is_connected

    def test_connection_metadata_tracking(self, vector_store):
        """Test that connection metadata is tracked."""
        vector_store.connect()
        assert "connected_at" in vector_store._connection_metadata

        vector_store.disconnect()
        assert "disconnected_at" in vector_store._connection_metadata


class TestHealthCheck:
    """Test health check functionality."""

    def test_health_check_default_success(self, vector_store):
        """Test default health check returns success."""
        response = vector_store.health_check()

        assert response.success is True
        assert response.data is not None
        assert "status" in response.data
        assert "connected" in response.data
        assert "store_type" in response.data

    def test_health_check_includes_metadata(self, vector_store):
        """Test health check response includes metadata."""
        response = vector_store.health_check(timeout=10.0)

        assert "elapsed_seconds" in response.metadata
        assert response.metadata["timeout"] == 10.0

    def test_health_check_when_connected(self, vector_store):
        """Test health check reports connection status correctly."""
        vector_store.connect()
        response = vector_store.health_check()

        assert response.success is True
        assert response.data["connected"] is True
        assert response.data["status"] == "healthy"

    def test_health_check_when_disconnected(self, vector_store):
        """Test health check reports disconnected status."""
        response = vector_store.health_check()

        assert response.success is True
        assert response.data["connected"] is False
        assert response.data["status"] == "unknown"


class TestCollectionStats:
    """Test collection statistics functionality."""

    def test_get_stats_for_existing_collection(self, vector_store):
        """Test getting stats for an existing collection."""
        # Create a test collection
        vector_store.create_collection("test_collection")

        response = vector_store.get_collection_stats("test_collection")

        assert response.success is True
        assert response.data is not None
        assert "count" in response.data
        assert "dimension" in response.data

    def test_get_stats_for_missing_collection(self, vector_store):
        """Test getting stats for non-existent collection returns error."""
        response = vector_store.get_collection_stats("nonexistent")

        assert response.success is False
        assert response.error is not None
        assert response.metadata["error_type"] == "CollectionError"

    def test_get_stats_includes_collection_name_in_metadata(self, vector_store):
        """Test that collection name is included in response metadata."""
        vector_store.create_collection("test_collection")
        response = vector_store.get_collection_stats("test_collection")

        assert response.metadata["collection_name"] == "test_collection"


class TestCollectionExistence:
    """Test _collection_exists utility method."""

    def test_collection_exists_true(self, vector_store):
        """Test that _collection_exists returns True for existing collections."""
        vector_store.create_collection("test_collection")

        assert vector_store._collection_exists("test_collection") is True

    def test_collection_exists_false(self, vector_store):
        """Test that _collection_exists returns False for missing collections."""
        assert vector_store._collection_exists("nonexistent") is False

    def test_collection_exists_raises_on_unexpected_error(self, vector_store):
        """Test that unexpected errors are re-raised as VectorStoreError."""

        # Mock _get_collection_stats_impl to raise an unexpected error
        def raise_unexpected():
            raise RuntimeError("Database connection lost")

        vector_store._get_collection_stats_impl = lambda _: raise_unexpected()  # noqa: ARG005

        with pytest.raises(VectorStoreError, match="Failed to check collection existence"):
            vector_store._collection_exists("test_collection")


class TestBatchChunks:
    """Test _batch_chunks utility method."""

    def test_batch_chunks_valid_batch_size(self, vector_store):
        """Test batching with valid batch size."""
        # Create mock chunks
        chunks = [MagicMock(spec=EmbeddedChunk) for _ in range(25)]

        batches = vector_store._batch_chunks(chunks, batch_size=10)

        assert len(batches) == 3  # 25 chunks / 10 per batch = 3 batches
        assert len(batches[0]) == 10
        assert len(batches[1]) == 10
        assert len(batches[2]) == 5  # Partial last batch

    def test_batch_chunks_exact_division(self, vector_store):
        """Test batching when total divides evenly."""
        chunks = [MagicMock(spec=EmbeddedChunk) for _ in range(30)]

        batches = vector_store._batch_chunks(chunks, batch_size=10)

        assert len(batches) == 3
        assert all(len(batch) == 10 for batch in batches)

    def test_batch_chunks_single_batch(self, vector_store):
        """Test batching when all chunks fit in one batch."""
        chunks = [MagicMock(spec=EmbeddedChunk) for _ in range(5)]

        batches = vector_store._batch_chunks(chunks, batch_size=10)

        assert len(batches) == 1
        assert len(batches[0]) == 5

    def test_batch_chunks_empty_list(self, vector_store):
        """Test batching with empty chunk list."""
        batches = vector_store._batch_chunks([], batch_size=10)

        assert len(batches) == 0

    def test_batch_chunks_invalid_batch_size(self, vector_store):
        """Test that invalid batch sizes raise ValueError."""
        chunks = [MagicMock(spec=EmbeddedChunk) for _ in range(10)]

        with pytest.raises(ValueError, match="Batch size must be positive"):
            vector_store._batch_chunks(chunks, batch_size=0)

        with pytest.raises(ValueError, match="Batch size must be positive"):
            vector_store._batch_chunks(chunks, batch_size=-5)


class TestCollectionConfigValidation:
    """Test _validate_collection_config utility method."""

    def test_validate_matching_dimensions(self, vector_store):
        """Test validation passes when dimensions match."""
        config = CollectionConfig(
            collection_name="test_collection",
            dimension=768,  # Matches mock_settings.embedding_dim
            metric="cosine",
        )

        # Should not raise
        vector_store._validate_collection_config(config)

    def test_validate_mismatched_dimensions_raises_error(self, vector_store):
        """Test that dimension mismatch raises ValueError."""
        config = CollectionConfig(
            collection_name="test_collection",
            dimension=1536,  # Does NOT match mock_settings.embedding_dim (768)
            metric="cosine",
        )

        with pytest.raises(ValueError, match="doesn't match embedding model dimension"):
            vector_store._validate_collection_config(config)

    def test_validate_error_message_includes_details(self, vector_store):
        """Test that validation error includes collection name and dimensions."""
        config = CollectionConfig(collection_name="my_collection", dimension=1536, metric="cosine")

        with pytest.raises(ValueError) as exc_info:
            vector_store._validate_collection_config(config)

        error_message = str(exc_info.value)
        assert "1536" in error_message  # Collection dimension
        assert "768" in error_message  # Expected dimension
        assert "my_collection" in error_message
