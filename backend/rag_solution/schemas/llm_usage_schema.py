"""Schemas for LLM token usage tracking.

This module defines Pydantic schemas for tracking token usage from LLM providers,
including usage statistics, warnings, and service-specific tracking.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ServiceType(str, Enum):
    """Type of service that used LLM tokens."""

    SEARCH = "search"
    CONVERSATION = "conversation"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    QUESTION_GENERATION = "question_generation"


class TokenWarningType(str, Enum):
    """Type of token warning."""

    APPROACHING_LIMIT = "approaching_limit"
    CONTEXT_TRUNCATED = "context_truncated"
    AT_LIMIT = "at_limit"
    CONVERSATION_TOO_LONG = "conversation_too_long"


@dataclass
class LLMUsage:
    """Actual token usage from LLM API response.

    Attributes:
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        total_tokens: Total number of tokens used
        model_name: Name of the LLM model
        service_type: Service that made the LLM request
        timestamp: When the usage occurred
        user_id: Optional user identifier
        session_id: Optional session identifier
    """

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model_name: str
    service_type: ServiceType
    timestamp: datetime
    user_id: str | None = None
    session_id: str | None = None

    def __post_init__(self) -> None:
        """Validate token counts after initialization."""
        if self.prompt_tokens < 0:
            raise ValueError("prompt_tokens cannot be negative")
        if self.completion_tokens < 0:
            raise ValueError("completion_tokens cannot be negative")
        if self.total_tokens < 0:
            raise ValueError("total_tokens cannot be negative")
        if self.total_tokens != self.prompt_tokens + self.completion_tokens:
            raise ValueError("total_tokens must equal prompt_tokens + completion_tokens")
        if not self.model_name:
            raise ValueError("model_name cannot be empty")


class TokenWarning(BaseModel):
    """Warning about token usage approaching limits.

    Attributes:
        warning_type: Type of warning
        current_tokens: Current token count
        limit_tokens: Token limit
        percentage_used: Percentage of limit used (0-100)
        message: Human-readable warning message
        severity: Warning severity level
        suggested_action: Optional suggested action for the user
    """

    warning_type: TokenWarningType
    current_tokens: int
    limit_tokens: int
    percentage_used: float = Field(..., ge=0, le=100)
    message: str
    severity: str = Field(..., pattern="^(info|warning|critical)$")
    suggested_action: str | None = None

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Validate severity is one of the allowed values."""
        if v not in ["info", "warning", "critical"]:
            raise ValueError("severity must be one of: info, warning, critical")
        return v


class TokenUsageStats(BaseModel):
    """Aggregated token usage statistics.

    Attributes:
        total_prompt_tokens: Total tokens used in prompts
        total_completion_tokens: Total tokens used in completions
        total_tokens: Total tokens used overall
        total_calls: Number of LLM calls
        average_tokens_per_call: Average tokens per call
        by_service: Token usage grouped by service type
        by_model: Token usage grouped by model name
    """

    total_prompt_tokens: int = Field(default=0, ge=0)
    total_completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    total_calls: int = Field(default=0, ge=0)
    average_tokens_per_call: float = Field(default=0, ge=0)
    by_service: dict[ServiceType | str, int] = Field(default_factory=dict)
    by_model: dict[str, int] = Field(default_factory=dict)

    @field_validator("total_prompt_tokens", "total_completion_tokens", "total_tokens", "total_calls")
    @classmethod
    def validate_non_negative(cls, v: int) -> int:
        """Validate that counts are non-negative."""
        if v < 0:
            raise ValueError("Token counts cannot be negative")
        return v
