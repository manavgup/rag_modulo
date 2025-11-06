"""Unit tests for MilvusStore Pydantic model integration.

Tests the Pydantic-based implementation methods (_*_impl) to ensure
type safety, validation, and correct integration with Pydantic models.
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from backend.vectordbs.data_types import CollectionConfig, EmbeddedChunk, VectorDBResponse, VectorSearchRequest
from backend.vectordbs.error_types import CollectionError, DocumentError
from backend.vectordbs.milvus_store import MilvusStore
from core.config import Settings


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.embedding_dim = 768
    settings.embedding_field = "embedding"
    settings.milvus_host = "localhost"
    settings.milvus_port = 19530
    return settings


class ConcreteMilvusStore(MilvusStore):
    """Concrete implementation for testing that implements all abstract methods."""

    def _delete_collection_impl(self, collection_name: str) -> None:
        """Mock implementation for testing."""


@pytest.fixture
def milvus_store(mock_settings):
    """Create a MilvusStore instance with mocked connection."""
    with patch("backend.vectordbs.milvus_store.connections"):
        store = ConcreteMilvusStore(settings=mock_settings)
        return store


class TestCreateCollectionImpl:
    """Test _create_collection_impl with CollectionConfig."""

    def test_create_collection_impl_success(self, milvus_store):
        """Test successful collection creation with Pydantic config."""
        config = CollectionConfig(
            collection_name="test_collection",
            dimension=768,
            metric_type="COSINE",
            index_type="HNSW",
            description="Test collection",
        )

        with patch("backend.vectordbs.milvus_store.utility.list_collections", return_value=[]):
            with patch("backend.vectordbs.milvus_store.CollectionSchema"):
                with patch("backend.vectordbs.milvus_store.Collection") as mock_collection:
                    result = milvus_store._create_collection_impl(config)

                    assert result["status"] == "created"
                    assert result["collection_name"] == "test_collection"
                    assert result["dimension"] == 768
                    assert result["metric_type"] == "COSINE"
                    mock_collection.return_value.create_index.assert_called_once()

    def test_create_collection_impl_already_exists(self, milvus_store):
        """Test that existing collection returns appropriate status."""
        config = CollectionConfig(
            collection_name="existing_collection",
            dimension=768,
            metric_type="COSINE",
        )

        with patch("backend.vectordbs.milvus_store.utility.list_collections", return_value=["existing_collection"]):
            result = milvus_store._create_collection_impl(config)

            assert result["status"] == "exists"
            assert result["collection_name"] == "existing_collection"

    def test_create_collection_impl_dimension_mismatch(self, milvus_store):
        """Test that dimension mismatch raises CollectionError."""
        config = CollectionConfig(
            collection_name="test_collection",
            dimension=1536,  # Doesn't match settings.embedding_dim (768)
            metric_type="COSINE",
        )

        # The validation raises ValueError, but _create_collection_impl wraps it in CollectionError
        with pytest.raises(CollectionError, match="doesn't match embedding model dimension"):
            milvus_store._create_collection_impl(config)


class TestAddDocumentsImpl:
    """Test _add_documents_impl with EmbeddedChunk."""

    def test_add_documents_impl_with_valid_chunks(self, milvus_store):
        """Test successful document addition with EmbeddedChunk."""
        chunks = [
            EmbeddedChunk(
                chunk_id="chunk1",
                text="Test text 1",
                embeddings=[0.1] * 768,
                document_id="doc1",
                metadata=None,
            ),
            EmbeddedChunk(
                chunk_id="chunk2",
                text="Test text 2",
                embeddings=[0.2] * 768,
                document_id="doc1",
                metadata=None,
            ),
        ]

        with patch.object(milvus_store, "_get_collection") as mock_get_collection:
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection

            result = milvus_store._add_documents_impl("test_collection", chunks)

            assert len(result) == 2
            assert result == ["chunk1", "chunk2"]
            mock_collection.insert.assert_called_once()
            mock_collection.flush.assert_called_once()

    def test_embedded_chunk_validates_embeddings_required(self):
        """Test that EmbeddedChunk enforces embeddings are present."""
        # Should work with embeddings
        chunk = EmbeddedChunk(
            chunk_id="c1",
            text="test",
            embeddings=[0.1] * 768,
            document_id="doc1",
        )
        assert chunk.embeddings is not None
        assert len(chunk.embeddings) == 768

        # Should fail without embeddings
        with pytest.raises(ValidationError):
            EmbeddedChunk(
                chunk_id="c1",
                text="test",
                embeddings=None,  # type: ignore
                document_id="doc1",
            )


class TestSearchImpl:
    """Test _search_impl with VectorSearchRequest."""

    def test_search_impl_with_query_vector(self, milvus_store):
        """Test search with pre-computed query vector."""
        request = VectorSearchRequest(
            query_vector=[0.5] * 768,
            collection_id="test_collection",
            top_k=5,
        )

        with patch.object(milvus_store, "_get_collection") as mock_get_collection:
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection
            mock_collection.search.return_value = [[]]  # Empty results

            with patch.object(milvus_store, "_process_search_results", return_value=[]):
                result = milvus_store._search_impl(request)

                assert isinstance(result, list)
                mock_collection.search.assert_called_once()

    def test_search_impl_with_query_text(self, milvus_store):
        """Test search with query text (generates embeddings)."""
        request = VectorSearchRequest(
            query_text="What is machine learning?",
            collection_id="test_collection",
            top_k=10,
        )

        with patch.object(milvus_store, "_get_collection"):
            with patch("backend.vectordbs.milvus_store.get_embeddings_for_vector_store") as mock_embed:
                mock_embed.return_value = [[0.5] * 768]

                with patch.object(milvus_store, "_process_search_results", return_value=[]):
                    result = milvus_store._search_impl(request)

                    assert isinstance(result, list)
                    mock_embed.assert_called_once_with("What is machine learning?", settings=milvus_store.settings)

    def test_search_impl_missing_both_query_params(self, milvus_store):
        """Test that VectorSearchRequest validates query params at model creation."""
        # Pydantic validates in model_post_init, so the error happens at creation time
        with pytest.raises(ValidationError, match="Either query_text or query_vector must be provided"):
            VectorSearchRequest(
                collection_id="test_collection",
                top_k=10,
            )


class TestDeleteDocumentsWithResponse:
    """Test delete_documents_with_response returning VectorDBResponse."""

    def test_delete_documents_with_response_success(self, milvus_store):
        """Test successful deletion returns success response."""
        with patch.object(milvus_store, "_get_collection") as mock_get_collection:
            mock_collection = MagicMock()
            mock_get_collection.return_value = mock_collection

            response = milvus_store.delete_documents_with_response("test_collection", ["doc1", "doc2"])

            assert response.success is True
            assert response.data["deleted_count"] == 2
            assert response.data["collection_name"] == "test_collection"
            assert "elapsed_seconds" in response.metadata

    def test_delete_documents_with_response_error(self, milvus_store):
        """Test that deletion errors return error response."""
        with patch.object(milvus_store, "_get_collection", side_effect=CollectionError("Collection not found")):
            response = milvus_store.delete_documents_with_response("missing_collection", ["doc1"])

            assert response.success is False
            assert response.error is not None
            assert "Failed to delete documents" in response.error


class TestBackwardCompatibility:
    """Test that backward compatibility wrappers work correctly."""

    def test_create_collection_wrapper_calls_impl(self, milvus_store):
        """Test that create_collection wrapper converts to CollectionConfig."""
        with patch.object(milvus_store, "_create_collection_impl") as mock_impl:
            mock_impl.return_value = {"status": "created"}

            # Also mock Collection to prevent actual connection attempt
            with patch("backend.vectordbs.milvus_store.Collection") as mock_collection:
                mock_collection.return_value = MagicMock()

                milvus_store.create_collection("test_collection", metadata={"description": "Test"})

                # Verify it called _create_collection_impl with CollectionConfig
                mock_impl.assert_called_once()
                call_args = mock_impl.call_args[0][0]
                assert isinstance(call_args, CollectionConfig)
                assert call_args.collection_name == "test_collection"
                assert call_args.dimension == 768

    def test_delete_documents_wrapper_raises_on_error(self, milvus_store):
        """Test that delete_documents wrapper raises error on failure."""
        error_response = VectorDBResponse.create_error(error="Deletion failed")

        with patch.object(milvus_store, "delete_documents_with_response", return_value=error_response):
            with pytest.raises(DocumentError, match="Deletion failed"):
                milvus_store.delete_documents("test_collection", ["doc1"])
