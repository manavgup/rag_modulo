"""Unit tests for enhanced pydantic data types (Issue #211)."""

import pytest
from pydantic import ValidationError

from backend.vectordbs.data_types import (
    CollectionConfig,
    Document,
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentIngestionRequest,
    EmbeddedChunk,
    QueryWithEmbedding,
    Source,
    VectorDBResponse,
    VectorSearchRequest,
)


class TestEmbeddedChunk:
    """Test EmbeddedChunk model."""

    def test_create_with_required_fields(self):
        """Test creating EmbeddedChunk with all required fields."""
        chunk = EmbeddedChunk(
            chunk_id="chunk_1",
            text="Test text",
            embeddings=[0.1, 0.2, 0.3],
        )
        assert chunk.chunk_id == "chunk_1"
        assert chunk.text == "Test text"
        assert chunk.embeddings == [0.1, 0.2, 0.3]

    def test_empty_embeddings_raises_error(self):
        """Test that empty embeddings raise ValueError."""
        with pytest.raises(ValueError, match="Embeddings must be non-empty"):
            EmbeddedChunk(
                chunk_id="chunk_1",
                text="Test text",
                embeddings=[],
            )

    def test_from_chunk_with_embeddings(self):
        """Test converting DocumentChunk to EmbeddedChunk."""
        metadata = DocumentChunkMetadata(source=Source.PDF, page_number=1, chunk_number=1)
        chunk = DocumentChunk(
            chunk_id="chunk_1",
            text="Test text",
            embeddings=[0.1, 0.2, 0.3],
            metadata=metadata,
            document_id="doc_1",
        )

        embedded = EmbeddedChunk.from_chunk(chunk)
        assert embedded.chunk_id == "chunk_1"
        assert embedded.text == "Test text"
        assert embedded.embeddings == [0.1, 0.2, 0.3]
        assert embedded.metadata == metadata

    def test_from_chunk_without_embeddings(self):
        """Test that converting chunk without embeddings raises error."""
        chunk = DocumentChunk(
            chunk_id="chunk_1",
            text="Test text",
            embeddings=None,
        )

        with pytest.raises(ValueError, match="has no embeddings"):
            EmbeddedChunk.from_chunk(chunk)

    def test_from_chunk_without_chunk_id(self):
        """Test that converting chunk without chunk_id raises error."""
        chunk = DocumentChunk(
            chunk_id=None,
            text="Test text",
            embeddings=[0.1, 0.2, 0.3],
        )

        with pytest.raises(ValueError, match="has no chunk_id"):
            EmbeddedChunk.from_chunk(chunk)

    def test_to_vector_metadata(self):
        """Test converting to vector metadata dict."""
        metadata = DocumentChunkMetadata(
            source=Source.PDF, page_number=1, chunk_number=2, start_index=0, end_index=100, author="Test Author"
        )
        chunk = EmbeddedChunk(
            chunk_id="chunk_1",
            text="Test text",
            embeddings=[0.1, 0.2, 0.3],
            metadata=metadata,
            document_id="doc_1",
            level=0,
        )

        metadata_dict = chunk.to_vector_metadata()
        assert metadata_dict["chunk_id"] == "chunk_1"
        assert metadata_dict["text"] == "Test text"
        assert metadata_dict["document_id"] == "doc_1"
        assert metadata_dict["source"] == "Source.PDF"  # Enum serializes with class name
        assert metadata_dict["page_number"] == 1
        assert metadata_dict["chunk_number"] == 2
        assert metadata_dict["level"] == 0

    def test_to_vector_db(self):
        """Test preparing data for vector DB insertion."""
        chunk = EmbeddedChunk(
            chunk_id="chunk_1",
            text="Test text",
            embeddings=[0.1, 0.2, 0.3],
        )

        embeddings, metadata = chunk.to_vector_db()
        assert embeddings == [0.1, 0.2, 0.3]
        assert metadata["chunk_id"] == "chunk_1"
        assert metadata["text"] == "Test text"


class TestCollectionConfig:
    """Test CollectionConfig model."""

    def test_create_with_defaults(self):
        """Test creating CollectionConfig with default values."""
        config = CollectionConfig(
            name="test_collection",
            dimension=768,
        )
        assert config.name == "test_collection"
        assert config.dimension == 768
        assert config.metric_type == "COSINE"
        assert config.index_type == "IVF_FLAT"

    def test_create_with_custom_values(self):
        """Test creating CollectionConfig with custom values."""
        config = CollectionConfig(
            name="test_collection",
            dimension=1024,
            metric_type="L2",
            index_type="HNSW",
            index_params={"M": 16, "efConstruction": 200},
        )
        assert config.metric_type == "L2"
        assert config.index_type == "HNSW"
        assert config.index_params == {"M": 16, "efConstruction": 200}

    def test_invalid_dimension(self):
        """Test that negative dimension raises error."""
        with pytest.raises(ValueError, match="Dimension must be positive"):
            CollectionConfig(
                name="test_collection",
                dimension=-1,
            )

    def test_invalid_metric_type(self):
        """Test that invalid metric type raises error."""
        with pytest.raises(ValueError, match="Invalid metric_type"):
            CollectionConfig(
                name="test_collection",
                dimension=768,
                metric_type="INVALID",
            )


class TestDocumentIngestionRequest:
    """Test DocumentIngestionRequest model."""

    def test_create_with_documents(self):
        """Test creating ingestion request with documents."""
        chunk = DocumentChunk(
            chunk_id="chunk_1",
            text="Test text",
            embeddings=[0.1, 0.2, 0.3],
        )
        doc = Document(
            document_id="doc_1",
            name="test.pdf",
            chunks=[chunk],
        )
        request = DocumentIngestionRequest(
            collection_name="test_collection",
            documents=[doc],
        )
        assert request.collection_name == "test_collection"
        assert len(request.documents) == 1
        assert request.batch_size == 100

    def test_empty_documents_raises_error(self):
        """Test that empty documents list raises error."""
        with pytest.raises(ValueError, match="Documents list cannot be empty"):
            DocumentIngestionRequest(
                collection_name="test_collection",
                documents=[],
            )

    def test_invalid_batch_size(self):
        """Test that invalid batch size raises error."""
        chunk = DocumentChunk(
            chunk_id="chunk_1",
            text="Test text",
            embeddings=[0.1, 0.2, 0.3],
        )
        doc = Document(
            document_id="doc_1",
            name="test.pdf",
            chunks=[chunk],
        )
        with pytest.raises(ValueError, match="Batch size must be positive"):
            DocumentIngestionRequest(
                collection_name="test_collection",
                documents=[doc],
                batch_size=0,
            )

    def test_create_collection_without_config(self):
        """Test that create_collection=True without config raises error."""
        chunk = DocumentChunk(
            chunk_id="chunk_1",
            text="Test text",
            embeddings=[0.1, 0.2, 0.3],
        )
        doc = Document(
            document_id="doc_1",
            name="test.pdf",
            chunks=[chunk],
        )
        with pytest.raises(ValueError, match="collection_config required"):
            DocumentIngestionRequest(collection_name="test_collection", documents=[doc], create_collection=True)

    def test_extract_embedded_chunks(self):
        """Test extracting embedded chunks from documents."""
        chunk1 = DocumentChunk(
            chunk_id="chunk_1",
            text="Test text 1",
            embeddings=[0.1, 0.2, 0.3],
        )
        chunk2 = DocumentChunk(
            chunk_id="chunk_2",
            text="Test text 2",
            embeddings=[0.4, 0.5, 0.6],
        )
        doc = Document(
            document_id="doc_1",
            name="test.pdf",
            chunks=[chunk1, chunk2],
        )
        request = DocumentIngestionRequest(
            collection_name="test_collection",
            documents=[doc],
        )

        embedded_chunks = request.extract_embedded_chunks()
        assert len(embedded_chunks) == 2
        assert all(isinstance(chunk, EmbeddedChunk) for chunk in embedded_chunks)
        assert embedded_chunks[0].chunk_id == "chunk_1"
        assert embedded_chunks[1].chunk_id == "chunk_2"

    def test_extract_embedded_chunks_fails_without_embeddings(self):
        """Test that extracting chunks without embeddings raises error."""
        chunk = DocumentChunk(
            chunk_id="chunk_1",
            text="Test text",
            embeddings=None,
        )
        doc = Document(
            document_id="doc_1",
            name="test.pdf",
            chunks=[chunk],
        )
        request = DocumentIngestionRequest(
            collection_name="test_collection",
            documents=[doc],
        )

        with pytest.raises(ValueError, match="has no embeddings"):
            request.extract_embedded_chunks()


class TestVectorSearchRequest:
    """Test VectorSearchRequest model."""

    def test_create_with_text_query(self):
        """Test creating search request with text query."""
        request = VectorSearchRequest(
            collection_name="test_collection",
            query="What is machine learning?",
        )
        assert request.collection_name == "test_collection"
        assert request.query == "What is machine learning?"
        assert request.number_of_results == 10

    def test_create_with_embedding_query(self):
        """Test creating search request with embedding query."""
        query_with_embedding = QueryWithEmbedding(text="What is ML?", embeddings=[0.1, 0.2, 0.3])
        request = VectorSearchRequest(
            collection_name="test_collection",
            query=query_with_embedding,
            number_of_results=5,
        )
        assert request.number_of_results == 5

    def test_invalid_number_of_results(self):
        """Test that invalid number of results raises error."""
        with pytest.raises(ValueError, match="number_of_results must be positive"):
            VectorSearchRequest(
                collection_name="test_collection",
                query="test",
                number_of_results=0,
            )

    def test_get_query_text_from_string(self):
        """Test getting query text from string query."""
        request = VectorSearchRequest(
            collection_name="test_collection",
            query="What is ML?",
        )
        assert request.get_query_text() == "What is ML?"

    def test_get_query_text_from_embedding(self):
        """Test getting query text from QueryWithEmbedding."""
        query_with_embedding = QueryWithEmbedding(text="What is ML?", embeddings=[0.1, 0.2, 0.3])
        request = VectorSearchRequest(
            collection_name="test_collection",
            query=query_with_embedding,
        )
        assert request.get_query_text() == "What is ML?"

    def test_get_query_embeddings_from_string(self):
        """Test getting query embeddings from string query."""
        request = VectorSearchRequest(
            collection_name="test_collection",
            query="What is ML?",
        )
        assert request.get_query_embeddings() is None

    def test_get_query_embeddings_from_embedding(self):
        """Test getting query embeddings from QueryWithEmbedding."""
        query_with_embedding = QueryWithEmbedding(text="What is ML?", embeddings=[0.1, 0.2, 0.3])
        request = VectorSearchRequest(
            collection_name="test_collection",
            query=query_with_embedding,
        )
        assert request.get_query_embeddings() == [0.1, 0.2, 0.3]


class TestVectorDBResponse:
    """Test VectorDBResponse model."""

    def test_success_response(self):
        """Test creating success response."""
        response = VectorDBResponse.success_response(data={"count": 5}, message="Success")
        assert response.success is True
        assert response.message == "Success"
        assert response.data == {"count": 5}
        assert response.error is None

    def test_error_response(self):
        """Test creating error response."""
        response = VectorDBResponse.error_response(error="Connection failed")
        assert response.success is False
        assert response.error == "Connection failed"
        assert response.data is None

    def test_response_with_metadata(self):
        """Test creating response with metadata."""
        response = VectorDBResponse.success_response(
            data={"count": 5}, message="Success", metadata={"elapsed_seconds": 1.23}
        )
        assert response.metadata == {"elapsed_seconds": 1.23}
