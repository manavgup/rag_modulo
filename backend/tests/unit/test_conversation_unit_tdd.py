"""TDD Red Phase: Unit tests for conversation functionality.

Unit tests focus on individual methods and classes in isolation,
with mocked dependencies.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from pydantic import UUID4

from rag_solution.services.conversation_service import ConversationService
from rag_solution.services.context_manager_service import ContextManagerService
from rag_solution.services.question_suggestion_service import QuestionSuggestionService
from rag_solution.schemas.conversation_schema import (
    ConversationSessionInput,
    ConversationSessionOutput,
    ConversationMessageInput,
    ConversationMessageOutput,
    ConversationContext,
    SessionStatus,
    MessageRole,
    MessageType,
)
from rag_solution.core.exceptions import NotFoundError, ValidationError, SessionExpiredError


class TestConversationServiceUnitTDD:
    """Unit tests for ConversationService individual methods."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Mock settings."""
        settings = Mock()
        settings.session_timeout_minutes = 30
        settings.max_context_window_size = 8000
        settings.max_messages_per_session = 100
        return settings

    @pytest.fixture
    def conversation_service(self, mock_db: Mock, mock_settings: Mock) -> ConversationService:
        """Create conversation service instance."""
        return ConversationService(mock_db, mock_settings)

    # ==================== UNIT TESTS ====================

    @pytest.mark.unit
    def test_create_session_validation_success(self, conversation_service: ConversationService) -> None:
        """Unit: Test create_session validates input successfully."""
        # Arrange
        session_input = ConversationSessionInput(
            user_id=uuid4(),
            collection_id=uuid4(),
            session_name="Test Session"
        )
        
        # Act
        result = conversation_service.create_session(session_input)
        
        # Assert
        assert isinstance(result, ConversationSessionOutput)
        assert result.session_name == "Test Session"
        assert result.status == SessionStatus.ACTIVE

    @pytest.mark.unit
    def test_create_session_validation_error(self, conversation_service: ConversationService) -> None:
        """Unit: Test create_session raises ValidationError for invalid input."""
        # Arrange
        session_input = ConversationSessionInput(
            user_id=uuid4(),
            collection_id=uuid4(),
            session_name=""  # Invalid empty name
        )
        
        # Act & Assert
        with pytest.raises(ValidationError):
            conversation_service.create_session(session_input)

    @pytest.mark.unit
    def test_get_session_success(self, conversation_service: ConversationService) -> None:
        """Unit: Test get_session returns session when found."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()
        
        # Act
        result = conversation_service.get_session(session_id, user_id)
        
        # Assert
        assert isinstance(result, ConversationSessionOutput)
        assert result.id == session_id
        assert result.user_id == user_id

    @pytest.mark.unit
    def test_get_session_not_found(self, conversation_service: ConversationService) -> None:
        """Unit: Test get_session raises NotFoundError when session not found."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()
        
        # Act & Assert
        with pytest.raises(NotFoundError):
            conversation_service.get_session(session_id, user_id)

    @pytest.mark.unit
    def test_add_message_validation_success(self, conversation_service: ConversationService) -> None:
        """Unit: Test add_message validates input successfully."""
        # Arrange
        message_input = ConversationMessageInput(
            session_id=uuid4(),
            content="Test message",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION
        )
        
        # Act
        result = conversation_service.add_message(message_input)
        
        # Assert
        assert isinstance(result, ConversationMessageOutput)
        assert result.content == "Test message"
        assert result.role == MessageRole.USER

    @pytest.mark.unit
    def test_add_message_session_not_found(self, conversation_service: ConversationService) -> None:
        """Unit: Test add_message raises NotFoundError for non-existent session."""
        # Arrange
        message_input = ConversationMessageInput(
            session_id=uuid4(),
            content="Test message",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION
        )
        
        # Act & Assert
        with pytest.raises(NotFoundError):
            conversation_service.add_message(message_input)

    @pytest.mark.unit
    def test_add_message_session_expired(self, conversation_service: ConversationService) -> None:
        """Unit: Test add_message raises SessionExpiredError for expired session."""
        # Arrange
        message_input = ConversationMessageInput(
            session_id=uuid4(),
            content="Test message",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION
        )
        
        # Act & Assert
        with pytest.raises(SessionExpiredError):
            conversation_service.add_message(message_input)

    @pytest.mark.unit
    def test_update_session_success(self, conversation_service: ConversationService) -> None:
        """Unit: Test update_session updates session successfully."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()
        updates = {"session_name": "Updated Name"}
        
        # Act
        result = conversation_service.update_session(session_id, user_id, updates)
        
        # Assert
        assert isinstance(result, ConversationSessionOutput)
        assert result.session_name == "Updated Name"

    @pytest.mark.unit
    def test_update_session_not_found(self, conversation_service: ConversationService) -> None:
        """Unit: Test update_session raises NotFoundError for non-existent session."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()
        updates = {"session_name": "Updated Name"}
        
        # Act & Assert
        with pytest.raises(NotFoundError):
            conversation_service.update_session(session_id, user_id, updates)

    @pytest.mark.unit
    def test_delete_session_success(self, conversation_service: ConversationService) -> None:
        """Unit: Test delete_session deletes session successfully."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()
        
        # Act
        result = conversation_service.delete_session(session_id, user_id)
        
        # Assert
        assert result is True

    @pytest.mark.unit
    def test_delete_session_not_found(self, conversation_service: ConversationService) -> None:
        """Unit: Test delete_session raises NotFoundError for non-existent session."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()
        
        # Act & Assert
        with pytest.raises(NotFoundError):
            conversation_service.delete_session(session_id, user_id)

    @pytest.mark.unit
    def test_get_session_messages_pagination(self, conversation_service: ConversationService) -> None:
        """Unit: Test get_session_messages with pagination parameters."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()
        limit = 10
        offset = 5
        
        # Act
        result = conversation_service.get_session_messages(session_id, user_id, limit, offset)
        
        # Assert
        assert isinstance(result, list)
        assert len(result) <= limit

    @pytest.mark.unit
    def test_archive_session_success(self, conversation_service: ConversationService) -> None:
        """Unit: Test archive_session changes status to ARCHIVED."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()
        
        # Act
        result = conversation_service.archive_session(session_id, user_id)
        
        # Assert
        assert isinstance(result, ConversationSessionOutput)
        assert result.status == SessionStatus.ARCHIVED

    @pytest.mark.unit
    def test_restore_session_success(self, conversation_service: ConversationService) -> None:
        """Unit: Test restore_session changes status to ACTIVE."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()
        
        # Act
        result = conversation_service.restore_session(session_id, user_id)
        
        # Assert
        assert isinstance(result, ConversationSessionOutput)
        assert result.status == SessionStatus.ACTIVE

    @pytest.mark.unit
    def test_export_session_json_format(self, conversation_service: ConversationService) -> None:
        """Unit: Test export_session with JSON format."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()
        export_format = "json"
        
        # Act
        result = conversation_service.export_session(session_id, user_id, export_format)
        
        # Assert
        assert isinstance(result, dict)
        assert "session_data" in result
        assert "messages" in result

    @pytest.mark.unit
    def test_export_session_unsupported_format(self, conversation_service: ConversationService) -> None:
        """Unit: Test export_session raises ValidationError for unsupported format."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()
        export_format = "unsupported"
        
        # Act & Assert
        with pytest.raises(ValidationError):
            conversation_service.export_session(session_id, user_id, export_format)

    @pytest.mark.unit
    def test_cleanup_expired_sessions(self, conversation_service: ConversationService) -> None:
        """Unit: Test cleanup_expired_sessions returns count of cleaned sessions."""
        # Act
        result = conversation_service.cleanup_expired_sessions()
        
        # Assert
        assert isinstance(result, int)
        assert result >= 0

    @pytest.mark.unit
    def test_get_session_statistics(self, conversation_service: ConversationService) -> None:
        """Unit: Test get_session_statistics returns correct structure."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()
        
        # Act
        result = conversation_service.get_session_statistics(session_id, user_id)
        
        # Assert
        assert isinstance(result, dict)
        assert "message_count" in result
        assert "session_duration" in result
        assert "average_response_time" in result

    @pytest.mark.unit
    def test_search_sessions_by_query(self, conversation_service: ConversationService) -> None:
        """Unit: Test search_sessions returns filtered results."""
        # Arrange
        user_id = uuid4()
        query = "machine learning"
        
        # Act
        result = conversation_service.search_sessions(user_id, query)
        
        # Assert
        assert isinstance(result, list)
        assert all(isinstance(session, ConversationSessionOutput) for session in result)

    @pytest.mark.unit
    def test_get_user_sessions_with_status_filter(self, conversation_service: ConversationService) -> None:
        """Unit: Test get_user_sessions with status filter."""
        # Arrange
        user_id = uuid4()
        status = SessionStatus.ACTIVE
        
        # Act
        result = conversation_service.get_user_sessions(user_id, status=status)
        
        # Assert
        assert isinstance(result, list)
        assert all(session.status == status for session in result)


class TestContextManagerServiceUnitTDD:
    """Unit tests for ContextManagerService individual methods."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Mock settings."""
        settings = Mock()
        settings.max_context_window_size = 8000
        settings.context_pruning_threshold = 0.7
        return settings

    @pytest.fixture
    def context_manager_service(self, mock_db: Mock, mock_settings: Mock) -> ContextManagerService:
        """Create context manager service instance."""
        return ContextManagerService(mock_db, mock_settings)

    @pytest.mark.unit
    def test_build_context_from_messages(self, context_manager_service: ContextManagerService) -> None:
        """Unit: Test build_context_from_messages creates context from message history."""
        # Arrange
        session_id = uuid4()
        messages = [
            ConversationMessageOutput(
                id=uuid4(),
                session_id=session_id,
                content="What is AI?",
                role=MessageRole.USER,
                message_type=MessageType.QUESTION,
                metadata={},
                created_at=datetime.now()
            ),
            ConversationMessageOutput(
                id=uuid4(),
                session_id=session_id,
                content="AI is artificial intelligence...",
                role=MessageRole.ASSISTANT,
                message_type=MessageType.ANSWER,
                metadata={},
                created_at=datetime.now()
            )
        ]
        
        # Act
        result = context_manager_service.build_context_from_messages(session_id, messages)
        
        # Assert
        assert isinstance(result, ConversationContext)
        assert result.session_id == session_id
        assert "What is AI?" in result.context_window
        assert "AI is artificial intelligence" in result.context_window

    @pytest.mark.unit
    def test_prune_context_by_relevance(self, context_manager_service: ContextManagerService) -> None:
        """Unit: Test prune_context_by_relevance removes less relevant content."""
        # Arrange
        context = ConversationContext(
            session_id=uuid4(),
            context_window="This is about AI and machine learning. Some irrelevant content here.",
            relevant_documents=["doc1", "doc2"],
            context_metadata={"relevance_scores": {"doc1": 0.9, "doc2": 0.3}}
        )
        
        # Act
        result = context_manager_service.prune_context_by_relevance(context, threshold=0.5)
        
        # Assert
        assert isinstance(result, ConversationContext)
        assert len(result.relevant_documents) <= len(context.relevant_documents)

    @pytest.mark.unit
    def test_extract_key_entities(self, context_manager_service: ContextManagerService) -> None:
        """Unit: Test extract_key_entities identifies important entities."""
        # Arrange
        text = "Artificial intelligence and machine learning are transforming healthcare."
        
        # Act
        result = context_manager_service.extract_key_entities(text)
        
        # Assert
        assert isinstance(result, list)
        assert "artificial intelligence" in result or "AI" in result
        assert "machine learning" in result or "ML" in result

    @pytest.mark.unit
    def test_resolve_pronouns(self, context_manager_service: ContextManagerService) -> None:
        """Unit: Test resolve_pronouns resolves pronouns in context."""
        # Arrange
        current_message = "Tell me more about it."
        context = "We discussed machine learning algorithms."
        
        # Act
        result = context_manager_service.resolve_pronouns(current_message, context)
        
        # Assert
        assert isinstance(result, str)
        assert "machine learning algorithms" in result or "it" not in result

    @pytest.mark.unit
    def test_detect_follow_up_question(self, context_manager_service: ContextManagerService) -> None:
        """Unit: Test detect_follow_up_question identifies follow-up questions."""
        # Arrange
        current_message = "What about deep learning?"
        previous_messages = [
            ConversationMessageOutput(
                id=uuid4(),
                session_id=uuid4(),
                content="Tell me about machine learning",
                role=MessageRole.USER,
                message_type=MessageType.QUESTION,
                metadata={},
                created_at=datetime.now()
            )
        ]
        
        # Act
        result = context_manager_service.detect_follow_up_question(current_message, previous_messages)
        
        # Assert
        assert isinstance(result, bool)
        assert result is True  # Should be detected as follow-up

    @pytest.mark.unit
    def test_calculate_context_relevance(self, context_manager_service: ContextManagerService) -> None:
        """Unit: Test calculate_context_relevance scores context relevance."""
        # Arrange
        context = "This is about machine learning and AI."
        query = "What is machine learning?"
        
        # Act
        result = context_manager_service.calculate_context_relevance(context, query)
        
        # Assert
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    @pytest.mark.unit
    def test_merge_contexts(self, context_manager_service: ContextManagerService) -> None:
        """Unit: Test merge_contexts combines multiple contexts."""
        # Arrange
        context1 = ConversationContext(
            session_id=uuid4(),
            context_window="Context about AI",
            relevant_documents=["doc1"],
            context_metadata={}
        )
        context2 = ConversationContext(
            session_id=uuid4(),
            context_window="Context about ML",
            relevant_documents=["doc2"],
            context_metadata={}
        )
        
        # Act
        result = context_manager_service.merge_contexts([context1, context2])
        
        # Assert
        assert isinstance(result, ConversationContext)
        assert "AI" in result.context_window
        assert "ML" in result.context_window
        assert len(result.relevant_documents) >= 2


class TestQuestionSuggestionServiceUnitTDD:
    """Unit tests for QuestionSuggestionService individual methods."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Mock settings."""
        settings = Mock()
        settings.suggestion_cache_ttl = 3600
        settings.max_suggestions = 5
        return settings

    @pytest.fixture
    def question_suggestion_service(self, mock_db: Mock, mock_settings: Mock) -> QuestionSuggestionService:
        """Create question suggestion service instance."""
        return QuestionSuggestionService(mock_db, mock_settings)

    @pytest.mark.unit
    def test_generate_suggestions_from_context(self, question_suggestion_service: QuestionSuggestionService) -> None:
        """Unit: Test generate_suggestions_from_context creates relevant suggestions."""
        # Arrange
        context = "This document discusses machine learning algorithms and their applications in healthcare."
        max_suggestions = 3
        
        # Act
        result = question_suggestion_service.generate_suggestions_from_context(context, max_suggestions)
        
        # Assert
        assert isinstance(result, list)
        assert len(result) <= max_suggestions
        assert all(isinstance(suggestion, str) for suggestion in result)

    @pytest.mark.unit
    def test_generate_suggestions_from_documents(self, question_suggestion_service: QuestionSuggestionService) -> None:
        """Unit: Test generate_suggestions_from_documents creates suggestions from document content."""
        # Arrange
        documents = [
            {"content": "Machine learning is a subset of AI.", "metadata": {"title": "AI Basics"}},
            {"content": "Deep learning uses neural networks.", "metadata": {"title": "Deep Learning"}}
        ]
        max_suggestions = 3
        
        # Act
        result = question_suggestion_service.generate_suggestions_from_documents(documents, max_suggestions)
        
        # Assert
        assert isinstance(result, list)
        assert len(result) <= max_suggestions
        assert all(isinstance(suggestion, str) for suggestion in result)

    @pytest.mark.unit
    def test_generate_follow_up_suggestions(self, question_suggestion_service: QuestionSuggestionService) -> None:
        """Unit: Test generate_follow_up_suggestions creates follow-up questions."""
        # Arrange
        current_message = "What is machine learning?"
        context = "Machine learning is a subset of artificial intelligence that focuses on algorithms."
        max_suggestions = 3
        
        # Act
        result = question_suggestion_service.generate_follow_up_suggestions(
            current_message, context, max_suggestions
        )
        
        # Assert
        assert isinstance(result, list)
        assert len(result) <= max_suggestions
        assert all(isinstance(suggestion, str) for suggestion in result)

    @pytest.mark.unit
    def test_cache_suggestions(self, question_suggestion_service: QuestionSuggestionService) -> None:
        """Unit: Test cache_suggestions stores suggestions in cache."""
        # Arrange
        cache_key = "test_key"
        suggestions = ["What is AI?", "How does ML work?", "What are neural networks?"]
        
        # Act
        result = question_suggestion_service.cache_suggestions(cache_key, suggestions)
        
        # Assert
        assert result is True

    @pytest.mark.unit
    def test_get_cached_suggestions(self, question_suggestion_service: QuestionSuggestionService) -> None:
        """Unit: Test get_cached_suggestions retrieves suggestions from cache."""
        # Arrange
        cache_key = "test_key"
        
        # Act
        result = question_suggestion_service.get_cached_suggestions(cache_key)
        
        # Assert
        assert result is None or isinstance(result, list)

    @pytest.mark.unit
    def test_clear_expired_cache(self, question_suggestion_service: QuestionSuggestionService) -> None:
        """Unit: Test clear_expired_cache removes expired cache entries."""
        # Act
        result = question_suggestion_service.clear_expired_cache()
        
        # Assert
        assert isinstance(result, int)  # Number of entries cleared

    @pytest.mark.unit
    def test_validate_suggestion_quality(self, question_suggestion_service: QuestionSuggestionService) -> None:
        """Unit: Test validate_suggestion_quality filters low-quality suggestions."""
        # Arrange
        suggestions = [
            "What is machine learning?",
            "Tell me more",
            "How does it work?",
            "What are the applications?"
        ]
        
        # Act
        result = question_suggestion_service.validate_suggestion_quality(suggestions)
        
        # Assert
        assert isinstance(result, list)
        assert len(result) <= len(suggestions)
        assert all(isinstance(suggestion, str) for suggestion in result)

    @pytest.mark.unit
    def test_rank_suggestions_by_relevance(self, question_suggestion_service: QuestionSuggestionService) -> None:
        """Unit: Test rank_suggestions_by_relevance orders suggestions by relevance."""
        # Arrange
        suggestions = ["What is AI?", "How does ML work?", "What are neural networks?"]
        context = "This document discusses artificial intelligence and machine learning algorithms."
        
        # Act
        result = question_suggestion_service.rank_suggestions_by_relevance(suggestions, context)
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == len(suggestions)
        assert all(isinstance(suggestion, str) for suggestion in result)
