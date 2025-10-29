"""Simple unit tests for ConversationService to verify basic functionality."""

# pylint: disable=import-error
# Justification: import-error is false positive when pylint runs standalone

from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from core.config import Settings, get_settings
from rag_solution.core.exceptions import ValidationError
from rag_solution.schemas.conversation_schema import (
    ConversationSessionInput,
)
from rag_solution.services.conversation_service import ConversationService


class TestConversationServiceSimple:
    """Simple unit tests for ConversationService."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Create mock settings."""
        return get_settings()

    @pytest.fixture
    def service(self, mock_db: Mock, mock_settings: Settings) -> ConversationService:
        """Create ConversationService instance."""
        return ConversationService(mock_db, mock_settings)

    def test_service_initialization(self, service: ConversationService) -> None:
        """Test service initializes correctly."""
        assert service is not None
        assert service.db is not None
        assert service.settings is not None

    def test_create_session_validates_empty_name(self) -> None:
        """Test create_session validates empty session name at Pydantic level."""
        with pytest.raises(PydanticValidationError):  # Pydantic validation will raise
            ConversationSessionInput(
                user_id=uuid4(),
                collection_id=uuid4(),
                session_name="",  # Empty name should raise ValidationError
            )

    @pytest.mark.asyncio
    async def test_export_session_validates_format(self, service: ConversationService) -> None:
        """Test export_session validates export format."""
        session_id = uuid4()
        user_id = uuid4()

        with pytest.raises(ValidationError, match="Unsupported export format"):
            await service.export_session(session_id, user_id, "unsupported_format")

    def test_cleanup_expired_sessions_returns_int(self, service: ConversationService) -> None:
        """Test cleanup_expired_sessions returns integer."""
        # Mock the database query to return empty list
        mock_query = service.db.query.return_value  # type: ignore
        mock_query.filter.return_value.all.return_value = []  # type: ignore

        result = service.cleanup_expired_sessions()
        assert isinstance(result, int)
        assert result >= 0

    def test_service_has_required_methods(self, service: ConversationService) -> None:
        """Test service has all required methods."""
        required_methods = [
            "create_session",
            "get_session",
            "update_session",
            "delete_session",
            "add_message",
            "archive_session",
            "restore_session",
            "cleanup_expired_sessions",
            "search_sessions",
            "get_user_sessions",
            "export_session",
        ]

        for method_name in required_methods:
            assert hasattr(service, method_name), f"Service missing method: {method_name}"
            assert callable(getattr(service, method_name)), f"Method {method_name} is not callable"

    def test_extract_user_messages_filters_assistant_responses(self, service):
        """Test that _extract_user_messages_from_context filters out assistant messages."""
        # Test with mixed user and assistant messages
        context = "User: What is IBM? Assistant: Based on the analysis, IBM is... User: What about revenue?"
        result = service._extract_user_messages_from_context(context)

        # Should only contain user messages
        assert "What is IBM?" in result
        assert "What about revenue?" in result
        assert "Based on the analysis" not in result
        assert "Assistant" not in result

    def test_extract_user_messages_handles_empty_context(self, service):
        """Test that empty or invalid context returns empty string."""
        assert service._extract_user_messages_from_context("") == ""
        assert service._extract_user_messages_from_context("No previous conversation context") == ""

    def test_extract_user_messages_handles_user_only_context(self, service):
        """Test that context with only user messages works correctly."""
        context = "User: What is machine learning? User: How does it work?"
        result = service._extract_user_messages_from_context(context)

        assert "What is machine learning?" in result
        assert "How does it work?" in result

    def test_extract_user_messages_prevents_discourse_marker_pollution(self, service):
        """Test that discourse markers from assistant responses are filtered out."""
        # This is the key test - discourse markers should NOT appear
        context = "User: Tell me about IBM Assistant: However, Based on the analysis, Additionally, Since the context suggests..."
        result = service._extract_user_messages_from_context(context)

        # User message should be present
        assert "Tell me about IBM" in result

        # Discourse markers should be filtered out
        assert "However" not in result
        assert "Based on" not in result
        assert "Additionally" not in result
        assert "Since" not in result
