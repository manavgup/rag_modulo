"""
Unit tests for QuestionService.

This module tests the QuestionService class which handles question suggestion
functionality with Chain of Thought support for both document-based and
conversation-based question generation.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from datetime import datetime

from rag_solution.services.question_service import QuestionService
from rag_solution.schemas.question_schema import QuestionInput
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase
from rag_solution.models.question import SuggestedQuestion
from core.config import Settings
from core.custom_exceptions import NotFoundError, ValidationError


class TestQuestionService:
    """Test cases for QuestionService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.max_questions_per_collection = 15
        settings.max_chunks_for_questions = 8
        settings.cot_question_ratio = 0.4
        return settings

    @pytest.fixture
    def service(self, mock_db_session, mock_settings):
        """Create a service instance with mocked dependencies."""
        return QuestionService(mock_db_session, mock_settings)

    @pytest.fixture
    def sample_collection_id(self):
        """Create a sample collection ID."""
        return uuid4()

    @pytest.fixture
    def sample_user_id(self):
        """Create a sample user ID."""
        return uuid4()

    def test_service_initialization(self, service, mock_db_session, mock_settings):
        """Test service initialization with dependencies."""
        assert service.db == mock_db_session
        assert service.settings == mock_settings
        assert service.max_questions_per_collection == 15
        assert service.max_chunks_to_process == 8
        assert service.cot_question_ratio == 0.4
        assert service._question_repository is None
        assert service._prompt_template_service is None
        assert service._llm_parameters_service is None

    def test_question_repository_lazy_initialization(self, service):
        """Test lazy initialization of question repository."""
        with patch('rag_solution.services.question_service.QuestionRepository') as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo

            # First access should create the repository
            repo = service.question_repository
            assert repo == mock_repo
            mock_repo_class.assert_called_once_with(service.db)

            # Second access should return the same instance
            repo2 = service.question_repository
            assert repo2 == mock_repo
            assert mock_repo_class.call_count == 1

    def test_prompt_template_service_lazy_initialization(self, service):
        """Test lazy initialization of prompt template service."""
        with patch('rag_solution.services.question_service.PromptTemplateService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service

            # First access should create the service
            svc = service.prompt_template_service
            assert svc == mock_service
            mock_service_class.assert_called_once_with(service.db)

            # Second access should return the same instance
            svc2 = service.prompt_template_service
            assert svc2 == mock_service
            assert mock_service_class.call_count == 1

    def test_llm_parameters_service_lazy_initialization(self, service):
        """Test lazy initialization of LLM parameters service."""
        with patch('rag_solution.services.question_service.LLMParametersService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service

            # First access should create the service
            svc = service.llm_parameters_service
            assert svc == mock_service
            mock_service_class.assert_called_once_with(service.db)

            # Second access should return the same instance
            svc2 = service.llm_parameters_service
            assert svc2 == mock_service
            assert mock_service_class.call_count == 1

    def test_validate_question_valid_question(self, service):
        """Test validation of a valid question."""
        question = "What is the main topic of this document?"
        context = "This document discusses machine learning algorithms and their applications."

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is True
        assert cleaned == "What is the main topic of this document?"

    def test_validate_question_no_question_mark(self, service):
        """Test validation of question without question mark."""
        question = "What is the main topic"
        context = "This document discusses machine learning algorithms."

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is False
        assert cleaned == "What is the main topic"

    def test_validate_question_empty_question(self, service):
        """Test validation of empty question."""
        question = ""
        context = "This document discusses machine learning algorithms."

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is False
        assert cleaned == ""

    def test_validate_question_multiple_question_marks(self, service):
        """Test validation of question with multiple question marks."""
        question = "What is this? And that?"
        context = "This document discusses machine learning algorithms."

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is False
        assert cleaned == "What is this? And that?"

    def test_validate_question_numbering_prefix(self, service):
        """Test validation of question with numbering prefix."""
        question = "1. What is the main topic of this document?"
        context = "This document discusses machine learning algorithms."

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is True
        assert cleaned == "What is the main topic of this document?"

    def test_validate_question_short_question_with_content_match(self, service):
        """Test validation of short question with content word match."""
        question = "What algorithms?"
        context = "This document discusses machine learning algorithms and neural networks."

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is True
        assert cleaned == "What algorithms?"

    def test_validate_question_short_question_no_content_match(self, service):
        """Test validation of short question without content word match."""
        question = "What is this?"
        context = "This document discusses machine learning algorithms."

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is False
        assert cleaned == "What is this?"

    def test_validate_question_long_question_high_relevance(self, service):
        """Test validation of long question with high relevance."""
        question = "What are the main machine learning algorithms discussed in this document?"
        context = "This document discusses machine learning algorithms including neural networks, decision trees, and support vector machines."

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is True
        assert cleaned == "What are the main machine learning algorithms discussed in this document?"

    def test_validate_question_long_question_low_relevance(self, service):
        """Test validation of long question with low relevance."""
        question = "What are the main cooking recipes discussed in this document?"
        context = "This document discusses machine learning algorithms and neural networks."

        is_valid, cleaned = service._validate_question(question, context)

        assert is_valid is False
        assert cleaned == "What are the main cooking recipes discussed in this document?"

    def test_rank_questions(self, service):
        """Test ranking of questions by relevance."""
        questions = [
            "What is machine learning?",
            "How do neural networks work?",
            "What is cooking?"
        ]
        context = "This document discusses machine learning algorithms and neural networks."

        ranked = service._rank_questions(questions, context)

        # Should return valid questions in order of relevance
        assert len(ranked) >= 2  # At least 2 valid questions
        assert "What is cooking?" not in ranked  # Should be filtered out
        # First question should be most relevant
        assert ranked[0] in ["What is machine learning?", "How do neural networks work?"]

    def test_filter_duplicate_questions(self, service):
        """Test filtering of duplicate questions."""
        questions = [
            "What is machine learning?",
            "What is machine learning?",  # Exact duplicate
            "1. What is machine learning?",  # Duplicate with numbering
            "What is machine learning!",  # Duplicate with different punctuation
            "How do neural networks work?",
            "What is deep learning?"
        ]

        filtered = service._filter_duplicate_questions(questions)

        # Should remove duplicates but keep unique questions
        assert len(filtered) == 3
        assert "What is machine learning?" in filtered
        assert "How do neural networks work?" in filtered
        assert "What is deep learning?" in filtered

    def test_select_representative_chunks_empty_list(self, service):
        """Test selection of representative chunks from empty list."""
        chunks = service._select_representative_chunks([], 5)
        assert chunks == []

    def test_select_representative_chunks_fewer_than_max(self, service):
        """Test selection when fewer chunks than max."""
        texts = ["chunk1", "chunk2", "chunk3"]
        chunks = service._select_representative_chunks(texts, 5)
        assert len(chunks) == 3
        assert chunks == texts

    def test_select_representative_chunks_more_than_max(self, service):
        """Test selection when more chunks than max."""
        texts = [f"chunk{i}" for i in range(10)]
        chunks = service._select_representative_chunks(texts, 5)
        assert len(chunks) == 5
        # Should include first, middle, and last chunks
        assert "chunk0" in chunks  # First chunk
        assert "chunk9" in chunks  # Last chunk

    def test_select_representative_chunks_single_chunk(self, service):
        """Test selection with single chunk."""
        texts = ["single chunk"]
        chunks = service._select_representative_chunks(texts, 5)
        assert chunks == ["single chunk"]

    @pytest.mark.asyncio
    async def test_generate_questions_for_collection_success(self, service, sample_collection_id, sample_user_id):
        """Test successful generation of questions for collection."""
        # Mock dependencies
        mock_llm_service = AsyncMock()
        mock_llm_service.generate_text_with_usage.return_value = (
            "1. What is the main topic?\n2. How does it work?\n3. What are the benefits?",
            {"prompt_tokens": 100, "completion_tokens": 50}
        )

        with patch.object(service, 'question_repository') as mock_repo, \
             patch.object(service, 'prompt_template_service') as mock_prompt_service, \
             patch.object(service, 'llm_parameters_service') as mock_llm_params_service, \
             patch('rag_solution.services.question_service.LLMProviderFactory') as mock_factory:

            # Setup mocks
            mock_repo.get_collection_chunks.return_value = [
                Mock(text="This document discusses machine learning algorithms.", chunk_index=0),
                Mock(text="Neural networks are a key component.", chunk_index=1)
            ]

            mock_prompt_template = Mock(spec=PromptTemplateBase)
            mock_prompt_template.template = "Generate questions based on: {context}"
            mock_prompt_service.get_template.return_value = mock_prompt_template

            mock_llm_params = Mock(spec=LLMParametersInput)
            mock_llm_params_service.get_user_parameters.return_value = mock_llm_params

            mock_provider = Mock()
            mock_provider.generate_text_with_usage = mock_llm_service.generate_text_with_usage
            mock_factory.return_value.get_provider.return_value = mock_provider

            # Execute
            result = await service.generate_questions_for_collection(sample_collection_id, sample_user_id)

            # Verify
            assert isinstance(result, list)
            assert len(result) > 0
            mock_repo.get_collection_chunks.assert_called_once_with(sample_collection_id)
            mock_prompt_service.get_template.assert_called_once()
            mock_llm_params_service.get_user_parameters.assert_called_once_with(sample_user_id)

    @pytest.mark.asyncio
    async def test_generate_questions_for_collection_no_chunks(self, service, sample_collection_id, sample_user_id):
        """Test generation when collection has no chunks."""
        with patch.object(service, 'question_repository') as mock_repo:
            mock_repo.get_collection_chunks.return_value = []

            result = await service.generate_questions_for_collection(sample_collection_id, sample_user_id)

            assert result == []

    @pytest.mark.asyncio
    async def test_generate_questions_for_collection_llm_error(self, service, sample_collection_id, sample_user_id):
        """Test handling of LLM generation error."""
        with patch.object(service, 'question_repository') as mock_repo, \
             patch.object(service, 'prompt_template_service') as mock_prompt_service, \
             patch.object(service, 'llm_parameters_service') as mock_llm_params_service, \
             patch('rag_solution.services.question_service.LLMProviderFactory') as mock_factory:

            # Setup mocks
            mock_repo.get_collection_chunks.return_value = [
                Mock(text="This document discusses machine learning.", chunk_index=0)
            ]

            mock_prompt_template = Mock(spec=PromptTemplateBase)
            mock_prompt_template.template = "Generate questions: {context}"
            mock_prompt_service.get_template.return_value = mock_prompt_template

            mock_llm_params = Mock(spec=LLMParametersInput)
            mock_llm_params_service.get_user_parameters.return_value = mock_llm_params

            mock_provider = Mock()
            mock_provider.generate_text_with_usage.side_effect = Exception("LLM error")
            mock_factory.return_value.get_provider.return_value = mock_provider

            # Execute
            result = await service.generate_questions_for_collection(sample_collection_id, sample_user_id)

            # Should return empty list on error
            assert result == []

    def test_save_questions_success(self, service, sample_collection_id, sample_user_id):
        """Test successful saving of questions."""
        questions = [
            "What is machine learning?",
            "How do neural networks work?"
        ]

        with patch.object(service, 'question_repository') as mock_repo:
            mock_repo.create_questions.return_value = [
                Mock(id=uuid4(), question=q, collection_id=sample_collection_id, user_id=sample_user_id)
                for q in questions
            ]

            result = service.save_questions(questions, sample_collection_id, sample_user_id)

            assert len(result) == 2
            assert all(isinstance(q, SuggestedQuestion) for q in result)
            mock_repo.create_questions.assert_called_once()

    def test_save_questions_empty_list(self, service, sample_collection_id, sample_user_id):
        """Test saving empty list of questions."""
        with patch.object(service, 'question_repository') as mock_repo:
            result = service.save_questions([], sample_collection_id, sample_user_id)

            assert result == []
            mock_repo.create_questions.assert_not_called()

    def test_get_questions_for_collection_success(self, service, sample_collection_id):
        """Test successful retrieval of questions for collection."""
        with patch.object(service, 'question_repository') as mock_repo:
            mock_questions = [
                Mock(id=uuid4(), question="What is machine learning?", collection_id=sample_collection_id),
                Mock(id=uuid4(), question="How do neural networks work?", collection_id=sample_collection_id)
            ]
            mock_repo.get_questions_by_collection.return_value = mock_questions

            result = service.get_questions_for_collection(sample_collection_id)

            assert len(result) == 2
            assert all(isinstance(q, SuggestedQuestion) for q in result)
            mock_repo.get_questions_by_collection.assert_called_once_with(sample_collection_id)

    def test_get_questions_for_collection_not_found(self, service, sample_collection_id):
        """Test retrieval when no questions found."""
        with patch.object(service, 'question_repository') as mock_repo:
            mock_repo.get_questions_by_collection.return_value = []

            result = service.get_questions_for_collection(sample_collection_id)

            assert result == []

    def test_delete_questions_for_collection_success(self, service, sample_collection_id):
        """Test successful deletion of questions for collection."""
        with patch.object(service, 'question_repository') as mock_repo:
            mock_repo.delete_questions_by_collection.return_value = 3

            result = service.delete_questions_for_collection(sample_collection_id)

            assert result == 3
            mock_repo.delete_questions_by_collection.assert_called_once_with(sample_collection_id)

    def test_delete_questions_for_collection_none_deleted(self, service, sample_collection_id):
        """Test deletion when no questions to delete."""
        with patch.object(service, 'question_repository') as mock_repo:
            mock_repo.delete_questions_by_collection.return_value = 0

            result = service.delete_questions_for_collection(sample_collection_id)

            assert result == 0
