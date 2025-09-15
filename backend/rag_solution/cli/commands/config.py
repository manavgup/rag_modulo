"""Configuration management commands for RAG CLI.

This module implements CLI commands for managing configuration profiles,
settings, and environment-specific configurations.
"""

import json
from pathlib import Path

from pydantic import HttpUrl, ValidationError

from rag_solution.cli.client import RAGAPIClient
from rag_solution.cli.config import RAGConfig
from rag_solution.cli.exceptions import APIError, AuthenticationError, RAGCLIError

from .base import BaseCommand, CommandResult


class ConfigCommands(BaseCommand):
    """Commands for configuration management operations.

    This class implements all configuration-related CLI commands,
    providing methods to manage profiles, settings, and environments.
    """

    def __init__(self, api_client: RAGAPIClient, config: RAGConfig | None = None) -> None:
        """Initialize configuration commands.

        Args:
            api_client: HTTP API client instance
            config: Optional configuration settings
        """
        super().__init__(api_client, config)

    def list_profiles(self) -> CommandResult:
        """List available configuration profiles.

        Returns:
            CommandResult with available profiles
        """
        try:
            config_dir = Path.home() / ".rag-cli"

            if not config_dir.exists():
                return self._create_success_result(data={"profiles": []}, message="No profiles found")

            profiles = []
            for config_file in config_dir.glob("*.json"):
                if config_file.stem != "current":  # Skip current profile pointer
                    profiles.append(config_file.stem)

            return self._create_success_result(data={"profiles": profiles}, message=f"Found {len(profiles)} profiles")

        except (OSError, PermissionError, ValueError) as e:
            return self._handle_api_error(e)

    def create_profile(self, name: str, api_url: str, timeout: int = 30, set_as_default: bool = False) -> CommandResult:
        """Create a new configuration profile.

        Args:
            name: Profile name
            api_url: API base URL
            timeout: Request timeout in seconds
            set_as_default: Set as default profile

        Returns:
            CommandResult with creation status
        """
        try:
            # Validate profile name
            if not name.replace("_", "").replace("-", "").isalnum():
                return self._create_error_result(
                    message="Profile name must contain only letters, numbers, hyphens, and underscores",
                    error_code="INVALID_PROFILE_NAME",
                )

            # Create configuration
            new_config = RAGConfig(api_url=HttpUrl(api_url), profile=name, timeout=timeout)

            # Save profile
            config_dir = Path.home() / ".rag-cli"
            config_dir.mkdir(exist_ok=True)

            config_file = config_dir / f"{name}.json"
            if config_file.exists():
                return self._create_error_result(
                    message=f"Profile '{name}' already exists", error_code="PROFILE_EXISTS"
                )

            with config_file.open("w", encoding="utf-8") as f:
                f.write(new_config.model_dump_json(indent=2))

            # Set as default if requested
            if set_as_default:
                current_file = config_dir / "current.txt"
                with current_file.open("w", encoding="utf-8") as f:
                    f.write(name)

            return self._create_success_result(data={"profile": name}, message=f"Profile '{name}' created successfully")

        except (ValidationError, OSError, PermissionError, ValueError) as e:
            return self._handle_api_error(e)

    def get_profile(self, name: str | None = None) -> CommandResult:
        """Get profile configuration details.

        Args:
            name: Profile name (uses current if not specified)

        Returns:
            CommandResult with profile details
        """
        try:
            config_dir = Path.home() / ".rag-cli"

            if name is None:
                # Get current profile
                current_file = config_dir / "current.txt"
                name = current_file.read_text(encoding="utf-8").strip() if current_file.exists() else "default"

            config_file = config_dir / f"{name}.json"
            if not config_file.exists():
                return self._create_error_result(message=f"Profile '{name}' not found", error_code="PROFILE_NOT_FOUND")

            # Load and return configuration
            profile_config = RAGConfig.model_validate_json(config_file.read_text(encoding="utf-8"))

            return self._create_success_result(
                data=profile_config.model_dump(), message=f"Profile '{name}' details retrieved"
            )

        except (ValidationError, OSError, PermissionError, ValueError) as e:
            return self._handle_api_error(e)

    def update_profile(self, name: str, api_url: str | None = None, timeout: int | None = None) -> CommandResult:
        """Update profile configuration.

        Args:
            name: Profile name
            api_url: New API URL
            timeout: New timeout value

        Returns:
            CommandResult with update status
        """
        try:
            config_dir = Path.home() / ".rag-cli"
            config_file = config_dir / f"{name}.json"

            if not config_file.exists():
                return self._create_error_result(message=f"Profile '{name}' not found", error_code="PROFILE_NOT_FOUND")

            # Load existing configuration
            profile_config = RAGConfig.model_validate_json(config_file.read_text(encoding="utf-8"))

            # Update fields if provided
            if api_url:
                profile_config.api_url = HttpUrl(api_url)
            if timeout is not None:
                profile_config.timeout = timeout

            # Save updated configuration
            with config_file.open("w", encoding="utf-8") as f:
                f.write(profile_config.model_dump_json(indent=2))

            return self._create_success_result(
                data=profile_config.model_dump(), message=f"Profile '{name}' updated successfully"
            )

        except (ValidationError, OSError, PermissionError, ValueError) as e:
            return self._handle_api_error(e)

    def delete_profile(self, name: str, force: bool = False) -> CommandResult:
        """Delete a configuration profile.

        Args:
            name: Profile name
            force: Force deletion without confirmation

        Returns:
            CommandResult with deletion status
        """
        try:
            if name == "default" and not force:
                return self._create_error_result(
                    message="Cannot delete default profile without --force flag", error_code="DEFAULT_PROFILE_PROTECTED"
                )

            config_dir = Path.home() / ".rag-cli"
            config_file = config_dir / f"{name}.json"

            if not config_file.exists():
                return self._create_error_result(message=f"Profile '{name}' not found", error_code="PROFILE_NOT_FOUND")

            # Remove profile file
            config_file.unlink()

            # Update current profile if it was deleted
            current_file = config_dir / "current.txt"
            if current_file.exists():
                current_profile = current_file.read_text(encoding="utf-8").strip()
                if current_profile == name:
                    # Set to default or first available profile
                    available_profiles = [f.stem for f in config_dir.glob("*.json") if f.stem != "current"]
                    if available_profiles:
                        new_current = available_profiles[0]
                        with current_file.open("w", encoding="utf-8") as f:
                            f.write(new_current)
                    else:
                        current_file.unlink()

            return self._create_success_result(message=f"Profile '{name}' deleted successfully")

        except (OSError, PermissionError, ValueError) as e:
            return self._handle_api_error(e)

    def set_current_profile(self, name: str) -> CommandResult:
        """Set the current active profile.

        Args:
            name: Profile name to set as current

        Returns:
            CommandResult with status
        """
        try:
            config_dir = Path.home() / ".rag-cli"
            config_file = config_dir / f"{name}.json"

            if not config_file.exists():
                return self._create_error_result(message=f"Profile '{name}' not found", error_code="PROFILE_NOT_FOUND")

            # Set as current profile
            current_file = config_dir / "current.txt"
            with current_file.open("w", encoding="utf-8") as f:
                f.write(name)

            return self._create_success_result(message=f"Current profile set to '{name}'")

        except (OSError, PermissionError, ValueError) as e:
            return self._handle_api_error(e)

    def get_current_profile(self) -> CommandResult:
        """Get the current active profile name.

        Returns:
            CommandResult with current profile
        """
        try:
            config_dir = Path.home() / ".rag-cli"
            current_file = config_dir / "current.txt"

            current_profile = current_file.read_text(encoding="utf-8").strip() if current_file.exists() else "default"

            return self._create_success_result(
                data={"current_profile": current_profile}, message=f"Current profile: {current_profile}"
            )

        except (OSError, PermissionError, ValueError) as e:
            return self._handle_api_error(e)

    def export_profile(self, name: str, output_path: str | Path | None = None) -> CommandResult:
        """Export profile configuration to a file.

        Args:
            name: Profile name to export
            output_path: Optional output file path

        Returns:
            CommandResult with export status
        """
        try:
            config_dir = Path.home() / ".rag-cli"
            config_file = config_dir / f"{name}.json"

            if not config_file.exists():
                return self._create_error_result(message=f"Profile '{name}' not found", error_code="PROFILE_NOT_FOUND")

            # Determine output path
            output_file = Path(output_path) if output_path else Path(f"{name}-profile.json")

            # Copy configuration file
            output_file.write_text(config_file.read_text(encoding="utf-8"), encoding="utf-8")

            return self._create_success_result(
                data={"output_path": str(output_file)}, message=f"Profile '{name}' exported to {output_file}"
            )

        except (OSError, PermissionError, ValueError) as e:
            return self._handle_api_error(e)

    def import_profile(self, config_path: str | Path, name: str | None = None) -> CommandResult:
        """Import profile configuration from a file.

        Args:
            config_path: Path to configuration file
            name: Optional profile name (uses filename if not provided)

        Returns:
            CommandResult with import status
        """
        try:
            config_path = Path(config_path)
            if not config_path.exists():
                return self._create_error_result(
                    message=f"Configuration file not found: {config_path}", error_code="CONFIG_FILE_NOT_FOUND"
                )

            # Load and validate configuration
            try:
                profile_config = RAGConfig.model_validate_json(config_path.read_text(encoding="utf-8"))
            except (ValidationError, json.JSONDecodeError, ValueError) as e:
                return self._create_error_result(
                    message=f"Invalid configuration file: {e!s}", error_code="INVALID_CONFIG_FILE"
                )

            # Determine profile name
            if name is None:
                name = config_path.stem

            # Update profile name in config
            profile_config.profile = name

            # Save imported profile
            config_dir = Path.home() / ".rag-cli"
            config_dir.mkdir(exist_ok=True)

            config_file = config_dir / f"{name}.json"
            with config_file.open("w", encoding="utf-8") as f:
                f.write(profile_config.model_dump_json(indent=2))

            return self._create_success_result(
                data={"profile": name}, message=f"Profile '{name}' imported successfully"
            )

        except (ValidationError, OSError, PermissionError, ValueError) as e:
            return self._handle_api_error(e)

    def validate_profile(self, name: str) -> CommandResult:
        """Validate profile configuration and connectivity.

        Args:
            name: Profile name to validate

        Returns:
            CommandResult with validation status
        """
        try:
            config_dir = Path.home() / ".rag-cli"
            config_file = config_dir / f"{name}.json"

            if not config_file.exists():
                return self._create_error_result(message=f"Profile '{name}' not found", error_code="PROFILE_NOT_FOUND")

            # Load and validate configuration structure
            try:
                profile_config = RAGConfig.model_validate_json(config_file.read_text(encoding="utf-8"))
            except (ValidationError, json.JSONDecodeError, ValueError) as e:
                return self._create_error_result(
                    message=f"Invalid profile configuration: {e!s}", error_code="INVALID_PROFILE_CONFIG"
                )

            # Test connectivity
            test_client = RAGAPIClient(profile_config)
            try:
                test_client.get("/health")
                connectivity_status = "OK"
                connectivity_message = "API connectivity verified"
            except (APIError, AuthenticationError, RAGCLIError) as e:
                connectivity_status = "FAILED"
                connectivity_message = f"API connectivity failed: {e!s}"

            validation_results = {
                "profile": name,
                "config_valid": True,
                "connectivity_status": connectivity_status,
                "connectivity_message": connectivity_message,
                "api_url": str(profile_config.api_url),
                "timeout": profile_config.timeout,
            }

            return self._create_success_result(
                data=validation_results, message=f"Profile '{name}' validation completed"
            )

        except (ValidationError, OSError, PermissionError, ValueError) as e:
            return self._handle_api_error(e)
