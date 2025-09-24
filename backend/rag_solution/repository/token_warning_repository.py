"""Repository for handling TokenWarning entity database operations."""

from datetime import datetime
from typing import Any

from core.custom_exceptions import RepositoryError
from core.logging_utils import get_logger
from pydantic import UUID4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rag_solution.core.exceptions import AlreadyExistsError, NotFoundError
from rag_solution.models.token_warning import TokenWarning
from rag_solution.schemas.llm_usage_schema import TokenWarning as TokenWarningSchema

logger = get_logger(__name__)


class TokenWarningRepository:
    """Repository for handling TokenWarning entity database operations."""

    def __init__(self: Any, db: Session) -> None:
        """Initialize with database session."""
        self.db = db

    def create(
        self, warning_data: TokenWarningSchema, user_id: UUID4 | None = None, session_id: str | None = None
    ) -> TokenWarning:
        """Create a new token warning.

        Args:
            warning_data: Token warning schema data
            user_id: Optional user ID
            session_id: Optional session ID

        Returns:
            Created TokenWarning model instance

        Raises:
            RepositoryError: For database errors
        """
        try:
            warning = TokenWarning(
                user_id=user_id,
                session_id=session_id,
                warning_type=warning_data.warning_type.value,
                current_tokens=warning_data.current_tokens,
                limit_tokens=warning_data.limit_tokens,
                percentage_used=warning_data.percentage_used,
                message=warning_data.message,
                severity=warning_data.severity,
                suggested_action=warning_data.suggested_action,
            )

            self.db.add(warning)
            self.db.commit()
            self.db.refresh(warning)

            logger.info(f"Created token warning: {warning.id}")
            return warning

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating token warning: {e}")
            raise AlreadyExistsError(
                "configuration", "Token warning with this configuration already exists", "duplicate"
            ) from e
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating token warning: {e}")
            raise RepositoryError(f"Failed to create token warning: {e}") from e

    def get_by_id(self, warning_id: UUID4) -> TokenWarning:
        """Get token warning by ID.

        Args:
            warning_id: Warning ID

        Returns:
            TokenWarning model instance

        Raises:
            NotFoundError: If warning not found
            RepositoryError: For other database errors
        """
        try:
            warning = self.db.query(TokenWarning).filter(TokenWarning.id == warning_id).first()

            if not warning:
                raise NotFoundError(f"Token warning not found: {warning_id}")

            return warning

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting token warning {warning_id}: {e}")
            raise RepositoryError(f"Failed to get token warning: {e}") from e

    def get_warnings_by_user(
        self, user_id: UUID4, limit: int = 50, offset: int = 0, acknowledged: bool | None = None
    ) -> list[TokenWarning]:
        """Get token warnings for a user.

        Args:
            user_id: User ID
            limit: Maximum number of warnings to return
            offset: Offset for pagination
            acknowledged: Filter by acknowledgment status (None for all)

        Returns:
            List of token warnings ordered by creation time (newest first)
        """
        try:
            query = self.db.query(TokenWarning).filter(TokenWarning.user_id == user_id)

            if acknowledged is not None:
                if acknowledged:
                    query = query.filter(TokenWarning.acknowledged_at.isnot(None))
                else:
                    query = query.filter(TokenWarning.acknowledged_at.is_(None))

            warnings = query.order_by(TokenWarning.created_at.desc()).limit(limit).offset(offset).all()

            return warnings

        except Exception as e:
            logger.error(f"Error getting warnings for user {user_id}: {e}")
            raise RepositoryError(f"Failed to get warnings for user: {e}") from e

    def get_warnings_by_session(self, session_id: str, limit: int = 20, offset: int = 0) -> list[TokenWarning]:
        """Get token warnings for a session.

        Args:
            session_id: Session ID
            limit: Maximum number of warnings to return
            offset: Offset for pagination

        Returns:
            List of token warnings ordered by creation time (newest first)
        """
        try:
            warnings = (
                self.db.query(TokenWarning)
                .filter(TokenWarning.session_id == session_id)
                .order_by(TokenWarning.created_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            return warnings

        except Exception as e:
            logger.error(f"Error getting warnings for session {session_id}: {e}")
            raise RepositoryError(f"Failed to get warnings for session: {e}") from e

    def get_recent_warnings(self, limit: int = 100, severity: str | None = None) -> list[TokenWarning]:
        """Get recent token warnings across all users.

        Args:
            limit: Maximum number of warnings to return
            severity: Filter by severity level (None for all)

        Returns:
            List of recent token warnings ordered by creation time (newest first)
        """
        try:
            query = self.db.query(TokenWarning)

            if severity:
                query = query.filter(TokenWarning.severity == severity)

            warnings = query.order_by(TokenWarning.created_at.desc()).limit(limit).all()

            return warnings

        except Exception as e:
            logger.error(f"Error getting recent warnings: {e}")
            raise RepositoryError(f"Failed to get recent warnings: {e}") from e

    def acknowledge_warning(self, warning_id: UUID4) -> TokenWarning:
        """Mark a token warning as acknowledged.

        Args:
            warning_id: Warning ID to acknowledge

        Returns:
            Updated TokenWarning model instance

        Raises:
            NotFoundError: If warning not found
            RepositoryError: For other database errors
        """
        try:
            warning = self.db.query(TokenWarning).filter(TokenWarning.id == warning_id).first()

            if not warning:
                raise NotFoundError(f"Token warning not found: {warning_id}")

            warning.acknowledged_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(warning)

            logger.info(f"Acknowledged token warning: {warning_id}")
            return warning

        except NotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error acknowledging token warning {warning_id}: {e}")
            raise RepositoryError(f"Failed to acknowledge token warning: {e}") from e

    def delete(self, warning_id: UUID4) -> bool:
        """Delete token warning.

        Args:
            warning_id: Warning ID to delete

        Returns:
            True if deleted successfully

        Raises:
            NotFoundError: If warning not found
            RepositoryError: For other database errors
        """
        try:
            warning = self.db.query(TokenWarning).filter(TokenWarning.id == warning_id).first()

            if not warning:
                raise NotFoundError(f"Token warning not found: {warning_id}")

            self.db.delete(warning)
            self.db.commit()

            logger.info(f"Deleted token warning: {warning_id}")
            return True

        except NotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting token warning {warning_id}: {e}")
            raise RepositoryError(f"Failed to delete token warning: {e}") from e

    def delete_warnings_by_user(self, user_id: UUID4) -> int:
        """Delete all token warnings for a user.

        Args:
            user_id: User ID

        Returns:
            Number of warnings deleted

        Raises:
            RepositoryError: For database errors
        """
        try:
            deleted_count = self.db.query(TokenWarning).filter(TokenWarning.user_id == user_id).delete()

            self.db.commit()
            logger.info(f"Deleted {deleted_count} warnings for user: {user_id}")
            return deleted_count

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting warnings for user {user_id}: {e}")
            raise RepositoryError(f"Failed to delete warnings for user: {e}") from e

    def get_warning_stats_by_user(self, user_id: UUID4) -> dict[str, Any]:
        """Get token warning statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary with warning statistics
        """
        try:
            from sqlalchemy import func

            stats = (
                self.db.query(
                    func.count(TokenWarning.id).label("total_warnings"),
                    func.count(TokenWarning.acknowledged_at).label("acknowledged_warnings"),
                    func.count(TokenWarning.id).filter(TokenWarning.severity == "critical").label("critical_warnings"),
                    func.count(TokenWarning.id).filter(TokenWarning.severity == "warning").label("warning_warnings"),
                    func.count(TokenWarning.id).filter(TokenWarning.severity == "info").label("info_warnings"),
                )
                .filter(TokenWarning.user_id == user_id)
                .first()
            )

            return {
                "total_warnings": stats.total_warnings or 0,
                "acknowledged_warnings": stats.acknowledged_warnings or 0,
                "unacknowledged_warnings": (stats.total_warnings or 0) - (stats.acknowledged_warnings or 0),
                "critical_warnings": stats.critical_warnings or 0,
                "warning_warnings": stats.warning_warnings or 0,
                "info_warnings": stats.info_warnings or 0,
            }

        except Exception as e:
            logger.error(f"Error getting warning stats for user {user_id}: {e}")
            raise RepositoryError(f"Failed to get warning stats for user: {e}") from e
