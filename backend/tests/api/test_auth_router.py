"""Tests for AuthRouter API endpoints."""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.testclient import TestClient

from core.config import settings
from main import app

# Test Data
TEST_USER = {
    "sub": "test-ibm-id",
    "email": "test@example.com",
    "name": "Test User",
    "uuid": "test-uuid",
    "role": "admin",  # Use admin role for broader access
}

TEST_JWT = jwt.encode(TEST_USER, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_jwt_verification():
    """Mock JWT verification."""

    def mock_verify(token):
        if token == "mock_token_for_testing" or token == TEST_JWT:
            return TEST_USER
        raise jwt.InvalidTokenError("Invalid token")

    with (
        patch("auth.oidc.verify_jwt_token", side_effect=mock_verify),
        patch("core.authentication_middleware.verify_jwt_token", side_effect=mock_verify),
    ):
        yield


@pytest.fixture
def mock_auth_middleware():
    """Mock authentication middleware."""

    async def mock_dispatch(request, call_next):
        # Define open paths that don't require auth
        open_paths = [
            "/api/auth/login",
            "/api/auth/callback",
            "/api/auth/oidc-config",
            "/api/auth/token",
            "/api/auth/userinfo",
            "/api/auth/session",
            "/api/health",
        ]

        # Check if path is open
        if any(request.url.path.startswith(path) for path in open_paths):
            return await call_next(request)

        # Handle authentication for protected paths
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

        token = auth_header.split(" ")[1]
        if token in ["mock_token_for_testing", "test-id-token", "valid-test-token", TEST_JWT]:
            # Add user info to request state for authenticated requests
            request.state.user = TEST_USER.copy()
            return await call_next(request)

        return JSONResponse(status_code=401, content={"detail": "Invalid token"})

    with patch("core.authentication_middleware.AuthenticationMiddleware.dispatch", side_effect=mock_dispatch):
        yield


@pytest.fixture
def auth_headers():
    """Create authentication headers."""
    return {"Authorization": f"Bearer {TEST_JWT}", "X-User-UUID": TEST_USER["uuid"], "X-User-Role": TEST_USER["role"]}


@pytest.fixture
def mock_ibm_oauth():
    """Mock IBM OAuth endpoints with proper token structure."""
    # Create a token that includes both id_token and userinfo
    mock_token_response = {
        "access_token": "mock_access_token",
        "id_token": TEST_JWT,
        "token_type": "Bearer",
        "expires_in": 3600,
        "expires_at": int((datetime.now() + timedelta(hours=1)).timestamp()),
        "userinfo": TEST_USER,
    }

    class MockResponse:
        def __init__(self, data, status_code=200):
            self.data = data
            self.status_code = status_code
            self.text = json.dumps(data)

        def json(self):
            return self.data

        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")

    # Mock the authorize_access_token to return proper structure
    async def mock_authorize_access_token(*args, **kwargs):
        return mock_token_response

    # Mock the authorize_redirect
    async def mock_authorize_redirect(*args, **kwargs):
        return RedirectResponse(url="https://test.com/authorize")

    # Create mock oauth object
    oauth_mock = MagicMock()
    oauth_mock.authorize_redirect = AsyncMock(side_effect=mock_authorize_redirect)
    oauth_mock.authorize_access_token = AsyncMock(side_effect=mock_authorize_access_token)

    with patch("auth.oidc.oauth.ibm", oauth_mock):
        yield oauth_mock


class TestAuthentication:
    def test_token_exchange(self, client, mock_auth_middleware):  # noqa: ARG002
        """Test POST /api/auth/token - exchanging auth code for token."""
        response_data = {
            "access_token": "test_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "id_token": "test_id_token",
        }

        # Create a ResponseMock class to ensure all attributes are regular values
        class ResponseMock:
            def __init__(self):
                self.status_code = 200
                self.text = json.dumps(response_data)
                self._json = response_data

            def json(self):
                return self._json

            def raise_for_status(self):
                pass

        mock_response = ResponseMock()

        # Create the mock post function
        async def mock_post(*args, **kwargs):
            return mock_response

        # Create the async client mock
        class AsyncClientMock:
            async def __aenter__(self):
                client_mock = MagicMock()
                client_mock.post = mock_post
                return client_mock

            async def __aexit__(self, exc_type, exc, tb):
                pass

        # Patch httpx.AsyncClient
        with patch("httpx.AsyncClient", return_value=AsyncClientMock()):
            response = client.post(
                "/api/auth/token",
                data={
                    "code": "test-code",
                    "grant_type": "authorization_code",
                    "redirect_uri": f"{settings.frontend_url}/api/auth/callback",
                    "client_id": settings.ibm_client_id,
                    "client_secret": settings.ibm_client_secret,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "test_access_token"
            assert data["token_type"] == "Bearer"
            assert data["expires_in"] == 3600
            assert data["id_token"] == "test_id_token"

    def test_callback_success(self, client, mock_ibm_oauth):  # noqa: ARG002
        """Test successful callback flow."""
        # Disable redirect following
        client.follow_redirects = False

        response = client.get("/api/auth/callback?code=test-code")

        # Check status and location header
        assert response.status_code == 307
        assert "callback?token=" in response.headers["location"]
        assert "error=" not in response.headers["location"]

        # Validate the token in the redirect URL
        token = response.headers["location"].split("token=")[1]
        assert token, "Token should be present in redirect URL"

        # Decode and verify token contents
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        assert decoded_token["sub"] == TEST_USER["sub"]
        assert decoded_token["email"] == TEST_USER["email"]
        assert decoded_token["name"] == TEST_USER["name"]

    def test_callback_missing_userinfo(self, client, mock_ibm_oauth):
        """Test callback with missing userinfo."""
        # Disable redirect following
        client.follow_redirects = False

        # Override mock to return token without userinfo
        mock_ibm_oauth.authorize_access_token.side_effect = AsyncMock(
            return_value={
                "access_token": "mock_access_token",
                "id_token": TEST_JWT,
                "token_type": "Bearer",
                "expires_in": 3600,
                # Deliberately omit userinfo
            }
        )

        response = client.get("/api/auth/callback?code=test-code")

        # Check status and error in location header
        assert response.status_code == 307
        assert "error=authentication_failed" in response.headers["location"]
        assert "signin" in response.headers["location"]


class TestUserEndpoints:
    def test_get_userinfo(self, client, auth_headers):
        """Test GET /api/auth/userinfo."""
        response = client.get("/api/auth/userinfo", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == TEST_USER["email"]
        assert data["role"] == TEST_USER["role"]

    def test_get_userinfo_no_auth(self, client):
        """Test GET /api/auth/userinfo without auth."""
        response = client.get("/api/auth/userinfo")
        assert response.status_code == 401

    def test_session_status(self, client, auth_headers):
        """Test GET /api/auth/session."""
        response = client.get("/api/auth/session", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user"]["email"] == TEST_USER["email"]

    def test_session_status_no_auth(self, client):
        """Test GET /api/auth/session without auth."""
        response = client.get("/api/auth/session")
        assert response.status_code == 200  # Should still return 200
        data = response.json()
        assert data["authenticated"] is False

    def test_logout(self, client, auth_headers):
        """Test POST /api/auth/logout."""
        response = client.post("/api/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"
