"""Unit tests for enhanced TokenTrackingService with accurate token counting."""

from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType, TokenUsageStats
from rag_solution.services.token_tracking_service import TokenTrackingService


class TestTokenTrackingServiceEnhanced:
    """Test suite for enhanced TokenTrackingService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock()

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        return Mock()

    @pytest.fixture
    def service(self, mock_db, mock_settings):
        """Create TokenTrackingService instance."""
        return TokenTrackingService(mock_db, mock_settings)

    def test_count_tokens_with_model(self, service):
        """Test accurate token counting with model name."""
        text = "This is a test sentence."

        # Test with GPT model
        tokens = service.count_tokens(text, "gpt-3.5-turbo")
        assert tokens > 0
        assert tokens < 20  # Should be around 6 tokens

        # Test with Claude model (estimation)
        tokens = service.count_tokens(text, "claude-3-opus")
        assert tokens > 0
        assert tokens < 20

    def test_estimate_tokens(self, service):
        """Test token estimation fallback."""
        text = "This is a test sentence with several words."

        # Default estimation
        tokens = service.estimate_tokens(text)
        assert tokens > 0

        # Model-specific estimation
        gpt_tokens = service.estimate_tokens(text, "gpt-3.5-turbo")
        claude_tokens = service.estimate_tokens(text, "claude-3-opus")
        granite_tokens = service.estimate_tokens(text, "ibm/granite-3-8b-instruct")

        assert gpt_tokens > 0
        assert claude_tokens > 0
        assert granite_tokens > 0

    def test_get_context_window(self, service):
        """Test getting accurate context windows for models."""
        # OpenAI models
        assert service.get_context_window("gpt-4") == 8192
        assert service.get_context_window("gpt-4-32k") == 32768
        assert service.get_context_window("gpt-3.5-turbo") == 4096
        assert service.get_context_window("gpt-3.5-turbo-16k") == 16384

        # Claude models
        assert service.get_context_window("claude-3-opus") == 200000
        assert service.get_context_window("claude-2") == 100000

        # IBM models
        assert service.get_context_window("ibm/granite-3-8b-instruct") == 8192

        # Unknown model
        assert service.get_context_window("unknown-model") == 4096

    def test_track_usage(self, service):
        """Test token usage tracking and accumulation."""
        user_id = uuid4()

        # Create usage records
        usage1 = LLMUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.CONVERSATION,
            timestamp=datetime.now(),
            user_id=user_id,
        )

        usage2 = LLMUsage(
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            model_name="claude-3-opus",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.now(),
            user_id=user_id,
        )

        # Track usage
        service.track_usage(usage1)
        service.track_usage(usage2)

        # Verify cache
        user_key = str(user_id)
        assert user_key in service._usage_cache
        assert len(service._usage_cache[user_key]) == 2
        assert service._usage_cache[user_key][0] == usage1
        assert service._usage_cache[user_key][1] == usage2

    def test_extract_usage_from_openai_response(self, service):
        """Test extracting token usage from OpenAI response."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150

        usage = service.extract_usage_from_response(
            mock_response, "gpt-3.5-turbo", "openai"
        )

        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
        assert usage.model_name == "gpt-3.5-turbo"

    def test_extract_usage_from_anthropic_response(self, service):
        """Test extracting token usage from Anthropic response."""
        # Mock Anthropic response
        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 120
        mock_response.usage.output_tokens = 80

        usage = service.extract_usage_from_response(
            mock_response, "claude-3-opus", "anthropic"
        )

        assert usage.prompt_tokens == 120
        assert usage.completion_tokens == 80
        assert usage.total_tokens == 200
        assert usage.model_name == "claude-3-opus"

    def test_extract_usage_from_watsonx_response(self, service):
        """Test extracting token usage from WatsonX response (counts manually)."""
        prompt = "What is machine learning?"
        completion = "Machine learning is a type of AI that enables systems to learn from data."

        usage = service.extract_usage_from_response(
            None,  # WatsonX doesn't provide usage in response
            "ibm/granite-3-8b-instruct",
            "watsonx",
            prompt=prompt,
            completion=completion,
        )

        assert usage.prompt_tokens > 0
        assert usage.completion_tokens > 0
        assert usage.total_tokens == usage.prompt_tokens + usage.completion_tokens
        assert usage.model_name == "ibm/granite-3-8b-instruct"

    def test_extract_usage_fallback(self, service):
        """Test fallback token counting when provider is unknown."""
        prompt = "Test prompt"
        completion = "Test completion"

        usage = service.extract_usage_from_response(
            None,
            "unknown-model",
            "unknown-provider",
            prompt=prompt,
            completion=completion,
        )

        assert usage.prompt_tokens > 0
        assert usage.completion_tokens > 0
        assert usage.total_tokens == usage.prompt_tokens + usage.completion_tokens

    @pytest.mark.asyncio
    async def test_get_user_token_stats(self, service):
        """Test getting user token statistics."""
        user_id = uuid4()

        # Track some usage
        usage1 = LLMUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.CONVERSATION,
            timestamp=datetime.now(),
            user_id=user_id,
        )

        usage2 = LLMUsage(
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            model_name="gpt-3.5-turbo",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.now(),
            user_id=user_id,
        )

        service.track_usage(usage1)
        service.track_usage(usage2)

        # Mock repository method
        service.token_warning_repository.get_warning_stats_by_user = Mock(
            return_value={"warnings_count": 2}
        )

        # Get stats
        stats = await service.get_user_token_stats(user_id)

        assert isinstance(stats, TokenUsageStats)
        assert stats.total_tokens == 450  # 150 + 300
        assert stats.total_calls == 2
        assert ServiceType.CONVERSATION.value in stats.by_service
        assert ServiceType.SEARCH.value in stats.by_service
        assert "gpt-3.5-turbo" in stats.by_model

    @pytest.mark.asyncio
    async def test_check_usage_warning_with_accurate_context(self, service):
        """Test warning generation with accurate context windows."""
        # Mock LLM model service
        service._llm_model_service = Mock()
        service._llm_model_service.get_model_by_id = Mock(return_value=None)

        # Test with GPT-4 (8192 token context)
        usage = LLMUsage(
            prompt_tokens=7500,  # ~92% of context
            completion_tokens=100,
            total_tokens=7600,
            model_name="gpt-4",
            timestamp=datetime.now(),
        )

        warning = await service.check_usage_warning(usage)
        assert warning is not None
        assert warning.limit_tokens == 8192
        assert warning.percentage_used >= 90

        # Test with Claude 3 (200000 token context)
        usage = LLMUsage(
            prompt_tokens=50000,  # 25% of context
            completion_tokens=1000,
            total_tokens=51000,
            model_name="claude-3-opus",
            timestamp=datetime.now(),
        )

        warning = await service.check_usage_warning(usage)
        assert warning is None  # Should not warn at 25%

        # Test at 75% for Claude
        usage.prompt_tokens = 150000
        warning = await service.check_usage_warning(usage)
        assert warning is not None
        assert warning.limit_tokens == 200000
        assert 70 <= warning.percentage_used <= 80

    def test_usage_cache_limit(self, service):
        """Test that usage cache has size limits."""
        user_id = uuid4()
        user_key = str(user_id)

        # Add many usage records
        for i in range(1100):
            usage = LLMUsage(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                model_name="test-model",
                timestamp=datetime.now(),
                user_id=user_id,
            )
            service.track_usage(usage)

        # Cache should be limited to 500 most recent entries
        assert len(service._usage_cache[user_key]) == 500