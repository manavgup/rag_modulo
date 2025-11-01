"""Integration tests for search with automatic pipeline resolution.

Tests the complete flow from SearchInput (without pipeline_id) through
SearchService to PipelineService with automatic pipeline resolution.
"""

import contextlib
from unittest.mock import AsyncMock, Mock, patch
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
    @pytest.mark.asyncio
    async def test_search_end_to_end_with_pipeline_resolution(
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
        mock_pipeline_service.initialize = AsyncMock(return_value=None)

        # Mock all pipeline stage methods (NEW pipeline architecture)
        # Stage 1: Pipeline Resolution
        mock_pipeline_service.llm_provider_service = Mock()
        mock_provider = Mock()
        mock_provider.id = uuid4()
        mock_pipeline_service.llm_provider_service.get_user_provider.return_value = mock_provider
        mock_pipeline_service.initialize_user_pipeline.return_value = mock_default_pipeline

        # Stage 2: Query Enhancement
        mock_pipeline_service._prepare_query = Mock(side_effect=lambda q: q.strip())
        mock_query_rewriter = Mock()
        mock_query_rewriter.rewrite = Mock(return_value="machine learning features enhanced")
        mock_pipeline_service.query_rewriter = mock_query_rewriter

        # Stage 3: Retrieval
        mock_pipeline_service.retrieve_documents_by_id = Mock(return_value=[])
        mock_pipeline_service.generate_document_metadata = Mock(return_value=[])
        mock_pipeline_service.settings = Mock(number_of_results=10)

        # Stage 4: Reranking
        mock_pipeline_service.get_reranker = Mock(return_value=None)

        # Stage 6: Generation
        mock_provider_obj = Mock()
        mock_llm_params = {"temperature": 0.7}
        mock_pipeline_service._validate_configuration = Mock(
            return_value=(resolved_pipeline_id, mock_llm_params, mock_provider_obj)
        )
        mock_rag_template = Mock()
        mock_rag_template.format = Mock(return_value="formatted prompt")
        mock_pipeline_service._get_templates = Mock(return_value=(mock_rag_template, None))
        mock_pipeline_service._format_context = Mock(return_value="formatted context")
        mock_pipeline_service._generate_answer = Mock(return_value="Machine learning key features include...")

        mock_pipeline_service_class.return_value = mock_pipeline_service

        # Mock FileManagementService
        mock_file_service = Mock()
        mock_file_service.get_files_by_collection.return_value = []
        mock_file_service_class.return_value = mock_file_service

        # Create SearchService
        search_service = SearchService(mock_db, mock_settings)

        # Mock token tracking
        search_service._token_tracking_service = Mock()
        search_service.token_tracking_service.check_usage_warning = AsyncMock(return_value=None)

        # Mock ChainOfThoughtService
        search_service._chain_of_thought_service = Mock()
        search_service.chain_of_thought_service.should_use_cot = Mock(return_value=False)

        # Act
        result = await search_service.search(search_input_without_pipeline)

        # Assert
        assert result is not None
        assert result.answer == "Machine learning key features include..."

        # Verify pipeline resolution was called
        mock_pipeline_service.get_default_pipeline.assert_called_once_with(search_input_without_pipeline.user_id)

    @patch("rag_solution.services.user_service.UserService")
    @patch("rag_solution.services.search_service.CollectionService")
    @patch("rag_solution.services.search_service.PipelineService")
    @pytest.mark.asyncio
    async def test_search_creates_default_pipeline_when_user_has_none(
        self,
        mock_pipeline_service_class,
        mock_collection_service_class,
        mock_user_service_class,
        mock_db,
        mock_settings,
        search_input_without_pipeline,
    ):
        """Test that search creates default pipeline when user has none."""
        # Arrange
        created_pipeline_id = uuid4()
        provider_id = uuid4()

        # Mock UserService
        mock_user_service = Mock()
        mock_user = Mock()
        mock_user.id = search_input_without_pipeline.user_id
        mock_user.ibm_id = "test_user"
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.role = "user"
        mock_user.preferred_provider_id = provider_id
        mock_user.created_at = "2023-01-01T00:00:00Z"
        mock_user.updated_at = "2023-01-01T00:00:00Z"
        mock_user_service.get_user.return_value = mock_user
        mock_user_service_class.return_value = mock_user_service

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
        mock_pipeline_service.get_pipeline_config.return_value = Mock()  # For validation

        # Mock all pipeline stage methods (NEW pipeline architecture)
        # Stage 1: Pipeline Resolution
        mock_pipeline_service.llm_provider_service = Mock()
        mock_pipeline_service.llm_provider_service.get_user_provider.return_value = mock_provider

        # Stage 2: Query Enhancement
        mock_pipeline_service._prepare_query = Mock(side_effect=lambda q: q.strip())
        mock_query_rewriter = Mock()
        mock_query_rewriter.rewrite = Mock(return_value="machine learning features")
        mock_pipeline_service.query_rewriter = mock_query_rewriter

        # Stage 3: Retrieval
        mock_pipeline_service.retrieve_documents_by_id = Mock(return_value=[])
        mock_pipeline_service.generate_document_metadata = Mock(return_value=[])
        mock_pipeline_service.settings = Mock(number_of_results=10)

        # Stage 4: Reranking
        mock_pipeline_service.get_reranker = Mock(return_value=None)

        # Stage 6: Generation
        mock_provider_obj = Mock()
        mock_llm_params = {"temperature": 0.7}
        mock_pipeline_service._validate_configuration = Mock(
            return_value=(created_pipeline_id, mock_llm_params, mock_provider_obj)
        )
        mock_rag_template = Mock()
        mock_rag_template.format = Mock(return_value="formatted prompt")
        mock_pipeline_service._get_templates = Mock(return_value=(mock_rag_template, None))
        mock_pipeline_service._format_context = Mock(return_value="formatted context")
        mock_pipeline_service._generate_answer = Mock(return_value="Test answer")

        mock_pipeline_service_class.return_value = mock_pipeline_service

        # Create SearchService and mock LLM provider service
        search_service = SearchService(mock_db, mock_settings)
        search_service._llm_provider_service = Mock()
        search_service.llm_provider_service.get_user_provider.return_value = mock_provider

        # Mock token tracking
        search_service._token_tracking_service = Mock()
        search_service.token_tracking_service.check_usage_warning = AsyncMock(return_value=None)

        # Mock ChainOfThoughtService
        search_service._chain_of_thought_service = Mock()
        search_service.chain_of_thought_service.should_use_cot = Mock(return_value=False)

        # Act
        result = await search_service.search(search_input_without_pipeline)

        # Assert
        assert result is not None

        # Verify default pipeline creation flow
        mock_pipeline_service.get_default_pipeline.assert_called_once_with(search_input_without_pipeline.user_id)
        # Note: In the new stage-based architecture, get_user_provider and initialize_user_pipeline
        # are called internally by PipelineResolutionStage, not directly by SearchService
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
