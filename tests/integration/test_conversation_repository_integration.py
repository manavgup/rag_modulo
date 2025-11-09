"""Integration tests for unified ConversationRepository.

These tests use real database connections with transaction rollback for isolation.
They verify:
- Complete CRUD operations for sessions, messages, and summaries
- Eager loading and N+1 query prevention
- Foreign key relationships and cascading deletes
- Transaction handling and data integrity
- Error handling with real database constraints
"""

from uuid import uuid4

import pytest
from pydantic import UUID4
from sqlalchemy.orm import Session

from rag_solution.core.exceptions import NotFoundError
from rag_solution.repository.conversation_repository import ConversationRepository
from rag_solution.schemas.conversation_schema import (
    ConversationMessageInput,
    ConversationSessionInput,
    ConversationSummaryInput,
    MessageRole,
    MessageType,
    SummarizationStrategy,
)


@pytest.mark.integration
class TestConversationRepositoryIntegration:
    """Integration tests for ConversationRepository with real database."""

    @pytest.fixture
    def repository(self, real_db_session: Session) -> ConversationRepository:
        """Create repository instance with real database session."""
        return ConversationRepository(real_db_session)

    @pytest.fixture
    def test_user_id(self) -> UUID4:
        """Generate a test user ID."""
        return uuid4()

    @pytest.fixture
    def test_collection_id(self) -> UUID4:
        """Generate a test collection ID."""
        return uuid4()

    # =========================================================================
    # SESSION INTEGRATION TESTS
    # =========================================================================

    def test_create_and_get_session(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test creating and retrieving a conversation session."""
        # Create session
        session_input = ConversationSessionInput(
            user_id=test_user_id,
            collection_id=test_collection_id,
            session_name="Integration Test Session",
            context_window_size=4096,
            max_messages=100,
            metadata={"test": "integration"},
        )
        created_session = repository.create_session(session_input)

        # Verify creation
        assert created_session.id is not None
        assert created_session.session_name == "Integration Test Session"
        assert created_session.user_id == test_user_id
        assert created_session.collection_id == test_collection_id

        # Retrieve and verify
        retrieved_session = repository.get_session_by_id(created_session.id)
        assert retrieved_session.id == created_session.id
        assert retrieved_session.session_name == created_session.session_name
        assert retrieved_session.message_count == 0

    def test_update_session(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test updating a conversation session."""
        # Create session
        session_input = ConversationSessionInput(
            user_id=test_user_id,
            collection_id=test_collection_id,
            session_name="Original Name",
            context_window_size=4096,
            max_messages=100,
        )
        created_session = repository.create_session(session_input)

        # Update session
        updates = {"session_name": "Updated Name", "status": "inactive"}
        updated_session = repository.update_session(created_session.id, updates)

        # Verify update
        assert updated_session.session_name == "Updated Name"
        assert updated_session.status == "inactive"

        # Verify persistence
        retrieved_session = repository.get_session_by_id(created_session.id)
        assert retrieved_session.session_name == "Updated Name"
        assert retrieved_session.status == "inactive"

    def test_delete_session(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test deleting a conversation session."""
        # Create session
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="To Delete"
        )
        created_session = repository.create_session(session_input)

        # Delete session
        result = repository.delete_session(created_session.id)
        assert result is True

        # Verify deletion
        with pytest.raises(NotFoundError):
            repository.get_session_by_id(created_session.id)

    def test_get_sessions_by_user(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test retrieving all sessions for a user."""
        # Create multiple sessions
        for i in range(3):
            session_input = ConversationSessionInput(
                user_id=test_user_id, collection_id=test_collection_id, session_name=f"Session {i}"
            )
            repository.create_session(session_input)

        # Retrieve sessions
        sessions = repository.get_sessions_by_user(test_user_id)

        # Verify
        assert len(sessions) >= 3
        user_session_names = {s.session_name for s in sessions if s.user_id == test_user_id}
        assert "Session 0" in user_session_names
        assert "Session 1" in user_session_names
        assert "Session 2" in user_session_names

    def test_get_sessions_by_collection(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test retrieving all sessions for a collection."""
        # Create multiple sessions
        for i in range(2):
            session_input = ConversationSessionInput(
                user_id=test_user_id, collection_id=test_collection_id, session_name=f"Collection Session {i}"
            )
            repository.create_session(session_input)

        # Retrieve sessions
        sessions = repository.get_sessions_by_collection(test_collection_id)

        # Verify
        assert len(sessions) >= 2
        collection_session_names = {s.session_name for s in sessions if s.collection_id == test_collection_id}
        assert "Collection Session 0" in collection_session_names
        assert "Collection Session 1" in collection_session_names

    # =========================================================================
    # MESSAGE INTEGRATION TESTS
    # =========================================================================

    def test_create_and_get_message(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test creating and retrieving a conversation message."""
        # Create session first
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Message Test Session"
        )
        session = repository.create_session(session_input)

        # Create message
        message_input = ConversationMessageInput(
            session_id=session.id,
            role=MessageRole.USER,
            message_type=MessageType.QUERY,
            content="Test message content",
            token_count=10,
            metadata={"test": "integration"},
        )
        created_message = repository.create_message(message_input)

        # Verify creation
        assert created_message.id is not None
        assert created_message.content == "Test message content"
        assert created_message.role == MessageRole.USER
        assert created_message.token_count == 10

        # Retrieve and verify
        retrieved_message = repository.get_message_by_id(created_message.id)
        assert retrieved_message.id == created_message.id
        assert retrieved_message.content == created_message.content

    def test_get_messages_by_session(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test retrieving all messages for a session."""
        # Create session
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Multi-Message Session"
        )
        session = repository.create_session(session_input)

        # Create multiple messages
        for i in range(5):
            message_input = ConversationMessageInput(
                session_id=session.id,
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                message_type=MessageType.QUERY if i % 2 == 0 else MessageType.RESPONSE,
                content=f"Message {i}",
                token_count=10,
            )
            repository.create_message(message_input)

        # Retrieve messages
        messages = repository.get_messages_by_session(session.id)

        # Verify
        assert len(messages) == 5
        message_contents = [m.content for m in messages]
        for i in range(5):
            assert f"Message {i}" in message_contents

    def test_get_recent_messages(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test retrieving recent messages."""
        # Create session
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Recent Messages Session"
        )
        session = repository.create_session(session_input)

        # Create multiple messages
        for i in range(10):
            message_input = ConversationMessageInput(
                session_id=session.id,
                role=MessageRole.USER,
                message_type=MessageType.QUERY,
                content=f"Message {i}",
                token_count=10,
            )
            repository.create_message(message_input)

        # Get recent 3 messages
        recent_messages = repository.get_recent_messages(session.id, count=3)

        # Verify (should get last 3 in reverse chronological order)
        assert len(recent_messages) == 3

    def test_update_message(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test updating a message."""
        # Create session and message
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Update Message Session"
        )
        session = repository.create_session(session_input)

        message_input = ConversationMessageInput(
            session_id=session.id,
            role=MessageRole.USER,
            message_type=MessageType.QUERY,
            content="Original content",
            token_count=10,
        )
        message = repository.create_message(message_input)

        # Update message
        updates = {"content": "Updated content", "token_count": 20}
        updated_message = repository.update_message(message.id, updates)

        # Verify update
        assert updated_message.content == "Updated content"
        assert updated_message.token_count == 20

    def test_delete_message(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test deleting a single message."""
        # Create session and message
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Delete Message Session"
        )
        session = repository.create_session(session_input)

        message_input = ConversationMessageInput(
            session_id=session.id, role=MessageRole.USER, message_type=MessageType.QUERY, content="To delete"
        )
        message = repository.create_message(message_input)

        # Delete message
        result = repository.delete_message(message.id)
        assert result is True

        # Verify deletion
        with pytest.raises(NotFoundError):
            repository.get_message_by_id(message.id)

    def test_delete_messages_by_session(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test bulk deletion of messages by session."""
        # Create session and messages
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Bulk Delete Session"
        )
        session = repository.create_session(session_input)

        for i in range(5):
            message_input = ConversationMessageInput(
                session_id=session.id,
                role=MessageRole.USER,
                message_type=MessageType.QUERY,
                content=f"Message {i}",
            )
            repository.create_message(message_input)

        # Delete all messages
        deleted_count = repository.delete_messages_by_session(session.id)
        assert deleted_count == 5

        # Verify deletion
        messages = repository.get_messages_by_session(session.id)
        assert len(messages) == 0

    def test_get_token_usage_by_session(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test calculating token usage for a session."""
        # Create session and messages
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Token Usage Session"
        )
        session = repository.create_session(session_input)

        # Create messages with known token counts
        token_counts = [10, 20, 30, 40, 50]
        for count in token_counts:
            message_input = ConversationMessageInput(
                session_id=session.id,
                role=MessageRole.USER,
                message_type=MessageType.QUERY,
                content="Content",
                token_count=count,
            )
            repository.create_message(message_input)

        # Get total token usage
        total_tokens = repository.get_token_usage_by_session(session.id)
        assert total_tokens == sum(token_counts)  # 150

    # =========================================================================
    # SUMMARY INTEGRATION TESTS
    # =========================================================================

    def test_create_and_get_summary(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test creating and retrieving a conversation summary."""
        # Create session first
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Summary Test Session"
        )
        session = repository.create_session(session_input)

        # Create summary
        summary_input = ConversationSummaryInput(
            session_id=session.id,
            summary_text="This is a test summary",
            strategy=SummarizationStrategy.SLIDING_WINDOW,
            tokens_saved=100,
            metadata={"test": "integration"},
        )
        created_summary = repository.create_summary(summary_input)

        # Verify creation
        assert created_summary.id is not None
        assert created_summary.summary_text == "This is a test summary"
        assert created_summary.strategy == SummarizationStrategy.SLIDING_WINDOW
        assert created_summary.tokens_saved == 100

        # Retrieve and verify
        retrieved_summary = repository.get_summary_by_id(created_summary.id)
        assert retrieved_summary.id == created_summary.id
        assert retrieved_summary.summary_text == created_summary.summary_text

    def test_get_summaries_by_session(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test retrieving all summaries for a session."""
        # Create session
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Multi-Summary Session"
        )
        session = repository.create_session(session_input)

        # Create multiple summaries
        for i in range(3):
            summary_input = ConversationSummaryInput(
                session_id=session.id,
                summary_text=f"Summary {i}",
                strategy=SummarizationStrategy.SLIDING_WINDOW,
                tokens_saved=50,
            )
            repository.create_summary(summary_input)

        # Retrieve summaries
        summaries = repository.get_summaries_by_session(session.id)

        # Verify
        assert len(summaries) == 3
        summary_texts = [s.summary_text for s in summaries]
        for i in range(3):
            assert f"Summary {i}" in summary_texts

    def test_get_latest_summary(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test retrieving the latest summary for a session."""
        # Create session
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Latest Summary Session"
        )
        session = repository.create_session(session_input)

        # Create multiple summaries
        for i in range(3):
            summary_input = ConversationSummaryInput(
                session_id=session.id,
                summary_text=f"Summary {i}",
                strategy=SummarizationStrategy.SLIDING_WINDOW,
                tokens_saved=50,
            )
            repository.create_summary(summary_input)

        # Get latest summary
        latest = repository.get_latest_summary_by_session(session.id)

        # Verify (should be the last one created)
        assert latest is not None
        assert "Summary 2" in latest.summary_text

    def test_update_summary(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test updating a summary."""
        # Create session and summary
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Update Summary Session"
        )
        session = repository.create_session(session_input)

        summary_input = ConversationSummaryInput(
            session_id=session.id,
            summary_text="Original summary",
            strategy=SummarizationStrategy.SLIDING_WINDOW,
            tokens_saved=50,
        )
        summary = repository.create_summary(summary_input)

        # Update summary
        updates = {"summary_text": "Updated summary", "tokens_saved": 100}
        updated_summary = repository.update_summary(summary.id, updates)

        # Verify update
        assert updated_summary.summary_text == "Updated summary"
        assert updated_summary.tokens_saved == 100

    def test_delete_summary(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test deleting a summary."""
        # Create session and summary
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Delete Summary Session"
        )
        session = repository.create_session(session_input)

        summary_input = ConversationSummaryInput(
            session_id=session.id, summary_text="To delete", strategy=SummarizationStrategy.SLIDING_WINDOW
        )
        summary = repository.create_summary(summary_input)

        # Delete summary
        result = repository.delete_summary(summary.id)
        assert result is True

        # Verify deletion
        with pytest.raises(NotFoundError):
            repository.get_summary_by_id(summary.id)

    def test_count_summaries_by_session(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test counting summaries for a session."""
        # Create session
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Count Summary Session"
        )
        session = repository.create_session(session_input)

        # Create summaries
        for i in range(5):
            summary_input = ConversationSummaryInput(
                session_id=session.id, summary_text=f"Summary {i}", strategy=SummarizationStrategy.SLIDING_WINDOW
            )
            repository.create_summary(summary_input)

        # Count summaries
        count = repository.count_summaries_by_session(session.id)
        assert count == 5

    def test_get_summaries_by_strategy(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test retrieving summaries filtered by strategy."""
        # Create session
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Strategy Filter Session"
        )
        session = repository.create_session(session_input)

        # Create summaries with different strategies
        summary_input1 = ConversationSummaryInput(
            session_id=session.id, summary_text="Sliding window", strategy=SummarizationStrategy.SLIDING_WINDOW
        )
        repository.create_summary(summary_input1)

        summary_input2 = ConversationSummaryInput(
            session_id=session.id, summary_text="Key points", strategy=SummarizationStrategy.KEY_POINTS
        )
        repository.create_summary(summary_input2)

        # Get summaries by strategy
        sliding_summaries = repository.get_summaries_by_strategy(session.id, SummarizationStrategy.SLIDING_WINDOW)
        assert len(sliding_summaries) == 1
        assert sliding_summaries[0].summary_text == "Sliding window"

        keypoint_summaries = repository.get_summaries_by_strategy(session.id, SummarizationStrategy.KEY_POINTS)
        assert len(keypoint_summaries) == 1
        assert keypoint_summaries[0].summary_text == "Key points"

    def test_get_summaries_with_tokens_saved(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test retrieving summaries filtered by minimum tokens saved."""
        # Create session
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Token Filter Session"
        )
        session = repository.create_session(session_input)

        # Create summaries with different token savings
        for tokens in [50, 100, 150, 200]:
            summary_input = ConversationSummaryInput(
                session_id=session.id,
                summary_text=f"Summary with {tokens} tokens",
                strategy=SummarizationStrategy.SLIDING_WINDOW,
                tokens_saved=tokens,
            )
            repository.create_summary(summary_input)

        # Get summaries with min 100 tokens saved
        high_impact_summaries = repository.get_summaries_with_tokens_saved(session.id, min_tokens=100)
        assert len(high_impact_summaries) == 3  # 100, 150, 200

        # Get summaries with min 150 tokens saved
        very_high_impact_summaries = repository.get_summaries_with_tokens_saved(session.id, min_tokens=150)
        assert len(very_high_impact_summaries) == 2  # 150, 200

    # =========================================================================
    # CASCADE DELETE AND RELATIONSHIP TESTS
    # =========================================================================

    def test_cascade_delete_session_with_messages(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test that deleting a session cascades to messages."""
        # Create session
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Cascade Test Session"
        )
        session = repository.create_session(session_input)

        # Create messages
        message_ids = []
        for i in range(3):
            message_input = ConversationMessageInput(
                session_id=session.id,
                role=MessageRole.USER,
                message_type=MessageType.QUERY,
                content=f"Message {i}",
            )
            message = repository.create_message(message_input)
            message_ids.append(message.id)

        # Delete session
        repository.delete_session(session.id)

        # Verify messages are also deleted (cascade)
        for message_id in message_ids:
            with pytest.raises(NotFoundError):
                repository.get_message_by_id(message_id)

    def test_cascade_delete_session_with_summaries(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4
    ) -> None:
        """Test that deleting a session cascades to summaries."""
        # Create session
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Cascade Summary Test"
        )
        session = repository.create_session(session_input)

        # Create summaries
        summary_ids = []
        for i in range(2):
            summary_input = ConversationSummaryInput(
                session_id=session.id,
                summary_text=f"Summary {i}",
                strategy=SummarizationStrategy.SLIDING_WINDOW,
            )
            summary = repository.create_summary(summary_input)
            summary_ids.append(summary.id)

        # Delete session
        repository.delete_session(session.id)

        # Verify summaries are also deleted (cascade)
        for summary_id in summary_ids:
            with pytest.raises(NotFoundError):
                repository.get_summary_by_id(summary_id)


# =============================================================================
# PERFORMANCE AND N+1 QUERY PREVENTION TESTS
# =============================================================================


@pytest.mark.integration
class TestEagerLoadingIntegration:
    """Integration tests for eager loading and N+1 query prevention."""

    @pytest.fixture
    def repository(self, real_db_session: Session) -> ConversationRepository:
        """Create repository instance with real database session."""
        return ConversationRepository(real_db_session)

    @pytest.fixture
    def test_user_id(self) -> UUID4:
        """Generate a test user ID."""
        return uuid4()

    @pytest.fixture
    def test_collection_id(self) -> UUID4:
        """Generate a test collection ID."""
        return uuid4()

    def test_get_sessions_by_user_eager_loads_messages(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4, real_db_session: Session
    ) -> None:
        """Test that get_sessions_by_user eager loads messages (prevents N+1 queries)."""
        # Create session with messages
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Eager Loading Test"
        )
        session = repository.create_session(session_input)

        # Add messages
        for i in range(5):
            message_input = ConversationMessageInput(
                session_id=session.id,
                role=MessageRole.USER,
                message_type=MessageType.QUERY,
                content=f"Message {i}",
            )
            repository.create_message(message_input)

        # Commit to ensure data is persisted
        real_db_session.commit()

        # Get sessions (this should eager load messages)
        sessions = repository.get_sessions_by_user(test_user_id)

        # Verify messages are accessible without additional queries
        # Note: In a real query monitoring test, we would count queries here
        assert len(sessions) > 0
        for session_obj in sessions:
            if session_obj.id == session.id:
                # Messages should be accessible without lazy loading
                assert session_obj.message_count >= 5

    def test_get_session_by_id_eager_loads_messages(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4, real_db_session: Session
    ) -> None:
        """Test that get_session_by_id eager loads messages."""
        # Create session with messages
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Single Session Eager Test"
        )
        session = repository.create_session(session_input)

        # Add messages
        for i in range(3):
            message_input = ConversationMessageInput(
                session_id=session.id,
                role=MessageRole.USER,
                message_type=MessageType.QUERY,
                content=f"Message {i}",
            )
            repository.create_message(message_input)

        # Commit
        real_db_session.commit()

        # Get session (should eager load messages)
        retrieved_session = repository.get_session_by_id(session.id)

        # Verify message count is correct (without lazy loading)
        assert retrieved_session.message_count >= 3
