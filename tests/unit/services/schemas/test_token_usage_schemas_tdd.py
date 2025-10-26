"""TDD Red Phase: Atomic tests for token usage schemas.

Atomic tests focus on the smallest units of functionality - individual
data structures, validation rules, and basic operations for token tracking.
"""

from datetime import datetime

import pytest
from backend.rag_solution.schemas.llm_usage_schema import (
    LLMUsage,
    ServiceType,
    TokenUsageStats,
    TokenWarning,
    TokenWarningType,
)
from pydantic import ValidationError


class TestTokenUsageSchemasAtomicTDD:
    """Atomic tests for token usage data structures and validation."""

    # ==================== SERVICE TYPE ENUM TESTS ====================

    @pytest.mark.atomic
    def test_service_type_enum_values(self) -> None:
        """Atomic: Test ServiceType enum has correct string values."""
        assert ServiceType.SEARCH == "search"
        assert ServiceType.CONVERSATION == "conversation"
        assert ServiceType.CHAIN_OF_THOUGHT == "chain_of_thought"
        assert ServiceType.QUESTION_GENERATION == "question_generation"

    # ==================== TOKEN WARNING TYPE ENUM TESTS ====================

    @pytest.mark.atomic
    def test_token_warning_type_enum_values(self) -> None:
        """Atomic: Test TokenWarningType enum has correct string values."""
        assert TokenWarningType.APPROACHING_LIMIT == "approaching_limit"
        assert TokenWarningType.CONTEXT_TRUNCATED == "context_truncated"
        assert TokenWarningType.AT_LIMIT == "at_limit"
        assert TokenWarningType.CONVERSATION_TOO_LONG == "conversation_too_long"

    # ==================== LLM USAGE TESTS ====================

    @pytest.mark.atomic
    def test_llm_usage_creation_all_fields(self) -> None:
        """Atomic: Test LLMUsage creation with all fields."""
        timestamp = datetime.utcnow()
        usage = LLMUsage(
            prompt_tokens=1200,
            completion_tokens=300,
            total_tokens=1500,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=timestamp,
            user_id="user_123",
            session_id="session_456",
        )

        assert usage.prompt_tokens == 1200
        assert usage.completion_tokens == 300
        assert usage.total_tokens == 1500
        assert usage.model_name == "gpt-3.5-turbo"
        assert usage.service_type == ServiceType.SEARCH
        assert usage.timestamp == timestamp
        assert usage.user_id == "user_123"
        assert usage.session_id == "session_456"

    @pytest.mark.atomic
    def test_llm_usage_creation_required_fields_only(self) -> None:
        """Atomic: Test LLMUsage creation with only required fields."""
        timestamp = datetime.utcnow()
        usage = LLMUsage(
            prompt_tokens=800,
            completion_tokens=200,
            total_tokens=1000,
            model_name="claude-3-sonnet",
            service_type=ServiceType.CONVERSATION,
            timestamp=timestamp,
        )

        assert usage.prompt_tokens == 800
        assert usage.completion_tokens == 200
        assert usage.total_tokens == 1000
        assert usage.model_name == "claude-3-sonnet"
        assert usage.service_type == ServiceType.CONVERSATION
        assert usage.timestamp == timestamp
        assert usage.user_id is None
        assert usage.session_id is None

    @pytest.mark.atomic
    def test_llm_usage_negative_tokens_validation(self) -> None:
        """Atomic: Test LLMUsage validation fails for negative token counts."""
        timestamp = datetime.utcnow()

        # This should fail because negative tokens don't make sense
        with pytest.raises((ValidationError, ValueError)):
            LLMUsage(
                prompt_tokens=-100,
                completion_tokens=200,
                total_tokens=100,
                model_name="gpt-4",
                service_type=ServiceType.SEARCH,
                timestamp=timestamp,
            )

    @pytest.mark.atomic
    def test_llm_usage_token_math_validation(self) -> None:
        """Atomic: Test LLMUsage validation for token math consistency."""
        timestamp = datetime.utcnow()

        # This should fail because total != prompt + completion
        with pytest.raises((ValidationError, ValueError)):
            LLMUsage(
                prompt_tokens=1000,
                completion_tokens=200,
                total_tokens=1500,  # Should be 1200
                model_name="gpt-4",
                service_type=ServiceType.SEARCH,
                timestamp=timestamp,
            )

    @pytest.mark.atomic
    def test_llm_usage_empty_model_name_validation(self) -> None:
        """Atomic: Test LLMUsage validation fails for empty model name."""
        timestamp = datetime.utcnow()

        with pytest.raises(ValueError, match="model_name cannot be empty"):
            LLMUsage(
                prompt_tokens=1000,
                completion_tokens=200,
                total_tokens=1200,
                model_name="",  # Empty string should fail
                service_type=ServiceType.SEARCH,
                timestamp=timestamp,
            )

    # ==================== TOKEN WARNING TESTS ====================

    @pytest.mark.atomic
    def test_token_warning_creation_all_fields(self) -> None:
        """Atomic: Test TokenWarning creation with all fields."""
        warning = TokenWarning(
            warning_type=TokenWarningType.APPROACHING_LIMIT,
            current_tokens=3500,
            limit_tokens=4096,
            percentage_used=85.4,
            message="Context window is 85% full. Approaching limit.",
            severity="warning",
            suggested_action="consider_new_session",
        )

        assert warning.warning_type == TokenWarningType.APPROACHING_LIMIT
        assert warning.current_tokens == 3500
        assert warning.limit_tokens == 4096
        assert warning.percentage_used == 85.4
        assert warning.message == "Context window is 85% full. Approaching limit."
        assert warning.severity == "warning"
        assert warning.suggested_action == "consider_new_session"

    @pytest.mark.atomic
    def test_token_warning_percentage_range_validation(self) -> None:
        """Atomic: Test TokenWarning percentage validation (0-100)."""
        # Valid percentage
        warning = TokenWarning(
            warning_type=TokenWarningType.APPROACHING_LIMIT,
            current_tokens=3500,
            limit_tokens=4096,
            percentage_used=85.4,
            message="Test message",
            severity="warning",
        )
        assert warning.percentage_used == 85.4

        # Invalid percentage > 100
        with pytest.raises(ValidationError):
            TokenWarning(
                warning_type=TokenWarningType.APPROACHING_LIMIT,
                current_tokens=3500,
                limit_tokens=4096,
                percentage_used=105.0,  # > 100
                message="Test message",
                severity="warning",
            )

        # Invalid percentage < 0
        with pytest.raises(ValidationError):
            TokenWarning(
                warning_type=TokenWarningType.APPROACHING_LIMIT,
                current_tokens=3500,
                limit_tokens=4096,
                percentage_used=-5.0,  # < 0
                message="Test message",
                severity="warning",
            )

    @pytest.mark.atomic
    def test_token_warning_severity_validation(self) -> None:
        """Atomic: Test TokenWarning severity validation (info|warning|critical)."""
        # Valid severities
        for severity in ["info", "warning", "critical"]:
            warning = TokenWarning(
                warning_type=TokenWarningType.APPROACHING_LIMIT,
                current_tokens=3500,
                limit_tokens=4096,
                percentage_used=85.4,
                message="Test message",
                severity=severity,
            )
            assert warning.severity == severity

        # Invalid severity
        with pytest.raises(ValidationError):
            TokenWarning(
                warning_type=TokenWarningType.APPROACHING_LIMIT,
                current_tokens=3500,
                limit_tokens=4096,
                percentage_used=85.4,
                message="Test message",
                severity="invalid",  # Not in allowed values
            )

    @pytest.mark.atomic
    def test_token_warning_suggested_action_optional(self) -> None:
        """Atomic: Test TokenWarning suggested_action is optional."""
        warning = TokenWarning(
            warning_type=TokenWarningType.APPROACHING_LIMIT,
            current_tokens=3500,
            limit_tokens=4096,
            percentage_used=85.4,
            message="Test message",
            severity="warning",
            # suggested_action omitted
        )
        assert warning.suggested_action is None

    # ==================== TOKEN USAGE STATS TESTS ====================

    @pytest.mark.atomic
    def test_token_usage_stats_creation_defaults(self) -> None:
        """Atomic: Test TokenUsageStats creation with default values."""
        stats = TokenUsageStats()

        assert stats.total_prompt_tokens == 0
        assert stats.total_completion_tokens == 0
        assert stats.total_tokens == 0
        assert stats.total_calls == 0
        assert stats.average_tokens_per_call == 0
        assert stats.by_service == {}
        assert stats.by_model == {}

    @pytest.mark.atomic
    def test_token_usage_stats_creation_with_values(self) -> None:
        """Atomic: Test TokenUsageStats creation with explicit values."""
        stats = TokenUsageStats(
            total_prompt_tokens=5000,
            total_completion_tokens=1500,
            total_tokens=6500,
            total_calls=10,
            average_tokens_per_call=650.0,
            by_service={
                ServiceType.SEARCH: 3000,
                ServiceType.CONVERSATION: 3500,
            },
            by_model={
                "gpt-3.5-turbo": 4000,
                "gpt-4": 2500,
            },
        )

        assert stats.total_prompt_tokens == 5000
        assert stats.total_completion_tokens == 1500
        assert stats.total_tokens == 6500
        assert stats.total_calls == 10
        assert stats.average_tokens_per_call == 650.0
        assert stats.by_service[ServiceType.SEARCH] == 3000
        assert stats.by_service[ServiceType.CONVERSATION] == 3500
        assert stats.by_model["gpt-3.5-turbo"] == 4000
        assert stats.by_model["gpt-4"] == 2500

    @pytest.mark.atomic
    def test_token_usage_stats_negative_values_validation(self) -> None:
        """Atomic: Test TokenUsageStats validation fails for negative values."""
        # Negative total_tokens should fail
        with pytest.raises(ValidationError):
            TokenUsageStats(
                total_prompt_tokens=1000,
                total_completion_tokens=500,
                total_tokens=-100,  # Negative value
                total_calls=5,
                average_tokens_per_call=300.0,
            )

        # Negative total_calls should fail
        with pytest.raises(ValidationError):
            TokenUsageStats(
                total_prompt_tokens=1000,
                total_completion_tokens=500,
                total_tokens=1500,
                total_calls=-5,  # Negative value
                average_tokens_per_call=300.0,
            )

    # ==================== SERIALIZATION TESTS ====================

    @pytest.mark.atomic
    def test_llm_usage_json_serialization(self) -> None:
        """Atomic: Test LLMUsage JSON serialization."""
        timestamp = datetime.utcnow()
        usage = LLMUsage(
            prompt_tokens=1200,
            completion_tokens=300,
            total_tokens=1500,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=timestamp,
            user_id="user_123",
            session_id="session_456",
        )

        # Convert to dict for JSON serialization
        json_data = usage.__dict__
        assert json_data["prompt_tokens"] == 1200
        assert json_data["completion_tokens"] == 300
        assert json_data["total_tokens"] == 1500
        assert json_data["model_name"] == "gpt-3.5-turbo"
        assert json_data["service_type"] == ServiceType.SEARCH
        assert json_data["timestamp"] == timestamp
        assert json_data["user_id"] == "user_123"
        assert json_data["session_id"] == "session_456"

    @pytest.mark.atomic
    def test_token_warning_json_serialization(self) -> None:
        """Atomic: Test TokenWarning JSON serialization."""
        warning = TokenWarning(
            warning_type=TokenWarningType.APPROACHING_LIMIT,
            current_tokens=3500,
            limit_tokens=4096,
            percentage_used=85.4,
            message="Context window is 85% full.",
            severity="warning",
            suggested_action="consider_new_session",
        )

        json_data = warning.model_dump(mode="json")
        assert json_data["warning_type"] == "approaching_limit"
        assert json_data["current_tokens"] == 3500
        assert json_data["limit_tokens"] == 4096
        assert json_data["percentage_used"] == 85.4
        assert json_data["message"] == "Context window is 85% full."
        assert json_data["severity"] == "warning"
        assert json_data["suggested_action"] == "consider_new_session"

    @pytest.mark.atomic
    def test_token_usage_stats_json_serialization(self) -> None:
        """Atomic: Test TokenUsageStats JSON serialization."""
        stats = TokenUsageStats(
            total_prompt_tokens=5000,
            total_completion_tokens=1500,
            total_tokens=6500,
            total_calls=10,
            average_tokens_per_call=650.0,
            by_service={ServiceType.SEARCH: 3000},
            by_model={"gpt-3.5-turbo": 4000},
        )

        json_data = stats.model_dump(mode="json")
        assert json_data["total_prompt_tokens"] == 5000
        assert json_data["total_completion_tokens"] == 1500
        assert json_data["total_tokens"] == 6500
        assert json_data["total_calls"] == 10
        assert json_data["average_tokens_per_call"] == 650.0
        assert "search" in json_data["by_service"]
        assert json_data["by_service"]["search"] == 3000
        assert json_data["by_model"]["gpt-3.5-turbo"] == 4000

    # ==================== EDGE CASE TESTS ====================

    @pytest.mark.atomic
    def test_llm_usage_zero_tokens(self) -> None:
        """Atomic: Test LLMUsage with zero token counts."""
        timestamp = datetime.utcnow()
        usage = LLMUsage(
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            model_name="test-model",
            service_type=ServiceType.SEARCH,
            timestamp=timestamp,
        )

        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    @pytest.mark.atomic
    def test_token_warning_boundary_percentages(self) -> None:
        """Atomic: Test TokenWarning with boundary percentage values."""
        # Test 0%
        warning_0 = TokenWarning(
            warning_type=TokenWarningType.APPROACHING_LIMIT,
            current_tokens=0,
            limit_tokens=4096,
            percentage_used=0.0,
            message="No tokens used",
            severity="info",
        )
        assert warning_0.percentage_used == 0.0

        # Test 100%
        warning_100 = TokenWarning(
            warning_type=TokenWarningType.AT_LIMIT,
            current_tokens=4096,
            limit_tokens=4096,
            percentage_used=100.0,
            message="At limit",
            severity="critical",
        )
        assert warning_100.percentage_used == 100.0

    @pytest.mark.atomic
    def test_service_type_enum_iteration(self) -> None:
        """Atomic: Test ServiceType enum can be iterated."""
        service_types = list(ServiceType)
        assert len(service_types) == 4
        assert ServiceType.SEARCH in service_types
        assert ServiceType.CONVERSATION in service_types
        assert ServiceType.CHAIN_OF_THOUGHT in service_types
        assert ServiceType.QUESTION_GENERATION in service_types

    @pytest.mark.atomic
    def test_token_warning_type_enum_iteration(self) -> None:
        """Atomic: Test TokenWarningType enum can be iterated."""
        warning_types = list(TokenWarningType)
        assert len(warning_types) == 4
        assert TokenWarningType.APPROACHING_LIMIT in warning_types
        assert TokenWarningType.CONTEXT_TRUNCATED in warning_types
        assert TokenWarningType.AT_LIMIT in warning_types
        assert TokenWarningType.CONVERSATION_TOO_LONG in warning_types
