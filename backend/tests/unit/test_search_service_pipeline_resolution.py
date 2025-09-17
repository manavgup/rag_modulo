"""Unit tests for SearchService pipeline resolution functionality.

Tests the core business logic for resolving user default pipelines
when no explicit pipeline_id is provided in SearchInput.
"""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from core.custom_exceptions import ConfigurationError

from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.search_service import SearchService


class TestSearchServicePipelineResolution:
    """Test suite for SearchService pipeline resolution logic."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        return Mock()

    @pytest.fixture
    def search_service(self, mock_db, mock_settings):
        """Create SearchService instance with mocked dependencies."""
        return SearchService(mock_db, mock_settings)

    @pytest.fixture
    def sample_search_input(self):
        """Create sample SearchInput without pipeline_id."""
        return SearchInput(
            question="What is machine learning?",
            collection_id=uuid4(),
            user_id=uuid4(),
            config_metadata={"max_chunks": 5},
        )

    def test_resolve_user_default_pipeline_exists(self, search_service, sample_search_input):
        """Test resolving user default pipeline when user has a default."""
        # Arrange
        expected_pipeline_id = uuid4()
        mock_pipeline = Mock()
        mock_pipeline.id = expected_pipeline_id

        # Mock pipeline service to return user's default
        search_service._pipeline_service = Mock()
        search_service.pipeline_service.get_default_pipeline.return_value = mock_pipeline

        # Act
        resolved_pipeline_id = search_service._resolve_user_default_pipeline(sample_search_input.user_id)

        # Assert
        assert resolved_pipeline_id == expected_pipeline_id
        search_service.pipeline_service.get_default_pipeline.assert_called_once_with(sample_search_input.user_id)

    def test_resolve_user_default_pipeline_none_creates_default(self, search_service, sample_search_input):
        """Test that a default pipeline is created when user has none."""
        # Arrange
        created_pipeline_id = uuid4()
        provider_id = uuid4()

        # Mock pipeline service - no default exists, then create one
        search_service._pipeline_service = Mock()
        search_service.pipeline_service.get_default_pipeline.return_value = None

        # Mock LLM provider service to return default provider
        search_service._llm_provider_service = Mock()
        mock_provider = Mock()
        mock_provider.id = provider_id
        search_service.llm_provider_service.get_user_provider.return_value = mock_provider

        # Mock pipeline creation
        mock_created_pipeline = Mock()
        mock_created_pipeline.id = created_pipeline_id
        search_service.pipeline_service.initialize_user_pipeline.return_value = mock_created_pipeline

        # Act
        resolved_pipeline_id = search_service._resolve_user_default_pipeline(sample_search_input.user_id)

        # Assert
        assert resolved_pipeline_id == created_pipeline_id
        search_service.pipeline_service.get_default_pipeline.assert_called_once_with(sample_search_input.user_id)
        search_service.llm_provider_service.get_user_provider.assert_called_once_with(sample_search_input.user_id)
        search_service.pipeline_service.initialize_user_pipeline.assert_called_once_with(
            sample_search_input.user_id, provider_id
        )

    def test_resolve_user_default_pipeline_no_provider_raises_error(self, search_service, sample_search_input):
        """Test that ConfigurationError is raised when no LLM provider is available."""
        # Arrange
        search_service._pipeline_service = Mock()
        search_service.pipeline_service.get_default_pipeline.return_value = None

        search_service._llm_provider_service = Mock()
        search_service.llm_provider_service.get_user_provider.return_value = None

        # Act & Assert
        with pytest.raises(ConfigurationError) as exc_info:
            search_service._resolve_user_default_pipeline(sample_search_input.user_id)

        assert "No LLM provider available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_uses_resolved_pipeline_id(self, search_service, sample_search_input):
        """Test that search method uses resolved pipeline_id instead of SearchInput.pipeline_id."""
        # Arrange
        resolved_pipeline_id = uuid4()

        # Mock all dependencies
        search_service._validate_search_input = Mock()
        search_service._validate_collection_access = Mock()
        search_service._validate_pipeline = Mock()
        search_service._resolve_user_default_pipeline = Mock(return_value=resolved_pipeline_id)
        search_service._initialize_pipeline = AsyncMock(return_value="test_collection")

        # Mock pipeline service execution
        search_service._pipeline_service = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.generated_answer = "Test answer"
        mock_result.query_results = []
        mock_result.rewritten_query = None
        mock_result.evaluation = None
        search_service.pipeline_service.execute_pipeline = AsyncMock(return_value=mock_result)

        # Mock document metadata generation
        search_service._generate_document_metadata = Mock(return_value=[])
        search_service._clean_generated_answer = Mock(return_value="Clean answer")

        # Act
        await search_service.search(sample_search_input)

        # Assert
        search_service._resolve_user_default_pipeline.assert_called_once_with(sample_search_input.user_id)
        search_service._validate_pipeline.assert_called_once_with(resolved_pipeline_id)
        search_service.pipeline_service.execute_pipeline.assert_called_once_with(
            search_input=sample_search_input,
            collection_name="test_collection",
            pipeline_id=resolved_pipeline_id,  # Should pass resolved pipeline_id
        )

    @pytest.mark.asyncio
    async def test_search_pipeline_resolution_error_propagated(self, search_service, sample_search_input):
        """Test that pipeline resolution errors are properly propagated."""
        # Arrange
        search_service._validate_search_input = Mock()
        search_service._validate_collection_access = Mock()
        search_service._resolve_user_default_pipeline = Mock(
            side_effect=ConfigurationError("Failed to resolve pipeline")
        )

        # Act & Assert
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await search_service.search(sample_search_input)

        assert exc_info.value.status_code == 500
        assert "Failed to resolve pipeline" in str(exc_info.value.detail)

    def test_method_resolve_user_default_pipeline_exists_on_service(self, search_service):
        """Test that _resolve_user_default_pipeline method exists on SearchService."""
        # This test will fail until method is implemented
        assert hasattr(search_service, "_resolve_user_default_pipeline")
        assert callable(search_service._resolve_user_default_pipeline)

    def test_pipeline_service_get_default_pipeline_simplified_signature(self, search_service):
        """Test that PipelineService.get_default_pipeline has simplified signature (no collection_id)."""
        # Arrange
        user_id = uuid4()
        search_service._pipeline_service = Mock()

        # Act - call with just user_id (no collection_id)
        search_service.pipeline_service.get_default_pipeline(user_id)

        # Assert - should be called with only user_id parameter
        search_service.pipeline_service.get_default_pipeline.assert_called_once_with(user_id)
