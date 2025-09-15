"""CLI configuration management using Pydantic 2.0.

This module provides configuration management for the RAG Modulo CLI,
including profile management, validation, and settings persistence.
"""

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from .exceptions import ConfigurationError, ValidationError


class RAGConfig(BaseModel):
    """Configuration model for RAG CLI using Pydantic 2.0.

    This model handles all CLI configuration including API settings,
    authentication tokens, and user preferences. It provides validation
    and serialization capabilities.

    Attributes:
        api_url: Base URL for the RAG Modulo API
        profile: Name of the current profile
        timeout: Request timeout in seconds
        auth_token: JWT authentication token
        output_format: Default output format (table, json, yaml)
        verbose: Enable verbose output
        max_retries: Maximum number of API request retries
    """

    api_url: HttpUrl = Field(default=HttpUrl("http://localhost:8000"), description="Base URL for the RAG Modulo API")
    profile: str = Field(
        default="default",
        min_length=1,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Profile name for configuration management",
    )
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    auth_token: str | None = Field(default=None, description="JWT authentication token")
    output_format: str = Field(default="table", pattern=r"^(table|json|yaml)$", description="Default output format")
    verbose: bool = Field(default=False, description="Enable verbose output")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum number of API request retries")
    dry_run: bool = Field(default=False, description="Enable dry-run mode for destructive operations")

    model_config = {"str_strip_whitespace": True, "validate_assignment": True, "extra": "forbid"}

    @field_validator("api_url")
    @classmethod
    def validate_api_url(cls, v: HttpUrl) -> HttpUrl:
        """Validate API URL format.

        Args:
            v: The API URL to validate

        Returns:
            The validated URL

        Raises:
            ValidationError: If URL is invalid
        """
        url_str = str(v)
        parsed = urlparse(url_str)

        if not parsed.scheme:
            raise ValidationError("API URL must include scheme (http/https)")

        if parsed.scheme not in ("http", "https"):
            raise ValidationError("API URL scheme must be http or https")

        if not parsed.netloc:
            raise ValidationError("API URL must include hostname")

        return v

    @field_validator("auth_token")
    @classmethod
    def validate_auth_token(cls, v: str | None) -> str | None:
        """Validate authentication token format.

        Args:
            v: The auth token to validate

        Returns:
            The validated token or None

        Raises:
            ValidationError: If token format is invalid
        """
        if v is None:
            return v

        if not isinstance(v, str):
            raise ValidationError("Auth token must be a string")

        if len(v.strip()) == 0:
            return None

        # Basic JWT format validation (header.payload.signature)
        parts = v.split(".")
        if len(parts) != 3:
            raise ValidationError("Auth token must be a valid JWT format")

        return v

    @model_validator(mode="after")
    def validate_model(self) -> "RAGConfig":
        """Perform model-level validation.

        Returns:
            The validated model instance

        Raises:
            ValidationError: If model validation fails
        """
        # Additional cross-field validation can be added here
        return self

    def is_valid(self) -> bool:
        """Validate the current configuration.

        Returns:
            True if configuration is valid

        Raises:
            ValidationError: If configuration is invalid
        """
        try:
            # Re-validate the model to ensure all constraints are met
            self.model_validate(self.model_dump())
            return True
        except Exception as e:
            raise ValidationError(f"Configuration validation failed: {e!s}") from e

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary representation of the configuration
        """
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RAGConfig":
        """Create configuration from dictionary.

        Args:
            data: Dictionary containing configuration data

        Returns:
            RAGConfig instance

        Raises:
            ValidationError: If data is invalid
        """
        try:
            return cls(**data)
        except Exception as e:
            raise ValidationError(f"Failed to create configuration from data: {e!s}") from e

    @classmethod
    def from_env(cls, prefix: str = "RAG_CLI_") -> "RAGConfig":
        """Create configuration from environment variables.

        Args:
            prefix: Prefix for environment variable names

        Returns:
            RAGConfig instance with values from environment
        """
        env_data: dict[str, Any] = {}

        env_mapping = {
            f"{prefix}API_URL": "api_url",
            f"{prefix}PROFILE": "profile",
            f"{prefix}TIMEOUT": "timeout",
            f"{prefix}AUTH_TOKEN": "auth_token",
            f"{prefix}OUTPUT_FORMAT": "output_format",
            f"{prefix}VERBOSE": "verbose",
            f"{prefix}MAX_RETRIES": "max_retries",
        }

        for env_var, field_name in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if field_name in ("timeout", "max_retries"):
                    try:
                        env_data[field_name] = int(value)
                    except ValueError as ve:
                        raise ValidationError(f"Invalid integer value for {env_var}: {value}") from ve
                elif field_name == "verbose":
                    env_data[field_name] = value.lower() in ("true", "1", "yes", "on")
                elif field_name == "api_url":
                    env_data[field_name] = HttpUrl(value)
                else:
                    env_data[field_name] = value

        return cls(**env_data)

    def get_config_dir(self) -> Path:
        """Get the configuration directory path.

        Returns:
            Path to the CLI configuration directory
        """
        home_dir = Path.home()
        config_dir = home_dir / ".rag-cli"
        config_dir.mkdir(exist_ok=True)
        return config_dir

    def get_profile_file(self) -> Path:
        """Get the profile configuration file path.

        Returns:
            Path to the profile configuration file
        """
        config_dir = self.get_config_dir()
        profiles_dir = config_dir / "profiles"
        profiles_dir.mkdir(exist_ok=True)
        return profiles_dir / f"{self.profile}.json"

    def save_to_file(self) -> None:
        """Save configuration to profile file.

        Raises:
            ConfigurationError: If save operation fails
        """
        try:
            profile_file = self.get_profile_file()
            config_data = self.model_dump_json(indent=2, exclude_none=True)
            profile_file.write_text(config_data, encoding="utf-8")
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e!s}") from e

    @classmethod
    def load_from_file(cls, profile: str = "default") -> "RAGConfig":
        """Load configuration from profile file.

        Args:
            profile: Name of the profile to load

        Returns:
            RAGConfig instance loaded from file

        Raises:
            ConfigurationError: If load operation fails
        """
        try:
            temp_config = cls(profile=profile)
            profile_file = temp_config.get_profile_file()

            if not profile_file.exists():
                # Return default configuration if profile doesn't exist
                return temp_config

            config_text = profile_file.read_text(encoding="utf-8")
            config_data = cls.model_validate_json(config_text)
            return config_data

        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e!s}") from e


class ProfileManager:
    """Manager for CLI profiles.

    This class handles profile creation, switching, listing, and deletion
    operations for the CLI configuration system.
    """

    def __init__(self) -> None:
        """Initialize the ProfileManager."""
        self.config_dir = Path.home() / ".rag-cli"
        self.profiles_dir = self.config_dir / "profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def list_profiles(self) -> dict[str, dict[str, Any]]:
        """List all available profiles.

        Returns:
            Dictionary mapping profile names to their metadata
        """
        profiles = {}

        for profile_file in self.profiles_dir.glob("*.json"):
            try:
                profile_name = profile_file.stem
                config = RAGConfig.load_from_file(profile_name)
                profiles[profile_name] = {
                    "name": profile_name,
                    "api_url": str(config.api_url),
                    "created_at": profile_file.stat().st_ctime,
                    "modified_at": profile_file.stat().st_mtime,
                    "has_token": config.auth_token is not None,
                }
            except Exception:
                # Skip invalid profile files
                continue

        return profiles

    def create_profile(self, name: str, api_url: str, description: str | None = None) -> RAGConfig:  # noqa: ARG002
        """Create a new profile.

        Args:
            name: Name of the new profile
            api_url: API URL for the profile
            description: Optional description for the profile

        Returns:
            The created RAGConfig instance

        Raises:
            ConfigurationError: If profile creation fails
        """
        try:
            config = RAGConfig(profile=name, api_url=HttpUrl(api_url))
            config.save_to_file()
            return config
        except Exception as e:
            raise ConfigurationError(f"Failed to create profile '{name}': {e!s}") from e

    def delete_profile(self, name: str) -> bool:
        """Delete a profile.

        Args:
            name: Name of the profile to delete

        Returns:
            True if profile was deleted successfully

        Raises:
            ConfigurationError: If profile deletion fails
        """
        if name == "default":
            raise ConfigurationError("Cannot delete the default profile")

        profile_file = self.profiles_dir / f"{name}.json"
        if not profile_file.exists():
            raise ConfigurationError(f"Profile '{name}' does not exist")

        try:
            profile_file.unlink()
            return True
        except Exception as e:
            raise ConfigurationError(f"Failed to delete profile '{name}': {e!s}") from e

    def profile_exists(self, name: str) -> bool:
        """Check if a profile exists.

        Args:
            name: Name of the profile to check

        Returns:
            True if profile exists
        """
        profile_file = self.profiles_dir / f"{name}.json"
        return profile_file.exists()
