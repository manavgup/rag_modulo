"""Unit tests for ConversationSessionRepository."""

from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from rag_solution.core.exceptions import AlreadyExistsError, NotFoundError
from rag_solution.models.conversation_session import ConversationSession
from rag_solution.repository.conversation_session_repository import ConversationSessionRepository
from rag_solution.schemas.conversation_schema import ConversationSessionInput, ConversationSessionOutput
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


@pytest.mark.unit
class TestConversationSessionRepository:
    """Unit tests for ConversationSessionRepository."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def repository(self, mock_db):
        """Create repository instance with mocked database."""
        return ConversationSessionRepository(mock_db)

    @pytest.fixture
    def sample_session_input(self):
        """Sample conversation session input."""
        return ConversationSessionInput(
            user_id=uuid4(),
            collection_id=uuid4(),
            session_name="Test Session",
            context_window_size=4096,
            max_messages=50,
            metadata={"type": "test", "priority": "high"},
        )

    @pytest.fixture
    def sample_session_model(self):
        """Sample conversation session model."""
        return ConversationSession(
            id=uuid4(),
            user_id=uuid4(),
            collection_id=uuid4(),
            session_name="Test Session",
            context_window_size=4096,
            max_messages=50,
            session_metadata={"type": "test"},
            created_at=datetime.utcnow(),
            status="active",
        )

    def test_create_session_success(self, repository, mock_db, sample_session_input):
        """Test successful session creation."""
        # Mock successful database operations
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        # Mock the model validation
        with patch("rag_solution.repository.conversation_session_repository.ConversationSessionOutput") as mock_output:
            mock_output.from_db_session.return_value = Mock(spec=ConversationSessionOutput)

            # Act
            result = repository.create(sample_session_input)

            # Assert
            assert result is not None
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()
            mock_output.from_db_session.assert_called_once()

    def test_create_session_integrity_error(self, repository, mock_db, sample_session_input):
        """Test session creation with integrity error."""
        # Mock integrity error
        mock_db.add.side_effect = IntegrityError("statement", "params", "orig")
        mock_db.rollback.return_value = None

        # Act & Assert
        with pytest.raises(AlreadyExistsError):
            repository.create(sample_session_input)

        mock_db.rollback.assert_called_once()

    def test_create_session_general_error(self, repository, mock_db, sample_session_input):
        """Test session creation with general error."""
        # Mock general error
        mock_db.add.side_effect = Exception("Database error")
        mock_db.rollback.return_value = None

        # Act & Assert
        with pytest.raises(Exception, match="Failed to create conversation session"):
            repository.create(sample_session_input)

        mock_db.rollback.assert_called_once()

    def test_get_by_id_success(self, repository, mock_db, sample_session_model):
        """Test successful session retrieval by ID."""
        session_id = sample_session_model.id

        # Mock database query
        mock_query = Mock()
        mock_query.options.return_value.filter.return_value.first.return_value = sample_session_model
        mock_db.query.return_value = mock_query

        # Mock the model validation
        with patch("rag_solution.repository.conversation_session_repository.ConversationSessionOutput") as mock_output:
            mock_output.from_db_session.return_value = Mock(spec=ConversationSessionOutput)

            # Act
            result = repository.get_by_id(session_id)

            # Assert
            assert result is not None
            mock_db.query.assert_called_once_with(ConversationSession)
            mock_output.from_db_session.assert_called_once_with(sample_session_model, message_count=0)

    def test_get_by_id_not_found(self, repository, mock_db):
        """Test session retrieval when not found."""
        session_id = uuid4()

        # Mock database query returning None
        mock_query = Mock()
        mock_query.options.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.get_by_id(session_id)

    def test_get_sessions_by_user(self, repository, mock_db, sample_session_model):
        """Test retrieving sessions by user ID."""
        user_id = uuid4()
        sessions = [sample_session_model]

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = (
            sessions
        )
        mock_db.query.return_value = mock_query

        # Mock the model validation
        with patch("rag_solution.repository.conversation_session_repository.ConversationSessionOutput") as mock_output:
            mock_output.from_db_session.side_effect = [Mock(spec=ConversationSessionOutput)]

            # Act
            result = repository.get_sessions_by_user(user_id, limit=50, offset=0)

            # Assert
            assert len(result) == 1
            mock_db.query.assert_called_once_with(ConversationSession)

    def test_update_session_success(self, repository, mock_db, sample_session_model):
        """Test successful session update."""
        session_id = sample_session_model.id
        updates = {"session_name": "Updated Session", "max_messages": 100}

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_session_model
        mock_db.query.return_value = mock_query
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        # Mock the model validation
        with patch("rag_solution.repository.conversation_session_repository.ConversationSessionOutput") as mock_output:
            mock_output.from_db_session.return_value = Mock(spec=ConversationSessionOutput)

            # Act
            result = repository.update(session_id, updates)

            # Assert
            assert result is not None
            assert sample_session_model.session_name == "Updated Session"
            assert sample_session_model.max_messages == 100
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

    def test_update_session_invalid_field(self, repository, mock_db, sample_session_model):
        """Test session update with invalid field."""
        session_id = sample_session_model.id
        updates = {"invalid_field": "value", "session_name": "Updated Session"}

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_session_model
        mock_db.query.return_value = mock_query
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        # Mock the model validation
        with patch("rag_solution.repository.conversation_session_repository.ConversationSessionOutput") as mock_output:
            mock_output.from_db_session.return_value = Mock(spec=ConversationSessionOutput)

            # Act
            result = repository.update(session_id, updates)

            # Assert
            assert result is not None
            # Only valid field should be updated
            assert sample_session_model.session_name == "Updated Session"
            # Invalid field should be ignored (no hasattr check passes)
            mock_db.commit.assert_called_once()

    def test_update_session_not_found(self, repository, mock_db):
        """Test updating non-existent session."""
        session_id = uuid4()
        updates = {"session_name": "Updated Session"}

        # Mock database query returning None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.update(session_id, updates)

    def test_delete_session_success(self, repository, mock_db, sample_session_model):
        """Test successful session deletion."""
        session_id = sample_session_model.id

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_session_model
        mock_db.query.return_value = mock_query
        mock_db.delete.return_value = None
        mock_db.commit.return_value = None

        # Act
        result = repository.delete(session_id)

        # Assert
        assert result is True
        mock_db.delete.assert_called_once_with(sample_session_model)
        mock_db.commit.assert_called_once()

    def test_delete_session_not_found(self, repository, mock_db):
        """Test deleting non-existent session."""
        session_id = uuid4()

        # Mock database query returning None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.delete(session_id)

    def test_get_sessions_by_collection(self, repository, mock_db, sample_session_model):
        """Test retrieving sessions by collection ID."""
        collection_id = uuid4()
        sessions = [sample_session_model]

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = (
            sessions
        )
        mock_db.query.return_value = mock_query

        # Mock the model validation
        with patch("rag_solution.repository.conversation_session_repository.ConversationSessionOutput") as mock_output:
            mock_output.from_db_session.side_effect = [Mock(spec=ConversationSessionOutput)]

            # Act
            result = repository.get_sessions_by_collection(collection_id, limit=50, offset=0)

            # Assert
            assert len(result) == 1
            mock_db.query.assert_called_once_with(ConversationSession)

    def test_allowed_fields_validation(self, repository, mock_db, sample_session_model):
        """Test that only allowed fields can be updated."""
        session_id = sample_session_model.id
        updates = {
            "session_name": "New Name",  # allowed
            "context_window_size": 8192,  # allowed
            "max_messages": 200,  # allowed
            "session_metadata": {"new": "data"},  # allowed
            "status": "inactive",  # allowed
            "id": "new-id",  # not allowed (not in allowed_fields)
            "user_id": uuid4(),  # not allowed (not in allowed_fields)
        }

        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = sample_session_model
        mock_db.query.return_value = mock_query
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        # Mock hasattr to return True only for allowed fields
        def mock_hasattr(obj, attr):
            allowed = {"session_name", "context_window_size", "max_messages", "session_metadata", "status"}
            return attr in allowed

        with (
            patch("rag_solution.repository.conversation_session_repository.ConversationSessionOutput") as mock_output,
            patch("builtins.hasattr", side_effect=mock_hasattr),
        ):
            mock_output.from_db_session.return_value = Mock(spec=ConversationSessionOutput)

            # Act
            result = repository.update(session_id, updates)

            # Assert
            assert result is not None
            # Only allowed fields should be updated
            assert sample_session_model.session_name == "New Name"
            assert sample_session_model.context_window_size == 8192
            assert sample_session_model.max_messages == 200
            assert sample_session_model.session_metadata == {"new": "data"}
            assert sample_session_model.status == "inactive"
            mock_db.commit.assert_called_once()
