"""Tests for AuthRouter with comprehensive coverage including error cases."""

import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import jwt
from uuid import uuid4

from main import app
from core.config import settings
from rag_solution.models.user import User
from rag_solution.services.user_service import UserService

@pytest.fixture
def test_user(db_session):
    """Create a test user in the database."""
    user = User(
        ibm_id="test-ibm-id",
        email="test@example.com",
        name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_token(test_user):
    """Generate a valid JWT token for testing."""
    token_payload = {
        "sub": test_user.ibm_id,
        "email": test_user.email,
        "name": test_user.name,
        "uuid": str(test_user.id)
    }
    return jwt.encode(token_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def mock_oidc_auth(monkeypatch):
    """Mock the OIDC authorization endpoint."""
    async def mock_authorize_access_token(*args, **kwargs):
        return {
            "userinfo": {
                "sub": "test-ibm-id",
                "email": "test@example.com",
                "name": "Test User"
            },
            "id_token": "test-id-token",
            "expires_at": int((datetime.now() + timedelta(hours=1)).timestamp())
        }

    monkeypatch.setattr(
        "auth.oidc.oauth.ibm.authorize_access_token",
        mock_authorize_access_token
    )

class TestOIDCConfig:
    def test_get_oidc_config_success(self, client):
        """Test successful OIDC configuration retrieval."""
        response = client.get("/api/auth/oidc-config")
        assert response.status_code == 200
        assert response.json()["client_id"] == settings.ibm_client_id

class TestTokenExchange:
    def test_token_exchange_success(self, client, mock_oidc_auth):
        """Test successful token exchange."""
        response = client.post("/api/auth/token", data={
            "grant_type": "authorization_code",
            "code": "test-code",
            "redirect_uri": f"{settings.frontend_url}/api/auth/callback"
        })
        assert response.status_code == 200

class TestCallback:
    def test_callback_success(self, client, mock_oidc_auth):
        """Test successful authentication callback."""
        response = client.get("/api/auth/callback")
        assert response.status_code == 307
        assert settings.frontend_callback in response.headers["location"]

    def test_callback_missing_userinfo(self, client, monkeypatch):
        """Test callback with missing user info."""
        async def mock_authorize_access_token(*args, **kwargs):
            return {"id_token": "test-id-token"}

        monkeypatch.setattr(
            "auth.oidc.oauth.ibm.authorize_access_token",
            mock_authorize_access_token
        )

        response = client.get("/api/auth/callback")
        assert response.status_code == 307
        assert "error=authentication_failed" in response.headers["location"]

class TestUserInfo:
    def test_get_userinfo_success(self, client, test_user, test_token):
        """Test successful user info retrieval."""
        response = client.get(
            "/api/auth/userinfo",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        assert response.json()["email"] == test_user.email

    def test_get_userinfo_invalid_token(self, client):
        """Test user info retrieval with invalid token."""
        response = client.get(
            "/api/auth/userinfo",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

class TestSession:
    def test_session_status_authenticated(self, client, test_user, test_token):
        """Test session status for authenticated user."""
        response = client.get(
            "/api/auth/session",
            headers={"Authorization": f"Bearer {test_token}"}
        )
        assert response.status_code == 200
        assert response.json()["authenticated"] is True

    def test_session_status_no_auth(self, client):
        """Test session status with no authentication."""
        response = client.get("/api/auth/session")
        assert response.status_code == 200
        assert response.json()["authenticated"] is False
