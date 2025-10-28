"""Service for comprehensive token usage tracking and management.

This service tracks all token usage (sent + received), accumulates usage statistics,
manages token limits per model, and generates appropriate warnings when approaching
or exceeding those limits. It provides the central hub for all token-related operations.
"""

from typing import Any
from uuid import UUID

from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.repository.token_warning_repository import TokenWarningRepository
from rag_solution.schemas.llm_usage_schema import (
    LLMUsage,
    TokenUsageStats,
    TokenWarning,
    TokenWarningType,
)
from rag_solution.services.llm_model_service import LLMModelService


class TokenTrackingService:
    """Service for comprehensive token usage tracking and management.

    This service provides:
    - Token usage tracking for all user interactions
    - Accumulation of token statistics per user and session
    - Token limit monitoring per LLM model
    - Warning generation when approaching limits (70%, 85%, 95% thresholds)
    - Usage analytics and reporting

    Attributes:
        db: Database session
        settings: Application settings
        llm_model_service: Service for retrieving model configurations
        token_warning_repository: Repository for token warning data access
    """

    def __init__(self, db: Session, settings: Settings) -> None:
        """Initialize the token tracking service.

        Args:
            db: Database session
            settings: Application settings
        """
        self.db = db
        self.settings = settings
        self.token_warning_repository = TokenWarningRepository(db)

        # Lazy initialization for LLM model service
        self._llm_model_service: LLMModelService | None = None

    @property
    def llm_model_service(self) -> LLMModelService:
        """Get LLM model service with lazy initialization."""
        if self._llm_model_service is None:
            self._llm_model_service = LLMModelService(self.db)
        return self._llm_model_service

    async def check_usage_warning(
        self,
        current_usage: LLMUsage,
        context_tokens: int | None = None,
    ) -> TokenWarning | None:
        """Check if current usage warrants a warning.

        Args:
            current_usage: Current token usage from LLM
            context_tokens: Optional override for context token count

        Returns:
            TokenWarning if thresholds are exceeded, None otherwise
        """
        # Get context limit with fallback - handle both UUID model IDs and string model names
        try:
            # Try to parse as UUID first (for backward compatibility)
            model_uuid = UUID(current_usage.model_name)
            model = await self.llm_model_service.get_model_by_id(model_uuid)
            context_limit = getattr(model, "context_window", 4096) if model else 4096
        except ValueError:
            # model_name is not a UUID, it's a string like "ibm/granite-3-3-8b-instruct"
            # Use default context window for now - this could be enhanced later
            context_limit = 4096

        # Determine tokens to check against limit
        check_tokens = context_tokens if context_tokens is not None else current_usage.prompt_tokens
        percentage = (check_tokens / context_limit) * 100

        # Generate appropriate warning based on percentage
        if percentage >= 95:
            return TokenWarning(
                warning_type=TokenWarningType.AT_LIMIT,
                current_tokens=check_tokens,
                limit_tokens=context_limit,
                percentage_used=min(percentage, 100.0),  # Cap at 100%
                message=f"Context window is {percentage:.0f}% full. Consider starting a new conversation.",
                severity="critical",
                suggested_action="start_new_session",
            )
        elif percentage >= 85:
            return TokenWarning(
                warning_type=TokenWarningType.APPROACHING_LIMIT,
                current_tokens=check_tokens,
                limit_tokens=context_limit,
                percentage_used=percentage,
                message=f"Context window is {percentage:.0f}% full. Approaching limit.",
                severity="warning",
                suggested_action="consider_new_session",
            )
        elif percentage >= 70:
            return TokenWarning(
                warning_type=TokenWarningType.APPROACHING_LIMIT,
                current_tokens=check_tokens,
                limit_tokens=context_limit,
                percentage_used=percentage,
                message=f"Context window is {percentage:.0f}% full.",
                severity="info",
                suggested_action=None,
            )

        return None

    async def check_conversation_warning(
        self,
        session_usage_history: list[LLMUsage],
        model_name: str,
    ) -> TokenWarning | None:
        """Check if conversation length warrants a warning.

        Args:
            session_usage_history: History of token usage in the conversation
            model_name: Name of the LLM model being used

        Returns:
            TokenWarning if conversation is getting too long, None otherwise
        """
        if not session_usage_history:
            return None

        # Calculate cumulative prompt tokens for recent messages
        recent_messages = session_usage_history[-5:]  # Last 5 messages
        recent_prompt_tokens = sum(u.prompt_tokens for u in recent_messages)

        # Get model limits
        model = await self.llm_model_service.get_model_by_id(UUID(model_name))
        if not model:
            return None

        context_limit = getattr(model, "context_window", 4096)

        # Check if conversation is getting too long
        percentage = (recent_prompt_tokens / context_limit) * 100
        if recent_prompt_tokens > context_limit * 0.8:
            return TokenWarning(
                warning_type=TokenWarningType.CONVERSATION_TOO_LONG,
                current_tokens=recent_prompt_tokens,
                limit_tokens=context_limit,
                percentage_used=min(percentage, 100.0),  # Cap at 100%
                message="Conversation context is getting large. Older messages may be excluded from context.",
                severity="warning" if percentage < 95 else "critical",
                suggested_action="start_new_session",
            )

        return None

    # Repository-based methods for persistence

    async def store_warning(
        self, warning: TokenWarning, user_id: UUID4 | None = None, session_id: str | None = None
    ) -> None:
        """Store a token warning in the database.

        Args:
            warning: Token warning to store
            user_id: Optional user ID
            session_id: Optional session ID
        """
        self.token_warning_repository.create(warning, user_id, session_id)

    async def get_user_warnings(
        self, user_id: UUID4, acknowledged: bool | None = None, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Get token warnings for a user.

        Args:
            user_id: User ID
            acknowledged: Filter by acknowledgment status
            limit: Maximum number of warnings
            offset: Offset for pagination

        Returns:
            List of warning dictionaries
        """
        warnings = self.token_warning_repository.get_warnings_by_user(user_id, limit, offset, acknowledged)
        return [
            {
                "id": str(warning.id),
                "warning_type": warning.warning_type,
                "current_tokens": warning.current_tokens,
                "limit_tokens": warning.limit_tokens,
                "percentage_used": warning.percentage_used,
                "message": warning.message,
                "severity": warning.severity,
                "suggested_action": warning.suggested_action,
                "model_name": warning.model_name,
                "service_type": warning.service_type,
                "created_at": warning.created_at.isoformat(),
                "acknowledged_at": warning.acknowledged_at.isoformat() if warning.acknowledged_at else None,
            }
            for warning in warnings
        ]

    async def get_session_warnings(self, session_id: str, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        """Get token warnings for a session.

        Args:
            session_id: Session ID
            limit: Maximum number of warnings
            offset: Offset for pagination

        Returns:
            List of warning dictionaries
        """
        warnings = self.token_warning_repository.get_warnings_by_session(session_id, limit, offset)
        return [
            {
                "id": str(warning.id),
                "warning_type": warning.warning_type,
                "current_tokens": warning.current_tokens,
                "limit_tokens": warning.limit_tokens,
                "percentage_used": warning.percentage_used,
                "message": warning.message,
                "severity": warning.severity,
                "suggested_action": warning.suggested_action,
                "model_name": warning.model_name,
                "service_type": warning.service_type,
                "created_at": warning.created_at.isoformat(),
                "acknowledged_at": warning.acknowledged_at.isoformat() if warning.acknowledged_at else None,
            }
            for warning in warnings
        ]

    async def get_recent_warnings(self, limit: int = 100, severity: str | None = None) -> list[dict[str, Any]]:
        """Get recent token warnings.

        Args:
            limit: Maximum number of warnings
            severity: Filter by severity level

        Returns:
            List of warning dictionaries
        """
        warnings = self.token_warning_repository.get_recent_warnings(limit, severity)
        return [
            {
                "id": str(warning.id),
                "user_id": str(warning.user_id) if warning.user_id else None,
                "session_id": warning.session_id,
                "warning_type": warning.warning_type,
                "current_tokens": warning.current_tokens,
                "limit_tokens": warning.limit_tokens,
                "percentage_used": warning.percentage_used,
                "message": warning.message,
                "severity": warning.severity,
                "suggested_action": warning.suggested_action,
                "model_name": warning.model_name,
                "service_type": warning.service_type,
                "created_at": warning.created_at.isoformat(),
                "acknowledged_at": warning.acknowledged_at.isoformat() if warning.acknowledged_at else None,
            }
            for warning in warnings
        ]

    async def acknowledge_warning(self, warning_id: UUID4) -> Any:
        """Acknowledge a token warning.

        Args:
            warning_id: Warning ID to acknowledge

        Returns:
            Updated warning model
        """
        return self.token_warning_repository.acknowledge_warning(warning_id)

    async def delete_warning(self, warning_id: UUID4) -> bool:
        """Delete a token warning.

        Args:
            warning_id: Warning ID to delete

        Returns:
            True if deleted successfully
        """
        return self.token_warning_repository.delete(warning_id)

    async def delete_user_warnings(self, user_id: UUID4) -> int:
        """Delete all warnings for a user.

        Args:
            user_id: User ID

        Returns:
            Number of warnings deleted
        """
        return self.token_warning_repository.delete_warnings_by_user(user_id)

    async def get_user_token_stats(self, user_id: UUID4) -> TokenUsageStats:
        """Get token usage statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Token usage statistics
        """
        stats = self.token_warning_repository.get_warning_stats_by_user(user_id)
        return TokenUsageStats(
            total_tokens=0,  # Would need to implement actual token tracking
            total_calls=0,  # Would need to implement actual call tracking
            by_service={},  # Would need to implement service-level tracking
            by_model={},  # Would need to implement model-level tracking
            **stats,
        )
