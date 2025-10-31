"""
Unit tests for QueryEnhancementStage.

Tests the query enhancement functionality including:
- Query cleaning and preparation
- Query rewriting
- Error handling
"""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.pipeline.search_context import SearchContext
from rag_solution.services.pipeline.stages.query_enhancement_stage import QueryEnhancementStage


@pytest.fixture
def mock_pipeline_service() -> Mock:
    """Create mock pipeline service."""
    service = Mock()
    service._prepare_query = Mock(side_effect=lambda x: x.strip().lower())
    service.query_rewriter = Mock()
    service.query_rewriter.rewrite = Mock(side_effect=lambda x: f"enhanced {x}")
    return service


@pytest.fixture
def search_context() -> SearchContext:
    """Create search context for testing."""
    user_id = uuid4()
    collection_id = uuid4()
    search_input = SearchInput(user_id=user_id, collection_id=collection_id, question="  What is ML?  ")
    return SearchContext(search_input=search_input, user_id=user_id, collection_id=collection_id)


@pytest.mark.unit
@pytest.mark.asyncio
class TestQueryEnhancementStage:
    """Test suite for QueryEnhancementStage."""

    async def test_stage_initialization(self, mock_pipeline_service: Mock) -> None:
        """Test that stage initializes correctly."""
        stage = QueryEnhancementStage(mock_pipeline_service)
        assert stage.stage_name == "QueryEnhancement"
        assert stage.pipeline_service == mock_pipeline_service

    async def test_successful_query_enhancement(
        self, mock_pipeline_service: Mock, search_context: SearchContext
    ) -> None:
        """Test successful query enhancement."""
        stage = QueryEnhancementStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is True
        assert result.context.rewritten_query == "enhanced what is ml?"
        assert "query_enhancement" in result.context.metadata
        assert result.context.metadata["query_enhancement"]["original_query"] == "  What is ML?  "
        assert result.context.metadata["query_enhancement"]["clean_query"] == "what is ml?"
        assert result.context.metadata["query_enhancement"]["rewritten_query"] == "enhanced what is ml?"

        mock_pipeline_service._prepare_query.assert_called_once_with("  What is ML?  ")
        mock_pipeline_service.query_rewriter.rewrite.assert_called_once_with("what is ml?")

    async def test_query_preparation(self, mock_pipeline_service: Mock, search_context: SearchContext) -> None:
        """Test query preparation."""
        stage = QueryEnhancementStage(mock_pipeline_service)
        clean_query = stage._prepare_query("  Test Query  ")

        assert clean_query == "test query"
        mock_pipeline_service._prepare_query.assert_called_once_with("  Test Query  ")

    async def test_query_rewriting(self, mock_pipeline_service: Mock, search_context: SearchContext) -> None:
        """Test query rewriting."""
        stage = QueryEnhancementStage(mock_pipeline_service)
        rewritten = stage._rewrite_query("test query")

        assert rewritten == "enhanced test query"
        mock_pipeline_service.query_rewriter.rewrite.assert_called_once_with("test query")

    async def test_error_during_preparation(self, mock_pipeline_service: Mock, search_context: SearchContext) -> None:
        """Test error handling during query preparation."""
        mock_pipeline_service._prepare_query.side_effect = ValueError("Preparation failed")

        stage = QueryEnhancementStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is False
        assert "preparation failed" in result.error.lower()

    async def test_error_during_rewriting(self, mock_pipeline_service: Mock, search_context: SearchContext) -> None:
        """Test error handling during query rewriting."""
        mock_pipeline_service.query_rewriter.rewrite.side_effect = ValueError("Rewriting failed")

        stage = QueryEnhancementStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is False
        assert "rewriting failed" in result.error.lower()

    async def test_empty_query(self) -> None:
        """Test handling of empty query."""
        user_id = uuid4()
        collection_id = uuid4()
        search_input = SearchInput(user_id=user_id, collection_id=collection_id, question="")
        context = SearchContext(search_input=search_input, user_id=user_id, collection_id=collection_id)

        # Create fresh mock with empty string behavior
        service = Mock()
        service._prepare_query = Mock(return_value="")
        service.query_rewriter = Mock()
        service.query_rewriter.rewrite = Mock(return_value="")

        stage = QueryEnhancementStage(service)
        result = await stage.execute(context)

        # Should succeed even with empty query
        assert result.success is True
        assert result.context.rewritten_query == ""

    async def test_special_characters_in_query(self) -> None:
        """Test handling of special characters."""
        user_id = uuid4()
        collection_id = uuid4()
        search_input = SearchInput(user_id=user_id, collection_id=collection_id, question="What is @#$ ML?!?")
        context = SearchContext(search_input=search_input, user_id=user_id, collection_id=collection_id)

        # Create fresh mock with custom behavior
        service = Mock()
        service._prepare_query = Mock(return_value="what is ml")
        service.query_rewriter = Mock()
        service.query_rewriter.rewrite = Mock(return_value="enhanced what is ml")

        stage = QueryEnhancementStage(service)
        result = await stage.execute(context)

        assert result.success is True
        assert result.context.rewritten_query == "enhanced what is ml"
