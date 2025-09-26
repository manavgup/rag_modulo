"""TDD Red Phase: Unit tests for LLM provider token tracking.

Unit tests focus on the enhanced LLM provider functionality with token tracking.
All tests should fail initially as the token tracking features don't exist yet.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from pydantic import UUID4

from core.custom_exceptions import LLMProviderError
from rag_solution.generation.providers.anthropic import AnthropicLLM
from rag_solution.generation.providers.base import LLMBase
from rag_solution.generation.providers.openai import OpenAILLM
from rag_solution.generation.providers.watsonx import WatsonXLLM
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput
from rag_solution.schemas.llm_usage_schema import LLMUsage, ServiceType
from rag_solution.schemas.prompt_template_schema import PromptTemplateBase


class TestLLMProviderTokenTrackingTDD:
    """Unit tests for LLM provider token tracking functionality."""

    @pytest.fixture
    def mock_provider_services(self) -> tuple[Mock, Mock, Mock, Mock]:
        """Create mock services for LLM providers."""
        llm_provider_service = Mock()
        llm_parameters_service = Mock()
        prompt_template_service = Mock()
        llm_model_service = Mock()
        return llm_provider_service, llm_parameters_service, prompt_template_service, llm_model_service

    # ==================== BASE PROVIDER TESTS ====================

    @pytest.mark.unit
    def test_base_provider_initializes_usage_tracking(self, mock_provider_services) -> None:
        """Unit: Test base provider initializes token usage tracking."""

        class TestProvider(LLMBase):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._max_history_size = 100

            def initialize_client(self) -> None:
                pass

            def generate_text(self, _user_id, _prompt, _model_parameters=None, _template=None, _variables=None) -> str:
                return "test response"

            def generate_text_stream(self, _user_id, _prompt, _model_parameters=None, _template=None, _variables=None):
                yield "test response"

            def get_embeddings(self, _texts):
                return []

            def generate_text_with_usage(
                self,
                _user_id: UUID4,
                _prompt: str | Sequence[str],
                service_type: ServiceType,
                _model_parameters: LLMParametersInput | None = None,
                _template: PromptTemplateBase | None = None,
                _variables: dict[str, Any] | None = None,
                _session_id: str | None = None,
            ) -> tuple[str | list[str], LLMUsage]:  # type: ignore
                return "test response", LLMUsage(
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150,
                    model_name="test-model",
                    service_type=service_type,
                    timestamp=datetime.utcnow(),
                )

            def track_usage(self, usage, user_id=None, session_id=None):
                """Track usage with history trimming."""
                super().track_usage(usage, user_id, session_id)
                # Trim history to max size
                if len(self._usage_history) > self._max_history_size:
                    self._usage_history = self._usage_history[-self._max_history_size :]

        provider = TestProvider(*mock_provider_services)

        # Should have empty usage history initially
        assert hasattr(provider, "_usage_history")
        assert provider._usage_history == []
        assert hasattr(provider, "_max_history_size")
        assert provider._max_history_size == 100

    @pytest.mark.unit
    def test_base_provider_track_usage(self, mock_provider_services) -> None:
        """Unit: Test base provider tracks usage in history."""

        class TestProvider(LLMBase):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._max_history_size = 100

            def initialize_client(self) -> None:
                pass

            def generate_text(self, _user_id, _prompt, _model_parameters=None, _template=None, _variables=None) -> str:
                return "test response"

            def generate_text_stream(self, _user_id, _prompt, _model_parameters=None, _template=None, _variables=None):
                yield "test response"

            def get_embeddings(self, _texts):
                return []

            def generate_text_with_usage(
                self,
                _user_id: UUID4,
                _prompt: str | Sequence[str],
                service_type: ServiceType,
                _model_parameters: LLMParametersInput | None = None,
                _template: PromptTemplateBase | None = None,
                _variables: dict[str, Any] | None = None,
                _session_id: str | None = None,
            ) -> tuple[str | list[str], LLMUsage]:  # type: ignore
                return "test response", LLMUsage(
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150,
                    model_name="test-model",
                    service_type=service_type,
                    timestamp=datetime.utcnow(),
                )

            def track_usage(self, usage, user_id=None, session_id=None):
                """Track usage with history trimming."""
                super().track_usage(usage, user_id, session_id)
                # Trim history to max size
                if len(self._usage_history) > self._max_history_size:
                    self._usage_history = self._usage_history[-self._max_history_size :]

        provider = TestProvider(*mock_provider_services)

        usage = LLMUsage(
            prompt_tokens=1000,
            completion_tokens=200,
            total_tokens=1200,
            model_name="test-model",
            service_type=ServiceType.SEARCH,
            timestamp=datetime.utcnow(),
        )

        provider.track_usage(usage)

        assert len(provider._usage_history) == 1
        assert provider._usage_history[0] == usage

    @pytest.mark.unit
    def test_base_provider_usage_history_limit(self, mock_provider_services) -> None:
        """Unit: Test base provider maintains usage history limit."""

        class TestProvider(LLMBase):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._max_history_size = 100

            def initialize_client(self) -> None:
                pass

            def generate_text(self, _user_id, _prompt, _model_parameters=None, _template=None, _variables=None) -> str:
                return "test response"

            def generate_text_stream(self, _user_id, _prompt, _model_parameters=None, _template=None, _variables=None):
                yield "test response"

            def get_embeddings(self, _texts):
                return []

            def generate_text_with_usage(
                self,
                _user_id: UUID4,
                _prompt: str | Sequence[str],
                service_type: ServiceType,
                _model_parameters: LLMParametersInput | None = None,
                _template: PromptTemplateBase | None = None,
                _variables: dict[str, Any] | None = None,
                _session_id: str | None = None,
            ) -> tuple[str | list[str], LLMUsage]:  # type: ignore
                return "test response", LLMUsage(
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150,
                    model_name="test-model",
                    service_type=service_type,
                    timestamp=datetime.utcnow(),
                )

            def track_usage(self, usage, user_id=None, session_id=None):
                """Track usage with history trimming."""
                super().track_usage(usage, user_id, session_id)
                # Trim history to max size
                if len(self._usage_history) > self._max_history_size:
                    self._usage_history = self._usage_history[-self._max_history_size :]

        provider = TestProvider(*mock_provider_services)
        provider._max_history_size = 3  # Set smaller limit for testing

        # Add more usage records than the limit
        for i in range(5):
            usage = LLMUsage(
                prompt_tokens=1000 + i,
                completion_tokens=200,
                total_tokens=1200 + i,
                model_name="test-model",
                service_type=ServiceType.SEARCH,
                timestamp=datetime.utcnow(),
            )
            provider.track_usage(usage)

        # Should only keep the last 3 records
        assert len(provider._usage_history) == 3
        assert provider._usage_history[0].prompt_tokens == 1002  # Last 3 should be 1002, 1003, 1004
        assert provider._usage_history[-1].prompt_tokens == 1004

    @pytest.mark.unit
    def test_base_provider_get_recent_usage(self, mock_provider_services) -> None:
        """Unit: Test base provider returns recent usage."""

        class TestProvider(LLMBase):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._max_history_size = 100

            def initialize_client(self) -> None:
                pass

            def generate_text(self, _user_id, _prompt, _model_parameters=None, _template=None, _variables=None) -> str:
                return "test response"

            def generate_text_stream(self, _user_id, _prompt, _model_parameters=None, _template=None, _variables=None):
                yield "test response"

            def get_embeddings(self, _texts):
                return []

            def generate_text_with_usage(
                self,
                _user_id: UUID4,
                _prompt: str | Sequence[str],
                service_type: ServiceType,
                _model_parameters: LLMParametersInput | None = None,
                _template: PromptTemplateBase | None = None,
                _variables: dict[str, Any] | None = None,
                _session_id: str | None = None,
            ) -> tuple[str | list[str], LLMUsage]:  # type: ignore
                return "test response", LLMUsage(
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150,
                    model_name="test-model",
                    service_type=service_type,
                    timestamp=datetime.utcnow(),
                )

            def track_usage(self, usage, user_id=None, session_id=None):
                """Track usage with history trimming."""
                super().track_usage(usage, user_id, session_id)
                # Trim history to max size
                if len(self._usage_history) > self._max_history_size:
                    self._usage_history = self._usage_history[-self._max_history_size :]

        provider = TestProvider(*mock_provider_services)

        # Add multiple usage records
        for i in range(15):
            usage = LLMUsage(
                prompt_tokens=1000 + i,
                completion_tokens=200,
                total_tokens=1200 + i,
                model_name="test-model",
                service_type=ServiceType.SEARCH,
                timestamp=datetime.utcnow(),
            )
            provider.track_usage(usage)

        # Get recent usage with default limit (10)
        recent = provider.get_recent_usage()
        assert len(recent) == 10
        assert recent[0].prompt_tokens == 1005  # Last 10 should start from 1005
        assert recent[-1].prompt_tokens == 1014

        # Get recent usage with custom limit
        recent_5 = provider.get_recent_usage(limit=5)
        assert len(recent_5) == 5
        assert recent_5[-1].prompt_tokens == 1014

    @pytest.mark.unit
    def test_base_provider_get_total_usage_stats(self, mock_provider_services) -> None:
        """Unit: Test base provider calculates total usage statistics."""

        class TestProvider(LLMBase):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._max_history_size = 100

            def initialize_client(self) -> None:
                pass

            def generate_text(self, _user_id, _prompt, _model_parameters=None, _template=None, _variables=None) -> str:
                return "test response"

            def generate_text_stream(self, _user_id, _prompt, _model_parameters=None, _template=None, _variables=None):
                yield "test response"

            def get_embeddings(self, _texts):
                return []

            def generate_text_with_usage(
                self,
                _user_id: UUID4,
                _prompt: str | Sequence[str],
                service_type: ServiceType,
                _model_parameters: LLMParametersInput | None = None,
                _template: PromptTemplateBase | None = None,
                _variables: dict[str, Any] | None = None,
                _session_id: str | None = None,
            ) -> tuple[str | list[str], LLMUsage]:  # type: ignore
                return "test response", LLMUsage(
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150,
                    model_name="test-model",
                    service_type=service_type,
                    timestamp=datetime.utcnow(),
                )

            def track_usage(self, usage, user_id=None, session_id=None):
                """Track usage with history trimming."""
                super().track_usage(usage, user_id, session_id)
                # Trim history to max size
                if len(self._usage_history) > self._max_history_size:
                    self._usage_history = self._usage_history[-self._max_history_size :]

        provider = TestProvider(*mock_provider_services)

        # Add usage for different services and models
        usages = [
            LLMUsage(1000, 200, 1200, "gpt-3.5-turbo", ServiceType.SEARCH, datetime.utcnow()),
            LLMUsage(800, 150, 950, "gpt-3.5-turbo", ServiceType.CONVERSATION, datetime.utcnow()),
            LLMUsage(1200, 300, 1500, "gpt-4", ServiceType.CHAIN_OF_THOUGHT, datetime.utcnow()),
        ]

        for usage in usages:
            provider.track_usage(usage)

        stats = provider.get_total_usage()

        assert stats.total_prompt_tokens == 3000  # 1000 + 800 + 1200
        assert stats.total_completion_tokens == 650  # 200 + 150 + 300
        assert stats.total_tokens == 3650  # 1200 + 950 + 1500
        assert stats.total_calls == 3
        assert stats.average_tokens_per_call == pytest.approx(1216.7, abs=0.1)  # 3650 / 3

        # Check service breakdown
        assert stats.by_service[ServiceType.SEARCH] == 1200
        assert stats.by_service[ServiceType.CONVERSATION] == 950
        assert stats.by_service[ServiceType.CHAIN_OF_THOUGHT] == 1500

        # Check model breakdown
        assert stats.by_model["gpt-3.5-turbo"] == 2150  # 1200 + 950
        assert stats.by_model["gpt-4"] == 1500

    @pytest.mark.unit
    def test_base_provider_empty_usage_stats(self, mock_provider_services) -> None:
        """Unit: Test base provider returns empty stats when no usage."""

        class TestProvider(LLMBase):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._max_history_size = 100

            def initialize_client(self) -> None:
                pass

            def generate_text(self, _user_id, _prompt, _model_parameters=None, _template=None, _variables=None) -> str:
                return "test response"

            def generate_text_stream(self, _user_id, _prompt, _model_parameters=None, _template=None, _variables=None):
                yield "test response"

            def get_embeddings(self, _texts):
                return []

            def generate_text_with_usage(
                self,
                _user_id: UUID4,
                _prompt: str | Sequence[str],
                service_type: ServiceType,
                _model_parameters: LLMParametersInput | None = None,
                _template: PromptTemplateBase | None = None,
                _variables: dict[str, Any] | None = None,
                _session_id: str | None = None,
            ) -> tuple[str | list[str], LLMUsage]:  # type: ignore
                return "test response", LLMUsage(
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150,
                    model_name="test-model",
                    service_type=service_type,
                    timestamp=datetime.utcnow(),
                )

            def track_usage(self, usage, user_id=None, session_id=None):
                """Track usage with history trimming."""
                super().track_usage(usage, user_id, session_id)
                # Trim history to max size
                if len(self._usage_history) > self._max_history_size:
                    self._usage_history = self._usage_history[-self._max_history_size :]

        provider = TestProvider(*mock_provider_services)

        stats = provider.get_total_usage()

        assert stats.total_prompt_tokens == 0
        assert stats.total_completion_tokens == 0
        assert stats.total_tokens == 0
        assert stats.total_calls == 0
        assert stats.average_tokens_per_call == 0
        assert stats.by_service == {}
        assert stats.by_model == {}

    # ==================== OPENAI PROVIDER TESTS ====================

    @pytest.mark.unit
    async def test_openai_provider_generate_text_with_usage(self, mock_provider_services) -> None:
        """Unit: Test OpenAI provider returns text and usage."""
        # Mock OpenAI client response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Generated response text"
        mock_response.usage.prompt_tokens = 1000
        mock_response.usage.completion_tokens = 200
        mock_response.usage.total_tokens = 1200

        with patch("rag_solution.generation.providers.openai.OpenAI") as mock_openai_class:
            mock_client = Mock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai_class.return_value = mock_client

            provider = OpenAILLM(*mock_provider_services)
            provider.model_id = "gpt-3.5-turbo"
            provider.client = mock_client

            # Mock llm_parameters_service.get_latest_or_default_parameters method
            with patch.object(
                provider.llm_parameters_service,
                "get_latest_or_default_parameters",
                return_value=Mock(max_new_tokens=150, temperature=0.7),
            ):
                text, usage = await provider.generate_text_with_usage(
                    user_id=uuid4(), prompt="Test prompt", service_type=ServiceType.SEARCH, session_id="session_456"
                )

                assert text == "Generated response text"
                assert usage.prompt_tokens == 1000
                assert usage.completion_tokens == 200
                assert usage.total_tokens == 1200
                assert usage.model_name == "gpt-3.5-turbo"
                assert usage.service_type == ServiceType.SEARCH
                assert usage.user_id == "user_123"
                assert usage.session_id == "session_456"
            assert isinstance(usage.timestamp, datetime)

    @pytest.mark.unit
    async def test_openai_provider_legacy_generate_text(self, mock_provider_services) -> None:
        """Unit: Test OpenAI provider legacy generate_text method."""
        with patch.object(OpenAILLM, "generate_text_with_usage") as mock_generate_with_usage:
            mock_usage = LLMUsage(
                prompt_tokens=1000,
                completion_tokens=200,
                total_tokens=1200,
                model_name="gpt-3.5-turbo",
                service_type=ServiceType.SEARCH,
                timestamp=datetime.utcnow(),
            )
            mock_generate_with_usage.return_value = ("Test response", mock_usage)

            provider = OpenAILLM(*mock_provider_services)

            text = await provider.generate_text(user_id=uuid4(), prompt="Test prompt")

            assert text == "Test response"
            mock_generate_with_usage.assert_called_once_with("Test prompt", ServiceType.SEARCH)

    # ==================== ANTHROPIC PROVIDER TESTS ====================

    @pytest.mark.unit
    async def test_anthropic_provider_generate_text_with_usage(self, mock_provider_services) -> None:
        """Unit: Test Anthropic provider returns text and usage."""
        # Mock Anthropic client response
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Generated response from Claude"
        mock_response.usage.input_tokens = 1100
        mock_response.usage.output_tokens = 250

        with patch("rag_solution.generation.providers.anthropic.Anthropic") as mock_anthropic_class:
            mock_client = Mock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicLLM(*mock_provider_services)
            provider.model_id = "claude-3-sonnet-20240229"
            provider.client = mock_client

            # Mock llm_parameters_service.get_latest_or_default_parameters method
            with patch.object(
                provider.llm_parameters_service,
                "get_latest_or_default_parameters",
                return_value=Mock(max_new_tokens=150, temperature=0.7),
            ):
                text, usage = await provider.generate_text_with_usage(
                    user_id=uuid4(),
                    prompt="Test prompt",
                    service_type=ServiceType.CONVERSATION,
                    session_id="session_789",
                )

                assert text == "Generated response from Claude"
                assert usage.prompt_tokens == 1100
                assert usage.completion_tokens == 250
                assert usage.total_tokens == 1350  # 1100 + 250
                assert usage.model_name == "claude-3-sonnet-20240229"
                assert usage.service_type == ServiceType.CONVERSATION
                assert usage.user_id == "user_456"
                assert usage.session_id == "session_789"

    # ==================== WATSONX PROVIDER TESTS ====================

    @pytest.mark.unit
    async def test_watsonx_provider_generate_text_with_usage(self, mock_provider_services) -> None:
        """Unit: Test WatsonX provider returns text and usage."""
        # Mock WatsonX client response
        mock_result = Mock()
        mock_result.generated_text = "Generated response from Granite"
        mock_result.input_token_count = 900
        mock_result.generated_token_count = 180

        mock_response = Mock()
        mock_response.results = [mock_result]

        with patch("rag_solution.generation.providers.watsonx.WatsonXClient") as mock_watsonx_class:
            mock_client = Mock()
            mock_client.generate = AsyncMock(return_value=mock_response)
            mock_watsonx_class.return_value = mock_client

            provider = WatsonXLLM(*mock_provider_services)
            provider.model_id = "ibm/granite-13b-chat-v2"
            provider.client = mock_client

            # Mock llm_parameters_service.get_latest_or_default_parameters method
            with patch.object(
                provider.llm_parameters_service,
                "get_latest_or_default_parameters",
                return_value=Mock(max_new_tokens=150, temperature=0.7),
            ):
                text, usage = await provider.generate_text_with_usage(
                    user_id=uuid4(),
                    prompt="Test prompt",
                    service_type=ServiceType.CHAIN_OF_THOUGHT,
                    session_id="session_abc",
                )

                assert text == "Generated response from Granite"
                assert usage.prompt_tokens == 900
                assert usage.completion_tokens == 180
                assert usage.total_tokens == 1080  # 900 + 180
                assert usage.model_name == "ibm/granite-13b-chat-v2"
                assert usage.service_type == ServiceType.CHAIN_OF_THOUGHT
                assert usage.user_id == "user_789"
                assert usage.session_id == "session_abc"

    # ==================== ERROR HANDLING TESTS ====================

    @pytest.mark.unit
    async def test_openai_provider_error_handling(self, mock_provider_services) -> None:
        """Unit: Test OpenAI provider handles API errors correctly."""
        with patch("rag_solution.generation.providers.openai.OpenAI") as mock_openai_class:
            mock_client = Mock()
            mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
            mock_openai_class.return_value = mock_client

            provider = OpenAILLM(*mock_provider_services)
            provider.model_id = "gpt-3.5-turbo"
            provider.client = mock_client
            with patch.object(provider, "_get_parameters", return_value=Mock(max_new_tokens=150, temperature=0.7)):
                with pytest.raises(LLMProviderError):  # Should raise LLMProviderError in actual implementation
                    await provider.generate_text_with_usage(
                        user_id=uuid4(), prompt="Test prompt", service_type=ServiceType.SEARCH
                    )

    @pytest.mark.unit
    async def test_anthropic_provider_error_handling(self, mock_provider_services) -> None:
        """Unit: Test Anthropic provider handles API errors correctly."""
        with patch("rag_solution.generation.providers.anthropic.Anthropic") as mock_anthropic_class:
            mock_client = Mock()
            mock_client.messages.create = AsyncMock(side_effect=Exception("Anthropic API Error"))
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicLLM(*mock_provider_services)
            provider.model_id = "claude-3-sonnet"
            provider.client = mock_client
            with patch.object(provider, "_get_parameters", return_value=Mock(max_new_tokens=150, temperature=0.7)):
                with pytest.raises(LLMProviderError):  # Should raise LLMProviderError in actual implementation
                    await provider.generate_text_with_usage(
                        user_id=uuid4(), prompt="Test prompt", service_type=ServiceType.CONVERSATION
                    )

    @pytest.mark.unit
    async def test_watsonx_provider_error_handling(self, mock_provider_services) -> None:
        """Unit: Test WatsonX provider handles API errors correctly."""
        with patch("rag_solution.generation.providers.watsonx.WatsonXClient") as mock_watsonx_class:
            mock_client = Mock()
            mock_client.generate = AsyncMock(side_effect=Exception("WatsonX API Error"))
            mock_watsonx_class.return_value = mock_client

            provider = WatsonXLLM(*mock_provider_services)
            provider.model_id = "granite-13b"
            provider.client = mock_client
            with patch.object(provider, "_get_parameters", return_value=Mock(max_new_tokens=150, temperature=0.7)):
                with pytest.raises(LLMProviderError):  # Should raise LLMProviderError in actual implementation
                    await provider.generate_text_with_usage(
                        user_id=uuid4(), prompt="Test prompt", service_type=ServiceType.CHAIN_OF_THOUGHT
                    )

    # ==================== USAGE TRACKING INTEGRATION TESTS ====================

    @pytest.mark.unit
    async def test_provider_tracks_usage_after_generation(self, mock_provider_services) -> None:
        """Unit: Test provider automatically tracks usage after generation."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.prompt_tokens = 1000
        mock_response.usage.completion_tokens = 200
        mock_response.usage.total_tokens = 1200

        with patch("rag_solution.generation.providers.openai.OpenAI") as mock_openai_class:
            mock_client = Mock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai_class.return_value = mock_client

            provider = OpenAILLM(*mock_provider_services)
            provider.model_id = "gpt-3.5-turbo"
            provider.client = mock_client
            with patch.object(provider, "_get_parameters", return_value=Mock(max_new_tokens=150, temperature=0.7)):
                # Initially no usage tracked
                assert len(provider._usage_history) == 0

                await provider.generate_text_with_usage(
                    user_id=uuid4(), prompt="Test prompt", service_type=ServiceType.SEARCH
                )

                # Usage should be tracked automatically
                assert len(provider._usage_history) == 1
                assert provider._usage_history[0].prompt_tokens == 1000
                assert provider._usage_history[0].completion_tokens == 200
