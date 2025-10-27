"""Atomic tests for CLI components.

These tests focus on individual functions and methods in isolation,
testing the smallest units of functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from rag_solution.cli.commands.base import BaseCommand, CommandResult
from rag_solution.cli.config import ProfileManager, RAGConfig
from rag_solution.cli.exceptions import AuthenticationError, ConfigurationError, RAGCLIError, ValidationError
from pydantic import HttpUrl


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
        # Use a valid JWT token for testing
        valid_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

        config = RAGConfig(
            api_url=HttpUrl("https://api.example.com"),
            profile="production",
            timeout=60,
            auth_token=valid_jwt,
            output_format="json",
            verbose=True,
            max_retries=5,
            dry_run=True,
        )

        assert str(config.api_url) == "https://api.example.com/"
        assert config.profile == "production"
        assert config.timeout == 60
        assert config.auth_token == valid_jwt
        assert config.output_format == "json"
        assert config.verbose is True
        assert config.max_retries == 5
        assert config.dry_run is True

    def test_invalid_api_url(self) -> None:
        """Test validation of invalid API URL."""
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            RAGConfig(api_url=HttpUrl("invalid-url"))

    def test_invalid_timeout(self) -> None:
        """Test validation of invalid timeout."""
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            RAGConfig(timeout=0)  # Must be >= 1

    def test_invalid_output_format(self) -> None:
        """Test validation of invalid output format."""
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            RAGConfig(output_format="invalid")

    def test_invalid_max_retries(self) -> None:
        """Test validation of invalid max retries."""
        from pydantic import ValidationError as PydanticValidationError

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
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            RAGConfig(timeout=0)  # Invalid timeout


class TestProfileManager:
    """Test ProfileManager functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.profiles_dir = Path(self.temp_dir) / "profiles"
        self.profiles_dir.mkdir(exist_ok=True)

        # Create a fresh ProfileManager for each test
        self.profile_manager = ProfileManager()

        # Mock the directories to use temp directory
        self.config_dir_patcher = patch.object(self.profile_manager, "config_dir", Path(self.temp_dir))
        self.profiles_dir_patcher = patch.object(self.profile_manager, "profiles_dir", self.profiles_dir)

        # Mock RAGConfig methods to use the temp directory
        self.load_from_file_patcher = patch("backend.rag_solution.cli.config.RAGConfig.load_from_file")
        self.mock_load_from_file = self.load_from_file_patcher.start()

        self.save_to_file_patcher = patch("backend.rag_solution.cli.config.RAGConfig.save_to_file")
        self.mock_save_to_file = self.save_to_file_patcher.start()

        self.config_dir_patcher.start()
        self.profiles_dir_patcher.start()

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        import shutil

        # Stop the patchers
        self.config_dir_patcher.stop()
        self.profiles_dir_patcher.stop()
        self.load_from_file_patcher.stop()
        self.save_to_file_patcher.stop()

        # Clean up temp directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_list_profiles_empty(self) -> None:
        """Test listing profiles when none exist."""
        # Mock load_from_file to raise an exception (simulating no file)
        self.mock_load_from_file.side_effect = Exception("File not found")

        profiles = self.profile_manager.list_profiles()

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
        # Mock the profile_exists method to return True for the second call
        with patch.object(self.profile_manager, "profile_exists") as mock_exists:
            mock_exists.side_effect = [False, True]  # First call returns False, second returns True

            # Create first profile
            self.profile_manager.create_profile("test-profile", "https://test.example.com")

            # Try to create again
            with pytest.raises(ConfigurationError):
                self.profile_manager.create_profile("test-profile", "https://test.example.com")

    def test_delete_profile(self) -> None:
        """Test deleting a profile."""
        # Mock the exists method to return True (profile exists)
        with patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.unlink") as mock_unlink:
            mock_unlink.return_value = None

            # Delete profile
            result = self.profile_manager.delete_profile("test-profile")

            assert result is True
            mock_unlink.assert_called_once()

    def test_delete_nonexistent_profile(self) -> None:
        """Test deleting non-existent profile."""
        with pytest.raises(ConfigurationError):
            self.profile_manager.delete_profile("nonexistent")

    def test_delete_default_profile(self) -> None:
        """Test deleting default profile."""
        with pytest.raises(ConfigurationError):
            self.profile_manager.delete_profile("default")

    def test_profile_exists(self) -> None:
        """Test checking if profile exists."""
        # Mock the exists method to simulate file existence
        with patch("pathlib.Path.exists") as mock_exists:
            # Initially file doesn't exist
            mock_exists.return_value = False
            assert self.profile_manager.profile_exists("test-profile") is False

            # Now simulate file exists
            mock_exists.return_value = True
            assert self.profile_manager.profile_exists("test-profile") is True

    def test_list_profiles_with_data(self) -> None:
        """Test listing profiles with data."""
        # Mock the glob method to return profile files
        with patch("pathlib.Path.glob") as mock_glob:
            # Create mock files
            mock_file1 = Mock()
            mock_file1.stem = "profile1"
            mock_file1.stat.return_value.st_ctime = 1234567890
            mock_file1.stat.return_value.st_mtime = 1234567890

            mock_file2 = Mock()
            mock_file2.stem = "profile2"
            mock_file2.stat.return_value.st_ctime = 1234567891
            mock_file2.stat.return_value.st_mtime = 1234567891

            mock_glob.return_value = [mock_file1, mock_file2]

            # Mock load_from_file to return configs
            mock_config1 = Mock()
            mock_config1.api_url = "https://api1.example.com/"
            mock_config1.auth_token = None

            mock_config2 = Mock()
            mock_config2.api_url = "https://api2.example.com/"
            mock_config2.auth_token = None

            self.mock_load_from_file.side_effect = [mock_config1, mock_config2]

            profiles = self.profile_manager.list_profiles()

            assert len(profiles) == 2
            assert "profile1" in profiles
            assert "profile2" in profiles
            assert profiles["profile1"]["api_url"] == "https://api1.example.com/"
            assert profiles["profile2"]["api_url"] == "https://api2.example.com/"
