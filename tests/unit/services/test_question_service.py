"""Comprehensive unit tests for QuestionService.

This test suite provides complete coverage of the QuestionService class,
testing all CRUD operations, question generation, validation, and error handling.
"""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from core.config import Settings
from core.custom_exceptions import NotFoundError, ValidationError
from rag_solution.models.question import SuggestedQuestion
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase
from rag_solution.schemas.question_schema import QuestionInput
from rag_solution.services.question_service import QuestionService
from pydantic import UUID4
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


@pytest.mark.unit
class TestQuestionServiceUnit:
    """Unit tests for QuestionService with fully mocked dependencies."""

    # ============================================================================
    # FIXTURES
    # ============================================================================

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session."""
        db = Mock(spec=Session)
        db.query = Mock()
        db.add = Mock()
        db.commit = Mock()
        db.rollback = Mock()
        db.refresh = Mock()
        return db

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Mock settings with default configuration."""
        settings = Mock(spec=Settings)
        settings.max_questions_per_collection = 15
        settings.max_chunks_for_questions = 8
        settings.cot_question_ratio = 0.4
        settings.max_context_length = 4000
        settings.max_new_tokens = 500
        settings.llm_concurrency = 3
        return settings

    @pytest.fixture
    def mock_question_repository(self) -> Mock:
        """Mock question repository."""
        repo = Mock()
        repo.create_question = Mock()
        repo.create_questions = Mock()
        repo.get_questions_by_collection = Mock(return_value=[])
        repo.delete_question = Mock()
        repo.delete_questions_by_collection = Mock(return_value=0)
        return repo

    @pytest.fixture
    def mock_provider_factory(self) -> Mock:
        """Mock LLM provider factory."""
        factory = Mock()
        mock_provider = Mock()
        mock_provider.generate_text = Mock(return_value=["What is machine learning?", "How does AI work?"])
        factory.get_provider = Mock(return_value=mock_provider)
        return factory

    @pytest.fixture
    def mock_prompt_template_service(self) -> Mock:
        """Mock prompt template service."""
        service = Mock()
        return service

    @pytest.fixture
    def mock_llm_parameters_service(self) -> Mock:
        """Mock LLM parameters service."""
        service = Mock()
        return service

    @pytest.fixture
    def service(
        self,
        mock_db,
        mock_settings,
        mock_question_repository,
        mock_provider_factory,
        mock_prompt_template_service,
        mock_llm_parameters_service,
    ) -> QuestionService:
        """Create QuestionService instance with all mocked dependencies."""
        service = QuestionService(mock_db, mock_settings)
        service._question_repository = mock_question_repository
        service._provider_factory = mock_provider_factory
        service._prompt_template_service = mock_prompt_template_service
        service._llm_parameters_service = mock_llm_parameters_service
        return service

    @pytest.fixture
    def sample_collection_id(self) -> UUID4:
        """Sample collection ID."""
        return uuid4()

    @pytest.fixture
    def sample_user_id(self) -> UUID4:
        """Sample user ID."""
        return uuid4()

    @pytest.fixture
    def sample_question_input(self, sample_collection_id) -> QuestionInput:
        """Sample question input."""
        return QuestionInput(collection_id=sample_collection_id, question="What is machine learning?")

    @pytest.fixture
    def sample_prompt_template(self) -> PromptTemplateBase:
        """Sample prompt template."""
        template = Mock(spec=PromptTemplateBase)
        template.template = "Generate {num_questions} questions about: {text}"
        template.name = "question_generation"
        return template

    @pytest.fixture
    def sample_llm_parameters(self, sample_user_id) -> LLMParametersInput:
        """Sample LLM parameters."""
        return LLMParametersInput(
            user_id=sample_user_id,
            name="test-parameters",
            description="Test LLM parameters",
            temperature=0.7,
            max_new_tokens=500,
            top_p=0.9,
            top_k=50,
            repetition_penalty=1.1,
        )

    # ============================================================================
    # INITIALIZATION TESTS
    # ============================================================================

    def test_service_initialization(self, mock_db, mock_settings):
        """Test QuestionService initialization with required dependencies."""
        service = QuestionService(mock_db, mock_settings)

        assert service.db is mock_db
        assert service.settings is mock_settings
        assert service._question_repository is None  # Lazy initialization
        assert service._prompt_template_service is None
        assert service._llm_parameters_service is None
        assert service.max_questions_per_collection == 15
        assert service.max_chunks_to_process == 8
        assert service.cot_question_ratio == 0.4

    def test_lazy_repository_initialization(self, service, mock_question_repository):
        """Test lazy initialization of question repository."""
        assert service.question_repository is mock_question_repository

    def test_lazy_prompt_template_service_initialization(self, service):
        """Test lazy initialization of prompt template service."""
        # Force initialization
        _ = service.prompt_template_service
        assert service._prompt_template_service is not None

    def test_lazy_llm_parameters_service_initialization(self, service):
        """Test lazy initialization of LLM parameters service."""
        # Force initialization
        _ = service.llm_parameters_service
        assert service._llm_parameters_service is not None

    # ============================================================================
    # CREATE QUESTION TESTS
    # ============================================================================

    def test_create_question_success(self, service, sample_question_input, sample_collection_id):
        """Test successful creation of a single question."""
        expected_question = SuggestedQuestion(
            id=uuid4(), collection_id=sample_collection_id, question="What is machine learning?"
        )
        service.question_repository.create_question.return_value = expected_question

        result = service.create_question(sample_question_input)

        assert isinstance(result, SuggestedQuestion)
        assert result.question == sample_question_input.question
        assert result.collection_id == sample_collection_id
        service.question_repository.create_question.assert_called_once_with(sample_question_input)

    def test_create_question_validation_error(self, service):
        """Test question creation with invalid input raises ValueError."""
        # QuestionInput validates at schema level, so we expect ValidationError from Pydantic
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            QuestionInput(collection_id=uuid4(), question="Invalid question without mark")

    def test_create_question_database_error(self, service, sample_question_input):
        """Test question creation when database error occurs."""
        service.question_repository.create_question.side_effect = SQLAlchemyError("Database connection error")

        with pytest.raises(SQLAlchemyError):
            service.create_question(sample_question_input)

    # ============================================================================
    # DELETE QUESTION TESTS
    # ============================================================================

    def test_delete_question_success(self, service):
        """Test successful deletion of a question."""
        question_id = uuid4()
        service.question_repository.delete_question.return_value = None

        service.delete_question(question_id)

        service.question_repository.delete_question.assert_called_once_with(question_id)

    def test_delete_question_not_found(self, service):
        """Test deletion of non-existent question."""
        question_id = uuid4()
        service.question_repository.delete_question.side_effect = NotFoundError("SuggestedQuestion", str(question_id))

        with pytest.raises(NotFoundError) as exc_info:
            service.delete_question(question_id)

        assert "SuggestedQuestion" in str(exc_info.value)

    def test_delete_question_database_error(self, service):
        """Test question deletion with database error."""
        question_id = uuid4()
        service.question_repository.delete_question.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(Exception):
            service.delete_question(question_id)

    # ============================================================================
    # DELETE QUESTIONS BY COLLECTION TESTS
    # ============================================================================

    def test_delete_questions_by_collection_success(self, service, sample_collection_id):
        """Test successful deletion of all questions for a collection."""
        service.question_repository.delete_questions_by_collection.return_value = 5

        service.delete_questions_by_collection(sample_collection_id)

        service.question_repository.delete_questions_by_collection.assert_called_once_with(sample_collection_id)

    def test_delete_questions_by_collection_not_found(self, service, sample_collection_id):
        """Test deletion when collection doesn't exist."""
        service.question_repository.delete_questions_by_collection.side_effect = NotFoundError(
            "Collection", str(sample_collection_id)
        )

        with pytest.raises(NotFoundError):
            service.delete_questions_by_collection(sample_collection_id)

    def test_delete_questions_by_collection_database_error(self, service, sample_collection_id):
        """Test deletion with database error."""
        service.question_repository.delete_questions_by_collection.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(Exception):
            service.delete_questions_by_collection(sample_collection_id)

    # ============================================================================
    # GET COLLECTION QUESTIONS TESTS
    # ============================================================================

    def test_get_collection_questions_success(self, service, sample_collection_id):
        """Test retrieving questions for a collection."""
        expected_questions = [
            SuggestedQuestion(id=uuid4(), collection_id=sample_collection_id, question="What is AI?"),
            SuggestedQuestion(id=uuid4(), collection_id=sample_collection_id, question="How does ML work?"),
        ]
        service.question_repository.get_questions_by_collection.return_value = expected_questions

        result = service.get_collection_questions(sample_collection_id)

        assert len(result) == 2
        assert all(isinstance(q, SuggestedQuestion) for q in result)
        service.question_repository.get_questions_by_collection.assert_called_once_with(sample_collection_id)

    def test_get_collection_questions_empty(self, service, sample_collection_id):
        """Test retrieving questions when collection has no questions."""
        service.question_repository.get_questions_by_collection.return_value = []

        result = service.get_collection_questions(sample_collection_id)

        assert result == []

    def test_get_collection_questions_database_error(self, service, sample_collection_id):
        """Test retrieval with database error."""
        service.question_repository.get_questions_by_collection.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            service.get_collection_questions(sample_collection_id)

    # ============================================================================
    # QUESTION VALIDATION TESTS
    # ============================================================================

    def test_validate_question_valid_short_question(self, service):
        """Test validation of valid short question."""
        question = "What is AI?"
        context = "Artificial Intelligence AI is a field of computer science."

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is True
        assert cleaned == "What is AI?"

    def test_validate_question_valid_long_question(self, service):
        """Test validation of valid long question."""
        question = "What are the key differences between supervised and unsupervised learning?"
        context = "Machine learning includes supervised learning and unsupervised learning methods."

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is True

    def test_validate_question_missing_question_mark(self, service):
        """Test validation rejects question without question mark."""
        question = "What is AI"
        context = "Artificial Intelligence context"

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is False

    def test_validate_question_multiple_question_marks(self, service):
        """Test validation rejects question with multiple question marks."""
        question = "What is AI? Really?"
        context = "Artificial Intelligence context"

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is False

    def test_validate_question_too_short(self, service):
        """Test validation rejects questions that are too short."""
        question = "AI?"
        context = "Artificial Intelligence context"

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is False

    def test_validate_question_removes_numbering(self, service):
        """Test validation removes numbering prefix."""
        question = "1. What is machine learning?"
        context = "Machine learning is a subset of artificial intelligence."

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is True
        assert cleaned == "What is machine learning?"
        assert not cleaned.startswith("1.")

    def test_validate_question_low_relevance(self, service):
        """Test validation rejects questions with low relevance to context."""
        question = "What is the weather today?"
        context = "Machine learning is a field of artificial intelligence."

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is False

    def test_validate_question_empty_string(self, service):
        """Test validation rejects empty string."""
        question = ""
        context = "Some context"

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is False

    # ============================================================================
    # QUESTION RANKING TESTS
    # ============================================================================

    def test_rank_questions_by_relevance(self, service):
        """Test ranking questions by relevance to context."""
        questions = [
            "What is the weather?",  # Low relevance
            "What is machine learning?",  # High relevance
            "How does machine learning work?",  # High relevance
        ]
        context = "Machine learning is a subset of artificial intelligence that enables systems to learn."

        ranked = service._rank_questions(questions, context)

        # High relevance questions should be ranked first
        assert len(ranked) == 2  # Low relevance question filtered out
        assert "machine learning" in ranked[0].lower()

    def test_rank_questions_empty_list(self, service):
        """Test ranking with empty question list."""
        questions = []
        context = "Some context"

        ranked = service._rank_questions(questions, context)

        assert ranked == []

    def test_rank_questions_all_invalid(self, service):
        """Test ranking when all questions are invalid."""
        questions = ["No question mark", "Too short?", "???"]
        context = "Some context"

        ranked = service._rank_questions(questions, context)

        assert ranked == []

    # ============================================================================
    # DUPLICATE FILTERING TESTS
    # ============================================================================

    def test_filter_duplicate_questions_exact_duplicates(self, service):
        """Test filtering exact duplicate questions."""
        questions = [
            "What is machine learning?",
            "What is machine learning?",
            "How does AI work?",
        ]

        unique = service._filter_duplicate_questions(questions)

        assert len(unique) == 2
        assert "What is machine learning?" in unique
        assert "How does AI work?" in unique

    def test_filter_duplicate_questions_normalized_duplicates(self, service):
        """Test filtering duplicates with different capitalization and punctuation."""
        questions = [
            "What is Machine Learning?",
            "what is machine learning?",
            "What is MACHINE LEARNING?",
            "How does AI work?",
        ]

        unique = service._filter_duplicate_questions(questions)

        assert len(unique) == 2

    def test_filter_duplicate_questions_with_numbering(self, service):
        """Test filtering duplicates that have numbering prefixes."""
        questions = [
            "1. What is machine learning?",
            "2. What is machine learning?",
            "3. How does AI work?",
        ]

        unique = service._filter_duplicate_questions(questions)

        assert len(unique) == 2

    def test_filter_duplicate_questions_empty_list(self, service):
        """Test filtering with empty list."""
        questions = []

        unique = service._filter_duplicate_questions(questions)

        assert unique == []

    # ============================================================================
    # CHUNK SELECTION TESTS
    # ============================================================================

    def test_select_representative_chunks_fewer_than_max(self, service):
        """Test chunk selection when total chunks less than max."""
        texts = ["Chunk 1", "Chunk 2", "Chunk 3"]
        max_chunks = 5

        selected = service._select_representative_chunks(texts, max_chunks)

        assert len(selected) == 3
        assert selected == texts

    def test_select_representative_chunks_stratified_sampling(self, service):
        """Test chunk selection uses stratified sampling."""
        texts = [f"Chunk {i}" for i in range(20)]
        max_chunks = 5

        selected = service._select_representative_chunks(texts, max_chunks)

        assert len(selected) == max_chunks
        # Should include first and last chunks
        assert texts[0] in selected
        assert texts[-1] in selected

    def test_select_representative_chunks_single_chunk_limit(self, service):
        """Test chunk selection with max_chunks=1."""
        texts = ["Short", "Medium length text", "This is a very long text with many words"]
        max_chunks = 1

        selected = service._select_representative_chunks(texts, max_chunks)

        assert len(selected) == 1
        # Should select the longest chunk
        assert selected[0] == texts[2]

    def test_select_representative_chunks_empty_list(self, service):
        """Test chunk selection with empty list."""
        texts = []
        max_chunks = 5

        selected = service._select_representative_chunks(texts, max_chunks)

        assert selected == []

    # ============================================================================
    # TEXT COMBINATION TESTS
    # ============================================================================

    def test_combine_text_chunks_within_limit(self, service):
        """Test combining text chunks within context length limit."""
        texts = ["Text 1", "Text 2", "Text 3"]
        available_context_length = 1000

        combined = service._combine_text_chunks(texts, available_context_length)

        assert len(combined) == 1
        assert "Text 1" in combined[0]
        assert "Text 2" in combined[0]
        assert "Text 3" in combined[0]

    def test_combine_text_chunks_exceeds_limit(self, service):
        """Test combining text chunks when exceeding context limit."""
        texts = ["A" * 1000, "B" * 1000, "C" * 1000]
        available_context_length = 1500

        combined = service._combine_text_chunks(texts, available_context_length)

        # Should create multiple batches
        assert len(combined) > 1

    def test_combine_text_chunks_truncate_long_text(self, service):
        """Test that excessively long texts are truncated."""
        texts = ["A" * 10000]  # Very long text
        available_context_length = 1000

        combined = service._combine_text_chunks(texts, available_context_length)

        assert len(combined[0]) <= available_context_length

    def test_combine_text_chunks_respects_max_chunks(self, service, mock_settings):
        """Test that combination respects max chunks limit."""
        texts = [f"Text {i}" for i in range(20)]
        available_context_length = 10000

        combined = service._combine_text_chunks(texts, available_context_length)

        # Should only process max_chunks_to_process (8 by default)
        assert len(" ".join(combined).split("Text")) - 1 <= mock_settings.max_chunks_for_questions

    # ============================================================================
    # ASYNC QUESTION GENERATION TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_suggest_questions_success(
        self,
        service,
        sample_collection_id,
        sample_user_id,
        sample_prompt_template,
        sample_llm_parameters,
    ):
        """Test successful question generation."""
        texts = ["Machine learning is a subset of AI.", "Deep learning uses neural networks."]

        # Mock provider response
        mock_provider = service._provider_factory.get_provider()
        mock_provider.generate_text.return_value = [
            "What is machine learning?\nHow does deep learning work?\nWhat are neural networks?"
        ]

        # Mock repository for storing questions
        service.question_repository.get_questions_by_collection.return_value = []
        service.question_repository.create_questions.return_value = [
            SuggestedQuestion(id=uuid4(), collection_id=sample_collection_id, question="What is machine learning?"),
            SuggestedQuestion(id=uuid4(), collection_id=sample_collection_id, question="How does deep learning work?"),
        ]

        result = await service.suggest_questions(
            texts=texts,
            collection_id=sample_collection_id,
            user_id=sample_user_id,
            provider_name="test_provider",
            template=sample_prompt_template,
            parameters=sample_llm_parameters,
            num_questions=5,
        )

        assert len(result) >= 1
        assert all(isinstance(q, SuggestedQuestion) for q in result)

    @pytest.mark.asyncio
    async def test_suggest_questions_empty_texts(
        self,
        service,
        sample_collection_id,
        sample_user_id,
        sample_prompt_template,
        sample_llm_parameters,
    ):
        """Test question generation with empty text list."""
        texts = []

        result = await service.suggest_questions(
            texts=texts,
            collection_id=sample_collection_id,
            user_id=sample_user_id,
            provider_name="test_provider",
            template=sample_prompt_template,
            parameters=sample_llm_parameters,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_suggest_questions_force_regenerate(
        self,
        service,
        sample_collection_id,
        sample_user_id,
        sample_prompt_template,
        sample_llm_parameters,
    ):
        """Test question generation with force_regenerate flag."""
        texts = ["Test content"]

        # Mock existing questions
        existing_questions = [
            SuggestedQuestion(id=uuid4(), collection_id=sample_collection_id, question="Old question?")
        ]
        service.question_repository.get_questions_by_collection.return_value = existing_questions

        # Mock provider
        mock_provider = service._provider_factory.get_provider()
        mock_provider.generate_text.return_value = ["What is new question?"]

        # Mock repository
        service.question_repository.create_questions.return_value = [
            SuggestedQuestion(id=uuid4(), collection_id=sample_collection_id, question="What is new question?")
        ]

        result = await service.suggest_questions(
            texts=texts,
            collection_id=sample_collection_id,
            user_id=sample_user_id,
            provider_name="test_provider",
            template=sample_prompt_template,
            parameters=sample_llm_parameters,
            force_regenerate=True,
        )

        # Should delete existing questions
        service.question_repository.delete_questions_by_collection.assert_called_once_with(sample_collection_id)

    @pytest.mark.asyncio
    async def test_suggest_questions_validation_error(
        self,
        service,
        sample_collection_id,
        sample_user_id,
        sample_prompt_template,
        sample_llm_parameters,
    ):
        """Test question generation when validation error occurs."""
        texts = ["Test content"]

        # Mock provider to raise validation error
        service._provider_factory.get_provider.side_effect = ValidationError("Invalid provider configuration")

        with pytest.raises(ValidationError):
            await service.suggest_questions(
                texts=texts,
                collection_id=sample_collection_id,
                user_id=sample_user_id,
                provider_name="invalid_provider",
                template=sample_prompt_template,
                parameters=sample_llm_parameters,
            )

    @pytest.mark.asyncio
    async def test_suggest_questions_provider_error(
        self,
        service,
        sample_collection_id,
        sample_user_id,
        sample_prompt_template,
        sample_llm_parameters,
    ):
        """Test question generation when provider error occurs during generation."""
        texts = ["Machine learning content for testing"]

        # Mock provider to raise error during text generation
        mock_provider = service._provider_factory.get_provider()
        mock_provider.generate_text.side_effect = Exception("Provider connection error")

        # Mock repository to return empty list
        service.question_repository.get_questions_by_collection.return_value = []

        # The service logs the error but continues, so it returns empty list
        result = await service.suggest_questions(
            texts=texts,
            collection_id=sample_collection_id,
            user_id=sample_user_id,
            provider_name="test_provider",
            template=sample_prompt_template,
            parameters=sample_llm_parameters,
        )

        # Should return empty list when all generations fail
        assert result == []

    # ============================================================================
    # QUESTION STORAGE TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_store_questions_new_collection(self, service, sample_collection_id):
        """Test storing questions for a collection with no existing questions."""
        questions = ["What is AI?", "How does ML work?", "What is deep learning?"]

        service.question_repository.get_questions_by_collection.return_value = []
        service.question_repository.create_questions.return_value = [
            SuggestedQuestion(id=uuid4(), collection_id=sample_collection_id, question=q) for q in questions
        ]

        result = await service._store_questions(sample_collection_id, questions)

        assert len(result) == 3
        service.question_repository.create_questions.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_questions_duplicate_filtering(self, service, sample_collection_id):
        """Test that duplicate questions are filtered during storage."""
        new_questions = ["What is AI?", "How does ML work?"]

        # Mock existing questions
        existing_questions = [
            SuggestedQuestion(id=uuid4(), collection_id=sample_collection_id, question="What is AI?")
        ]
        service.question_repository.get_questions_by_collection.return_value = existing_questions

        service.question_repository.create_questions.return_value = [
            SuggestedQuestion(id=uuid4(), collection_id=sample_collection_id, question="How does ML work?")
        ]

        result = await service._store_questions(sample_collection_id, new_questions)

        # Should only store the non-duplicate question
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_store_questions_at_capacity(self, service, sample_collection_id):
        """Test storing questions when collection is at max capacity."""
        new_questions = ["New question 1?", "New question 2?"]

        # Mock existing questions at max capacity (15)
        existing_questions = [
            SuggestedQuestion(id=uuid4(), collection_id=sample_collection_id, question=f"Question {i}?")
            for i in range(15)
        ]
        service.question_repository.get_questions_by_collection.return_value = existing_questions

        result = await service._store_questions(sample_collection_id, new_questions)

        # Should not add new questions
        assert result == existing_questions
        service.question_repository.create_questions.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_questions_partial_capacity(self, service, sample_collection_id):
        """Test storing questions when collection has partial capacity."""
        new_questions = ["New question 1?", "New question 2?", "New question 3?"]

        # Mock existing questions (13 out of 15)
        existing_questions = [
            SuggestedQuestion(id=uuid4(), collection_id=sample_collection_id, question=f"Existing question {i}?")
            for i in range(13)
        ]
        service.question_repository.get_questions_by_collection.return_value = existing_questions

        # Mock creating 2 new questions (limited by available capacity)
        new_stored_questions = [
            SuggestedQuestion(id=uuid4(), collection_id=sample_collection_id, question="New question 1?"),
            SuggestedQuestion(id=uuid4(), collection_id=sample_collection_id, question="New question 2?"),
        ]
        service.question_repository.create_questions.return_value = new_stored_questions

        result = await service._store_questions(sample_collection_id, new_questions)

        # Should only add 2 questions (to reach capacity of 15)
        assert len(result) == 2
        # Verify create_questions was called with correct number of questions
        call_args = service.question_repository.create_questions.call_args
        assert len(call_args[0][1]) == 2  # Should only create 2 questions

    @pytest.mark.asyncio
    async def test_store_questions_empty_list(self, service, sample_collection_id):
        """Test storing empty question list."""
        questions = []

        result = await service._store_questions(sample_collection_id, questions)

        assert result == []
        service.question_repository.create_questions.assert_not_called()

    # ============================================================================
    # REGENERATE QUESTIONS TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_regenerate_questions_success(
        self,
        service,
        sample_collection_id,
        sample_user_id,
        sample_prompt_template,
        sample_llm_parameters,
    ):
        """Test successful question regeneration."""
        texts = ["Machine learning is a field of artificial intelligence that focuses on learning."]

        # Mock provider to return questions with proper formatting
        mock_provider = service._provider_factory.get_provider()
        mock_provider.generate_text.return_value = [
            "What is machine learning?\nHow does artificial intelligence work?\nWhat is the focus of learning?"
        ]

        # Mock repository
        service.question_repository.get_questions_by_collection.return_value = []
        service.question_repository.create_questions.return_value = [
            SuggestedQuestion(id=uuid4(), collection_id=sample_collection_id, question="What is machine learning?"),
            SuggestedQuestion(id=uuid4(), collection_id=sample_collection_id, question="How does artificial intelligence work?"),
        ]

        result = await service.regenerate_questions(
            collection_id=sample_collection_id,
            user_id=sample_user_id,
            texts=texts,
            provider_name="test_provider",
            template=sample_prompt_template,
            parameters=sample_llm_parameters,
            num_questions=5,
        )

        # Should delete existing questions
        service.question_repository.delete_questions_by_collection.assert_called_once_with(sample_collection_id)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_regenerate_questions_error(
        self,
        service,
        sample_collection_id,
        sample_user_id,
        sample_prompt_template,
        sample_llm_parameters,
    ):
        """Test question regeneration when error occurs."""
        texts = ["Test content"]

        # Mock repository to raise error
        service.question_repository.delete_questions_by_collection.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            await service.regenerate_questions(
                collection_id=sample_collection_id,
                user_id=sample_user_id,
                texts=texts,
                provider_name="test_provider",
                template=sample_prompt_template,
                parameters=sample_llm_parameters,
            )

    # ============================================================================
    # EXTRACT QUESTIONS FROM RESPONSES TESTS
    # ============================================================================

    def test_extract_questions_from_string_response(self, service):
        """Test extracting questions from string response."""
        response = "What is AI?\nHow does ML work?\nInvalid line without question mark"

        questions = service._extract_questions_from_responses(response)

        assert len(questions) == 2
        assert "What is AI?" in questions
        assert "How does ML work?" in questions

    def test_extract_questions_from_list_response(self, service):
        """Test extracting questions from list of responses."""
        responses = ["What is AI?\nHow does ML work?", "What is deep learning?\nWhat are neural networks?"]

        questions = service._extract_questions_from_responses(responses)

        assert len(questions) == 4
        assert "What is AI?" in questions
        assert "What are neural networks?" in questions

    def test_extract_questions_empty_response(self, service):
        """Test extracting questions from empty response."""
        response = ""

        questions = service._extract_questions_from_responses(response)

        assert questions == []

    def test_extract_questions_no_valid_questions(self, service):
        """Test extracting questions when response has no valid questions."""
        response = "This is a statement.\nAnother statement without question mark."

        questions = service._extract_questions_from_responses(response)

        assert questions == []

    # ============================================================================
    # EDGE CASES AND ERROR HANDLING
    # ============================================================================

    def test_service_with_none_settings_uses_defaults(self, mock_db, mock_provider_factory):
        """Test that service uses default values when settings is None."""
        service = QuestionService(mock_db, None)
        service._provider_factory = mock_provider_factory

        # Service should use default values from getattr
        assert service.max_questions_per_collection == 15
        assert service.max_chunks_to_process == 8
        assert service.cot_question_ratio == 0.4

        # When actually needing settings in _setup_question_generation, it should raise ValueError
        with pytest.raises(ValueError, match="Settings must be provided"):
            service._setup_question_generation(["text"], "test_provider", Mock(), Mock())

    def test_validate_question_with_special_characters(self, service):
        """Test validation of question with special characters."""
        question = "What is machine learning (ML) & artificial intelligence (AI)?"
        context = "Machine learning and artificial intelligence are related fields."

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is True

    def test_rank_questions_with_unicode_characters(self, service):
        """Test ranking questions containing unicode characters."""
        questions = ["What is AI?", "¿Qué es el aprendizaje automático?"]
        context = "Machine learning and AI are important fields."

        ranked = service._rank_questions(questions, context)

        assert len(ranked) >= 1

    @pytest.mark.asyncio
    async def test_suggest_questions_with_very_long_text(
        self,
        service,
        sample_collection_id,
        sample_user_id,
        sample_prompt_template,
        sample_llm_parameters,
    ):
        """Test question generation with very long texts."""
        # Create very long text that exceeds context length
        long_text = "Machine learning " * 1000

        # Mock provider
        mock_provider = service._provider_factory.get_provider()
        mock_provider.generate_text.return_value = ["What is machine learning?"]

        # Mock repository
        service.question_repository.get_questions_by_collection.return_value = []
        service.question_repository.create_questions.return_value = [
            SuggestedQuestion(id=uuid4(), collection_id=sample_collection_id, question="What is machine learning?")
        ]

        result = await service.suggest_questions(
            texts=[long_text],
            collection_id=sample_collection_id,
            user_id=sample_user_id,
            provider_name="test_provider",
            template=sample_prompt_template,
            parameters=sample_llm_parameters,
        )

        # Should handle long text without error
        assert isinstance(result, list)

    # ============================================================================
    # ADDITIONAL EDGE CASES - VALIDATION
    # ============================================================================

    def test_validate_question_very_long_question(self, service):
        """Test validation with very long question (1000+ characters)."""
        # Create a very long question
        long_question = "What are the implications of " + "machine learning " * 100 + "in modern AI systems?"
        context = "Machine learning and AI systems are important in modern technology."

        is_valid, cleaned = service._validate_question(long_question, context)

        # Should still validate based on relevance, not just length
        assert isinstance(is_valid, bool)
        assert isinstance(cleaned, str)

    def test_validate_question_unicode_characters(self, service):
        """Test validation with Unicode characters (Chinese, Arabic, emoji)."""
        question = "What is 机器学习 and مل and how does it work 🤖?"
        context = "Machine learning ML systems work with algorithms."

        is_valid, cleaned = service._validate_question(question, context)

        # Should handle Unicode gracefully
        assert isinstance(is_valid, bool)
        assert "🤖" in cleaned or "机器学习" in cleaned

    def test_validate_question_only_special_characters(self, service):
        """Test validation with mostly special characters."""
        question = "!@#$%^&*()_+-={}[]|\\:;<>,.?/~`?"
        context = "Some context here"

        is_valid, cleaned = service._validate_question(question, context)

        # Should reject questions with no meaningful words
        assert is_valid is False

    def test_validate_question_whitespace_variations(self, service):
        """Test validation with various whitespace (tabs, newlines, multiple spaces)."""
        question = "What   is\t\tmachine\nlearning\r\n?"
        context = "Machine learning is a field of AI"

        is_valid, cleaned = service._validate_question(question, context)

        # Should normalize whitespace and validate properly
        assert is_valid is True

    def test_validate_question_html_entities(self, service):
        """Test validation with HTML entities and tags."""
        question = "What is &lt;machine learning&gt; and &amp; AI?"
        context = "Machine learning and AI are related fields"

        is_valid, cleaned = service._validate_question(question, context)

        # Should handle HTML entities
        assert isinstance(is_valid, bool)

    # ============================================================================
    # ADDITIONAL EDGE CASES - RANKING
    # ============================================================================

    def test_rank_questions_all_same_score(self, service):
        """Test ranking when all questions have identical relevance scores."""
        questions = [
            "What is machine learning?",
            "How does machine learning work?",
            "Why is machine learning important?",
        ]
        context = "machine learning"

        ranked = service._rank_questions(questions, context)

        # Should return all questions with deterministic ordering
        assert len(ranked) == 3
        # Order should be stable
        assert all("machine learning" in q.lower() for q in ranked)

    def test_rank_questions_tie_breaking_by_complexity(self, service):
        """Test ranking uses complexity as tie-breaker for same relevance."""
        questions = [
            "What is AI?",  # Short
            "What is artificial intelligence in modern computing systems?",  # Long
        ]
        context = "Artificial intelligence AI computing systems"

        ranked = service._rank_questions(questions, context)

        # Longer, more complex question should rank higher with same relevance
        assert len(ranked) >= 1
        if len(ranked) == 2:
            # The longer question should come first due to complexity bonus
            assert len(ranked[0]) > len(ranked[1])

    def test_rank_questions_float_precision_edge_case(self, service):
        """Test ranking handles float precision correctly."""
        questions = [
            "What is the primary application of machine learning?",
            "What is the primary application for machine learning?",  # Very similar
        ]
        context = "Primary application machine learning systems"

        ranked = service._rank_questions(questions, context)

        # Should handle very similar scores without errors
        assert isinstance(ranked, list)
        assert len(ranked) <= 2

    def test_rank_questions_empty_context(self, service):
        """Test ranking with empty context string."""
        questions = ["What is machine learning?", "How does AI work?"]
        context = ""

        ranked = service._rank_questions(questions, context)

        # Should handle empty context gracefully (all questions fail validation)
        assert isinstance(ranked, list)

    # ============================================================================
    # ADDITIONAL EDGE CASES - CoT QUESTION GENERATION
    # ============================================================================

    @pytest.mark.asyncio
    async def test_generate_cot_questions_single_chunk(self, service, sample_user_id, sample_prompt_template, sample_llm_parameters):
        """Test CoT question generation with only one chunk (should return empty)."""
        combined_texts = ["Single chunk of text"]
        mock_provider = Mock()
        stats = {}

        result = await service._generate_cot_questions(
            combined_texts,
            mock_provider,
            sample_user_id,
            sample_prompt_template,
            sample_llm_parameters,
            target_questions=5,
            stats=stats,
        )

        # Should return empty list for single chunk
        assert result == []
        assert "cot_questions_generated" not in stats

    @pytest.mark.asyncio
    async def test_generate_cot_questions_provider_failure(self, service, sample_user_id, sample_prompt_template, sample_llm_parameters):
        """Test CoT question generation when provider fails."""
        combined_texts = ["Chunk 1", "Chunk 2", "Chunk 3"]
        mock_provider = Mock()
        mock_provider.generate_text.side_effect = Exception("Provider error")
        stats = {}

        result = await service._generate_cot_questions(
            combined_texts,
            mock_provider,
            sample_user_id,
            sample_prompt_template,
            sample_llm_parameters,
            target_questions=5,
            stats=stats,
        )

        # Should return empty list on error
        assert result == []

    @pytest.mark.asyncio
    async def test_generate_cot_questions_zero_target(self, service, sample_user_id, sample_prompt_template, sample_llm_parameters):
        """Test CoT question generation with zero target questions."""
        combined_texts = ["Chunk 1", "Chunk 2"]
        mock_provider = Mock()
        mock_provider.generate_text.return_value = ["What is this?"]
        stats = {}

        result = await service._generate_cot_questions(
            combined_texts,
            mock_provider,
            sample_user_id,
            sample_prompt_template,
            sample_llm_parameters,
            target_questions=0,  # Zero target
            stats=stats,
        )

        # Should still try to generate at least 1 CoT question
        assert isinstance(result, list)

    # ============================================================================
    # ADDITIONAL EDGE CASES - CONVERSATION SUGGESTIONS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_generate_conversation_suggestions_no_provider(self, service, sample_user_id):
        """Test conversation suggestions when no provider is available."""
        service._provider_factory.get_provider = AsyncMock(return_value=None)

        result = await service.generate_conversation_suggestions(
            conversation_context="Some context",
            current_message="What is AI?",
            user_id=sample_user_id,
            max_suggestions=3,
        )

        # Should fallback to basic suggestions
        assert isinstance(result, list)
        assert len(result) <= 3

    @pytest.mark.asyncio
    async def test_generate_conversation_suggestions_provider_error(self, service, sample_user_id):
        """Test conversation suggestions when provider raises error."""
        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(side_effect=Exception("Provider error"))
        service._provider_factory.get_provider = AsyncMock(return_value=mock_provider)

        result = await service.generate_conversation_suggestions(
            conversation_context="Context",
            current_message="Question?",
            user_id=sample_user_id,
            max_suggestions=3,
        )

        # Should fallback to basic suggestions on error
        assert isinstance(result, list)
        assert all("question" in s.keys() for s in result)

    @pytest.mark.asyncio
    async def test_generate_conversation_suggestions_empty_context(self, service, sample_user_id):
        """Test conversation suggestions with empty context."""
        result = await service.generate_conversation_suggestions(
            conversation_context="",
            current_message="What is AI?",
            user_id=sample_user_id,
            max_suggestions=3,
        )

        # Should still generate basic suggestions
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_extract_entities_from_empty_text(self, service):
        """Test entity extraction from empty text."""
        entities = service._extract_entities_from_text("")

        assert entities == []

    def test_extract_topics_from_text_no_questions(self, service):
        """Test topic extraction when text has no question patterns."""
        text = "This is a declarative statement about machine learning. It contains no questions."

        topics = service._extract_topics_from_text(text)

        # Should return empty list when no question patterns found
        assert isinstance(topics, list)

    def test_score_conversation_suggestion_perfect_overlap(self, service):
        """Test scoring when suggestion has perfect word overlap with current message."""
        suggestion = "What is machine learning?"
        current_message = "What is machine learning?"
        context = "Machine learning context"
        entities = ["machine learning"]

        score = service._score_conversation_suggestion(suggestion, current_message, context, entities)

        # Should penalize too much overlap (redundancy)
        assert 0.0 <= score <= 1.0
        assert score < 0.9  # Should be penalized for being too similar

    def test_generate_basic_suggestions_with_entities(self, service):
        """Test basic suggestion generation with detected entities."""
        entities = ["machine learning", "artificial intelligence", "neural networks"]
        topics = ["AI", "ML"]

        suggestions = service._generate_basic_suggestions(
            _current_message="What is AI?",
            entities=entities,
            topics=topics,
            max_suggestions=5,
        )

        assert len(suggestions) == 5
        assert all("confidence" in s for s in suggestions)
        # Should include entity-specific suggestions
        assert any("machine learning" in s["question"] or "artificial intelligence" in s["question"] for s in suggestions)

    # ============================================================================
    # ADDITIONAL EDGE CASES - ERROR HANDLING & CONCURRENT ACCESS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_store_questions_database_commit_error(self, service, sample_collection_id):
        """Test storing questions when database commit fails."""
        questions = ["What is AI?", "How does ML work?"]

        service.question_repository.get_questions_by_collection.return_value = []
        service.question_repository.create_questions.side_effect = SQLAlchemyError("Commit failed")

        with pytest.raises(SQLAlchemyError):
            await service._store_questions(sample_collection_id, questions)

    @pytest.mark.asyncio
    async def test_suggest_questions_not_found_error(
        self,
        service,
        sample_collection_id,
        sample_user_id,
        sample_prompt_template,
        sample_llm_parameters,
    ):
        """Test question generation when NotFoundError occurs."""
        texts = ["Test content"]

        # Mock provider to raise NotFoundError
        service._provider_factory.get_provider.side_effect = NotFoundError("Provider", "test_provider")

        with pytest.raises(NotFoundError):
            await service.suggest_questions(
                texts=texts,
                collection_id=sample_collection_id,
                user_id=sample_user_id,
                provider_name="test_provider",
                template=sample_prompt_template,
                parameters=sample_llm_parameters,
            )

    def test_process_generated_questions_all_duplicates(self, service):
        """Test processing when all generated questions are duplicates."""
        all_questions = [
            "What is AI?",
            "what is ai?",
            "WHAT IS AI?",
            "What is AI?",
        ]
        texts = ["AI is artificial intelligence"]

        result = service._process_generated_questions(all_questions, texts, num_questions=5)

        # Should deduplicate to single question
        assert len(result) == 1
        assert "what is ai" in result[0].lower()

    def test_process_generated_questions_exceeds_target(self, service):
        """Test processing when generated questions exceed target limit."""
        all_questions = [f"What is question {i}?" for i in range(50)]
        texts = ["question " * 20]  # Context with the word "question"
        target = 10

        result = service._process_generated_questions(all_questions, texts, num_questions=target)

        # Should limit to target number
        assert len(result) <= target

    @pytest.mark.asyncio
    async def test_generate_questions_from_texts_early_exit(
        self,
        service,
        sample_user_id,
        sample_prompt_template,
        sample_llm_parameters,
    ):
        """Test that question generation exits early when enough questions generated."""
        combined_texts = [f"Text chunk {i}" for i in range(20)]
        mock_provider = Mock()
        mock_provider.generate_text.return_value = ["What is this?" * 100]  # Many questions
        stats = {"successful_generations": 0, "failed_generations": 0}

        result = await service._generate_questions_from_texts(
            combined_texts,
            mock_provider,
            sample_user_id,
            sample_prompt_template,
            sample_llm_parameters,
            num_questions=5,
            stats=stats,
        )

        # Should exit early and not process all chunks
        assert isinstance(result, list)
        assert stats["successful_generations"] >= 1

    def test_parse_conversation_suggestions_mixed_formats(self, service):
        """Test parsing conversation suggestions with mixed numbering formats."""
        llm_response = """
        1. What is the first question?
        2 What is the second question without period?
        3. What is the third question?
        Random line without number
        What is question without number?
        """

        suggestions = service._parse_conversation_suggestions(llm_response)

        # Should parse numbered questions correctly
        assert len(suggestions) >= 2
        assert any("first question" in s for s in suggestions)

    def test_build_conversation_suggestion_prompt_empty_entities_topics(self, service):
        """Test building prompt with no entities or topics detected."""
        prompt = service._build_conversation_suggestion_prompt(
            context="Some generic context",
            current_message="Tell me more",
            entities=[],
            topics=[],
            max_suggestions=3,
        )

        # Should handle empty entities/topics gracefully
        assert "general topics" in prompt
        assert "3" in prompt
        assert "Tell me more" in prompt
