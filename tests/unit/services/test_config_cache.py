"""Unit tests for ConfigCache service.

Tests request-scoped caching behavior for read-mostly configuration data.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from rag_solution.services.config_cache import ConfigCache


@pytest.mark.unit
class TestConfigCache:
    """Tests for ConfigCache per-request caching."""

    def setup_method(self) -> None:
        self.mock_db = MagicMock()
        self.cache = ConfigCache(self.mock_db)

    @patch("rag_solution.services.llm_provider_service.LLMProviderService")
    def test_caches_on_second_call(self, mock_provider_cls: MagicMock) -> None:
        """Second call returns cached value without querying the service again."""
        mock_service = MagicMock()
        mock_service.get_default_provider.return_value = {"name": "watsonx"}
        mock_provider_cls.return_value = mock_service

        result1 = self.cache.get_default_provider()
        result2 = self.cache.get_default_provider()

        assert result1 == {"name": "watsonx"}
        assert result2 == {"name": "watsonx"}
        # Service constructor called only once (first call), not on the cached second call
        mock_provider_cls.assert_called_once_with(self.mock_db)
        mock_service.get_default_provider.assert_called_once()

    @patch("rag_solution.services.llm_provider_service.LLMProviderService")
    def test_different_users_separate_entries(self, mock_provider_cls: MagicMock) -> None:
        """Different user IDs result in separate cache entries, both queried."""
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        mock_service = MagicMock()
        mock_service.get_user_provider.side_effect = [
            {"provider": "a"},
            {"provider": "b"},
        ]
        mock_provider_cls.return_value = mock_service

        result_a = self.cache.get_user_provider(user_a)
        result_b = self.cache.get_user_provider(user_b)

        assert result_a == {"provider": "a"}
        assert result_b == {"provider": "b"}
        assert mock_service.get_user_provider.call_count == 2

    @patch("rag_solution.services.llm_provider_service.LLMProviderService")
    def test_invalidate_clears_all(self, mock_provider_cls: MagicMock) -> None:
        """invalidate() with no key clears entire cache, forcing re-query."""
        mock_service = MagicMock()
        mock_service.get_default_provider.side_effect = [
            {"name": "watsonx"},
            {"name": "watsonx-v2"},
        ]
        mock_provider_cls.return_value = mock_service

        result1 = self.cache.get_default_provider()
        assert result1 == {"name": "watsonx"}

        self.cache.invalidate()

        result2 = self.cache.get_default_provider()
        assert result2 == {"name": "watsonx-v2"}
        assert mock_service.get_default_provider.call_count == 2

    @patch("rag_solution.services.llm_provider_service.LLMProviderService")
    def test_invalidate_specific_key(self, mock_provider_cls: MagicMock) -> None:
        """invalidate(key) clears only that key; other cached entries remain."""
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        mock_service = MagicMock()
        mock_service.get_user_provider.side_effect = [
            {"provider": "a"},
            {"provider": "b"},
            {"provider": "a-refreshed"},
        ]
        mock_provider_cls.return_value = mock_service

        self.cache.get_user_provider(user_a)
        self.cache.get_user_provider(user_b)

        # Invalidate only user_a's entry
        self.cache.invalidate(f"provider:{user_a}")

        result_a = self.cache.get_user_provider(user_a)
        result_b = self.cache.get_user_provider(user_b)

        # user_a was re-queried, user_b still cached
        assert result_a == {"provider": "a-refreshed"}
        assert result_b == {"provider": "b"}
        assert mock_service.get_user_provider.call_count == 3
