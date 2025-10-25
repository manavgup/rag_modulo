"""E2E test fixtures for system administration tests."""

import pytest


@pytest.fixture(scope="session")
def base_url() -> str:
    """Provide base URL for E2E tests."""
    # E2E tests run in Docker container and need to connect to backend service
    # The CONTAINER_ENV=false just indicates we're not running in the main backend container
    return "http://backend:8000/api"


@pytest.fixture(scope="session")
def auth_headers() -> dict[str, str]:
    """Provide authentication headers for E2E tests."""
    # For E2E tests, we might need to authenticate
    # For now, return basic headers
    return {"Content-Type": "application/json", "Accept": "application/json"}
