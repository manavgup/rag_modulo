"""Atomic tests for CLI components.

These tests focus on individual functions and methods in isolation,
testing the smallest units of functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydantic import HttpUrl
from pydantic import ValidationError as PydanticValidationError

from rag_solution.cli.commands.base import BaseCommand, CommandResult
from rag_solution.cli.config import ProfileManager, RAGConfig
from rag_solution.cli.exceptions import AuthenticationError, ConfigurationError, RAGCLIError, ValidationError


class TestCommandResult:
    """Test CommandResult model."""

    def test_success_result_creation(self) -> None:
        """Test creating a successful command result."""
        result = CommandResult(success=True, message="Test success")

        assert result.success is True
        assert result.message == "Test success"
        assert result.data is None
        assert result.error_code is None

    def test_error_result_creation(self) -> None:
        """Test creating an error command result."""
        result = CommandResult(success=False, message="Test error", error_code="TEST_ERROR", data={"key": "value"})

        assert result.success is False
        assert result.message == "Test error"
        assert result.error_code == "TEST_ERROR"
        assert result.data == {"key": "value"}

    def test_result_with_data(self) -> None:
        """Test creating result with data."""
        data = {"items": [1, 2, 3], "total": 3}
        result = CommandResult(success=True, data=data)

        assert result.success is True
        assert result.data == data


class TestBaseCommand:
    """Test BaseCommand functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_api_client = Mock()
        self.mock_config = Mock()
        self.command = BaseCommand(self.mock_api_client, self.mock_config)

    def test_require_authentication_success(self) -> None:
        """Test authentication check when authenticated."""
        self.mock_api_client.is_authenticated.return_value = True

        # Should not raise exception
        self.command._require_authentication()

    def test_require_authentication_failure(self) -> None:
        """Test authentication check when not authenticated."""
        self.mock_api_client.is_authenticated.return_value = False

        with pytest.raises(AuthenticationError, match="Authentication required"):
            self.command._require_authentication()

    def test_create_success_result(self) -> None:
        """Test creating success result."""
        data = {"test": "data"}
        message = "Success message"

        result = self.command._create_success_result(data=data, message=message)

        assert result.success is True
        assert result.data == data
        assert result.message == message
        assert result.error_code is None

    def test_create_error_result(self) -> None:
        """Test creating error result."""
        message = "Error message"
        error_code = "TEST_ERROR"
        data = {"error": "details"}

        result = self.command._create_error_result(message=message, error_code=error_code, data=data)

        assert result.success is False
        assert result.message == message
        assert result.error_code == error_code
        assert result.data == data

    def test_handle_api_error_authentication(self) -> None:
        """Test handling authentication errors."""
        error = AuthenticationError("Auth failed")

        result = self.command._handle_api_error(error)

        assert result.success is False
        assert "Auth failed" in result.message
        assert result.error_code == "AUTHENTICATION_FAILED"

    def test_handle_api_error_rag_cli(self) -> None:
        """Test handling RAGCLIError."""
        error = RAGCLIError("CLI error")
        error.error_code = "CLI_ERROR"

        result = self.command._handle_api_error(error)

        assert result.success is False
        assert "CLI error" in result.message
        assert result.error_code == "CLI_ERROR"

    def test_handle_api_error_generic(self) -> None:
        """Test handling generic exceptions."""
        error = ValueError("Generic error")

        result = self.command._handle_api_error(error)

        assert result.success is False
        assert "Unexpected error" in result.message
        assert result.error_code == "UNEXPECTED_ERROR"

    def test_is_dry_run_enabled(self) -> None:
        """Test dry-run mode when enabled."""
        self.mock_config.dry_run = True

        assert self.command._is_dry_run() is True

    def test_is_dry_run_disabled(self) -> None:
        """Test dry-run mode when disabled."""
        self.mock_config.dry_run = False

        assert self.command._is_dry_run() is False

    def test_is_dry_run_no_config(self) -> None:
        """Test dry-run mode when no config."""
        command = BaseCommand(self.mock_api_client, None)

        assert command._is_dry_run() is False

    def test_create_dry_run_result(self) -> None:
        """Test creating dry-run result."""
        operation = "delete user 123"
        data = {"user_id": "123"}

        result = self.command._create_dry_run_result(operation, data)

        assert result.success is True
        assert "[DRY RUN]" in result.message
        assert result.data["dry_run"] is True
        assert result.data["operation"] == operation
        assert result.data["affected_data"] == data


class TestRAGConfig:
    """Test RAGConfig model."""

    def test_default_config(self) -> None:
        """Test creating config with default values."""
        config = RAGConfig()

        assert str(config.api_url) == "http://localhost:8000/"
        assert config.profile == "default"
        assert config.timeout == 30
        assert config.auth_token is None
        assert config.output_format == "table"
        assert config.verbose is False
        assert config.max_retries == 3
        assert config.dry_run is False

    def test_custom_config(self) -> None:
        """Test creating config with custom values."""
        config = RAGConfig(
            api_url=HttpUrl("https://api.example.com"),
            profile="production",
            timeout=60,
            auth_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
            output_format="json",
            verbose=True,
            max_retries=5,
            dry_run=True,
        )

        assert str(config.api_url) == "https://api.example.com/"
        assert config.profile == "production"
        assert config.timeout == 60
        assert (
            config.auth_token
            == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        )
        assert config.output_format == "json"
        assert config.verbose is True
        assert config.max_retries == 5
        assert config.dry_run is True

    def test_invalid_api_url(self) -> None:
        """Test validation of invalid API URL."""
        with pytest.raises(PydanticValidationError):
            RAGConfig(api_url=HttpUrl("invalid-url"))

    def test_invalid_timeout(self) -> None:
        """Test validation of invalid timeout."""
        with pytest.raises(PydanticValidationError):
            RAGConfig(timeout=0)  # Must be >= 1

    def test_invalid_output_format(self) -> None:
        """Test validation of invalid output format."""
        with pytest.raises(PydanticValidationError):
            RAGConfig(output_format="invalid")

    def test_invalid_max_retries(self) -> None:
        """Test validation of invalid max retries."""
        with pytest.raises(PydanticValidationError):
            RAGConfig(max_retries=11)  # Must be <= 10

    def test_invalid_auth_token_format(self) -> None:
        """Test validation of invalid auth token format."""
        with pytest.raises(ValidationError):
            RAGConfig(auth_token="invalid-jwt")  # Not a valid JWT format

    def test_valid_jwt_token(self) -> None:
        """Test validation of valid JWT token."""
        # Valid JWT format: header.payload.signature
        valid_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

        config = RAGConfig(auth_token=valid_jwt)
        assert config.auth_token == valid_jwt

    def test_config_to_dict(self) -> None:
        """Test converting config to dictionary."""
        config = RAGConfig(profile="test", verbose=True)
        config_dict = config.to_dict()

        assert "profile" in config_dict
        assert "verbose" in config_dict
        assert config_dict["profile"] == "test"
        assert config_dict["verbose"] is True

    def test_config_from_dict(self) -> None:
        """Test creating config from dictionary."""
        data = {
            "profile": "test",
            "timeout": 45,
            "verbose": True,
            "dry_run": True,
        }

        config = RAGConfig.from_dict(data)

        assert config.profile == "test"
        assert config.timeout == 45
        assert config.verbose is True
        assert config.dry_run is True

    def test_config_from_env(self) -> None:
        """Test creating config from environment variables."""
        env_vars = {
            "RAG_CLI_API_URL": "https://test.example.com",
            "RAG_CLI_PROFILE": "test",
            "RAG_CLI_TIMEOUT": "60",
            "RAG_CLI_VERBOSE": "true",
            "RAG_CLI_DRY_RUN": "true",
        }

        with patch.dict("os.environ", env_vars):
            config = RAGConfig.from_env()

            assert str(config.api_url) == "https://test.example.com/"
            assert config.profile == "test"
            assert config.timeout == 60
            assert config.verbose is True
            assert config.dry_run is True

    def test_config_validation(self) -> None:
        """Test config validation."""
        config = RAGConfig()

        # Should not raise exception
        assert config.is_valid() is True

    def test_config_validation_failure(self) -> None:
        """Test config validation failure."""
        with pytest.raises(PydanticValidationError):
            RAGConfig(timeout=0)  # Invalid timeout - should fail during instantiation


class TestProfileManager:
    """Test ProfileManager functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Create a fresh ProfileManager for each test
        self.profile_manager = ProfileManager()

        # Mock the config directory to use temp directory
        self.profile_manager.config_dir = Path(self.temp_dir)
        self.profile_manager.profiles_dir = Path(self.temp_dir) / "profiles"
        self.profile_manager.profiles_dir.mkdir(exist_ok=True)

        # ProfileManager doesn't have get_config_dir method, so we just patch RAGConfig

        # Patch RAGConfig.get_config_dir to use our temp directory
        self.rag_config_patch = patch.object(RAGConfig, "get_config_dir", return_value=Path(self.temp_dir))
        self.rag_config_patch.start()

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        import shutil

        # Stop the patch
        self.rag_config_patch.stop()

        # Clean up temp directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_list_profiles_empty(self) -> None:
        """Test listing profiles when none exist."""
        profiles = self.profile_manager.list_profiles()

        # Should be empty initially (no profiles created yet)
        assert profiles == {}

    def test_create_profile(self) -> None:
        """Test creating a new profile."""
        profile = self.profile_manager.create_profile(
            name="test-profile", api_url="https://test.example.com", description="Test profile"
        )

        assert profile.profile == "test-profile"
        assert str(profile.api_url) == "https://test.example.com/"

    def test_create_profile_already_exists(self) -> None:
        """Test creating profile that already exists."""
        # Create first profile
        profile1 = self.profile_manager.create_profile("test-profile", "https://test.example.com")
        assert profile1.profile == "test-profile"

        # Create again (should overwrite)
        profile2 = self.profile_manager.create_profile("test-profile", "https://test.example.com")
        assert profile2.profile == "test-profile"

        # Both should be the same profile
        assert profile1.profile == profile2.profile

    def test_delete_profile(self) -> None:
        """Test deleting a profile."""
        # Create profile
        self.profile_manager.create_profile("test-profile", "https://test.example.com")

        # Delete profile
        result = self.profile_manager.delete_profile("test-profile")

        assert result is True

    def test_delete_nonexistent_profile(self) -> None:
        """Test deleting non-existent profile."""
        with pytest.raises(ConfigurationError):  # Should raise ConfigurationError
            self.profile_manager.delete_profile("nonexistent")

    def test_delete_default_profile(self) -> None:
        """Test deleting default profile."""
        with pytest.raises(ConfigurationError):  # Should raise ConfigurationError
            self.profile_manager.delete_profile("default")

    def test_profile_exists(self) -> None:
        """Test checking if profile exists."""
        # Initially should not exist
        assert self.profile_manager.profile_exists("test-profile") is False

        # Create profile
        self.profile_manager.create_profile("test-profile", "https://test.example.com")

        # Should now exist
        assert self.profile_manager.profile_exists("test-profile") is True

    def test_list_profiles_with_data(self) -> None:
        """Test listing profiles with data."""
        # Create multiple profiles
        self.profile_manager.create_profile("profile1", "https://api1.example.com")
        self.profile_manager.create_profile("profile2", "https://api2.example.com")

        profiles = self.profile_manager.list_profiles()

        # Should have 2 created profiles
        assert len(profiles) == 2
        assert "profile1" in profiles
        assert "profile2" in profiles
        assert profiles["profile1"]["api_url"] == "https://api1.example.com/"
        assert profiles["profile2"]["api_url"] == "https://api2.example.com/"
