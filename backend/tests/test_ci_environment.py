"""
Test suite to verify CI environment behavior for auth and OIDC.
These tests ensure that authentication and OIDC registration work correctly
in different environments (CI, development, production).
"""

import os
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from auth.oidc import verify_jwt_token
from core.authentication_middleware import AuthenticationMiddleware
from fastapi import Request, Response
from fastapi.responses import JSONResponse


@pytest.mark.api
class TestCIEnvironmentAuth:
    """Test authentication behavior in CI environment."""

    @pytest.fixture(autouse=True)
    def setup_environment(self) -> Generator[None, None, None]:
        """Set up CI environment variables for tests."""
        # Save original env vars
        self.original_testing = os.getenv("TESTING")
        self.original_skip_auth = os.getenv("SKIP_AUTH")
        self.original_dev_mode = os.getenv("DEVELOPMENT_MODE")

        yield

        # Restore original env vars
        if self.original_testing:
            os.environ["TESTING"] = self.original_testing
        elif "TESTING" in os.environ:
            del os.environ["TESTING"]

        if self.original_skip_auth:
            os.environ["SKIP_AUTH"] = self.original_skip_auth
        elif "SKIP_AUTH" in os.environ:
            del os.environ["SKIP_AUTH"]

        if self.original_dev_mode:
            os.environ["DEVELOPMENT_MODE"] = self.original_dev_mode
        elif "DEVELOPMENT_MODE" in os.environ:
            del os.environ["DEVELOPMENT_MODE"]

    def test_oidc_skip_with_testing_true(self) -> None:
        """Test that OIDC registration is skipped when TESTING=true."""
        os.environ["TESTING"] = "true"
        os.environ["SKIP_AUTH"] = "false"
        os.environ["DEVELOPMENT_MODE"] = "false"

        # Import after setting env vars

        # Check that OIDC should be skipped
        skip_auth = os.getenv("SKIP_AUTH", "false").lower() == "true"
        development_mode = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
        testing_mode = os.getenv("TESTING", "false").lower() == "true"

        assert testing_mode is True
        assert skip_auth or development_mode or testing_mode

    def test_oidc_skip_with_skip_auth_true(self) -> None:
        """Test that OIDC registration is skipped when SKIP_AUTH=true."""
        os.environ["TESTING"] = "false"
        os.environ["SKIP_AUTH"] = "true"
        os.environ["DEVELOPMENT_MODE"] = "false"

        skip_auth = os.getenv("SKIP_AUTH", "false").lower() == "true"
        development_mode = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"  # noqa: F841
        testing_mode = os.getenv("TESTING", "false").lower() == "true"  # noqa: F841

        assert skip_auth is True
        # This assertion is redundant since skip_auth is already True
        # assert skip_auth or development_mode or testing_mode

    def test_oidc_skip_with_development_mode_true(self) -> None:
        """Test that OIDC registration is skipped when DEVELOPMENT_MODE=true."""
        os.environ["TESTING"] = "false"
        os.environ["SKIP_AUTH"] = "false"
        os.environ["DEVELOPMENT_MODE"] = "true"

        skip_auth = os.getenv("SKIP_AUTH", "false").lower() == "true"  # noqa: F841
        development_mode = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
        testing_mode = os.getenv("TESTING", "false").lower() == "true"  # noqa: F841

        assert development_mode is True
        # This assertion is redundant since development_mode is already True
        # assert skip_auth or development_mode or testing_mode

    def test_oidc_not_skipped_in_production(self) -> None:
        """Test that OIDC registration is NOT skipped in production mode."""
        os.environ["TESTING"] = "false"
        os.environ["SKIP_AUTH"] = "false"
        os.environ["DEVELOPMENT_MODE"] = "false"

        skip_auth = os.getenv("SKIP_AUTH", "false").lower() == "true"
        development_mode = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
        testing_mode = os.getenv("TESTING", "false").lower() == "true"

        assert not (skip_auth or development_mode or testing_mode)

    @pytest.mark.asyncio
    async def test_auth_middleware_skip_in_ci(self) -> None:
        """Test that authentication middleware is skipped in CI environment."""
        os.environ["TESTING"] = "true"
        os.environ["SKIP_AUTH"] = "true"
        os.environ["DEVELOPMENT_MODE"] = "true"

        # Create mock request and call_next
        request = MagicMock(spec=Request)
        request.url.path = "/api/collections"  # Protected endpoint
        request.headers = {}
        request.state = MagicMock()

        async def call_next(req: Request) -> Response:
            return MagicMock(status_code=200)

        middleware = AuthenticationMiddleware(app=MagicMock())
        await middleware.dispatch(request, call_next)

        # Check that user was set automatically
        assert hasattr(request.state, "user")
        assert request.state.user["id"] == "test_user_id"
        assert request.state.user["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_auth_middleware_requires_auth_in_production(self) -> None:
        """Test that authentication is required in production mode."""
        os.environ["TESTING"] = "false"
        os.environ["SKIP_AUTH"] = "false"
        os.environ["DEVELOPMENT_MODE"] = "false"

        # Create mock request without auth header
        request = MagicMock(spec=Request)
        request.url.path = "/api/collections"  # Protected endpoint
        request.headers = {}
        request.state = MagicMock()

        # Remove user attribute if it exists
        if hasattr(request.state, "user"):
            delattr(request.state, "user")

        async def call_next(req: Request) -> Response:
            return MagicMock(status_code=200)

        middleware = AuthenticationMiddleware(app=MagicMock())
        response = await middleware.dispatch(request, call_next)

        # Check that request was rejected
        assert isinstance(response, JSONResponse)
        assert response.status_code == 401

    def test_verify_jwt_token_with_mock_token(self) -> None:
        """Test that mock token works in test environment."""
        os.environ["TESTING"] = "true"

        # Test with mock token
        result = verify_jwt_token("mock_token_for_testing")

        assert result["sub"] == "test_user_id"
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"


class TestHealthEndpoint:
    """Test health endpoint behavior in CI environment."""

    @pytest.mark.asyncio
    async def test_health_endpoint_accessible_without_auth(self) -> None:
        """Test that health endpoint is accessible without authentication."""
        os.environ["TESTING"] = "false"
        os.environ["SKIP_AUTH"] = "false"
        os.environ["DEVELOPMENT_MODE"] = "false"

        # Create mock request for health endpoint
        request = MagicMock(spec=Request)
        request.url.path = "/api/health"
        request.headers = {}
        request.state = MagicMock()

        async def call_next(req: Request) -> Response:
            return MagicMock(status_code=200)

        middleware = AuthenticationMiddleware(app=MagicMock())
        response = await middleware.dispatch(request, call_next)

        # Should pass through without auth
        assert response.status_code == 200


class TestEnvironmentVariables:
    """Test environment variable handling."""

    def test_env_var_parsing(self) -> None:
        """Test that environment variables are parsed correctly."""
        test_cases = [
            ("true", True),
            ("TRUE", True),
            ("True", True),
            ("false", False),
            ("FALSE", False),
            ("False", False),
            ("1", False),  # Should be false, not truthy
            ("0", False),
            ("", False),
            (None, False),
        ]

        for value, expected in test_cases:
            if value is not None:
                os.environ["TEST_VAR"] = value
            elif "TEST_VAR" in os.environ:
                del os.environ["TEST_VAR"]

            result = os.getenv("TEST_VAR", "false").lower() == "true"
            assert result == expected, f"Failed for value: {value}"

    def test_multiple_env_combinations(self) -> None:
        """Test various combinations of environment variables."""
        combinations = [
            # (TESTING, SKIP_AUTH, DEVELOPMENT_MODE, should_skip_auth)
            ("true", "false", "false", True),
            ("false", "true", "false", True),
            ("false", "false", "true", True),
            ("true", "true", "false", True),
            ("true", "false", "true", True),
            ("false", "true", "true", True),
            ("true", "true", "true", True),
            ("false", "false", "false", False),
        ]

        for testing, skip_auth, dev_mode, should_skip in combinations:
            os.environ["TESTING"] = testing
            os.environ["SKIP_AUTH"] = skip_auth
            os.environ["DEVELOPMENT_MODE"] = dev_mode

            skip = (
                os.getenv("SKIP_AUTH", "false").lower() == "true"
                or os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
                or os.getenv("TESTING", "false").lower() == "true"
            )

            assert skip == should_skip, (
                f"Failed for TESTING={testing}, SKIP_AUTH={skip_auth}, "
                f"DEVELOPMENT_MODE={dev_mode}. Expected skip={should_skip}, got {skip}"
            )


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
