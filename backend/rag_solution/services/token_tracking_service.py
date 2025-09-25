"""Service for comprehensive token usage tracking and management.

This service provides:
- Accurate token counting using model-specific tokenizers
- Token usage tracking (sent + received) with real data from LLM APIs
- Usage statistics accumulation per user and session
- Token limit monitoring per LLM model
- Warning generation when approaching limits (70%, 85%, 95% thresholds)
- Centralized token operations for all services
"""

from typing import Any
from uuid import UUID

from core.config import Settings
from core.logging_utils import get_logger
from pydantic import UUID4
from sqlalchemy.orm import Session

from rag_solution.repository.token_warning_repository import TokenWarningRepository
from rag_solution.schemas.llm_usage_schema import (
    LLMUsage,
    TokenUsageStats,
    TokenWarning,
    TokenWarningType,
)
from rag_solution.services.llm_model_service import LLMModelService
from rag_solution.utils.tokenization_utils import TokenizationUtils

logger = get_logger("token_tracking_service")


class TokenTrackingService:
    """Service for comprehensive token usage tracking and management.

    This service provides:
    - Accurate token counting using model-specific tokenizers (tiktoken for OpenAI, etc.)
    - Real token usage extraction from LLM provider responses
    - Token usage tracking for all user interactions
    - Accumulation of token statistics per user and session
    - Token limit monitoring per LLM model with accurate context windows
    - Warning generation when approaching limits (70%, 85%, 95% thresholds)
    - Usage analytics and reporting
    - Token estimation fallback when exact counting is not available

    Attributes:
        db: Database session
        settings: Application settings
        llm_model_service: Service for retrieving model configurations
        token_warning_repository: Repository for token warning data access
        tokenization_utils: Utilities for accurate token counting
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
        self.tokenization_utils = TokenizationUtils()

        # Lazy initialization for LLM model service
        self._llm_model_service: LLMModelService | None = None

        # Cache for token usage accumulation
        self._usage_cache: dict[str, list[LLMUsage]] = {}

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
            context_limit = getattr(model, "context_window", None)
            if context_limit is None:
                # If model doesn't have context_window, use tokenization utils
                context_limit = self.get_context_window(current_usage.model_name)
        except ValueError:
            # model_name is not a UUID, it's a string like "ibm/granite-3-3-8b-instruct"
            # Use tokenization utils to get accurate context window
            context_limit = self.get_context_window(current_usage.model_name)

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
        try:
            model = await self.llm_model_service.get_model_by_id(UUID(model_name))
            context_limit = getattr(model, "context_window", None)
            if context_limit is None:
                context_limit = self.get_context_window(model_name)
        except ValueError:
            # model_name is not a UUID, use tokenization utils
            context_limit = self.get_context_window(model_name)

        # Check if conversation is getting too long
        percentage = (recent_prompt_tokens / context_limit) * 100
        if recent_prompt_tokens > context_limit * 0.8:
            return TokenWarning(
                warning_type=TokenWarningType.CONVERSATION_TOO_LONG,
                current_tokens=recent_prompt_tokens,
                limit_tokens=context_limit,
                percentage_used=percentage,
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

        # Calculate actual token statistics from cached usage
        user_key = str(user_id)
        usage_history = self._usage_cache.get(user_key, [])

        total_tokens = sum(u.total_tokens for u in usage_history)
        total_calls = len(usage_history)

        # Aggregate by service
        by_service = {}
        for usage in usage_history:
            service = usage.service_type.value if usage.service_type else "unknown"
            if service not in by_service:
                by_service[service] = {"tokens": 0, "calls": 0}
            by_service[service]["tokens"] += usage.total_tokens
            by_service[service]["calls"] += 1

        # Aggregate by model
        by_model = {}
        for usage in usage_history:
            model = usage.model_name or "unknown"
            if model not in by_model:
                by_model[model] = {"tokens": 0, "calls": 0}
            by_model[model]["tokens"] += usage.total_tokens
            by_model[model]["calls"] += 1

        return TokenUsageStats(
            total_tokens=total_tokens,
            total_calls=total_calls,
            by_service=by_service,
            by_model=by_model,
            **stats,
        )

    def count_tokens(self, text: str, model_name: str) -> int:
        """Count tokens for a given text and model using accurate tokenization.

        This method uses model-specific tokenizers when available (tiktoken for OpenAI,
        transformers for IBM/Meta models) and falls back to intelligent estimation
        for models without available tokenizers.

        Args:
            text: Text to tokenize
            model_name: Name of the model

        Returns:
            Accurate or estimated token count
        """
        return self.tokenization_utils.count_tokens(text, model_name)

    def estimate_tokens(self, text: str, model_name: str | None = None) -> int:
        """Estimate token count when exact tokenization is not available.

        Uses model-specific heuristics for better accuracy:
        - OpenAI models: ~4 characters per token
        - Anthropic models: ~3.5 characters per token
        - IBM/Meta models: ~3.8 characters per token

        Args:
            text: Text to estimate tokens for
            model_name: Optional model name for model-specific estimation

        Returns:
            Estimated token count
        """
        return self.tokenization_utils.estimate_tokens(text, model_name)

    def get_context_window(self, model_name: str) -> int:
        """Get the context window size for a model.

        Returns accurate context windows for known models:
        - GPT-4: 8192 tokens (32k variant: 32768)
        - GPT-3.5: 4096 tokens (16k variant: 16384)
        - Claude 3: 200000 tokens
        - Claude 2: 100000 tokens
        - Granite models: 8192 tokens
        - Llama 3: 8192 tokens
        - Mixtral: 32768 tokens

        Args:
            model_name: Name of the model

        Returns:
            Context window size in tokens
        """
        return self.tokenization_utils.get_context_window(model_name)

    def track_usage(self, usage: LLMUsage) -> None:
        """Track token usage for a user.

        Args:
            usage: LLM usage data to track
        """
        if usage.user_id:
            user_key = str(usage.user_id)
            if user_key not in self._usage_cache:
                self._usage_cache[user_key] = []
            self._usage_cache[user_key].append(usage)

            # Limit cache size per user
            if len(self._usage_cache[user_key]) > 1000:
                self._usage_cache[user_key] = self._usage_cache[user_key][-500:]

    def extract_usage_from_response(
        self,
        response: Any,
        model_name: str,
        provider: str,
        prompt: str | None = None,
        completion: str | None = None,
    ) -> LLMUsage:
        """Extract actual token usage from LLM provider response.

        Handles different response formats from various providers:
        - OpenAI: response.usage.prompt_tokens, completion_tokens, total_tokens
        - Anthropic: response.usage.input_tokens, output_tokens
        - WatsonX: May need to count tokens manually

        Args:
            response: Response object from LLM provider
            model_name: Name of the model used
            provider: Provider name (openai, anthropic, watsonx)
            prompt: Optional prompt text for fallback counting
            completion: Optional completion text for fallback counting

        Returns:
            LLMUsage object with actual or estimated token counts
        """
        from datetime import datetime

        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        # Extract based on provider
        if provider.lower() == "openai" and hasattr(response, "usage"):
            usage = response.usage
            prompt_tokens = getattr(usage, "prompt_tokens", 0)
            completion_tokens = getattr(usage, "completion_tokens", 0)
            total_tokens = getattr(usage, "total_tokens", 0)
        elif provider.lower() == "anthropic" and hasattr(response, "usage"):
            usage = response.usage
            prompt_tokens = getattr(usage, "input_tokens", 0)
            completion_tokens = getattr(usage, "output_tokens", 0)
            total_tokens = prompt_tokens + completion_tokens
        elif provider.lower() == "watsonx":
            # WatsonX doesn't provide token counts in response, need to count
            if prompt:
                prompt_tokens = self.count_tokens(prompt, model_name)
            if completion:
                completion_tokens = self.count_tokens(completion, model_name)
            total_tokens = prompt_tokens + completion_tokens
        else:
            # Fallback to counting/estimation
            if prompt:
                prompt_tokens = self.count_tokens(prompt, model_name)
            if completion:
                completion_tokens = self.count_tokens(completion, model_name)
            total_tokens = prompt_tokens + completion_tokens

        return LLMUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model_name=model_name,
            timestamp=datetime.now(),
        )
