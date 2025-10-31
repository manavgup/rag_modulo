"""
Unit tests for PipelineResolutionStage.

Tests the pipeline resolution functionality including:
- Pipeline resolution and creation
- Pipeline validation
- Error handling
"""

from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest

from core.custom_exceptions import ConfigurationError, NotFoundError
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.pipeline.search_context import SearchContext
from rag_solution.services.pipeline.stages.pipeline_resolution_stage import PipelineResolutionStage


@pytest.fixture
def mock_pipeline_service() -> Mock:
    """Create mock pipeline service."""
    service = Mock()
    service.get_default_pipeline = Mock()
    service.get_pipeline_config = Mock()
    service.initialize_user_pipeline = Mock()
    service.llm_provider_service = Mock()
    service.llm_provider_service.get_user_provider = Mock()
    return service


@pytest.fixture
def search_context() -> SearchContext:
    """Create search context for testing."""
    user_id = uuid4()
    collection_id = uuid4()
    search_input = SearchInput(user_id=user_id, collection_id=collection_id, question="Test question?")
    return SearchContext(search_input=search_input, user_id=user_id, collection_id=collection_id)


@pytest.mark.unit
@pytest.mark.asyncio
class TestPipelineResolutionStage:
    """Test suite for PipelineResolutionStage."""

    async def test_stage_initialization(self, mock_pipeline_service: Mock) -> None:
        """Test that stage initializes correctly."""
        stage = PipelineResolutionStage(mock_pipeline_service)
        assert stage.stage_name == "PipelineResolution"
        assert stage.pipeline_service == mock_pipeline_service

    async def test_successful_pipeline_resolution_existing_pipeline(
        self, mock_pipeline_service: Mock, search_context: SearchContext
    ) -> None:
        """Test successful pipeline resolution with existing pipeline."""
        # Setup: existing pipeline
        pipeline_id = uuid4()
        mock_pipeline = MagicMock()
        mock_pipeline.id = pipeline_id
        mock_pipeline_service.get_default_pipeline.return_value = mock_pipeline
        mock_pipeline_service.get_pipeline_config.return_value = MagicMock()

        stage = PipelineResolutionStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is True
        assert result.context.pipeline_id == pipeline_id
        assert "pipeline_resolution" in result.context.metadata
        assert result.context.metadata["pipeline_resolution"]["success"] is True
        mock_pipeline_service.get_default_pipeline.assert_called_once_with(search_context.user_id)
        mock_pipeline_service.get_pipeline_config.assert_called_once_with(pipeline_id)

    async def test_successful_pipeline_creation_no_existing_pipeline(
        self, mock_pipeline_service: Mock, search_context: SearchContext
    ) -> None:
        """Test successful pipeline creation when no pipeline exists."""
        # Setup: no existing pipeline, need to create one
        pipeline_id = uuid4()
        provider_id = uuid4()
        mock_pipeline_service.get_default_pipeline.return_value = None
        mock_provider = MagicMock()
        mock_provider.id = provider_id
        mock_pipeline_service.llm_provider_service.get_user_provider.return_value = mock_provider
        mock_created_pipeline = MagicMock()
        mock_created_pipeline.id = pipeline_id
        mock_pipeline_service.initialize_user_pipeline.return_value = mock_created_pipeline
        mock_pipeline_service.get_pipeline_config.return_value = MagicMock()

        stage = PipelineResolutionStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is True
        assert result.context.pipeline_id == pipeline_id
        mock_pipeline_service.get_default_pipeline.assert_called_once()
        mock_pipeline_service.llm_provider_service.get_user_provider.assert_called_once_with(search_context.user_id)
        mock_pipeline_service.initialize_user_pipeline.assert_called_once_with(search_context.user_id, provider_id)

    async def test_pipeline_validation_failure(
        self, mock_pipeline_service: Mock, search_context: SearchContext
    ) -> None:
        """Test pipeline validation failure."""
        pipeline_id = uuid4()
        mock_pipeline = MagicMock()
        mock_pipeline.id = pipeline_id
        mock_pipeline_service.get_default_pipeline.return_value = mock_pipeline
        mock_pipeline_service.get_pipeline_config.return_value = None  # Pipeline not found

        stage = PipelineResolutionStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is False
        assert "not found" in result.error.lower()

    async def test_no_llm_provider_error(self, mock_pipeline_service: Mock, search_context: SearchContext) -> None:
        """Test error when no LLM provider is available."""
        mock_pipeline_service.get_default_pipeline.return_value = None
        mock_pipeline_service.llm_provider_service.get_user_provider.return_value = None

        stage = PipelineResolutionStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is False
        assert "llm provider" in result.error.lower()

    async def test_pipeline_creation_failure(
        self, mock_pipeline_service: Mock, search_context: SearchContext
    ) -> None:
        """Test failure during pipeline creation."""
        mock_pipeline_service.get_default_pipeline.return_value = None
        mock_provider = MagicMock()
        mock_provider.id = uuid4()
        mock_pipeline_service.llm_provider_service.get_user_provider.return_value = mock_provider
        mock_pipeline_service.initialize_user_pipeline.side_effect = Exception("Creation failed")

        stage = PipelineResolutionStage(mock_pipeline_service)
        result = await stage.execute(search_context)

        assert result.success is False
        assert "creation failed" in result.error.lower() or "failed to create" in result.error.lower()

    async def test_validate_pipeline_success(self, mock_pipeline_service: Mock) -> None:
        """Test successful pipeline validation."""
        pipeline_id = uuid4()
        mock_pipeline_service.get_pipeline_config.return_value = MagicMock()

        stage = PipelineResolutionStage(mock_pipeline_service)
        stage._validate_pipeline(pipeline_id)  # Should not raise

        mock_pipeline_service.get_pipeline_config.assert_called_once_with(pipeline_id)

    async def test_validate_pipeline_not_found(self, mock_pipeline_service: Mock) -> None:
        """Test pipeline validation with non-existent pipeline."""
        pipeline_id = uuid4()
        mock_pipeline_service.get_pipeline_config.return_value = None

        stage = PipelineResolutionStage(mock_pipeline_service)

        with pytest.raises(NotFoundError) as exc_info:
            stage._validate_pipeline(pipeline_id)

        assert "pipeline" in str(exc_info.value).lower()
        assert str(pipeline_id) in str(exc_info.value)
