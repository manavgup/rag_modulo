"""TDD Red Phase: Integration tests for conversation functionality.

Integration tests focus on testing multiple components working together,
with real database interactions and service dependencies.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from uuid import uuid4
from pydantic import UUID4

from rag_solution.services.conversation_service import ConversationService
from rag_solution.services.context_manager_service import ContextManagerService
from rag_solution.services.question_suggestion_service import QuestionSuggestionService
from rag_solution.services.search_service import SearchService
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
from rag_solution.schemas.search_schema import SearchInput, SearchOutput
from rag_solution.core.exceptions import NotFoundError, ValidationError, SessionExpiredError


class TestConversationIntegrationTDD:
    """Integration tests for conversation functionality."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session with realistic behavior."""
        db = Mock()
        db.commit = Mock()
        db.rollback = Mock()
        db.refresh = Mock()
        return db

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Mock settings with realistic values."""
        settings = Mock()
        settings.session_timeout_minutes = 30
        settings.max_context_window_size = 8000
        settings.max_messages_per_session = 100
        settings.suggestion_cache_ttl = 3600
        settings.max_suggestions = 5
        return settings

    @pytest.fixture
    def conversation_service(self, mock_db: Mock, mock_settings: Mock) -> ConversationService:
        """Create conversation service with dependencies."""
        return ConversationService(mock_db, mock_settings)

    @pytest.fixture
    def context_manager_service(self, mock_db: Mock, mock_settings: Mock) -> ContextManagerService:
        """Create context manager service with dependencies."""
        return ContextManagerService(mock_db, mock_settings)

    @pytest.fixture
    def question_suggestion_service(self, mock_db: Mock, mock_settings: Mock) -> QuestionSuggestionService:
        """Create question suggestion service with dependencies."""
        return QuestionSuggestionService(mock_db, mock_settings)

    @pytest.fixture
    def search_service(self, mock_db: Mock, mock_settings: Mock) -> SearchService:
        """Create search service with dependencies."""
        return SearchService(mock_db, mock_settings)

    # ==================== INTEGRATION TESTS ====================

    @pytest.mark.integration
    def test_conversation_flow_with_context_management(self, 
                                                     conversation_service: ConversationService,
                                                     context_manager_service: ContextManagerService) -> None:
        """Integration: Test complete conversation flow with context management."""
        # Arrange
        user_id = uuid4()
        collection_id = uuid4()
        
        # Create session
        session_input = ConversationSessionInput(
            user_id=user_id,
            collection_id=collection_id,
            session_name="Test Conversation"
        )
        session = conversation_service.create_session(session_input)
        
        # Add first message
        message1 = ConversationMessageInput(
            session_id=session.id,
            content="What is machine learning?",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION
        )
        response1 = conversation_service.add_message(message1)
        
        # Add follow-up message
        message2 = ConversationMessageInput(
            session_id=session.id,
            content="Tell me more about it",
            role=MessageRole.USER,
            message_type=MessageType.FOLLOW_UP
        )
        response2 = conversation_service.add_message(message2)
        
        # Get context
        context = context_manager_service.build_context_from_messages(
            session.id, [response1, response2]
        )
        
        # Assert
        assert session.status == SessionStatus.ACTIVE
        assert response1.content == "What is machine learning?"
        assert response2.content == "Tell me more about it"
        assert context.session_id == session.id
        assert "machine learning" in context.context_window

    @pytest.mark.integration
    def test_conversation_with_search_integration(self,
                                                conversation_service: ConversationService,
                                                search_service: SearchService) -> None:
        """Integration: Test conversation with search service integration."""
        # Arrange
        user_id = uuid4()
        collection_id = uuid4()
        
        # Create session
        session_input = ConversationSessionInput(
            user_id=user_id,
            collection_id=collection_id,
            session_name="Search Integration Test"
        )
        session = conversation_service.create_session(session_input)
        
        # Add question message
        message = ConversationMessageInput(
            session_id=session.id,
            content="What documents do we have about AI?",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION
        )
        conversation_message = conversation_service.add_message(message)
        
        # Perform search
        search_input = SearchInput(
            question="What documents do we have about AI?",
            collection_id=collection_id,
            user_id=user_id
        )
        search_result = search_service.search(search_input)
        
        # Add search result as assistant message
        assistant_message = ConversationMessageInput(
            session_id=session.id,
            content=search_result.answer,
            role=MessageRole.ASSISTANT,
            message_type=MessageType.ANSWER,
            metadata={"search_results": search_result.sources}
        )
        assistant_response = conversation_service.add_message(assistant_message)
        
        # Assert
        assert conversation_message.role == MessageRole.USER
        assert assistant_response.role == MessageRole.ASSISTANT
        assert assistant_response.metadata["search_results"] == search_result.sources

    @pytest.mark.integration
    def test_conversation_session_lifecycle(self, conversation_service: ConversationService) -> None:
        """Integration: Test complete session lifecycle from creation to deletion."""
        # Arrange
        user_id = uuid4()
        collection_id = uuid4()
        
        # Create session
        session_input = ConversationSessionInput(
            user_id=user_id,
            collection_id=collection_id,
            session_name="Lifecycle Test"
        )
        session = conversation_service.create_session(session_input)
        assert session.status == SessionStatus.ACTIVE
        
        # Add messages
        for i in range(3):
            message = ConversationMessageInput(
                session_id=session.id,
                content=f"Test message {i}",
                role=MessageRole.USER,
                message_type=MessageType.QUESTION
            )
            conversation_service.add_message(message)
        
        # Get session statistics
        stats = conversation_service.get_session_statistics(session.id, user_id)
        assert stats["message_count"] == 3
        
        # Archive session
        archived_session = conversation_service.archive_session(session.id, user_id)
        assert archived_session.status == SessionStatus.ARCHIVED
        
        # Restore session
        restored_session = conversation_service.restore_session(session.id, user_id)
        assert restored_session.status == SessionStatus.ACTIVE
        
        # Delete session
        deleted = conversation_service.delete_session(session.id, user_id)
        assert deleted is True
