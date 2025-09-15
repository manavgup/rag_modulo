"""Pipeline management commands for RAG CLI.

This module implements CLI commands for managing search pipelines including
creation, configuration, testing, and deletion operations.
"""

from typing import Any

from rag_solution.cli.client import RAGAPIClient
from rag_solution.cli.config import RAGConfig
from rag_solution.cli.exceptions import APIError, AuthenticationError, RAGCLIError

from .base import BaseCommand, CommandResult


class PipelineCommands(BaseCommand):
    """Commands for pipeline management operations.

    This class implements all pipeline-related CLI commands,
    providing methods to interact with the pipelines API.
    """

    def __init__(self, api_client: RAGAPIClient, config: RAGConfig | None = None) -> None:
        """Initialize pipeline commands.

        Args:
            api_client: HTTP API client instance
            config: Optional configuration settings
        """
        super().__init__(api_client, config)

    def list_pipelines(self, user_id: str | None = None) -> CommandResult:
        """List pipelines for the current user.

        Args:
            user_id: Optional user ID (defaults to current user)

        Returns:
            CommandResult with pipelines data
        """
        self._require_authentication()

        try:
            # Get current user if not specified
            if not user_id:
                current_user = self.api_client.get("/api/users/me")
                user_id = current_user["id"]

            response = self.api_client.get(f"/api/users/{user_id}/pipelines")

            return self._create_success_result(data=response, message=f"Found {len(response)} pipelines")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def create_pipeline(
        self,
        name: str,
        llm_provider_id: str | None = None,
        parameters: dict[str, Any] | None = None,
        template_id: str | None = None,
    ) -> CommandResult:
        """Create a new pipeline.

        Args:
            name: Pipeline name
            llm_provider_id: LLM provider to use
            parameters: Pipeline parameters
            template_id: Template to use for creation

        Returns:
            CommandResult with created pipeline data
        """
        self._require_authentication()

        try:
            data: dict[str, Any] = {"name": name}

            if llm_provider_id:
                data["llm_provider_id"] = llm_provider_id
            if parameters:
                data["parameters"] = parameters
            if template_id:
                data["template_id"] = template_id

            response = self.api_client.post("/api/pipelines", data=data)

            return self._create_success_result(data=response, message=f"Pipeline '{name}' created successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def get_pipeline(
        self, pipeline_id: str, include_config: bool = False, include_performance: bool = False
    ) -> CommandResult:
        """Get pipeline details.

        Args:
            pipeline_id: Pipeline identifier
            include_config: Include configuration details
            include_performance: Include performance metrics

        Returns:
            CommandResult with pipeline details
        """
        self._require_authentication()

        try:
            params: dict[str, Any] = {}
            if include_config:
                params["include_config"] = True
            if include_performance:
                params["include_performance"] = True

            response = self.api_client.get(f"/api/pipelines/{pipeline_id}", params=params)

            return self._create_success_result(data=response, message="Pipeline details retrieved successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def update_pipeline(
        self,
        pipeline_id: str,
        provider_id: str | None = None,
        parameters: dict[str, Any] | None = None,
        name: str | None = None,
        active: bool | None = None,
    ) -> CommandResult:
        """Update pipeline configuration.

        Args:
            pipeline_id: Pipeline identifier
            provider_id: New LLM provider ID
            parameters: New parameters
            name: New pipeline name
            active: New active status

        Returns:
            CommandResult with updated pipeline data
        """
        self._require_authentication()

        try:
            data: dict[str, Any] = {}
            if provider_id:
                data["provider_id"] = provider_id
            if parameters:
                data["parameters"] = parameters
            if name:
                data["name"] = name
            if active is not None:
                data["active"] = active

            if not data:
                return self._create_error_result(message="No updates provided", error_code="NO_UPDATES")

            response = self.api_client.put(f"/api/pipelines/{pipeline_id}", data=data)

            return self._create_success_result(data=response, message="Pipeline updated successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def delete_pipeline(self, pipeline_id: str, force: bool = False) -> CommandResult:
        """Delete a pipeline.

        Args:
            pipeline_id: Pipeline identifier
            force: Force deletion without confirmation

        Returns:
            CommandResult with deletion status
        """
        self._require_authentication()

        try:
            params: dict[str, Any] = {}
            if force:
                params["force"] = True

            response = self.api_client.delete(f"/api/pipelines/{pipeline_id}", params=params)

            return self._create_success_result(data=response, message="Pipeline deleted successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def test_pipeline(
        self, pipeline_id: str, test_query: str, verbose: bool = False, save_results: bool = False
    ) -> CommandResult:
        """Test pipeline with a query.

        Args:
            pipeline_id: Pipeline identifier
            test_query: Query to test with
            verbose: Include detailed test results
            save_results: Save test results for analysis

        Returns:
            CommandResult with test results
        """
        self._require_authentication()

        try:
            data: dict[str, Any] = {
                "test_query": test_query,
                "verbose": verbose,
                "save_results": save_results,
            }

            response = self.api_client.post(f"/api/pipelines/{pipeline_id}/test", data=data)

            test_status = response.get("status", "unknown")
            message = f"Pipeline test: {test_status}"

            if test_status.lower() == "success":
                return self._create_success_result(data=response, message=message)
            else:
                return self._create_error_result(message=message, error_code="PIPELINE_TEST_FAILED", data=response)

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def get_pipeline_performance(self, pipeline_id: str, time_range: str = "7d") -> CommandResult:
        """Get pipeline performance metrics.

        Args:
            pipeline_id: Pipeline identifier
            time_range: Time range for metrics (1h, 1d, 7d, 30d)

        Returns:
            CommandResult with performance metrics
        """
        self._require_authentication()

        try:
            params = {"time_range": time_range}

            response = self.api_client.get(f"/api/pipelines/{pipeline_id}/performance", params=params)

            return self._create_success_result(
                data=response, message=f"Performance metrics for {time_range} retrieved successfully"
            )

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def get_pipeline_usage(self, pipeline_id: str, time_range: str = "7d") -> CommandResult:
        """Get pipeline usage statistics.

        Args:
            pipeline_id: Pipeline identifier
            time_range: Time range for usage stats (1h, 1d, 7d, 30d)

        Returns:
            CommandResult with usage statistics
        """
        self._require_authentication()

        try:
            params = {"time_range": time_range}

            response = self.api_client.get(f"/api/pipelines/{pipeline_id}/usage", params=params)

            return self._create_success_result(
                data=response, message=f"Usage statistics for {time_range} retrieved successfully"
            )

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def clone_pipeline(self, pipeline_id: str, new_name: str, new_provider_id: str | None = None) -> CommandResult:
        """Clone an existing pipeline.

        Args:
            pipeline_id: Source pipeline identifier
            new_name: Name for the cloned pipeline
            new_provider_id: Optional new provider for the clone

        Returns:
            CommandResult with cloned pipeline data
        """
        self._require_authentication()

        try:
            data: dict[str, Any] = {"new_name": new_name}
            if new_provider_id:
                data["new_provider_id"] = new_provider_id

            response = self.api_client.post(f"/api/pipelines/{pipeline_id}/clone", data=data)

            return self._create_success_result(data=response, message=f"Pipeline cloned as '{new_name}' successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def batch_test_pipelines(
        self, pipeline_ids: list[str] | None = None, test_query: str = "Test query"
    ) -> CommandResult:
        """Test multiple pipelines in batch.

        Args:
            pipeline_ids: List of pipeline IDs to test (None for all active pipelines)
            test_query: Test query to use

        Returns:
            CommandResult with batch test results
        """
        self._require_authentication()

        try:
            data: dict[str, Any] = {"test_query": test_query}
            if pipeline_ids:
                data["pipeline_ids"] = pipeline_ids

            response = self.api_client.post("/api/pipelines/batch/test", data=data)

            tested_count = response.get("tested", 0)
            success_count = response.get("successful", 0)
            failed_count = response.get("failed", 0)

            message = f"Tested {tested_count} pipelines: {success_count} successful, {failed_count} failed"

            return self._create_success_result(data=response, message=message)

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def get_pipeline_templates(self) -> CommandResult:
        """Get available pipeline templates.

        Returns:
            CommandResult with available templates
        """
        self._require_authentication()

        try:
            response = self.api_client.get("/api/pipelines/templates")

            templates_count = len(response.get("templates", []))
            return self._create_success_result(data=response, message=f"Found {templates_count} available templates")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def export_pipeline_config(self, pipeline_id: str, include_secrets: bool = False) -> CommandResult:
        """Export pipeline configuration.

        Args:
            pipeline_id: Pipeline identifier
            include_secrets: Include sensitive information

        Returns:
            CommandResult with exported configuration
        """
        self._require_authentication()

        try:
            params = {"include_secrets": include_secrets}

            response = self.api_client.get(f"/api/pipelines/{pipeline_id}/export", params=params)

            return self._create_success_result(data=response, message="Pipeline configuration exported successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def import_pipeline_config(self, config_data: dict[str, Any], dry_run: bool = False) -> CommandResult:
        """Import pipeline configuration.

        Args:
            config_data: Pipeline configuration data
            dry_run: Only validate without importing

        Returns:
            CommandResult with import status
        """
        self._require_authentication()

        try:
            data = {**config_data}
            if dry_run:
                data["dry_run"] = True

            response = self.api_client.post("/api/pipelines/import", data=data)

            if dry_run:
                message = f"Would import {response.get('would_import', 0)} pipelines"
            else:
                imported_count = response.get("imported", 0)
                error_count = response.get("errors", 0)
                message = f"Imported {imported_count} pipelines"
                if error_count > 0:
                    message += f" with {error_count} errors"

            return self._create_success_result(data=response, message=message)

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)
