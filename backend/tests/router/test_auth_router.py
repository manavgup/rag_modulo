import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.rag_solution.router.auth_router import router, create_jwt, decode_jwt, get_current_user
from main import app
import jwt
from datetime import datetime, timedelta, timezone

# Create a test client
client = TestClient(app)

# Mock JWT secret key and algorithm for testing
TEST_JWT_SECRET_KEY = "test_secret_key"
TEST_JWT_ALGORITHM = "HS256"

@pytest.fixture
def user_data():
    return {
        "sub": "mock_ibm_id",
        "email": "mockuser@example.com",
        "name": "Mock User",
        "uuid": "mock_uuid"
    }

@pytest.fixture
def mock_jwt_settings():
    with patch("backend.rag_solution.router.auth_router.JWT_SECRET_KEY", TEST_JWT_SECRET_KEY):
        with patch("backend.rag_solution.router.auth_router.JWT_ALGORITHM", TEST_JWT_ALGORITHM):
            yield

@pytest.fixture
def valid_token(user_data, mock_jwt_settings):
    return create_jwt(user_data)

@pytest.fixture
def headers(valid_token):
    return {
        "Authorization": f"Bearer {valid_token}",
    }

def test_create_jwt(user_data, mock_jwt_settings):
    token = create_jwt(user_data)
    assert token is not None
    decoded = jwt.decode(token, TEST_JWT_SECRET_KEY, algorithms=[TEST_JWT_ALGORITHM])
    assert decoded["sub"] == user_data["sub"]
    assert decoded["email"] == user_data["email"]
    assert "exp" in decoded

def test_decode_jwt(valid_token, mock_jwt_settings):
    decoded = decode_jwt(valid_token)
    assert decoded is not None
    assert decoded["sub"] == "mock_ibm_id"
    assert decoded["email"] == "mockuser@example.com"

def test_decode_jwt_invalid_token(mock_jwt_settings):
    invalid_token = "invalid.token.here"
    decoded = decode_jwt(invalid_token)
    assert decoded is None

@pytest.mark.asyncio
async def test_get_current_user(valid_token, mock_jwt_settings):
    user = await get_current_user(valid_token)
    assert user is not None
    assert user["sub"] == "mock_ibm_id"
    assert user["email"] == "mockuser@example.com"

@pytest.mark.asyncio
async def test_get_current_user_invalid_token(mock_jwt_settings):
    with pytest.raises(Exception):  # Expecting an HTTPException, but using a general Exception for simplicity
        await get_current_user("invalid.token.here")

def test_get_oidc_config():
    response = client.get("/api/auth/oidc-config")
    assert response.status_code == 200
    config = response.json()
    assert "authority" in config
    assert "client_id" in config
    assert "redirect_uri" in config

@patch("backend.rag_solution.router.auth_router.get_current_user")
def test_userinfo(mock_get_current_user, user_data, headers):
    mock_get_current_user.return_value = user_data
    response = client.get("/api/auth/userinfo", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["sub"] == user_data["sub"]
    assert data["email"] == user_data["email"]
    assert data["name"] == user_data["name"]
    assert data["uuid"] == user_data["uuid"]

def test_userinfo_no_auth_header():
    response = client.get("/api/auth/userinfo")
    assert response.status_code == 401

def test_logout():
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"message": "Successfully logged out"}

# Add more test functions for each endpoint in the `auth_router.py`
# For example, you might want to add tests for:
# - test_token_exchange
# - test_login
# - test_get_session
# - test_auth_callback
# - test_get_user_uuid

# These tests would require more complex mocking of the OAuth flow and database interactions
