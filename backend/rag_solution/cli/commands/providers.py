"""Provider management commands for RAG CLI.

This module implements CLI commands for managing LLM providers including
creation, configuration, testing, and deletion operations.
"""

from typing import Any

from rag_solution.cli.client import RAGAPIClient
from rag_solution.cli.config import RAGConfig
from rag_solution.cli.exceptions import APIError, AuthenticationError, RAGCLIError

from .base import BaseCommand, CommandResult


class ProviderCommands(BaseCommand):
    """Commands for provider management operations.

    This class implements all provider-related CLI commands,
    providing methods to interact with the providers API.
    """

    def __init__(self, api_client: RAGAPIClient, config: RAGConfig | None = None) -> None:
        """Initialize provider commands.

        Args:
            api_client: HTTP API client instance
            config: Optional configuration settings
        """
        super().__init__(api_client, config)

    def list_providers(self, user_id: str | None = None) -> CommandResult:
        """List LLM providers for the current user.

        Args:
            user_id: Optional user ID (defaults to current user)

        Returns:
            CommandResult with providers data
        """
        self._require_authentication()

        try:
            # Get current user if not specified
            if not user_id:
                current_user = self.api_client.get("/api/auth/me")
                user_id = current_user["id"]

            response = self.api_client.get(f"/api/users/{user_id}/llm-providers")

            return self._create_success_result(data=response, message=f"Found {len(response)} providers")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def create_provider(
        self,
        name: str,
        provider_type: str,
        api_key: str | None = None,
        endpoint: str | None = None,
        model: str | None = None,
        user_id: str | None = None,
    ) -> CommandResult:
        """Create a new provider configuration.

        Args:
            name: Provider name/identifier
            provider_type: Type of provider (openai, anthropic, watsonx, etc.)
            api_key: API key for the provider
            endpoint: Custom endpoint URL
            model: Default model to use
            user_id: Optional user ID (defaults to current user)

        Returns:
            CommandResult with created provider data
        """
        self._require_authentication()

        try:
            # Get current user if not specified
            if not user_id:
                current_user = self.api_client.get("/api/auth/me")
                user_id = current_user["id"]

            data: dict[str, Any] = {
                "name": name,
                "provider_type": provider_type,
                "user_id": user_id,
            }

            if api_key:
                data["api_key"] = api_key
            if endpoint:
                data["endpoint"] = endpoint
            if model:
                data["model"] = model

            response = self.api_client.post(f"/api/users/{user_id}/llm-providers", data=data)

            return self._create_success_result(data=response, message=f"Provider '{name}' created successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def get_provider(self, provider_id: str, user_id: str | None = None) -> CommandResult:
        """Get provider details.

        Args:
            provider_id: Provider identifier
            user_id: Optional user ID (defaults to current user)

        Returns:
            CommandResult with provider details
        """
        self._require_authentication()

        try:
            # Get current user if not specified
            if not user_id:
                current_user = self.api_client.get("/api/auth/me")
                user_id = current_user["id"]

            response = self.api_client.get(f"/api/users/{user_id}/llm-providers/{provider_id}")

            return self._create_success_result(data=response, message="Provider details retrieved successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def update_provider(
        self,
        provider_id: str,
        api_key: str | None = None,
        endpoint: str | None = None,
        model: str | None = None,
        active: bool | None = None,
    ) -> CommandResult:
        """Update provider configuration.

        Args:
            provider_id: Provider identifier
            api_key: New API key
            endpoint: New endpoint URL
            model: New default model
            active: New active status

        Returns:
            CommandResult with updated provider data
        """
        self._require_authentication()

        try:
            data: dict[str, Any] = {}
            if api_key:
                data["api_key"] = api_key
            if endpoint:
                data["endpoint"] = endpoint
            if model:
                data["model"] = model
            if active is not None:
                data["active"] = active

            if not data:
                return self._create_error_result(message="No updates provided", error_code="NO_UPDATES")

            response = self.api_client.put(f"/api/providers/{provider_id}", data=data)

            return self._create_success_result(data=response, message="Provider updated successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def delete_provider(
        self, provider_id: str, force: bool = False, migrate_pipelines_to: str | None = None
    ) -> CommandResult:
        """Delete a provider.

        Args:
            provider_id: Provider identifier
            force: Force deletion without confirmation
            migrate_pipelines_to: Provider ID to migrate pipelines to

        Returns:
            CommandResult with deletion status
        """
        self._require_authentication()

        try:
            params: dict[str, Any] = {}
            if force:
                params["force"] = True
            if migrate_pipelines_to:
                params["migrate_pipelines_to"] = migrate_pipelines_to

            response = self.api_client.delete(f"/api/providers/{provider_id}", params=params)

            return self._create_success_result(data=response, message="Provider deleted successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def test_provider(self, provider_id: str, test_query: str | None = None, verbose: bool = False) -> CommandResult:
        """Test provider connection and functionality.

        Args:
            provider_id: Provider identifier
            test_query: Optional test query to send
            verbose: Include detailed test results

        Returns:
            CommandResult with test results
        """
        self._require_authentication()

        try:
            data: dict[str, Any] = {"verbose": verbose}
            if test_query:
                data["test_query"] = test_query

            response = self.api_client.post(f"/api/providers/{provider_id}/test", data=data)

            test_status = response.get("status", "unknown")
            message = f"Provider test: {test_status}"

            if test_status.lower() == "success":
                return self._create_success_result(data=response, message=message)
            else:
                return self._create_error_result(message=message, error_code="PROVIDER_TEST_FAILED", data=response)

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def get_provider_models(self, provider_id: str) -> CommandResult:
        """Get available models for a provider.

        Args:
            provider_id: Provider identifier

        Returns:
            CommandResult with available models
        """
        self._require_authentication()

        try:
            response = self.api_client.get(f"/api/providers/{provider_id}/models")

            models_count = len(response.get("models", []))
            return self._create_success_result(data=response, message=f"Found {models_count} available models")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def get_provider_usage(self, provider_id: str, time_range: str = "1d") -> CommandResult:
        """Get provider usage statistics.

        Args:
            provider_id: Provider identifier
            time_range: Time range for usage stats (1h, 1d, 7d, 30d)

        Returns:
            CommandResult with usage statistics
        """
        self._require_authentication()

        try:
            params = {"time_range": time_range}

            response = self.api_client.get(f"/api/providers/{provider_id}/usage", params=params)

            return self._create_success_result(
                data=response, message=f"Usage statistics for {time_range} retrieved successfully"
            )

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def batch_test_providers(self, provider_ids: list[str] | None = None) -> CommandResult:
        """Test multiple providers in batch.

        Args:
            provider_ids: List of provider IDs to test (None for all active providers)

        Returns:
            CommandResult with batch test results
        """
        self._require_authentication()

        try:
            data: dict[str, Any] = {}
            if provider_ids:
                data["provider_ids"] = provider_ids

            response = self.api_client.post("/api/providers/batch/test", data=data)

            tested_count = response.get("tested", 0)
            success_count = response.get("successful", 0)
            failed_count = response.get("failed", 0)

            message = f"Tested {tested_count} providers: {success_count} successful, {failed_count} failed"

            return self._create_success_result(data=response, message=message)

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def export_provider_config(self, provider_id: str, include_secrets: bool = False) -> CommandResult:
        """Export provider configuration.

        Args:
            provider_id: Provider identifier
            include_secrets: Include sensitive information like API keys

        Returns:
            CommandResult with exported configuration
        """
        self._require_authentication()

        try:
            params = {"include_secrets": include_secrets}

            response = self.api_client.get(f"/api/providers/{provider_id}/export", params=params)

            return self._create_success_result(data=response, message="Provider configuration exported successfully")

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)

    def import_provider_config(self, config_data: dict[str, Any], dry_run: bool = False) -> CommandResult:
        """Import provider configuration.

        Args:
            config_data: Provider configuration data
            dry_run: Only validate without importing

        Returns:
            CommandResult with import status
        """
        self._require_authentication()

        try:
            data = {**config_data}
            if dry_run:
                data["dry_run"] = True

            response = self.api_client.post("/api/providers/import", data=data)

            if dry_run:
                message = f"Would import {response.get('would_import', 0)} providers"
            else:
                imported_count = response.get("imported", 0)
                error_count = response.get("errors", 0)
                message = f"Imported {imported_count} providers"
                if error_count > 0:
                    message += f" with {error_count} errors"

            return self._create_success_result(data=response, message=message)

        except (APIError, AuthenticationError, RAGCLIError) as e:
            return self._handle_api_error(e)
