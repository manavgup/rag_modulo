"""Unit tests for WeaviateStore Pydantic model integration.

Tests the Pydantic-based implementation methods (_*_impl) to ensure
type safety, validation, and correct integration with Pydantic models.
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from backend.vectordbs.data_types import CollectionConfig, EmbeddedChunk, VectorDBResponse, VectorSearchRequest
from backend.vectordbs.error_types import CollectionError, DocumentError
from backend.vectordbs.weaviate_store import WeaviateDataStore
from core.config import Settings


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.embedding_dim = 768
    settings.embedding_field = "embedding"
    settings.weaviate_host = "localhost"
    settings.weaviate_port = 8080
    settings.weaviate_grpc_port = 50051
    settings.weaviate_username = None
    settings.weaviate_password = None
    settings.weaviate_scopes = None
    return settings


class ConcreteWeaviateStore(WeaviateDataStore):
    """Concrete implementation for testing that implements all abstract methods."""

    def _delete_collection_impl(self, collection_name: str) -> None:
        """Mock implementation for testing."""


@pytest.fixture
def weaviate_store(mock_settings):
    """Create a WeaviateDataStore instance with mocked connection."""
    with patch("backend.vectordbs.weaviate_store.weaviate.connect_to_custom") as mock_connect:
        mock_client = MagicMock()
        mock_connect.return_value = mock_client

        # Mock schema operations
        mock_client.schema.exists.return_value = False
        mock_client.schema.create_class = MagicMock()

        store = ConcreteWeaviateStore(settings=mock_settings)
        return store


class TestCreateCollectionImpl:
    """Test _create_collection_impl with CollectionConfig."""

    def test_create_collection_impl_success(self, weaviate_store):
        """Test successful collection creation with Pydantic config."""
        config = CollectionConfig(
            collection_name="test_collection",
            dimension=768,
            metric_type="COSINE",
            index_type="HNSW",
            description="Test collection",
        )

        with patch.object(weaviate_store.client.schema, "exists", return_value=False):
            with patch.object(weaviate_store.client.schema, "create_class") as mock_create:
                result = weaviate_store._create_collection_impl(config)

                assert result["status"] == "created"
                assert result["collection_name"] == "test_collection"
                assert result["dimension"] == 768
                assert result["metric_type"] == "COSINE"
                mock_create.assert_called_once()

                # Verify schema structure
                call_args = mock_create.call_args[0][0]
                assert call_args["class"] == "test_collection"
                assert call_args["vectorizer"] == "none"
                assert (
                    len(call_args["properties"]) == 6
                )  # text, document_id, chunk_id, source, page_number, chunk_number

    def test_create_collection_impl_already_exists(self, weaviate_store):
        """Test that existing collection returns appropriate status."""
        config = CollectionConfig(
            collection_name="existing_collection",
            dimension=768,
            metric_type="COSINE",
        )

        with patch.object(weaviate_store.client.schema, "exists", return_value=True):
            result = weaviate_store._create_collection_impl(config)

            assert result["status"] == "exists"
            assert result["collection_name"] == "existing_collection"

    def test_create_collection_impl_dimension_mismatch(self, weaviate_store):
        """Test that dimension mismatch raises CollectionError."""
        config = CollectionConfig(
            collection_name="test_collection",
            dimension=1536,  # Doesn't match settings.embedding_dim (768)
            metric_type="COSINE",
        )

        # The validation raises ValueError, but _create_collection_impl wraps it in CollectionError
        with pytest.raises(CollectionError, match="doesn't match embedding model dimension"):
            weaviate_store._create_collection_impl(config)


class TestAddDocumentsImpl:
    """Test _add_documents_impl with EmbeddedChunk."""

    def test_add_documents_impl_with_valid_chunks(self, weaviate_store):
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

        with patch.object(weaviate_store.client.data_object, "create") as mock_create:
            result = weaviate_store._add_documents_impl("test_collection", chunks)

            assert len(result) == 2
            assert result == ["chunk1", "chunk2"]
            assert mock_create.call_count == 2

            # Verify first call
            first_call_kwargs = mock_create.call_args_list[0][1]
            assert first_call_kwargs["class_name"] == "test_collection"
            assert first_call_kwargs["data_object"]["text"] == "Test text 1"
            assert first_call_kwargs["data_object"]["chunk_id"] == "chunk1"
            assert first_call_kwargs["vector"] == [0.1] * 768

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

    def test_search_impl_with_query_vector(self, weaviate_store):
        """Test search with pre-computed query vector."""
        request = VectorSearchRequest(
            query_vector=[0.5] * 768,
            collection_id="test_collection",
            top_k=5,
        )

        mock_query_builder = MagicMock()
        mock_query_builder.with_near_vector.return_value = mock_query_builder
        mock_query_builder.with_limit.return_value = mock_query_builder
        mock_query_builder.do.return_value = {"data": {"Get": {"test_collection": []}}}

        with patch.object(weaviate_store.client.query, "get", return_value=mock_query_builder):
            result = weaviate_store._search_impl(request)

            assert isinstance(result, list)
            mock_query_builder.with_near_vector.assert_called_once_with({"vector": [0.5] * 768})
            mock_query_builder.with_limit.assert_called_once_with(5)

    def test_search_impl_with_query_text(self, weaviate_store):
        """Test search with query text (generates embeddings)."""
        request = VectorSearchRequest(
            query_text="What is machine learning?",
            collection_id="test_collection",
            top_k=10,
        )

        mock_query_builder = MagicMock()
        mock_query_builder.with_near_vector.return_value = mock_query_builder
        mock_query_builder.with_limit.return_value = mock_query_builder
        mock_query_builder.do.return_value = {"data": {"Get": {"test_collection": []}}}

        with patch.object(weaviate_store.client.query, "get", return_value=mock_query_builder):
            with patch("backend.vectordbs.weaviate_store.get_embeddings_for_vector_store") as mock_embed:
                mock_embed.return_value = [[0.5] * 768]

                result = weaviate_store._search_impl(request)

                assert isinstance(result, list)
                mock_embed.assert_called_once_with("What is machine learning?", settings=weaviate_store.settings)
                mock_query_builder.with_near_vector.assert_called_once_with({"vector": [0.5] * 768})

    def test_search_impl_missing_both_query_params(self, weaviate_store):
        """Test that VectorSearchRequest validates query params at model creation."""
        # Pydantic validates in model_post_init, so the error happens at creation time
        with pytest.raises(ValidationError, match="Either query_text or query_vector must be provided"):
            VectorSearchRequest(
                collection_id="test_collection",
                top_k=10,
            )


class TestDeleteDocumentsWithResponse:
    """Test delete_documents_with_response returning VectorDBResponse."""

    def test_delete_documents_with_response_success(self, weaviate_store):
        """Test successful deletion returns success response."""
        mock_query_builder = MagicMock()
        mock_query_builder.with_where.return_value = mock_query_builder
        mock_query_builder.do.return_value = {
            "data": {
                "Get": {
                    "test_collection": [
                        {"_additional": {"id": "uuid1"}},
                        {"_additional": {"id": "uuid2"}},
                    ]
                }
            }
        }

        with patch.object(weaviate_store.client.query, "get", return_value=mock_query_builder):
            with patch.object(weaviate_store.client.data_object, "delete") as mock_delete:
                response = weaviate_store.delete_documents_with_response("test_collection", ["doc1", "doc2"])

                assert response.success is True
                assert response.data["deleted_count"] == 4  # 2 docs with 2 objects each
                assert response.data["collection_name"] == "test_collection"
                assert "elapsed_seconds" in response.metadata
                assert mock_delete.call_count == 4

    def test_delete_documents_with_response_error(self, weaviate_store):
        """Test that deletion errors return error response."""
        with patch.object(weaviate_store.client.query, "get", side_effect=Exception("Query failed")):
            response = weaviate_store.delete_documents_with_response("missing_collection", ["doc1"])

            assert response.success is False
            assert response.error is not None
            assert "Failed to delete documents" in response.error


class TestBackwardCompatibility:
    """Test that backward compatibility wrappers work correctly."""

    def test_create_collection_wrapper_calls_impl(self, weaviate_store):
        """Test that create_collection wrapper converts to CollectionConfig."""
        with patch.object(weaviate_store, "_create_collection_impl") as mock_impl:
            mock_impl.return_value = {"status": "created"}

            weaviate_store.create_collection("test_collection", metadata={"description": "Test"})

            # Verify it called _create_collection_impl with CollectionConfig
            mock_impl.assert_called_once()
            call_args = mock_impl.call_args[0][0]
            assert isinstance(call_args, CollectionConfig)
            assert call_args.collection_name == "test_collection"
            assert call_args.dimension == 768

    def test_delete_documents_wrapper_raises_on_error(self, weaviate_store):
        """Test that delete_documents wrapper raises error on failure."""
        error_response = VectorDBResponse.create_error(error="Deletion failed")

        with patch.object(weaviate_store, "delete_documents_with_response", return_value=error_response):
            with pytest.raises(DocumentError, match="Deletion failed"):
                weaviate_store.delete_documents("test_collection", ["doc1"])
