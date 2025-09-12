"""TDD Unit tests for SearchService - RED phase: Tests that describe expected behavior."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from sqlalchemy.orm import Session
from fastapi import HTTPException

from core.config import Settings
from rag_solution.services.search_service import SearchService, handle_search_errors
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.schemas.collection_schema import CollectionOutput, CollectionStatus
from core.custom_exceptions import ConfigurationError, LLMProviderError, NotFoundError, ValidationError
from vectordbs.data_types import QueryResult


@pytest.mark.unit
class TestSearchServiceTDD:
    """TDD tests for SearchService - following Red-Green-Refactor cycle."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Mock settings."""
        return Mock(spec=Settings)

    @pytest.fixture
    def service(self, mock_db, mock_settings):
        """Create service instance with mocked dependencies."""
        service = SearchService(mock_db, mock_settings)

        # Mock the lazy-loaded services
        service._file_service = Mock()
        service._collection_service = Mock()
        service._pipeline_service = Mock()

        return service

    def test_service_initialization_red_phase(self, mock_db, mock_settings):
        """RED: Test service initialization sets up dependencies correctly."""
        service = SearchService(mock_db, mock_settings)

        assert service.db is mock_db
        assert service.settings is mock_settings
        # Services should be None initially (lazy loading)
        assert service._file_service is None
        assert service._collection_service is None
        assert service._pipeline_service is None

    def test_lazy_loading_file_service_red_phase(self, service, mock_db, mock_settings):
        """RED: Test lazy loading of file management service."""
        # Reset to None to test lazy loading
        service._file_service = None

        with patch("rag_solution.services.search_service.FileManagementService") as mock_service_class:
            mock_instance = Mock()
            mock_service_class.return_value = mock_instance

            result = service.file_service

            assert result is mock_instance
            mock_service_class.assert_called_once_with(mock_db, mock_settings)
            # Second access should return cached instance
            result2 = service.file_service
            assert result2 is mock_instance
            # Should only be called once due to caching
            assert mock_service_class.call_count == 1

    def test_lazy_loading_collection_service_red_phase(self, service, mock_db, mock_settings):
        """RED: Test lazy loading of collection service."""
        service._collection_service = None

        with patch("rag_solution.services.search_service.CollectionService") as mock_service_class:
            mock_instance = Mock()
            mock_service_class.return_value = mock_instance

            result = service.collection_service

            assert result is mock_instance
            mock_service_class.assert_called_once_with(mock_db, mock_settings)

    def test_lazy_loading_pipeline_service_red_phase(self, service, mock_db, mock_settings):
        """RED: Test lazy loading of pipeline service."""
        service._pipeline_service = None

        with patch("rag_solution.services.search_service.PipelineService") as mock_service_class:
            mock_instance = Mock()
            mock_service_class.return_value = mock_instance

            result = service.pipeline_service

            assert result is mock_instance
            mock_service_class.assert_called_once_with(mock_db, mock_settings)

    @pytest.mark.asyncio
    async def test_initialize_pipeline_success_red_phase(self, service):
        """RED: Test successful pipeline initialization."""
        collection_id = uuid4()
        collection = CollectionOutput(
            id=collection_id,
            name="Test Collection",
            is_private=False,
            vector_db_name="test_collection_vector",
            status=CollectionStatus.COMPLETED,
            user_ids=[],
            files=[],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        service._collection_service.get_collection.return_value = collection
        service._pipeline_service.initialize = AsyncMock()

        result = await service._initialize_pipeline(collection_id)

        assert result == "test_collection_vector"
        service._collection_service.get_collection.assert_called_once_with(collection_id)
        service._pipeline_service.initialize.assert_called_once_with("test_collection_vector", collection_id)

    @pytest.mark.asyncio
    async def test_initialize_pipeline_collection_not_found_red_phase(self, service):
        """RED: Test pipeline initialization when collection not found."""
        collection_id = uuid4()

        service._collection_service.get_collection.return_value = None

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await service._initialize_pipeline(collection_id)

        assert exc_info.value.status_code == 404
        assert "Collection" in exc_info.value.detail
        assert str(collection_id) in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_initialize_pipeline_initialization_fails_red_phase(self, service):
        """RED: Test pipeline initialization when pipeline service fails."""
        collection_id = uuid4()
        collection = CollectionOutput(
            id=collection_id,
            name="Test Collection",
            is_private=False,
            vector_db_name="test_collection_vector",
            status=CollectionStatus.COMPLETED,
            user_ids=[],
            files=[],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        service._collection_service.get_collection.return_value = collection
        service._pipeline_service.initialize = AsyncMock(side_effect=Exception("Pipeline init failed"))

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await service._initialize_pipeline(collection_id)

        assert exc_info.value.status_code == 500
        assert "Pipeline initialization failed" in exc_info.value.detail

    def test_generate_document_metadata_success_red_phase(self, service):
        """RED: Test successful document metadata generation."""
        collection_id = uuid4()
        doc_id_1 = "doc1"
        doc_id_2 = "doc2"

        from vectordbs.data_types import DocumentChunk

        query_results = [
            QueryResult(chunk=DocumentChunk(chunk_id="chunk1", text="Sample text 1", document_id=doc_id_1, page_number=1), score=0.9),
            QueryResult(chunk=DocumentChunk(chunk_id="chunk2", text="Sample text 2", document_id=doc_id_2, page_number=2), score=0.8),
        ]

        # Mock file metadata
        from rag_solution.schemas.file_schema import FileOutput, FileMetadata

        files = [
            FileOutput(
                id=uuid4(),
                filename="doc1.pdf",
                document_id=doc_id_1,
                collection_id=collection_id,
                user_id=uuid4(),
                size=1024,
                file_path="/path/to/doc1.pdf",
                metadata=FileMetadata(total_pages=5, total_chunks=10, keywords=["keyword1", "keyword2"]),
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            ),
            FileOutput(
                id=uuid4(),
                filename="doc2.txt",
                document_id=doc_id_2,
                collection_id=collection_id,
                user_id=uuid4(),
                size=512,
                file_path="/path/to/doc2.txt",
                metadata=FileMetadata(total_pages=1, total_chunks=5, keywords=["keyword3"]),
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            ),
        ]

        # Mock the file service by setting the internal attribute
        mock_file_service = Mock()
        mock_file_service.get_files_by_collection.return_value = files
        service._file_service = mock_file_service

        result = service._generate_document_metadata(query_results, collection_id)

        assert len(result) == 2
        # Should contain metadata for both documents
        doc_names = [metadata.document_name for metadata in result]
        assert "doc1.pdf" in doc_names
        assert "doc2.txt" in doc_names

    def test_generate_document_metadata_no_query_results_red_phase(self, service):
        """RED: Test document metadata generation with no query results."""
        collection_id = uuid4()
        query_results = []

        result = service._generate_document_metadata(query_results, collection_id)

        assert result == []
        # Should not even call file service if no query results
        service._file_service.get_files_by_collection.assert_not_called()

    def test_generate_document_metadata_missing_files_red_phase(self, service):
        """RED: Test document metadata generation when files not found - should raise ConfigurationError."""
        from vectordbs.data_types import DocumentChunk, QueryResult

        collection_id = uuid4()
        # Create proper QueryResult with DocumentChunk
        chunk = DocumentChunk(chunk_id="chunk1", text="Sample text", document_id="doc1")
        query_results = [
            QueryResult(chunk=chunk, score=0.9),
        ]

        service._file_service.get_files_by_collection.return_value = []  # No files found

        with pytest.raises(ConfigurationError) as exc_info:
            service._generate_document_metadata(query_results, collection_id)

        assert "No files found for collection" in str(exc_info.value)

    def test_generate_document_metadata_missing_document_metadata_red_phase(self, service):
        """RED: Test when document referenced in results but not found in metadata - should raise ConfigurationError."""
        from vectordbs.data_types import DocumentChunk, QueryResult

        collection_id = uuid4()
        # Create proper QueryResult with DocumentChunk
        chunk = DocumentChunk(chunk_id="chunk1", text="Sample text", document_id="missing_doc")
        query_results = [
            QueryResult(chunk=chunk, score=0.9),
        ]

        # Files exist but don't include the referenced document
        from rag_solution.schemas.file_schema import FileOutput

        files = [
            FileOutput(
                id=uuid4(),
                filename="other_doc.pdf",
                document_id="other_doc",
                collection_id=collection_id,
                user_id=uuid4(),
                size=1024,
                file_path="/path/to/other_doc.pdf",
                metadata=None,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            )
        ]

        service._file_service.get_files_by_collection.return_value = files

        with pytest.raises(ConfigurationError) as exc_info:
            service._generate_document_metadata(query_results, collection_id)

        assert "Documents not found in collection metadata" in str(exc_info.value)
        assert "missing_doc" in str(exc_info.value)

    def test_clean_generated_answer_success_red_phase(self, service):
        """RED: Test answer cleaning functionality."""
        # Test basic cleaning
        answer = "This is AND a test AND answer"
        result = service._clean_generated_answer(answer)
        assert result == "This is a test answer"

        # Test deduplication
        answer_with_duplicates = "This This is a test test answer"
        result = service._clean_generated_answer(answer_with_duplicates)
        assert result == "This is a test answer"

        # Test combination
        complex_answer = "This AND is AND a test test answer AND"
        result = service._clean_generated_answer(complex_answer)
        assert result == "This is a test answer"

    def test_validate_search_input_success_red_phase(self, service):
        """RED: Test successful search input validation."""
        search_input = SearchInput(question="What is the capital of France?", collection_id=uuid4(), pipeline_id=uuid4(), user_id=uuid4())

        # Should not raise any exception
        service._validate_search_input(search_input)

    def test_validate_search_input_empty_question_red_phase(self, service):
        """RED: Test search input validation with empty question - should raise ValidationError."""
        search_input = SearchInput(question="", collection_id=uuid4(), pipeline_id=uuid4(), user_id=uuid4())

        with pytest.raises(ValidationError) as exc_info:
            service._validate_search_input(search_input)

        assert "Query cannot be empty" in str(exc_info.value)

    def test_validate_search_input_whitespace_only_question_red_phase(self, service):
        """RED: Test search input validation with whitespace-only question."""
        search_input = SearchInput(question="   ", collection_id=uuid4(), pipeline_id=uuid4(), user_id=uuid4())

        with pytest.raises(ValidationError):
            service._validate_search_input(search_input)

    def test_validate_collection_access_public_collection_red_phase(self, service):
        """RED: Test collection access validation for public collection."""
        collection_id = uuid4()
        user_id = uuid4()

        collection = CollectionOutput(
            id=collection_id,
            name="Public Collection",
            is_private=False,
            vector_db_name="public_collection",
            status=CollectionStatus.COMPLETED,
            user_ids=[],
            files=[],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        service._collection_service.get_collection.return_value = collection

        # Should not raise any exception for public collection
        service._validate_collection_access(collection_id, user_id)

    def test_validate_collection_access_private_collection_with_access_red_phase(self, service):
        """RED: Test collection access validation for private collection with user access."""
        collection_id = uuid4()
        user_id = uuid4()

        collection = CollectionOutput(
            id=collection_id,
            name="Private Collection",
            is_private=True,
            vector_db_name="private_collection",
            status=CollectionStatus.COMPLETED,
            user_ids=[],
            files=[],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        # User has access to this collection
        user_collections = [collection]

        service._collection_service.get_collection.return_value = collection
        service._collection_service.get_user_collections.return_value = user_collections

        # Should not raise any exception
        service._validate_collection_access(collection_id, user_id)

    def test_validate_collection_access_private_collection_without_access_red_phase(self, service):
        """RED: Test collection access validation for private collection without user access."""
        collection_id = uuid4()
        user_id = uuid4()

        collection = CollectionOutput(
            id=collection_id,
            name="Private Collection",
            is_private=True,
            vector_db_name="private_collection",
            status=CollectionStatus.COMPLETED,
            user_ids=[],
            files=[],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        # User has no collections or doesn't have access to this one
        user_collections = []

        service._collection_service.get_collection.return_value = collection
        service._collection_service.get_user_collections.return_value = user_collections

        with pytest.raises(NotFoundError) as exc_info:
            service._validate_collection_access(collection_id, user_id)

        assert "Collection not found or access denied" in str(exc_info.value)

    def test_validate_collection_access_collection_not_found_red_phase(self, service):
        """RED: Test collection access validation when collection doesn't exist."""
        collection_id = uuid4()
        user_id = uuid4()

        service._collection_service.get_collection.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            service._validate_collection_access(collection_id, user_id)

        assert "Collection" in str(exc_info.value)
        assert str(collection_id) in str(exc_info.value)

    def test_validate_pipeline_success_red_phase(self, service):
        """RED: Test successful pipeline validation."""
        pipeline_id = uuid4()
        mock_config = Mock()

        service._pipeline_service.get_pipeline_config.return_value = mock_config

        # Should not raise any exception
        service._validate_pipeline(pipeline_id)
        service._pipeline_service.get_pipeline_config.assert_called_once_with(pipeline_id)

    def test_validate_pipeline_not_found_red_phase(self, service):
        """RED: Test pipeline validation when pipeline config not found."""
        pipeline_id = uuid4()

        service._pipeline_service.get_pipeline_config.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            service._validate_pipeline(pipeline_id)

        assert "Pipeline" in str(exc_info.value)
        assert str(pipeline_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_success_red_phase(self, service):
        """RED: Test successful search operation end-to-end."""
        search_input = SearchInput(question="What is machine learning?", collection_id=uuid4(), pipeline_id=uuid4(), user_id=uuid4())

        # Mock all validation methods to pass
        service._validate_search_input = Mock()
        service._validate_collection_access = Mock()
        service._validate_pipeline = Mock()
        service._initialize_pipeline = AsyncMock(return_value="test_collection")

        # Mock pipeline execution
        from rag_solution.schemas.pipeline_schema import PipelineResult

        pipeline_result = PipelineResult(success=True, generated_answer="Machine learning is AI", query_results=[], rewritten_query="machine learning definition", evaluation=None, error=None)

        service._pipeline_service.execute_pipeline = AsyncMock(return_value=pipeline_result)
        service._generate_document_metadata = Mock(return_value=[])
        service._clean_generated_answer = Mock(return_value="Machine learning is AI")

        result = await service.search(search_input)

        assert isinstance(result, SearchOutput)
        assert result.answer == "Machine learning is AI"
        assert result.documents == []
        assert result.rewritten_query == "machine learning definition"

        # Verify all validations were called
        service._validate_search_input.assert_called_once_with(search_input)
        service._validate_collection_access.assert_called_once_with(search_input.collection_id, search_input.user_id)
        service._validate_pipeline.assert_called_once_with(search_input.pipeline_id)

    @pytest.mark.asyncio
    async def test_search_pipeline_execution_fails_red_phase(self, service):
        """RED: Test search when pipeline execution fails."""
        search_input = SearchInput(question="What is machine learning?", collection_id=uuid4(), pipeline_id=uuid4(), user_id=uuid4())

        # Mock validations to pass
        service._validate_search_input = Mock()
        service._validate_collection_access = Mock()
        service._validate_pipeline = Mock()
        service._initialize_pipeline = AsyncMock(return_value="test_collection")

        # Mock pipeline execution failure
        from rag_solution.schemas.pipeline_schema import PipelineResult

        pipeline_result = PipelineResult(success=False, generated_answer=None, query_results=None, rewritten_query=None, evaluation=None, error="Pipeline execution failed")

        service._pipeline_service.execute_pipeline = AsyncMock(return_value=pipeline_result)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await service.search(search_input)

        assert exc_info.value.status_code == 500
        assert "Pipeline execution failed" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_search_with_null_pipeline_results_red_phase(self, service):
        """RED: Test search handles null pipeline results gracefully."""
        search_input = SearchInput(question="What is machine learning?", collection_id=uuid4(), pipeline_id=uuid4(), user_id=uuid4())

        # Mock validations
        service._validate_search_input = Mock()
        service._validate_collection_access = Mock()
        service._validate_pipeline = Mock()
        service._initialize_pipeline = AsyncMock(return_value="test_collection")

        # Mock pipeline result with null values
        from rag_solution.schemas.pipeline_schema import PipelineResult

        pipeline_result = PipelineResult(success=True, generated_answer=None, query_results=None, rewritten_query=None, evaluation=None, error=None)

        service._pipeline_service.execute_pipeline = AsyncMock(return_value=pipeline_result)
        service._generate_document_metadata = Mock(return_value=[])
        service._clean_generated_answer = Mock(return_value="")

        result = await service.search(search_input)

        # Should handle null values gracefully
        assert result.answer == ""
        assert result.query_results == []
        service._generate_document_metadata.assert_called_once_with([], search_input.collection_id)

    def test_handle_search_errors_decorator_not_found_error_red_phase(self):
        """RED: Test error handler decorator converts NotFoundError to HTTPException."""

        @handle_search_errors
        async def mock_function():
            raise NotFoundError("Resource", "123")

        with pytest.raises(HTTPException) as exc_info:
            import asyncio

            asyncio.run(mock_function())

        assert exc_info.value.status_code == 404
        assert "Resource" in str(exc_info.value.detail)

    def test_handle_search_errors_decorator_validation_error_red_phase(self):
        """RED: Test error handler decorator converts ValidationError to HTTPException."""

        @handle_search_errors
        async def mock_function():
            raise ValidationError("Invalid input")

        with pytest.raises(HTTPException) as exc_info:
            import asyncio

            asyncio.run(mock_function())

        assert exc_info.value.status_code == 400
        assert "Invalid input" in str(exc_info.value.detail)

    def test_handle_search_errors_decorator_llm_provider_error_red_phase(self):
        """RED: Test error handler decorator converts LLMProviderError to HTTPException."""

        @handle_search_errors
        async def mock_function():
            raise LLMProviderError("provider", "operation", "reason")

        with pytest.raises(HTTPException) as exc_info:
            import asyncio

            asyncio.run(mock_function())

        assert exc_info.value.status_code == 500

    def test_handle_search_errors_decorator_unexpected_error_red_phase(self):
        """RED: Test error handler decorator converts unexpected errors to HTTPException."""

        @handle_search_errors
        async def mock_function():
            raise Exception("Unexpected error")

        with pytest.raises(HTTPException) as exc_info:
            import asyncio

            asyncio.run(mock_function())

        assert exc_info.value.status_code == 500
        assert "Error processing search" in str(exc_info.value.detail)

    def test_search_time_tracking_logic_issue_red_phase(self, service):
        """RED: Test search method has logic issue - time.time() called but result not used."""
        search_input = SearchInput(question="Test question", collection_id=uuid4(), pipeline_id=uuid4(), user_id=uuid4())

        with patch("rag_solution.services.search_service.time.time") as mock_time:
            mock_time.return_value = 12345.67

            # Mock all methods to avoid actual execution
            service._validate_search_input = Mock()
            service._validate_collection_access = Mock()
            service._validate_pipeline = Mock()
            service._initialize_pipeline = AsyncMock(return_value="test")

            from rag_solution.schemas.pipeline_schema import PipelineResult

            pipeline_result = PipelineResult(success=True, generated_answer="Answer", query_results=[], rewritten_query="query", evaluation=None, error=None)
            service._pipeline_service.execute_pipeline = AsyncMock(return_value=pipeline_result)
            service._generate_document_metadata = Mock(return_value=[])
            service._clean_generated_answer = Mock(return_value="Answer")

            import asyncio

            result = asyncio.run(service.search(search_input))

            # Verify time.time() is called at least twice (start and end, plus possible logging calls)
            assert mock_time.call_count >= 2
            # The result should now contain timing information
            assert hasattr(result, "execution_time")
            assert result.execution_time is not None


# RED PHASE COMPLETE: These tests will reveal several logic issues:
# 1. time.time() called but result never used (dead code)
# 2. Complex error handling may have gaps
# 3. Lazy loading pattern may have initialization issues
# 4. Private collection access logic may be flawed
# Let's run these to see what fails and needs fixing
