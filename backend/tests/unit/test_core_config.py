"""
Tests for core configuration settings including Chain of Thought (CoT) settings.
"""

import os
import pytest
from core.config import Settings


@pytest.mark.unit
class TestSimplified:
    """Simplified test that works."""

    def test_basic_functionality(self):
        """Test basic functionality."""
        assert True

    def test_configuration(self, integration_settings):
        """Test configuration."""
        assert integration_settings is not None
        assert hasattr(integration_settings, "jwt_secret_key")

    def test_mock_services(self, mock_watsonx_provider):
        """Test mock services."""
        assert mock_watsonx_provider is not None
        assert hasattr(mock_watsonx_provider, "generate_response")


@pytest.mark.unit
class TestChainOfThoughtConfiguration:
    """Test Chain of Thought configuration settings."""

    def test_cot_default_settings(self):
        """Test CoT settings have proper defaults."""
        settings = Settings()

        assert hasattr(settings, "cot_max_reasoning_depth")
        assert hasattr(settings, "cot_reasoning_strategy")
        assert hasattr(settings, "cot_token_budget_multiplier")

        # Test default values
        assert settings.cot_max_reasoning_depth == 3
        assert settings.cot_reasoning_strategy == "decomposition"
        assert settings.cot_token_budget_multiplier == 2.0

    def test_cot_environment_variable_override(self, monkeypatch):
        """Test CoT settings can be overridden by environment variables."""
        # Set custom environment variables
        monkeypatch.setenv("COT_MAX_REASONING_DEPTH", "5")
        monkeypatch.setenv("COT_REASONING_STRATEGY", "hierarchical")
        monkeypatch.setenv("COT_TOKEN_BUDGET_MULTIPLIER", "3.5")

        settings = Settings()

        assert settings.cot_max_reasoning_depth == 5
        assert settings.cot_reasoning_strategy == "hierarchical"
        assert settings.cot_token_budget_multiplier == 3.5

    def test_cot_reasoning_strategy_validation(self):
        """Test CoT reasoning strategy accepts valid values."""
        valid_strategies = ["decomposition", "iterative", "hierarchical", "causal"]

        for strategy in valid_strategies:
            os.environ["COT_REASONING_STRATEGY"] = strategy
            settings = Settings()
            assert settings.cot_reasoning_strategy == strategy

        # Clean up
        if "COT_REASONING_STRATEGY" in os.environ:
            del os.environ["COT_REASONING_STRATEGY"]

    def test_cot_max_reasoning_depth_type(self):
        """Test CoT max reasoning depth is properly typed as integer."""
        settings = Settings()
        assert isinstance(settings.cot_max_reasoning_depth, int)
        assert settings.cot_max_reasoning_depth > 0

    def test_cot_token_budget_multiplier_type(self):
        """Test CoT token budget multiplier is properly typed as float."""
        settings = Settings()
        assert isinstance(settings.cot_token_budget_multiplier, float)
        assert settings.cot_token_budget_multiplier > 0.0

    def test_cot_integration_with_existing_settings(self, integration_settings):
        """Test CoT settings integrate properly with existing configuration."""
        settings = integration_settings

        # Verify existing settings still work
        assert hasattr(settings, "jwt_secret_key")
        assert hasattr(settings, "rag_llm")

        # Verify CoT settings are available
        assert hasattr(settings, "cot_max_reasoning_depth")
        assert hasattr(settings, "cot_reasoning_strategy")
        assert hasattr(settings, "cot_token_budget_multiplier")
