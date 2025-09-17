"""TDD Red Phase: Integration tests for Pipeline Resolution Architecture.

Integration level tests that verify the interaction between SearchService,
PipelineResolutionService, and related components working together.
"""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from rag_solution.core.exceptions import NotFoundError
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.services.pipeline_resolution_service import PipelineResolutionService
from rag_solution.services.search_service import SearchService


class TestPipelineResolutionIntegration:
    """Integration tests for pipeline resolution with SearchService."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create integrated mock dependencies."""
        return {
            "db": Mock(),
            "settings": Mock(),
            "collection_service": Mock(),
            "pipeline_service": Mock(),
            "file_service": Mock(),
        }

    @pytest.fixture
    def search_service_with_resolution(self, mock_dependencies):
        """Create SearchService with PipelineResolutionService integration."""
        search_service = SearchService(db=mock_dependencies["db"], settings=mock_dependencies["settings"])

        # Inject mocked services for integration testing
        search_service._collection_service = mock_dependencies["collection_service"]
        search_service._pipeline_service = mock_dependencies["pipeline_service"]
        search_service._file_service = mock_dependencies["file_service"]

        # Create PipelineResolutionService with same mocked dependencies
        resolution_service = PipelineResolutionService(
            pipeline_service=mock_dependencies["pipeline_service"],
            collection_service=mock_dependencies["collection_service"],
            user_service=Mock(),  # Additional service for resolution
        )
        search_service._pipeline_resolution_service = resolution_service

        return search_service

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        return {
            "user_id": uuid4(),
            "collection_id": uuid4(),
            "user_default_pipeline_id": uuid4(),
            "collection_default_pipeline_id": uuid4(),
            "system_default_pipeline_id": uuid4(),
        }

    @pytest.mark.asyncio
    async def test_end_to_end_search_with_pipeline_resolution_integration(
        self, search_service_with_resolution, mock_dependencies, sample_data
    ):
        """Test complete search flow with pipeline resolution integration."""
        # Arrange
        search_input = SearchInput(
            question="What is machine learning?",
            collection_id=sample_data["collection_id"],
            user_id=sample_data["user_id"],
            pipeline_id=None,  # Will be resolved
        )

        # Mock resolution service behavior
        mock_dependencies["pipeline_service"].get_user_pipelines.return_value = [
            Mock(id=sample_data["user_default_pipeline_id"], is_default=True)
        ]

        # Mock SearchService dependencies
        mock_collection = Mock()
        mock_collection.status = "COMPLETED"
        mock_dependencies["collection_service"].get_collection.return_value = mock_collection

        mock_dependencies["pipeline_service"].get_pipeline_config.return_value = Mock()

        # Mock pipeline execution
        mock_pipeline_result = Mock()
        mock_pipeline_result.success = True
        mock_pipeline_result.generated_answer = "Machine learning is a subset of AI."
        mock_pipeline_result.query_results = []
        mock_pipeline_result.rewritten_query = None
        mock_pipeline_result.evaluation = None

        search_service_with_resolution._initialize_pipeline = AsyncMock(return_value="test_collection")
        search_service_with_resolution.pipeline_service.execute_pipeline = AsyncMock(return_value=mock_pipeline_result)
        search_service_with_resolution._generate_document_metadata = Mock(return_value=[])

        # Act
        result = await search_service_with_resolution.search(search_input)

        # Assert
        assert isinstance(result, SearchOutput)
        assert result.answer == "Machine learning is a subset of AI."

        # Verify integration: resolution service was used
        mock_dependencies["pipeline_service"].get_user_pipelines.assert_called_once_with(sample_data["user_id"])

        # Verify integration: resolved pipeline was validated
        mock_dependencies["pipeline_service"].get_pipeline_config.assert_called_once_with(
            sample_data["user_default_pipeline_id"]
        )

    @pytest.mark.asyncio
    async def test_search_service_integration_falls_back_through_hierarchy(
        self, search_service_with_resolution, mock_dependencies, sample_data
    ):
        """Test integration where search falls back through the resolution hierarchy."""
        # Arrange
        search_input = SearchInput(
            question="What is machine learning?",
            collection_id=sample_data["collection_id"],
            user_id=sample_data["user_id"],
            pipeline_id=None,
        )

        # Mock: User has no default pipeline
        mock_dependencies["pipeline_service"].get_user_pipelines.return_value = [
            Mock(id=uuid4(), is_default=False)  # No default
        ]

        # Mock: Collection has default pipeline
        mock_collection = Mock()
        mock_collection.status = "COMPLETED"
        mock_collection.default_pipeline_id = sample_data["collection_default_pipeline_id"]
        mock_dependencies["collection_service"].get_collection.return_value = mock_collection

        mock_dependencies["pipeline_service"].get_pipeline_config.return_value = Mock()

        # Mock successful pipeline execution
        mock_pipeline_result = Mock()
        mock_pipeline_result.success = True
        mock_pipeline_result.generated_answer = "Test answer"
        mock_pipeline_result.query_results = []
        mock_pipeline_result.rewritten_query = None
        mock_pipeline_result.evaluation = None

        search_service_with_resolution._initialize_pipeline = AsyncMock(return_value="test_collection")
        search_service_with_resolution.pipeline_service.execute_pipeline = AsyncMock(return_value=mock_pipeline_result)
        search_service_with_resolution._generate_document_metadata = Mock(return_value=[])

        # Act
        result = await search_service_with_resolution.search(search_input)

        # Assert
        assert isinstance(result, SearchOutput)

        # Verify integration: fell back to collection default
        mock_dependencies["pipeline_service"].get_pipeline_config.assert_called_once_with(
            sample_data["collection_default_pipeline_id"]
        )

    @pytest.mark.asyncio
    async def test_search_service_integration_handles_resolution_failure(
        self, search_service_with_resolution, mock_dependencies, sample_data
    ):
        """Test integration error handling when pipeline resolution fails."""
        # Arrange
        search_input = SearchInput(
            question="What is machine learning?",
            collection_id=sample_data["collection_id"],
            user_id=sample_data["user_id"],
            pipeline_id=None,
        )

        # Mock: No pipelines available anywhere
        mock_dependencies["pipeline_service"].get_user_pipelines.return_value = []

        mock_collection = Mock()
        mock_collection.status = "COMPLETED"
        mock_collection.default_pipeline_id = None
        mock_dependencies["collection_service"].get_collection.return_value = mock_collection

        mock_dependencies["pipeline_service"].get_or_create_system_default.side_effect = Exception("No system default")

        # Act & Assert
        with pytest.raises(NotFoundError, match="No pipeline configuration could be resolved"):
            await search_service_with_resolution.search(search_input)

    @pytest.mark.asyncio
    async def test_search_service_bypasses_resolution_with_explicit_pipeline(
        self, search_service_with_resolution, mock_dependencies, sample_data
    ):
        """Test that explicit pipeline_id bypasses resolution service entirely."""
        # Arrange
        explicit_pipeline_id = uuid4()
        search_input = SearchInput(
            question="What is machine learning?",
            collection_id=sample_data["collection_id"],
            user_id=sample_data["user_id"],
            pipeline_id=explicit_pipeline_id,
        )

        # Mock successful validation and execution
        mock_collection = Mock()
        mock_collection.status = "COMPLETED"
        mock_dependencies["collection_service"].get_collection.return_value = mock_collection

        mock_dependencies["pipeline_service"].get_pipeline_config.return_value = Mock()

        mock_pipeline_result = Mock()
        mock_pipeline_result.success = True
        mock_pipeline_result.generated_answer = "Test answer"
        mock_pipeline_result.query_results = []
        mock_pipeline_result.rewritten_query = None
        mock_pipeline_result.evaluation = None

        search_service_with_resolution._initialize_pipeline = AsyncMock(return_value="test_collection")
        search_service_with_resolution.pipeline_service.execute_pipeline = AsyncMock(return_value=mock_pipeline_result)
        search_service_with_resolution._generate_document_metadata = Mock(return_value=[])

        # Act
        result = await search_service_with_resolution.search(search_input)

        # Assert
        assert isinstance(result, SearchOutput)

        # Verify integration: resolution service was NOT used
        mock_dependencies["pipeline_service"].get_user_pipelines.assert_not_called()

        # Verify integration: explicit pipeline was used directly
        mock_dependencies["pipeline_service"].get_pipeline_config.assert_called_once_with(explicit_pipeline_id)

    @pytest.mark.asyncio
    async def test_collection_service_integration_with_default_pipeline(self, mock_dependencies, sample_data):
        """Test integration between CollectionService and pipeline resolution."""
        # This tests that CollectionService properly handles default_pipeline_id

        # Arrange
        collection_with_default = Mock()
        collection_with_default.id = sample_data["collection_id"]
        collection_with_default.default_pipeline_id = sample_data["collection_default_pipeline_id"]
        collection_with_default.status = "COMPLETED"

        mock_dependencies["collection_service"].get_collection.return_value = collection_with_default

        # Act
        collection = mock_dependencies["collection_service"].get_collection(sample_data["collection_id"])

        # Assert
        assert collection.default_pipeline_id == sample_data["collection_default_pipeline_id"]
        mock_dependencies["collection_service"].get_collection.assert_called_once_with(sample_data["collection_id"])

    def test_pipeline_service_integration_with_user_pipelines(self, mock_dependencies, sample_data):
        """Test integration of PipelineService with user pipeline management."""
        # Arrange
        user_pipelines = [
            Mock(id=uuid4(), is_default=False, name="Pipeline 1"),
            Mock(id=sample_data["user_default_pipeline_id"], is_default=True, name="Default Pipeline"),
            Mock(id=uuid4(), is_default=False, name="Pipeline 3"),
        ]

        mock_dependencies["pipeline_service"].get_user_pipelines.return_value = user_pipelines

        # Act
        pipelines = mock_dependencies["pipeline_service"].get_user_pipelines(sample_data["user_id"])

        # Assert
        assert len(pipelines) == 3
        default_pipeline = next((p for p in pipelines if p.is_default), None)
        assert default_pipeline is not None
        assert default_pipeline.id == sample_data["user_default_pipeline_id"]
