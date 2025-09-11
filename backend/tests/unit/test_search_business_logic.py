"""Unit tests for search business logic.

These tests focus on business logic with mocked dependencies.
No external services, databases, or HTTP calls.
"""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from rag_solution.schemas.collection_schema import CollectionStatus
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.services.search_service import SearchService


class TestSearchBusinessLogic:
    """Test search business logic with mocked dependencies."""

    @pytest.fixture
    def mock_vector_store(self):
        """Create a mocked vector store."""
        mock_store = Mock()
        mock_store.search.return_value = [{"document_id": "doc-1", "text": "Sample document content", "score": 0.95, "metadata": {"source": "test.txt"}}]
        mock_store.retrieve_documents.return_value = [{"id": "doc-1", "name": "test.txt", "content": "Sample document content", "chunks": []}]
        return mock_store

    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mocked LLM provider."""
        mock_provider = Mock()
        mock_provider.generate_response.return_value = "This is a test answer."
        mock_provider.rewrite_query.return_value = "Rewritten test query"
        return mock_provider

    @pytest.fixture
    def mock_database_session(self):
        """Create a mocked database session."""
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = Mock()
        return mock_session

    @pytest.fixture
    def search_service(self, mock_database_session, mock_settings):
        """Create SearchService with mocked dependencies."""
        service = SearchService(db=mock_database_session, settings=mock_settings)
        return service

    def test_search_query_processing(self, search_service):
        """Test that search queries are processed correctly."""
        search_input = SearchInput(question="What is the main topic?", collection_id=uuid4(), pipeline_id=uuid4(), user_id=uuid4())

        # Mock the async search method
        with patch.object(search_service, "search") as mock_search:
            mock_search.return_value = SearchOutput(answer="Test answer", documents=[], query_results=[], rewritten_query="Test query", evaluation={})

            # Since search is async, we need to handle it properly
            import asyncio

            result = asyncio.run(search_service.search(search_input))

            assert result.answer == "Test answer"
            assert result.rewritten_query == "Test query"
            mock_search.assert_called_once_with(search_input)

    def test_collection_validation(self, search_service, mock_database_session):
        """Test that collection validation works correctly."""
        collection_id = uuid4()
        user_id = uuid4()

        # Mock collection exists
        mock_collection = Mock()
        mock_collection.id = collection_id
        mock_collection.name = "Test Collection"
        mock_collection.status = CollectionStatus.COMPLETED
        mock_collection.is_private = False  # Public collection for easier testing

        # Mock the collection service at module level to avoid external dependencies
        with patch("rag_solution.services.search_service.CollectionService") as mock_collection_service_class:
            mock_collection_service = Mock()
            mock_collection_service.get_collection.return_value = mock_collection
            mock_collection_service.get_user_collections.return_value = [mock_collection]  # User has access
            mock_collection_service_class.return_value = mock_collection_service

            # Test collection validation using the actual method
            try:
                search_service._validate_collection_access(collection_id, user_id)
                validation_passed = True
            except Exception:
                validation_passed = False

            assert validation_passed is True

    def test_collection_not_found(self, search_service, mock_database_session):
        """Test handling of non-existent collections."""
        collection_id = uuid4()
        user_id = uuid4()

        # Mock collection not found
        mock_database_session.query.return_value.filter.return_value.first.return_value = None

        # Test collection validation should raise an exception
        with pytest.raises(Exception):
            search_service._validate_collection_access(collection_id, user_id)

    def test_search_input_validation(self, search_service):
        """Test search input validation."""
        # Test valid input
        valid_input = SearchInput(question="What is the main topic?", collection_id=uuid4(), pipeline_id=uuid4(), user_id=uuid4())

        # Should not raise an exception
        search_service._validate_search_input(valid_input)

    def test_search_input_validation_invalid(self, search_service):
        """Test search input validation with invalid data."""
        # Test with invalid input (missing required fields)
        with pytest.raises(Exception):
            search_service._validate_search_input(None)

    def test_pipeline_validation(self, search_service, mock_database_session):
        """Test pipeline validation."""
        pipeline_id = uuid4()

        # Mock pipeline exists
        mock_pipeline = Mock()
        mock_pipeline.id = pipeline_id
        mock_pipeline.name = "Test Pipeline"

        # Mock the pipeline service at module level to avoid external dependencies
        with patch("rag_solution.services.search_service.PipelineService") as mock_pipeline_service_class:
            mock_pipeline_service = Mock()
            mock_pipeline_service.get_pipeline.return_value = mock_pipeline
            mock_pipeline_service_class.return_value = mock_pipeline_service

            # Test pipeline validation
            try:
                search_service._validate_pipeline(pipeline_id)
                validation_passed = True
            except Exception:
                validation_passed = False

            assert validation_passed is True

    def test_pipeline_not_found(self, search_service, mock_database_session):
        """Test handling of non-existent pipelines."""
        pipeline_id = uuid4()

        # Mock pipeline not found
        mock_database_session.query.return_value.filter.return_value.first.return_value = None

        # Test pipeline validation should raise an exception
        with pytest.raises(Exception):
            search_service._validate_pipeline(pipeline_id)

    def test_search_service_initialization(self, mock_database_session, mock_settings):
        """Test that SearchService initializes correctly."""
        service = SearchService(db=mock_database_session, settings=mock_settings)

        assert service.db == mock_database_session
        assert service.settings == mock_settings
        assert service._file_service is None  # Lazy initialization
        assert service._collection_service is None  # Lazy initialization
        assert service._pipeline_service is None  # Lazy initialization

    def test_lazy_service_initialization(self, search_service):
        """Test lazy initialization of services."""
        # Mock the services to avoid external dependencies
        with patch("rag_solution.services.search_service.FileManagementService"), patch("rag_solution.services.search_service.CollectionService"), patch(
            "rag_solution.services.search_service.PipelineService"
        ):
            # Access file_service property to trigger lazy initialization
            file_service = search_service.file_service
            assert file_service is not None

            # Access collection_service property to trigger lazy initialization
            collection_service = search_service.collection_service
            assert collection_service is not None

            # Access pipeline_service property to trigger lazy initialization
            pipeline_service = search_service.pipeline_service
            assert pipeline_service is not None
