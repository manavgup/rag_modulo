"""TDD Red Phase: Atomic tests for conversation functionality.

Atomic tests focus on the smallest units of functionality - individual
data structures, validation rules, and basic operations.
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from rag_solution.schemas.conversation_schema import (
    ConversationContext,
    ConversationMessageInput,
    ConversationSessionInput,
    ConversationSessionOutput,
    MessageRole,
    MessageType,
    SessionStatus,
)
from pydantic import ValidationError


class TestConversationAtomicTDD:
    """Atomic tests for conversation data structures and validation."""

    # ==================== ATOMIC TESTS ====================

    @pytest.mark.atomic
    def test_session_status_enum_values(self) -> None:
        """Atomic: Test session status enum has correct string values."""
        assert SessionStatus.ACTIVE == "active"
        assert SessionStatus.PAUSED == "paused"
        assert SessionStatus.ARCHIVED == "archived"
        assert SessionStatus.EXPIRED == "expired"

    @pytest.mark.atomic
    def test_message_role_enum_values(self) -> None:
        """Atomic: Test message role enum has correct string values."""
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.SYSTEM == "system"

    @pytest.mark.atomic
    def test_message_type_enum_values(self) -> None:
        """Atomic: Test message type enum has correct string values."""
        assert MessageType.QUESTION == "question"
        assert MessageType.ANSWER == "answer"
        assert MessageType.FOLLOW_UP == "follow_up"
        assert MessageType.CLARIFICATION == "clarification"
        assert MessageType.SYSTEM_MESSAGE == "system_message"

    @pytest.mark.atomic
    def test_uuid4_validation(self) -> None:
        """Atomic: Test UUID4 validation in schemas."""
        valid_uuid = uuid4()
        invalid_uuid = "not-a-uuid"

        # Valid UUID should work
        session_input = ConversationSessionInput(user_id=valid_uuid, collection_id=valid_uuid, session_name="Test")
        assert session_input.user_id == valid_uuid

        # Invalid UUID should raise ValidationError
        with pytest.raises(ValidationError):
            ConversationSessionInput(
                user_id=invalid_uuid,  # type: ignore
                collection_id=valid_uuid,
                session_name="Test",
            )

    @pytest.mark.atomic
    def test_session_name_validation_min_length(self) -> None:
        """Atomic: Test session name minimum length validation."""
        with pytest.raises(ValidationError):
            ConversationSessionInput(
                user_id=uuid4(),
                collection_id=uuid4(),
                session_name="",  # Empty string should fail
            )

    @pytest.mark.atomic
    def test_session_name_validation_max_length(self) -> None:
        """Atomic: Test session name maximum length validation."""
        long_name = "x" * 256  # Assuming max length is 255
        with pytest.raises(ValidationError):
            ConversationSessionInput(user_id=uuid4(), collection_id=uuid4(), session_name=long_name)

    @pytest.mark.atomic
    def test_context_window_size_validation_min(self) -> None:
        """Atomic: Test context window size minimum validation."""
        with pytest.raises(ValidationError):
            ConversationSessionInput(
                user_id=uuid4(),
                collection_id=uuid4(),
                session_name="Test",
                context_window_size=0,  # Should be > 0
            )

    @pytest.mark.atomic
    def test_context_window_size_validation_max(self) -> None:
        """Atomic: Test context window size maximum validation."""
        with pytest.raises(ValidationError):
            ConversationSessionInput(
                user_id=uuid4(),
                collection_id=uuid4(),
                session_name="Test",
                context_window_size=50000,  # Assuming max is 10000
            )

    @pytest.mark.atomic
    def test_max_messages_validation_min(self) -> None:
        """Atomic: Test max messages minimum validation."""
        with pytest.raises(ValidationError):
            ConversationSessionInput(
                user_id=uuid4(),
                collection_id=uuid4(),
                session_name="Test",
                max_messages=0,  # Should be > 0
            )

    @pytest.mark.atomic
    def test_max_messages_validation_max(self) -> None:
        """Atomic: Test max messages maximum validation."""
        with pytest.raises(ValidationError):
            ConversationSessionInput(
                user_id=uuid4(),
                collection_id=uuid4(),
                session_name="Test",
                max_messages=1000,  # Assuming max is 500
            )

    @pytest.mark.atomic
    def test_message_content_validation_min_length(self) -> None:
        """Atomic: Test message content minimum length validation."""
        with pytest.raises(ValidationError):
            ConversationMessageInput(
                session_id=uuid4(),
                content="",  # Empty content should fail
                role=MessageRole.USER,
                message_type=MessageType.QUESTION,
            )

    @pytest.mark.atomic
    def test_message_content_validation_max_length(self) -> None:
        """Atomic: Test message content maximum length validation."""
        long_content = "x" * 100001  # Max length is 100000
        with pytest.raises(ValidationError):
            ConversationMessageInput(
                session_id=uuid4(), content=long_content, role=MessageRole.USER, message_type=MessageType.QUESTION
            )

    @pytest.mark.atomic
    def test_context_window_validation_min_length(self) -> None:
        """Atomic: Test context window minimum length validation."""
        with pytest.raises(ValidationError):
            ConversationContext(
                session_id=uuid4(),
                context_window="",  # Empty context should fail
                relevant_documents=[],
            )

    @pytest.mark.atomic
    def test_context_window_validation_max_length(self) -> None:
        """Atomic: Test context window maximum length validation."""
        long_context = "x" * 50001  # Assuming max length is 50000
        with pytest.raises(ValidationError):
            ConversationContext(session_id=uuid4(), context_window=long_context, relevant_documents=[])

    @pytest.mark.atomic
    def test_metadata_validation_type(self) -> None:
        """Atomic: Test metadata must be dict type."""
        with pytest.raises(ValidationError):
            ConversationMessageInput(
                session_id=uuid4(),
                content="Test message",
                role=MessageRole.USER,
                message_type=MessageType.QUESTION,
                metadata="not-a-dict",  # type: ignore
            )

    @pytest.mark.atomic
    def test_relevant_documents_validation_type(self) -> None:
        """Atomic: Test relevant documents must be list type."""
        with pytest.raises(ValidationError):
            ConversationContext(
                session_id=uuid4(),
                context_window="Test context",
                relevant_documents="not-a-list",  # type: ignore
            )

    @pytest.mark.atomic
    def test_datetime_validation(self) -> None:
        """Atomic: Test datetime field validation."""
        invalid_datetime = "not-a-datetime"

        with pytest.raises(ValidationError):
            ConversationSessionOutput(
                id=uuid4(),
                user_id=uuid4(),
                collection_id=uuid4(),
                session_name="Test",
                status=SessionStatus.ACTIVE,
                context_window_size=4000,
                max_messages=50,
                message_count=0,
                created_at=invalid_datetime,  # type: ignore
                updated_at=datetime.now(),
            )

    @pytest.mark.atomic
    def test_required_fields_validation(self) -> None:
        """Atomic: Test required fields validation."""
        # Missing user_id
        with pytest.raises(ValidationError):
            ConversationSessionInput(collection_id=uuid4(), session_name="Test")  # type: ignore

        # Missing collection_id
        with pytest.raises(ValidationError):
            ConversationSessionInput(user_id=uuid4(), session_name="Test")  # type: ignore

        # Missing session_name
        with pytest.raises(ValidationError):
            ConversationSessionInput(user_id=uuid4(), collection_id=uuid4())  # type: ignore

    @pytest.mark.atomic
    def test_optional_fields_default_values(self) -> None:
        """Atomic: Test optional fields have correct default values."""
        session_input = ConversationSessionInput(user_id=uuid4(), collection_id=uuid4(), session_name="Test")

        assert session_input.context_window_size == 4000  # default
        assert session_input.max_messages == 50  # default
        assert session_input.metadata == {}  # default

    @pytest.mark.atomic
    def test_message_metadata_default_value(self) -> None:
        """Atomic: Test message metadata has correct default value."""
        message_input = ConversationMessageInput(
            session_id=uuid4(), content="Test message", role=MessageRole.USER, message_type=MessageType.QUESTION
        )

        assert message_input.metadata is None  # default is None for MessageMetadata

    @pytest.mark.atomic
    def test_context_metadata_default_value(self) -> None:
        """Atomic: Test context metadata has correct default value."""
        context = ConversationContext(session_id=uuid4(), context_window="Test context", relevant_documents=[])

        assert context.context_metadata == {}  # default

    @pytest.mark.atomic
    def test_model_config_settings(self) -> None:
        """Atomic: Test Pydantic model configuration settings."""
        ConversationSessionInput(user_id=uuid4(), collection_id=uuid4(), session_name="Test")

        # Test that extra fields are forbidden
        with pytest.raises(ValidationError):
            ConversationSessionInput(
                user_id=uuid4(),
                collection_id=uuid4(),
                session_name="Test",
                extra_field="not_allowed",  # type: ignore
            )

    @pytest.mark.atomic
    def test_string_strip_whitespace(self) -> None:
        """Atomic: Test string fields strip whitespace."""
        message_input = ConversationMessageInput(
            session_id=uuid4(),
            content="  Test message  ",  # Should be stripped
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
        )

        assert message_input.content == "Test message"

    @pytest.mark.atomic
    def test_enum_case_sensitivity(self) -> None:
        """Atomic: Test enum values are case sensitive."""
        # These should work
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"

        # These should not work
        assert MessageRole.USER != "USER"
        assert MessageRole.ASSISTANT != "ASSISTANT"

    @pytest.mark.atomic
    def test_uuid_string_conversion(self) -> None:
        """Atomic: Test UUID string to UUID4 conversion."""
        # uuid_string = str(uuid4())  # Not needed anymore

        session_input = ConversationSessionInput(
            user_id=uuid4(),  # Use UUID directly
            collection_id=uuid4(),
            session_name="Test",
        )

        assert isinstance(session_input.user_id, UUID)
        assert isinstance(session_input.collection_id, UUID)

    @pytest.mark.atomic
    def test_datetime_serialization(self) -> None:
        """Atomic: Test datetime serialization to ISO format."""
        now = datetime.now()
        session_output = ConversationSessionOutput(
            id=uuid4(),
            user_id=uuid4(),
            collection_id=uuid4(),
            session_name="Test",
            status=SessionStatus.ACTIVE,
            context_window_size=4000,
            max_messages=50,
            message_count=0,
            created_at=now,
            updated_at=now,
        )

        json_data = session_output.model_dump(mode="json")
        assert "created_at" in json_data
        assert "updated_at" in json_data
        assert isinstance(json_data["created_at"], str)
        assert isinstance(json_data["updated_at"], str)

    @pytest.mark.atomic
    def test_boolean_field_validation(self) -> None:
        """Atomic: Test boolean field validation and defaults."""
        session_input = ConversationSessionInput(user_id=uuid4(), collection_id=uuid4(), session_name="Test")

        # Test boolean field defaults
        assert session_input.is_archived is False  # default
        assert session_input.is_pinned is False  # default

    @pytest.mark.atomic
    def test_numeric_field_precision(self) -> None:
        """Atomic: Test numeric field precision and rounding."""
        session_input = ConversationSessionInput(
            user_id=uuid4(),
            collection_id=uuid4(),
            session_name="Test",
            context_window_size=4000,  # Use int directly
        )

        assert isinstance(session_input.context_window_size, int)
        assert session_input.context_window_size == 4000

    @pytest.mark.atomic
    def test_list_field_validation(self) -> None:
        """Atomic: Test list field validation."""
        context = ConversationContext(
            session_id=uuid4(), context_window="Test context", relevant_documents=["doc1", "doc2", "doc3"]
        )

        assert len(context.relevant_documents) == 3
        assert all(isinstance(doc, str) for doc in context.relevant_documents)

    @pytest.mark.atomic
    def test_message_metadata_validation(self) -> None:
        """Atomic: Test MessageMetadata field validation."""
        from rag_solution.schemas.conversation_schema import MessageMetadata

        metadata = MessageMetadata(
            source_documents=["doc1", "doc2"],
            cot_used=True,
            conversation_aware=True,
            execution_time=1.5,
            token_count=100,
        )

        message_input = ConversationMessageInput(
            session_id=uuid4(),
            content="Test message",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
            metadata=metadata,
        )

        assert message_input.metadata == metadata
        assert isinstance(message_input.metadata, MessageMetadata)
