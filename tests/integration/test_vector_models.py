"""Integration tests for vector database models with real data flow."""

import pytest

from vectordbs.data_types import (
    CollectionConfig,
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentIngestionRequest,
    EmbeddedChunk,
    QueryResult,
    Source,
    VectorDBIngestionResponse,
    VectorDBSearchResponse,
    VectorSearchRequest,
)


@pytest.mark.integration
class TestEmbeddedChunkIntegration:
    """Integration tests for EmbeddedChunk in real scenarios."""

    def test_document_processing_to_embedded_chunks(self):
        """Test converting processed documents to embedded chunks."""
        # Simulate document processing pipeline
        metadata = DocumentChunkMetadata(
            source=Source.PDF,
            document_id="doc_123",
            page_number=1,
            chunk_number=1,
        )

        chunk = DocumentChunk(
            chunk_id="chunk_001",
            text="This is a sample document chunk.",
            metadata=metadata,
            document_id="doc_123",
        )

        # Simulate embedding generation
        embeddings = [float(i) * 0.01 for i in range(768)]
        embedded_chunk = EmbeddedChunk.from_chunk(chunk, embeddings=embeddings)

        # Verify the embedded chunk is ready for vector DB
        vector_db_format = embedded_chunk.to_vector_db()
        assert vector_db_format["id"] == "chunk_001"
        assert len(vector_db_format["vector"]) == 768
        assert "metadata" in vector_db_format
        assert vector_db_format["metadata"]["source"] == Source.PDF

    def test_batch_processing_with_embedded_chunks(self):
        """Test batch processing of multiple embedded chunks."""
        # Create multiple chunks as they would come from document processing
        chunks = []
        for i in range(100):
            metadata = DocumentChunkMetadata(
                source=Source.PDF,
                document_id=f"doc_{i // 10}",
                page_number=i // 10 + 1,
                chunk_number=i % 10,
            )
            chunk = DocumentChunk(
                chunk_id=f"chunk_{i:03d}",
                text=f"Content of chunk {i}",
                embeddings=[float(j) * 0.01 for j in range(384)],
                metadata=metadata,
                document_id=f"doc_{i // 10}",
            )
            chunks.append(chunk)

        # Create ingestion request
        request = DocumentIngestionRequest(
            chunks=chunks,
            collection_id="test_collection",
            batch_size=25,
        )

        # Get embedded chunks
        embedded_chunks = request.get_embedded_chunks()
        assert len(embedded_chunks) == 100

        # Verify batching
        batches = request.get_batches()
        assert len(batches) == 4
        assert all(len(batch) == 25 for batch in batches)

        # Verify each batch can be converted to vector DB format
        for batch in batches:
            for chunk in batch:
                if chunk.embeddings:
                    embedded = EmbeddedChunk.from_chunk(chunk)
                    db_format = embedded.to_vector_db()
                    assert "id" in db_format
                    assert "vector" in db_format
                    assert "metadata" in db_format


@pytest.mark.integration
class TestDocumentIngestionRequestIntegration:
    """Integration tests for document ingestion workflow."""

    def test_end_to_end_ingestion_workflow(self):
        """Test complete ingestion workflow from chunks to response."""
        # Step 1: Create chunks (simulating document processing)
        chunks = []
        for i in range(50):
            chunk = DocumentChunk(
                chunk_id=f"chunk_{i}",
                text=f"Content of chunk {i}",
                embeddings=[float(j) * 0.01 for j in range(768)],
                document_id=f"doc_{i // 10}",
            )
            chunks.append(chunk)

        # Step 2: Create ingestion request
        request = DocumentIngestionRequest(
            chunks=chunks,
            collection_id="integration_test_collection",
            batch_size=10,
        )

        # Step 3: Process in batches (simulating vector DB ingestion)
        ingested_ids = []
        batches = request.get_batches()

        for batch in batches:
            for chunk in batch:
                if chunk.embeddings:
                    embedded = EmbeddedChunk.from_chunk(chunk)
                    db_format = embedded.to_vector_db()
                    # Simulate successful ingestion
                    ingested_ids.append(db_format["id"])

        # Step 4: Create response
        response: VectorDBIngestionResponse = VectorDBIngestionResponse.create_success(
            data=ingested_ids,
            metadata={"total_ingested": len(ingested_ids), "batches": len(batches)},
        )

        # Verify
        assert response.is_success()
        assert len(response.data) == 50
        assert response.metadata["batches"] == 5

    def test_ingestion_with_mixed_chunks(self):
        """Test ingestion with chunks that have and don't have embeddings."""
        chunks = [
            DocumentChunk(chunk_id="1", text="Text 1", embeddings=[0.1, 0.2]),
            DocumentChunk(chunk_id="2", text="Text 2"),  # No embeddings
            DocumentChunk(chunk_id="3", text="Text 3", embeddings=[0.3, 0.4]),
            DocumentChunk(chunk_id="4", text="Text 4"),  # No embeddings
        ]

        request = DocumentIngestionRequest(
            chunks=chunks,
            collection_id="test_collection",
        )

        # Only chunks with embeddings should be ingested
        embedded_chunks = request.get_embedded_chunks()
        assert len(embedded_chunks) == 2
        assert embedded_chunks[0].chunk_id == "1"
        assert embedded_chunks[1].chunk_id == "3"


@pytest.mark.integration
class TestVectorSearchRequestIntegration:
    """Integration tests for vector search workflow."""

    def test_text_search_workflow(self):
        """Test text-based search workflow."""
        # Step 1: Create search request
        request = VectorSearchRequest(
            query_text="What is machine learning?",
            collection_id="ml_documents",
            top_k=10,
            include_metadata=True,
            include_vectors=False,
        )

        # Step 2: Convert to VectorQuery for backward compatibility
        vector_query = request.to_vector_query()
        assert vector_query.text == "What is machine learning?"
        assert vector_query.number_of_results == 10

        # Step 3: Simulate search results
        results = []
        for i in range(10):
            chunk = DocumentChunk(
                chunk_id=f"result_{i}",
                text=f"Result text {i}",
                embeddings=[float(j) * 0.01 for j in range(768)],
            )
            result = QueryResult(chunk=chunk, score=0.9 - i * 0.05)
            results.append(result)

        # Step 4: Create response
        response: VectorDBSearchResponse = VectorDBSearchResponse.create_success(
            data=results,
            metadata={"query_time": "0.05s", "total_found": 100},
        )

        # Verify
        assert response.is_success()
        assert len(response.data) == 10
        assert response.data[0].score == 0.9

    def test_vector_search_workflow(self):
        """Test vector-based search workflow."""
        # Step 1: Pre-computed query vector
        query_vector = [float(i) * 0.01 for i in range(768)]

        request = VectorSearchRequest(
            query_vector=query_vector,
            collection_id="documents",
            top_k=5,
        )

        # Step 2: Verify request structure
        assert request.query_vector == query_vector
        assert request.top_k == 5

        # Step 3: Convert to VectorQuery
        vector_query = request.to_vector_query()
        assert vector_query.embeddings == query_vector

    def test_search_with_metadata_filter(self):
        """Test search with metadata filtering."""
        from vectordbs.data_types import DocumentMetadataFilter

        metadata_filter = DocumentMetadataFilter(
            field_name="document_type",
            operator="eq",
            value="technical_doc",
        )

        request = VectorSearchRequest(
            query_text="API documentation",
            collection_id="documents",
            top_k=20,
            metadata_filter=metadata_filter,
        )

        # Verify filter is included
        assert request.metadata_filter is not None
        vector_query = request.to_vector_query()
        assert vector_query.metadata_filter is not None


@pytest.mark.integration
class TestCollectionConfigIntegration:
    """Integration tests for collection configuration."""

    def test_collection_creation_workflow(self):
        """Test complete collection creation workflow."""
        # Step 1: Create configuration
        config = CollectionConfig(
            collection_name="embeddings_768",
            dimension=768,
            metric_type="COSINE",
            index_type="HNSW",
            index_params={
                "M": 16,
                "efConstruction": 200,
            },
            description="OpenAI embeddings collection",
        )

        # Step 2: Convert to dict for vector DB
        config_dict = config.to_dict()

        # Verify structure
        assert config_dict["collection_name"] == "embeddings_768"
        assert config_dict["dimension"] == 768
        assert config_dict["metric_type"] == "COSINE"
        assert config_dict["index_params"]["M"] == 16

        # Step 3: Simulate successful creation
        from vectordbs.data_types import VectorDBCollectionResponse

        response: VectorDBCollectionResponse = VectorDBCollectionResponse.create_success(
            data=config_dict,
            metadata={"created_at": "2025-11-06T10:00:00Z"},
        )

        assert response.is_success()
        assert response.data["collection_name"] == "embeddings_768"

    def test_multiple_collection_configurations(self):
        """Test creating configurations for different embedding models."""
        configs = [
            CollectionConfig(
                collection_name="openai_embeddings",
                dimension=1536,
                metric_type="COSINE",
                index_type="HNSW",
            ),
            CollectionConfig(
                collection_name="sentence_transformers",
                dimension=384,
                metric_type="L2",
                index_type="IVF_FLAT",
                index_params={"nlist": 1024},
            ),
            CollectionConfig(
                collection_name="custom_embeddings",
                dimension=768,
                metric_type="IP",
                index_type="FLAT",
            ),
        ]

        # Verify all configs are valid
        for config in configs:
            config_dict = config.to_dict()
            assert "collection_name" in config_dict
            assert "dimension" in config_dict
            assert config_dict["dimension"] in [384, 768, 1536]


@pytest.mark.integration
class TestVectorDBResponseIntegration:
    """Integration tests for response handling."""

    def test_successful_operation_chain(self):
        """Test chaining multiple successful operations."""
        # Operation 1: Ingestion
        ingestion_response = VectorDBIngestionResponse.create_success(
            data=["id1", "id2", "id3"],
            metadata={"time": "0.5s"},
        )

        assert ingestion_response.is_success()
        ingested_ids = ingestion_response.get_data_or_raise()

        # Operation 2: Search using ingested data
        search_response = VectorDBSearchResponse.create_success(
            data=[],
            metadata={"searched_ids": ingested_ids},
        )

        assert search_response.is_success()

    def test_error_handling_workflow(self):
        """Test error handling in operations."""
        # Operation fails
        error_response = VectorDBIngestionResponse.create_error(
            error="Connection timeout",
            metadata={"retry_count": 3, "last_attempt": "2025-11-06T10:00:00Z"},
        )

        assert error_response.is_error()
        assert not error_response.is_success()

        # Verify error can be retrieved
        with pytest.raises(ValueError) as exc_info:
            error_response.get_data_or_raise()

        assert "Connection timeout" in str(exc_info.value)

    def test_mixed_success_error_workflow(self):
        """Test handling mix of success and error responses."""
        responses = [
            VectorDBIngestionResponse.create_success(["id1", "id2"]),
            VectorDBIngestionResponse.create_error("Batch 2 failed"),
            VectorDBIngestionResponse.create_success(["id3"]),
        ]

        successful_ids = []
        errors = []

        for response in responses:
            if response.is_success():
                successful_ids.extend(response.data)
            else:
                errors.append(response.error)

        assert len(successful_ids) == 3
        assert len(errors) == 1
        assert errors[0] == "Batch 2 failed"


@pytest.mark.integration
class TestRoundTripSerialization:
    """Integration tests for round-trip serialization."""

    def test_embedded_chunk_serialization_round_trip(self):
        """Test that embedded chunks can be serialized and deserialized."""
        original = EmbeddedChunk(
            chunk_id="test_chunk",
            text="Test text",
            embeddings=[0.1, 0.2, 0.3],
            document_id="doc_1",
        )

        # Serialize to dict
        chunk_dict = original.model_dump()

        # Deserialize
        restored = EmbeddedChunk.model_validate(chunk_dict)

        assert restored.chunk_id == original.chunk_id
        assert restored.text == original.text
        assert restored.embeddings == original.embeddings

    def test_ingestion_request_json_round_trip(self):
        """Test JSON serialization round-trip for ingestion request."""
        chunks = [
            DocumentChunk(chunk_id="1", text="Text 1", embeddings=[0.1, 0.2]),
            DocumentChunk(chunk_id="2", text="Text 2", embeddings=[0.3, 0.4]),
        ]

        original = DocumentIngestionRequest(
            chunks=chunks,
            collection_id="test_collection",
            batch_size=50,
        )

        # Serialize to JSON
        json_str = original.model_dump_json()

        # Deserialize
        restored = DocumentIngestionRequest.model_validate_json(json_str)

        assert len(restored.chunks) == len(original.chunks)
        assert restored.collection_id == original.collection_id
        assert restored.batch_size == original.batch_size

    def test_collection_config_json_round_trip(self):
        """Test JSON serialization round-trip for collection config."""
        original = CollectionConfig(
            collection_name="test",
            dimension=768,
            metric_type="COSINE",
            index_type="HNSW",
            index_params={"M": 16},
        )

        # Serialize to JSON
        json_str = original.model_dump_json()

        # Deserialize
        restored = CollectionConfig.model_validate_json(json_str)

        assert restored.collection_name == original.collection_name
        assert restored.dimension == original.dimension
        assert restored.index_params == original.index_params
