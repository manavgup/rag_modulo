"""TDD Red Phase: Tests for SearchService with Pipeline Resolution.

This module tests the enhanced SearchService that integrates with the new
pipeline resolution system to make pipeline_id optional in search requests.
"""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from rag_solution.core.exceptions import NotFoundError
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.services.search_service import SearchService


class TestSearchServicePipelineResolution:
    """Test suite for SearchService pipeline resolution integration."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for SearchService."""
        return {
            "db": Mock(),
            "settings": Mock(),
            "pipeline_resolution_service": Mock(),
            "collection_service": Mock(),
            "pipeline_service": Mock(),
            "file_service": Mock(),
        }

    @pytest.fixture
    def search_service(self, mock_dependencies):
        """Create SearchService with mocked dependencies."""
        service = SearchService(db=mock_dependencies["db"], settings=mock_dependencies["settings"])
        # Inject mock services
        service._pipeline_resolution_service = mock_dependencies["pipeline_resolution_service"]
        service._collection_service = mock_dependencies["collection_service"]
        service._pipeline_service = mock_dependencies["pipeline_service"]
        service._file_service = mock_dependencies["file_service"]
        return service

    @pytest.fixture
    def sample_ids(self):
        """Generate sample UUIDs for testing."""
        return {
            "user_id": uuid4(),
            "collection_id": uuid4(),
            "resolved_pipeline_id": uuid4(),
        }

    @pytest.mark.asyncio
    async def test_search_resolves_pipeline_when_pipeline_id_not_provided(
        self, search_service, mock_dependencies, sample_ids
    ):
        """Test that search service resolves pipeline when pipeline_id is None."""
        # Arrange
        search_input = SearchInput(
            question="What is machine learning?",
            collection_id=sample_ids["collection_id"],
            user_id=sample_ids["user_id"],
            pipeline_id=None,  # No explicit pipeline
        )

        # Mock pipeline resolution
        mock_dependencies["pipeline_resolution_service"].resolve_pipeline.return_value = sample_ids[
            "resolved_pipeline_id"
        ]

        # Mock successful validation and execution
        mock_dependencies["collection_service"].get_collection.return_value = Mock(status="COMPLETED")
        mock_dependencies["pipeline_service"].get_pipeline_config.return_value = Mock()

        # Mock pipeline execution
        mock_pipeline_result = Mock()
        mock_pipeline_result.success = True
        mock_pipeline_result.generated_answer = "Machine learning is a subset of AI."
        mock_pipeline_result.query_results = []
        mock_pipeline_result.rewritten_query = None
        mock_pipeline_result.evaluation = None

        search_service._initialize_pipeline = AsyncMock(return_value="test_collection")
        search_service.pipeline_service.execute_pipeline = AsyncMock(return_value=mock_pipeline_result)
        search_service._generate_document_metadata = Mock(return_value=[])

        # Act
        result = await search_service.search(search_input)

        # Assert
        assert isinstance(result, SearchOutput)
        mock_dependencies["pipeline_resolution_service"].resolve_pipeline.assert_called_once_with(search_input)

        # Verify the resolved pipeline ID was used in validation
        mock_dependencies["pipeline_service"].get_pipeline_config.assert_called_once_with(
            sample_ids["resolved_pipeline_id"]
        )

    @pytest.mark.asyncio
    async def test_search_uses_explicit_pipeline_id_when_provided(self, search_service, mock_dependencies, sample_ids):
        """Test that explicit pipeline_id bypasses resolution service."""
        # Arrange
        explicit_pipeline_id = uuid4()
        search_input = SearchInput(
            question="What is machine learning?",
            collection_id=sample_ids["collection_id"],
            user_id=sample_ids["user_id"],
            pipeline_id=explicit_pipeline_id,
        )

        # Mock successful validation and execution
        mock_dependencies["collection_service"].get_collection.return_value = Mock(status="COMPLETED")
        mock_dependencies["pipeline_service"].get_pipeline_config.return_value = Mock()

        # Mock pipeline execution
        mock_pipeline_result = Mock()
        mock_pipeline_result.success = True
        mock_pipeline_result.generated_answer = "Machine learning is a subset of AI."
        mock_pipeline_result.query_results = []
        mock_pipeline_result.rewritten_query = None
        mock_pipeline_result.evaluation = None

        search_service._initialize_pipeline = AsyncMock(return_value="test_collection")
        search_service.pipeline_service.execute_pipeline = AsyncMock(return_value=mock_pipeline_result)
        search_service._generate_document_metadata = Mock(return_value=[])

        # Act
        result = await search_service.search(search_input)

        # Assert
        assert isinstance(result, SearchOutput)
        # Resolution service should NOT be called when explicit pipeline_id is provided
        mock_dependencies["pipeline_resolution_service"].resolve_pipeline.assert_not_called()

        # Explicit pipeline ID should be used directly
        mock_dependencies["pipeline_service"].get_pipeline_config.assert_called_once_with(explicit_pipeline_id)

    @pytest.mark.asyncio
    async def test_search_fails_when_pipeline_resolution_fails(self, search_service, mock_dependencies, sample_ids):
        """Test error handling when pipeline resolution fails."""
        # Arrange
        search_input = SearchInput(
            question="What is machine learning?",
            collection_id=sample_ids["collection_id"],
            user_id=sample_ids["user_id"],
            pipeline_id=None,
        )

        # Mock pipeline resolution failure
        mock_dependencies["pipeline_resolution_service"].resolve_pipeline.side_effect = NotFoundError(
            resource_type="Pipeline", resource_id="none", message="No pipeline configuration could be resolved"
        )

        # Act & Assert
        with pytest.raises(NotFoundError, match="No pipeline configuration could be resolved"):
            await search_service.search(search_input)

    @pytest.mark.asyncio
    async def test_search_validates_resolved_pipeline_exists(self, search_service, mock_dependencies, sample_ids):
        """Test that resolved pipeline is validated for existence."""
        # Arrange
        search_input = SearchInput(
            question="What is machine learning?",
            collection_id=sample_ids["collection_id"],
            user_id=sample_ids["user_id"],
            pipeline_id=None,
        )

        # Mock pipeline resolution returns invalid pipeline
        invalid_pipeline_id = uuid4()
        mock_dependencies["pipeline_resolution_service"].resolve_pipeline.return_value = invalid_pipeline_id

        # Mock validation failure
        mock_dependencies["pipeline_service"].get_pipeline_config.side_effect = NotFoundError(
            resource_type="Pipeline", resource_id=str(invalid_pipeline_id), message="Pipeline configuration not found"
        )

        # Act & Assert
        with pytest.raises(NotFoundError, match="Pipeline configuration not found"):
            await search_service.search(search_input)

    @pytest.mark.asyncio
    async def test_search_preserves_original_search_input_in_pipeline_execution(
        self, search_service, mock_dependencies, sample_ids
    ):
        """Test that original search input is preserved when passed to pipeline execution."""
        # Arrange
        search_input = SearchInput(
            question="What is machine learning?",
            collection_id=sample_ids["collection_id"],
            user_id=sample_ids["user_id"],
            pipeline_id=None,
            config_metadata={"max_chunks": 10},
        )

        # Mock pipeline resolution
        mock_dependencies["pipeline_resolution_service"].resolve_pipeline.return_value = sample_ids[
            "resolved_pipeline_id"
        ]

        # Mock successful validation
        mock_dependencies["collection_service"].get_collection.return_value = Mock(status="COMPLETED")
        mock_dependencies["pipeline_service"].get_pipeline_config.return_value = Mock()

        # Mock pipeline execution
        mock_pipeline_result = Mock()
        mock_pipeline_result.success = True
        mock_pipeline_result.generated_answer = "Machine learning is a subset of AI."
        mock_pipeline_result.query_results = []
        mock_pipeline_result.rewritten_query = None
        mock_pipeline_result.evaluation = None

        search_service._initialize_pipeline = AsyncMock(return_value="test_collection")
        search_service.pipeline_service.execute_pipeline = AsyncMock(return_value=mock_pipeline_result)
        search_service._generate_document_metadata = Mock(return_value=[])

        # Act
        await search_service.search(search_input)

        # Assert
        # The execute_pipeline should be called with the enhanced search_input that includes resolved pipeline_id
        call_args = search_service.pipeline_service.execute_pipeline.call_args
        executed_search_input = call_args[1]["search_input"]  # keyword argument

        assert executed_search_input.question == "What is machine learning?"
        assert executed_search_input.collection_id == sample_ids["collection_id"]
        assert executed_search_input.user_id == sample_ids["user_id"]
        assert executed_search_input.pipeline_id == sample_ids["resolved_pipeline_id"]  # Should be resolved
        assert executed_search_input.config_metadata == {"max_chunks": 10}

    def test_search_input_schema_allows_optional_pipeline_id(self):
        """Test that SearchInput schema accepts None for pipeline_id."""
        # This test ensures our schema changes are correctly implemented

        # Test with pipeline_id=None
        search_input_without_pipeline = SearchInput(
            question="What is machine learning?",
            collection_id=uuid4(),
            user_id=uuid4(),
            pipeline_id=None,
        )
        assert search_input_without_pipeline.pipeline_id is None

        # Test with explicit pipeline_id
        explicit_pipeline_id = uuid4()
        search_input_with_pipeline = SearchInput(
            question="What is machine learning?",
            collection_id=uuid4(),
            user_id=uuid4(),
            pipeline_id=explicit_pipeline_id,
        )
        assert search_input_with_pipeline.pipeline_id == explicit_pipeline_id

        # Test that SearchInput can be created without pipeline_id field at all
        search_input_minimal = SearchInput(
            question="What is machine learning?",
            collection_id=uuid4(),
            user_id=uuid4(),
        )
        assert search_input_minimal.pipeline_id is None
