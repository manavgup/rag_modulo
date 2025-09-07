"""
Timeout retry handler for API calls in integration tests.

Provides retry mechanisms when API calls timeout during integration tests,
with exponential backoff and configurable retry strategies.
"""

import time
from typing import Any, Optional
from collections.abc import Callable
from requests.exceptions import Timeout


class TimeoutRetryHandler:
    """
    Handles timeout scenarios in API calls with intelligent retry mechanisms.

    Addresses network latency and slow response issues by implementing
    retry logic with exponential backoff.
    """

    def __init__(self):
        """Initialize timeout retry handler."""
        self.default_config = {"max_retries": 3, "base_delay": 1.0, "backoff_multiplier": 2.0, "timeout_threshold": 30, "jitter": True}

    def execute_with_timeout_retry(self, func: Callable, retry_config: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """
        Execute function with timeout retry logic.

        Args:
            func: Function to execute
            retry_config: Retry configuration dict

        Returns:
            Dict containing execution results and retry information
        """
        config = {**self.default_config, **(retry_config or {})}

        start_time = time.time()
        last_error = None
        retry_count = 0

        for attempt in range(config["max_retries"] + 1):  # +1 for initial attempt
            try:
                # Execute the function
                result = func()

                # Success - return results
                return {"success": True, "result": result, "retry_count": retry_count, "total_time": time.time() - start_time, "attempts": attempt + 1, "final_attempt": attempt + 1, "error": None}

            except Timeout as e:
                last_error = e
                retry_count += 1

                # If this was the last attempt, break
                if attempt >= config["max_retries"]:
                    break

                # Calculate delay with exponential backoff
                delay = self._calculate_delay(attempt, config)

                # Wait before retry
                time.sleep(delay)

            except Exception as e:
                # Non-timeout errors are not retried
                return {
                    "success": False,
                    "result": None,
                    "retry_count": retry_count,
                    "total_time": time.time() - start_time,
                    "attempts": attempt + 1,
                    "final_attempt": attempt + 1,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }

        # All retries exhausted
        return {
            "success": False,
            "result": None,
            "retry_count": retry_count,
            "total_time": time.time() - start_time,
            "attempts": config["max_retries"] + 1,
            "final_attempt": config["max_retries"] + 1,
            "error": str(last_error),
            "error_type": "Timeout",
            "retries_exhausted": True,
        }

    def _calculate_delay(self, attempt: int, config: dict[str, Any]) -> float:
        """
        Calculate delay for retry attempt with exponential backoff.

        Args:
            attempt: Current attempt number (0-based)
            config: Retry configuration

        Returns:
            Delay in seconds
        """
        base_delay = config["base_delay"]
        multiplier = config["backoff_multiplier"]

        # Exponential backoff: base_delay * (multiplier ^ attempt)
        delay = base_delay * (multiplier**attempt)

        # Add jitter to prevent thundering herd
        if config.get("jitter", True):
            import random

            jitter_factor = random.uniform(0.8, 1.2)
            delay *= jitter_factor

        return delay

    def create_retry_wrapper(self, retry_config: dict[str, Any]):
        """
        Create a decorator for automatic retry handling.

        Args:
            retry_config: Retry configuration

        Returns:
            Decorator function
        """

        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                return self.execute_with_timeout_retry(lambda: func(*args, **kwargs), retry_config)

            return wrapper

        return decorator

    def get_recommended_config_for_environment(self, environment: str) -> dict[str, Any]:
        """
        Get recommended retry configuration for environment.

        Args:
            environment: Environment name ("local", "ci", "production")

        Returns:
            Recommended retry configuration
        """
        environment_configs = {
            "local": {"max_retries": 2, "base_delay": 0.5, "backoff_multiplier": 1.5, "timeout_threshold": 15, "jitter": True},
            "ci": {"max_retries": 3, "base_delay": 1.0, "backoff_multiplier": 2.0, "timeout_threshold": 30, "jitter": True},
            "production": {"max_retries": 4, "base_delay": 2.0, "backoff_multiplier": 1.8, "timeout_threshold": 45, "jitter": True},
        }

        return environment_configs.get(environment, self.default_config)
