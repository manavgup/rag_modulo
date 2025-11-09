"""Comprehensive unit tests for unified ConversationRepository.

Tests cover all conversation system operations:
- Session operations (create, get, update, delete, list)
- Message operations (create, get, update, delete, list, token usage)
- Summary operations (create, get, update, delete, list, strategies)
- Eager loading and N+1 query prevention
- Error handling and edge cases

This test suite ensures 90%+ coverage of the unified ConversationRepository.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, Mock
from uuid import uuid4

import pytest
from pydantic import UUID4
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Query

from core.custom_exceptions import RepositoryError
from rag_solution.core.exceptions import AlreadyExistsError, NotFoundError
from rag_solution.models.conversation import ConversationMessage, ConversationSession, ConversationSummary
from rag_solution.repository.conversation_repository import ConversationRepository
from rag_solution.schemas.conversation_schema import (
    ConversationMessageInput,
    ConversationSessionInput,
    ConversationSessionOutput,
    ConversationSummaryInput,
    ConversationSummaryOutput,
    MessageRole,
    MessageType,
    SessionStatus,
    SummarizationStrategy,
)


@pytest.fixture
def mock_db() -> MagicMock:
    """Create mock database session."""
    return MagicMock()


@pytest.fixture
def repository(mock_db: MagicMock) -> ConversationRepository:
    """Create repository instance with mock database."""
    return ConversationRepository(mock_db)


@pytest.fixture
def sample_user_id() -> UUID4:
    """Sample user UUID for testing."""
    return uuid4()


@pytest.fixture
def sample_collection_id() -> UUID4:
    """Sample collection UUID for testing."""
    return uuid4()


@pytest.fixture
def sample_session_id() -> UUID4:
    """Sample session UUID for testing."""
    return uuid4()


@pytest.fixture
def sample_message_id() -> UUID4:
    """Sample message UUID for testing."""
    return uuid4()


@pytest.fixture
def sample_summary_id() -> UUID4:
    """Sample summary UUID for testing."""
    return uuid4()


@pytest.fixture
def sample_session_input(sample_user_id: UUID4, sample_collection_id: UUID4) -> ConversationSessionInput:
    """Sample session input for testing."""
    return ConversationSessionInput(
        user_id=sample_user_id,
        collection_id=sample_collection_id,
        session_name="Test Session",
        context_window_size=4096,
        max_messages=100,
        metadata={"test": "data"},
    )


@pytest.fixture
def sample_message_input(sample_session_id: UUID4) -> ConversationMessageInput:
    """Sample message input for testing."""
    return ConversationMessageInput(
        session_id=sample_session_id,
        role=MessageRole.USER,
        message_type=MessageType.QUESTION,  # Fixed: QUERY → QUESTION
        content="Test message",
        token_count=10,
        metadata={"test": "data"},
    )


@pytest.fixture
def sample_summary_input(sample_session_id: UUID4) -> ConversationSummaryInput:
    """Sample summary input for testing."""
    return ConversationSummaryInput(
        session_id=sample_session_id,
        message_count_to_summarize=10,  # Fixed: required field
        strategy=SummarizationStrategy.RECENT_PLUS_SUMMARY,
        preserve_context=True,
        include_decisions=True,
        include_questions=True,
    )


# =============================================================================
# SESSION OPERATION TESTS
# =============================================================================


class TestSessionOperations:
    """Test suite for conversation session operations."""

    def test_create_session_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_input: ConversationSessionInput
    ) -> None:
        """Test successful session creation."""
        # Arrange
        mock_session_id = uuid4()

        def mock_refresh(obj):
            """Mock refresh that simulates database defaults."""
            obj.id = mock_session_id
            obj.status = SessionStatus.ACTIVE
            obj.is_archived = False
            obj.is_pinned = False
            obj.created_at = datetime.now(UTC)
            obj.updated_at = datetime.now(UTC)
            obj.messages = []

        mock_db.refresh.side_effect = mock_refresh

        # Act
        result = repository.create_session(sample_session_input)

        # Assert
        assert isinstance(result, ConversationSessionOutput)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_create_session_duplicate_error(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_input: ConversationSessionInput
    ) -> None:
        """Test session creation with duplicate error."""
        # Arrange
        mock_db.commit.side_effect = IntegrityError("unique", "params", "orig")

        # Act & Assert
        with pytest.raises(AlreadyExistsError):
            repository.create_session(sample_session_input)
        mock_db.rollback.assert_called_once()

    def test_create_session_general_error(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_input: ConversationSessionInput
    ) -> None:
        """Test session creation with foreign key constraint error."""
        # Arrange
        mock_db.commit.side_effect = IntegrityError("foreign key", "params", "orig")

        # Act & Assert
        with pytest.raises(NotFoundError):  # Fixed: IntegrityError with foreign key raises NotFoundError
            repository.create_session(sample_session_input)
        mock_db.rollback.assert_called_once()

    def test_get_session_by_id_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_id: UUID4
    ) -> None:
        """Test successful session retrieval by ID."""
        # Arrange
        mock_session = MagicMock(spec=ConversationSession)
        mock_session.id = sample_session_id
        mock_session.user_id = uuid4()
        mock_session.collection_id = uuid4()
        mock_session.session_name = "Test Session"
        mock_session.status = "active"
        mock_session.context_window_size = 4096
        mock_session.max_messages = 100
        mock_session.session_metadata = {}
        mock_session.created_at = datetime.now(UTC)
        mock_session.updated_at = datetime.now(UTC)
        mock_session.messages = []

        # Mock query chain
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_options = Mock(spec=Query)
        mock_query.options.return_value = mock_query_with_options
        mock_query_with_filter = Mock(spec=Query)
        mock_query_with_options.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = mock_session

        # Act
        result = repository.get_session_by_id(sample_session_id)

        # Assert
        assert isinstance(result, ConversationSessionOutput)
        mock_query.options.assert_called_once()  # Verify eager loading

    def test_get_session_by_id_not_found(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_id: UUID4
    ) -> None:
        """Test session retrieval when session not found."""
        # Arrange
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_options = Mock(spec=Query)
        mock_query.options.return_value = mock_query_with_options
        mock_query_with_filter = Mock(spec=Query)
        mock_query_with_options.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.get_session_by_id(sample_session_id)

    def test_get_sessions_by_user_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_user_id: UUID4
    ) -> None:
        """Test successful retrieval of sessions by user."""
        # Arrange
        mock_session = MagicMock(spec=ConversationSession)
        mock_session.id = uuid4()
        mock_session.user_id = sample_user_id
        mock_session.collection_id = uuid4()
        mock_session.session_name = "Test Session"
        mock_session.status = "active"
        mock_session.context_window_size = 4096
        mock_session.max_messages = 100
        mock_session.session_metadata = {}
        mock_session.created_at = datetime.now(UTC)
        mock_session.updated_at = datetime.now(UTC)
        mock_session.messages = []

        # Mock query chain
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_options = Mock(spec=Query)
        mock_query.options.return_value = mock_query_with_options
        mock_query_with_filter = Mock(spec=Query)
        mock_query_with_options.filter.return_value = mock_query_with_filter
        mock_query_with_order = Mock(spec=Query)
        mock_query_with_filter.order_by.return_value = mock_query_with_order
        mock_query_with_limit = Mock(spec=Query)
        mock_query_with_order.limit.return_value = mock_query_with_limit
        mock_query_with_offset = Mock(spec=Query)
        mock_query_with_limit.offset.return_value = mock_query_with_offset
        mock_query_with_offset.all.return_value = [mock_session]

        # Act
        result = repository.get_sessions_by_user(sample_user_id, limit=50, offset=0)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        mock_query.options.assert_called_once()  # Verify eager loading

    def test_get_sessions_by_collection_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_collection_id: UUID4
    ) -> None:
        """Test successful retrieval of sessions by collection."""
        # Arrange
        mock_session = MagicMock(spec=ConversationSession)
        mock_session.id = uuid4()
        mock_session.user_id = uuid4()
        mock_session.collection_id = sample_collection_id
        mock_session.session_name = "Test Session"
        mock_session.status = "active"
        mock_session.context_window_size = 4096
        mock_session.max_messages = 100
        mock_session.session_metadata = {}
        mock_session.created_at = datetime.now(UTC)
        mock_session.updated_at = datetime.now(UTC)
        mock_session.messages = []

        # Mock query chain
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_options = Mock(spec=Query)
        mock_query.options.return_value = mock_query_with_options
        mock_query_with_filter = Mock(spec=Query)
        mock_query_with_options.filter.return_value = mock_query_with_filter
        mock_query_with_order = Mock(spec=Query)
        mock_query_with_filter.order_by.return_value = mock_query_with_order
        mock_query_with_limit = Mock(spec=Query)
        mock_query_with_order.limit.return_value = mock_query_with_limit
        mock_query_with_offset = Mock(spec=Query)
        mock_query_with_limit.offset.return_value = mock_query_with_offset
        mock_query_with_offset.all.return_value = [mock_session]

        # Act
        result = repository.get_sessions_by_collection(sample_collection_id, limit=50, offset=0)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        mock_query.options.assert_called_once()  # Verify eager loading

    def test_update_session_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_id: UUID4
    ) -> None:
        """Test successful session update."""
        # Arrange
        updates = {"session_name": "Updated Name", "status": "paused"}  # Fixed: inactive → paused
        mock_session = MagicMock(spec=ConversationSession)
        mock_session.id = sample_session_id
        mock_session.user_id = uuid4()
        mock_session.collection_id = uuid4()
        mock_session.session_name = "Old Name"
        mock_session.status = SessionStatus.ACTIVE  # Fixed: use enum
        mock_session.is_archived = False  # Fixed: add missing field
        mock_session.is_pinned = False  # Fixed: add missing field
        mock_session.context_window_size = 4096
        mock_session.max_messages = 100
        mock_session.session_metadata = {}
        mock_session.created_at = datetime.now(UTC)
        mock_session.updated_at = datetime.now(UTC)
        mock_session.messages = []

        # Mock query chain
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_options = Mock(spec=Query)
        mock_query.options.return_value = mock_query_with_options
        mock_query_with_filter = Mock(spec=Query)
        mock_query_with_options.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = mock_session

        # Act
        result = repository.update_session(sample_session_id, updates)

        # Assert
        assert isinstance(result, ConversationSessionOutput)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_update_session_not_found(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_id: UUID4
    ) -> None:
        """Test session update when session not found."""
        # Arrange
        updates = {"session_name": "Updated Name"}
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_options = Mock(spec=Query)
        mock_query.options.return_value = mock_query_with_options
        mock_query_with_filter = Mock(spec=Query)
        mock_query_with_options.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.update_session(sample_session_id, updates)

    def test_delete_session_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_id: UUID4
    ) -> None:
        """Test successful session deletion."""
        # Arrange
        mock_session = MagicMock(spec=ConversationSession)
        mock_session.id = sample_session_id
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = mock_session

        # Act
        result = repository.delete_session(sample_session_id)

        # Assert
        assert result is True
        mock_db.delete.assert_called_once_with(mock_session)
        mock_db.commit.assert_called_once()

    def test_delete_session_not_found(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_id: UUID4
    ) -> None:
        """Test session deletion when session not found."""
        # Arrange
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.delete_session(sample_session_id)


# =============================================================================
# MESSAGE OPERATION TESTS
# =============================================================================


class TestMessageOperations:
    """Test suite for conversation message operations."""

    def test_create_message_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_message_input: ConversationMessageInput
    ) -> None:
        """Test successful message creation."""
        # Arrange
        mock_message = ConversationMessage(
            id=uuid4(),
            session_id=sample_message_input.session_id,
            role=sample_message_input.role,
            message_type=sample_message_input.message_type,
            content=sample_message_input.content,
            token_count=sample_message_input.token_count,
            message_metadata=sample_message_input.metadata or {},
            created_at=datetime.now(UTC),
        )
        mock_db.refresh.side_effect = lambda x: setattr(x, "id", mock_message.id)

        # Act
        result = repository.create_message(sample_message_input)

        # Assert
        assert isinstance(result, ConversationMessage)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_create_message_session_not_found(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_message_input: ConversationMessageInput
    ) -> None:
        """Test message creation when session not found."""
        # Arrange
        mock_db.commit.side_effect = IntegrityError("foreign key", "params", "orig")

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.create_message(sample_message_input)
        mock_db.rollback.assert_called_once()

    def test_get_message_by_id_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_message_id: UUID4
    ) -> None:
        """Test successful message retrieval by ID."""
        # Arrange
        mock_message = MagicMock(spec=ConversationMessage)
        mock_message.id = sample_message_id
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        # Fixed: Add .options() to mock chain
        mock_query_with_options = Mock(spec=Query)
        mock_query.options.return_value = mock_query_with_options
        mock_query_with_filter = Mock(spec=Query)
        mock_query_with_options.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = mock_message

        # Act
        result = repository.get_message_by_id(sample_message_id)

        # Assert
        assert result == mock_message

    def test_get_message_by_id_not_found(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_message_id: UUID4
    ) -> None:
        """Test message retrieval when message not found."""
        # Arrange
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        # Fixed: Add .options() to mock chain
        mock_query_with_options = Mock(spec=Query)
        mock_query.options.return_value = mock_query_with_options
        mock_query_with_filter = Mock(spec=Query)
        mock_query_with_options.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.get_message_by_id(sample_message_id)

    def test_get_messages_by_session_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_id: UUID4
    ) -> None:
        """Test successful retrieval of messages by session."""
        # Arrange
        mock_message = MagicMock(spec=ConversationMessage)
        mock_message.id = uuid4()
        mock_message.session_id = sample_session_id

        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_order = Mock(spec=Query)
        mock_query_with_filter.order_by.return_value = mock_query_with_order
        mock_query_with_limit = Mock(spec=Query)
        mock_query_with_order.limit.return_value = mock_query_with_limit
        mock_query_with_offset = Mock(spec=Query)
        mock_query_with_limit.offset.return_value = mock_query_with_offset
        mock_query_with_offset.all.return_value = [mock_message]

        # Act
        result = repository.get_messages_by_session(sample_session_id, limit=50, offset=0)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1

    def test_get_recent_messages_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_id: UUID4
    ) -> None:
        """Test successful retrieval of recent messages."""
        # Arrange
        mock_message = MagicMock(spec=ConversationMessage)
        mock_message.id = uuid4()
        mock_message.session_id = sample_session_id

        # Fixed: Match actual query chain: query().select_from().order_by().all()
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_select = Mock(spec=Query)
        mock_query.select_from.return_value = mock_query_with_select
        mock_query_with_order = Mock(spec=Query)
        mock_query_with_select.order_by.return_value = mock_query_with_order
        mock_query_with_order.all.return_value = [mock_message]

        # Act
        result = repository.get_recent_messages(sample_session_id, count=10)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1

    def test_update_message_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_message_id: UUID4
    ) -> None:
        """Test successful message update."""
        # Arrange
        updates = {"content": "Updated content"}
        mock_message = MagicMock(spec=ConversationMessage)
        mock_message.id = sample_message_id
        mock_message.content = "Old content"

        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = mock_message

        # Act
        result = repository.update_message(sample_message_id, updates)

        # Assert
        assert result == mock_message
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_update_message_not_found(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_message_id: UUID4
    ) -> None:
        """Test message update when message not found."""
        # Arrange
        updates = {"content": "Updated content"}
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.update_message(sample_message_id, updates)

    def test_delete_message_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_message_id: UUID4
    ) -> None:
        """Test successful message deletion."""
        # Arrange
        mock_message = MagicMock(spec=ConversationMessage)
        mock_message.id = sample_message_id
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = mock_message

        # Act
        result = repository.delete_message(sample_message_id)

        # Assert
        assert result is True
        mock_db.delete.assert_called_once_with(mock_message)
        mock_db.commit.assert_called_once()

    def test_delete_message_not_found(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_message_id: UUID4
    ) -> None:
        """Test message deletion when message not found."""
        # Arrange
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.delete_message(sample_message_id)

    def test_delete_messages_by_session_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_id: UUID4
    ) -> None:
        """Test successful bulk deletion of messages by session."""
        # Arrange
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_filter.delete.return_value = 5  # 5 messages deleted

        # Act
        result = repository.delete_messages_by_session(sample_session_id)

        # Assert
        assert result == 5
        mock_db.commit.assert_called_once()

    def test_get_token_usage_by_session_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_id: UUID4
    ) -> None:
        """Test successful calculation of token usage."""
        # Arrange
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_filter.scalar.return_value = 1000  # Total token count

        # Act
        result = repository.get_token_usage_by_session(sample_session_id)

        # Assert
        assert result == 1000

    def test_get_token_usage_by_session_no_messages(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_id: UUID4
    ) -> None:
        """Test token usage calculation when no messages exist."""
        # Arrange
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_filter.scalar.return_value = None

        # Act
        result = repository.get_token_usage_by_session(sample_session_id)

        # Assert
        assert result == 0


# =============================================================================
# SUMMARY OPERATION TESTS
# =============================================================================


class TestSummaryOperations:
    """Test suite for conversation summary operations."""

    def test_create_summary_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_summary_input: ConversationSummaryInput
    ) -> None:
        """Test successful summary creation."""
        # Arrange
        mock_summary_id = uuid4()

        def mock_refresh(obj):
            """Mock refresh that simulates database defaults."""
            obj.id = mock_summary_id
            obj.summary_text = "Summary being generated..."
            obj.summarized_message_count = sample_summary_input.message_count_to_summarize
            obj.tokens_saved = 0
            obj.key_topics = []
            obj.important_decisions = []
            obj.unresolved_questions = []
            obj.summary_strategy = sample_summary_input.strategy.value
            obj.summary_metadata = {
                "preserve_context": sample_summary_input.preserve_context,
                "include_decisions": sample_summary_input.include_decisions,
                "include_questions": sample_summary_input.include_questions,
            }
            obj.created_at = datetime.now(UTC)

        mock_db.refresh.side_effect = mock_refresh

        # Act
        result = repository.create_summary(sample_summary_input)

        # Assert
        assert isinstance(result, ConversationSummaryOutput)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_create_summary_session_not_found(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_summary_input: ConversationSummaryInput
    ) -> None:
        """Test summary creation when session not found."""
        # Arrange
        mock_db.commit.side_effect = IntegrityError("foreign key", "params", "orig")

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.create_summary(sample_summary_input)
        mock_db.rollback.assert_called_once()

    def test_get_summary_by_id_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_summary_id: UUID4
    ) -> None:
        """Test successful summary retrieval by ID."""
        # Arrange
        mock_summary = MagicMock(spec=ConversationSummary)
        mock_summary.id = sample_summary_id
        mock_summary.session_id = uuid4()
        mock_summary.summary_text = "Test summary"
        mock_summary.summary_strategy = "recent_plus_summary"  # Fixed: use database field name and string value
        mock_summary.tokens_saved = 100
        mock_summary.summary_metadata = {}
        mock_summary.created_at = datetime.now(UTC)

        # Fixed: Add .options() to mock chain
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_options = Mock(spec=Query)
        mock_query.options.return_value = mock_query_with_options
        mock_query_with_filter = Mock(spec=Query)
        mock_query_with_options.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = mock_summary

        # Act
        result = repository.get_summary_by_id(sample_summary_id)

        # Assert
        assert isinstance(result, ConversationSummaryOutput)

    def test_get_summary_by_id_not_found(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_summary_id: UUID4
    ) -> None:
        """Test summary retrieval when summary not found."""
        # Arrange
        # Fixed: Add .options() to mock chain
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_options = Mock(spec=Query)
        mock_query.options.return_value = mock_query_with_options
        mock_query_with_filter = Mock(spec=Query)
        mock_query_with_options.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.get_summary_by_id(sample_summary_id)

    def test_get_summaries_by_session_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_id: UUID4
    ) -> None:
        """Test successful retrieval of summaries by session."""
        # Arrange
        mock_summary = MagicMock(spec=ConversationSummary)
        mock_summary.id = uuid4()
        mock_summary.session_id = sample_session_id
        mock_summary.summary_text = "Test summary"
        mock_summary.summary_strategy = "recent_plus_summary"
        mock_summary.tokens_saved = 100
        mock_summary.summary_metadata = {}
        mock_summary.created_at = datetime.now(UTC)

        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_order = Mock(spec=Query)
        mock_query_with_filter.order_by.return_value = mock_query_with_order
        mock_query_with_limit = Mock(spec=Query)
        mock_query_with_order.limit.return_value = mock_query_with_limit
        mock_query_with_offset = Mock(spec=Query)
        mock_query_with_limit.offset.return_value = mock_query_with_offset
        mock_query_with_offset.all.return_value = [mock_summary]

        # Act
        result = repository.get_summaries_by_session(sample_session_id, limit=50, offset=0)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1

    def test_get_latest_summary_by_session_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_id: UUID4
    ) -> None:
        """Test successful retrieval of latest summary."""
        # Arrange
        mock_summary = MagicMock(spec=ConversationSummary)
        mock_summary.id = uuid4()
        mock_summary.session_id = sample_session_id
        mock_summary.summary_text = "Test summary"
        mock_summary.summary_strategy = "recent_plus_summary"
        mock_summary.tokens_saved = 100
        mock_summary.summary_metadata = {}
        mock_summary.created_at = datetime.now(UTC)

        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_order = Mock(spec=Query)
        mock_query_with_filter.order_by.return_value = mock_query_with_order
        mock_query_with_order.first.return_value = mock_summary

        # Act
        result = repository.get_latest_summary_by_session(sample_session_id)

        # Assert
        assert isinstance(result, ConversationSummaryOutput)

    def test_get_latest_summary_by_session_not_found(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_id: UUID4
    ) -> None:
        """Test latest summary retrieval when no summaries exist."""
        # Arrange
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_order = Mock(spec=Query)
        mock_query_with_filter.order_by.return_value = mock_query_with_order
        mock_query_with_order.first.return_value = None

        # Act
        result = repository.get_latest_summary_by_session(sample_session_id)

        # Assert
        assert result is None

    def test_update_summary_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_summary_id: UUID4
    ) -> None:
        """Test successful summary update."""
        # Arrange
        updates = {"summary_text": "Updated summary"}
        mock_summary = MagicMock(spec=ConversationSummary)
        mock_summary.id = sample_summary_id
        mock_summary.session_id = uuid4()
        mock_summary.summary_text = "Old summary"
        mock_summary.summary_strategy = "recent_plus_summary"
        mock_summary.tokens_saved = 100
        mock_summary.summary_metadata = {}
        mock_summary.created_at = datetime.now(UTC)

        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = mock_summary

        # Act
        result = repository.update_summary(sample_summary_id, updates)

        # Assert
        assert isinstance(result, ConversationSummaryOutput)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_update_summary_not_found(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_summary_id: UUID4
    ) -> None:
        """Test summary update when summary not found."""
        # Arrange
        updates = {"summary_text": "Updated summary"}
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.update_summary(sample_summary_id, updates)

    def test_delete_summary_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_summary_id: UUID4
    ) -> None:
        """Test successful summary deletion."""
        # Arrange
        mock_summary = MagicMock(spec=ConversationSummary)
        mock_summary.id = sample_summary_id
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = mock_summary

        # Act
        result = repository.delete_summary(sample_summary_id)

        # Assert
        assert result is True
        mock_db.delete.assert_called_once_with(mock_summary)
        mock_db.commit.assert_called_once()

    def test_delete_summary_not_found(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_summary_id: UUID4
    ) -> None:
        """Test summary deletion when summary not found."""
        # Arrange
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.delete_summary(sample_summary_id)

    def test_count_summaries_by_session_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_id: UUID4
    ) -> None:
        """Test successful count of summaries by session."""
        # Arrange
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_filter.count.return_value = 5

        # Act
        result = repository.count_summaries_by_session(sample_session_id)

        # Assert
        assert result == 5

    def test_get_summaries_by_strategy_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_id: UUID4
    ) -> None:
        """Test successful retrieval of summaries by strategy."""
        # Arrange
        mock_summary = MagicMock(spec=ConversationSummary)
        mock_summary.id = uuid4()
        mock_summary.session_id = sample_session_id
        mock_summary.summary_text = "Test summary"
        mock_summary.summary_strategy = "recent_plus_summary"
        mock_summary.tokens_saved = 100
        mock_summary.summary_metadata = {}
        mock_summary.created_at = datetime.now(UTC)

        # Fixed: Match actual query chain: query().filter().order_by().limit().offset().all()
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_order = Mock(spec=Query)
        mock_query_with_filter.order_by.return_value = mock_query_with_order
        mock_query_with_limit = Mock(spec=Query)
        mock_query_with_order.limit.return_value = mock_query_with_limit
        mock_query_with_offset = Mock(spec=Query)
        mock_query_with_limit.offset.return_value = mock_query_with_offset
        mock_query_with_offset.all.return_value = [mock_summary]

        # Act - Fixed: Method signature is get_summaries_by_strategy(strategy, limit, offset)
        result = repository.get_summaries_by_strategy(SummarizationStrategy.RECENT_PLUS_SUMMARY)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1

    def test_get_summaries_with_tokens_saved_success(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_id: UUID4
    ) -> None:
        """Test successful retrieval of summaries with minimum tokens saved."""
        # Arrange
        mock_summary = MagicMock(spec=ConversationSummary)
        mock_summary.id = uuid4()
        mock_summary.session_id = sample_session_id
        mock_summary.summary_text = "Test summary"
        mock_summary.summary_strategy = "recent_plus_summary"
        mock_summary.tokens_saved = 200
        mock_summary.summary_metadata = {}
        mock_summary.created_at = datetime.now(UTC)

        # Fixed: Match actual query chain: query().filter().order_by().limit().offset().all()
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_filter = Mock(spec=Query)
        mock_query.filter.return_value = mock_query_with_filter
        mock_query_with_order = Mock(spec=Query)
        mock_query_with_filter.order_by.return_value = mock_query_with_order
        mock_query_with_limit = Mock(spec=Query)
        mock_query_with_order.limit.return_value = mock_query_with_limit
        mock_query_with_offset = Mock(spec=Query)
        mock_query_with_limit.offset.return_value = mock_query_with_offset
        mock_query_with_offset.all.return_value = [mock_summary]

        # Act - Fixed: Method signature is get_summaries_with_tokens_saved(min_tokens_saved, limit, offset)
        result = repository.get_summaries_with_tokens_saved(min_tokens_saved=100)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1


# =============================================================================
# EAGER LOADING AND PERFORMANCE TESTS
# =============================================================================


class TestEagerLoading:
    """Test suite for eager loading and N+1 query prevention."""

    def test_get_sessions_by_user_uses_joinedload(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_user_id: UUID4
    ) -> None:
        """Test that get_sessions_by_user uses joinedload for eager loading."""
        # Arrange
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_options = Mock(spec=Query)
        mock_query.options.return_value = mock_query_with_options
        mock_query_with_filter = Mock(spec=Query)
        mock_query_with_options.filter.return_value = mock_query_with_filter
        mock_query_with_order = Mock(spec=Query)
        mock_query_with_filter.order_by.return_value = mock_query_with_order
        mock_query_with_limit = Mock(spec=Query)
        mock_query_with_order.limit.return_value = mock_query_with_limit
        mock_query_with_offset = Mock(spec=Query)
        mock_query_with_limit.offset.return_value = mock_query_with_offset
        mock_query_with_offset.all.return_value = []

        # Act
        repository.get_sessions_by_user(sample_user_id)

        # Assert
        mock_query.options.assert_called_once()  # Verify eager loading is used

    def test_get_sessions_by_collection_uses_joinedload(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_collection_id: UUID4
    ) -> None:
        """Test that get_sessions_by_collection uses joinedload for eager loading."""
        # Arrange
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_options = Mock(spec=Query)
        mock_query.options.return_value = mock_query_with_options
        mock_query_with_filter = Mock(spec=Query)
        mock_query_with_options.filter.return_value = mock_query_with_filter
        mock_query_with_order = Mock(spec=Query)
        mock_query_with_filter.order_by.return_value = mock_query_with_order
        mock_query_with_limit = Mock(spec=Query)
        mock_query_with_order.limit.return_value = mock_query_with_limit
        mock_query_with_offset = Mock(spec=Query)
        mock_query_with_limit.offset.return_value = mock_query_with_offset
        mock_query_with_offset.all.return_value = []

        # Act
        repository.get_sessions_by_collection(sample_collection_id)

        # Assert
        mock_query.options.assert_called_once()  # Verify eager loading is used

    def test_get_session_by_id_uses_joinedload(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_id: UUID4
    ) -> None:
        """Test that get_session_by_id uses joinedload for eager loading."""
        # Arrange
        mock_query = Mock(spec=Query)
        mock_db.query.return_value = mock_query
        mock_query_with_options = Mock(spec=Query)
        mock_query.options.return_value = mock_query_with_options
        mock_query_with_filter = Mock(spec=Query)
        mock_query_with_options.filter.return_value = mock_query_with_filter
        mock_query_with_filter.first.return_value = None

        # Act & Assert (will raise NotFoundError, but we're just testing query building)
        with pytest.raises(NotFoundError):
            repository.get_session_by_id(sample_session_id)

        # Assert
        mock_query.options.assert_called_once()  # Verify eager loading is used


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Test suite for error handling scenarios."""

    def test_database_error_on_create_session(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_session_input: ConversationSessionInput
    ) -> None:
        """Test handling of general database errors during session creation."""
        # Arrange
        mock_db.commit.side_effect = SQLAlchemyError("Database error")

        # Act & Assert
        with pytest.raises(RepositoryError):
            repository.create_session(sample_session_input)
        mock_db.rollback.assert_called_once()

    def test_database_error_on_create_message(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_message_input: ConversationMessageInput
    ) -> None:
        """Test handling of general database errors during message creation."""
        # Arrange
        mock_db.commit.side_effect = SQLAlchemyError("Database error")

        # Act & Assert
        with pytest.raises(RepositoryError):
            repository.create_message(sample_message_input)
        mock_db.rollback.assert_called_once()

    def test_database_error_on_create_summary(
        self, repository: ConversationRepository, mock_db: MagicMock, sample_summary_input: ConversationSummaryInput
    ) -> None:
        """Test handling of general database errors during summary creation."""
        # Arrange
        mock_db.commit.side_effect = SQLAlchemyError("Database error")

        # Act & Assert
        with pytest.raises(RepositoryError):
            repository.create_summary(sample_summary_input)
        mock_db.rollback.assert_called_once()
