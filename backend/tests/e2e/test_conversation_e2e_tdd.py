"""TDD Red Phase: End-to-end tests for conversation functionality.

E2E tests focus on testing complete user workflows from API to database,
with real dependencies and full system integration.
"""

import pytest
from fastapi.testclient import TestClient

from core.config import get_settings
from core.mock_auth import ensure_mock_user_exists
from main import app
from rag_solution.file_management.database import get_db
from rag_solution.schemas.collection_schema import CollectionInput
from rag_solution.services.collection_service import CollectionService


class TestConversationE2ETDD:
    """End-to-end tests for conversation functionality."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client for E2E testing."""
        return TestClient(app)

    @pytest.fixture
    def test_user_id(self) -> str:
        """Create a real test user in the database for E2E testing."""
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        try:
            settings = get_settings()
            # Create a real user using the mock auth helper
            user_id = ensure_mock_user_exists(db, settings, user_key="default")
            return str(user_id)
        finally:
            db.close()

    @pytest.fixture
    def e2e_settings(self):
        """Create a real settings object for E2E tests using actual environment variables."""
        from core.config import get_settings

        return get_settings()

    @pytest.fixture
    def test_collection_id(self, test_user_id: str, e2e_settings) -> str:
        """Create a real test collection in the database for E2E testing."""
        # Get database session
        db_gen = get_db()
        db = next(db_gen)
        try:
            # Create a test collection
            from datetime import datetime
            from uuid import UUID

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            collection_input = CollectionInput(
                name=f"E2E Conversation Test Collection {timestamp}", is_private=True, users=[UUID(test_user_id)]
            )
            collection_service = CollectionService(db, e2e_settings)
            collection = collection_service.create_collection(collection_input)
            return str(collection.id)
        finally:
            db.close()

    # ==================== E2E TESTS ====================

    @pytest.mark.e2e
    def test_complete_conversation_workflow(
        self, client: TestClient, test_user_id: str, test_collection_id: str
    ) -> None:
        """E2E: Test complete conversation workflow from session creation to deletion."""
        # Step 1: Create a new conversation session
        session_data = {
            "user_id": test_user_id,
            "collection_id": test_collection_id,
            "session_name": "E2E Test Session",
            "context_window_size": 4000,
            "max_messages": 50,
        }

        create_response = client.post("/api/chat/sessions", json=session_data)
        assert create_response.status_code == 200
        session = create_response.json()
        session_id = session["id"]

        # Step 2: Add user message
        user_message = {
            "session_id": session_id,
            "content": "What is artificial intelligence?",
            "role": "user",
            "message_type": "question",
            "metadata": None,
        }

        message_response = client.post(f"/api/chat/sessions/{session_id}/messages", json=user_message)
        assert message_response.status_code == 200
        user_msg = message_response.json()
        assert user_msg["content"] == "What is artificial intelligence?"
        assert user_msg["role"] == "user"

        # Step 3: Add assistant response
        assistant_message = {
            "session_id": session_id,
            "content": "Artificial intelligence (AI) is a branch of computer science that aims to create machines capable of intelligent behavior.",
            "role": "assistant",
            "message_type": "answer",
            "metadata": None,
        }

        assistant_response = client.post(f"/api/chat/sessions/{session_id}/messages", json=assistant_message)
        assert assistant_response.status_code == 200
        assistant_msg = assistant_response.json()
        assert assistant_msg["role"] == "assistant"

        # Step 4: Add follow-up question
        followup_message = {
            "session_id": session_id,
            "content": "Tell me more about machine learning",
            "role": "user",
            "message_type": "follow_up",
            "metadata": None,
        }

        followup_response = client.post(f"/api/chat/sessions/{session_id}/messages", json=followup_message)
        assert followup_response.status_code == 200
        followup_msg = followup_response.json()
        assert followup_msg["content"] == "Tell me more about machine learning"

        # Step 5: Get session messages
        messages_response = client.get(f"/api/chat/sessions/{session_id}/messages?user_id={test_user_id}")
        assert messages_response.status_code == 200
        messages = messages_response.json()
        assert len(messages) == 3
        assert messages[0]["content"] == "What is artificial intelligence?"
        assert (
            messages[1]["content"]
            == "Artificial intelligence (AI) is a branch of computer science that aims to create machines capable of intelligent behavior."
        )
        assert messages[2]["content"] == "Tell me more about machine learning"

        # Step 6: Export session
        export_response = client.get(f"/api/chat/sessions/{session_id}/export?user_id={test_user_id}&format=json")
        assert export_response.status_code == 200
        export_data = export_response.json()
        assert "session_data" in export_data
        assert "messages" in export_data
        assert len(export_data["messages"]) == 3

        # Step 7: Delete session
        delete_response = client.delete(f"/api/chat/sessions/{session_id}?user_id={test_user_id}")
        assert delete_response.status_code == 200
        delete_data = delete_response.json()
        assert delete_data["message"] == "Session deleted successfully"

    @pytest.mark.e2e
    @pytest.mark.skip(reason="Multi-user isolation test requires different auth setup than mock middleware provides")
    def test_multi_user_conversation_isolation(self, client: TestClient, test_collection_id: str) -> None:
        """E2E: Test that conversations are properly isolated between users."""
        # Create two different real users in the database
        db_gen = get_db()
        db = next(db_gen)
        try:
            settings = get_settings()
            # Create real users using the mock auth helper with different keys
            user1_id = str(ensure_mock_user_exists(db, settings, user_key="default"))
            user2_id = str(ensure_mock_user_exists(db, settings, user_key="default"))
        finally:
            db.close()

        # User 1 creates a session
        session1_data = {"user_id": user1_id, "collection_id": test_collection_id, "session_name": "User 1 Session"}
        session1_response = client.post("/api/chat/sessions", json=session1_data)
        assert session1_response.status_code == 200
        session1 = session1_response.json()
        session1_id = session1["id"]

        # User 2 creates a session
        session2_data = {"user_id": user2_id, "collection_id": test_collection_id, "session_name": "User 2 Session"}
        session2_response = client.post("/api/chat/sessions", json=session2_data)
        assert session2_response.status_code == 200
        session2 = session2_response.json()
        session2_id = session2["id"]

        # User 1 adds a message to their session
        user1_message = {
            "session_id": session1_id,
            "content": "User 1 private message",
            "role": "user",
            "message_type": "question",
            "metadata": None,
        }
        user1_msg_response = client.post(f"/api/chat/sessions/{session1_id}/messages", json=user1_message)
        assert user1_msg_response.status_code == 200

        # User 2 adds a message to their session
        user2_message = {
            "session_id": session2_id,
            "content": "User 2 private message",
            "role": "user",
            "message_type": "question",
            "metadata": None,
        }
        user2_msg_response = client.post(f"/api/chat/sessions/{session2_id}/messages", json=user2_message)
        assert user2_msg_response.status_code == 200

        # User 1 tries to access User 2's session (should fail)
        user1_access_user2_response = client.get(f"/api/chat/sessions/{session2_id}?user_id={user1_id}")
        assert user1_access_user2_response.status_code == 404

        # User 2 tries to access User 1's session (should fail)
        user2_access_user1_response = client.get(f"/api/chat/sessions/{session1_id}?user_id={user2_id}")
        assert user2_access_user1_response.status_code == 404

        # Each user can only see their own sessions
        user1_sessions_response = client.get(f"/api/chat/users/{user1_id}/sessions")
        assert user1_sessions_response.status_code == 200
        user1_sessions = user1_sessions_response.json()
        assert len(user1_sessions) == 1
        assert user1_sessions[0]["id"] == session1_id

        user2_sessions_response = client.get(f"/api/chat/users/{user2_id}/sessions")
        assert user2_sessions_response.status_code == 200
        user2_sessions = user2_sessions_response.json()
        assert len(user2_sessions) == 1
        assert user2_sessions[0]["id"] == session2_id
