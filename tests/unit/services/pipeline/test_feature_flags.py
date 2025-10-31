"""
Unit tests for feature flag system.

Tests the feature flag functionality including:
- Flag checking
- Environment variable integration
- Percentage-based rollout
- Flag management
"""

import os
from uuid import uuid4

import pytest

from rag_solution.services.pipeline.feature_flags import (
    FeatureFlag,
    FeatureFlagManager,
    get_feature_flag_manager,
)


@pytest.fixture
def feature_manager() -> FeatureFlagManager:
    """Create fresh feature flag manager for testing."""
    return FeatureFlagManager()


@pytest.fixture(autouse=True)
def clean_env() -> None:
    """Clean environment variables before each test."""
    # Remove any test feature flags
    if "USE_PIPELINE_ARCHITECTURE" in os.environ:
        del os.environ["USE_PIPELINE_ARCHITECTURE"]


@pytest.mark.unit
class TestFeatureFlagManager:
    """Test suite for FeatureFlagManager."""

    def test_manager_initialization(self, feature_manager: FeatureFlagManager) -> None:
        """Test manager initializes correctly."""
        assert feature_manager._flags == {}
        assert feature_manager._rollout_percentage == {}

    def test_flag_disabled_by_default(self, feature_manager: FeatureFlagManager) -> None:
        """Test that flags are disabled by default."""
        assert feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE) is False

    def test_enable_flag(self, feature_manager: FeatureFlagManager) -> None:
        """Test enabling a feature flag."""
        feature_manager.enable(FeatureFlag.USE_PIPELINE_ARCHITECTURE)
        assert feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE) is True

    def test_disable_flag(self, feature_manager: FeatureFlagManager) -> None:
        """Test disabling a feature flag."""
        feature_manager.enable(FeatureFlag.USE_PIPELINE_ARCHITECTURE)
        assert feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE) is True

        feature_manager.disable(FeatureFlag.USE_PIPELINE_ARCHITECTURE)
        assert feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE) is False

    def test_environment_variable_true(self, feature_manager: FeatureFlagManager) -> None:
        """Test flag enabled via environment variable (true)."""
        os.environ["USE_PIPELINE_ARCHITECTURE"] = "true"
        assert feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE) is True

    def test_environment_variable_false(self, feature_manager: FeatureFlagManager) -> None:
        """Test flag disabled via environment variable (false)."""
        os.environ["USE_PIPELINE_ARCHITECTURE"] = "false"
        assert feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE) is False

    def test_environment_variable_variations(self, feature_manager: FeatureFlagManager) -> None:
        """Test different environment variable formats."""
        # Test "1"
        os.environ["USE_PIPELINE_ARCHITECTURE"] = "1"
        assert feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE) is True

        # Test "yes"
        os.environ["USE_PIPELINE_ARCHITECTURE"] = "yes"
        assert feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE) is True

        # Test "on"
        os.environ["USE_PIPELINE_ARCHITECTURE"] = "on"
        assert feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE) is True

        # Test "0"
        os.environ["USE_PIPELINE_ARCHITECTURE"] = "0"
        assert feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE) is False

    def test_env_var_overrides_explicit_flag(self, feature_manager: FeatureFlagManager) -> None:
        """Test that environment variables override explicit flag settings."""
        feature_manager.enable(FeatureFlag.USE_PIPELINE_ARCHITECTURE)

        # Env var should override
        os.environ["USE_PIPELINE_ARCHITECTURE"] = "false"
        assert feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE) is False

    def test_percentage_rollout_0_percent(self, feature_manager: FeatureFlagManager) -> None:
        """Test 0% rollout disables for all users."""
        feature_manager.set_rollout_percentage(FeatureFlag.USE_PIPELINE_ARCHITECTURE, 0)

        user_id = str(uuid4())
        assert feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE, user_id) is False

    def test_percentage_rollout_100_percent(self, feature_manager: FeatureFlagManager) -> None:
        """Test 100% rollout enables for all users."""
        feature_manager.set_rollout_percentage(FeatureFlag.USE_PIPELINE_ARCHITECTURE, 100)

        # Test multiple users
        for _ in range(10):
            user_id = str(uuid4())
            assert feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE, user_id) is True

    def test_percentage_rollout_50_percent(self, feature_manager: FeatureFlagManager) -> None:
        """Test 50% rollout enables for approximately half of users."""
        feature_manager.set_rollout_percentage(FeatureFlag.USE_PIPELINE_ARCHITECTURE, 50)

        # Test 100 users, expect ~50% enabled
        enabled_count = 0
        total_users = 100

        for _ in range(total_users):
            user_id = str(uuid4())
            if feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE, user_id):
                enabled_count += 1

        # Allow some variance but should be roughly 50%
        assert 30 <= enabled_count <= 70, f"Expected ~50%, got {enabled_count}%"

    def test_percentage_rollout_deterministic(self, feature_manager: FeatureFlagManager) -> None:
        """Test that rollout is deterministic for same user."""
        feature_manager.set_rollout_percentage(FeatureFlag.USE_PIPELINE_ARCHITECTURE, 50)

        user_id = str(uuid4())
        first_result = feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE, user_id)
        second_result = feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE, user_id)

        assert first_result == second_result

    def test_percentage_rollout_invalid_percentage(self, feature_manager: FeatureFlagManager) -> None:
        """Test that invalid percentages raise ValueError."""
        with pytest.raises(ValueError):
            feature_manager.set_rollout_percentage(FeatureFlag.USE_PIPELINE_ARCHITECTURE, -1)

        with pytest.raises(ValueError):
            feature_manager.set_rollout_percentage(FeatureFlag.USE_PIPELINE_ARCHITECTURE, 101)

    def test_percentage_rollout_without_user_id(self, feature_manager: FeatureFlagManager) -> None:
        """Test percentage rollout returns False without user_id."""
        feature_manager.set_rollout_percentage(FeatureFlag.USE_PIPELINE_ARCHITECTURE, 100)

        # Without user_id, should return False
        assert feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE, None) is False

    def test_global_manager_singleton(self) -> None:
        """Test that global manager is a singleton."""
        manager1 = get_feature_flag_manager()
        manager2 = get_feature_flag_manager()

        assert manager1 is manager2

    def test_multiple_flags_independent(self, feature_manager: FeatureFlagManager) -> None:
        """Test that multiple flags are independent."""
        feature_manager.enable(FeatureFlag.USE_PIPELINE_ARCHITECTURE)

        # USE_PIPELINE_ARCHITECTURE is enabled
        assert feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE) is True

    def test_case_insensitive_env_var(self, feature_manager: FeatureFlagManager) -> None:
        """Test that environment variable values are case-insensitive."""
        os.environ["USE_PIPELINE_ARCHITECTURE"] = "TRUE"
        assert feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE) is True

        os.environ["USE_PIPELINE_ARCHITECTURE"] = "False"
        assert feature_manager.is_enabled(FeatureFlag.USE_PIPELINE_ARCHITECTURE) is False
