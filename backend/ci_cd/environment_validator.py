"""
Environment validation for CI/CD pipelines.

Validates that all required environment variables are present and correctly
configured for different deployment environments.
"""

import os
from typing import Any
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of environment validation."""

    valid: bool
    missing_variables: list[str]
    invalid_variables: dict[str, str]
    warnings: list[str]


class EnvironmentValidator:
    """
    Validates environment configuration for CI/CD pipelines.

    Ensures all required environment variables are present and correctly
    formatted for the target deployment environment.
    """

    def __init__(self):
        """Initialize environment validator."""
        self.required_variables = {
            "production": ["DATABASE_URL", "JWT_SECRET_KEY", "RAG_LLM", "WATSONX_INSTANCE_ID", "WATSONX_APIKEY", "WATSONX_URL"],
            "staging": ["DATABASE_URL", "JWT_SECRET_KEY", "RAG_LLM", "WATSONX_INSTANCE_ID", "WATSONX_APIKEY", "WATSONX_URL"],
            "development": ["JWT_SECRET_KEY", "RAG_LLM"],
        }

        self.optional_variables = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "VECTOR_DB", "MILVUS_HOST", "MILVUS_PORT"]

    def validate_environment(self, environment: str = "development") -> ValidationResult:
        """
        Validate environment variables for specified environment.

        Args:
            environment: Target environment (production, staging, development)

        Returns:
            ValidationResult with validation status and details
        """
        if environment not in self.required_variables:
            environment = "development"  # Default fallback

        required_vars = self.required_variables[environment]
        missing_variables = []
        invalid_variables = {}
        warnings = []

        # Check required variables
        for var in required_vars:
            value = os.getenv(var)
            if not value:
                missing_variables.append(var)
            elif not self._validate_variable_format(var, value):
                invalid_variables[var] = f"Invalid format for {var}"

        # Check for common misconfigurations
        self._check_common_issues(warnings)

        # Environment-specific validations
        if environment == "production":
            self._validate_production_environment(warnings, invalid_variables)

        valid = len(missing_variables) == 0 and len(invalid_variables) == 0

        return ValidationResult(valid=valid, missing_variables=missing_variables, invalid_variables=invalid_variables, warnings=warnings)

    def _validate_variable_format(self, var_name: str, value: str) -> bool:
        """
        Validate format of environment variable value.

        Args:
            var_name: Variable name
            value: Variable value

        Returns:
            True if format is valid
        """
        if var_name == "DATABASE_URL":
            return value.startswith(("postgresql://", "postgres://"))
        elif var_name == "WATSONX_URL":
            return value.startswith("http")
        elif var_name == "JWT_SECRET_KEY":
            return len(value) >= 32  # Minimum security requirement
        elif var_name == "RAG_LLM":
            return value in ["openai", "watsonx", "anthropic"]

        return True  # Default: accept any non-empty value

    def _check_common_issues(self, warnings: list[str]) -> None:
        """Check for common environment configuration issues."""
        # Check for test values in non-test environments
        if os.getenv("CI") != "true":
            test_values = ["test", "development", "dev", "localhost"]
            for var in ["DATABASE_URL", "WATSONX_URL"]:
                value = os.getenv(var, "").lower()
                if any(test_val in value for test_val in test_values):
                    warnings.append(f"{var} appears to contain test/development values")

    def _validate_production_environment(self, warnings: list[str], invalid_variables: dict[str, str]) -> None:
        """Additional validation for production environment."""
        # Check JWT secret strength
        jwt_secret = os.getenv("JWT_SECRET_KEY", "")
        if jwt_secret and len(jwt_secret) < 64:
            warnings.append("JWT_SECRET_KEY should be at least 64 characters for production")

        # Check for development/test URLs in production
        database_url = os.getenv("DATABASE_URL", "")
        if "localhost" in database_url or "127.0.0.1" in database_url:
            invalid_variables["DATABASE_URL"] = "Production should not use localhost database"

    def get_environment_info(self) -> dict[str, Any]:
        """
        Get information about current environment configuration.

        Returns:
            Dictionary with environment information
        """
        return {
            "detected_environment": self._detect_environment(),
            "ci_environment": os.getenv("CI", "false").lower() == "true",
            "python_version": os.getenv("PYTHON_VERSION"),
            "node_env": os.getenv("NODE_ENV"),
            "environment_vars_count": len([k for k in os.environ.keys() if not k.startswith("_")]),
            "has_docker": os.path.exists("/.dockerenv"),
        }

    def _detect_environment(self) -> str:
        """Detect current environment based on environment variables."""
        if os.getenv("NODE_ENV") == "production" or os.getenv("ENVIRONMENT") == "production":
            return "production"
        elif os.getenv("NODE_ENV") == "staging" or os.getenv("ENVIRONMENT") == "staging":
            return "staging"
        elif os.getenv("CI", "false").lower() == "true":
            return "ci"
        else:
            return "development"

    def validate_required_variables(self, required_vars: list[str]) -> ValidationResult:
        """
        Validate specific list of required variables.

        Args:
            required_vars: List of required variable names

        Returns:
            ValidationResult for specified variables
        """
        missing_variables = []
        invalid_variables = {}
        warnings = []

        for var in required_vars:
            value = os.getenv(var)
            if not value:
                missing_variables.append(var)
            elif not self._validate_variable_format(var, value):
                invalid_variables[var] = f"Invalid format for {var}"

        valid = len(missing_variables) == 0 and len(invalid_variables) == 0

        return ValidationResult(valid=valid, missing_variables=missing_variables, invalid_variables=invalid_variables, warnings=warnings)

    def validate_all(self) -> dict[str, Any]:
        """
        Validate all environment configurations.

        Returns:
            Complete validation results
        """
        environment = self._detect_environment()
        result = self.validate_environment(environment)

        return {"valid": result.valid, "missing_vars": result.missing_variables, "invalid_vars": result.invalid_variables, "warnings": result.warnings, "environment": environment}

    def validate_required_vars(self, required_vars: list[str]) -> dict[str, Any]:
        """
        Validate required variables (alternative method name for compatibility).

        Args:
            required_vars: List of required variable names

        Returns:
            Dictionary with validation results
        """
        result = self.validate_required_variables(required_vars)

        return {"valid": result.valid, "missing_vars": result.missing_variables, "invalid_vars": result.invalid_variables, "warnings": result.warnings}

    def validate_service_configs(self) -> dict[str, Any]:
        """
        Validate service configuration environment variables.

        Returns:
            Service configuration validation results
        """
        service_vars = ["COLLECTIONDB_HOST", "COLLECTIONDB_PORT", "COLLECTIONDB_USER", "COLLECTIONDB_PASSWORD", "VECTOR_DB", "MILVUS_HOST", "MILVUS_PORT"]

        result = self.validate_required_variables(service_vars)

        return {"valid": result.valid, "missing_vars": result.missing_variables, "invalid_vars": result.invalid_variables, "warnings": result.warnings, "service_type": "database_and_vector"}
