"""
Adaptive health checker that adjusts timeouts based on CI runner performance.

Addresses variable service startup times on different CI runners.
"""

from typing import Any


class AdaptiveHealthChecker:
    """
    Health checker that adapts timeout values based on CI runner performance.

    Addresses the issue where services might take longer on slower runners.
    """

    def __init__(self):
        """Initialize adaptive health checker."""
        self.performance_profiles = {"fast": {"multiplier": 0.5, "max_timeout": 60}, "standard": {"multiplier": 1.0, "max_timeout": 120}, "slow": {"multiplier": 2.0, "max_timeout": 300}}

    def calculate_adaptive_timeout(self, base_timeout: int, runner_performance: str) -> dict[str, Any]:
        """
        Calculate adaptive timeout based on runner performance.

        Args:
            base_timeout: Base timeout value in seconds
            runner_performance: Performance level ("fast", "standard", "slow")

        Returns:
            Dict containing adaptive timeout configuration
        """
        profile = self.performance_profiles.get(runner_performance, self.performance_profiles["standard"])

        adaptive_timeout = int(base_timeout * profile["multiplier"])
        adaptive_timeout = min(adaptive_timeout, profile["max_timeout"])

        return {
            "adaptive_timeout": adaptive_timeout,
            "runner_performance_factor": profile["multiplier"],
            "base_timeout": base_timeout,
            "runner_type": runner_performance,
            "max_allowed_timeout": profile["max_timeout"],
        }

    def detect_runner_performance(self) -> str:
        """
        Detect CI runner performance based on system characteristics.

        This would typically analyze:
        - CPU performance
        - Memory availability
        - Network latency
        - Historical timing data

        Returns:
            Performance level string
        """
        # Placeholder for performance detection logic
        # In a real implementation, this would analyze system metrics
        return "standard"

    def get_recommended_timeouts(self, services: list) -> dict[str, dict[str, Any]]:
        """
        Get recommended timeouts for all services based on runner performance.

        Args:
            services: List of service configurations

        Returns:
            Dict mapping service names to recommended timeout configs
        """
        runner_performance = self.detect_runner_performance()
        recommendations = {}

        for service in services:
            service_name = service.get("name", "unknown")
            base_timeout = service.get("timeout", 30)

            timeout_config = self.calculate_adaptive_timeout(base_timeout, runner_performance)
            recommendations[service_name] = timeout_config

        return recommendations
