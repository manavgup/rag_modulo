"""DEPRECATED: This repository will be removed in Phase 7.

Use rag_solution.repository.conversation_repository.ConversationRepository instead.
This file is maintained for backward compatibility during Phases 3-6.
"""

import warnings
from typing import Any

from pydantic import UUID4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from core.custom_exceptions import RepositoryError
from core.logging_utils import get_logger
from rag_solution.core.exceptions import AlreadyExistsError, NotFoundError
from rag_solution.models.conversation_session import ConversationSession
from rag_solution.schemas.conversation_schema import ConversationSessionInput, ConversationSessionOutput

# Issue deprecation warning when this module is imported
warnings.warn(
    "conversation_session_repository.py is deprecated and will be removed in Phase 7. "
    "Use rag_solution.repository.conversation_repository.ConversationRepository instead.",
    DeprecationWarning,
    stacklevel=2,
)

logger = get_logger(__name__)


class ConversationSessionRepository:
    """Repository for handling ConversationSession entity database operations."""

    def __init__(self: Any, db: Session) -> None:
        """Initialize with database session."""
        self.db = db

    def create(self, session_input: ConversationSessionInput) -> ConversationSessionOutput:
        """Create a new conversation session.

        Raises:
            RepositoryError: For database errors
            ValidationError: For validation errors
        """
        try:
            session = ConversationSession(
                user_id=session_input.user_id,
                collection_id=session_input.collection_id,
                session_name=session_input.session_name,
                context_window_size=session_input.context_window_size,
                max_messages=session_input.max_messages,
                session_metadata=session_input.metadata or {},
            )

            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)

            logger.info(f"Created conversation session: {session.id}")
            return ConversationSessionOutput.from_db_session(
                session, message_count=len(session.messages) if hasattr(session, "messages") else 0
            )

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating conversation session: {e}")
            raise AlreadyExistsError(
                "configuration", "Conversation session with this configuration already exists", "duplicate"
            ) from e
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating conversation session: {e}")
            raise RepositoryError(f"Failed to create conversation session: {e}") from e

    def get_by_id(self, session_id: UUID4) -> ConversationSessionOutput:
        """Get conversation session by ID with eager loading to prevent N+1 queries.

        Raises:
            NotFoundError: If session not found
            RepositoryError: For other database errors
        """
        try:
            logger.info(f"🔍 REPOSITORY DEBUG: Getting conversation session {session_id}")
            session = (
                self.db.query(ConversationSession)
                .options(
                    joinedload(ConversationSession.messages),
                    joinedload(ConversationSession.user),
                    joinedload(ConversationSession.collection),
                )
                .filter(ConversationSession.id == session_id)
                .first()
            )

            if not session:
                raise NotFoundError(f"Conversation session not found: {session_id}")

            logger.info(f"🔍 REPOSITORY DEBUG: Found session {session_id}, type: {type(session)}")
            logger.info(f"🔍 REPOSITORY DEBUG: Session status: {session.status}, type: {type(session.status)}")
            logger.info(f"🔍 REPOSITORY DEBUG: Session messages count: {len(session.messages)}")
            logger.info("🔍 REPOSITORY DEBUG: About to call ConversationSessionOutput.from_db_session")

            result = ConversationSessionOutput.from_db_session(session, message_count=len(session.messages))

            logger.info("🔍 REPOSITORY DEBUG: Successfully created ConversationSessionOutput")
            return result

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"🔍 REPOSITORY DEBUG: Exception in get_by_id: {e}")
            logger.error(f"🔍 REPOSITORY DEBUG: Exception type: {type(e)}")
            logger.error(f"Error getting conversation session {session_id}: {e}")
            raise RepositoryError(f"Failed to get conversation session: {e}") from e

    def get_sessions_by_user(self, user_id: UUID4, limit: int = 50, offset: int = 0) -> list[ConversationSessionOutput]:
        """Get conversation sessions for a user with eager loading to prevent N+1 queries.

        Args:
            user_id: User ID
            limit: Maximum number of sessions to return
            offset: Offset for pagination

        Returns:
            List of conversation sessions
        """
        try:
            sessions = (
                self.db.query(ConversationSession)
                .options(
                    joinedload(ConversationSession.messages),
                    joinedload(ConversationSession.user),
                    joinedload(ConversationSession.collection),
                )
                .filter(ConversationSession.user_id == user_id)
                .order_by(ConversationSession.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            return [
                ConversationSessionOutput.from_db_session(
                    session, message_count=len(session.messages) if hasattr(session, "messages") else 0
                )
                for session in sessions
            ]

        except Exception as e:
            logger.error(f"Error getting sessions for user {user_id}: {e}")
            raise RepositoryError(f"Failed to get sessions for user: {e}") from e

    def update(self, session_id: UUID4, updates: dict[str, Any]) -> ConversationSessionOutput:
        """Update conversation session with eager loading to prevent N+1 queries.

        Args:
            session_id: Session ID to update
            updates: Dictionary of fields to update

        Raises:
            NotFoundError: If session not found
            RepositoryError: For other database errors
        """
        try:
            session = (
                self.db.query(ConversationSession)
                .options(
                    joinedload(ConversationSession.messages),
                    joinedload(ConversationSession.user),
                    joinedload(ConversationSession.collection),
                )
                .filter(ConversationSession.id == session_id)
                .first()
            )

            if not session:
                raise NotFoundError(f"Conversation session not found: {session_id}")

            # Update allowed fields
            allowed_fields = {"session_name", "context_window_size", "max_messages", "session_metadata", "status"}
            for field, value in updates.items():
                if field in allowed_fields and hasattr(session, field):
                    setattr(session, field, value)

            self.db.commit()
            self.db.refresh(session)

            logger.info(f"Updated conversation session: {session_id}")
            return ConversationSessionOutput.from_db_session(
                session, message_count=len(session.messages) if hasattr(session, "messages") else 0
            )

        except NotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating conversation session {session_id}: {e}")
            raise RepositoryError(f"Failed to update conversation session: {e}") from e

    def delete(self, session_id: UUID4) -> bool:
        """Delete conversation session.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted successfully

        Raises:
            NotFoundError: If session not found
            RepositoryError: For other database errors
        """
        try:
            session = self.db.query(ConversationSession).filter(ConversationSession.id == session_id).first()

            if not session:
                raise NotFoundError(f"Conversation session not found: {session_id}")

            self.db.delete(session)
            self.db.commit()

            logger.info(f"Deleted conversation session: {session_id}")
            return True

        except NotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting conversation session {session_id}: {e}")
            raise RepositoryError(f"Failed to delete conversation session: {e}") from e

    def get_sessions_by_collection(
        self, collection_id: UUID4, limit: int = 50, offset: int = 0
    ) -> list[ConversationSessionOutput]:
        """Get conversation sessions for a collection with eager loading to prevent N+1 queries.

        Args:
            collection_id: Collection ID
            limit: Maximum number of sessions to return
            offset: Offset for pagination

        Returns:
            List of conversation sessions
        """
        try:
            sessions = (
                self.db.query(ConversationSession)
                .options(
                    joinedload(ConversationSession.messages),
                    joinedload(ConversationSession.user),
                    joinedload(ConversationSession.collection),
                )
                .filter(ConversationSession.collection_id == collection_id)
                .order_by(ConversationSession.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            return [
                ConversationSessionOutput.from_db_session(
                    session, message_count=len(session.messages) if hasattr(session, "messages") else 0
                )
                for session in sessions
            ]

        except Exception as e:
            logger.error(f"Error getting sessions for collection {collection_id}: {e}")
            raise RepositoryError(f"Failed to get sessions for collection: {e}") from e
