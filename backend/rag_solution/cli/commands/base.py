"""Base command class for CLI operations.

This module provides the base class for all CLI commands, implementing
common functionality like authentication checks, error handling, and
result standardization.
"""

from typing import Any

from pydantic import BaseModel

from rag_solution.cli.client import RAGAPIClient
from rag_solution.cli.config import RAGConfig
from rag_solution.cli.exceptions import AuthenticationError, RAGCLIError


class CommandResult(BaseModel):
    """Result of a CLI command execution.

    This model standardizes command results providing consistent
    structure for success/failure handling.

    Attributes:
        success: Whether the command succeeded
        data: Command result data
        message: Human-readable result message
        error_code: Machine-readable error code if failed
    """

    success: bool
    data: dict[str, Any] | None = None
    message: str | None = None
    error_code: str | None = None

    model_config = {"extra": "forbid"}


class BaseCommand:
    """Base class for all CLI commands.

    This base class provides common functionality for CLI commands
    including API client management, authentication checks, and result handling.
    """

    def __init__(self, api_client: RAGAPIClient, config: RAGConfig | None = None) -> None:
        """Initialize the base command.

        Args:
            api_client: HTTP API client instance
            config: Optional configuration settings
        """
        self.api_client = api_client
        self.config = config

    def _require_authentication(self) -> None:
        """Check that user is authenticated.

        Raises:
            AuthenticationError: If user is not authenticated
        """
        if not self.api_client.is_authenticated():
            raise AuthenticationError("Authentication required. Please run 'rag-cli auth login' first.")

    def _create_success_result(self, data: dict[str, Any] | None = None, message: str | None = None) -> CommandResult:
        """Create a successful command result.

        Args:
            data: Optional result data
            message: Optional success message

        Returns:
            CommandResult indicating success
        """
        return CommandResult(success=True, data=data, message=message)

    def _create_error_result(self, message: str, error_code: str | None = None, data: dict[str, Any] | None = None) -> CommandResult:
        """Create an error command result.

        Args:
            message: Error message
            error_code: Optional error code
            data: Optional error data

        Returns:
            CommandResult indicating failure
        """
        return CommandResult(success=False, message=message, error_code=error_code, data=data)

    def _handle_api_error(self, error: Exception) -> CommandResult:
        """Handle API errors and convert to CommandResult.

        Args:
            error: Exception that occurred during API call

        Returns:
            CommandResult with error information
        """
        if isinstance(error, AuthenticationError):
            return self._create_error_result(message=str(error), error_code="AUTHENTICATION_FAILED")
        elif isinstance(error, RAGCLIError):
            return self._create_error_result(message=str(error), error_code=getattr(error, "error_code", None))
        else:
            return self._create_error_result(message=f"Unexpected error: {error!s}", error_code="UNEXPECTED_ERROR")
