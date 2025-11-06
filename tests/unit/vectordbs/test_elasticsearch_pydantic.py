"""Unit tests for ElasticSearchStore Pydantic model integration.

Tests the Pydantic-based implementation methods (_*_impl) to ensure
type safety, validation, and correct integration with Pydantic models.
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from backend.vectordbs.data_types import CollectionConfig, EmbeddedChunk, VectorDBResponse, VectorSearchRequest
from backend.vectordbs.elasticsearch_store import ElasticSearchStore
from backend.vectordbs.error_types import CollectionError, DocumentError
from core.config import Settings


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.embedding_dim = 768
    settings.embedding_field = "embedding"
    settings.elastic_host = "localhost"
    settings.elastic_port = 9200
    settings.elastic_password = "test_password"
    settings.elastic_cloud_id = None
    settings.elastic_api_key = None
    settings.collection_name = "test_collection"
    settings.log_level = "INFO"
    return settings


class ConcreteElasticSearchStore(ElasticSearchStore):
    """Concrete implementation for testing that implements all abstract methods."""

    def _delete_collection_impl(self, collection_name: str) -> None:
        """Mock implementation for testing."""


@pytest.fixture
def elasticsearch_store(mock_settings):
    """Create an ElasticSearchStore instance with mocked Elasticsearch client."""
    with patch("backend.vectordbs.elasticsearch_store.Elasticsearch") as mock_es:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_es.return_value = mock_client

        store = ConcreteElasticSearchStore(settings=mock_settings)
        store.client = mock_client
        return store


class TestCreateCollectionImpl:
    """Test _create_collection_impl with CollectionConfig."""

    def test_create_collection_impl_success(self, elasticsearch_store):
        """Test successful collection creation with Pydantic config.

        Given: Valid CollectionConfig with dimension matching settings
        When: _create_collection_impl is called
        Then: Collection is created with proper index mapping
        """
        config = CollectionConfig(
            collection_name="test_collection",
            dimension=768,
            metric_type="COSINE",
            index_type="FLAT",
            description="Test collection",
        )

        elasticsearch_store.client.indices.exists.return_value = False

        result = elasticsearch_store._create_collection_impl(config)

        assert result["status"] == "created"
        assert result["collection_name"] == "test_collection"
        assert result["dimension"] == 768
        assert result["metric_type"] == "COSINE"
        assert result["index_type"] == "FLAT"

        # Verify indices.create was called with proper mapping
        elasticsearch_store.client.indices.create.assert_called_once()
        call_args = elasticsearch_store.client.indices.create.call_args
        assert call_args[1]["index"] == "test_collection"
        assert "mappings" in call_args[1]["body"]
        assert "embeddings" in call_args[1]["body"]["mappings"]["properties"]
        assert call_args[1]["body"]["mappings"]["properties"]["embeddings"]["type"] == "dense_vector"
        assert call_args[1]["body"]["mappings"]["properties"]["embeddings"]["dims"] == 768

    def test_create_collection_impl_already_exists(self, elasticsearch_store):
        """Test that existing collection returns appropriate status.

        Given: Collection already exists in Elasticsearch
        When: _create_collection_impl is called
        Then: Returns 'exists' status without creating duplicate
        """
        config = CollectionConfig(
            collection_name="existing_collection",
            dimension=768,
            metric_type="COSINE",
            index_type="FLAT",
        )

        elasticsearch_store.client.indices.exists.return_value = True

        result = elasticsearch_store._create_collection_impl(config)

        assert result["status"] == "exists"
        assert result["collection_name"] == "existing_collection"
        assert result["dimension"] == 768

        # Verify create was NOT called
        elasticsearch_store.client.indices.create.assert_not_called()

    def test_create_collection_impl_dimension_mismatch(self, elasticsearch_store):
        """Test that dimension mismatch raises CollectionError.

        Given: CollectionConfig with dimension not matching settings
        When: _create_collection_impl is called
        Then: ValueError is raised with appropriate message
        """
        config = CollectionConfig(
            collection_name="test_collection",
            dimension=1536,  # Doesn't match settings.embedding_dim (768)
            metric_type="COSINE",
            index_type="FLAT",
        )

        # The validation raises ValueError, caught by _create_collection_impl and wrapped in CollectionError
        with pytest.raises(CollectionError, match="doesn't match embedding model dimension"):
            elasticsearch_store._create_collection_impl(config)


class TestAddDocumentsImpl:
    """Test _add_documents_impl with EmbeddedChunk."""

    def test_add_documents_impl_with_valid_chunks(self, elasticsearch_store):
        """Test successful document addition with EmbeddedChunk.

        Given: Valid EmbeddedChunk objects with embeddings
        When: _add_documents_impl is called
        Then: Chunks are indexed in Elasticsearch with proper structure
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

        result = elasticsearch_store._add_documents_impl("test_collection", chunks)

        assert len(result) == 2
        assert result == ["chunk1", "chunk2"]

        # Verify client.index was called for each chunk
        assert elasticsearch_store.client.index.call_count == 2

        # Verify structure of first call
        first_call = elasticsearch_store.client.index.call_args_list[0]
        assert first_call[1]["index"] == "test_collection"
        assert first_call[1]["id"] == "chunk1"
        assert "text" in first_call[1]["body"]
        assert "embeddings" in first_call[1]["body"]
        assert len(first_call[1]["body"]["embeddings"]) == 768

    def test_embedded_chunk_validates_embeddings_required(self):
        """Test that EmbeddedChunk enforces embeddings are present.

        Given: EmbeddedChunk model definition
        When: Creating instance with/without embeddings
        Then: Validates embeddings are required and present
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

    def test_search_impl_with_query_vector(self, elasticsearch_store):
        """Test search with pre-computed query vector.

        Given: VectorSearchRequest with query_vector
        When: _search_impl is called
        Then: Elasticsearch script_score query is executed with cosineSimilarity
        """
        request = VectorSearchRequest(
            query_vector=[0.5] * 768,
            collection_id="test_collection",
            top_k=5,
        )

        mock_response = {"hits": {"hits": []}}
        elasticsearch_store.client.search.return_value = mock_response

        with patch.object(elasticsearch_store, "_process_search_results", return_value=[]):
            result = elasticsearch_store._search_impl(request)

            assert isinstance(result, list)
            elasticsearch_store.client.search.assert_called_once()

            # Verify search body structure
            call_args = elasticsearch_store.client.search.call_args
            assert call_args[1]["index"] == "test_collection"
            search_body = call_args[1]["body"]
            assert "query" in search_body
            assert "script_score" in search_body["query"]
            assert "cosineSimilarity" in search_body["query"]["script_score"]["script"]["source"]
            assert search_body["size"] == 5

    def test_search_impl_with_query_text(self, elasticsearch_store):
        """Test search with query text (generates embeddings).

        Given: VectorSearchRequest with query_text
        When: _search_impl is called
        Then: Embeddings are generated and used for script_score query
        """
        request = VectorSearchRequest(
            query_text="What is machine learning?",
            collection_id="test_collection",
            top_k=10,
        )

        mock_response = {"hits": {"hits": []}}
        elasticsearch_store.client.search.return_value = mock_response

        with patch("backend.vectordbs.elasticsearch_store.get_embeddings_for_vector_store") as mock_embed:
            mock_embed.return_value = [[0.5] * 768]

            with patch.object(elasticsearch_store, "_process_search_results", return_value=[]):
                result = elasticsearch_store._search_impl(request)

                assert isinstance(result, list)
                mock_embed.assert_called_once_with("What is machine learning?", settings=elasticsearch_store.settings)
                elasticsearch_store.client.search.assert_called_once()

    def test_search_impl_missing_both_query_params(self, elasticsearch_store):
        """Test that VectorSearchRequest validates query params at model creation.

        Given: VectorSearchRequest with neither query_text nor query_vector
        When: Creating VectorSearchRequest instance
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

    def test_delete_documents_with_response_success(self, elasticsearch_store):
        """Test successful deletion returns success response.

        Given: Valid collection and document IDs
        When: delete_documents_with_response is called
        Then: Returns VectorDBResponse with success=True and deletion metadata
        """
        mock_delete_result = {"deleted": 1}
        elasticsearch_store.client.delete_by_query.return_value = mock_delete_result

        response = elasticsearch_store.delete_documents_with_response("test_collection", ["doc1", "doc2"])

        assert response.success is True
        assert response.data["deleted_count"] == 2
        assert response.data["collection_name"] == "test_collection"
        assert "elapsed_seconds" in response.metadata

        # Verify delete_by_query was called for each document
        assert elasticsearch_store.client.delete_by_query.call_count == 2

    def test_delete_documents_with_response_error(self, elasticsearch_store):
        """Test that deletion errors return error response.

        Given: Elasticsearch client raises exception
        When: delete_documents_with_response is called
        Then: Returns VectorDBResponse with success=False and error message
        """
        elasticsearch_store.client.delete_by_query.side_effect = Exception("Deletion failed")

        response = elasticsearch_store.delete_documents_with_response("missing_collection", ["doc1"])

        assert response.success is False
        assert response.error is not None
        assert "Failed to delete documents" in response.error


class TestBackwardCompatibility:
    """Test that backward compatibility wrappers work correctly."""

    def test_create_collection_wrapper_calls_impl(self, elasticsearch_store):
        """Test that create_collection wrapper converts to CollectionConfig.

        Given: Legacy create_collection call with collection_name and metadata
        When: create_collection is called
        Then: Internally calls _create_collection_impl with CollectionConfig
        """
        with patch.object(elasticsearch_store, "_create_collection_impl") as mock_impl:
            mock_impl.return_value = {"status": "created"}

            elasticsearch_store.create_collection("test_collection", metadata={"description": "Test"})

            # Verify it called _create_collection_impl with CollectionConfig
            mock_impl.assert_called_once()
            call_args = mock_impl.call_args[0][0]
            assert isinstance(call_args, CollectionConfig)
            assert call_args.collection_name == "test_collection"
            assert call_args.dimension == 768
            assert call_args.description == "Test"

    def test_delete_documents_wrapper_raises_on_error(self, elasticsearch_store):
        """Test that delete_documents wrapper raises error on failure.

        Given: delete_documents_with_response returns error response
        When: delete_documents is called
        Then: Raises DocumentError with error message
        """
        error_response = VectorDBResponse.create_error(error="Deletion failed")

        with patch.object(elasticsearch_store, "delete_documents_with_response", return_value=error_response):
            with pytest.raises(DocumentError, match="Deletion failed"):
                elasticsearch_store.delete_documents("test_collection", ["doc1"])
