"""Repository for handling ConversationSummary entity database operations."""

from typing import Any

from core.custom_exceptions import RepositoryError
from core.logging_utils import get_logger
from pydantic import UUID4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from rag_solution.core.exceptions import AlreadyExistsError, NotFoundError
from rag_solution.models.conversation_summary import ConversationSummary
from rag_solution.schemas.conversation_schema import (
    ConversationSummaryInput,
    ConversationSummaryOutput,
    SummarizationStrategy,
)

logger = get_logger(__name__)


class ConversationSummaryRepository:
    """Repository for handling ConversationSummary entity database operations."""

    def __init__(self, db: Session) -> None:
        """Initialize with database session."""
        self.db = db

    def create(self, summary_input: ConversationSummaryInput) -> ConversationSummaryOutput:
        """Create a new conversation summary.

        Args:
            summary_input: Summary input data

        Returns:
            Created conversation summary output

        Raises:
            RepositoryError: For database errors
            AlreadyExistsError: If summary already exists
        """
        try:
            summary = ConversationSummary(
                session_id=summary_input.session_id,
                summary_text="Summary being generated...",  # Placeholder text that will be updated by the service
                summarized_message_count=summary_input.message_count_to_summarize,
                tokens_saved=0,  # Will be calculated by the service
                key_topics=[],
                important_decisions=[],
                unresolved_questions=[],
                summary_strategy=summary_input.strategy.value,
                summary_metadata={
                    "preserve_context": summary_input.preserve_context,
                    "include_decisions": summary_input.include_decisions,
                    "include_questions": summary_input.include_questions,
                },
            )

            self.db.add(summary)
            self.db.commit()
            self.db.refresh(summary)

            logger.info(f"Created conversation summary: {summary.id}")
            return ConversationSummaryOutput.from_db_summary(summary)

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating conversation summary: {e}")
            raise AlreadyExistsError(
                "summary", "Conversation summary for this session already exists", "duplicate"
            ) from e
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating conversation summary: {e}")
            raise RepositoryError(f"Failed to create conversation summary: {e}") from e

    def get_by_id(self, summary_id: UUID4) -> ConversationSummaryOutput:
        """Get conversation summary by ID.

        Args:
            summary_id: Summary ID

        Returns:
            Conversation summary output

        Raises:
            NotFoundError: If summary not found
            RepositoryError: For other database errors
        """
        try:
            summary = (
                self.db.query(ConversationSummary)
                .options(joinedload(ConversationSummary.session))
                .filter(ConversationSummary.id == summary_id)
                .first()
            )

            if not summary:
                raise NotFoundError(f"Conversation summary not found: {summary_id}")

            return ConversationSummaryOutput.from_db_summary(summary)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting conversation summary {summary_id}: {e}")
            raise RepositoryError(f"Failed to get conversation summary: {e}") from e

    def get_by_session_id(self, session_id: UUID4, limit: int = 10, offset: int = 0) -> list[ConversationSummaryOutput]:
        """Get conversation summaries for a session.

        Args:
            session_id: Session ID
            limit: Maximum number of summaries to return
            offset: Offset for pagination

        Returns:
            List of conversation summaries ordered by creation date (newest first)

        Raises:
            RepositoryError: For database errors
        """
        try:
            summaries = (
                self.db.query(ConversationSummary)
                .filter(ConversationSummary.session_id == session_id)
                .order_by(ConversationSummary.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            return [ConversationSummaryOutput.from_db_summary(summary) for summary in summaries]

        except Exception as e:
            logger.error(f"Error getting summaries for session {session_id}: {e}")
            raise RepositoryError(f"Failed to get summaries for session: {e}") from e

    def get_latest_by_session_id(self, session_id: UUID4) -> ConversationSummaryOutput | None:
        """Get the latest conversation summary for a session.

        Args:
            session_id: Session ID

        Returns:
            Latest conversation summary or None if no summaries exist

        Raises:
            RepositoryError: For database errors
        """
        try:
            summary = (
                self.db.query(ConversationSummary)
                .filter(ConversationSummary.session_id == session_id)
                .order_by(ConversationSummary.created_at.desc())
                .first()
            )

            if not summary:
                return None

            return ConversationSummaryOutput.from_db_summary(summary)

        except Exception as e:
            logger.error(f"Error getting latest summary for session {session_id}: {e}")
            raise RepositoryError(f"Failed to get latest summary for session: {e}") from e

    def update(self, summary_id: UUID4, updates: dict[str, Any]) -> ConversationSummaryOutput:
        """Update conversation summary.

        Args:
            summary_id: Summary ID to update
            updates: Dictionary of fields to update

        Returns:
            Updated conversation summary

        Raises:
            NotFoundError: If summary not found
            RepositoryError: For other database errors
        """
        try:
            summary = self.db.query(ConversationSummary).filter(ConversationSummary.id == summary_id).first()

            if not summary:
                raise NotFoundError(f"Conversation summary not found: {summary_id}")

            # Update allowed fields
            allowed_fields = {
                "summary_text",
                "summarized_message_count",
                "tokens_saved",
                "key_topics",
                "important_decisions",
                "unresolved_questions",
                "summary_strategy",
                "summary_metadata",
            }
            for field, value in updates.items():
                if field in allowed_fields and hasattr(summary, field):
                    setattr(summary, field, value)

            self.db.commit()
            self.db.refresh(summary)

            logger.info(f"Updated conversation summary: {summary_id}")
            return ConversationSummaryOutput.from_db_summary(summary)

        except NotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating conversation summary {summary_id}: {e}")
            raise RepositoryError(f"Failed to update conversation summary: {e}") from e

    def delete(self, summary_id: UUID4) -> bool:
        """Delete conversation summary.

        Args:
            summary_id: Summary ID to delete

        Returns:
            True if deleted successfully

        Raises:
            NotFoundError: If summary not found
            RepositoryError: For other database errors
        """
        try:
            summary = self.db.query(ConversationSummary).filter(ConversationSummary.id == summary_id).first()

            if not summary:
                raise NotFoundError(f"Conversation summary not found: {summary_id}")

            self.db.delete(summary)
            self.db.commit()

            logger.info(f"Deleted conversation summary: {summary_id}")
            return True

        except NotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting conversation summary {summary_id}: {e}")
            raise RepositoryError(f"Failed to delete conversation summary: {e}") from e

    def count_by_session_id(self, session_id: UUID4) -> int:
        """Count conversation summaries for a session.

        Args:
            session_id: Session ID

        Returns:
            Number of summaries for the session

        Raises:
            RepositoryError: For database errors
        """
        try:
            count = self.db.query(ConversationSummary).filter(ConversationSummary.session_id == session_id).count()

            return count

        except Exception as e:
            logger.error(f"Error counting summaries for session {session_id}: {e}")
            raise RepositoryError(f"Failed to count summaries for session: {e}") from e

    def get_by_strategy(
        self, strategy: SummarizationStrategy, limit: int = 50, offset: int = 0
    ) -> list[ConversationSummaryOutput]:
        """Get conversation summaries by strategy.

        Args:
            strategy: Summarization strategy
            limit: Maximum number of summaries to return
            offset: Offset for pagination

        Returns:
            List of conversation summaries with the specified strategy

        Raises:
            RepositoryError: For database errors
        """
        try:
            summaries = (
                self.db.query(ConversationSummary)
                .filter(ConversationSummary.summary_strategy == strategy.value)
                .order_by(ConversationSummary.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            return [ConversationSummaryOutput.from_db_summary(summary) for summary in summaries]

        except Exception as e:
            logger.error(f"Error getting summaries by strategy {strategy}: {e}")
            raise RepositoryError(f"Failed to get summaries by strategy: {e}") from e

    def get_summaries_with_tokens_saved(
        self, min_tokens_saved: int = 100, limit: int = 50, offset: int = 0
    ) -> list[ConversationSummaryOutput]:
        """Get conversation summaries that saved a minimum number of tokens.

        Args:
            min_tokens_saved: Minimum tokens saved threshold
            limit: Maximum number of summaries to return
            offset: Offset for pagination

        Returns:
            List of conversation summaries that saved significant tokens

        Raises:
            RepositoryError: For database errors
        """
        try:
            summaries = (
                self.db.query(ConversationSummary)
                .filter(ConversationSummary.tokens_saved >= min_tokens_saved)
                .order_by(ConversationSummary.tokens_saved.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            return [ConversationSummaryOutput.from_db_summary(summary) for summary in summaries]

        except Exception as e:
            logger.error(f"Error getting summaries with min tokens saved {min_tokens_saved}: {e}")
            raise RepositoryError(f"Failed to get summaries with tokens saved: {e}") from e
