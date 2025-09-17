"""CLI-specific exceptions for the RAG Modulo CLI.

This module defines the exception hierarchy for CLI operations, providing
clear error messages and appropriate handling for different failure scenarios.
"""

from typing import Any


class RAGCLIError(Exception):
    """Base exception for all RAG CLI errors.

    This is the base class for all CLI-specific exceptions. It provides
    a common interface for error handling and supports additional context
    information through the details parameter.

    Args:
        message: Human-readable error message
        error_code: Optional machine-readable error code
        details: Optional dictionary of additional error context

    Attributes:
        message: The error message
        error_code: Machine-readable error code
        details: Additional error context
    """

    def __init__(self, message: str, error_code: str | None = None, details: dict[str, Any] | None = None) -> None:
        """Initialize the RAGCLIError.

        Args:
            message: Human-readable error message
            error_code: Optional machine-readable error code
            details: Optional dictionary of additional error context
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def __str__(self) -> str:
        """Return string representation of the error."""
        return self.message


class AuthenticationError(RAGCLIError):
    """Exception raised for authentication-related errors.

    This exception is raised when authentication fails, tokens are invalid,
    or authentication is required but not provided.
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the AuthenticationError.

        Args:
            message: Human-readable error message
            error_code: Optional machine-readable error code
            details: Optional dictionary of additional error context
        """
        super().__init__(message, error_code, details)


class ValidationError(RAGCLIError):
    """Exception raised for input validation errors.

    This exception is raised when user input fails validation,
    such as invalid configuration values, malformed arguments,
    or missing required parameters.
    """

    def __init__(
        self, message: str = "Validation failed", error_code: str | None = None, details: dict[str, Any] | None = None
    ) -> None:
        """Initialize the ValidationError.

        Args:
            message: Human-readable error message
            error_code: Optional machine-readable error code
            details: Optional dictionary of additional error context
        """
        super().__init__(message, error_code, details)


class APIError(RAGCLIError):
    """Exception raised for API communication errors.

    This exception is raised when communication with the RAG Modulo API
    fails, including network errors, HTTP errors, and API-specific errors.
    """

    def __init__(
        self,
        message: str = "API request failed",
        status_code: int | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the APIError.

        Args:
            message: Human-readable error message
            status_code: HTTP status code if applicable
            error_code: Optional machine-readable error code
            details: Optional dictionary of additional error context
        """
        super().__init__(message, error_code, details)
        self.status_code = status_code


class ConfigurationError(RAGCLIError):
    """Exception raised for configuration-related errors.

    This exception is raised when there are issues with CLI configuration,
    such as invalid config files, missing required settings, or
    profile-related problems.
    """

    def __init__(
        self, message: str = "Configuration error", error_code: str | None = None, details: dict[str, Any] | None = None
    ) -> None:
        """Initialize the ConfigurationError.

        Args:
            message: Human-readable error message
            error_code: Optional machine-readable error code
            details: Optional dictionary of additional error context
        """
        super().__init__(message, error_code, details)
