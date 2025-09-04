from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from core.config import settings


# Mock the OAuth client
@pytest.fixture(autouse=True)
def mock_oauth_client():
    with patch("rag_solution.router.auth_router.oauth") as mock_oauth:
        mock_oauth.ibm = MagicMock()
        yield mock_oauth


@pytest.fixture
@pytest.mark.integration
def test_client():
    from main import app

    return TestClient(app)


def test_login_redirect(test_client):
    response = test_client.get("/api/auth/login")
    assert response.status_code == 302
    assert response.headers["location"].startswith(settings.oidc_authorization_endpoint)


def test_callback_success(test_client, mock_oauth_client):
    # Mock the token exchange and user info retrieval
    mock_oauth_client.ibm.authorize_access_token.return_value = {
        "access_token": "mock_access_token",
        "id_token": "mock_id_token",
    }
    mock_oauth_client.ibm.parse_id_token.return_value = {
        "sub": "mock_ibm_id",
        "email": "test@example.com",
        "name": "Test User",
    }

    response = test_client.get("/api/auth/callback?code=mock_code&state=mock_state")
    assert response.status_code == 302
    assert response.headers["location"].startswith(settings.frontend_url)

    # Check if JWT is returned in the response
    assert "access_token" in response.json()
    jwt_token = response.json()["access_token"]
    assert jwt_token.startswith("eyJ")  # JWT typically starts with this


def test_get_user_info(test_client):
    # Create a mock JWT token
    mock_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtb2NrX2libV9pZCIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsIm5hbWUiOiJUZXN0IFVzZXIiLCJ1dWlkIjoibW9ja191dWlkIn0.mock_signature"

    response = test_client.get("/api/auth/userinfo", headers={"Authorization": f"Bearer {mock_jwt}"})
    assert response.status_code == 200
    user_info = response.json()
    assert user_info["sub"] == "mock_ibm_id"
    assert user_info["email"] == "test@example.com"
    assert user_info["name"] == "Test User"
    assert user_info["uuid"] == "mock_uuid"


def test_logout(test_client):
    response = test_client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"message": "Successfully logged out"}


def test_get_user_uuid(test_client):
    response = test_client.get("/api/auth/user-id/mock_ibm_id")
    assert response.status_code == 200
    assert response.json() == "mock_uuid"


def test_protected_route(test_client):
    # Test a protected route without a valid JWT
    response = test_client.get("/api/protected")
    assert response.status_code == 401

    # Test a protected route with a valid JWT
    mock_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtb2NrX2libV9pZCIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsIm5hbWUiOiJUZXN0IFVzZXIiLCJ1dWlkIjoibW9ja191dWlkIn0.mock_signature"
    response = test_client.get("/api/protected", headers={"Authorization": f"Bearer {mock_jwt}"})
    assert response.status_code == 200
    assert response.json() == {"message": "Access granted to protected resource"}
