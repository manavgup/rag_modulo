"""WebSocket router for real-time chat functionality.

This router provides WebSocket endpoints for real-time communication between
the frontend and backend, supporting chat sessions, message streaming, and
live updates.
"""

import json
import logging
from typing import Any
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from auth.oidc import verify_jwt_token
from core.config import get_settings
from core.mock_auth import (
    create_mock_user_data,
    ensure_mock_user_exists,
    is_bypass_mode_active,
    is_mock_token,
)
from rag_solution.core.exceptions import NotFoundError
from rag_solution.file_management.database import get_db
from rag_solution.schemas.conversation_schema import (
    ConversationMessageInput,
    MessageRole,
    MessageType,
)
from rag_solution.services.conversation_service import ConversationService

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self) -> None:
        """Initialize the connection manager."""
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """Accept a WebSocket connection and store it.

        Args:
            websocket: The WebSocket connection
            user_id: The user ID for this connection
        """
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info("WebSocket connection established for user %s", str(user_id))

    def disconnect(self, user_id: str) -> None:
        """Remove a WebSocket connection.

        Args:
            user_id: The user ID to disconnect
        """
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info("WebSocket connection removed for user %s", str(user_id))

    async def send_personal_message(self, message: str, user_id: str) -> None:
        """Send a message to a specific user.

        Args:
            message: The message to send
            user_id: The target user ID
        """
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(message)
            except WebSocketDisconnect:
                logger.warning("Connection closed for user %s, removing from active connections", str(user_id))
                self.disconnect(user_id)

    async def broadcast(self, message: str) -> None:
        """Broadcast a message to all connected users.

        Args:
            message: The message to broadcast
        """
        disconnected_users = []
        for user_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message)
            except WebSocketDisconnect:
                logger.warning("Connection closed for user %s during broadcast", str(user_id))
                disconnected_users.append(user_id)

        # Clean up disconnected users
        for user_id in disconnected_users:
            self.disconnect(user_id)


# Global connection manager instance
manager = ConnectionManager()


def get_conversation_service(db: Session = Depends(get_db)) -> ConversationService:
    """Get conversation service instance."""
    settings = get_settings()
    return ConversationService(db, settings)


async def _handle_ping_message(websocket: WebSocket, message_data: dict[str, Any]) -> None:
    """Handle ping/pong for connection health.

    Args:
        websocket: The WebSocket connection
        message_data: The message data containing timestamp
    """
    pong_response = {"type": "pong", "timestamp": message_data.get("timestamp")}
    await websocket.send_text(json.dumps(pong_response))


def _validate_chat_message_data(message_data: dict[str, Any]) -> tuple[str | None, str | None]:
    """Validate chat message data and extract session_id and content.

    Args:
        message_data: The message data to validate

    Returns:
        Tuple of (session_id, content) or (None, None) if invalid
    """
    session_id = message_data.get("session_id")
    content = message_data.get("content")

    if not session_id or not content:
        return None, None

    return session_id, content


def _extract_sources_from_metadata(response_message: Any) -> list[dict[str, Any]]:
    """Extract sources from response message metadata.

    Args:
        response_message: The response message with metadata

    Returns:
        List of source dictionaries
    """
    sources: list[dict[str, Any]] = []
    if response_message.metadata and hasattr(response_message.metadata, "sources"):
        sources = response_message.metadata.sources or []
    elif response_message.metadata and isinstance(response_message.metadata, dict):
        sources = response_message.metadata.get("sources", [])
    return sources


def _create_ai_response(session_id: str, response_message: Any, sources: list[dict[str, Any]]) -> dict[str, Any]:
    """Create AI response dictionary.

    Args:
        session_id: The session ID
        response_message: The response message object
        sources: List of source documents

    Returns:
        AI response dictionary
    """
    return {
        "type": "ai_response",
        "session_id": session_id,
        "message_id": str(response_message.id),
        "content": response_message.content,
        "sources": sources,
        "token_count": response_message.token_count,
        "timestamp": response_message.created_at.isoformat() if response_message.created_at else None,
    }


async def _process_chat_message(
    websocket: WebSocket,
    session_id: str,
    content: str,
    conversation_service: ConversationService,
) -> None:
    """Process a chat message and send response.

    Args:
        websocket: The WebSocket connection
        session_id: The session ID
        content: The message content
        conversation_service: The conversation service instance
    """
    # Create message input
    message_input = ConversationMessageInput(
        session_id=UUID(session_id),
        content=content,
        role=MessageRole.USER,
        message_type=MessageType.QUESTION,
    )

    # Send acknowledgment that we're processing
    processing_response = {
        "type": "processing",
        "session_id": session_id,
        "message": "Processing your message...",
    }
    await websocket.send_text(json.dumps(processing_response))

    # Process the message and get AI response
    response_message = await conversation_service.process_user_message(message_input)

    # Extract sources from metadata
    sources = _extract_sources_from_metadata(response_message)

    # Create and send the AI response
    ai_response = _create_ai_response(session_id, response_message, sources)
    await websocket.send_text(json.dumps(ai_response))


async def authenticate_websocket(websocket: WebSocket, db: Session) -> dict[str, Any] | None:  # pylint: disable=too-many-return-statements
    """Authenticate WebSocket connection.

    Args:
        websocket: The WebSocket connection
        db: Database session

    Returns:
        User data if authenticated, None otherwise
    """
    # Check for bypass mode (development/testing)
    if is_bypass_mode_active():
        logger.info("WebSocket: Bypass mode active, creating mock user")
        try:
            settings = get_settings()
            user_id = ensure_mock_user_exists(db, settings)
            user_data = create_mock_user_data(str(user_id))
            logger.info("WebSocket: Using mock user: %s", str(user_id))
            return user_data
        except (ValueError, KeyError, AttributeError, NotFoundError) as e:
            logger.error("WebSocket: Failed to create mock user: %s", str(e))
            return None

    # Try to get token from query parameters
    token = websocket.query_params.get("token")
    if not token:
        # Try to get from headers (some WebSocket clients support this)
        auth_header = websocket.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        logger.warning("WebSocket: No authentication token provided")
        return None

    try:
        # Check if this is a mock token
        if is_mock_token(token):
            logger.info("WebSocket: Mock token detected")
            settings = get_settings()
            user_id = ensure_mock_user_exists(db, settings)
            user_data = create_mock_user_data(str(user_id))
            return user_data

        # Verify JWT token
        payload = verify_jwt_token(token)
        user_data = {
            "id": payload.get("sub"),
            "email": payload.get("email"),
            "name": payload.get("name"),
            "uuid": payload.get("uuid"),
            "role": payload.get("role"),
        }
        logger.info("WebSocket: JWT token validated successfully for user: %s", str(user_data.get("user_id")))
        return user_data

    except jwt.ExpiredSignatureError:
        logger.warning("WebSocket: Expired JWT token")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("WebSocket: Invalid JWT token - %s", str(e))
        return None
    except (jwt.PyJWTError, ValueError, KeyError) as e:
        logger.error("WebSocket: Authentication error - %s", str(e))
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    db: Session = Depends(get_db),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> None:
    """WebSocket endpoint for real-time chat.

    This endpoint handles:
    - WebSocket connection establishment
    - Authentication via token parameter or header
    - Real-time message processing
    - Session management
    """
    user_data = await authenticate_websocket(websocket, db)
    if not user_data:
        await websocket.close(code=1008, reason="Authentication failed")
        return

    user_id = user_data["uuid"]
    await manager.connect(websocket, user_id)

    try:
        # Send welcome message
        welcome_message = {
            "type": "connection_established",
            "user_id": user_id,
            "message": "WebSocket connection established successfully",
        }
        await websocket.send_text(json.dumps(welcome_message))

        while True:
            # Wait for message from client
            data = await websocket.receive_text()
            logger.info("WebSocket: Received message from user %s", str(user_id))

            try:
                message_data = json.loads(data)
                message_type = message_data.get("type", "chat_message")

                if message_type == "ping":
                    await _handle_ping_message(websocket, message_data)
                    continue

                if message_type == "chat_message":
                    session_id, content = _validate_chat_message_data(message_data)

                    if not session_id or not content:
                        error_response = {
                            "type": "error",
                            "message": "Missing required fields: session_id and content",
                        }
                        await websocket.send_text(json.dumps(error_response))
                        continue

                    # Process the message through the conversation service
                    try:
                        await _process_chat_message(websocket, session_id, content, conversation_service)

                    except (ValueError, KeyError, AttributeError) as e:
                        logger.error("WebSocket: Error processing message: %s", str(e), exc_info=True)
                        error_response = {
                            "type": "error",
                            "session_id": session_id,
                            "message": f"Processing error: {e}",
                        }
                        await websocket.send_text(json.dumps(error_response))

                else:
                    # Unknown message type
                    error_response = {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                    }
                    await websocket.send_text(json.dumps(error_response))

            except json.JSONDecodeError:
                error_response = {"type": "error", "message": "Invalid JSON format"}
                await websocket.send_text(json.dumps(error_response))

    except WebSocketDisconnect:
        logger.info("WebSocket: User %s disconnected", str(user_id))
        manager.disconnect(user_id)
    except (ValueError, KeyError, AttributeError) as e:
        logger.error("WebSocket: Unexpected error for user %s: %s", str(user_id), str(e), exc_info=True)
        manager.disconnect(user_id)


@router.websocket("/ws/health")
async def websocket_health_check(websocket: WebSocket) -> None:
    """WebSocket health check endpoint.

    Simple endpoint to verify WebSocket functionality is working.
    """
    await websocket.accept()
    try:
        health_response = {
            "type": "health_check",
            "status": "healthy",
            "message": "WebSocket service is operational",
        }
        await websocket.send_text(json.dumps(health_response))
        await websocket.close(code=1000, reason="Health check completed")
    except (ValueError, KeyError, AttributeError) as e:
        logger.error("WebSocket health check error: %s", str(e))
        await websocket.close(code=1011, reason="Health check failed")
