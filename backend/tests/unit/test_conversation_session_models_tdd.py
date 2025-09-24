"""TDD Red Phase: Test cases for conversation session models and schemas.

These tests define the expected behavior for conversation session management
without any implementation. All tests should fail initially.
"""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from rag_solution.schemas.conversation_schema import (
    ConversationContext,
    ConversationMessageInput,
    ConversationMessageOutput,
    ConversationSessionInput,
    ConversationSessionOutput,
    MessageMetadata,
    MessageRole,
    MessageType,
    SessionStatus,
)


class TestConversationSessionModelsTDD:
    """Test cases for conversation session models and schemas."""

    def test_conversation_session_input_creation(self) -> None:
        """Test creating a conversation session input with valid data."""
        # Arrange
        user_id = uuid4()
        collection_id = uuid4()
        session_name = "Test Chat Session"

        # Act
        session_input = ConversationSessionInput(
            user_id=user_id, collection_id=collection_id, session_name=session_name
        )

        # Assert
        assert session_input.user_id == user_id
        assert session_input.collection_id == collection_id
        assert session_input.session_name == session_name
        assert session_input.context_window_size == 4000  # default
        assert session_input.max_messages == 50  # default

    def test_conversation_session_input_with_custom_settings(self) -> None:
        """Test creating a conversation session input with custom settings."""
        # Arrange
        user_id = uuid4()
        collection_id = uuid4()
        session_name = "Custom Chat Session"
        context_window_size = 8000
        max_messages = 100

        # Act
        session_input = ConversationSessionInput(
            user_id=user_id,
            collection_id=collection_id,
            session_name=session_name,
            context_window_size=context_window_size,
            max_messages=max_messages,
        )

        # Assert
        assert session_input.context_window_size == context_window_size
        assert session_input.max_messages == max_messages

    def test_conversation_session_input_validation_errors(self) -> None:
        """Test validation errors for conversation session input."""
        # Test empty session name
        with pytest.raises(ValidationError):
            ConversationSessionInput(user_id=uuid4(), collection_id=uuid4(), session_name="")

        # Test invalid context window size
        with pytest.raises(ValidationError):
            ConversationSessionInput(user_id=uuid4(), collection_id=uuid4(), session_name="Test", context_window_size=0)

        # Test invalid max messages
        with pytest.raises(ValidationError):
            ConversationSessionInput(user_id=uuid4(), collection_id=uuid4(), session_name="Test", max_messages=0)

    def test_conversation_session_output_creation(self) -> None:
        """Test creating a conversation session output with valid data."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()
        collection_id = uuid4()
        session_name = "Test Chat Session"
        created_at = datetime.now()
        updated_at = datetime.now()

        # Act
        session_output = ConversationSessionOutput(
            id=session_id,
            user_id=user_id,
            collection_id=collection_id,
            session_name=session_name,
            status=SessionStatus.ACTIVE,
            context_window_size=4000,
            max_messages=50,
            message_count=0,
            created_at=created_at,
            updated_at=updated_at,
        )

        # Assert
        assert session_output.id == session_id
        assert session_output.user_id == user_id
        assert session_output.collection_id == collection_id
        assert session_output.session_name == session_name
        assert session_output.status == SessionStatus.ACTIVE
        assert session_output.message_count == 0

    def test_conversation_message_input_creation(self) -> None:
        """Test creating a conversation message input with valid data."""
        # Arrange
        session_id = uuid4()
        content = "What is the main topic of this document?"
        role = MessageRole.USER
        message_type = MessageType.QUESTION

        # Act
        message_input = ConversationMessageInput(
            session_id=session_id, content=content, role=role, message_type=message_type
        )

        # Assert
        assert message_input.session_id == session_id
        assert message_input.content == content
        assert message_input.role == role
        assert message_input.message_type == message_type
        assert message_input.metadata is None  # default is None for MessageMetadata

    def test_conversation_message_input_with_metadata(self) -> None:
        """Test creating a conversation message input with metadata."""
        from rag_solution.schemas.conversation_schema import MessageMetadata

        # Arrange
        session_id = uuid4()
        content = "Tell me more about this topic"
        role = MessageRole.USER
        message_type = MessageType.FOLLOW_UP
        metadata = MessageMetadata(
            source_documents=["doc1", "doc2"],
            cot_used=True,
            conversation_aware=True,
            confidence_score=0.85,
        )

        # Act
        message_input = ConversationMessageInput(
            session_id=session_id, content=content, role=role, message_type=message_type, metadata=metadata
        )

        # Assert
        assert message_input.metadata == metadata
        assert isinstance(message_input.metadata, MessageMetadata)

    def test_conversation_message_output_creation(self) -> None:
        """Test creating a conversation message output with valid data."""
        # Arrange
        message_id = uuid4()
        session_id = uuid4()
        content = "Based on the document, the main topic is..."
        role = MessageRole.ASSISTANT
        message_type = MessageType.ANSWER
        created_at = datetime.now()

        # Act
        message_output = ConversationMessageOutput(
            id=message_id,
            session_id=session_id,
            content=content,
            role=role,
            message_type=message_type,
            metadata=MessageMetadata(),
            created_at=created_at,
        )

        # Assert
        assert message_output.id == message_id
        assert message_output.session_id == session_id
        assert message_output.content == content
        assert message_output.role == role
        assert message_output.message_type == message_type

    def test_conversation_context_creation(self) -> None:
        """Test creating a conversation context with valid data."""
        # Arrange
        session_id = uuid4()
        context_window = "Previous conversation about machine learning..."
        relevant_documents = ["doc1", "doc2", "doc3"]
        context_metadata = {"topic": "machine_learning", "confidence": 0.9, "last_updated": datetime.now().isoformat()}

        # Act
        context = ConversationContext(
            session_id=session_id,
            context_window=context_window,
            relevant_documents=relevant_documents,
            context_metadata=context_metadata,
        )

        # Assert
        assert context.session_id == session_id
        assert context.context_window == context_window
        assert context.relevant_documents == relevant_documents
        assert context.context_metadata == context_metadata

    def test_session_status_enum_values(self) -> None:
        """Test that session status enum has correct values."""
        # Assert
        assert SessionStatus.ACTIVE == "active"
        assert SessionStatus.PAUSED == "paused"
        assert SessionStatus.ARCHIVED == "archived"
        assert SessionStatus.EXPIRED == "expired"

    def test_message_role_enum_values(self) -> None:
        """Test that message role enum has correct values."""
        # Assert
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.SYSTEM == "system"

    def test_message_type_enum_values(self) -> None:
        """Test that message type enum has correct values."""
        # Assert
        assert MessageType.QUESTION == "question"
        assert MessageType.ANSWER == "answer"
        assert MessageType.FOLLOW_UP == "follow_up"
        assert MessageType.CLARIFICATION == "clarification"
        assert MessageType.SYSTEM_MESSAGE == "system_message"

    def test_conversation_session_input_to_output_conversion(self) -> None:
        """Test converting conversation session input to output format."""
        # Arrange
        user_id = uuid4()
        collection_id = uuid4()
        session_name = "Test Session"
        session_input = ConversationSessionInput(
            user_id=user_id, collection_id=collection_id, session_name=session_name
        )

        # Act
        session_output = session_input.to_output(
            session_id=uuid4(),
            status=SessionStatus.ACTIVE,
            message_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Assert
        assert isinstance(session_output, ConversationSessionOutput)
        assert session_output.user_id == user_id
        assert session_output.collection_id == collection_id
        assert session_output.session_name == session_name

    def test_conversation_message_input_to_output_conversion(self) -> None:
        """Test converting conversation message input to output format."""
        # Arrange
        session_id = uuid4()
        content = "Test message"
        role = MessageRole.USER
        message_type = MessageType.QUESTION
        message_input = ConversationMessageInput(
            session_id=session_id, content=content, role=role, message_type=message_type
        )

        # Act
        message_output = message_input.to_output(message_id=uuid4(), created_at=datetime.now())

        # Assert
        assert isinstance(message_output, ConversationMessageOutput)
        assert message_output.session_id == session_id
        assert message_output.content == content
        assert message_output.role == role
        assert message_output.message_type == message_type

    def test_conversation_context_validation(self) -> None:
        """Test validation of conversation context."""
        # Test empty context window
        with pytest.raises(ValidationError):
            ConversationContext(session_id=uuid4(), context_window="", relevant_documents=[])

        # Test context window too long
        with pytest.raises(ValidationError):
            ConversationContext(
                session_id=uuid4(),
                context_window="x" * 50001,  # Too long (50001 > 50000)
                relevant_documents=[],
            )

    def test_conversation_session_serialization(self) -> None:
        """Test that conversation session can be serialized to JSON."""
        # Arrange
        session_output = ConversationSessionOutput(
            id=uuid4(),
            user_id=uuid4(),
            collection_id=uuid4(),
            session_name="Test Session",
            status=SessionStatus.ACTIVE,
            context_window_size=4000,
            max_messages=50,
            message_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Act
        json_data = session_output.model_dump()

        # Assert
        assert isinstance(json_data, dict)
        assert "id" in json_data
        assert "user_id" in json_data
        assert "session_name" in json_data
        assert "status" in json_data

    def test_conversation_message_serialization(self) -> None:
        """Test that conversation message can be serialized to JSON."""
        # Arrange
        message_output = ConversationMessageOutput(
            id=uuid4(),
            session_id=uuid4(),
            content="Test message",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
            metadata=MessageMetadata(),
            created_at=datetime.now(),
        )

        # Act
        json_data = message_output.model_dump()

        # Assert
        assert isinstance(json_data, dict)
        assert "id" in json_data
        assert "session_id" in json_data
        assert "content" in json_data
        assert "role" in json_data
        assert "message_type" in json_data
