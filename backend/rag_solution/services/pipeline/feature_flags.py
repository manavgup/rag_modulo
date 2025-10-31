"""
Feature flags for pipeline architecture.

This module provides feature flag functionality for gradual rollout
of the new pipeline architecture.
"""

import os
from enum import Enum

from core.logging_utils import get_logger

logger = get_logger("services.pipeline.feature_flags")


class FeatureFlag(str, Enum):
    """Feature flags for search pipeline."""

    USE_PIPELINE_ARCHITECTURE = "USE_PIPELINE_ARCHITECTURE"


class FeatureFlagManager:
    """
    Manages feature flags for gradual rollout.

    Supports environment variables and percentage-based rollouts.
    """

    def __init__(self) -> None:
        """Initialize the feature flag manager."""
        self._flags: dict[str, bool] = {}
        self._rollout_percentage: dict[str, int] = {}
        logger.debug("Feature flag manager initialized")

    def is_enabled(self, flag: FeatureFlag, user_id: str | None = None) -> bool:
        """
        Check if a feature flag is enabled.

        Args:
            flag: Feature flag to check
            user_id: Optional user ID for percentage-based rollout

        Returns:
            True if feature is enabled, False otherwise
        """
        # Check environment variable first
        env_value = os.getenv(flag.value)
        if env_value is not None:
            enabled = env_value.lower() in ("true", "1", "yes", "on")
            logger.debug("Feature flag %s from env: %s", flag.value, enabled)
            return enabled

        # Check explicit flag setting
        if flag.value in self._flags:
            enabled = self._flags[flag.value]
            logger.debug("Feature flag %s from config: %s", flag.value, enabled)
            return enabled

        # Check percentage rollout
        if flag.value in self._rollout_percentage and user_id:
            percentage = self._rollout_percentage[flag.value]
            # Simple hash-based rollout
            user_hash = hash(user_id) % 100
            enabled = user_hash < percentage
            logger.debug(
                "Feature flag %s percentage rollout (%d%%): %s (user_hash=%d)",
                flag.value,
                percentage,
                enabled,
                user_hash,
            )
            return enabled

        # Default to disabled
        logger.debug("Feature flag %s not found, defaulting to False", flag.value)
        return False

    def enable(self, flag: FeatureFlag) -> None:
        """
        Enable a feature flag.

        Args:
            flag: Feature flag to enable
        """
        self._flags[flag.value] = True
        logger.info("Feature flag %s enabled", flag.value)

    def disable(self, flag: FeatureFlag) -> None:
        """
        Disable a feature flag.

        Args:
            flag: Feature flag to disable
        """
        self._flags[flag.value] = False
        logger.info("Feature flag %s disabled", flag.value)

    def set_rollout_percentage(self, flag: FeatureFlag, percentage: int) -> None:
        """
        Set percentage-based rollout for a feature flag.

        Args:
            flag: Feature flag to configure
            percentage: Percentage of users to enable (0-100)

        Raises:
            ValueError: If percentage is not between 0 and 100
        """
        if not 0 <= percentage <= 100:
            raise ValueError(f"Percentage must be between 0 and 100, got {percentage}")

        self._rollout_percentage[flag.value] = percentage
        logger.info("Feature flag %s rollout set to %d%%", flag.value, percentage)


# Global feature flag manager instance
_feature_flag_manager = FeatureFlagManager()


def get_feature_flag_manager() -> FeatureFlagManager:
    """
    Get the global feature flag manager instance.

    Returns:
        Global FeatureFlagManager instance
    """
    return _feature_flag_manager
