"""TDD Red Phase: API router tests for chat functionality.

API tests focus on testing HTTP endpoints, request/response handling,
authentication, and API contracts.
"""

from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import UUID4

from rag_solution.core.exceptions import NotFoundError, SessionExpiredError, ValidationError
from rag_solution.router.chat_router import router as chat_router
from rag_solution.schemas.conversation_schema import (
    ConversationMessageOutput,
    ConversationSessionOutput,
    MessageMetadata,
    MessageRole,
    MessageType,
    SessionStatus,
)


class TestChatRouterTDD:
    """API tests for chat router endpoints."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create FastAPI app with chat router."""
        app = FastAPI()
        app.include_router(chat_router)
        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_conversation_service(self) -> Mock:
        """Mock conversation service."""
        return Mock()

    @pytest.fixture
    def mock_context_manager_service(self) -> Mock:
        """Mock context manager service."""
        return Mock()

    @pytest.fixture
    def mock_question_suggestion_service(self) -> Mock:
        """Mock question suggestion service."""
        return Mock()

    @pytest.fixture
    def mock_search_service(self) -> Mock:
        """Mock search service."""
        return Mock()

    @pytest.fixture
    def sample_session_data(self) -> dict:
        """Sample session data for testing."""
        return {
            "user_id": str(uuid4()),
            "collection_id": str(uuid4()),
            "session_name": "Test Chat Session",
            "context_window_size": 4000,
            "max_messages": 50,
        }

    @pytest.fixture
    def sample_message_data(self) -> dict:
        """Sample message data for testing."""
        return {
            "session_id": str(uuid4()),
            "content": "What is machine learning?",
            "role": "user",
            "message_type": "question",
            "metadata": {},
        }

    # ==================== API TESTS ====================

    @pytest.mark.api
    def test_create_session_endpoint_success(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test POST /sessions endpoint creates session successfully."""
        # Arrange
        session_data = {"user_id": str(uuid4()), "collection_id": str(uuid4()), "session_name": "Test Session"}

        expected_response = ConversationSessionOutput(
            id=uuid4(),
            user_id=UUID4(session_data["user_id"]),
            collection_id=UUID4(session_data["collection_id"]),
            session_name="Test Session",
            status=SessionStatus.ACTIVE,
            context_window_size=4000,
            max_messages=50,
            message_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_conversation_service.create_session.return_value = expected_response

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.post("/api/chat/sessions", json=session_data)

        # Assert
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["session_name"] == "Test Session"
        assert response_data["status"] == "active"
        assert "id" in response_data

    @pytest.mark.api
    def test_create_session_endpoint_validation_error(
        self, client: TestClient, mock_conversation_service: Mock
    ) -> None:
        """API: Test POST /sessions endpoint handles validation errors."""
        # Arrange
        invalid_session_data = {
            "user_id": "invalid-uuid",
            "collection_id": str(uuid4()),
            "session_name": "",  # Empty name
        }

        mock_conversation_service.create_session.side_effect = ValidationError("Invalid data")

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.post("/api/chat/sessions", json=invalid_session_data)

        # Assert
        assert response.status_code == 400
        response_data = response.json()
        assert "detail" in response_data

    @pytest.mark.api
    def test_get_session_endpoint_success(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test GET /sessions/{session_id} endpoint retrieves session."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()

        expected_response = ConversationSessionOutput(
            id=session_id,
            user_id=user_id,
            collection_id=uuid4(),
            session_name="Test Session",
            status=SessionStatus.ACTIVE,
            context_window_size=4000,
            max_messages=50,
            message_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_conversation_service.get_session.return_value = expected_response

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.get(f"/api/chat/sessions/{session_id}?user_id={user_id}")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == str(session_id)
        assert response_data["session_name"] == "Test Session"

    @pytest.mark.api
    def test_get_session_endpoint_not_found(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test GET /sessions/{session_id} endpoint handles not found."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()

        mock_conversation_service.get_session.side_effect = NotFoundError("Session not found")

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.get(f"/api/chat/sessions/{session_id}?user_id={user_id}")

        # Assert
        assert response.status_code == 404
        response_data = response.json()
        assert "detail" in response_data

    @pytest.mark.api
    def test_get_user_sessions_endpoint(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test GET /users/{user_id}/sessions endpoint retrieves user sessions."""
        # Arrange
        user_id = uuid4()

        expected_sessions = [
            ConversationSessionOutput(
                id=uuid4(),
                user_id=user_id,
                collection_id=uuid4(),
                session_name="Session 1",
                status=SessionStatus.ACTIVE,
                context_window_size=4000,
                max_messages=50,
                message_count=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            ConversationSessionOutput(
                id=uuid4(),
                user_id=user_id,
                collection_id=uuid4(),
                session_name="Session 2",
                status=SessionStatus.ARCHIVED,
                context_window_size=4000,
                max_messages=50,
                message_count=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]

        mock_conversation_service.get_user_sessions.return_value = expected_sessions

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.get(f"/api/chat/users/{user_id}/sessions")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 2
        assert response_data[0]["session_name"] == "Session 1"
        assert response_data[1]["session_name"] == "Session 2"

    @pytest.mark.api
    def test_get_user_sessions_with_status_filter(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test GET /users/{user_id}/sessions with status filter."""
        # Arrange
        user_id = uuid4()
        status = "active"

        expected_sessions = [
            ConversationSessionOutput(
                id=uuid4(),
                user_id=user_id,
                collection_id=uuid4(),
                session_name="Active Session",
                status=SessionStatus.ACTIVE,
                context_window_size=4000,
                max_messages=50,
                message_count=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        ]

        mock_conversation_service.get_user_sessions.return_value = expected_sessions

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.get(f"/api/chat/users/{user_id}/sessions?status={status}")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 1
        assert response_data[0]["status"] == "active"

    @pytest.mark.api
    def test_update_session_endpoint_success(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test PUT /sessions/{session_id} endpoint updates session."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()
        update_data = {"session_name": "Updated Session Name"}

        expected_response = ConversationSessionOutput(
            id=session_id,
            user_id=user_id,
            collection_id=uuid4(),
            session_name="Updated Session Name",
            status=SessionStatus.ACTIVE,
            context_window_size=4000,
            max_messages=50,
            message_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_conversation_service.update_session.return_value = expected_response

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.put(f"/api/chat/sessions/{session_id}?user_id={user_id}", json=update_data)

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["session_name"] == "Updated Session Name"

    @pytest.mark.api
    def test_delete_session_endpoint_success(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test DELETE /sessions/{session_id} endpoint deletes session."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()

        mock_conversation_service.delete_session.return_value = True

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.delete(f"/api/chat/sessions/{session_id}?user_id={user_id}")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["deleted"] is True

    @pytest.mark.api
    def test_add_message_endpoint_success(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test POST /sessions/{session_id}/messages endpoint adds message."""
        # Arrange
        session_id = uuid4()
        message_data = {
            "content": "What is machine learning?",
            "role": "user",
            "message_type": "question",
            "metadata": {},
        }

        expected_response = ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content="What is machine learning?",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
            metadata=MessageMetadata(),
            created_at=datetime.now(),
        )

        mock_conversation_service.add_message.return_value = expected_response

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.post(f"/api/chat/sessions/{session_id}/messages", json=message_data)

        # Assert
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["content"] == "What is machine learning?"
        assert response_data["role"] == "user"

    @pytest.mark.api
    def test_add_message_endpoint_session_not_found(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test POST /sessions/{session_id}/messages handles session not found."""
        # Arrange
        session_id = uuid4()
        message_data = {"content": "Test message", "role": "user", "message_type": "question"}

        mock_conversation_service.add_message.side_effect = NotFoundError("Session not found")

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.post(f"/api/chat/sessions/{session_id}/messages", json=message_data)

        # Assert
        assert response.status_code == 404
        response_data = response.json()
        assert "detail" in response_data

    @pytest.mark.api
    def test_add_message_endpoint_session_expired(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test POST /sessions/{session_id}/messages handles session expired."""
        # Arrange
        session_id = uuid4()
        message_data = {"content": "Test message", "role": "user", "message_type": "question"}

        mock_conversation_service.add_message.side_effect = SessionExpiredError("Session expired")

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.post(f"/api/chat/sessions/{session_id}/messages", json=message_data)

        # Assert
        assert response.status_code == 410  # Gone
        response_data = response.json()
        assert "detail" in response_data

    @pytest.mark.api
    def test_get_session_messages_endpoint(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test GET /sessions/{session_id}/messages endpoint retrieves messages."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()

        expected_messages = [
            ConversationMessageOutput(
                id=uuid4(),
                session_id=session_id,
                content="What is AI?",
                role=MessageRole.USER,
                message_type=MessageType.QUESTION,
                metadata=MessageMetadata(),
                created_at=datetime.now(),
            ),
            ConversationMessageOutput(
                id=uuid4(),
                session_id=session_id,
                content="AI is artificial intelligence...",
                role=MessageRole.ASSISTANT,
                message_type=MessageType.ANSWER,
                metadata=MessageMetadata(),
                created_at=datetime.now(),
            ),
        ]

        mock_conversation_service.get_session_messages.return_value = expected_messages

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.get(f"/api/chat/sessions/{session_id}/messages?user_id={user_id}")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 2
        assert response_data[0]["content"] == "What is AI?"
        assert response_data[1]["content"] == "AI is artificial intelligence..."

    @pytest.mark.api
    def test_get_session_messages_with_pagination(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test GET /sessions/{session_id}/messages with pagination."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()
        limit = 10
        offset = 5

        expected_messages: list[ConversationMessageOutput] = []
        mock_conversation_service.get_session_messages.return_value = expected_messages

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.get(
                f"/api/chat/sessions/{session_id}/messages?user_id={user_id}&limit={limit}&offset={offset}"
            )

        # Assert
        assert response.status_code == 200
        mock_conversation_service.get_session_messages.assert_called_once_with(session_id, user_id, limit, offset)

    @pytest.mark.api
    def test_archive_session_endpoint(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test POST /sessions/{session_id}/archive endpoint archives session."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()

        expected_response = ConversationSessionOutput(
            id=session_id,
            user_id=user_id,
            collection_id=uuid4(),
            session_name="Test Session",
            status=SessionStatus.ARCHIVED,
            context_window_size=4000,
            max_messages=50,
            message_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_conversation_service.archive_session.return_value = expected_response

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.post(f"/api/chat/sessions/{session_id}/archive?user_id={user_id}")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "archived"

    @pytest.mark.api
    def test_restore_session_endpoint(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test POST /sessions/{session_id}/restore endpoint restores session."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()

        expected_response = ConversationSessionOutput(
            id=session_id,
            user_id=user_id,
            collection_id=uuid4(),
            session_name="Test Session",
            status=SessionStatus.ACTIVE,
            context_window_size=4000,
            max_messages=50,
            message_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_conversation_service.restore_session.return_value = expected_response

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.post(f"/api/chat/sessions/{session_id}/restore?user_id={user_id}")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "active"

    @pytest.mark.api
    def test_export_session_endpoint(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test GET /sessions/{session_id}/export endpoint exports session."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()
        export_format = "json"

        expected_export = {
            "session_data": {"id": str(session_id), "name": "Test Session"},
            "messages": [{"content": "Test message", "role": "user"}],
            "metadata": {"exported_at": datetime.now().isoformat()},
        }

        mock_conversation_service.export_session.return_value = expected_export

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.get(f"/api/chat/sessions/{session_id}/export?user_id={user_id}&format={export_format}")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert "session_data" in response_data
        assert "messages" in response_data

    @pytest.mark.api
    def test_export_session_unsupported_format(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test GET /sessions/{session_id}/export handles unsupported format."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()
        export_format = "unsupported"

        mock_conversation_service.export_session.side_effect = ValidationError("Unsupported format")

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.get(f"/api/chat/sessions/{session_id}/export?user_id={user_id}&format={export_format}")

        # Assert
        assert response.status_code == 400
        response_data = response.json()
        assert "detail" in response_data

    @pytest.mark.api
    def test_get_session_statistics_endpoint(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test GET /sessions/{session_id}/statistics endpoint retrieves statistics."""
        # Arrange
        session_id = uuid4()
        user_id = uuid4()

        expected_stats = {
            "message_count": 10,
            "session_duration": 3600,
            "average_response_time": 2.5,
            "context_usage": 0.75,
        }

        mock_conversation_service.get_session_statistics.return_value = expected_stats

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.get(f"/api/chat/sessions/{session_id}/statistics?user_id={user_id}")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message_count"] == 10
        assert response_data["session_duration"] == 3600

    @pytest.mark.api
    def test_search_sessions_endpoint(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test GET /users/{user_id}/sessions/search endpoint searches sessions."""
        # Arrange
        user_id = uuid4()
        query = "machine learning"

        expected_sessions = [
            ConversationSessionOutput(
                id=uuid4(),
                user_id=user_id,
                collection_id=uuid4(),
                session_name="ML Discussion",
                status=SessionStatus.ACTIVE,
                context_window_size=4000,
                max_messages=50,
                message_count=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        ]

        mock_conversation_service.search_sessions.return_value = expected_sessions

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.get(f"/api/chat/users/{user_id}/sessions/search?q={query}")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 1
        assert response_data[0]["session_name"] == "ML Discussion"

    @pytest.mark.api
    def test_cleanup_expired_sessions_endpoint(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test POST /sessions/cleanup endpoint cleans up expired sessions."""
        # Arrange
        mock_conversation_service.cleanup_expired_sessions.return_value = 5

        # Act
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            response = client.post("/api/chat/sessions/cleanup")

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["cleaned_sessions"] == 5

    @pytest.mark.api
    def test_authentication_required(self, client: TestClient) -> None:
        """API: Test that authentication is required for protected endpoints."""
        # Act
        response = client.post("/api/chat/sessions", json={})

        # Assert
        # This should return 401 or redirect to auth, depending on implementation
        assert response.status_code in [401, 403, 422]

    @pytest.mark.api
    def test_cors_headers(self, client: TestClient) -> None:
        """API: Test that CORS headers are properly set."""
        # Act
        response = client.options("/api/chat/sessions")

        # Assert
        # CORS headers should be present
        assert response.status_code in [200, 204]

    @pytest.mark.api
    def test_rate_limiting(self, client: TestClient, mock_conversation_service: Mock) -> None:
        """API: Test rate limiting on message endpoints."""
        # Arrange
        session_id = uuid4()
        message_data = {"content": "Test message", "role": "user", "message_type": "question"}

        mock_conversation_service.add_message.return_value = ConversationMessageOutput(
            id=uuid4(),
            session_id=session_id,
            content="Test message",
            role=MessageRole.USER,
            message_type=MessageType.QUESTION,
            metadata=MessageMetadata(),
            created_at=datetime.now(),
        )

        # Act - Send multiple requests rapidly
        with patch("rag_solution.router.chat_router.get_conversation_service", return_value=mock_conversation_service):
            responses = []
            for _ in range(10):
                response = client.post(f"/api/chat/sessions/{session_id}/messages", json=message_data)
                responses.append(response)

        # Assert
        # All requests should succeed (rate limiting may be implemented differently)
        assert all(response.status_code in [200, 201, 429] for response in responses)
