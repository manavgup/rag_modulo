"""
Unit tests for RerankingStage.

Tests the document reranking functionality including:
- Cross-encoder reranking
- Conditional execution (enable/disable)
- Top-k parameter handling
- Error handling
"""

import os
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.pipeline.search_context import SearchContext
from rag_solution.services.pipeline.stages.reranking_stage import RerankingStage


@pytest.fixture
def mock_pipeline_service() -> Mock:
    """Create mock pipeline service."""
    service = Mock()
    service.settings = Mock()
    return service


@pytest.fixture
def mock_reranker() -> Mock:
    """Create mock reranker."""
    reranker = Mock()
    reranker.rerank_async = AsyncMock()
    return reranker


@pytest.fixture
def search_context() -> SearchContext:
    """Create search context for testing."""
    user_id = uuid4()
    collection_id = uuid4()
    search_input = SearchInput(user_id=user_id, collection_id=collection_id, question="Test question?")
    context = SearchContext(search_input=search_input, user_id=user_id, collection_id=collection_id)
    context.rewritten_query = "enhanced test question"
    context.query_results = [MagicMock() for _ in range(10)]
    return context


@pytest.mark.unit
@pytest.mark.asyncio
class TestRerankingStage:
    """Test suite for RerankingStage."""

    async def test_stage_initialization(self, mock_pipeline_service: Mock) -> None:
        """Test that stage initializes correctly."""
        stage = RerankingStage(mock_pipeline_service)
        assert stage.stage_name == "Reranking"
        assert stage.pipeline_service == mock_pipeline_service

    @patch.dict(os.environ, {"ENABLE_RERANKING": "true"})
    async def test_successful_reranking(
        self, mock_pipeline_service: Mock, mock_reranker: Mock, search_context: SearchContext
    ) -> None:
        """Test successful reranking execution."""
        # Setup mocks
        original_results = search_context.query_results
        mock_pipeline_service.get_reranker.return_value = mock_reranker
        reranked_results = [MagicMock() for _ in range(5)]
        mock_reranker.rerank_async.return_value = reranked_results

        stage = RerankingStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is True
        assert len(result.context.query_results) == 5
        assert "reranking" in result.context.metadata
        assert result.context.metadata["reranking"]["original_count"] == 10
        assert result.context.metadata["reranking"]["reranked_count"] == 5
        assert result.context.metadata["reranking"]["method"] == "cross_encoder"

        mock_reranker.rerank_async.assert_called_once_with(
            query="enhanced test question", results=original_results, top_k=None
        )

    @patch.dict(os.environ, {"ENABLE_RERANKING": "false"})
    async def test_reranking_disabled_env_var(
        self, mock_pipeline_service: Mock, search_context: SearchContext
    ) -> None:
        """Test that reranking is skipped when disabled via environment variable."""
        stage = RerankingStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is True
        assert len(result.context.query_results) == 10  # Unchanged
        assert "reranking" not in result.context.metadata
        mock_pipeline_service.get_reranker.assert_not_called()

    @patch.dict(os.environ, {"ENABLE_RERANKING": "true"})
    async def test_reranking_disabled_config_metadata(
        self, mock_pipeline_service: Mock, search_context: SearchContext
    ) -> None:
        """Test that reranking is skipped when disabled via config_metadata."""
        search_context.search_input.config_metadata = {"disable_rerank": True}

        stage = RerankingStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is True
        assert len(result.context.query_results) == 10  # Unchanged
        assert "reranking" not in result.context.metadata
        mock_pipeline_service.get_reranker.assert_not_called()

    @patch.dict(os.environ, {"ENABLE_RERANKING": "true"})
    async def test_reranking_custom_top_k(
        self, mock_pipeline_service: Mock, mock_reranker: Mock, search_context: SearchContext
    ) -> None:
        """Test reranking with custom top_k from config_metadata."""
        search_context.search_input.config_metadata = {"top_k_rerank": 3}
        original_results = search_context.query_results
        mock_pipeline_service.get_reranker.return_value = mock_reranker
        reranked_results = [MagicMock() for _ in range(3)]
        mock_reranker.rerank_async.return_value = reranked_results

        stage = RerankingStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is True
        assert len(result.context.query_results) == 3
        assert result.context.metadata["reranking"]["reranked_count"] == 3

        mock_reranker.rerank_async.assert_called_once_with(
            query="enhanced test question", results=original_results, top_k=3
        )

    @patch.dict(os.environ, {"ENABLE_RERANKING": "true"})
    async def test_reranker_not_available(
        self, mock_pipeline_service: Mock, search_context: SearchContext
    ) -> None:
        """Test handling when reranker is not available."""
        mock_pipeline_service.get_reranker.return_value = None

        stage = RerankingStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is True
        assert len(result.context.query_results) == 10  # Unchanged
        assert "reranking" not in result.context.metadata

    @patch.dict(os.environ, {"ENABLE_RERANKING": "true"})
    async def test_missing_query_results(
        self, mock_pipeline_service: Mock, search_context: SearchContext
    ) -> None:
        """Test error handling when query results are missing."""
        search_context.query_results = None

        stage = RerankingStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is False
        assert result.error is not None
        assert "Query results not set" in result.error

    @patch.dict(os.environ, {"ENABLE_RERANKING": "true"})
    async def test_missing_rewritten_query(
        self, mock_pipeline_service: Mock, search_context: SearchContext
    ) -> None:
        """Test error handling when rewritten query is missing."""
        search_context.rewritten_query = None

        stage = RerankingStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is False
        assert result.error is not None
        assert "Rewritten query not set" in result.error

    @patch.dict(os.environ, {"ENABLE_RERANKING": "true"})
    async def test_reranking_error_handling(
        self, mock_pipeline_service: Mock, mock_reranker: Mock, search_context: SearchContext
    ) -> None:
        """Test error handling during reranking."""
        mock_pipeline_service.get_reranker.return_value = mock_reranker
        mock_reranker.rerank_async.side_effect = ValueError("Reranking failed")

        stage = RerankingStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is False
        assert result.error is not None
        assert "Reranking failed" in result.error

    @patch.dict(os.environ, {"ENABLE_RERANKING": "true"})
    async def test_empty_query_results(
        self, mock_pipeline_service: Mock, mock_reranker: Mock, search_context: SearchContext
    ) -> None:
        """Test reranking with empty query results."""
        search_context.query_results = []
        mock_pipeline_service.get_reranker.return_value = mock_reranker
        mock_reranker.rerank_async.return_value = []

        stage = RerankingStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is True
        assert len(result.context.query_results) == 0
        assert result.context.metadata["reranking"]["original_count"] == 0
        assert result.context.metadata["reranking"]["reranked_count"] == 0
