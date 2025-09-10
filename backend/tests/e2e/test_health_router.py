# test_health_router.py

from collections.abc import Awaitable, Callable, Generator
from typing import Any
from unittest.mock import patch

import jwt
import pytest
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from core.config import get_settings
from main import app

# Test Data
TEST_USER = {
    "sub": "test-ibm-id",
    "email": "test@example.com",
    "name": "Test User",
    "uuid": "test-uuid",
    "role": "admin",
}

settings = get_settings()
TEST_JWT_TOKEN = jwt.encode(TEST_USER, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
# Ensure TEST_JWT is a string, not bytes
TEST_JWT = TEST_JWT_TOKEN.decode("utf-8") if isinstance(TEST_JWT_TOKEN, bytes) else TEST_JWT_TOKEN


@pytest.fixture
def async_client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Create authentication headers."""
    return {"Authorization": f"Bearer {TEST_JWT}", "X-User-UUID": TEST_USER["uuid"], "X-User-Role": TEST_USER["role"]}


@pytest.fixture
def mock_auth_middleware() -> Generator[None, Any, None]:
    """Mock authentication middleware."""

    async def mock_dispatch(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Handle authentication for all paths except health check
        if request.url.path != "/api/health":
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

            token = auth_header.split(" ")[1]
            if token in ["mock_token_for_testing", "test-id-token", "valid-test-token", TEST_JWT]:
                request.state.user = TEST_USER.copy()
                response = await call_next(request)
                return response

            return JSONResponse(status_code=401, content={"detail": "Invalid token"})

        # Always require auth for health check
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

        token = auth_header.split(" ")[1]
        if token in ["mock_token_for_testing", "test-id-token", "valid-test-token", TEST_JWT]:
            request.state.user = TEST_USER.copy()
            response = await call_next(request)
            return response

        return JSONResponse(status_code=401, content={"detail": "Invalid token"})

    with patch("core.authentication_middleware.AuthenticationMiddleware.dispatch", side_effect=mock_dispatch):
        yield


@pytest.fixture
def mock_health_checks() -> Generator[dict[str, Any], None, None]:
    """Mock all health check functions."""
    with (
        patch("rag_solution.router.health_router.check_vectordb") as mock_vectordb,
        patch("rag_solution.router.health_router.check_datastore") as mock_datastore,
        patch("rag_solution.router.health_router.check_watsonx") as mock_watsonx,
        patch("rag_solution.router.health_router.check_file_system") as mock_file_system,
    ):
        # Set default healthy responses
        mock_vectordb.return_value = {"status": "healthy", "message": "Vector DB is connected"}
        mock_datastore.return_value = {"status": "healthy", "message": "Relational DB is connected"}
        mock_watsonx.return_value = {"status": "healthy", "message": "WatsonX is connected"}
        mock_file_system.return_value = {"status": "healthy", "message": "File system is accessible"}

        yield {
            "vectordb": mock_vectordb,
            "datastore": mock_datastore,
            "watsonx": mock_watsonx,
            "file_system": mock_file_system,
        }


@pytest.mark.api
class TestHealthCheck:
    def test_health_check_success(
        self,
        async_client: TestClient,
        mock_health_checks: dict[str, Any],  # noqa: ARG002
        auth_headers: dict[str, str],
        mock_auth_middleware: Any,  # noqa: ARG002
    ) -> None:
        """Test GET /api/health when all components are healthy."""
        response = async_client.get("/api/health", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data

        components = data["components"]
        assert components["vectordb"]["status"] == "healthy"
        assert components["datastore"]["status"] == "healthy"
        assert components["watsonx"]["status"] == "healthy"
        assert components["file_system"]["status"] == "healthy"

    def test_vectordb_failure(
        self,
        async_client: TestClient,
        mock_health_checks: dict[str, Any],
        auth_headers: dict[str, str],
        mock_auth_middleware: Any,  # noqa: ARG002
    ) -> None:
        """Test health check when vector DB fails."""
        mock_health_checks["vectordb"].return_value = {"status": "unhealthy", "message": "Connection failed"}

        response = async_client.get("/api/health", headers=auth_headers)
        assert response.status_code == 503
        data = response.json()
        assert "vectordb" in data["detail"]
        assert "unhealthy" in data["detail"]

    def test_unauthorized_access(
        self,
        async_client: TestClient,
        mock_auth_middleware: Any,  # noqa: ARG002
    ) -> None:
        """Test health check endpoint without authentication."""
        response = async_client.get("/api/health")
        assert response.status_code == 401

    def test_invalid_token(
        self,
        async_client: TestClient,
        mock_auth_middleware: Any,  # noqa: ARG002
    ) -> None:
        """Test health check with invalid token."""
        response = async_client.get("/api/health", headers={"Authorization": "Bearer invalid-token"})
        assert response.status_code == 401

    def test_watsonx_not_configured(
        self,
        async_client: TestClient,
        mock_health_checks: dict[str, Any],
        auth_headers: dict[str, str],
        mock_auth_middleware: Any,  # noqa: ARG002
    ) -> None:
        """Test health check when WatsonX is not configured."""
        mock_health_checks["watsonx"].return_value = {"status": "skipped", "message": "WatsonX not configured"}

        response = async_client.get("/api/health", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["components"]["watsonx"]["status"] == "skipped"
