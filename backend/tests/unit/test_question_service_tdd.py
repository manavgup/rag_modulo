"""TDD Unit tests for QuestionService - RED phase: Tests that describe expected behavior."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.services.question_service import QuestionService
from rag_solution.schemas.question_schema import QuestionInput
from rag_solution.models.question import SuggestedQuestion
from core.custom_exceptions import NotFoundError


@pytest.mark.unit
class TestQuestionServiceTDD:
    """TDD tests for QuestionService - following Red-Green-Refactor cycle."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Mock settings."""
        settings = Mock(spec=Settings)
        settings.max_context_length = 4000
        settings.max_new_tokens = 500
        settings.llm_concurrency = 2
        return settings

    @pytest.fixture
    def service(self, mock_db, mock_settings):
        """Create service instance with mocked dependencies."""
        with patch('rag_solution.services.question_service.LLMProviderFactory') as mock_factory:
            service = QuestionService(mock_db, mock_settings)

            # Mock the lazy-loaded services
            service._question_repository = Mock()
            service._prompt_template_service = Mock()
            service._llm_parameters_service = Mock()
            service._provider_factory = Mock()

            return service

    def test_service_initialization_red_phase(self, mock_db, mock_settings):
        """RED: Test service initialization sets up dependencies correctly."""
        with patch('rag_solution.services.question_service.LLMProviderFactory'):
            service = QuestionService(mock_db, mock_settings)

            assert service.db is mock_db
            assert service.settings is mock_settings
            # Services should be None initially (lazy loading)
            assert service._question_repository is None
            assert service._prompt_template_service is None
            assert service._llm_parameters_service is None

    def test_lazy_loading_question_repository_red_phase(self, service, mock_db):
        """RED: Test lazy loading of question repository."""
        # Reset to None to test lazy loading
        service._question_repository = None

        with patch('rag_solution.services.question_service.QuestionRepository') as mock_repo_class:
            mock_instance = Mock()
            mock_repo_class.return_value = mock_instance

            result = service.question_repository

            assert result is mock_instance
            mock_repo_class.assert_called_once_with(mock_db)
            # Second access should return cached instance
            result2 = service.question_repository
            assert result2 is mock_instance
            assert mock_repo_class.call_count == 1

    def test_validate_question_valid_simple_question_red_phase(self, service):
        """RED: Test validation of valid simple question."""
        question = "What is machine learning?"
        context = "Machine learning is a subset of artificial intelligence"

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is True
        assert cleaned == "What is machine learning?"

    def test_validate_question_no_question_mark_red_phase(self, service):
        """RED: Test validation rejects questions without question marks."""
        question = "What is machine learning"  # No question mark
        context = "Machine learning is a subset of artificial intelligence"

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is False
        assert cleaned == question

    def test_validate_question_empty_question_red_phase(self, service):
        """RED: Test validation rejects empty questions."""
        question = ""
        context = "Some context"

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is False

    def test_validate_question_multiple_question_marks_red_phase(self, service):
        """RED: Test validation rejects questions with multiple question marks."""
        question = "What is this? And that?"
        context = "Some context"

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is False

    def test_validate_question_too_few_words_red_phase(self, service):
        """RED: Test validation rejects questions with too few words."""
        question = "What?"  # Only 1 word
        context = "Some context"

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is False

    def test_validate_question_removes_numbering_red_phase(self, service):
        """RED: Test validation removes numbering prefix."""
        question = "1. What is machine learning?"
        context = "Machine learning is AI"

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is True
        assert cleaned == "What is machine learning?"

    def test_validate_question_short_with_content_words_red_phase(self, service):
        """RED: Test validation for short questions with content words."""
        question = "What is AI?"  # 3 words, has content word "AI"
        context = "Artificial intelligence (AI) is technology"

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is True

    def test_validate_question_long_with_relevance_red_phase(self, service):
        """RED: Test validation for longer questions with sufficient relevance."""
        question = "What are the main applications of machine learning algorithms?"  # 9 words
        context = "Machine learning algorithms have many applications in technology"

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is True  # Should have >25% word overlap

    def test_validate_question_long_insufficient_relevance_red_phase(self, service):
        """RED: Test validation rejects longer questions with insufficient relevance."""
        question = "What are the best restaurants in Paris today?"  # Irrelevant to context
        context = "Machine learning algorithms are used in data science"

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is False  # Should have <25% word overlap

    def test_rank_questions_returns_sorted_list_red_phase(self, service):
        """RED: Test question ranking returns questions sorted by relevance."""
        questions = [
            "What is data science?",  # High relevance
            "How does machine learning work?",  # Medium relevance
            "What are the best restaurants?"  # Low relevance
        ]
        context = "Data science uses machine learning algorithms to analyze data"

        ranked = service._rank_questions(questions, context)

        # Should return valid questions sorted by relevance
        assert len(ranked) <= len(questions)
        assert "What is data science?" in ranked  # Should be included due to high relevance
        assert "What are the best restaurants?" not in ranked  # Should be excluded

    def test_filter_duplicate_questions_removes_duplicates_red_phase(self, service):
        """RED: Test duplicate filtering removes similar questions."""
        questions = [
            "What is machine learning?",
            "1. What is machine learning?",  # Same after normalization
            "What is AI?",
            "What is machine learning"  # Different punctuation
        ]

        unique = service._filter_duplicate_questions(questions)

        # Should remove duplicates based on normalized comparison
        assert len(unique) < len(questions)
        # Should keep at least the unique ones
        unique_normalized = [q.lower().replace("?", "").strip() for q in unique]
        assert len(set(unique_normalized)) == len(unique)

    def test_combine_text_chunks_respects_length_limits_red_phase(self, service):
        """RED: Test text chunk combination respects length limits."""
        texts = ["Short text", "Another short text", "A much longer text that exceeds the limit"]
        available_length = 30  # Small limit to force splitting

        combined = service._combine_text_chunks(texts, available_length)

        # Should combine texts while respecting length limits
        assert len(combined) >= 1
        for chunk in combined:
            assert len(chunk) <= available_length

    def test_combine_text_chunks_empty_input_red_phase(self, service):
        """RED: Test text chunk combination with empty input."""
        texts = []
        available_length = 1000

        combined = service._combine_text_chunks(texts, available_length)

        assert combined == []

    @pytest.mark.asyncio
    async def test_suggest_questions_empty_texts_red_phase(self, service):
        """RED: Test suggest_questions returns empty list for empty texts."""
        result = await service.suggest_questions(
            texts=[],
            collection_id=uuid4(),
            user_id=uuid4(),
            provider_name="openai",
            template=Mock(),
            parameters=Mock()
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_suggest_questions_success_red_phase(self, service):
        """RED: Test successful question suggestion flow."""
        texts = ["Machine learning is a field of AI", "It involves algorithms and data"]
        collection_id = uuid4()
        user_id = uuid4()

        # Mock provider and responses
        mock_provider = Mock()
        mock_provider.generate_text.return_value = ["What is machine learning?", "How do algorithms work?"]
        service._provider_factory.get_provider.return_value = mock_provider

        # Mock question creation
        mock_questions = [
            SuggestedQuestion(id=uuid4(), collection_id=collection_id, question="What is machine learning?"),
            SuggestedQuestion(id=uuid4(), collection_id=collection_id, question="How do algorithms work?")
        ]
        service._question_repository.create_questions.return_value = mock_questions

        with patch('time.time', side_effect=[1000.0, 1000.2, 1000.4, 1000.6, 1000.8, 1001.0, 1001.2, 1001.5]):  # Start and end times plus logging calls
            result = await service.suggest_questions(
                texts=texts,
                collection_id=collection_id,
                user_id=user_id,
                provider_name="openai",
                template=Mock(),
                parameters=Mock()
            )

        assert len(result) == 2
        assert all(isinstance(q, SuggestedQuestion) for q in result)
        service._question_repository.create_questions.assert_called_once()

    @pytest.mark.asyncio
    async def test_suggest_questions_validation_error_red_phase(self, service):
        """RED: Test suggest_questions handles validation errors properly."""
        texts = ["Some text"]

        # Mock settings as None to trigger validation error
        service.settings = None

        with pytest.raises(ValueError) as exc_info:
            await service.suggest_questions(
                texts=texts,
                collection_id=uuid4(),
                user_id=uuid4(),
                provider_name="openai",
                template=Mock(),
                parameters=Mock()
            )

        assert "Settings must be provided" in str(exc_info.value)

    def test_setup_question_generation_success_red_phase(self, service):
        """RED: Test successful setup of question generation components."""
        texts = ["Text 1", "Text 2"]
        provider_name = "openai"
        template = Mock()
        parameters = Mock()

        mock_provider = Mock()
        service._provider_factory.get_provider.return_value = mock_provider

        provider, combined_texts, stats = service._setup_question_generation(texts, provider_name, template, parameters)

        assert provider is mock_provider
        assert len(combined_texts) >= 1  # Should combine texts
        assert stats["total_chunks"] == 2
        assert stats["successful_generations"] == 0
        assert stats["failed_generations"] == 0

    @pytest.mark.asyncio
    async def test_generate_questions_from_texts_success_red_phase(self, service):
        """RED: Test successful question generation from texts."""
        combined_texts = ["Combined text chunk"]
        mock_provider = Mock()
        mock_provider.generate_text.return_value = "What is this?\nHow does it work?"

        user_id = uuid4()
        template = Mock()
        parameters = Mock()
        stats = {"successful_generations": 0, "failed_generations": 0}

        result = await service._generate_questions_from_texts(
            combined_texts, mock_provider, user_id, template, parameters, 3, stats
        )

        assert "What is this?" in result
        assert "How does it work?" in result
        assert stats["successful_generations"] == 1
        assert stats["failed_generations"] == 0

    @pytest.mark.asyncio
    async def test_generate_questions_from_texts_provider_failure_red_phase(self, service):
        """RED: Test question generation handles provider failures gracefully."""
        combined_texts = ["Combined text chunk"]
        mock_provider = Mock()
        mock_provider.generate_text.side_effect = Exception("Provider failed")

        user_id = uuid4()
        template = Mock()
        parameters = Mock()
        stats = {"successful_generations": 0, "failed_generations": 0}

        result = await service._generate_questions_from_texts(
            combined_texts, mock_provider, user_id, template, parameters, 3, stats
        )

        assert result == []  # Should return empty list on failure
        assert stats["successful_generations"] == 0
        assert stats["failed_generations"] == 1

    def test_extract_questions_from_responses_list_input_red_phase(self, service):
        """RED: Test question extraction from list responses."""
        responses = [
            "What is this?\nHow does it work?\nNot a question",
            "Why is this important?\nSome statement."
        ]

        result = service._extract_questions_from_responses(responses)

        expected = ["What is this?", "How does it work?", "Why is this important?"]
        assert result == expected

    def test_extract_questions_from_responses_string_input_red_phase(self, service):
        """RED: Test question extraction from string response."""
        response = "What is this?\nHow does it work?\nNot a question"

        result = service._extract_questions_from_responses(response)

        expected = ["What is this?", "How does it work?"]
        assert result == expected

    def test_process_generated_questions_filters_and_ranks_red_phase(self, service):
        """RED: Test processing filters invalid questions and ranks valid ones."""
        all_questions = [
            "What is machine learning?",  # Valid
            "Invalid question",  # Invalid - no question mark
            "How does AI work?",  # Valid
            "What is machine learning?"  # Duplicate
        ]
        texts = ["Machine learning and AI are important technologies"]

        # Mock validation to return specific results
        def mock_validate(q, ctx):
            return q.endswith("?"), q
        service._validate_question = mock_validate

        result = service._process_generated_questions(all_questions, texts, None)

        # Should filter out invalid questions and duplicates
        assert len(result) <= 2  # Max 2 unique valid questions
        assert "Invalid question" not in result
        assert all(q.endswith("?") for q in result)

    @pytest.mark.asyncio
    async def test_store_questions_success_red_phase(self, service):
        """RED: Test successful question storage."""
        collection_id = uuid4()
        questions = ["What is this?", "How does it work?"]

        mock_stored_questions = [
            SuggestedQuestion(id=uuid4(), collection_id=collection_id, question=q)
            for q in questions
        ]

        # Mock the asyncio.to_thread call
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = mock_stored_questions

            result = await service._store_questions(collection_id, questions)

            assert result == mock_stored_questions
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_questions_empty_input_red_phase(self, service):
        """RED: Test question storage with empty input."""
        collection_id = uuid4()
        questions = []

        result = await service._store_questions(collection_id, questions)

        assert result == []

    def test_create_question_success_red_phase(self, service):
        """RED: Test successful question creation."""
        question_input = QuestionInput(
            collection_id=uuid4(),
            question="What is this?"
        )

        expected_question = SuggestedQuestion(
            id=uuid4(),
            collection_id=question_input.collection_id,
            question=question_input.question
        )

        service._question_repository.create_question.return_value = expected_question

        result = service.create_question(question_input)

        assert result is expected_question
        service._question_repository.create_question.assert_called_once_with(question_input)

    def test_create_question_repository_error_red_phase(self, service):
        """RED: Test question creation handles repository errors."""
        question_input = QuestionInput(
            collection_id=uuid4(),
            question="What is this?"
        )

        service._question_repository.create_question.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            service.create_question(question_input)

        assert "Database error" in str(exc_info.value)

    def test_delete_question_success_red_phase(self, service):
        """RED: Test successful question deletion."""
        question_id = uuid4()

        service._question_repository.delete_question.return_value = None

        result = service.delete_question(question_id)

        assert result is None
        service._question_repository.delete_question.assert_called_once_with(question_id)

    def test_delete_question_not_found_red_phase(self, service):
        """RED: Test question deletion when question not found."""
        question_id = uuid4()

        service._question_repository.delete_question.side_effect = NotFoundError("Question", str(question_id))

        with pytest.raises(NotFoundError):
            service.delete_question(question_id)

    def test_delete_questions_by_collection_success_red_phase(self, service):
        """RED: Test successful deletion of collection questions."""
        collection_id = uuid4()

        service._question_repository.delete_questions_by_collection.return_value = None

        result = service.delete_questions_by_collection(collection_id)

        assert result is None
        service._question_repository.delete_questions_by_collection.assert_called_once_with(collection_id)

    def test_get_collection_questions_success_red_phase(self, service):
        """RED: Test successful retrieval of collection questions."""
        collection_id = uuid4()
        expected_questions = [
            SuggestedQuestion(id=uuid4(), collection_id=collection_id, question="What is this?"),
            SuggestedQuestion(id=uuid4(), collection_id=collection_id, question="How does it work?")
        ]

        service._question_repository.get_questions_by_collection.return_value = expected_questions

        result = service.get_collection_questions(collection_id)

        assert result == expected_questions
        service._question_repository.get_questions_by_collection.assert_called_once_with(collection_id)

    def test_get_collection_questions_error_red_phase(self, service):
        """RED: Test collection questions retrieval handles errors."""
        collection_id = uuid4()

        service._question_repository.get_questions_by_collection.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            service.get_collection_questions(collection_id)

        assert "Database error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_regenerate_questions_success_red_phase(self, service):
        """RED: Test successful question regeneration."""
        collection_id = uuid4()
        user_id = uuid4()
        texts = ["Text for regeneration"]

        # Mock deletion
        service._question_repository.delete_questions_by_collection.return_value = None

        # Mock new question generation
        expected_questions = [
            SuggestedQuestion(id=uuid4(), collection_id=collection_id, question="What is regenerated?")
        ]

        # Mock the suggest_questions method
        service.suggest_questions = AsyncMock(return_value=expected_questions)

        result = await service.regenerate_questions(
            collection_id=collection_id,
            user_id=user_id,
            texts=texts,
            provider_name="openai",
            template=Mock(),
            parameters=Mock()
        )

        assert result == expected_questions
        service._question_repository.delete_questions_by_collection.assert_called_once_with(collection_id)
        service.suggest_questions.assert_called_once()

    @pytest.mark.asyncio
    async def test_regenerate_questions_deletion_error_red_phase(self, service):
        """RED: Test question regeneration handles deletion errors."""
        collection_id = uuid4()

        service._question_repository.delete_questions_by_collection.side_effect = Exception("Delete failed")

        with pytest.raises(Exception) as exc_info:
            await service.regenerate_questions(
                collection_id=collection_id,
                user_id=uuid4(),
                texts=["Text"],
                provider_name="openai",
                template=Mock(),
                parameters=Mock()
            )

        assert "Delete failed" in str(exc_info.value)

    def test_ranking_algorithm_logic_issue_red_phase(self, service):
        """RED: Test ranking algorithm potential division by zero issue."""
        questions = ["What?"]  # Single word question (after removing stop words)
        context = "machine learning context"

        # This should not crash due to division by zero
        ranked = service._rank_questions(questions, context)

        # Should handle edge case gracefully
        assert isinstance(ranked, list)

    def test_text_combination_logic_issue_red_phase(self, service):
        """RED: Test text combination with edge case of single large text."""
        texts = ["A" * 5000]  # Single very large text
        available_length = 1000  # Much smaller than text

        combined = service._combine_text_chunks(texts, available_length)

        # LOGIC ISSUE: Should this truncate or skip the large text?
        # Current implementation may create empty batches
        if combined:
            assert all(len(chunk) <= available_length for chunk in combined)

# RED PHASE COMPLETE: These tests will reveal several logic issues:
# 1. Complex question validation logic with edge cases
# 2. Potential division by zero in ranking algorithm
# 3. Text combination algorithm may not handle oversized texts well
# 4. Async/await patterns may have race conditions
# 5. Error handling inconsistencies across methods
# Let's run these to see what fails and needs fixing
