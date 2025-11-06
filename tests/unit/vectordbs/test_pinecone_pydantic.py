"""Unit tests for PineconeStore Pydantic model integration.

Tests the Pydantic-based implementation methods (_*_impl) to ensure
type safety, validation, and correct integration with Pydantic models.
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from backend.vectordbs.data_types import CollectionConfig, EmbeddedChunk, VectorDBResponse, VectorSearchRequest
from backend.vectordbs.error_types import CollectionError, DocumentError
from backend.vectordbs.pinecone_store import PineconeStore
from core.config import Settings


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.embedding_dim = 768
    settings.embedding_field = "embedding"
    settings.pinecone_api_key = "test-api-key"
    return settings


class ConcretePineconeStore(PineconeStore):
    """Concrete implementation for testing that implements all abstract methods."""

    def _delete_collection_impl(self, collection_name: str) -> None:
        """Mock implementation for testing."""


@pytest.fixture
def pinecone_store(mock_settings):
    """Create a PineconeStore instance with mocked Pinecone client."""
    with patch("backend.vectordbs.pinecone_store.Pinecone") as mock_pinecone:
        mock_pc = MagicMock()
        mock_pinecone.return_value = mock_pc
        store = ConcretePineconeStore(settings=mock_settings)
        store.pc = mock_pc  # Ensure we have the mocked client
        return store


class TestCreateCollectionImpl:
    """Test _create_collection_impl with CollectionConfig."""

    def test_create_collection_impl_success(self, pinecone_store):
        """Test successful collection creation with Pydantic config.

        Given: Valid collection configuration
        When: _create_collection_impl is called
        Then: Collection is created successfully with correct parameters
        """
        config = CollectionConfig(
            collection_name="test_collection",
            dimension=768,
            metric_type="COSINE",
            index_type="HNSW",
            description="Test collection",
        )

        # Mock list_indexes to return empty list (collection doesn't exist)
        mock_index = MagicMock()
        mock_index.name = "other_collection"
        pinecone_store.pc.list_indexes.return_value = [mock_index]

        result = pinecone_store._create_collection_impl(config)

        assert result["status"] == "created"
        assert result["collection_name"] == "test_collection"
        assert result["dimension"] == 768
        assert result["metric_type"] == "COSINE"
        pinecone_store.pc.create_index.assert_called_once()

        # Verify create_index was called with correct parameters
        call_args = pinecone_store.pc.create_index.call_args
        assert call_args[1]["name"] == "test_collection"
        assert call_args[1]["dimension"] == 768
        assert call_args[1]["metric"] == "cosine"

    def test_create_collection_impl_already_exists(self, pinecone_store):
        """Test that existing collection returns appropriate status.

        Given: Collection already exists in Pinecone
        When: _create_collection_impl is called
        Then: Returns 'exists' status without attempting creation
        """
        config = CollectionConfig(
            collection_name="existing_collection",
            dimension=768,
            metric_type="COSINE",
        )

        # Mock list_indexes to return the collection
        mock_index = MagicMock()
        mock_index.name = "existing_collection"
        pinecone_store.pc.list_indexes.return_value = [mock_index]

        result = pinecone_store._create_collection_impl(config)

        assert result["status"] == "exists"
        assert result["collection_name"] == "existing_collection"
        pinecone_store.pc.create_index.assert_not_called()

    def test_create_collection_impl_dimension_mismatch(self, pinecone_store):
        """Test that dimension mismatch raises CollectionError.

        Given: Collection config with dimension that doesn't match settings
        When: _create_collection_impl is called
        Then: CollectionError is raised with appropriate message
        """
        config = CollectionConfig(
            collection_name="test_collection",
            dimension=1536,  # Doesn't match settings.embedding_dim (768)
            metric_type="COSINE",
        )

        # The validation raises ValueError, but _create_collection_impl wraps it in CollectionError
        with pytest.raises(CollectionError, match="doesn't match embedding model dimension"):
            pinecone_store._create_collection_impl(config)


class TestAddDocumentsImpl:
    """Test _add_documents_impl with EmbeddedChunk."""

    def test_add_documents_impl_with_valid_chunks(self, pinecone_store):
        """Test successful document addition with EmbeddedChunk.

        Given: Valid embedded chunks with proper metadata
        When: _add_documents_impl is called
        Then: Chunks are upserted to Pinecone with correct structure
        """
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

        # Mock Index
        mock_index = MagicMock()
        pinecone_store.pc.Index.return_value = mock_index

        result = pinecone_store._add_documents_impl("test_collection", chunks)

        assert len(result) == 2
        assert result == ["chunk1", "chunk2"]
        mock_index.upsert.assert_called_once()

        # Verify upsert was called with correct vector structure
        call_args = mock_index.upsert.call_args
        vectors = call_args[1]["vectors"]
        assert len(vectors) == 2
        assert vectors[0]["id"] == "chunk1"
        assert vectors[0]["values"] == [0.1] * 768
        assert vectors[0]["metadata"]["text"] == "Test text 1"
        assert vectors[0]["metadata"]["document_id"] == "doc1"

    def test_embedded_chunk_validates_embeddings_required(self):
        """Test that EmbeddedChunk enforces embeddings are present.

        Given: EmbeddedChunk model
        When: Creating chunk without embeddings
        Then: ValidationError is raised
        """
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

    def test_search_impl_with_query_vector(self, pinecone_store):
        """Test search with pre-computed query vector.

        Given: VectorSearchRequest with pre-computed query vector
        When: _search_impl is called
        Then: Pinecone index.query is called with correct parameters
        """
        request = VectorSearchRequest(
            query_vector=[0.5] * 768,
            collection_id="test_collection",
            top_k=5,
        )

        # Mock Index and query results
        mock_index = MagicMock()
        mock_index.query.return_value = {"matches": []}
        pinecone_store.pc.Index.return_value = mock_index

        with patch.object(pinecone_store, "_process_search_results", return_value=[]):
            result = pinecone_store._search_impl(request)

            assert isinstance(result, list)
            mock_index.query.assert_called_once()

            # Verify query was called with correct parameters
            call_args = mock_index.query.call_args
            assert call_args[1]["vector"] == [0.5] * 768
            assert call_args[1]["top_k"] == 5
            assert call_args[1]["include_metadata"] is True

    def test_search_impl_with_query_text(self, pinecone_store):
        """Test search with query text (generates embeddings).

        Given: VectorSearchRequest with query text
        When: _search_impl is called
        Then: Embeddings are generated and search is performed
        """
        request = VectorSearchRequest(
            query_text="What is machine learning?",
            collection_id="test_collection",
            top_k=10,
        )

        # Mock Index
        mock_index = MagicMock()
        mock_index.query.return_value = {"matches": []}
        pinecone_store.pc.Index.return_value = mock_index

        with patch("backend.vectordbs.pinecone_store.get_embeddings_for_vector_store") as mock_embed:
            mock_embed.return_value = [[0.5] * 768]

            with patch.object(pinecone_store, "_process_search_results", return_value=[]):
                result = pinecone_store._search_impl(request)

                assert isinstance(result, list)
                mock_embed.assert_called_once_with("What is machine learning?", settings=pinecone_store.settings)
                mock_index.query.assert_called_once()

    def test_search_impl_missing_both_query_params(self, pinecone_store):
        """Test that VectorSearchRequest validates query params at model creation.

        Given: VectorSearchRequest without query_text or query_vector
        When: Creating the request
        Then: ValidationError is raised
        """
        # Pydantic validates in model_post_init, so the error happens at creation time
        with pytest.raises(ValidationError, match="Either query_text or query_vector must be provided"):
            VectorSearchRequest(
                collection_id="test_collection",
                top_k=10,
            )


class TestDeleteDocumentsWithResponse:
    """Test delete_documents_with_response returning VectorDBResponse."""

    def test_delete_documents_with_response_success(self, pinecone_store):
        """Test successful deletion returns success response.

        Given: Valid document IDs in existing collection
        When: delete_documents_with_response is called
        Then: Documents are deleted and success response is returned
        """
        # Mock Index and query results
        mock_index = MagicMock()
        mock_index.query.return_value = {
            "matches": [
                {"id": "vec1", "score": 0.9},
                {"id": "vec2", "score": 0.8},
            ]
        }
        pinecone_store.pc.Index.return_value = mock_index

        response = pinecone_store.delete_documents_with_response("test_collection", ["doc1", "doc2"])

        assert response.success is True
        assert response.data["deleted_count"] == 2
        assert response.data["collection_name"] == "test_collection"
        assert "elapsed_seconds" in response.metadata
        mock_index.delete.assert_called()

    def test_delete_documents_with_response_error(self, pinecone_store):
        """Test that deletion errors return error response.

        Given: Collection that doesn't exist
        When: delete_documents_with_response is called
        Then: Error response is returned with details
        """
        # Mock Index to raise exception
        pinecone_store.pc.Index.side_effect = Exception("Collection not found")

        response = pinecone_store.delete_documents_with_response("missing_collection", ["doc1"])

        assert response.success is False
        assert response.error is not None
        assert "Failed to delete documents" in response.error


class TestBackwardCompatibility:
    """Test that backward compatibility wrappers work correctly."""

    def test_create_collection_wrapper_calls_impl(self, pinecone_store):
        """Test that create_collection wrapper converts to CollectionConfig.

        Given: Legacy create_collection method call
        When: Method is invoked with collection name and metadata
        Then: _create_collection_impl is called with proper CollectionConfig
        """
        with patch.object(pinecone_store, "_create_collection_impl") as mock_impl:
            mock_impl.return_value = {"status": "created"}

            pinecone_store.create_collection("test_collection", metadata={"description": "Test"})

            # Verify it called _create_collection_impl with CollectionConfig
            mock_impl.assert_called_once()
            call_args = mock_impl.call_args[0][0]
            assert isinstance(call_args, CollectionConfig)
            assert call_args.collection_name == "test_collection"
            assert call_args.dimension == 768
            assert call_args.description == "Test"

    def test_delete_documents_wrapper_raises_on_error(self, pinecone_store):
        """Test that delete_documents wrapper raises error on failure.

        Given: delete_documents_with_response returns error response
        When: delete_documents wrapper is called
        Then: DocumentError is raised with error message
        """
        error_response = VectorDBResponse.create_error(error="Deletion failed")

        with patch.object(pinecone_store, "delete_documents_with_response", return_value=error_response):
            with pytest.raises(DocumentError, match="Deletion failed"):
                pinecone_store.delete_documents("test_collection", ["doc1"])
