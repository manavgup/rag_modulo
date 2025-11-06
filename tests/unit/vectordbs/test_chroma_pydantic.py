"""Unit tests for ChromaDBStore Pydantic model integration.

Tests the Pydantic-based implementation methods (_*_impl) to ensure
type safety, validation, and correct integration with Pydantic models.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from pydantic import ValidationError

from backend.vectordbs.chroma_store import ChromaDBStore
from backend.vectordbs.data_types import CollectionConfig, EmbeddedChunk, VectorDBResponse, VectorSearchRequest
from backend.vectordbs.error_types import CollectionError, DocumentError
from core.config import Settings


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.embedding_dim = 768
    settings.embedding_field = "embedding"
    settings.chromadb_host = "localhost"
    settings.chromadb_port = 8000
    settings.log_level = "INFO"
    return settings


class ConcreteChromaStore(ChromaDBStore):
    """Concrete implementation for testing that implements all abstract methods."""

    def _delete_collection_impl(self, collection_name: str) -> None:
        """Mock implementation for testing."""


@pytest.fixture
def chroma_store(mock_settings):
    """Create a ChromaDBStore instance with mocked client."""
    with patch("backend.vectordbs.chroma_store.chromadb.HttpClient") as mock_client:
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        store = ConcreteChromaStore(client=mock_client_instance, settings=mock_settings)
        return store


class TestCreateCollectionImpl:
    """Test _create_collection_impl with CollectionConfig."""

    def test_create_collection_impl_success(self, chroma_store):
        """Test successful collection creation with Pydantic config."""
        config = CollectionConfig(
            collection_name="test_collection",
            dimension=768,
            metric_type="COSINE",
            index_type="FLAT",
            description="Test collection",
        )

        chroma_store._client.create_collection = MagicMock()

        result = chroma_store._create_collection_impl(config)

        assert result["status"] == "created"
        assert result["collection_name"] == "test_collection"
        assert result["dimension"] == 768
        assert result["metric_type"] == "COSINE"
        chroma_store._client.create_collection.assert_called_once_with(
            name="test_collection",
            metadata={"dimension": 768, "metric": "cosine", "description": "Test collection"},
        )

    def test_create_collection_impl_without_description(self, chroma_store):
        """Test collection creation without description."""
        config = CollectionConfig(
            collection_name="simple_collection",
            dimension=768,
            metric_type="COSINE",
        )

        chroma_store._client.create_collection = MagicMock()

        result = chroma_store._create_collection_impl(config)

        assert result["status"] == "created"
        assert result["collection_name"] == "simple_collection"
        # Verify description not included when None
        call_args = chroma_store._client.create_collection.call_args[1]["metadata"]
        assert "description" not in call_args

    def test_create_collection_impl_dimension_mismatch(self, chroma_store):
        """Test that dimension mismatch raises CollectionError."""
        config = CollectionConfig(
            collection_name="test_collection",
            dimension=1536,  # Doesn't match settings.embedding_dim (768)
            metric_type="COSINE",
        )

        # The validation raises ValueError, but _create_collection_impl wraps it in CollectionError
        with pytest.raises(CollectionError, match="doesn't match embedding model dimension"):
            chroma_store._create_collection_impl(config)


class TestAddDocumentsImpl:
    """Test _add_documents_impl with EmbeddedChunk."""

    def test_add_documents_impl_with_valid_chunks(self, chroma_store):
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

        mock_collection = MagicMock()
        chroma_store._client.get_collection = MagicMock(return_value=mock_collection)

        result = chroma_store._add_documents_impl("test_collection", chunks)

        assert len(result) == 2
        assert result == ["chunk1", "chunk2"]
        mock_collection.upsert.assert_called_once()

        # Verify upsert was called with correct parameters
        call_args = mock_collection.upsert.call_args
        assert call_args[1]["ids"] == ["chunk1", "chunk2"]
        assert call_args[1]["documents"] == ["Test text 1", "Test text 2"]

        # Verify embeddings are numpy arrays
        embeddings_arg = call_args[1]["embeddings"]
        assert isinstance(embeddings_arg, np.ndarray)
        assert embeddings_arg.shape == (2, 768)
        assert embeddings_arg.dtype == np.float32

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

    def test_search_impl_with_query_vector(self, chroma_store):
        """Test search with pre-computed query vector."""
        request = VectorSearchRequest(
            query_vector=[0.5] * 768,
            collection_id="test_collection",
            top_k=5,
        )

        mock_collection = MagicMock()
        chroma_store._client.get_collection = MagicMock(return_value=mock_collection)
        mock_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "distances": [[0.1, 0.2]],
            "metadatas": [[{"source": "OTHER", "document_id": "doc1"}, {"source": "OTHER", "document_id": "doc2"}]],
            "documents": [["text1", "text2"]],
        }

        with patch.object(chroma_store, "_process_search_results", return_value=[]):
            result = chroma_store._search_impl(request)

            assert isinstance(result, list)
            mock_collection.query.assert_called_once_with(
                query_embeddings=[0.5] * 768,
                n_results=5,
            )

    def test_search_impl_with_query_text(self, chroma_store):
        """Test search with query text (generates embeddings)."""
        request = VectorSearchRequest(
            query_text="What is machine learning?",
            collection_id="test_collection",
            top_k=10,
        )

        mock_collection = MagicMock()
        chroma_store._client.get_collection = MagicMock(return_value=mock_collection)
        mock_collection.query.return_value = {
            "ids": [[]],
            "distances": [[]],
            "metadatas": [[]],
            "documents": [[]],
        }

        with patch("backend.vectordbs.chroma_store.get_embeddings_for_vector_store") as mock_embed:
            mock_embed.return_value = [[0.5] * 768]

            with patch.object(chroma_store, "_process_search_results", return_value=[]):
                result = chroma_store._search_impl(request)

                assert isinstance(result, list)
                mock_embed.assert_called_once_with("What is machine learning?", settings=chroma_store.settings)
                mock_collection.query.assert_called_once()

    def test_search_impl_missing_both_query_params(self, chroma_store):
        """Test that VectorSearchRequest validates query params at model creation."""
        # Pydantic validates in model_post_init, so the error happens at creation time
        with pytest.raises(ValidationError, match="Either query_text or query_vector must be provided"):
            VectorSearchRequest(
                collection_id="test_collection",
                top_k=10,
            )


class TestDeleteDocumentsWithResponse:
    """Test delete_documents_with_response returning VectorDBResponse."""

    def test_delete_documents_with_response_success(self, chroma_store):
        """Test successful deletion returns success response."""
        mock_collection = MagicMock()
        chroma_store._client.get_collection = MagicMock(return_value=mock_collection)

        response = chroma_store.delete_documents_with_response("test_collection", ["doc1", "doc2"])

        assert response.success is True
        assert response.data["deleted_count"] == 2
        assert response.data["collection_name"] == "test_collection"
        assert response.data["document_ids"] == ["doc1", "doc2"]
        assert "elapsed_seconds" in response.metadata
        mock_collection.delete.assert_called_once_with(ids=["doc1", "doc2"])

    def test_delete_documents_with_response_error(self, chroma_store):
        """Test that deletion errors return error response."""
        chroma_store._client.get_collection = MagicMock(side_effect=Exception("Collection not found"))

        response = chroma_store.delete_documents_with_response("missing_collection", ["doc1"])

        assert response.success is False
        assert response.error is not None
        assert "Failed to delete documents" in response.error
        assert response.metadata["collection_name"] == "missing_collection"
        assert response.metadata["document_count"] == 1


class TestBackwardCompatibility:
    """Test that backward compatibility wrappers work correctly."""

    def test_create_collection_wrapper_calls_impl(self, chroma_store):
        """Test that create_collection wrapper converts to CollectionConfig."""
        with patch.object(chroma_store, "_create_collection_impl") as mock_impl:
            mock_impl.return_value = {"status": "created"}

            chroma_store.create_collection("test_collection", metadata={"description": "Test"})

            # Verify it called _create_collection_impl with CollectionConfig
            mock_impl.assert_called_once()
            call_args = mock_impl.call_args[0][0]
            assert isinstance(call_args, CollectionConfig)
            assert call_args.collection_name == "test_collection"
            assert call_args.dimension == 768
            assert call_args.description == "Test"

    def test_delete_documents_wrapper_raises_on_error(self, chroma_store):
        """Test that delete_documents wrapper raises error on failure."""
        error_response = VectorDBResponse.create_error(error="Deletion failed")

        with patch.object(chroma_store, "delete_documents_with_response", return_value=error_response):
            with pytest.raises(DocumentError, match="Deletion failed"):
                chroma_store.delete_documents("test_collection", ["doc1"])
