"""TDD Unit tests for CollectionService - RED phase: Tests that describe expected behavior."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from core.config import Settings

# Import the custom exceptions from the correct module
from core.custom_exceptions import DocumentStorageError, EmptyDocumentError, QuestionGenerationError
from rag_solution.core.exceptions import AlreadyExistsError
from rag_solution.schemas.collection_schema import CollectionInput, CollectionOutput, CollectionStatus
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.prompt_template_schema import PromptTemplateType
from rag_solution.services.collection_service import CollectionService
from vectordbs.data_types import Document, DocumentChunk
from vectordbs.error_types import CollectionError


@pytest.mark.unit
class TestCollectionServiceTDD:
    """TDD tests for CollectionService - following Red-Green-Refactor cycle."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Mock settings."""
        return Mock(spec=Settings, vector_db="milvus")

    @pytest.fixture
    def service(self, mock_db, mock_settings):
        """Create service instance with mocked dependencies."""
        with (
            patch("rag_solution.services.collection_service.CollectionRepository"),
            patch("rag_solution.services.collection_service.UserCollectionService"),
            patch("rag_solution.services.collection_service.FileManagementService"),
            patch("rag_solution.services.collection_service.VectorStoreFactory") as mock_vector_factory,
            patch("rag_solution.services.collection_service.UserProviderService"),
            patch("rag_solution.services.collection_service.PromptTemplateService"),
            patch("rag_solution.services.collection_service.LLMParametersService"),
            patch("rag_solution.services.collection_service.QuestionService"),
            patch("rag_solution.services.collection_service.LLMModelService"),
        ):
            # Mock vector store
            mock_vector_store = Mock()
            mock_vector_factory.return_value.get_datastore.return_value = mock_vector_store

            service = CollectionService(mock_db, mock_settings)

            # Replace with mocks for easier testing
            service.collection_repository = Mock()
            service.user_collection_service = Mock()
            service.file_management_service = Mock()
            service.vector_store = mock_vector_store
            service.user_provider_service = Mock()
            service.prompt_template_service = Mock()
            service.llm_parameters_service = Mock()
            service.question_service = Mock()
            service.llm_model_service = Mock()

            return service

    def test_generate_valid_collection_name_red_phase(self):
        """RED: Test collection name generation follows valid format."""
        name = CollectionService._generate_valid_collection_name()

        # Should start with 'collection_' and contain only valid characters
        assert name.startswith("collection_")
        assert all(c.isalnum() or c == "_" for c in name)
        assert len(name) > 11  # 'collection_' + some uuid chars

    def test_create_collection_success_red_phase(self, service):
        """RED: Test successful collection creation."""
        collection_input = CollectionInput(
            name="Test Collection", is_private=False, users=[uuid4()], status=CollectionStatus.CREATED
        )

        expected_collection = CollectionOutput(
            id=uuid4(),
            name="Test Collection",
            is_private=False,
            vector_db_name="collection_abc123",
            status=CollectionStatus.CREATED,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        # Mock successful creation flow
        service.collection_repository.get_by_name.return_value = None  # No existing collection
        service.collection_repository.create.return_value = expected_collection
        service.vector_store.create_collection.return_value = None

        result = service.create_collection(collection_input)

        assert result is expected_collection
        service.collection_repository.get_by_name.assert_called_once_with("Test Collection")
        service.collection_repository.create.assert_called_once()
        service.vector_store.create_collection.assert_called_once()

    def test_create_collection_already_exists_red_phase(self, service):
        """RED: Test collection creation when name already exists - should raise AlreadyExistsError."""
        collection_input = CollectionInput(
            name="Existing Collection", is_private=False, users=[uuid4()], status=CollectionStatus.CREATED
        )

        existing_collection = CollectionOutput(
            id=uuid4(),
            name="Existing Collection",
            is_private=False,
            vector_db_name="collection_existing",
            status=CollectionStatus.CREATED,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        service.collection_repository.get_by_name.return_value = existing_collection

        with pytest.raises(AlreadyExistsError) as exc_info:
            service.create_collection(collection_input)

        assert "Collection" in str(exc_info.value)
        assert "name" in str(exc_info.value)
        service.vector_store.create_collection.assert_not_called()

    def test_create_collection_vector_store_failure_red_phase(self, service):
        """RED: Test collection creation with vector store failure - should cleanup."""
        collection_input = CollectionInput(
            name="Test Collection", is_private=False, users=[uuid4()], status=CollectionStatus.CREATED
        )

        expected_collection = CollectionOutput(
            id=uuid4(),
            name="Test Collection",
            is_private=False,
            vector_db_name="collection_abc123",
            status=CollectionStatus.CREATED,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        service.collection_repository.get_by_name.return_value = None
        service.collection_repository.create.return_value = expected_collection
        service.vector_store.create_collection.side_effect = Exception("Vector store failed")
        service.vector_store.delete_collection.return_value = None

        with pytest.raises(Exception) as exc_info:
            service.create_collection(collection_input)

        assert "Vector store failed" in str(exc_info.value)
        # Should attempt cleanup
        service.vector_store.delete_collection.assert_called_once()

    def test_get_collection_success_red_phase(self, service):
        """RED: Test successful collection retrieval."""
        collection_id = uuid4()
        expected_collection = CollectionOutput(
            id=collection_id,
            name="Test Collection",
            is_private=False,
            vector_db_name="collection_abc123",
            status=CollectionStatus.CREATED,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        service.collection_repository.get.return_value = expected_collection

        result = service.get_collection(collection_id)

        assert result is expected_collection
        service.collection_repository.get.assert_called_once_with(collection_id)

    def test_update_collection_success_red_phase(self, service):
        """RED: Test successful collection update."""
        collection_id = uuid4()
        user_id_1 = uuid4()
        user_id_2 = uuid4()

        collection_update = CollectionInput(
            name="Updated Collection", is_private=True, users=[user_id_1, user_id_2], status=CollectionStatus.CREATED
        )

        existing_collection = CollectionOutput(
            id=collection_id,
            name="Old Collection",
            is_private=False,
            vector_db_name="collection_abc123",
            status=CollectionStatus.CREATED,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        updated_collection = CollectionOutput(
            id=collection_id,
            name="Updated Collection",
            is_private=True,
            vector_db_name="collection_abc123",
            status=CollectionStatus.CREATED,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        # Mock user collection outputs (existing users)
        from rag_solution.schemas.user_collection_schema import UserCollectionOutput

        existing_user_collections = [
            UserCollectionOutput(user_id=user_id_1, collection_id=collection_id, created_at="2024-01-01T00:00:00Z")
        ]

        service.collection_repository.get.side_effect = [existing_collection, updated_collection]
        service.user_collection_service.get_collection_users.return_value = existing_user_collections
        service.collection_repository.update.return_value = None
        service.user_collection_service.add_user_to_collection.return_value = None

        result = service.update_collection(collection_id, collection_update)

        assert result is updated_collection
        service.collection_repository.update.assert_called_once()
        # Should add user_id_2 (new user)
        service.user_collection_service.add_user_to_collection.assert_called_once_with(user_id_2, collection_id)

    def test_delete_collection_success_red_phase(self, service):
        """RED: Test successful collection deletion."""
        collection_id = uuid4()

        existing_collection = CollectionOutput(
            id=collection_id,
            name="Test Collection",
            is_private=False,
            vector_db_name="collection_abc123",
            status=CollectionStatus.CREATED,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        service.collection_repository.get.return_value = existing_collection
        service.user_collection_service.remove_all_users_from_collection.return_value = None
        service.collection_repository.delete.return_value = True
        service.vector_store.delete_collection.return_value = None

        result = service.delete_collection(collection_id)

        assert result is True
        service.collection_repository.delete.assert_called_once_with(collection_id)
        service.vector_store.delete_collection.assert_called_once_with("collection_abc123")

    def test_delete_collection_postgres_failure_red_phase(self, service):
        """RED: Test collection deletion when PostgreSQL delete fails - LOGIC ISSUE."""
        collection_id = uuid4()

        existing_collection = CollectionOutput(
            id=collection_id,
            name="Test Collection",
            is_private=False,
            vector_db_name="collection_abc123",
            status=CollectionStatus.CREATED,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        service.collection_repository.get.return_value = existing_collection
        service.user_collection_service.remove_all_users_from_collection.return_value = None
        service.collection_repository.delete.return_value = False  # Failed to delete

        # LOGIC ISSUE: Code raises generic Exception instead of specific error
        with pytest.raises(Exception) as exc_info:
            service.delete_collection(collection_id)

        assert "Failed to delete collection from PostgreSQL" in str(exc_info.value)
        # Vector store delete should NOT be called if PostgreSQL delete fails
        service.vector_store.delete_collection.assert_not_called()

    def test_get_user_collections_success_red_phase(self, service):
        """RED: Test successful user collections retrieval."""
        user_id = uuid4()
        collections = [
            CollectionOutput(
                id=uuid4(),
                name="Collection 1",
                is_private=False,
                vector_db_name="col1",
                status=CollectionStatus.CREATED,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            ),
            CollectionOutput(
                id=uuid4(),
                name="Collection 2",
                is_private=True,
                vector_db_name="col2",
                status=CollectionStatus.COMPLETED,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            ),
        ]

        service.collection_repository.get_user_collections.return_value = collections

        result = service.get_user_collections(user_id)

        assert result == collections
        service.collection_repository.get_user_collections.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_process_documents_success_red_phase(self, service):
        """RED: Test successful document processing."""
        file_paths = ["/path/to/doc1.pdf", "/path/to/doc2.txt"]
        collection_id = uuid4()
        vector_db_name = "collection_abc123"
        document_ids = ["doc1", "doc2"]
        user_id = uuid4()

        # Mock processed documents
        chunk1 = DocumentChunk(chunk_index=0, text="Sample text 1")
        chunk2 = DocumentChunk(chunk_index=1, text="Sample text 2")
        processed_docs = [Document(id="doc1", chunks=[chunk1]), Document(id="doc2", chunks=[chunk2])]

        # Mock successful processing
        service._process_and_ingest_documents = AsyncMock(return_value=processed_docs)
        service._extract_document_texts = Mock(return_value=["Sample text 1", "Sample text 2"])
        service._generate_collection_questions = AsyncMock(return_value=None)

        await service.process_documents(file_paths, collection_id, vector_db_name, document_ids, user_id)

        service._process_and_ingest_documents.assert_called_once_with(
            file_paths, vector_db_name, document_ids, collection_id
        )
        service._extract_document_texts.assert_called_once_with(processed_docs, collection_id)
        service._generate_collection_questions.assert_called_once_with(
            ["Sample text 1", "Sample text 2"], collection_id, user_id
        )

    def test_extract_document_texts_success_red_phase(self, service):
        """RED: Test successful document text extraction."""
        collection_id = uuid4()
        chunk1 = DocumentChunk(chunk_index=0, text="Sample text 1")
        chunk2 = DocumentChunk(chunk_index=1, text="Sample text 2")
        chunk3 = DocumentChunk(chunk_index=2, text="")  # Empty text

        processed_docs = [Document(id="doc1", chunks=[chunk1, chunk3]), Document(id="doc2", chunks=[chunk2])]

        result = service._extract_document_texts(processed_docs, collection_id)

        # Should extract only non-empty texts
        assert result == ["Sample text 1", "Sample text 2"]

    def test_extract_document_texts_no_valid_chunks_red_phase(self, service):
        """RED: Test document text extraction when no valid chunks - should raise EmptyDocumentError."""
        collection_id = uuid4()
        chunk1 = DocumentChunk(chunk_index=0, text="")  # Empty text
        chunk2 = DocumentChunk(chunk_index=1, text=None)  # None text

        processed_docs = [Document(id="doc1", chunks=[chunk1]), Document(id="doc2", chunks=[chunk2])]

        service.update_collection_status = Mock()

        with pytest.raises(EmptyDocumentError):
            service._extract_document_texts(processed_docs, collection_id)

        service.update_collection_status.assert_called_once_with(collection_id, CollectionStatus.ERROR)

    @pytest.mark.asyncio
    async def test_generate_collection_questions_success_red_phase(self, service):
        """RED: Test successful question generation."""
        document_texts = ["Sample text 1", "Sample text 2"]
        collection_id = uuid4()
        user_id = uuid4()

        # Mock dependencies
        mock_provider = Mock(name="openai")
        mock_template = Mock()
        mock_parameters = LLMParametersInput(
            name="test_params",
            description="Test parameters",
            user_id=user_id,
            temperature=0.7,
            max_new_tokens=100,
            top_p=0.9,
            top_k=40,
            repetition_penalty=1.1,
        )
        mock_questions = ["Question 1?", "Question 2?"]

        service.user_provider_service.get_user_provider.return_value = mock_provider
        service._get_question_generation_template = Mock(return_value=mock_template)
        service._get_llm_parameters_input = Mock(return_value=mock_parameters)
        service.question_service.suggest_questions = AsyncMock(return_value=mock_questions)
        service.update_collection_status = Mock()

        await service._generate_collection_questions(document_texts, collection_id, user_id)

        service.question_service.suggest_questions.assert_called_once_with(
            texts=document_texts,
            collection_id=collection_id,
            user_id=user_id,
            provider_name=mock_provider.name,
            template=mock_template,
            parameters=mock_parameters,
        )
        service.update_collection_status.assert_called_once_with(collection_id, CollectionStatus.COMPLETED)

    @pytest.mark.asyncio
    async def test_generate_collection_questions_no_provider_red_phase(self, service):
        """RED: Test question generation when no provider available."""
        document_texts = ["Sample text 1"]
        collection_id = uuid4()
        user_id = uuid4()

        service.user_provider_service.get_user_provider.return_value = None

        with pytest.raises(ValueError) as exc_info:
            await service._generate_collection_questions(document_texts, collection_id, user_id)

        assert "No LLM provider found for user" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_collection_questions_no_questions_generated_red_phase(self, service):
        """RED: Test question generation when no questions returned - should raise QuestionGenerationError."""
        document_texts = ["Sample text 1"]
        collection_id = uuid4()
        user_id = uuid4()

        mock_provider = Mock(name="openai")
        mock_template = Mock()
        mock_parameters = LLMParametersInput(
            name="test_params",
            description="Test parameters",
            user_id=user_id,
            temperature=0.7,
            max_new_tokens=100,
            top_p=0.9,
            top_k=40,
            repetition_penalty=1.1,
        )

        service.user_provider_service.get_user_provider.return_value = mock_provider
        service._get_question_generation_template = Mock(return_value=mock_template)
        service._get_llm_parameters_input = Mock(return_value=mock_parameters)
        service.question_service.suggest_questions.return_value = []  # No questions
        service.update_collection_status = Mock()

        with pytest.raises(QuestionGenerationError):
            await service._generate_collection_questions(document_texts, collection_id, user_id)

        service.update_collection_status.assert_called_once_with(collection_id, CollectionStatus.ERROR)

    def test_get_question_generation_template_success_red_phase(self, service):
        """RED: Test getting question generation template."""
        user_id = uuid4()
        expected_template = Mock()

        service.prompt_template_service.get_by_type.return_value = expected_template

        result = service._get_question_generation_template(user_id)

        assert result is expected_template
        service.prompt_template_service.get_by_type.assert_called_once_with(
            user_id, PromptTemplateType.QUESTION_GENERATION
        )

    def test_get_llm_parameters_input_success_red_phase(self, service):
        """RED: Test getting LLM parameters input."""
        user_id = uuid4()

        from rag_solution.schemas.llm_parameters_schema import LLMParametersOutput

        mock_parameters = LLMParametersOutput(
            id=uuid4(),
            name="test_params",
            description="Test parameters",
            user_id=user_id,
            temperature=0.7,
            max_new_tokens=100,
            top_p=0.9,
            top_k=40,
            repetition_penalty=1.1,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        service.llm_parameters_service.get_latest_or_default_parameters.return_value = mock_parameters

        result = service._get_llm_parameters_input(user_id)

        assert isinstance(result, LLMParametersInput)
        assert result.name == "test_params"
        assert result.user_id == user_id
        assert result.temperature == 0.7

    def test_get_llm_parameters_input_no_parameters_red_phase(self, service):
        """RED: Test getting LLM parameters when none exist."""
        user_id = uuid4()

        service.llm_parameters_service.get_latest_or_default_parameters.return_value = None

        with pytest.raises(ValueError) as exc_info:
            service._get_llm_parameters_input(user_id)

        assert "No LLM parameters found for user" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ingest_documents_success_red_phase(self, service):
        """RED: Test successful document ingestion."""
        file_paths = ["/path/to/doc1.pdf"]
        vector_db_name = "collection_abc123"
        document_ids = ["doc1"]

        chunk1 = DocumentChunk(chunk_index=0, text="Sample text 1")
        document = Document(id="doc1", chunks=[chunk1])

        with (
            patch("rag_solution.services.collection_service.multiprocessing.Manager"),
            patch("rag_solution.services.collection_service.DocumentProcessor") as mock_processor_class,
        ):
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor

            async def mock_process_document(file_path, doc_id):
                yield document

            mock_processor.process_document.return_value = mock_process_document("/path/to/doc1.pdf", "doc1")
            service.store_documents_in_vector_store = Mock()

            result = await service.ingest_documents(file_paths, vector_db_name, document_ids)

            assert result == [document]
            service.store_documents_in_vector_store.assert_called_once_with([document], vector_db_name)

    def test_store_documents_in_vector_store_success_red_phase(self, service):
        """RED: Test successful document storage in vector store."""
        chunk1 = DocumentChunk(chunk_index=0, text="Sample text 1")
        documents = [Document(id="doc1", chunks=[chunk1])]
        collection_name = "collection_abc123"

        service.vector_store.add_documents.return_value = None

        service.store_documents_in_vector_store(documents, collection_name)

        service.vector_store.add_documents.assert_called_once_with(collection_name, documents)

    def test_store_documents_in_vector_store_collection_error_red_phase(self, service):
        """RED: Test document storage with collection error."""
        chunk1 = DocumentChunk(chunk_index=0, text="Sample text 1")
        documents = [Document(id="doc1", chunks=[chunk1])]
        collection_name = "collection_abc123"

        service.vector_store.add_documents.side_effect = CollectionError("Vector store error")

        with pytest.raises(DocumentStorageError) as exc_info:
            service.store_documents_in_vector_store(documents, collection_name)

        # Check that DocumentStorageError contains the original exception message
        assert "Vector store error" in str(exc_info.value)

    def test_update_collection_status_success_red_phase(self, service):
        """RED: Test successful collection status update."""
        collection_id = uuid4()
        status = CollectionStatus.COMPLETED

        service.collection_repository.update.return_value = None

        service.update_collection_status(collection_id, status)

        service.collection_repository.update.assert_called_once_with(collection_id, {"status": status})

    def test_update_collection_status_error_handling_red_phase(self, service):
        """RED: Test collection status update error handling - should not raise."""
        collection_id = uuid4()
        status = CollectionStatus.ERROR

        service.collection_repository.update.side_effect = Exception("Database error")

        # Should not raise exception - just log error
        try:
            service.update_collection_status(collection_id, status)
        except Exception:
            pytest.fail("update_collection_status should not raise exceptions")

    def test_service_initialization_red_phase(self, mock_db, mock_settings):
        """RED: Test service initialization with all dependencies."""
        with (
            patch("rag_solution.services.collection_service.CollectionRepository"),
            patch("rag_solution.services.collection_service.VectorStoreFactory") as mock_vector_factory,
        ):
            mock_vector_store = Mock()
            mock_vector_factory.return_value.get_datastore.return_value = mock_vector_store

            service = CollectionService(mock_db, mock_settings)

            assert service.db is mock_db
            assert service.settings is mock_settings
            assert service.vector_store is mock_vector_store
            mock_vector_factory.assert_called_once_with(mock_settings)


# RED PHASE COMPLETE: These tests will reveal several logic issues:
# 1. delete_collection raises generic Exception instead of specific error for PostgreSQL failure
# 2. Complex error handling in async methods may have gaps
# 3. update_collection_status swallows all exceptions (could mask real issues)
# 4. Vector store cleanup on creation failure might not always work
# Let's run these to see what fails and needs fixing
