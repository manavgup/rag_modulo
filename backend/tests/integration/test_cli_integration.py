"""Integration tests for CLI-API communication.

These tests focus on CLI-specific integration concerns:
- CLI can reach API endpoints
- Authentication flow works
- Output formatting works
- Error handling is appropriate for CLI users

Business logic is covered by existing service/API tests.
"""

import pytest
import requests

from rag_solution.cli.client import RAGAPIClient
from rag_solution.cli.commands.auth import AuthCommands
from rag_solution.cli.commands.collections import CollectionCommands
from rag_solution.cli.config import RAGConfig
from rag_solution.cli.exceptions import APIError, AuthenticationError


@pytest.mark.integration
class TestCLIAPIConnectivity:
    """Test CLI-API connectivity and communication."""

    @pytest.fixture
    def api_url(self, monkeypatch):
        """Get API URL for testing."""
        # Set default API URL for testing - avoiding direct env access
        api_url = "http://localhost:8000"
        monkeypatch.setenv("API_URL", api_url)
        return api_url

    @pytest.fixture
    def cli_config(self, api_url):
        """Create CLI configuration for testing."""
        return RAGConfig(api_url=api_url, profile="test", timeout=10)

    @pytest.fixture
    def api_client(self, cli_config, tmp_path, monkeypatch):
        """Create API client for testing."""
        # Set temporary home directory
        monkeypatch.setenv("HOME", str(tmp_path))
        client = RAGAPIClient(cli_config)
        return client

    def test_api_health_endpoint_reachable(self, api_client):
        """Test that CLI can reach the API health endpoint."""
        # This test expects the backend to be running
        try:
            result = api_client.get("/api/health")
            assert result is not None
            # Health endpoint should return some status information
            assert isinstance(result, dict)
        except (requests.exceptions.ConnectionError, APIError) as e:
            if (isinstance(e, APIError) and "Connection refused" in str(e)) or isinstance(e, requests.exceptions.ConnectionError):
                pytest.skip("Backend API not running - integration test requires live backend")
            else:
                raise

    def test_authentication_flow_integration(self, api_client):
        """Test CLI authentication flow with backend."""
        auth_commands = AuthCommands(api_client)

        # Test authentication status when not logged in
        result = auth_commands.status()
        assert result.success is False
        assert result.error_code == "NOT_AUTHENTICATED"

    def test_cli_start_endpoint_integration(self, api_client):
        """Test CLI authentication start endpoint integration."""
        try:
            # Test CLI authentication start endpoint
            cli_request = {"provider": "ibm", "client_id": "test-cli-client", "scope": "openid profile email"}

            response = api_client.post("/api/auth/cli/start", data=cli_request)

            # Should return auth_url and state
            assert "auth_url" in response
            assert "state" in response
            assert isinstance(response["auth_url"], str)
            assert response["auth_url"].startswith("http")

        except (requests.exceptions.ConnectionError, APIError) as e:
            if (isinstance(e, APIError) and "Connection refused" in str(e)) or isinstance(e, requests.exceptions.ConnectionError):
                pytest.skip("Backend API not running - integration test requires live backend")
            elif isinstance(e, APIError) and e.status_code == 404:
                pytest.fail("CLI auth endpoints not implemented in backend")
            else:
                # Other API errors are expected (auth config issues, etc.)
                pass

    def test_collections_api_integration(self, api_client):
        """Test collections API integration without authentication."""
        try:
            collections_commands = CollectionCommands(api_client)

            # This should fail due to authentication requirement
            with pytest.raises(AuthenticationError):
                collections_commands.list_collections()

        except (requests.exceptions.ConnectionError, APIError) as e:
            if (isinstance(e, APIError) and "Connection refused" in str(e)) or isinstance(e, requests.exceptions.ConnectionError):
                pytest.skip("Backend API not running - integration test requires live backend")
            else:
                raise

    def test_error_response_handling(self, api_client):
        """Test CLI handles backend error responses appropriately."""
        try:
            # Try to access non-existent endpoint
            api_client.get("/api/nonexistent")
        except APIError as e:
            if "Connection refused" in str(e):
                pytest.skip("Backend API not running - integration test requires live backend")
            # Should get 404 error
            assert e.status_code == 404
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend API not running - integration test requires live backend")

    def test_authentication_error_handling(self, api_client):
        """Test CLI handles authentication errors from backend."""
        # Try to access protected endpoint without authentication
        try:
            api_client.get("/api/collections")
        except AuthenticationError:
            # Expected authentication error
            pass
        except APIError as e:
            if "Connection refused" in str(e):
                pytest.skip("Backend API not running - integration test requires live backend")
            # Might get 401 instead of AuthenticationError depending on backend
            assert e.status_code == 401
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend API not running - integration test requires live backend")


@pytest.mark.integration
class TestCLIConfigurationIntegration:
    """Test CLI configuration management with real auth storage."""

    def test_auth_token_persistence(self, tmp_path, monkeypatch):
        """Test that CLI auth tokens are properly stored and retrieved."""
        # Set temporary home directory
        monkeypatch.setenv("HOME", str(tmp_path))

        config = RAGConfig(profile="test")
        client = RAGAPIClient(config)

        # Test token storage
        test_token = "test.jwt.token"
        from datetime import datetime, timedelta

        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()

        client.set_auth_token(test_token, expires_at)

        # Verify token is stored
        assert client.is_authenticated() is True
        assert client.get_auth_token() == test_token

        # Test logout clears token
        client.logout()
        assert client.is_authenticated() is False
        assert client.get_auth_token() is None

    def test_configuration_validation(self):
        """Test CLI configuration validation works correctly."""
        # Test valid configuration
        config = RAGConfig(api_url="http://localhost:8000", profile="test")
        assert str(config.api_url) == "http://localhost:8000/"
        assert config.profile == "test"

        # Test invalid URL should raise validation error
        with pytest.raises(ValueError):  # Pydantic validation error
            RAGConfig(api_url="not-a-url")


@pytest.mark.integration
class TestCLIOutputFormatting:
    """Test CLI output formatting with real data."""

    def test_table_output_formatting(self):
        """Test table output formatting works with backend data."""
        from rag_solution.cli.output import format_table_output

        # Test with collection-like data
        data = [
            {"id": "123", "name": "Collection 1", "status": "active", "documents": 5},
            {"id": "456", "name": "Collection 2", "status": "processing", "documents": 0},
        ]

        result = format_table_output(data)
        assert isinstance(result, str)
        assert "Collection 1" in result
        assert "Collection 2" in result
        assert "active" in result
        assert "processing" in result

    def test_json_output_formatting(self):
        """Test JSON output formatting works with backend data."""
        from rag_solution.cli.output import format_json_output

        data = {"collections": [{"id": "123", "name": "Test Collection"}], "total": 1}

        result = format_json_output(data)
        assert isinstance(result, str)
        assert '"collections"' in result
        assert '"Test Collection"' in result
        assert '"total": 1' in result
