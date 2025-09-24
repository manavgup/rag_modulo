"""TDD Red Phase: Unit tests for TokenTrackingService.

Unit tests focus on the TokenTrackingService behavior with mocked dependencies.
All tests should fail initially as the service doesn't exist yet.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from rag_solution.schemas.llm_usage_schema import (
    LLMUsage,
    ServiceType,
    TokenWarningType,
)
from rag_solution.services.token_tracking_service import TokenTrackingService


class TestTokenTrackingServiceTDD:
    """Unit tests for TokenTrackingService functionality."""

    @pytest.fixture
    def mock_llm_model_service(self) -> Mock:
        """Create mock LLM model service with known context windows."""
        mock_service = Mock()

        # Mock different model configurations
        def mock_get_model_by_name(model_name: str) -> Mock | None:
            model_configs = {
                "gpt-3.5-turbo": {"context_window": 4096, "max_output_tokens": 4096},
                "gpt-4": {"context_window": 8192, "max_output_tokens": 4096},
                "gpt-4-turbo": {"context_window": 128000, "max_output_tokens": 4096},
                "claude-3-sonnet": {"context_window": 200000, "max_output_tokens": 4096},
                "granite-13b": {"context_window": 8192, "max_output_tokens": 2048},
            }

            if model_name in model_configs:
                mock_model = Mock()
                config = model_configs[model_name]
                mock_model.context_window = config["context_window"]
                mock_model.max_output_tokens = config["max_output_tokens"]
                return mock_model
            return None

        mock_service.get_model_by_name = AsyncMock(side_effect=mock_get_model_by_name)
        return mock_service

    @pytest.fixture
    def token_warning_service(self, mock_llm_model_service: Mock, mock_settings) -> TokenTrackingService:
        """Create TokenTrackingService with mocked dependencies."""
        return TokenTrackingService(mock_llm_model_service, mock_settings)

    # ==================== WARNING THRESHOLD TESTS ====================

    @pytest.mark.unit
    async def test_no_warning_under_70_percent(self, token_warning_service: TokenTrackingService) -> None:
        """Unit: Test no warning generated when under 70% usage."""
        usage = LLMUsage(
            prompt_tokens=2800,  # ~68% of 4096
            completion_tokens=200,
            total_tokens=3000,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow(),
        )

        warning = await token_warning_service.check_usage_warning(usage)
        assert warning is None

    @pytest.mark.unit
    async def test_info_warning_70_to_85_percent(self, token_warning_service: TokenTrackingService) -> None:
        """Unit: Test info warning generated between 70-85% usage."""
        usage = LLMUsage(
            prompt_tokens=3200,  # ~78% of 4096
            completion_tokens=200,
            total_tokens=3400,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow(),
        )

        warning = await token_warning_service.check_usage_warning(usage)
        assert warning is not None
        assert warning.warning_type == TokenWarningType.APPROACHING_LIMIT
        assert warning.severity == "info"
        assert 70 <= warning.percentage_used < 85
        assert warning.current_tokens == 3200
        assert warning.limit_tokens == 4096

    @pytest.mark.unit
    async def test_warning_severity_85_to_95_percent(self, token_warning_service: TokenTrackingService) -> None:
        """Unit: Test warning severity generated between 85-95% usage."""
        usage = LLMUsage(
            prompt_tokens=3700,  # ~90% of 4096
            completion_tokens=200,
            total_tokens=3900,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow(),
        )

        warning = await token_warning_service.check_usage_warning(usage)
        assert warning is not None
        assert warning.warning_type == TokenWarningType.APPROACHING_LIMIT
        assert warning.severity == "warning"
        assert 85 <= warning.percentage_used < 95
        assert warning.suggested_action == "consider_new_session"

    @pytest.mark.unit
    async def test_critical_warning_over_95_percent(self, token_warning_service: TokenTrackingService) -> None:
        """Unit: Test critical warning generated over 95% usage."""
        usage = LLMUsage(
            prompt_tokens=3900,  # ~95% of 4096
            completion_tokens=200,
            total_tokens=4100,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow(),
        )

        warning = await token_warning_service.check_usage_warning(usage)
        assert warning is not None
        assert warning.warning_type == TokenWarningType.AT_LIMIT
        assert warning.severity == "critical"
        assert warning.percentage_used >= 95
        assert warning.suggested_action == "start_new_session"
        assert "new conversation" in warning.message.lower()

    # ==================== DIFFERENT MODEL TESTS ====================

    @pytest.mark.unit
    async def test_warning_with_gpt4_larger_context(self, token_warning_service: TokenTrackingService) -> None:
        """Unit: Test warning calculation with GPT-4's larger context window."""
        usage = LLMUsage(
            prompt_tokens=7000,  # ~85% of 8192
            completion_tokens=500,
            total_tokens=7500,
            model_name="gpt-4",
            service_type=ServiceType.CONVERSATION,
            timestamp=datetime.utcnow(),
        )

        warning = await token_warning_service.check_usage_warning(usage)
        assert warning is not None
        assert warning.warning_type == TokenWarningType.APPROACHING_LIMIT
        assert warning.severity == "warning"
        assert warning.limit_tokens == 8192
        assert 85 <= warning.percentage_used < 95

    @pytest.mark.unit
    async def test_warning_with_claude_large_context(self, token_warning_service: TokenTrackingService) -> None:
        """Unit: Test warning calculation with Claude's very large context window."""
        usage = LLMUsage(
            prompt_tokens=150000,  # 75% of 200000
            completion_tokens=5000,
            total_tokens=155000,
            model_name="claude-3-sonnet",
            service_type=ServiceType.CHAIN_OF_THOUGHT,
            timestamp=datetime.utcnow(),
        )

        warning = await token_warning_service.check_usage_warning(usage)
        assert warning is not None
        assert warning.warning_type == TokenWarningType.APPROACHING_LIMIT
        assert warning.severity == "info"
        assert warning.limit_tokens == 200000

    @pytest.mark.unit
    async def test_no_warning_unknown_model(self, token_warning_service: TokenTrackingService) -> None:
        """Unit: Test no warning generated for unknown model."""
        usage = LLMUsage(
            prompt_tokens=3000,
            completion_tokens=500,
            total_tokens=3500,
            model_name="unknown-model",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow(),
        )

        warning = await token_warning_service.check_usage_warning(usage)
        assert warning is None

    # ==================== CONTEXT TOKENS OVERRIDE TESTS ====================

    @pytest.mark.unit
    async def test_warning_with_context_tokens_override(self, token_warning_service: TokenTrackingService) -> None:
        """Unit: Test warning uses context_tokens parameter when provided."""
        usage = LLMUsage(
            prompt_tokens=1000,  # This should be ignored
            completion_tokens=200,
            total_tokens=1200,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.CONVERSATION,
            timestamp=datetime.utcnow(),
        )

        # Override with higher context token count
        warning = await token_warning_service.check_usage_warning(usage, context_tokens=3500)
        assert warning is not None
        assert warning.current_tokens == 3500  # Should use override, not usage.prompt_tokens
        assert warning.percentage_used > 80  # 3500/4096 = ~85%

    # ==================== CONVERSATION WARNING TESTS ====================

    @pytest.mark.unit
    async def test_conversation_warning_short_history(self, token_warning_service: TokenTrackingService) -> None:
        """Unit: Test no conversation warning for short history."""
        session_history = [
            LLMUsage(
                prompt_tokens=500,
                completion_tokens=100,
                total_tokens=600,
                model_name="gpt-3.5-turbo",
                service_type=ServiceType.CONVERSATION,
                timestamp=datetime.utcnow(),
            ),
            LLMUsage(
                prompt_tokens=600,
                completion_tokens=120,
                total_tokens=720,
                model_name="gpt-3.5-turbo",
                service_type=ServiceType.CONVERSATION,
                timestamp=datetime.utcnow(),
            ),
        ]

        warning = await token_warning_service.check_conversation_warning(session_history, "gpt-3.5-turbo")
        assert warning is None

    @pytest.mark.unit
    async def test_conversation_warning_long_history(self, token_warning_service: TokenTrackingService) -> None:
        """Unit: Test conversation warning for long session history."""
        # Create history where recent 5 messages exceed 80% of context limit
        session_history = []
        for i in range(7):  # 7 messages total
            session_history.append(
                LLMUsage(
                    prompt_tokens=700,  # Each message uses 700 tokens
                    completion_tokens=100,
                    total_tokens=800,
                    model_name="gpt-3.5-turbo",
                    service_type=ServiceType.CONVERSATION,
                    timestamp=datetime.utcnow(),
                )
            )
        # Recent 5 messages = 5 * 700 = 3500 tokens > 80% of 4096

        warning = await token_warning_service.check_conversation_warning(session_history, "gpt-3.5-turbo")
        assert warning is not None
        assert warning.warning_type == TokenWarningType.CONVERSATION_TOO_LONG
        assert warning.severity == "warning"
        assert "older messages may be excluded" in warning.message.lower()
        assert warning.suggested_action == "start_new_session"

    @pytest.mark.unit
    async def test_conversation_warning_empty_history(self, token_warning_service: TokenTrackingService) -> None:
        """Unit: Test no conversation warning for empty history."""
        warning = await token_warning_service.check_conversation_warning([], "gpt-3.5-turbo")
        assert warning is None

    @pytest.mark.unit
    async def test_conversation_warning_unknown_model(self, token_warning_service: TokenTrackingService) -> None:
        """Unit: Test no conversation warning for unknown model."""
        session_history = [
            LLMUsage(
                prompt_tokens=1000,
                completion_tokens=200,
                total_tokens=1200,
                model_name="unknown-model",
                service_type=ServiceType.CONVERSATION,
                timestamp=datetime.utcnow(),
            )
        ]

        warning = await token_warning_service.check_conversation_warning(session_history, "unknown-model")
        assert warning is None

    # ==================== EDGE CASE TESTS ====================

    @pytest.mark.unit
    async def test_warning_exactly_at_threshold(self, token_warning_service: TokenTrackingService) -> None:
        """Unit: Test warning generation exactly at threshold boundaries."""
        # Exactly 70%
        usage_70 = LLMUsage(
            prompt_tokens=2867,  # Exactly 70% of 4096
            completion_tokens=200,
            total_tokens=3067,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow(),
        )

        warning = await token_warning_service.check_usage_warning(usage_70)
        assert warning is not None
        assert warning.severity == "info"

        # Exactly 85%
        usage_85 = LLMUsage(
            prompt_tokens=3482,  # Exactly 85% of 4096
            completion_tokens=200,
            total_tokens=3682,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow(),
        )

        warning = await token_warning_service.check_usage_warning(usage_85)
        assert warning is not None
        assert warning.severity == "warning"

        # Exactly 95%
        usage_95 = LLMUsage(
            prompt_tokens=3891,  # Exactly 95% of 4096
            completion_tokens=200,
            total_tokens=4091,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow(),
        )

        warning = await token_warning_service.check_usage_warning(usage_95)
        assert warning is not None
        assert warning.severity == "critical"

    @pytest.mark.unit
    async def test_warning_zero_tokens(self, token_warning_service: TokenTrackingService) -> None:
        """Unit: Test no warning for zero token usage."""
        usage = LLMUsage(
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow(),
        )

        warning = await token_warning_service.check_usage_warning(usage)
        assert warning is None

    @pytest.mark.unit
    async def test_warning_tokens_exceed_limit(self, token_warning_service: TokenTrackingService) -> None:
        """Unit: Test warning when tokens exceed model limit."""
        usage = LLMUsage(
            prompt_tokens=5000,  # Exceeds 4096 limit
            completion_tokens=500,
            total_tokens=5500,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow(),
        )

        warning = await token_warning_service.check_usage_warning(usage)
        assert warning is not None
        assert warning.warning_type == TokenWarningType.AT_LIMIT
        assert warning.severity == "critical"
        assert warning.percentage_used > 100

    # ==================== MESSAGE CONTENT TESTS ====================

    @pytest.mark.unit
    async def test_warning_message_contains_percentage(self, token_warning_service: TokenTrackingService) -> None:
        """Unit: Test warning message contains percentage information."""
        usage = LLMUsage(
            prompt_tokens=3200,
            completion_tokens=200,
            total_tokens=3400,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow(),
        )

        warning = await token_warning_service.check_usage_warning(usage)
        assert warning is not None
        assert "78%" in warning.message or "78.1%" in warning.message  # ~78% usage

    @pytest.mark.unit
    async def test_warning_message_different_severities(self, token_warning_service: TokenTrackingService) -> None:
        """Unit: Test warning messages vary by severity level."""
        # Info level warning
        usage_info = LLMUsage(
            prompt_tokens=3000,  # ~73%
            completion_tokens=200,
            total_tokens=3200,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow(),
        )

        warning_info = await token_warning_service.check_usage_warning(usage_info)
        assert warning_info is not None
        assert warning_info.severity == "info"
        assert warning_info.suggested_action is None

        # Warning level
        usage_warning = LLMUsage(
            prompt_tokens=3600,  # ~88%
            completion_tokens=200,
            total_tokens=3800,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow(),
        )

        warning_warn = await token_warning_service.check_usage_warning(usage_warning)
        assert warning_warn is not None
        assert warning_warn.severity == "warning"
        assert warning_warn.suggested_action == "consider_new_session"

        # Critical level
        usage_critical = LLMUsage(
            prompt_tokens=3900,  # ~95%
            completion_tokens=200,
            total_tokens=4100,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow(),
        )

        warning_critical = await token_warning_service.check_usage_warning(usage_critical)
        assert warning_critical is not None
        assert warning_critical.severity == "critical"
        assert warning_critical.suggested_action == "start_new_session"
