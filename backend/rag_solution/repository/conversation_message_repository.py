"""Repository for handling ConversationMessage entity database operations."""

from typing import Any

from pydantic import UUID4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from core.custom_exceptions import RepositoryError
from core.logging_utils import get_logger
from rag_solution.core.exceptions import AlreadyExistsError, NotFoundError
from rag_solution.models.conversation_message import ConversationMessage
from rag_solution.schemas.conversation_schema import ConversationMessageInput, ConversationMessageOutput

logger = get_logger(__name__)


class ConversationMessageRepository:
    """Repository for handling ConversationMessage entity database operations."""

    def __init__(self: Any, db: Session) -> None:
        """Initialize with database session."""
        self.db = db

    def create(self, message_input: ConversationMessageInput) -> ConversationMessageOutput:
        """Create a new conversation message.

        Raises:
            RepositoryError: For database errors
            ValidationError: For validation errors
        """
        try:
            message = ConversationMessage(
                session_id=message_input.session_id,
                role=message_input.role,
                message_type=message_input.message_type,
                content=message_input.content,
                message_metadata=message_input.metadata or {},
                token_count=message_input.token_count,
                execution_time=message_input.execution_time,
            )

            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)

            logger.info(f"Created conversation message: {message.id}")
            return ConversationMessageOutput.from_db_message(message)

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating conversation message: {e}")
            raise AlreadyExistsError(
                "configuration", "Conversation message with this configuration already exists", "duplicate"
            ) from e
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating conversation message: {e}")
            raise RepositoryError(f"Failed to create conversation message: {e}") from e

    def get_by_id(self, message_id: UUID4) -> ConversationMessageOutput:
        """Get conversation message by ID.

        Raises:
            NotFoundError: If message not found
            RepositoryError: For other database errors
        """
        try:
            message = (
                self.db.query(ConversationMessage)
                .options(joinedload(ConversationMessage.session))
                .filter(ConversationMessage.id == message_id)
                .first()
            )

            if not message:
                raise NotFoundError(f"Conversation message not found: {message_id}")

            return ConversationMessageOutput.from_db_message(message)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting conversation message {message_id}: {e}")
            raise RepositoryError(f"Failed to get conversation message: {e}") from e

    def get_messages_by_session(
        self, session_id: UUID4, limit: int = 100, offset: int = 0
    ) -> list[ConversationMessageOutput]:
        """Get conversation messages for a session.

        Args:
            session_id: Session ID
            limit: Maximum number of messages to return
            offset: Offset for pagination

        Returns:
            List of conversation messages ordered by creation time
        """
        try:
            messages = (
                self.db.query(ConversationMessage)
                .filter(ConversationMessage.session_id == session_id)
                .order_by(ConversationMessage.created_at.asc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            return [ConversationMessageOutput.from_db_message(message) for message in messages]

        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {e}")
            raise RepositoryError(f"Failed to get messages for session: {e}") from e

    def get_recent_messages(self, session_id: UUID4, count: int = 10) -> list[ConversationMessageOutput]:
        """Get recent conversation messages for a session.

        Args:
            session_id: Session ID
            count: Number of recent messages to return

        Returns:
            List of recent conversation messages ordered by creation time (newest first)
        """
        try:
            messages = (
                self.db.query(ConversationMessage)
                .filter(ConversationMessage.session_id == session_id)
                .order_by(ConversationMessage.created_at.desc())
                .limit(count)
                .all()
            )

            # Reverse to get chronological order
            messages.reverse()
            return [ConversationMessageOutput.from_db_message(message) for message in messages]

        except Exception as e:
            logger.error(f"Error getting recent messages for session {session_id}: {e}")
            raise RepositoryError(f"Failed to get recent messages for session: {e}") from e

    def update(self, message_id: UUID4, updates: dict[str, Any]) -> ConversationMessageOutput:
        """Update conversation message.

        Args:
            message_id: Message ID to update
            updates: Dictionary of fields to update

        Raises:
            NotFoundError: If message not found
            RepositoryError: For other database errors
        """
        try:
            message = self.db.query(ConversationMessage).filter(ConversationMessage.id == message_id).first()

            if not message:
                raise NotFoundError(f"Conversation message not found: {message_id}")

            # Update allowed fields
            allowed_fields = {"content", "message_metadata", "token_count", "execution_time"}
            for field, value in updates.items():
                if field in allowed_fields and hasattr(message, field):
                    setattr(message, field, value)

            self.db.commit()
            self.db.refresh(message)

            logger.info(f"Updated conversation message: {message_id}")
            return ConversationMessageOutput.from_db_message(message)

        except NotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating conversation message {message_id}: {e}")
            raise RepositoryError(f"Failed to update conversation message: {e}") from e

    def delete(self, message_id: UUID4) -> bool:
        """Delete conversation message.

        Args:
            message_id: Message ID to delete

        Returns:
            True if deleted successfully

        Raises:
            NotFoundError: If message not found
            RepositoryError: For other database errors
        """
        try:
            message = self.db.query(ConversationMessage).filter(ConversationMessage.id == message_id).first()

            if not message:
                raise NotFoundError(f"Conversation message not found: {message_id}")

            self.db.delete(message)
            self.db.commit()

            logger.info(f"Deleted conversation message: {message_id}")
            return True

        except NotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting conversation message {message_id}: {e}")
            raise RepositoryError(f"Failed to delete conversation message: {e}") from e

    def delete_messages_by_session(self, session_id: UUID4) -> int:
        """Delete all messages for a session.

        Args:
            session_id: Session ID

        Returns:
            Number of messages deleted

        Raises:
            RepositoryError: For database errors
        """
        try:
            deleted_count = (
                self.db.query(ConversationMessage).filter(ConversationMessage.session_id == session_id).delete()
            )

            self.db.commit()
            logger.info(f"Deleted {deleted_count} messages for session: {session_id}")
            return deleted_count

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting messages for session {session_id}: {e}")
            raise RepositoryError(f"Failed to delete messages for session: {e}") from e

    def get_token_usage_by_session(self, session_id: UUID4) -> int:
        """Get total token usage for a session.

        Args:
            session_id: Session ID

        Returns:
            Total token count for the session
        """
        try:
            from sqlalchemy import func

            result = (
                self.db.query(func.sum(ConversationMessage.token_count))
                .filter(ConversationMessage.session_id == session_id)
                .scalar()
            )

            return result or 0

        except Exception as e:
            logger.error(f"Error getting token usage for session {session_id}: {e}")
            raise RepositoryError(f"Failed to get token usage for session: {e}") from e
