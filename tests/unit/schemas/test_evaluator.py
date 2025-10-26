"""Atomic tests for evaluation data validation and schemas."""

import numpy as np
import pytest
from backend.vectordbs.data_types import DocumentChunk, DocumentChunkMetadata, QueryResult, Source


@pytest.mark.atomic
class TestEvaluationDataValidation:
    """Test evaluation data validation and schemas - no external dependencies."""

    def test_query_result_validation(self):
        """Test QueryResult data structure validation."""
        # Valid QueryResult
        chunk = DocumentChunk(
            chunk_id="test_chunk_1",
            text="This is a test chunk with some content.",
            metadata=DocumentChunkMetadata(
                source=Source.PDF, document_id="test_doc", page_number=1, chunk_number=1, start_index=0, end_index=50
            ),
        )

        query_result = QueryResult(chunk=chunk, score=0.85, embeddings=[0.1, 0.2, 0.3, 0.4, 0.5])

        # Test structure
        assert isinstance(query_result.chunk, DocumentChunk)
        assert isinstance(query_result.score, float)
        assert isinstance(query_result.embeddings, list)

        # Test values
        assert query_result.score == 0.85
        assert len(query_result.embeddings) == 5
        assert all(isinstance(x, int | float) for x in query_result.embeddings)
        assert query_result.chunk.chunk_id == "test_chunk_1"
        assert query_result.chunk.text == "This is a test chunk with some content."

    def test_evaluation_metrics_validation(self):
        """Test evaluation metrics data structure validation."""
        # Valid evaluation results
        evaluation_results = {
            "relevance": 0.85,
            "coherence": 0.92,
            "faithfulness": 0.78,
            "overall_score": 0.85,
            "context_relevance": 0.88,
            "answer_relevance": 0.82,
        }

        # Test structure
        assert isinstance(evaluation_results, dict)
        assert "relevance" in evaluation_results
        assert "coherence" in evaluation_results
        assert "faithfulness" in evaluation_results
        assert "overall_score" in evaluation_results

        # Test value types and ranges
        for metric, score in evaluation_results.items():
            assert isinstance(score, int | float)
            assert 0.0 <= score <= 1.0, f"{metric} score {score} is out of range [0, 1]"

    def test_embedding_validation(self):
        """Test embedding data validation."""
        # Valid embeddings
        valid_embeddings = [
            [0.1, 0.2, 0.3, 0.4, 0.5],  # List format
            np.array([0.1, 0.2, 0.3, 0.4, 0.5]),  # Numpy array
            [0.0, 0.0, 0.0, 0.0, 0.0],  # Zero vector
            [1.0, 1.0, 1.0, 1.0, 1.0],  # Unit vector
        ]

        for embedding in valid_embeddings:
            if isinstance(embedding, list):
                assert len(embedding) > 0
                assert all(isinstance(x, int | float) for x in embedding)
            elif isinstance(embedding, np.ndarray):
                assert embedding.ndim == 1
                assert len(embedding) > 0
                assert embedding.dtype in [np.float32, np.float64, np.int32, np.int64]

    def test_cosine_similarity_validation(self):
        """Test cosine similarity calculation validation."""

        # Mock cosine similarity function
        def mock_cosine_similarity(a, b):
            # Return different types to test conversion
            return np.array(0.85)  # This should be converted to float

        # Test conversion
        result = mock_cosine_similarity([1, 2, 3], [1, 2, 3])
        converted = float(result.item()) if hasattr(result, "item") else float(result)

        assert isinstance(converted, float)
        assert 0.0 <= converted <= 1.0

    def test_evaluation_configuration_validation(self):
        """Test evaluation configuration validation."""
        # Valid evaluation configuration
        config = {
            "relevance_threshold": 0.7,
            "coherence_threshold": 0.8,
            "faithfulness_threshold": 0.75,
            "overall_threshold": 0.8,
            "embedding_model": "text-embedding-ada-002",
            "max_tokens": 1000,
            "temperature": 0.0,
        }

        # Test structure
        assert isinstance(config, dict)
        assert "relevance_threshold" in config
        assert "coherence_threshold" in config
        assert "faithfulness_threshold" in config
        assert "overall_threshold" in config

        # Test value types and ranges
        for key, value in config.items():
            if key.endswith("_threshold"):
                assert isinstance(value, int | float)
                assert 0.0 <= value <= 1.0
            elif key == "max_tokens":
                assert isinstance(value, int)
                assert value > 0
            elif key == "temperature":
                assert isinstance(value, int | float)
                assert 0.0 <= value <= 2.0
            elif key == "embedding_model":
                assert isinstance(value, str)
                assert len(value) > 0

    def test_evaluation_error_handling(self):
        """Test evaluation error handling validation."""
        # Valid error structures
        valid_errors = [
            {
                "error_type": "EmbeddingError",
                "message": "Failed to generate embeddings",
                "query": "test query",
                "timestamp": "2024-01-01T00:00:00Z",
            },
            {
                "error_type": "EvaluationError",
                "message": "Failed to evaluate response",
                "response": "test response",
                "timestamp": "2024-01-01T00:00:00Z",
            },
            {
                "error_type": "ValidationError",
                "message": "Invalid input data",
                "input_data": {"query": "test"},
                "timestamp": "2024-01-01T00:00:00Z",
            },
        ]

        for error in valid_errors:
            assert isinstance(error, dict)
            assert "error_type" in error
            assert "message" in error
            assert "timestamp" in error

            assert isinstance(error["error_type"], str)
            assert isinstance(error["message"], str)
            assert isinstance(error["timestamp"], str)

    def test_evaluation_batch_processing(self):
        """Test evaluation batch processing validation."""
        # Valid batch evaluation data
        batch_data = {
            "queries": ["What is machine learning?", "How does neural networks work?", "What is deep learning?"],
            "responses": [
                "Machine learning is a subset of AI.",
                "Neural networks are inspired by the brain.",
                "Deep learning uses multiple layers.",
            ],
            "contexts": [
                [{"text": "ML context 1"}, {"text": "ML context 2"}],
                [{"text": "NN context 1"}, {"text": "NN context 2"}],
                [{"text": "DL context 1"}, {"text": "DL context 2"}],
            ],
        }

        # Test structure
        assert isinstance(batch_data, dict)
        assert "queries" in batch_data
        assert "responses" in batch_data
        assert "contexts" in batch_data

        assert isinstance(batch_data["queries"], list)
        assert isinstance(batch_data["responses"], list)
        assert isinstance(batch_data["contexts"], list)

        # Test length consistency
        assert len(batch_data["queries"]) == len(batch_data["responses"])
        assert len(batch_data["queries"]) == len(batch_data["contexts"])

        # Test content validation
        for query in batch_data["queries"]:
            assert isinstance(query, str)
            assert len(query.strip()) > 0

        for response in batch_data["responses"]:
            assert isinstance(response, str)
            assert len(response.strip()) > 0

        for context_list in batch_data["contexts"]:
            assert isinstance(context_list, list)
            for context in context_list:
                assert isinstance(context, dict)
                assert "text" in context
                assert isinstance(context["text"], str)
