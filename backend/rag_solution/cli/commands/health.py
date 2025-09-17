"""Health and system status commands for RAG CLI.

This module implements CLI commands for checking system health,
service status, and diagnostic information.
"""

from rag_solution.cli.client import RAGAPIClient
from rag_solution.cli.config import RAGConfig

from .base import BaseCommand, CommandResult


class HealthCommands(BaseCommand):
    """Commands for health and system status operations.

    This class implements all health-related CLI commands,
    providing methods to check system status and diagnostics.
    """

    def __init__(self, api_client: RAGAPIClient, config: RAGConfig | None = None) -> None:
        """Initialize health commands.

        Args:
            api_client: HTTP API client instance
            config: Optional configuration settings
        """
        super().__init__(api_client, config)

    def check_health(self) -> CommandResult:
        """Check overall system health.

        Returns:
            CommandResult with system health status
        """
        try:
            response = self.api_client.get("/api/health")

            status = response.get("status", "unknown")
            message = f"System status: {status}"

            if status.lower() == "healthy":
                return self._create_success_result(data=response, message=message)
            else:
                return self._create_error_result(message=message, error_code="SYSTEM_UNHEALTHY", data=response)

        except Exception as e:
            return self._handle_api_error(e)

    def check_readiness(self) -> CommandResult:
        """Check if system is ready to serve requests.

        Returns:
            CommandResult with readiness status
        """
        try:
            response = self.api_client.get("/ready")

            return self._create_success_result(data=response, message="System readiness check completed")

        except Exception as e:
            return self._handle_api_error(e)

    def check_liveness(self) -> CommandResult:
        """Check if system is alive and responsive.

        Returns:
            CommandResult with liveness status
        """
        try:
            response = self.api_client.get("/health/live")

            return self._create_success_result(data=response, message="System liveness check completed")

        except Exception as e:
            return self._handle_api_error(e)

    def get_system_info(self) -> CommandResult:
        """Get detailed system information.

        Returns:
            CommandResult with system information
        """
        self._require_authentication()

        try:
            response = self.api_client.get("/api/health/info")

            return self._create_success_result(data=response, message="System information retrieved successfully")

        except Exception as e:
            return self._handle_api_error(e)

    def check_database_health(self) -> CommandResult:
        """Check database connectivity and health.

        Returns:
            CommandResult with database health status
        """
        self._require_authentication()

        try:
            response = self.api_client.get("/api/health/database")

            status = response.get("status", "unknown")
            message = f"Database status: {status}"

            if status.lower() == "healthy":
                return self._create_success_result(data=response, message=message)
            else:
                return self._create_error_result(message=message, error_code="DATABASE_UNHEALTHY", data=response)

        except Exception as e:
            return self._handle_api_error(e)

    def check_vector_db_health(self) -> CommandResult:
        """Check vector database connectivity and health.

        Returns:
            CommandResult with vector database health status
        """
        self._require_authentication()

        try:
            response = self.api_client.get("/api/health/vector-db")

            status = response.get("status", "unknown")
            message = f"Vector database status: {status}"

            if status.lower() == "healthy":
                return self._create_success_result(data=response, message=message)
            else:
                return self._create_error_result(message=message, error_code="VECTOR_DB_UNHEALTHY", data=response)

        except Exception as e:
            return self._handle_api_error(e)

    def check_llm_providers_health(self) -> CommandResult:
        """Check LLM providers connectivity and health.

        Returns:
            CommandResult with LLM providers health status
        """
        self._require_authentication()

        try:
            response = self.api_client.get("/api/health/llm-providers")

            return self._create_success_result(data=response, message="LLM providers health check completed")

        except Exception as e:
            return self._handle_api_error(e)

    def get_metrics(self, metric_type: str | None = None) -> CommandResult:
        """Get system metrics.

        Args:
            metric_type: Optional metric type filter

        Returns:
            CommandResult with system metrics
        """
        self._require_authentication()

        try:
            params = {}
            if metric_type:
                params["type"] = metric_type

            response = self.api_client.get("/api/health/metrics", params=params)

            return self._create_success_result(data=response, message="System metrics retrieved successfully")

        except Exception as e:
            return self._handle_api_error(e)

    def get_version_info(self) -> CommandResult:
        """Get application version information.

        Returns:
            CommandResult with version information
        """
        try:
            response = self.api_client.get("/api/version")

            return self._create_success_result(data=response, message="Version information retrieved successfully")

        except Exception as e:
            return self._handle_api_error(e)

    def run_diagnostics(self, component: str | None = None, verbose: bool = False) -> CommandResult:
        """Run system diagnostics.

        Args:
            component: Optional specific component to diagnose
            verbose: Include verbose diagnostic information

        Returns:
            CommandResult with diagnostic results
        """
        self._require_authentication()

        try:
            from typing import Any

            params: dict[str, Any] = {"verbose": verbose}
            if component:
                params["component"] = component

            response = self.api_client.get("/api/health/diagnostics", params=params)

            issues_count = len(response.get("issues", []))
            warnings_count = len(response.get("warnings", []))

            message = "System diagnostics completed"
            if issues_count > 0:
                message += f" - {issues_count} issues found"
            if warnings_count > 0:
                message += f" - {warnings_count} warnings"

            return self._create_success_result(data=response, message=message)

        except Exception as e:
            return self._handle_api_error(e)

    def get_service_dependencies(self) -> CommandResult:
        """Get service dependency status.

        Returns:
            CommandResult with dependency information
        """
        self._require_authentication()

        try:
            response = self.api_client.get("/api/health/dependencies")

            return self._create_success_result(data=response, message="Service dependencies retrieved successfully")

        except Exception as e:
            return self._handle_api_error(e)

    def check_storage_health(self) -> CommandResult:
        """Check storage systems health.

        Returns:
            CommandResult with storage health status
        """
        self._require_authentication()

        try:
            response = self.api_client.get("/api/health/storage")

            status = response.get("status", "unknown")
            message = f"Storage status: {status}"

            if status.lower() == "healthy":
                return self._create_success_result(data=response, message=message)
            else:
                return self._create_error_result(message=message, error_code="STORAGE_UNHEALTHY", data=response)

        except Exception as e:
            return self._handle_api_error(e)

    def get_performance_stats(self, time_range: str = "1h") -> CommandResult:
        """Get system performance statistics.

        Args:
            time_range: Time range for statistics (1h, 6h, 1d, 7d)

        Returns:
            CommandResult with performance statistics
        """
        self._require_authentication()

        try:
            params = {"time_range": time_range}

            response = self.api_client.get("/api/health/performance", params=params)

            return self._create_success_result(
                data=response, message=f"Performance statistics for {time_range} retrieved successfully"
            )

        except Exception as e:
            return self._handle_api_error(e)
