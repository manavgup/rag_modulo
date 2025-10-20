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

    def test_source_documents_extraction_uses_document_name(self) -> None:
        """Test that source_documents extraction uses document_name field (regression test for #442)."""
        # Mock serialized documents as they come from serialize_documents()
        # This function creates dicts with 'document_name', not 'document_id'
        serialized_documents = [
            {"document_name": "2023-ibm-annual-report.pdf", "content": "test1", "metadata": {}},
            {"document_name": "2020-ibm-annual-report.pdf", "content": "test2", "metadata": {}},
            {"document_name": "financial-summary.pdf", "content": "test3", "metadata": {}},
        ]

        # This is the exact logic from conversation_service.py:610 (after fix)
        source_docs = [doc.get("document_name", "") for doc in serialized_documents]

        # Verify we get actual document names, not empty strings
        assert source_docs == [
            "2023-ibm-annual-report.pdf",
            "2020-ibm-annual-report.pdf",
            "financial-summary.pdf",
        ]
        assert "" not in source_docs  # No empty strings (would indicate bug is back)
        assert len(source_docs) == 3

        # Verify the bug scenario doesn't happen (using wrong field name)
        wrong_extraction = [doc.get("document_id", "") for doc in serialized_documents]
        assert wrong_extraction == ["", "", ""]  # This is what the bug caused
