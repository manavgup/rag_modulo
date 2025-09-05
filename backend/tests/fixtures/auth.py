"""Authentication fixtures for pytest."""

from collections.abc import Callable, Generator
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app
from rag_solution.schemas.user_schema import UserOutput


@pytest.fixture
def mock_auth_token() -> str:
    """Create a mock JWT token."""
    return "mock_token_for_testing"


@pytest.fixture
def admin_auth_headers(mock_auth_token: str) -> dict[str, str]:
    """Create admin authentication headers."""
    return {"Authorization": f"Bearer {mock_auth_token}", "X-User-Role": "admin"}


@pytest.fixture
def auth_headers_for_role(mock_auth_token: str) -> Callable[[str], dict[str, str]]:
    """Create headers for a specific role."""

    def _make_headers(role: str = "user") -> dict[str, str]:
        return {"Authorization": f"Bearer {mock_auth_token}", "X-User-Role": role}

    return _make_headers


@pytest.fixture
def auth_headers(mock_auth_token: str, base_user: UserOutput) -> dict[str, str]:
    """Create regular user authentication headers."""
    return {"Authorization": f"Bearer {mock_auth_token}", "X-User-UUID": str(base_user.id), "X-User-Role": "user"}


@pytest.fixture
def test_client(base_user: UserOutput) -> Generator[TestClient, None, None]:
    """Create a test client with mocked authentication."""

    def mock_verify_token(token: str) -> dict[str, Any]:
        return {
            "sub": base_user.ibm_id,
            "email": base_user.email,
            "name": base_user.name,
            "uuid": str(base_user.id),
            "role": "user",
        }

    with patch("core.authentication_middleware.verify_jwt_token", side_effect=mock_verify_token):
        client = TestClient(app)
        yield client
