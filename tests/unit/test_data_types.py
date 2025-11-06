"""Unit tests for vectordbs/data_types.py models."""

import pytest
from pydantic import ValidationError

from vectordbs.data_types import (
    CollectionConfig,
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentIngestionRequest,
    EmbeddedChunk,
    QueryResult,
    Source,
    VectorDBCollectionResponse,
    VectorDBDeleteResponse,
    VectorDBIngestionResponse,
    VectorDBResponse,
    VectorDBSearchResponse,
    VectorSearchRequest,
)


class TestEmbeddedChunk:
    """Tests for EmbeddedChunk model."""

    def test_embedded_chunk_creation_with_embeddings(self):
        """Test creating an EmbeddedChunk with valid embeddings."""
        embeddings = [0.1, 0.2, 0.3, 0.4]
        chunk = EmbeddedChunk(
            chunk_id="test_chunk_1",
            text="Test chunk text",
            embeddings=embeddings,
            document_id="doc_1",
        )

        assert chunk.chunk_id == "test_chunk_1"
        assert chunk.text == "Test chunk text"
        assert chunk.embeddings == embeddings
        assert chunk.document_id == "doc_1"

    def test_embedded_chunk_requires_embeddings(self):
        """Test that EmbeddedChunk requires embeddings."""
        with pytest.raises(ValidationError) as exc_info:
            EmbeddedChunk(
                chunk_id="test_chunk_1",
                text="Test chunk text",
            )

        assert "embeddings" in str(exc_info.value).lower()

    def test_embedded_chunk_rejects_empty_embeddings(self):
        """Test that EmbeddedChunk rejects empty embeddings list."""
        with pytest.raises(ValidationError) as exc_info:
            EmbeddedChunk(
                chunk_id="test_chunk_1",
                text="Test chunk text",
                embeddings=[],
            )

        assert "empty" in str(exc_info.value).lower()

    def test_from_chunk_with_embeddings(self):
        """Test converting DocumentChunk to EmbeddedChunk when embeddings exist."""
        embeddings = [0.1, 0.2, 0.3]
        chunk = DocumentChunk(
            chunk_id="test_chunk",
            text="Test text",
            embeddings=embeddings,
            document_id="doc_1",
        )

        embedded = EmbeddedChunk.from_chunk(chunk)

        assert embedded.chunk_id == chunk.chunk_id
        assert embedded.text == chunk.text
        assert embedded.embeddings == embeddings
        assert embedded.document_id == chunk.document_id

    def test_from_chunk_with_provided_embeddings(self):
        """Test converting DocumentChunk with explicitly provided embeddings."""
        chunk = DocumentChunk(
            chunk_id="test_chunk",
            text="Test text",
            document_id="doc_1",
        )
        embeddings = [0.1, 0.2, 0.3]

        embedded = EmbeddedChunk.from_chunk(chunk, embeddings=embeddings)

        assert embedded.embeddings == embeddings

    def test_from_chunk_without_embeddings_raises_error(self):
        """Test that from_chunk raises error when no embeddings available."""
        chunk = DocumentChunk(
            chunk_id="test_chunk",
            text="Test text",
        )

        with pytest.raises(ValueError) as exc_info:
            EmbeddedChunk.from_chunk(chunk)

        assert "without embeddings" in str(exc_info.value).lower()

    def test_to_vector_metadata(self):
        """Test converting EmbeddedChunk to vector metadata dict."""
        metadata = DocumentChunkMetadata(
            source=Source.PDF,
            document_id="doc_1",
            page_number=1,
            chunk_number=5,
        )
        chunk = EmbeddedChunk(
            chunk_id="test_chunk",
            text="Test text",
            embeddings=[0.1, 0.2],
            metadata=metadata,
            document_id="doc_1",
        )

        meta_dict = chunk.to_vector_metadata()

        assert meta_dict["chunk_id"] == "test_chunk"
        assert meta_dict["text"] == "Test text"
        assert meta_dict["document_id"] == "doc_1"
        assert meta_dict["source"] == Source.PDF
        assert meta_dict["page_number"] == 1
        assert meta_dict["chunk_number"] == 5
        # Check that None values are excluded
        assert "parent_chunk_id" not in meta_dict

    def test_to_vector_db(self):
        """Test converting EmbeddedChunk to vector DB format."""
        embeddings = [0.1, 0.2, 0.3]
        chunk = EmbeddedChunk(
            chunk_id="test_chunk",
            text="Test text",
            embeddings=embeddings,
            document_id="doc_1",
        )

        db_format = chunk.to_vector_db()

        assert db_format["id"] == "test_chunk"
        assert db_format["vector"] == embeddings
        assert "metadata" in db_format
        assert db_format["metadata"]["chunk_id"] == "test_chunk"

    def test_embedded_chunk_with_hierarchical_data(self):
        """Test EmbeddedChunk with hierarchical chunking data."""
        chunk = EmbeddedChunk(
            chunk_id="parent_chunk",
            text="Parent text",
            embeddings=[0.1, 0.2],
            parent_chunk_id="root_chunk",
            child_chunk_ids=["child_1", "child_2"],
            level=1,
        )

        assert chunk.parent_chunk_id == "root_chunk"
        assert chunk.child_chunk_ids == ["child_1", "child_2"]
        assert chunk.level == 1


class TestDocumentIngestionRequest:
    """Tests for DocumentIngestionRequest model."""

    def test_ingestion_request_creation(self):
        """Test creating a valid DocumentIngestionRequest."""
        chunks = [
            DocumentChunk(chunk_id="1", text="Text 1", embeddings=[0.1]),
            DocumentChunk(chunk_id="2", text="Text 2", embeddings=[0.2]),
        ]

        request = DocumentIngestionRequest(
            chunks=chunks,
            collection_id="test_collection",
        )

        assert len(request.chunks) == 2
        assert request.collection_id == "test_collection"
        assert request.batch_size == 100  # Default

    def test_ingestion_request_custom_batch_size(self):
        """Test DocumentIngestionRequest with custom batch size."""
        chunks = [DocumentChunk(chunk_id="1", text="Text 1")]

        request = DocumentIngestionRequest(
            chunks=chunks,
            collection_id="test_collection",
            batch_size=50,
        )

        assert request.batch_size == 50

    def test_ingestion_request_rejects_empty_chunks(self):
        """Test that empty chunks list is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DocumentIngestionRequest(
                chunks=[],
                collection_id="test_collection",
            )

        assert "empty" in str(exc_info.value).lower()

    def test_ingestion_request_validates_batch_size(self):
        """Test that batch_size is validated."""
        chunks = [DocumentChunk(chunk_id="1", text="Text 1")]

        # Batch size too small
        with pytest.raises(ValidationError):
            DocumentIngestionRequest(
                chunks=chunks,
                collection_id="test_collection",
                batch_size=0,
            )

        # Batch size too large
        with pytest.raises(ValidationError):
            DocumentIngestionRequest(
                chunks=chunks,
                collection_id="test_collection",
                batch_size=2000,
            )

    def test_get_embedded_chunks(self):
        """Test extracting embedded chunks from request."""
        chunks = [
            DocumentChunk(chunk_id="1", text="Text 1", embeddings=[0.1, 0.2]),
            DocumentChunk(chunk_id="2", text="Text 2"),  # No embeddings
            DocumentChunk(chunk_id="3", text="Text 3", embeddings=[0.3, 0.4]),
        ]

        request = DocumentIngestionRequest(
            chunks=chunks,
            collection_id="test_collection",
        )

        embedded = request.get_embedded_chunks()

        assert len(embedded) == 2
        assert all(isinstance(c, EmbeddedChunk) for c in embedded)
        assert embedded[0].chunk_id == "1"
        assert embedded[1].chunk_id == "3"

    def test_get_batches(self):
        """Test splitting chunks into batches."""
        chunks = [DocumentChunk(chunk_id=str(i), text=f"Text {i}") for i in range(250)]

        request = DocumentIngestionRequest(
            chunks=chunks,
            collection_id="test_collection",
            batch_size=100,
        )

        batches = request.get_batches()

        assert len(batches) == 3
        assert len(batches[0]) == 100
        assert len(batches[1]) == 100
        assert len(batches[2]) == 50

    def test_get_batches_exact_division(self):
        """Test batching when total chunks divides evenly."""
        chunks = [DocumentChunk(chunk_id=str(i), text=f"Text {i}") for i in range(200)]

        request = DocumentIngestionRequest(
            chunks=chunks,
            collection_id="test_collection",
            batch_size=50,
        )

        batches = request.get_batches()

        assert len(batches) == 4
        assert all(len(b) == 50 for b in batches)


class TestVectorSearchRequest:
    """Tests for VectorSearchRequest model."""

    def test_search_request_with_text_query(self):
        """Test creating search request with text query."""
        request = VectorSearchRequest(
            query_text="What is machine learning?",
            collection_id="test_collection",
        )

        assert request.query_text == "What is machine learning?"
        assert request.query_vector is None
        assert request.collection_id == "test_collection"
        assert request.top_k == 10  # Default

    def test_search_request_with_vector_query(self):
        """Test creating search request with vector query."""
        vector = [0.1, 0.2, 0.3, 0.4]
        request = VectorSearchRequest(
            query_vector=vector,
            collection_id="test_collection",
            top_k=5,
        )

        assert request.query_vector == vector
        assert request.query_text is None
        assert request.top_k == 5

    def test_search_request_with_both_queries(self):
        """Test search request with both text and vector."""
        request = VectorSearchRequest(
            query_text="Test query",
            query_vector=[0.1, 0.2],
            collection_id="test_collection",
        )

        assert request.query_text == "Test query"
        assert request.query_vector == [0.1, 0.2]

    def test_search_request_requires_at_least_one_query(self):
        """Test that at least one query type is required."""
        with pytest.raises(ValidationError) as exc_info:
            VectorSearchRequest(
                collection_id="test_collection",
            )

        assert "query" in str(exc_info.value).lower()

    def test_search_request_validates_top_k(self):
        """Test that top_k is validated."""
        # Too small
        with pytest.raises(ValidationError):
            VectorSearchRequest(
                query_text="test",
                collection_id="test_collection",
                top_k=0,
            )

        # Too large
        with pytest.raises(ValidationError):
            VectorSearchRequest(
                query_text="test",
                collection_id="test_collection",
                top_k=200,
            )

    def test_search_request_with_metadata_filter(self):
        """Test search request with metadata filter."""
        from vectordbs.data_types import DocumentMetadataFilter

        metadata_filter = DocumentMetadataFilter(
            field_name="source",
            operator="eq",
            value="pdf",
        )

        request = VectorSearchRequest(
            query_text="test",
            collection_id="test_collection",
            metadata_filter=metadata_filter,
        )

        assert request.metadata_filter is not None
        assert request.metadata_filter.field_name == "source"

    def test_search_request_flags(self):
        """Test include_metadata and include_vectors flags."""
        request = VectorSearchRequest(
            query_text="test",
            collection_id="test_collection",
            include_metadata=False,
            include_vectors=True,
        )

        assert request.include_metadata is False
        assert request.include_vectors is True

    def test_to_vector_query(self):
        """Test converting to VectorQuery for backward compatibility."""
        request = VectorSearchRequest(
            query_text="test query",
            query_vector=[0.1, 0.2],
            collection_id="test_collection",
            top_k=5,
        )

        vector_query = request.to_vector_query()

        assert vector_query.text == "test query"
        assert vector_query.embeddings == [0.1, 0.2]
        assert vector_query.number_of_results == 5


class TestCollectionConfig:
    """Tests for CollectionConfig model."""

    def test_collection_config_creation(self):
        """Test creating a valid CollectionConfig."""
        config = CollectionConfig(
            collection_name="test_collection",
            dimension=768,
        )

        assert config.collection_name == "test_collection"
        assert config.dimension == 768
        assert config.metric_type == "L2"  # Default
        assert config.index_type == "HNSW"  # Default

    def test_collection_config_with_all_fields(self):
        """Test CollectionConfig with all fields specified."""
        config = CollectionConfig(
            collection_name="test_collection",
            dimension=1536,
            metric_type="COSINE",
            index_type="IVF_FLAT",
            index_params={"nlist": 1024},
            description="Test collection for unit tests",
        )

        assert config.metric_type == "COSINE"
        assert config.index_type == "IVF_FLAT"
        assert config.index_params == {"nlist": 1024}
        assert config.description == "Test collection for unit tests"

    def test_collection_config_validates_name_length(self):
        """Test that collection name length is validated."""
        # Empty name
        with pytest.raises(ValidationError):
            CollectionConfig(
                collection_name="",
                dimension=768,
            )

        # Name too long
        with pytest.raises(ValidationError):
            CollectionConfig(
                collection_name="a" * 300,
                dimension=768,
            )

    def test_collection_config_validates_dimension(self):
        """Test that dimension is validated."""
        # Too small
        with pytest.raises(ValidationError):
            CollectionConfig(
                collection_name="test",
                dimension=0,
            )

        # Too large
        with pytest.raises(ValidationError):
            CollectionConfig(
                collection_name="test",
                dimension=10000,
            )

    def test_collection_config_validates_metric_type(self):
        """Test that metric_type is validated."""
        with pytest.raises(ValidationError) as exc_info:
            CollectionConfig(
                collection_name="test",
                dimension=768,
                metric_type="INVALID_METRIC",
            )

        assert "Invalid metric_type" in str(exc_info.value)

    def test_collection_config_accepts_valid_metrics(self):
        """Test that all valid metric types are accepted."""
        valid_metrics = ["L2", "IP", "COSINE", "HAMMING", "JACCARD"]

        for metric in valid_metrics:
            config = CollectionConfig(
                collection_name="test",
                dimension=768,
                metric_type=metric,
            )
            assert config.metric_type == metric.upper()

    def test_collection_config_validates_index_type(self):
        """Test that index_type is validated."""
        with pytest.raises(ValidationError) as exc_info:
            CollectionConfig(
                collection_name="test",
                dimension=768,
                index_type="INVALID_INDEX",
            )

        assert "Invalid index_type" in str(exc_info.value)

    def test_collection_config_accepts_valid_indexes(self):
        """Test that all valid index types are accepted."""
        valid_indexes = ["FLAT", "IVF_FLAT", "IVF_SQ8", "IVF_PQ", "HNSW", "ANNOY"]

        for index in valid_indexes:
            config = CollectionConfig(
                collection_name="test",
                dimension=768,
                index_type=index,
            )
            assert config.index_type == index.upper()

    def test_collection_config_case_insensitive(self):
        """Test that metric and index types are case-insensitive."""
        config = CollectionConfig(
            collection_name="test",
            dimension=768,
            metric_type="cosine",
            index_type="hnsw",
        )

        assert config.metric_type == "COSINE"
        assert config.index_type == "HNSW"

    def test_to_dict(self):
        """Test converting CollectionConfig to dictionary."""
        config = CollectionConfig(
            collection_name="test_collection",
            dimension=768,
            metric_type="L2",
            index_type="HNSW",
            index_params={"M": 16, "efConstruction": 200},
        )

        config_dict = config.to_dict()

        assert config_dict["collection_name"] == "test_collection"
        assert config_dict["dimension"] == 768
        assert config_dict["metric_type"] == "L2"
        assert config_dict["index_type"] == "HNSW"
        assert config_dict["index_params"] == {"M": 16, "efConstruction": 200}


class TestVectorDBResponse:
    """Tests for VectorDBResponse model."""

    def test_create_success_response(self):
        """Test creating a success response."""
        data = ["id1", "id2", "id3"]
        response = VectorDBResponse.create_success(data)

        assert response.success is True
        assert response.data == data
        assert response.error is None
        assert response.metadata == {}

    def test_create_success_with_metadata(self):
        """Test creating success response with metadata."""
        data = ["id1", "id2"]
        metadata = {"count": 2, "time": "0.5s"}
        response = VectorDBResponse.create_success(data, metadata=metadata)

        assert response.success is True
        assert response.metadata == metadata

    def test_create_error_response(self):
        """Test creating an error response."""
        error_msg = "Database connection failed"
        response = VectorDBResponse.create_error(error_msg)

        assert response.success is False
        assert response.data is None
        assert response.error == error_msg

    def test_create_error_with_metadata(self):
        """Test creating error response with metadata."""
        error_msg = "Timeout"
        metadata = {"retry_count": 3}
        response = VectorDBResponse.create_error(error_msg, metadata=metadata)

        assert response.error == error_msg
        assert response.metadata == metadata

    def test_is_success(self):
        """Test is_success method."""
        success_response = VectorDBResponse.create_success([1, 2, 3])
        error_response = VectorDBResponse.create_error("error")

        assert success_response.is_success() is True
        assert error_response.is_success() is False

    def test_is_error(self):
        """Test is_error method."""
        success_response = VectorDBResponse.create_success([1, 2, 3])
        error_response = VectorDBResponse.create_error("error")

        assert success_response.is_error() is False
        assert error_response.is_error() is True

    def test_get_data_or_raise_success(self):
        """Test get_data_or_raise with success response."""
        data = ["id1", "id2"]
        response = VectorDBResponse.create_success(data)

        retrieved_data = response.get_data_or_raise()
        assert retrieved_data == data

    def test_get_data_or_raise_error(self):
        """Test get_data_or_raise with error response."""
        error_msg = "Database error"
        response = VectorDBResponse.create_error(error_msg)

        with pytest.raises(ValueError) as exc_info:
            response.get_data_or_raise()

        assert "Operation failed" in str(exc_info.value)
        assert error_msg in str(exc_info.value)

    def test_get_data_or_raise_no_data(self):
        """Test get_data_or_raise when data is None despite success."""
        response = VectorDBResponse(success=True, data=None)

        with pytest.raises(ValueError) as exc_info:
            response.get_data_or_raise()

        assert "No data available" in str(exc_info.value)


class TestVectorDBResponseTypeAliases:
    """Tests for VectorDBResponse type aliases."""

    def test_ingestion_response_type(self):
        """Test VectorDBIngestionResponse type alias."""
        ids = ["id1", "id2", "id3"]
        response: VectorDBIngestionResponse = VectorDBResponse.create_success(ids)

        assert response.success is True
        assert isinstance(response.data, list)

    def test_search_response_type(self):
        """Test VectorDBSearchResponse type alias."""
        results = [
            QueryResult(
                chunk=None,
                score=0.95,
            )
        ]
        response: VectorDBSearchResponse = VectorDBResponse.create_success(results)

        assert response.success is True
        assert isinstance(response.data, list)

    def test_collection_response_type(self):
        """Test VectorDBCollectionResponse type alias."""
        info = {"name": "test_collection", "dimension": 768}
        response: VectorDBCollectionResponse = VectorDBResponse.create_success(info)

        assert response.success is True
        assert isinstance(response.data, dict)

    def test_delete_response_type(self):
        """Test VectorDBDeleteResponse type alias."""
        response: VectorDBDeleteResponse = VectorDBResponse.create_success(True)

        assert response.success is True
        assert response.data is True


class TestPerformance:
    """Performance tests for data models."""

    def test_embedded_chunk_serialization_performance(self):
        """Test serialization performance for large batches."""
        import time

        # Create 1000 embedded chunks
        chunks = [
            EmbeddedChunk(
                chunk_id=f"chunk_{i}",
                text=f"This is test text for chunk {i}",
                embeddings=[float(j) for j in range(768)],
                document_id=f"doc_{i // 100}",
            )
            for i in range(1000)
        ]

        # Test serialization
        start = time.time()
        for chunk in chunks:
            _ = chunk.to_vector_db()
        elapsed = time.time() - start

        # Should complete in under 100ms for 1000 chunks
        assert elapsed < 0.1, f"Serialization took {elapsed:.3f}s (expected < 0.1s)"

    def test_ingestion_request_batching_performance(self):
        """Test batching performance for large datasets."""
        import time

        # Create 10,000 chunks
        chunks = [
            DocumentChunk(chunk_id=f"chunk_{i}", text=f"Text {i}")
            for i in range(10000)
        ]

        request = DocumentIngestionRequest(
            chunks=chunks,
            collection_id="test",
            batch_size=100,
        )

        # Test batching
        start = time.time()
        batches = request.get_batches()
        elapsed = time.time() - start

        assert len(batches) == 100
        # Should complete in under 10ms
        assert elapsed < 0.01, f"Batching took {elapsed:.3f}s (expected < 0.01s)"
