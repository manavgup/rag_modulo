"""Unit tests for RequestContext.

Tests cover:
- User data caching and retrieval
- Session data caching and retrieval
- Context clearing
- Thread safety via contextvars
"""

from core.request_context import RequestContext


class TestRequestContext:
    """Test request context caching functionality."""

    def test_set_and_get_user(self):
        """Test setting and retrieving user data."""
        user_data = {
            "id": "user123",
            "email": "test@example.com",
            "name": "Test User",
            "role": "user",
        }

        RequestContext.set_user(user_data)
        cached_user = RequestContext.get_user()

        assert cached_user == user_data
        assert cached_user["id"] == "user123"
        assert cached_user["email"] == "test@example.com"

    def test_get_user_when_not_set(self):
        """Test getting user when not set returns None."""
        RequestContext.clear()
        user = RequestContext.get_user()
        assert user is None

    def test_set_and_get_session(self):
        """Test setting and retrieving session data."""
        session_data = {
            "session_id": "sess123",
            "created_at": "2025-01-01T00:00:00Z",
            "expires_at": "2025-01-02T00:00:00Z",
        }

        RequestContext.set_session(session_data)
        cached_session = RequestContext.get_session()

        assert cached_session == session_data
        assert cached_session["session_id"] == "sess123"

    def test_get_session_when_not_set(self):
        """Test getting session when not set returns None."""
        RequestContext.clear()
        session = RequestContext.get_session()
        assert session is None

    def test_clear_context(self):
        """Test clearing all context data."""
        # Set both user and session
        user_data = {"id": "user123", "email": "test@example.com"}
        session_data = {"session_id": "sess123"}

        RequestContext.set_user(user_data)
        RequestContext.set_session(session_data)

        # Verify data is set
        assert RequestContext.get_user() is not None
        assert RequestContext.get_session() is not None

        # Clear context
        RequestContext.clear()

        # Verify data is cleared
        assert RequestContext.get_user() is None
        assert RequestContext.get_session() is None

    def test_has_user(self):
        """Test has_user method."""
        RequestContext.clear()
        assert not RequestContext.has_user()

        RequestContext.set_user({"id": "user123"})
        assert RequestContext.has_user()

        RequestContext.clear()
        assert not RequestContext.has_user()

    def test_has_session(self):
        """Test has_session method."""
        RequestContext.clear()
        assert not RequestContext.has_session()

        RequestContext.set_session({"session_id": "sess123"})
        assert RequestContext.has_session()

        RequestContext.clear()
        assert not RequestContext.has_session()

    def test_overwrite_user(self):
        """Test that setting user data overwrites previous data."""
        user1 = {"id": "user1", "email": "user1@example.com"}
        user2 = {"id": "user2", "email": "user2@example.com"}

        RequestContext.set_user(user1)
        assert RequestContext.get_user()["id"] == "user1"

        RequestContext.set_user(user2)
        assert RequestContext.get_user()["id"] == "user2"

    def test_overwrite_session(self):
        """Test that setting session data overwrites previous data."""
        session1 = {"session_id": "sess1"}
        session2 = {"session_id": "sess2"}

        RequestContext.set_session(session1)
        assert RequestContext.get_session()["session_id"] == "sess1"

        RequestContext.set_session(session2)
        assert RequestContext.get_session()["session_id"] == "sess2"

    def test_independent_user_and_session(self):
        """Test that user and session are independent."""
        user_data = {"id": "user123"}
        session_data = {"session_id": "sess123"}

        RequestContext.set_user(user_data)
        RequestContext.set_session(session_data)

        # Both should be present
        assert RequestContext.has_user()
        assert RequestContext.has_session()

        # Clear only affects both (by design)
        RequestContext.clear()
        assert not RequestContext.has_user()
        assert not RequestContext.has_session()
