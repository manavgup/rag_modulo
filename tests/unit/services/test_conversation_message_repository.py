"""Unit tests for ConversationMessageRepository."""

from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.custom_exceptions import DuplicateEntryError, NotFoundError
from backend.rag_solution.models.conversation_message import ConversationMessage
from backend.rag_solution.repository.conversation_message_repository import ConversationMessageRepository
from backend.rag_solution.schemas.conversation_schema import (
    ConversationMessageInput,
    ConversationMessageOutput,
    MessageMetadata,
)


@pytest.mark.unit
class TestConversationMessageRepository:
    """Unit tests for ConversationMessageRepository."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def repository(self, mock_db):
        """Create repository instance with mocked database."""
        return ConversationMessageRepository(mock_db)

    @pytest.fixture
    def sample_message_input(self):
        """Sample conversation message input."""
        return ConversationMessageInput(
            session_id=uuid4(),
            role="user",
            message_type="question",
            content="What is machine learning?",
            metadata=MessageMetadata(),
            token_count=15,
            execution_time=0.5,
        )

    @pytest.fixture
    def sample_message_model(self):
        """Sample conversation message model."""
        return ConversationMessage(
            id=uuid4(),
            session_id=uuid4(),
            role="assistant",
            message_type="answer",
            content="Machine learning is a subset of AI...",
            message_metadata={"confidence": 0.9},
            token_count=45,
            execution_time=2.1,
            created_at=datetime.utcnow(),
        )

    def test_create_message_success(self, repository, mock_db, sample_message_input):
        """Test successful message creation."""
        # Mock successful database operations
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        # Mock the model validation
        with patch("backend.rag_solution.repository.conversation_message_repository.ConversationMessageOutput") as mock_output:
            mock_output.from_db_message.return_value = Mock(spec=ConversationMessageOutput)

            # Act
            result = repository.create(sample_message_input)

            # Assert
            assert result is not None
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()
            mock_output.from_db_message.assert_called_once()

    def test_create_message_integrity_error(self, repository, mock_db, sample_message_input):
        """Test message creation with integrity error."""
        # Mock integrity error
        mock_db.add.side_effect = IntegrityError("statement", "params", "orig")
        mock_db.rollback.return_value = None

        # Act & Assert
        with pytest.raises(DuplicateEntryError):
            repository.create(sample_message_input)

        mock_db.rollback.assert_called_once()

    def test_create_message_general_error(self, repository, mock_db, sample_message_input):
        """Test message creation with general error."""
        # Mock general error
        mock_db.add.side_effect = Exception("Database error")
        mock_db.rollback.return_value = None

        # Act & Assert
        with pytest.raises(Exception, match="Failed to create conversation message"):
            repository.create(sample_message_input)

        mock_db.rollback.assert_called_once()

    def test_get_by_id_success(self, repository, mock_db, sample_message_model):
        """Test successful message retrieval by ID."""
        message_id = sample_message_model.id

        # Mock database query
        mock_query = Mock()
        mock_query.options.return_value.filter.return_value.first.return_value = sample_message_model
        mock_db.query.return_value = mock_query

        # Mock the model validation
        with patch("backend.rag_solution.repository.conversation_message_repository.ConversationMessageOutput") as mock_output:
            mock_output.from_db_message.return_value = Mock(spec=ConversationMessageOutput)

            # Act
            result = repository.get_by_id(message_id)

            # Assert
            assert result is not None
            mock_db.query.assert_called_once_with(ConversationMessage)
            mock_output.from_db_message.assert_called_once_with(sample_message_model)

    def test_get_by_id_not_found(self, repository, mock_db):
        """Test message retrieval when not found."""
        message_id = uuid4()

        # Mock database query returning None
        mock_query = Mock()
        mock_query.options.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.get_by_id(message_id)

    def test_get_messages_by_session(self, repository, mock_db, sample_message_model):
        """Test retrieving messages by session ID."""
        session_id = uuid4()
        messages = [sample_message_model]

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = (
            messages
        )
        mock_db.query.return_value = mock_query

        # Mock the model validation
        with patch("backend.rag_solution.repository.conversation_message_repository.ConversationMessageOutput") as mock_output:
            mock_output.from_db_message.side_effect = [Mock(spec=ConversationMessageOutput)]

            # Act
            result = repository.get_messages_by_session(session_id, limit=100, offset=0)

            # Assert
            assert len(result) == 1
            mock_db.query.assert_called_once_with(ConversationMessage)

    def test_get_recent_messages(self, repository, mock_db, sample_message_model):
        """Test retrieving recent messages for a session."""
        session_id = uuid4()
        messages = [sample_message_model]

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = messages
        mock_db.query.return_value = mock_query

        # Mock the model validation
        with patch("backend.rag_solution.repository.conversation_message_repository.ConversationMessageOutput") as mock_output:
            mock_output.from_db_message.side_effect = [Mock(spec=ConversationMessageOutput)]

            # Act
            result = repository.get_recent_messages(session_id, count=10)

            # Assert
            assert len(result) == 1
            mock_db.query.assert_called_once_with(ConversationMessage)

    def test_update_message_success(self, repository, mock_db, sample_message_model):
        """Test successful message update."""
        message_id = sample_message_model.id
        updates = {"content": "Updated content", "token_count": 20}

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_message_model
        mock_db.query.return_value = mock_query
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        # Mock the model validation
        with patch("backend.rag_solution.repository.conversation_message_repository.ConversationMessageOutput") as mock_output:
            mock_output.from_db_message.return_value = Mock(spec=ConversationMessageOutput)

            # Act
            result = repository.update(message_id, updates)

            # Assert
            assert result is not None
            assert sample_message_model.content == "Updated content"
            assert sample_message_model.token_count == 20
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

    def test_update_message_not_found(self, repository, mock_db):
        """Test updating non-existent message."""
        message_id = uuid4()
        updates = {"content": "Updated content"}

        # Mock database query returning None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.update(message_id, updates)

    def test_delete_message_success(self, repository, mock_db, sample_message_model):
        """Test successful message deletion."""
        message_id = sample_message_model.id

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_message_model
        mock_db.query.return_value = mock_query
        mock_db.delete.return_value = None
        mock_db.commit.return_value = None

        # Act
        result = repository.delete(message_id)

        # Assert
        assert result is True
        mock_db.delete.assert_called_once_with(sample_message_model)
        mock_db.commit.assert_called_once()

    def test_delete_message_not_found(self, repository, mock_db):
        """Test deleting non-existent message."""
        message_id = uuid4()

        # Mock database query returning None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.delete(message_id)

    def test_delete_messages_by_session(self, repository, mock_db):
        """Test deleting all messages for a session."""
        session_id = uuid4()
        deleted_count = 3

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.delete.return_value = deleted_count
        mock_db.query.return_value = mock_query
        mock_db.commit.return_value = None

        # Act
        result = repository.delete_messages_by_session(session_id)

        # Assert
        assert result == deleted_count
        mock_db.query.assert_called_once_with(ConversationMessage)
        mock_db.commit.assert_called_once()

    @patch("sqlalchemy.func")
    def test_get_token_usage_by_session(self, _mock_func, repository, mock_db):
        """Test retrieving token usage for a session."""
        session_id = uuid4()
        total_tokens = 150

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.scalar.return_value = total_tokens
        mock_db.query.return_value = mock_query

        # Act
        result = repository.get_token_usage_by_session(session_id)

        # Assert
        assert result == total_tokens
        mock_db.query.assert_called_once()

    @patch("sqlalchemy.func")
    def test_get_token_usage_by_session_none_result(self, _mock_func, repository, mock_db):
        """Test retrieving token usage when no messages exist."""
        session_id = uuid4()

        # Mock database query returning None
        mock_query = Mock()
        mock_query.filter.return_value.scalar.return_value = None
        mock_db.query.return_value = mock_query

        # Act
        result = repository.get_token_usage_by_session(session_id)

        # Assert
        assert result == 0
        mock_db.query.assert_called_once()
