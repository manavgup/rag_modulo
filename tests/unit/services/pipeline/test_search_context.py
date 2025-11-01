"""
Unit tests for SearchContext dataclass.

Tests the search context functionality including:
- Context initialization
- Data accumulation
- Execution time tracking
- Metadata management
"""

import time
from uuid import uuid4

import pytest

from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.pipeline.search_context import SearchContext
from vectordbs.data_types import DocumentMetadata, QueryResult


@pytest.fixture
def mock_search_input() -> SearchInput:
    """Create mock search input."""
    return SearchInput(user_id=uuid4(), collection_id=uuid4(), question="Test question?")


@pytest.mark.unit
class TestSearchContext:
    """Test suite for SearchContext dataclass."""

    def test_context_initialization(self, mock_search_input: SearchInput) -> None:
        """Test that context initializes with correct default values."""
        context = SearchContext(
            search_input=mock_search_input,
            user_id=mock_search_input.user_id,
            collection_id=mock_search_input.collection_id,
        )

        assert context.search_input == mock_search_input
        assert context.user_id == mock_search_input.user_id
        assert context.collection_id == mock_search_input.collection_id
        assert context.pipeline_id is None
        assert context.collection_name is None
        assert context.query_results == []
        assert context.rewritten_query is None
        assert context.document_metadata == []
        assert context.generated_answer == ""
        assert context.evaluation is None
        assert context.cot_output is None
        assert context.token_warning is None
        assert context.execution_time == 0.0
        assert context.metadata == {}
        assert context.errors == []

    def test_execution_time_tracking(self, mock_search_input: SearchInput) -> None:
        """Test execution time tracking."""
        context = SearchContext(
            search_input=mock_search_input,
            user_id=mock_search_input.user_id,
            collection_id=mock_search_input.collection_id,
        )

        # Simulate some processing time
        time.sleep(0.1)
        context.update_execution_time()

        assert context.execution_time > 0.0
        assert context.execution_time >= 0.1

    def test_add_error(self, mock_search_input: SearchInput) -> None:
        """Test adding errors to context."""
        context = SearchContext(
            search_input=mock_search_input,
            user_id=mock_search_input.user_id,
            collection_id=mock_search_input.collection_id,
        )

        context.add_error("Error 1")
        context.add_error("Error 2")

        assert len(context.errors) == 2
        assert "Error 1" in context.errors
        assert "Error 2" in context.errors

    def test_add_metadata(self, mock_search_input: SearchInput) -> None:
        """Test adding metadata to context."""
        context = SearchContext(
            search_input=mock_search_input,
            user_id=mock_search_input.user_id,
            collection_id=mock_search_input.collection_id,
        )

        context.add_metadata("key1", "value1")
        context.add_metadata("key2", 42)
        context.add_metadata("key3", {"nested": "data"})

        assert context.metadata["key1"] == "value1"
        assert context.metadata["key2"] == 42
        assert context.metadata["key3"] == {"nested": "data"}

    def test_context_with_query_results(self, mock_search_input: SearchInput) -> None:
        """Test context with query results."""
        context = SearchContext(
            search_input=mock_search_input,
            user_id=mock_search_input.user_id,
            collection_id=mock_search_input.collection_id,
        )

        # Create a simple mock QueryResult
        # We just need to verify the list can hold QueryResult objects
        from unittest.mock import MagicMock

        mock_result = MagicMock(spec=QueryResult)
        mock_result.chunk_id = "chunk1"
        mock_result.document_id = "doc1"
        mock_result.collection_id = "col1"
        mock_result.score = 0.95

        context.query_results = [mock_result]
        assert len(context.query_results) == 1
        assert context.query_results[0].chunk_id == "chunk1"

    def test_context_with_document_metadata(self, mock_search_input: SearchInput) -> None:
        """Test context with document metadata."""
        context = SearchContext(
            search_input=mock_search_input,
            user_id=mock_search_input.user_id,
            collection_id=mock_search_input.collection_id,
        )

        metadata = DocumentMetadata(document_name="test.pdf", total_pages=10, total_chunks=50)
        context.document_metadata = [metadata]

        assert len(context.document_metadata) == 1
        assert context.document_metadata[0].document_name == "test.pdf"

    def test_context_pipeline_configuration(self, mock_search_input: SearchInput) -> None:
        """Test context pipeline configuration fields."""
        pipeline_id = uuid4()
        context = SearchContext(
            search_input=mock_search_input,
            user_id=mock_search_input.user_id,
            collection_id=mock_search_input.collection_id,
            pipeline_id=pipeline_id,
            collection_name="test_collection",
        )

        assert context.pipeline_id == pipeline_id
        assert context.collection_name == "test_collection"

    def test_context_generation_results(self, mock_search_input: SearchInput) -> None:
        """Test context generation result fields."""
        context = SearchContext(
            search_input=mock_search_input,
            user_id=mock_search_input.user_id,
            collection_id=mock_search_input.collection_id,
        )

        context.generated_answer = "Generated answer text"
        context.rewritten_query = "Rewritten query"
        context.evaluation = {"relevance": 0.9}

        assert context.generated_answer == "Generated answer text"
        assert context.rewritten_query == "Rewritten query"
        assert context.evaluation == {"relevance": 0.9}
