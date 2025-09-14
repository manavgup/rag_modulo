"""Atomic tests for CLI core functionality - command parsing, config, and authentication logic."""

from argparse import ArgumentParser
from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from rag_solution.cli.auth import AuthManager, AuthResult
from rag_solution.cli.config import RAGConfig
from rag_solution.cli.main import create_main_parser


@pytest.mark.atomic
class TestCLICommandParsing:
    """Test CLI command parsing logic without external dependencies."""

    def test_main_parser_creation(self):
        """Test main parser is created with expected structure."""
        parser = create_main_parser()

        assert parser is not None
        assert isinstance(parser, ArgumentParser)
        assert parser.description == "RAG Modulo - Comprehensive CLI"

    def test_global_options_parsing(self):
        """Test global options are parsed correctly."""
        parser = create_main_parser()

        # Test default values
        args = parser.parse_args([])
        assert args.profile == "default"
        assert args.api_url == "http://localhost:8000"
        assert args.verbose is False
        assert args.output == "table"

    def test_auth_commands_parsing(self):
        """Test authentication commands parsing."""
        parser = create_main_parser()

        # Test login command
        args = parser.parse_args(["auth", "login", "--username", "test@example.com"])
        assert args.command == "auth"
        assert args.auth_command == "login"
        assert args.username == "test@example.com"

        # Test logout command
        args = parser.parse_args(["auth", "logout"])
        assert args.command == "auth"
        assert args.auth_command == "logout"

    def test_main_commands_parsing(self):
        """Test main resource commands parsing."""
        parser = create_main_parser()

        # Test collections command
        args = parser.parse_args(["collections", "list"])
        assert args.command == "collections"
        assert args.collections_command == "list"

        # Test users command
        args = parser.parse_args(["users", "create", "test@example.com", "--name", "Test User"])
        assert args.command == "users"
        assert args.users_command == "create"
        assert args.email == "test@example.com"
        assert args.name == "Test User"

        # Test search command
        args = parser.parse_args(["search", "query", "collection123", "test query"])
        assert args.command == "search"
        assert args.search_command == "query"
        assert args.collection_id == "collection123"
        assert args.query == "test query"


@pytest.mark.atomic
class TestCLIConfiguration:
    """Test CLI configuration management without external dependencies."""

    def test_default_config_creation(self):
        """Test default configuration values."""
        config = RAGConfig()

        assert config.api_url == "http://localhost:8000"
        assert config.profile == "default"
        assert config.timeout == 30
        assert config.auth_token is None

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        config = RAGConfig(api_url="https://api.example.com")
        assert str(config.api_url) == "https://api.example.com/"

        # Invalid URL
        with pytest.raises(ValidationError):
            RAGConfig(api_url="invalid-url")

        # Invalid timeout
        with pytest.raises(ValidationError):
            RAGConfig(timeout=-1)


@pytest.mark.atomic
class TestCLIAuthentication:
    """Test CLI authentication logic without external dependencies."""

    def test_auth_manager_creation(self, tmp_path, monkeypatch):
        """Test AuthManager creation with profiles."""
        # Set a writable home directory for testing
        monkeypatch.setenv("HOME", str(tmp_path))
        auth_manager = AuthManager(profile="test")
        assert auth_manager.profile == "test"
        assert ".rag-cli" in str(auth_manager.token_file)

    def test_token_validation_logic(self, tmp_path, monkeypatch):
        """Test token validation logic."""
        # Set a writable home directory for testing
        monkeypatch.setenv("HOME", str(tmp_path))
        auth_manager = AuthManager()

        # Valid token (1 hour in future)
        valid_expires = datetime.now() + timedelta(hours=1)
        assert auth_manager.is_token_valid("token", valid_expires) is True

        # Expired token
        expired_expires = datetime.now() - timedelta(hours=1)
        assert auth_manager.is_token_valid("token", expired_expires) is False

        # Near expiry (5 minutes left - should be considered expired)
        near_expiry = datetime.now() + timedelta(minutes=5)
        assert auth_manager.is_token_valid("token", near_expiry) is False

    def test_auth_headers_generation(self, tmp_path, monkeypatch):
        """Test authentication headers generation."""
        # Set a writable home directory for testing
        monkeypatch.setenv("HOME", str(tmp_path))
        auth_manager = AuthManager()

        headers = auth_manager.generate_auth_headers("test-token")

        expected = {"Authorization": "Bearer test-token"}
        assert headers == expected

    def test_auth_result_creation(self):
        """Test authentication result objects."""
        # Success result
        success_result = AuthResult(success=True, token="valid-token", message="Login successful")

        assert success_result.success is True
        assert success_result.token == "valid-token"

        # Failure result
        failure_result = AuthResult(success=False, message="Invalid credentials", error_code="INVALID_CREDENTIALS")

        assert failure_result.success is False
        assert failure_result.token is None
        assert failure_result.error_code == "INVALID_CREDENTIALS"


@pytest.mark.atomic
class TestCLIOutputFormatting:
    """Test CLI output formatting utilities."""

    def test_format_table_output(self):
        """Test table output formatting."""
        from rag_solution.cli.output import format_table_output

        data = [{"name": "Collection 1", "status": "active"}, {"name": "Collection 2", "status": "processing"}]

        result = format_table_output(data)

        assert "Collection 1" in result
        assert "Collection 2" in result
        assert "active" in result
        assert "processing" in result

    def test_format_json_output(self):
        """Test JSON output formatting."""
        from rag_solution.cli.output import format_json_output

        data = {"collections": [{"name": "Test", "id": "123"}]}
        result = format_json_output(data)

        assert '"collections"' in result
        assert '"name": "Test"' in result

    def test_format_operation_result(self):
        """Test operation result formatting."""
        from rag_solution.cli.output import format_operation_result

        # Success case
        success_result = format_operation_result("Operation completed", success_count=5, error_count=0)
        assert "✅" in success_result
        assert "5 items processed" in success_result

        # With errors case
        error_result = format_operation_result("Batch operation", success_count=3, error_count=2)
        assert "⚠️" in error_result
        assert "3 successful" in error_result
        assert "2 errors" in error_result
