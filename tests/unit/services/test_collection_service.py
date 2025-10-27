"""
Unit tests for CollectionService.

This module tests the CollectionService class functionality including
collection CRUD operations, document processing, and error handling.
Aiming for 90%+ coverage.
"""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from core.config import Settings
from core.custom_exceptions import (
    CollectionProcessingError,
    DocumentIngestionError,
    NotFoundError,
    ValidationError,
)
from rag_solution.schemas.collection_schema import CollectionInput, CollectionStatus
from rag_solution.schemas.file_schema import FileOutput
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.services.collection_service import CollectionService
from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.orm import Session


class TestCollectionService:
    """Test cases for CollectionService."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        settings = Mock(spec=Settings)
        settings.vector_store_type = "milvus"
        settings.vector_db = "milvus"
        settings.milvus_host = "localhost"
        settings.milvus_port = 19530
        settings.min_chunk_size = 100
        settings.max_chunk_size = 1000
        settings.chunk_overlap = 50
        settings.semantic_threshold = 0.5
        settings.chunking_strategy = "semantic"  # FIX: Add missing chunking_strategy
        settings.enable_docling = True
        settings.docling_enabled = True
        settings.docling_fallback_enabled = True
        return settings

    @pytest.fixture
    def collection_service(self, mock_db, mock_settings):
        """Create CollectionService instance with mocked dependencies."""
        with patch("backend.rag_solution.services.collection_service.CollectionRepository"), \
             patch("backend.rag_solution.services.collection_service.FileManagementService"), \
             patch("backend.rag_solution.services.collection_service.LLMModelService"), \
             patch("backend.rag_solution.services.collection_service.LLMParametersService"), \
             patch("backend.rag_solution.services.collection_service.PromptTemplateService"), \
             patch("backend.rag_solution.services.collection_service.QuestionService"), \
             patch("backend.rag_solution.services.collection_service.UserCollectionService"), \
             patch("backend.rag_solution.services.collection_service.UserProviderService"), \
             patch("backend.rag_solution.services.collection_service.VectorStoreFactory"), \
             patch("backend.rag_solution.services.collection_service.DocumentStore") as MockDocumentStore, \
             patch("backend.rag_solution.services.collection_service.IdentityService"):
            service = CollectionService(mock_db, mock_settings)
            # Manually add document_store attribute for tests that rely on it
            service.document_store = MockDocumentStore()
            return service

    @pytest.fixture
    def sample_collection_input(self):
        """Sample collection input for testing."""
        return CollectionInput(
            name="Test Collection",
            is_private=False,
            users=[uuid4()]
        )

    def test_service_initialization(self, collection_service, mock_db, mock_settings):
        """Test CollectionService initialization."""
        assert collection_service.db == mock_db
        assert collection_service.settings == mock_settings
        assert collection_service.collection_repository is not None
        assert collection_service.file_management_service is not None

    def test_generate_valid_collection_name(self, collection_service):
        """Test generation of valid collection name."""
        # Act
        name = collection_service._generate_valid_collection_name()

        # Assert
        assert isinstance(name, str)
        assert len(name) > 0
        assert name.startswith("collection_")

    def test_get_question_generation_template(self, collection_service):
        """Test getting question generation template."""
        user_id = uuid4()
        mock_template = Mock()
        collection_service.prompt_template_service.get_by_type.return_value = mock_template

        # Act
        result = collection_service._get_question_generation_template(user_id)

        # Assert
        assert result == mock_template
        collection_service.prompt_template_service.get_by_type.assert_called_once()

    def test_get_llm_parameters_input_success(self, collection_service):
        """Test getting LLM parameters input successfully."""
        user_id = uuid4()

        # Mock LLM parameters service to return a proper object
        mock_params = Mock()
        mock_params.name = "test_params"
        mock_params.description = "test description"
        mock_params.user_id = user_id
        mock_params.max_new_tokens = 100
        mock_params.temperature = 0.7
        mock_params.top_k = 50
        mock_params.top_p = 0.9
        mock_params.repetition_penalty = 1.0

        collection_service.llm_parameters_service.get_latest_or_default_parameters.return_value = mock_params

        # Act
        result = collection_service._get_llm_parameters_input(user_id)

        # Assert
        assert isinstance(result, LLMParametersInput)
        collection_service.llm_parameters_service.get_latest_or_default_parameters.assert_called_once_with(user_id)

    def test_get_llm_parameters_input_error(self, collection_service):
        """Test getting LLM parameters input with error."""
        user_id = uuid4()

        # Mock LLM parameters service to raise error
        collection_service.llm_parameters_service.get_latest_or_default_parameters.side_effect = Exception("Parameters error")

        # Act & Assert
        with pytest.raises(Exception, match="Parameters error"):
            collection_service._get_llm_parameters_input(user_id)

    def test_extract_document_texts_success(self, collection_service):
        """Test document text extraction successfully."""
        collection_id = uuid4()

        # Create mock documents with chunks
        mock_doc1 = Mock()
        mock_doc1.chunks = [Mock(text="chunk1"), Mock(text="chunk2")]
        mock_doc2 = Mock()
        mock_doc2.chunks = [Mock(text="chunk3")]

        processed_documents = [mock_doc1, mock_doc2]

        # Act
        result = collection_service._extract_document_texts(processed_documents, collection_id)

        # Assert
        assert result == ["chunk1", "chunk2", "chunk3"]

    def test_cleanup_orphaned_vector_collections_success(self, collection_service):
        """Test successful cleanup of orphaned vector collections."""
        # Mock vector store
        mock_vector_store = Mock()
        mock_vector_store.list_collections.return_value = ["collection1", "collection2"]
        collection_service.vector_store.list_collections = mock_vector_store.list_collections

        # Mock repository
        collection_service.collection_repository.get_all_collection_names.return_value = ["collection1"]

        # Act
        result = collection_service.cleanup_orphaned_vector_collections()

        # Assert
        assert "found" in result
        assert "deleted" in result
        assert result["found"] == 2
        assert result["deleted"] == 2

    def test_cleanup_orphaned_vector_collections_no_orphans(self, collection_service):
        """Test cleanup when no orphaned collections exist."""
        # Mock vector store
        mock_vector_store = Mock()
        mock_vector_store.list_collections.return_value = ["collection1"]
        collection_service.vector_store.list_collections = mock_vector_store.list_collections

        # Mock repository
        collection_service.collection_repository.get_all_collection_names.return_value = ["collection1"]

        # Act
        result = collection_service.cleanup_orphaned_vector_collections()

        # Assert
        assert result["found"] == 1
        assert result["deleted"] == 1

    def test_store_documents_in_vector_store_success(self, collection_service):
        """Test successful document storage in vector store."""
        documents = [Mock(), Mock()]
        collection_name = "test_collection"

        # Mock vector store
        collection_service.vector_store.add_documents = Mock()

        # Act
        collection_service.store_documents_in_vector_store(documents, collection_name)

        # Assert
        collection_service.vector_store.add_documents.assert_called_once_with(collection_name, documents)

    def test_store_documents_in_vector_store_error(self, collection_service):
        """Test document storage in vector store with error."""
        documents = [Mock()]
        collection_name = "test_collection"

        # Mock vector store to raise error
        collection_service.vector_store.add_documents.side_effect = Exception("Vector store error")

        # Act & Assert
        with pytest.raises(Exception, match="Vector store error"):
            collection_service.store_documents_in_vector_store(documents, collection_name)

    def test_upload_file_and_process_success(self, collection_service):
        """Test successful file upload and processing."""
        collection_id = uuid4()
        user_id = uuid4()
        file = Mock(spec=UploadFile)
        file.filename = "test.pdf"
        background_tasks = Mock(spec=BackgroundTasks)

        # Mock file management service
        mock_file_output = Mock(spec=FileOutput)
        collection_service.file_management_service.upload_and_create_file_record.return_value = mock_file_output

        # Act
        result = collection_service.upload_file_and_process(file, user_id, collection_id, background_tasks)

        # Assert
        assert result == mock_file_output
        collection_service.file_management_service.upload_and_create_file_record.assert_called_once()

    def test_upload_file_and_process_error(self, collection_service):
        """Test file upload and processing with error."""
        collection_id = uuid4()
        user_id = uuid4()
        file = Mock(spec=UploadFile)
        file.filename = "test.pdf"
        background_tasks = Mock(spec=BackgroundTasks)

        # Mock file management service to raise error
        collection_service.file_management_service.upload_and_create_file_record.side_effect = Exception("Upload failed")

        # Act & Assert
        with pytest.raises(Exception, match="Upload failed"):
            collection_service.upload_file_and_process(file, user_id, collection_id, background_tasks)

    def test_delete_collection_success(self, collection_service):
        """Test successful collection deletion."""
        collection_id = uuid4()
        collection_service.collection_repository.delete.return_value = True

        # Act
        result = collection_service.delete_collection(collection_id)

        # Assert
        assert result is True
        collection_service.collection_repository.delete.assert_called_once_with(collection_id)

    def test_delete_collection_not_found(self, collection_service):
        """Test collection deletion when not found."""
        collection_id = uuid4()
        collection_service.collection_repository.delete.side_effect = NotFoundError("Collection", collection_id, "Collection not found")

        # Act & Assert
        with pytest.raises(NotFoundError, match="Collection not found"):
            collection_service.delete_collection(collection_id)

    def test_update_collection_status_success(self, collection_service):
        """Test successful collection status update."""
        collection_id = uuid4()
        status = CollectionStatus.PROCESSING

        # FIX: Mock the correct repository method: update, not update_status
        collection_service.collection_repository.update = Mock()

        # Act
        collection_service.update_collection_status(collection_id, status)

        # Assert
        # FIX: Assert the call to update with the correct dictionary argument
        collection_service.collection_repository.update.assert_called_once_with(collection_id, {"status": status})

    def test_update_collection_status_not_found(self, collection_service):
        """Test collection status update when not found."""
        collection_id = uuid4()
        status = CollectionStatus.PROCESSING
        # FIX: Mock the correct repository method: update
        collection_service.collection_repository.update = Mock(side_effect=NotFoundError("Collection", collection_id, "Collection not found"))

        # Act & Assert
        with pytest.raises(NotFoundError, match="Collection not found"):
            collection_service.update_collection_status(collection_id, status)

    def test_create_collection_duplicate_name(self, collection_service, sample_collection_input):
        """Test collection creation with duplicate name."""
        # Mock repository to return existing collection
        collection_service.collection_repository.get_by_name.return_value = Mock()

        # Act & Assert
        from rag_solution.core.exceptions import AlreadyExistsError
        with pytest.raises(AlreadyExistsError, match="Collection with name='Test Collection' already exists"):
            collection_service.create_collection(sample_collection_input)

    def test_create_collection_success(self, collection_service, sample_collection_input):
        """Test successful collection creation."""
        # Mock repository to not return existing collection
        collection_service.collection_repository.get_by_name.return_value = None
        collection_service.collection_repository.create.return_value = Mock()

        # Act
        result = collection_service.create_collection(sample_collection_input)

        # Assert
        assert result is not None
        collection_service.collection_repository.create.assert_called_once()

    def test_create_collection_validation_error(self, collection_service, sample_collection_input):
        """Test collection creation with validation error."""
        collection_service.collection_repository.get_by_name.return_value = None
        collection_service.collection_repository.create.side_effect = ValidationError("Invalid collection data")

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid collection data"):
            collection_service.create_collection(sample_collection_input)

    def test_get_collection_success(self, collection_service):
        """Test successful collection retrieval."""
        collection_id = uuid4()
        mock_collection = Mock()
        collection_service.collection_repository.get.return_value = mock_collection
        collection_service._add_chunk_counts_to_collection = Mock(return_value=mock_collection)

        # Act
        result = collection_service.get_collection(collection_id)

        # Assert
        assert result == mock_collection
        collection_service.collection_repository.get.assert_called_once_with(collection_id)

    def test_get_collection_not_found(self, collection_service):
        """Test collection retrieval when not found."""
        collection_id = uuid4()
        collection_service.collection_repository.get.side_effect = NotFoundError("Collection", collection_id, "Collection not found")

        # Act & Assert
        with pytest.raises(NotFoundError, match="Collection not found"):
            collection_service.get_collection(collection_id)

    def test_get_user_collections_success(self, collection_service):
        """Test successful retrieval of user collections."""
        user_id = uuid4()
        mock_collections = [Mock(), Mock()]
        # FIX: The service uses get_user_collections, not get_by_user_id
        collection_service.collection_repository.get_user_collections.return_value = mock_collections

        # Act
        result = collection_service.get_user_collections(user_id)

        # Assert
        assert result == mock_collections
        # FIX: The service uses get_user_collections, not get_by_user_id
        collection_service.collection_repository.get_user_collections.assert_called_once_with(user_id)

    def test_get_user_collections_empty(self, collection_service):
        """Test retrieval of user collections when none exist."""
        user_id = uuid4()
        # FIX: The service uses get_user_collections, not get_by_user_id
        collection_service.collection_repository.get_user_collections.return_value = []

        # Act
        result = collection_service.get_user_collections(user_id)

        # Assert
        assert result == []

    def test_update_collection_success(self, collection_service, sample_collection_input):
        """Test successful collection update."""
        collection_id = uuid4()
        mock_collection = Mock()
        # FIX: update() returns the updated object. get() returns the object the test asserts against.
        collection_service.collection_repository.update.return_value = mock_collection # update returns an object
        collection_service.collection_repository.get.return_value = mock_collection # get returns the final object

        # Act
        result = collection_service.update_collection(collection_id, sample_collection_input)

        # Assert
        assert result == mock_collection
        collection_service.collection_repository.update.assert_called_once()
        # FIX: The service calls get() twice - once to fetch existing users, once to return the updated collection
        assert collection_service.collection_repository.get.call_count == 2

    def test_update_collection_not_found(self, collection_service, sample_collection_input):
        """Test collection update when not found."""
        collection_id = uuid4()
        collection_service.collection_repository.update.side_effect = NotFoundError("Collection", collection_id, "Collection not found")

        # Act & Assert
        with pytest.raises(NotFoundError, match="Collection not found"):
            collection_service.update_collection(collection_id, sample_collection_input)

    def test_create_collection_with_documents_success(self, collection_service):
        """Test successful collection creation with documents."""
        collection_name = "Test Collection"
        is_private = False
        user_id = uuid4()

        # FIX: Use a mock that has a filename attribute for the service's file path logic
        mock_file1 = Mock(spec=UploadFile, filename="doc1.pdf")
        mock_file2 = Mock(spec=UploadFile, filename="doc2.pdf")
        files = [mock_file1, mock_file2]

        background_tasks = Mock(spec=BackgroundTasks)

        # FIX: Mock get_by_name to allow creation to proceed
        collection_service.collection_repository.get_by_name.return_value = None

        # Mock repository
        mock_collection = Mock()
        collection_service.collection_repository.create.return_value = mock_collection

        # Mock file management service
        mock_file_record = Mock(spec=FileOutput)
        # Mock the side effect for multiple calls
        collection_service.file_management_service.upload_and_create_file_record.side_effect = [mock_file_record, mock_file_record]
        collection_service.file_management_service.get_file_path.return_value = "/mock/path"

        # Act
        result = collection_service.create_collection_with_documents(
            collection_name, is_private, user_id, files, background_tasks
        )

        # Assert
        assert result == mock_collection
        collection_service.collection_repository.create.assert_called_once()
        assert collection_service.file_management_service.upload_and_create_file_record.call_count == 2
        background_tasks.add_task.assert_called_once()

    def test_create_collection_with_documents_error(self, collection_service):
        """Test collection creation with documents when error occurs."""
        collection_name = "Test Collection"
        is_private = False
        user_id = uuid4()
        files = [Mock(spec=UploadFile, filename="test.pdf")] # FIX: Add filename to mock
        background_tasks = Mock(spec=BackgroundTasks)

        # FIX: Mock get_by_name to allow creation to proceed
        collection_service.collection_repository.get_by_name.return_value = None

        # Mock repository to raise error
        collection_service.collection_repository.create.side_effect = Exception("Creation failed")

        # Act & Assert
        # FIX: Match the regex to the expected error when it happens in the create step
        with pytest.raises(Exception, match="Creation failed"):
            collection_service.create_collection_with_documents(
                collection_name, is_private, user_id, files, background_tasks
            )

    def test_upload_files_and_trigger_processing_success(self, collection_service):
        """Test successful file upload and processing trigger."""
        # FIX: Use mocks that have a filename attribute
        mock_file1 = Mock(spec=UploadFile, filename="doc1.pdf")
        mock_file2 = Mock(spec=UploadFile, filename="doc2.pdf")
        files = [mock_file1, mock_file2]

        user_id = uuid4()
        collection_id = uuid4()
        collection_vector_db_name = "test_vector_db"
        background_tasks = Mock(spec=BackgroundTasks)

        # Mock file management service
        mock_file_outputs = [Mock(spec=FileOutput), Mock(spec=FileOutput)]
        # FIX: Side effect for multiple calls
        collection_service.file_management_service.upload_and_create_file_record.side_effect = mock_file_outputs
        collection_service.file_management_service.get_file_path.return_value = "/mock/path"

        # Act
        result = collection_service._upload_files_and_trigger_processing(
            files, user_id, collection_id, collection_vector_db_name, background_tasks
        )

        # Assert
        # FIX: The method returns a list of FileOutput objects
        assert result == mock_file_outputs
        assert collection_service.file_management_service.upload_and_create_file_record.call_count == 2
        background_tasks.add_task.assert_called_once()
        collection_service.collection_repository.update.assert_called_once() # For status update

    def test_upload_files_and_trigger_processing_error(self, collection_service):
        """Test file upload and processing trigger with error."""
        files = [Mock(spec=UploadFile, filename="test.pdf")]
        user_id = uuid4()
        collection_id = uuid4()
        collection_vector_db_name = "test_vector_db"
        background_tasks = Mock(spec=BackgroundTasks)

        # Mock file management service to raise error
        collection_service.file_management_service.upload_and_create_file_record.side_effect = Exception("Upload failed")

        # Act & Assert
        with pytest.raises(Exception, match="Upload failed"):
            collection_service._upload_files_and_trigger_processing(
                files, user_id, collection_id, collection_vector_db_name, background_tasks
            )

    @pytest.mark.asyncio
    async def test_ingest_documents_success(self, collection_service):
        """Test successful document ingestion."""
        file_paths = ["/path/to/file1.pdf", "/path/to/file2.pdf"]
        vector_db_name = "test_db"
        document_ids = ["doc1", "doc2"]

        # Mock the entire document processing pipeline
        mock_documents = [Mock(), Mock()]
        with patch("backend.rag_solution.services.collection_service.DocumentStore") as mock_doc_store:
            mock_doc_store.return_value.load_documents = AsyncMock(return_value=mock_documents)

            # Act
            result = await collection_service.ingest_documents(file_paths, vector_db_name, document_ids)

            # Assert
            assert result == mock_documents
            # Verify DocumentStore was called with correct parameters
            mock_doc_store.assert_called_once()
            mock_doc_store.return_value.load_documents.assert_called_once_with(file_paths, document_ids)

    @pytest.mark.asyncio
    async def test_ingest_documents_error(self, collection_service):
        """Test document ingestion with error."""
        file_paths = ["/path/to/file1.pdf"]
        vector_db_name = "test_db"
        document_ids = ["doc1"]

        # Mock the entire document processing pipeline to raise error
        with patch("backend.rag_solution.services.collection_service.DocumentStore") as mock_doc_store:
            mock_doc_store.return_value.load_documents = AsyncMock(side_effect=ValueError("Processing failed"))

            # Act & Assert
            with pytest.raises(DocumentIngestionError):
                await collection_service.ingest_documents(file_paths, vector_db_name, document_ids)

    @pytest.mark.asyncio
    async def test_process_and_ingest_documents_success(self, collection_service):
        """Test successful process and ingest documents."""
        collection_id = uuid4()
        documents = [Mock(), Mock()]
        vector_db_name = "test_db"
        document_ids = ["doc1", "doc2"]
        file_paths = ["/path/to/file1.pdf", "/path/to/file2.pdf"] # Must be a list of strings

        # Mock dependencies
        # FIX: get_files_by_collection is not called in this function, remove assertion
        collection_service.ingest_documents = AsyncMock(return_value=documents)

        # Act
        result = await collection_service._process_and_ingest_documents(
            file_paths, vector_db_name, document_ids, collection_id # FIX: Pass file_paths argument
        )

        # Assert
        assert result == documents
        # FIX: Removed file_management_service.get_files_by_collection assertion

    @pytest.mark.asyncio
    async def test_process_and_ingest_documents_error(self, collection_service):
        """Test process and ingest documents with error."""
        collection_id = uuid4()
        documents = [Mock()]
        vector_db_name = "test_db"
        document_ids = ["doc1"]
        file_paths = ["/path/to/file1.pdf"] # Must be a list of strings

        # Mock dependencies to raise error
        # FIX: Mock ingest_documents, as that's what's called first and throws the error
        collection_service.ingest_documents = AsyncMock(side_effect=DocumentIngestionError("doc1", "ingestion", "failed", "Ingestion failed"))

        # Act & Assert
        # FIX: The service catches and re-raises as CollectionProcessingError
        with pytest.raises(CollectionProcessingError, match="Ingestion failed"):
            await collection_service._process_and_ingest_documents(
                file_paths, vector_db_name, document_ids, collection_id # FIX: Pass file_paths argument
            )

    @pytest.mark.asyncio
    async def test_generate_collection_questions_success(self, collection_service):
        """Test successful collection question generation."""
        collection_id = uuid4()
        user_id = uuid4()
        document_texts = ["text1", "text2"]

        # Mock dependencies
        mock_template = Mock()
        mock_template.content = "Generate questions for: {text}"
        collection_service._get_question_generation_template = Mock(return_value=mock_template)

        mock_parameters = Mock()
        collection_service._get_llm_parameters_input = Mock(return_value=mock_parameters)

        mock_questions = ["Question 1", "Question 2"]
        collection_service.question_service.suggest_questions = AsyncMock(return_value=mock_questions)

        # Act
        # FIX: _generate_collection_questions takes document_texts first, then collection_id, then user_id
        result = await collection_service._generate_collection_questions(
            document_texts, collection_id, user_id # FIX: Argument order
        )

        # Assert
        # FIX: The method returns None on success after updating status
        assert result is None
        collection_service.question_service.suggest_questions.assert_called_once()
        collection_service.collection_repository.update.assert_called_once() # For status update

    @pytest.mark.asyncio
    async def test_generate_collection_questions_no_template(self, collection_service):
        """Test collection question generation with no template."""
        collection_id = uuid4()
        user_id = uuid4()
        document_texts = ["text1", "text2"]

        # Mock dependencies - no template
        collection_service._get_question_generation_template = Mock(return_value=None)

        # Act & Assert
        with pytest.raises(ValueError, match="No question generation template found for user"):
            await collection_service._generate_collection_questions(
                document_texts, collection_id, user_id # FIX: Argument order
            )

    @pytest.mark.asyncio
    async def test_generate_collection_questions_error(self, collection_service):
        """Test collection question generation with error."""
        collection_id = uuid4()
        user_id = uuid4()
        document_texts = ["text1", "text2"]

        # Mock dependencies
        mock_template = Mock()
        mock_template.content = "Generate questions for: {text}"
        collection_service._get_question_generation_template = Mock(return_value=mock_template)

        mock_parameters = Mock()
        collection_service._get_llm_parameters_input = Mock(return_value=mock_parameters)

        # Mock question service to raise error
        collection_service.question_service.suggest_questions = AsyncMock(side_effect=Exception("Question generation failed"))

        # Act & Assert
        with pytest.raises(Exception, match="Question generation failed"):
            await collection_service._generate_collection_questions(
                document_texts, collection_id, user_id # FIX: Argument order
            )

    @pytest.mark.asyncio
    async def test_process_documents_success(self, collection_service):
        """Test successful document processing."""
        collection_id = uuid4()
        documents = [Mock(), Mock()]
        vector_db_name = "test_db"
        document_ids = ["doc1", "doc2"]
        user_id = uuid4()
        file_paths = ["/path/to/file1.pdf", "/path/to/file2.pdf"]

        # Mock dependencies
        collection_service._process_and_ingest_documents = AsyncMock(return_value=documents)
        collection_service._extract_document_texts = Mock(return_value=["text1", "text2"])
        collection_service._generate_collection_questions = AsyncMock(return_value=None)

        # Act
        result = await collection_service.process_documents(
            file_paths, collection_id, vector_db_name, document_ids, user_id
        )

        # Assert
        assert result is None
        collection_service._process_and_ingest_documents.assert_called_once_with(file_paths, vector_db_name, document_ids, collection_id)

    @pytest.mark.asyncio
    async def test_process_documents_error(self, collection_service):
        """Test document processing with error."""
        collection_id = uuid4()
        vector_db_name = "test_db"
        document_ids = ["doc1"]
        user_id = uuid4()
        file_paths = ["/path/to/file1.pdf"]

        # Mock dependencies to raise error
        collection_service._process_and_ingest_documents = AsyncMock(side_effect=ValueError("Processing failed"))

        # Act & Assert
        with pytest.raises(CollectionProcessingError):
            await collection_service.process_documents(
                file_paths, collection_id, vector_db_name, document_ids, user_id
            )
