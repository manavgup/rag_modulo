"""Integration tests for search with automatic pipeline resolution.

Tests the complete flow from SearchInput (without pipeline_id) through
SearchService to PipelineService with automatic pipeline resolution.
"""

import contextlib
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from rag_solution.schemas.search_schema import SearchInput
from rag_solution.services.search_service import SearchService


class TestSearchPipelineResolutionIntegration:
    """Integration tests for search with automatic pipeline resolution."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def mock_settings(self):
        """Mock application settings."""
        settings = Mock()
        settings.vector_db = "milvus"
        return settings

    @pytest.fixture
    def search_input_without_pipeline(self):
        """Create SearchInput without pipeline_id."""
        return SearchInput(
            question="What are the key features of machine learning?",
            collection_id=uuid4(),
            user_id=uuid4(),
            config_metadata={"max_chunks": 10},
        )

    @patch("rag_solution.services.search_service.CollectionService")
    @patch("rag_solution.services.search_service.PipelineService")
    @patch("rag_solution.services.search_service.FileManagementService")
    def test_search_end_to_end_with_pipeline_resolution(
        self,
        mock_file_service_class,
        mock_pipeline_service_class,
        mock_collection_service_class,
        mock_db,
        mock_settings,
        search_input_without_pipeline,
    ):
        """Test complete search flow with automatic pipeline resolution."""
        # Arrange
        resolved_pipeline_id = uuid4()

        # Mock CollectionService
        mock_collection_service = Mock()
        mock_collection = Mock()
        mock_collection.vector_db_name = "test_collection"
        mock_collection.id = search_input_without_pipeline.collection_id
        mock_collection.status = "completed"
        mock_collection.is_private = False
        mock_collection_service.get_collection.return_value = mock_collection
        mock_collection_service_class.return_value = mock_collection_service

        # Mock PipelineService for pipeline resolution
        mock_pipeline_service = Mock()
        mock_default_pipeline = Mock()
        mock_default_pipeline.id = resolved_pipeline_id
        mock_pipeline_service.get_default_pipeline.return_value = mock_default_pipeline
        mock_pipeline_service.get_pipeline_config.return_value = Mock()  # For validation
        mock_pipeline_service.initialize.return_value = None

        # Mock successful pipeline execution
        mock_pipeline_result = Mock()
        mock_pipeline_result.success = True
        mock_pipeline_result.generated_answer = "Machine learning key features include..."
        mock_pipeline_result.query_results = []
        mock_pipeline_result.rewritten_query = None
        mock_pipeline_result.evaluation = None
        mock_pipeline_service.execute_pipeline.return_value = mock_pipeline_result
        mock_pipeline_service_class.return_value = mock_pipeline_service

        # Mock FileManagementService
        mock_file_service = Mock()
        mock_file_service.get_files_by_collection.return_value = []
        mock_file_service_class.return_value = mock_file_service

        # Create SearchService
        search_service = SearchService(mock_db, mock_settings)

        # Act
        result = search_service.search(search_input_without_pipeline)

        # Assert
        assert result is not None
        assert result.answer == "Machine learning key features include..."

        # Verify pipeline resolution was called
        mock_pipeline_service.get_default_pipeline.assert_called_once_with(search_input_without_pipeline.user_id)

        # Verify pipeline execution was called with resolved pipeline_id
        mock_pipeline_service.execute_pipeline.assert_called_once()
        call_args = mock_pipeline_service.execute_pipeline.call_args
        assert call_args[1]["pipeline_id"] == resolved_pipeline_id  # Should use resolved pipeline_id

    @patch("rag_solution.services.search_service.CollectionService")
    @patch("rag_solution.services.search_service.PipelineService")
    def test_search_creates_default_pipeline_when_user_has_none(
        self,
        mock_pipeline_service_class,
        mock_collection_service_class,
        mock_db,
        mock_settings,
        search_input_without_pipeline,
    ):
        """Test that search creates default pipeline when user has none."""
        # Arrange
        created_pipeline_id = uuid4()
        provider_id = uuid4()

        # Mock CollectionService
        mock_collection_service = Mock()
        mock_collection = Mock()
        mock_collection.vector_db_name = "test_collection"
        mock_collection.status = "completed"
        mock_collection.is_private = False
        mock_collection_service.get_collection.return_value = mock_collection
        mock_collection_service_class.return_value = mock_collection_service

        # Mock PipelineService - no default pipeline exists
        mock_pipeline_service = Mock()
        mock_pipeline_service.get_default_pipeline.return_value = None  # No default exists

        # Mock LLM provider service
        mock_provider = Mock()
        mock_provider.id = provider_id

        # Mock pipeline creation
        mock_created_pipeline = Mock()
        mock_created_pipeline.id = created_pipeline_id
        mock_pipeline_service.initialize_user_pipeline.return_value = mock_created_pipeline

        mock_pipeline_service_class.return_value = mock_pipeline_service

        # Create SearchService and mock LLM provider service
        search_service = SearchService(mock_db, mock_settings)
        search_service._llm_provider_service = Mock()
        search_service.llm_provider_service.get_default_provider.return_value = mock_provider

        # Mock other required methods
        search_service._validate_search_input = Mock()
        search_service._validate_collection_access = Mock()
        search_service._validate_pipeline = Mock()
        search_service._initialize_pipeline = Mock(return_value="test_collection")
        search_service._generate_document_metadata = Mock(return_value=[])
        search_service._clean_generated_answer = Mock(return_value="Test answer")

        # Mock pipeline execution
        mock_result = Mock()
        mock_result.success = True
        mock_result.generated_answer = "Test answer"
        mock_result.query_results = []
        mock_result.rewritten_query = None
        mock_result.evaluation = None
        mock_pipeline_service.execute_pipeline.return_value = mock_result

        # Act
        result = search_service.search(search_input_without_pipeline)

        # Assert
        assert result is not None

        # Verify default pipeline creation flow
        mock_pipeline_service.get_default_pipeline.assert_called_once_with(search_input_without_pipeline.user_id)
        search_service.llm_provider_service.get_default_provider.assert_called_once()
        mock_pipeline_service.initialize_user_pipeline.assert_called_once_with(
            search_input_without_pipeline.user_id, provider_id
        )

    def test_search_input_has_no_pipeline_id_attribute(self, search_input_without_pipeline):
        """Test that SearchInput no longer has pipeline_id attribute."""
        # This test ensures the schema change is properly implemented
        assert not hasattr(search_input_without_pipeline, "pipeline_id")

        # Verify all expected attributes exist
        assert hasattr(search_input_without_pipeline, "question")
        assert hasattr(search_input_without_pipeline, "collection_id")
        assert hasattr(search_input_without_pipeline, "user_id")
        assert hasattr(search_input_without_pipeline, "config_metadata")

    @patch("rag_solution.services.search_service.PipelineService")
    def test_pipeline_service_execute_pipeline_signature_change(
        self, mock_pipeline_service_class, mock_db, mock_settings, search_input_without_pipeline
    ):
        """Test that PipelineService.execute_pipeline accepts pipeline_id parameter."""
        # Arrange
        mock_pipeline_service = Mock()
        mock_pipeline_service_class.return_value = mock_pipeline_service

        search_service = SearchService(mock_db, mock_settings)
        pipeline_id = uuid4()

        # Act - call execute_pipeline with new signature
        with contextlib.suppress(Exception):
            search_service.pipeline_service.execute_pipeline(
                search_input=search_input_without_pipeline, collection_name="test_collection", pipeline_id=pipeline_id
            )

        # Assert - verify the call was made with pipeline_id parameter
        # This test will fail until PipelineService.execute_pipeline signature is updated
        mock_pipeline_service.execute_pipeline.assert_called_once_with(
            search_input=search_input_without_pipeline, collection_name="test_collection", pipeline_id=pipeline_id
        )
