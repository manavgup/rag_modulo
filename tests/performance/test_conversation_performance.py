"""Performance benchmark tests for unified ConversationRepository.

These tests verify:
- N+1 query prevention through eager loading
- Response time improvements
- Query count optimization
- Performance regression detection

Target Metrics (from Issue #539):
- List sessions: 54 queries → 1 query (98% reduction)
- Response time: 156ms → 3ms (98% improvement)
"""

import time
from uuid import uuid4

import pytest
from pydantic import UUID4
from sqlalchemy import event
from sqlalchemy.orm import Session

from rag_solution.repository.conversation_repository import ConversationRepository
from rag_solution.schemas.conversation_schema import (
    ConversationMessageInput,
    ConversationSessionInput,
    MessageRole,
    MessageType,
)


class QueryCounter:
    """Helper class to count database queries."""

    def __init__(self, session: Session) -> None:
        """Initialize query counter.

        Args:
            session: SQLAlchemy session to monitor
        """
        self.session = session
        self.query_count = 0
        self.queries: list[str] = []

    def __enter__(self) -> "QueryCounter":
        """Start monitoring queries."""
        event.listen(self.session.bind, "before_cursor_execute", self._before_cursor_execute)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop monitoring queries."""
        event.remove(self.session.bind, "before_cursor_execute", self._before_cursor_execute)

    def _before_cursor_execute(
        self, conn, cursor, statement, parameters, context, executemany
    ) -> None:
        """Record each query execution."""
        self.query_count += 1
        self.queries.append(statement)

    def reset(self) -> None:
        """Reset query counter."""
        self.query_count = 0
        self.queries = []


@pytest.mark.performance
@pytest.mark.integration
class TestConversationRepositoryPerformance:
    """Performance benchmark tests for ConversationRepository."""

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

    @pytest.fixture
    def populated_sessions(
        self, repository: ConversationRepository, test_user_id: UUID4, test_collection_id: UUID4, real_db_session: Session
    ) -> list[UUID4]:
        """Create multiple sessions with messages for testing.

        Returns:
            List of session IDs
        """
        session_ids = []
        for i in range(10):
            # Create session
            session_input = ConversationSessionInput(
                user_id=test_user_id, collection_id=test_collection_id, session_name=f"Perf Test Session {i}"
            )
            session = repository.create_session(session_input)
            session_ids.append(session.id)

            # Add 5 messages to each session
            for j in range(5):
                message_input = ConversationMessageInput(
                    session_id=session.id,
                    role=MessageRole.USER if j % 2 == 0 else MessageRole.ASSISTANT,
                    message_type=MessageType.QUERY if j % 2 == 0 else MessageType.RESPONSE,
                    content=f"Message {j}",
                    token_count=10,
                )
                repository.create_message(message_input)

        # Commit all data
        real_db_session.commit()
        return session_ids

    # =========================================================================
    # N+1 QUERY PREVENTION TESTS
    # =========================================================================

    def test_get_sessions_by_user_query_count(
        self,
        repository: ConversationRepository,
        test_user_id: UUID4,
        populated_sessions: list[UUID4],
        real_db_session: Session,
    ) -> None:
        """Test that get_sessions_by_user prevents N+1 queries.

        Expected: 1-2 queries regardless of number of sessions.
        Without eager loading: 1 + (3 * N) queries for N sessions.
        """
        # Clear session to force fresh queries
        real_db_session.expunge_all()

        # Count queries
        with QueryCounter(real_db_session) as counter:
            sessions = repository.get_sessions_by_user(test_user_id)

            # Should load all sessions with messages in a single query
            # Allow up to 3 queries (main query + possible relationship queries)
            assert counter.query_count <= 3, f"Expected ≤3 queries, got {counter.query_count}"

            # Verify we got sessions
            assert len(sessions) >= 10

            # Access message counts (should not trigger additional queries)
            counter.reset()
            total_messages = sum(s.message_count for s in sessions)
            assert counter.query_count == 0, "Accessing message_count should not trigger queries"
            assert total_messages >= 50  # 10 sessions * 5 messages

    def test_get_session_by_id_query_count(
        self,
        repository: ConversationRepository,
        populated_sessions: list[UUID4],
        real_db_session: Session,
    ) -> None:
        """Test that get_session_by_id uses minimal queries.

        Expected: 1-2 queries to load session with messages.
        """
        # Clear session
        real_db_session.expunge_all()

        # Count queries
        with QueryCounter(real_db_session) as counter:
            session = repository.get_session_by_id(populated_sessions[0])

            # Should load session and messages in 1-2 queries
            assert counter.query_count <= 2, f"Expected ≤2 queries, got {counter.query_count}"

            # Verify message count is accessible without additional queries
            counter.reset()
            message_count = session.message_count
            assert counter.query_count == 0, "Accessing message_count should not trigger queries"
            assert message_count >= 5

    def test_get_sessions_by_collection_query_count(
        self,
        repository: ConversationRepository,
        test_collection_id: UUID4,
        populated_sessions: list[UUID4],
        real_db_session: Session,
    ) -> None:
        """Test that get_sessions_by_collection prevents N+1 queries.

        Expected: 1-2 queries regardless of number of sessions.
        """
        # Clear session
        real_db_session.expunge_all()

        # Count queries
        with QueryCounter(real_db_session) as counter:
            sessions = repository.get_sessions_by_collection(test_collection_id)

            # Should load all sessions with messages in minimal queries
            assert counter.query_count <= 3, f"Expected ≤3 queries, got {counter.query_count}"
            assert len(sessions) >= 10

    # =========================================================================
    # RESPONSE TIME BENCHMARKS
    # =========================================================================

    def test_get_sessions_by_user_response_time(
        self,
        repository: ConversationRepository,
        test_user_id: UUID4,
        populated_sessions: list[UUID4],
        real_db_session: Session,
    ) -> None:
        """Benchmark response time for get_sessions_by_user.

        Target: < 50ms for 10 sessions (significant improvement from 156ms).
        Note: Target is higher than the documented 3ms to account for test overhead.
        """
        # Clear session and warm up
        real_db_session.expunge_all()
        repository.get_sessions_by_user(test_user_id)
        real_db_session.expunge_all()

        # Benchmark
        start_time = time.perf_counter()
        sessions = repository.get_sessions_by_user(test_user_id)
        end_time = time.perf_counter()

        response_time_ms = (end_time - start_time) * 1000

        # Assert reasonable performance
        assert response_time_ms < 50, f"Response time {response_time_ms:.2f}ms exceeds 50ms target"
        assert len(sessions) >= 10

        # Log performance for monitoring
        print(f"\nget_sessions_by_user: {response_time_ms:.2f}ms for {len(sessions)} sessions")

    def test_get_session_by_id_response_time(
        self,
        repository: ConversationRepository,
        populated_sessions: list[UUID4],
        real_db_session: Session,
    ) -> None:
        """Benchmark response time for get_session_by_id.

        Target: < 10ms per session.
        """
        # Clear session and warm up
        real_db_session.expunge_all()
        repository.get_session_by_id(populated_sessions[0])
        real_db_session.expunge_all()

        # Benchmark
        start_time = time.perf_counter()
        session = repository.get_session_by_id(populated_sessions[0])
        end_time = time.perf_counter()

        response_time_ms = (end_time - start_time) * 1000

        # Assert reasonable performance
        assert response_time_ms < 10, f"Response time {response_time_ms:.2f}ms exceeds 10ms target"
        assert session.message_count >= 5

        # Log performance
        print(f"\nget_session_by_id: {response_time_ms:.2f}ms")

    def test_bulk_operations_performance(
        self,
        repository: ConversationRepository,
        test_user_id: UUID4,
        test_collection_id: UUID4,
        real_db_session: Session,
    ) -> None:
        """Benchmark bulk operations (multiple sessions with messages).

        Target: Create 20 sessions with 100 messages in < 1 second.
        """
        start_time = time.perf_counter()

        # Create 20 sessions with 5 messages each
        for i in range(20):
            session_input = ConversationSessionInput(
                user_id=test_user_id, collection_id=test_collection_id, session_name=f"Bulk Session {i}"
            )
            session = repository.create_session(session_input)

            for j in range(5):
                message_input = ConversationMessageInput(
                    session_id=session.id,
                    role=MessageRole.USER,
                    message_type=MessageType.QUERY,
                    content=f"Message {j}",
                    token_count=10,
                )
                repository.create_message(message_input)

        real_db_session.commit()
        end_time = time.perf_counter()

        total_time_s = end_time - start_time
        assert total_time_s < 1.0, f"Bulk operations took {total_time_s:.2f}s, exceeds 1.0s target"

        # Log performance
        print(f"\nBulk create (20 sessions, 100 messages): {total_time_s:.2f}s")

    # =========================================================================
    # SCALABILITY TESTS
    # =========================================================================

    def test_scalability_with_many_messages(
        self,
        repository: ConversationRepository,
        test_user_id: UUID4,
        test_collection_id: UUID4,
        real_db_session: Session,
    ) -> None:
        """Test performance with sessions containing many messages.

        Verify that query count remains constant as message count increases.
        """
        # Create session with 50 messages
        session_input = ConversationSessionInput(
            user_id=test_user_id, collection_id=test_collection_id, session_name="Scalability Test"
        )
        session = repository.create_session(session_input)

        # Add 50 messages
        for i in range(50):
            message_input = ConversationMessageInput(
                session_id=session.id,
                role=MessageRole.USER,
                message_type=MessageType.QUERY,
                content=f"Message {i}",
                token_count=10,
            )
            repository.create_message(message_input)

        real_db_session.commit()
        real_db_session.expunge_all()

        # Benchmark retrieval
        with QueryCounter(real_db_session) as counter:
            retrieved_session = repository.get_session_by_id(session.id)

            # Query count should remain constant regardless of message count
            assert counter.query_count <= 2, f"Expected ≤2 queries, got {counter.query_count}"
            assert retrieved_session.message_count >= 50

    def test_pagination_performance(
        self,
        repository: ConversationRepository,
        test_user_id: UUID4,
        populated_sessions: list[UUID4],
        real_db_session: Session,
    ) -> None:
        """Test that pagination doesn't cause performance degradation."""
        # Clear session
        real_db_session.expunge_all()

        # Test first page
        with QueryCounter(real_db_session) as counter:
            page1 = repository.get_sessions_by_user(test_user_id, limit=5, offset=0)
            page1_queries = counter.query_count

        real_db_session.expunge_all()

        # Test second page
        with QueryCounter(real_db_session) as counter:
            page2 = repository.get_sessions_by_user(test_user_id, limit=5, offset=5)
            page2_queries = counter.query_count

        # Query count should be similar for all pages
        assert abs(page1_queries - page2_queries) <= 1, "Pagination should have consistent query count"
        assert len(page1) >= 5
        assert len(page2) >= 5


@pytest.mark.performance
@pytest.mark.integration
class TestMessagePerformance:
    """Performance tests for message operations."""

    @pytest.fixture
    def repository(self, real_db_session: Session) -> ConversationRepository:
        """Create repository instance."""
        return ConversationRepository(real_db_session)

    @pytest.fixture
    def test_session(
        self, repository: ConversationRepository, real_db_session: Session
    ) -> UUID4:
        """Create a test session."""
        session_input = ConversationSessionInput(
            user_id=uuid4(), collection_id=uuid4(), session_name="Message Performance Test"
        )
        session = repository.create_session(session_input)
        real_db_session.commit()
        return session.id

    def test_get_messages_pagination_performance(
        self,
        repository: ConversationRepository,
        test_session: UUID4,
        real_db_session: Session,
    ) -> None:
        """Test message pagination performance."""
        # Create 100 messages
        for i in range(100):
            message_input = ConversationMessageInput(
                session_id=test_session,
                role=MessageRole.USER,
                message_type=MessageType.QUERY,
                content=f"Message {i}",
                token_count=10,
            )
            repository.create_message(message_input)

        real_db_session.commit()
        real_db_session.expunge_all()

        # Test pagination performance
        start_time = time.perf_counter()
        messages_page1 = repository.get_messages_by_session(test_session, limit=20, offset=0)
        messages_page2 = repository.get_messages_by_session(test_session, limit=20, offset=20)
        end_time = time.perf_counter()

        total_time_ms = (end_time - start_time) * 1000

        # Should be fast even with 100 messages
        assert total_time_ms < 50, f"Pagination took {total_time_ms:.2f}ms, exceeds 50ms target"
        assert len(messages_page1) == 20
        assert len(messages_page2) == 20

    def test_token_usage_calculation_performance(
        self,
        repository: ConversationRepository,
        test_session: UUID4,
        real_db_session: Session,
    ) -> None:
        """Test token usage calculation performance."""
        # Create 50 messages
        for i in range(50):
            message_input = ConversationMessageInput(
                session_id=test_session,
                role=MessageRole.USER,
                message_type=MessageType.QUERY,
                content=f"Message {i}",
                token_count=10,
            )
            repository.create_message(message_input)

        real_db_session.commit()
        real_db_session.expunge_all()

        # Benchmark token usage calculation
        start_time = time.perf_counter()
        total_tokens = repository.get_token_usage_by_session(test_session)
        end_time = time.perf_counter()

        response_time_ms = (end_time - start_time) * 1000

        # Should be fast (aggregation query)
        assert response_time_ms < 20, f"Token calculation took {response_time_ms:.2f}ms"
        assert total_tokens == 500  # 50 messages * 10 tokens
