"""TDD Red Phase: Unit tests for Pipeline Resolution Service.

Unit level tests for PipelineResolutionService class with mocked dependencies.
Tests the service's core business logic for pipeline resolution hierarchy.
"""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from rag_solution.core.exceptions import NotFoundError
from rag_solution.schemas.pipeline_schema import PipelineConfigOutput
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.pipeline_resolution_service import PipelineResolutionService


class TestPipelineResolutionService:
    """Test suite for Pipeline Resolution Service TDD Red Phase."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing."""
        return {
            "pipeline_service": Mock(),
            "collection_service": Mock(),
            "user_service": Mock(),
        }

    @pytest.fixture
    def resolution_service(self, mock_services):
        """Create PipelineResolutionService with mocked dependencies."""
        return PipelineResolutionService(
            pipeline_service=mock_services["pipeline_service"],
            collection_service=mock_services["collection_service"],
            user_service=mock_services["user_service"],
        )

    @pytest.fixture
    def sample_ids(self):
        """Generate sample UUIDs for testing."""
        return {
            "user_id": uuid4(),
            "collection_id": uuid4(),
            "explicit_pipeline_id": uuid4(),
            "user_default_pipeline_id": uuid4(),
            "collection_default_pipeline_id": uuid4(),
            "system_default_pipeline_id": uuid4(),
        }

    def test_resolve_pipeline_uses_explicit_pipeline_id_when_provided(
        self, resolution_service, mock_services, sample_ids
    ):
        """Test that explicit pipeline_id takes highest priority."""
        # Arrange
        search_input = SearchInput(
            question="test query",
            collection_id=sample_ids["collection_id"],
            user_id=sample_ids["user_id"],
            pipeline_id=sample_ids["explicit_pipeline_id"],
        )

        # Act
        result = resolution_service.resolve_pipeline(search_input)

        # Assert
        assert result == sample_ids["explicit_pipeline_id"]
        # Should not call any other services when explicit pipeline_id is provided
        mock_services["pipeline_service"].get_user_pipelines.assert_not_called()
        mock_services["collection_service"].get_collection.assert_not_called()

    def test_resolve_pipeline_falls_back_to_user_default_when_no_explicit_id(
        self, resolution_service, mock_services, sample_ids
    ):
        """Test fallback to user's default pipeline when no explicit pipeline_id."""
        # Arrange
        search_input = SearchInput(
            question="test query",
            collection_id=sample_ids["collection_id"],
            user_id=sample_ids["user_id"],
            pipeline_id=None,
        )

        user_pipeline_default = PipelineConfigOutput(
            id=sample_ids["user_default_pipeline_id"],
            name="User Default Pipeline",
            user_id=sample_ids["user_id"],
            is_default=True,
            embedding_model="test-model",
            provider_id=uuid4(),
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        user_pipeline_non_default = PipelineConfigOutput(
            id=uuid4(),
            name="User Non-Default Pipeline",
            user_id=sample_ids["user_id"],
            is_default=False,
            embedding_model="test-model",
            provider_id=uuid4(),
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        mock_services["pipeline_service"].get_user_pipelines.return_value = [
            user_pipeline_non_default,
            user_pipeline_default,
        ]

        # Act
        result = resolution_service.resolve_pipeline(search_input)

        # Assert
        assert result == sample_ids["user_default_pipeline_id"]
        mock_services["pipeline_service"].get_user_pipelines.assert_called_once_with(sample_ids["user_id"])

    def test_resolve_pipeline_falls_back_to_collection_default_when_no_user_default(
        self, resolution_service, mock_services, sample_ids
    ):
        """Test fallback to collection's default pipeline when user has no default."""
        # Arrange
        search_input = SearchInput(
            question="test query",
            collection_id=sample_ids["collection_id"],
            user_id=sample_ids["user_id"],
            pipeline_id=None,
        )

        # User has no default pipeline
        user_pipeline_non_default = PipelineConfigOutput(
            id=uuid4(),
            name="User Non-Default Pipeline",
            user_id=sample_ids["user_id"],
            is_default=False,
            embedding_model="test-model",
            provider_id=uuid4(),
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        mock_services["pipeline_service"].get_user_pipelines.return_value = [user_pipeline_non_default]

        # Collection has default pipeline
        mock_collection = Mock()
        mock_collection.default_pipeline_id = sample_ids["collection_default_pipeline_id"]
        mock_services["collection_service"].get_collection.return_value = mock_collection

        # Act
        result = resolution_service.resolve_pipeline(search_input)

        # Assert
        assert result == sample_ids["collection_default_pipeline_id"]
        mock_services["pipeline_service"].get_user_pipelines.assert_called_once_with(sample_ids["user_id"])
        mock_services["collection_service"].get_collection.assert_called_once_with(sample_ids["collection_id"])

    def test_resolve_pipeline_falls_back_to_system_default_when_no_collection_default(
        self, resolution_service, mock_services, sample_ids
    ):
        """Test fallback to system default pipeline when collection has no default."""
        # Arrange
        search_input = SearchInput(
            question="test query",
            collection_id=sample_ids["collection_id"],
            user_id=sample_ids["user_id"],
            pipeline_id=None,
        )

        # User has no default pipeline
        mock_services["pipeline_service"].get_user_pipelines.return_value = []

        # Collection has no default pipeline
        mock_collection = Mock()
        mock_collection.default_pipeline_id = None
        mock_services["collection_service"].get_collection.return_value = mock_collection

        # System has default pipeline
        mock_services["pipeline_service"].get_or_create_system_default.return_value = sample_ids[
            "system_default_pipeline_id"
        ]

        # Act
        result = resolution_service.resolve_pipeline(search_input)

        # Assert
        assert result == sample_ids["system_default_pipeline_id"]
        mock_services["pipeline_service"].get_user_pipelines.assert_called_once_with(sample_ids["user_id"])
        mock_services["collection_service"].get_collection.assert_called_once_with(sample_ids["collection_id"])
        mock_services["pipeline_service"].get_or_create_system_default.assert_called_once()

    def test_resolve_pipeline_raises_error_when_no_pipeline_available(
        self, resolution_service, mock_services, sample_ids
    ):
        """Test error handling when no pipeline can be resolved."""
        # Arrange
        search_input = SearchInput(
            question="test query",
            collection_id=sample_ids["collection_id"],
            user_id=sample_ids["user_id"],
            pipeline_id=None,
        )

        # No user pipelines
        mock_services["pipeline_service"].get_user_pipelines.return_value = []

        # No collection default
        mock_collection = Mock()
        mock_collection.default_pipeline_id = None
        mock_services["collection_service"].get_collection.return_value = mock_collection

        # System default creation fails
        mock_services["pipeline_service"].get_or_create_system_default.side_effect = Exception(
            "System default creation failed"
        )

        # Act & Assert
        with pytest.raises(NotFoundError, match="No pipeline configuration could be resolved"):
            resolution_service.resolve_pipeline(search_input)

    def test_resolve_pipeline_validates_resolved_pipeline_exists(self, resolution_service, mock_services, sample_ids):
        """Test that resolved pipeline is validated for existence."""
        # Arrange
        search_input = SearchInput(
            question="test query",
            collection_id=sample_ids["collection_id"],
            user_id=sample_ids["user_id"],
            pipeline_id=sample_ids["explicit_pipeline_id"],
        )

        mock_services["pipeline_service"].get_pipeline_config.side_effect = NotFoundError(
            resource_type="Pipeline", resource_id=str(sample_ids["explicit_pipeline_id"]), message="Pipeline not found"
        )

        # Act & Assert
        with pytest.raises(NotFoundError, match="Pipeline not found"):
            resolution_service.resolve_pipeline(search_input)

        mock_services["pipeline_service"].get_pipeline_config.assert_called_once_with(
            sample_ids["explicit_pipeline_id"]
        )

    def test_resolve_pipeline_caches_system_default_for_performance(
        self, resolution_service, mock_services, sample_ids
    ):
        """Test that system default pipeline is cached for performance."""
        # Arrange
        search_input1 = SearchInput(
            question="test query 1",
            collection_id=sample_ids["collection_id"],
            user_id=sample_ids["user_id"],
            pipeline_id=None,
        )

        search_input2 = SearchInput(
            question="test query 2",
            collection_id=uuid4(),  # Different collection
            user_id=uuid4(),  # Different user
            pipeline_id=None,
        )

        # Setup mocks for both calls to fall back to system default
        mock_services["pipeline_service"].get_user_pipelines.return_value = []
        mock_collection = Mock()
        mock_collection.default_pipeline_id = None
        mock_services["collection_service"].get_collection.return_value = mock_collection
        mock_services["pipeline_service"].get_or_create_system_default.return_value = sample_ids[
            "system_default_pipeline_id"
        ]

        # Act
        result1 = resolution_service.resolve_pipeline(search_input1)
        result2 = resolution_service.resolve_pipeline(search_input2)

        # Assert
        assert result1 == sample_ids["system_default_pipeline_id"]
        assert result2 == sample_ids["system_default_pipeline_id"]
        # System default should only be created/fetched once
        assert mock_services["pipeline_service"].get_or_create_system_default.call_count == 1
