"""
Timeout configuration management for different environments.

Provides environment-specific timeout settings to handle network latency
and slow responses in CI environments.
"""

from typing import Any, Optional
import os


class TimeoutManager:
    """
    Manages timeout configurations for different environments and services.

    Addresses network latency and slow response issues by providing
    appropriate timeout values for local, CI, and production environments.
    """

    def __init__(self):
        """Initialize timeout manager with environment-specific configurations."""
        self.timeout_profiles = {
            "local": {"http_timeout": 10, "database_timeout": 15, "vector_store_timeout": 20, "health_check_timeout": 5, "file_upload_timeout": 30, "api_call_timeout": 10},
            "ci": {"http_timeout": 30, "database_timeout": 60, "vector_store_timeout": 90, "health_check_timeout": 45, "file_upload_timeout": 120, "api_call_timeout": 45},
            "production": {"http_timeout": 20, "database_timeout": 30, "vector_store_timeout": 60, "health_check_timeout": 30, "file_upload_timeout": 90, "api_call_timeout": 30},
        }

        # Detect current environment
        self.current_environment = self._detect_environment()

    def get_timeout_config_for_environment(self, environment: str) -> dict[str, int]:
        """
        Get timeout configuration for specified environment.

        Args:
            environment: Environment name ("local", "ci", "production")

        Returns:
            Dict containing timeout values in seconds
        """
        if environment not in self.timeout_profiles:
            environment = "local"  # Default fallback

        return self.timeout_profiles[environment].copy()

    def get_current_timeout_config(self) -> dict[str, int]:
        """
        Get timeout configuration for current environment.

        Returns:
            Dict containing timeout values for current environment
        """
        return self.get_timeout_config_for_environment(self.current_environment)

    def get_timeout_for_service(self, service_type: str, environment: Optional[str] = None) -> int:
        """
        Get timeout value for specific service type.

        Args:
            service_type: Type of service (http, database, vector_store, etc.)
            environment: Environment name (uses current if None)

        Returns:
            Timeout value in seconds
        """
        env = environment or self.current_environment
        config = self.get_timeout_config_for_environment(env)

        timeout_key = f"{service_type}_timeout"
        return config.get(timeout_key, config.get("http_timeout", 30))

    def _detect_environment(self) -> str:
        """
        Detect current environment based on environment variables and context.

        Returns:
            Environment name string
        """
        # Check for CI environment indicators
        ci_indicators = ["CI", "CONTINUOUS_INTEGRATION", "GITHUB_ACTIONS", "TRAVIS", "CIRCLECI", "JENKINS_URL", "BUILDKITE"]

        for indicator in ci_indicators:
            if os.getenv(indicator):
                return "ci"

        # Check for production indicators
        if os.getenv("ENVIRONMENT") == "production":
            return "production"
        if os.getenv("NODE_ENV") == "production":
            return "production"

        # Default to local
        return "local"

    def create_environment_specific_config(self, base_config: dict[str, Any]) -> dict[str, Any]:
        """
        Create environment-specific configuration by applying timeout adjustments.

        Args:
            base_config: Base configuration to adjust

        Returns:
            Environment-adjusted configuration
        """
        adjusted_config = base_config.copy()
        timeout_config = self.get_current_timeout_config()

        # Apply timeout adjustments to configuration
        for key, value in adjusted_config.items():
            if key.endswith("_timeout") or "timeout" in key.lower():
                # Use environment-specific timeout if available
                env_timeout = timeout_config.get(key, timeout_config.get("api_call_timeout"))
                adjusted_config[key] = env_timeout

        return adjusted_config

    def get_adaptive_timeout(self, base_timeout: int, service_type: str = "http") -> int:
        """
        Get adaptive timeout based on current environment performance.

        Args:
            base_timeout: Base timeout value
            service_type: Type of service for timeout adjustment

        Returns:
            Adjusted timeout value
        """
        environment_multipliers = {
            "local": 1.0,
            "ci": 2.0,  # CI runners can be slower
            "production": 1.5,  # Production has more load
        }

        multiplier = environment_multipliers.get(self.current_environment, 1.0)
        adaptive_timeout = int(base_timeout * multiplier)

        # Apply service-specific adjustments
        service_adjustments = {"database": 1.5, "vector_store": 2.0, "file_upload": 3.0}

        if service_type in service_adjustments:
            adaptive_timeout = int(adaptive_timeout * service_adjustments[service_type])

        return adaptive_timeout
