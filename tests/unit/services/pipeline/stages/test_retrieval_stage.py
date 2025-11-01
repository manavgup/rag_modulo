"""
Unit tests for RetrievalStage.

Tests the document retrieval functionality including:
- Document retrieval from vector database
- Top-k parameter extraction
- Error handling
"""

from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest

from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.pipeline.search_context import SearchContext
from rag_solution.services.pipeline.stages.retrieval_stage import RetrievalStage


@pytest.fixture
def mock_pipeline_service() -> Mock:
    """Create mock pipeline service."""
    service = Mock()
    service.settings = Mock()
    service.settings.number_of_results = 10
    service.retrieve_documents_by_id = Mock()
    # Mock the db query for collection lookup
    service.db = Mock()
    return service


@pytest.fixture
def search_context() -> SearchContext:
    """Create search context for testing."""
    user_id = uuid4()
    collection_id = uuid4()
    search_input = SearchInput(user_id=user_id, collection_id=collection_id, question="Test question?")
    context = SearchContext(search_input=search_input, user_id=user_id, collection_id=collection_id)
    context.rewritten_query = "enhanced test question"
    return context


@pytest.mark.unit
@pytest.mark.asyncio
class TestRetrievalStage:
    """Test suite for RetrievalStage."""

    async def test_stage_initialization(self, mock_pipeline_service: Mock) -> None:
        """Test that stage initializes correctly."""
        stage = RetrievalStage(mock_pipeline_service)
        assert stage.stage_name == "Retrieval"
        assert stage.pipeline_service == mock_pipeline_service

    async def test_successful_retrieval_default_top_k(
        self, mock_pipeline_service: Mock, search_context: SearchContext
    ) -> None:
        """Test successful retrieval with default top_k."""
        # Setup mock results
        mock_results = [MagicMock() for _ in range(5)]
        mock_pipeline_service.retrieve_documents_by_id.return_value = mock_results

        stage = RetrievalStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is True
        assert len(result.context.query_results) == 5
        assert "retrieval" in result.context.metadata
        assert result.context.metadata["retrieval"]["top_k"] == 10
        assert result.context.metadata["retrieval"]["results_count"] == 5

        mock_pipeline_service.retrieve_documents_by_id.assert_called_once_with(
            query="enhanced test question", collection_id=search_context.collection_id, top_k=10
        )

    async def test_successful_retrieval_custom_top_k(
        self, mock_pipeline_service: Mock, search_context: SearchContext
    ) -> None:
        """Test successful retrieval with custom top_k from config."""
        # Set custom top_k in config_metadata
        search_context.search_input.config_metadata = {"top_k": 20}

        mock_results = [MagicMock() for _ in range(15)]
        mock_pipeline_service.retrieve_documents_by_id.return_value = mock_results

        stage = RetrievalStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is True
        assert len(result.context.query_results) == 15
        assert result.context.metadata["retrieval"]["top_k"] == 20

        mock_pipeline_service.retrieve_documents_by_id.assert_called_once_with(
            query="enhanced test question", collection_id=search_context.collection_id, top_k=20
        )

    async def test_retrieval_no_results(self, mock_pipeline_service: Mock, search_context: SearchContext) -> None:
        """Test retrieval with no results found."""
        mock_pipeline_service.retrieve_documents_by_id.return_value = []

        stage = RetrievalStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is True
        assert len(result.context.query_results) == 0
        assert result.context.metadata["retrieval"]["results_count"] == 0

    async def test_missing_collection_id(self, mock_pipeline_service: Mock, search_context: SearchContext) -> None:
        """Test error when collection ID is missing."""
        search_context.collection_id = None

        stage = RetrievalStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is False
        assert "collection id" in result.error.lower()

    async def test_missing_rewritten_query(self, mock_pipeline_service: Mock, search_context: SearchContext) -> None:
        """Test error when rewritten query is missing."""
        search_context.rewritten_query = None

        stage = RetrievalStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is False
        assert "rewritten query" in result.error.lower()

    async def test_retrieval_error(self, mock_pipeline_service: Mock, search_context: SearchContext) -> None:
        """Test error handling during retrieval."""
        mock_pipeline_service.retrieve_documents_by_id.side_effect = ValueError("Retrieval failed")

        stage = RetrievalStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is False
        assert "retrieval failed" in result.error.lower()

    async def test_get_top_k_from_settings(self, mock_pipeline_service: Mock, search_context: SearchContext) -> None:
        """Test getting top_k from settings."""
        stage = RetrievalStage(mock_pipeline_service)
        top_k = stage._get_top_k(search_context)

        assert top_k == 10  # From mock settings

    async def test_get_top_k_from_config(self, mock_pipeline_service: Mock, search_context: SearchContext) -> None:
        """Test getting top_k from config_metadata."""
        search_context.search_input.config_metadata = {"top_k": 25}

        stage = RetrievalStage(mock_pipeline_service)
        top_k = stage._get_top_k(search_context)

        assert top_k == 25

    async def test_different_collection_ids(self, mock_pipeline_service: Mock) -> None:
        """Test retrieval with different collection IDs."""
        user_id = uuid4()
        collection_id = uuid4()
        search_input = SearchInput(user_id=user_id, collection_id=collection_id, question="Test?")
        context = SearchContext(search_input=search_input, user_id=user_id, collection_id=collection_id)
        context.rewritten_query = "test"

        mock_pipeline_service.retrieve_documents_by_id.return_value = [MagicMock()]

        stage = RetrievalStage(mock_pipeline_service)
        result = await stage.execute(context)

        assert result.success is True
        assert result.context.metadata["retrieval"]["collection_id"] == str(collection_id)
