"""Authentication fixtures for tests."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="function")
def test_client() -> Generator[TestClient, None, None]:
    """Create a test client for API testing."""
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
def auth_headers() -> dict[str, str]:
    """Create authentication headers for tests."""
    return {"Authorization": "Bearer test-token", "X-User-UUID": "test-user-123", "X-User-Role": "user"}
