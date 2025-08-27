# test_health_router.py

import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
import jwt
from fastapi.responses import JSONResponse

from main import app
from core.config import settings

# Test Data
TEST_USER = {
    "sub": "test-ibm-id",
    "email": "test@example.com",
    "name": "Test User",
    "uuid": "test-uuid",
    "role": "admin"
}

TEST_JWT = jwt.encode(TEST_USER, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

@pytest_asyncio.fixture
async def async_client():
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture(autouse=True)
def mock_jwt_verification():
    """Mock JWT verification."""
    def mock_verify(token):
        if token == "mock_token_for_testing" or token == TEST_JWT:
            return TEST_USER
        raise jwt.InvalidTokenError("Invalid token")

    with patch("auth.oidc.verify_jwt_token", side_effect=mock_verify), \
         patch("core.authentication_middleware.verify_jwt_token", side_effect=mock_verify):
        yield

@pytest.fixture
def auth_headers():
    """Create authentication headers."""
    return {
        "Authorization": f"Bearer {TEST_JWT}",
        "X-User-UUID": TEST_USER["uuid"],
        "X-User-Role": TEST_USER["role"]
    }

@pytest.fixture
def mock_auth_middleware():
    """Mock authentication middleware."""
    async def mock_dispatch(request, call_next):
        # Handle authentication for all paths except health check
        if request.url.path != '/api/health':
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
                
            token = auth_header.split(' ')[1]
            if token in ["mock_token_for_testing", "test-id-token", "valid-test-token", TEST_JWT]:
                request.state.user = TEST_USER.copy()
                return await call_next(request)
            
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})
            
        # Always require auth for health check
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
            
        token = auth_header.split(' ')[1]
        if token in ["mock_token_for_testing", "test-id-token", "valid-test-token", TEST_JWT]:
            request.state.user = TEST_USER.copy()
            return await call_next(request)
        
        return JSONResponse(status_code=401, content={"detail": "Invalid token"})

    with patch('core.authentication_middleware.AuthenticationMiddleware.dispatch', 
              side_effect=mock_dispatch):
        yield

@pytest.fixture
def mock_health_checks():
    """Mock all health check functions."""
    with patch("rag_solution.router.health_router.check_vectordb") as mock_vectordb, \
         patch("rag_solution.router.health_router.check_datastore") as mock_datastore, \
         patch("rag_solution.router.health_router.check_watsonx") as mock_watsonx, \
         patch("rag_solution.router.health_router.check_file_system") as mock_file_system:
            
        # Set default healthy responses
        mock_vectordb.return_value = {
            "status": "healthy",
            "message": "Vector DB is connected"
        }
        mock_datastore.return_value = {
            "status": "healthy",
            "message": "Relational DB is connected"
        }
        mock_watsonx.return_value = {
            "status": "healthy",
            "message": "WatsonX is connected"
        }
        mock_file_system.return_value = {
            "status": "healthy",
            "message": "File system is accessible"
        }

        yield {
            "vectordb": mock_vectordb,
            "datastore": mock_datastore,
            "watsonx": mock_watsonx,
            "file_system": mock_file_system
        }

class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_success(self, async_client, mock_health_checks, auth_headers, mock_auth_middleware):
        """Test GET /api/health when all components are healthy."""
        response = await async_client.get("/api/health", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        
        components = data["components"]
        assert components["vectordb"]["status"] == "healthy"
        assert components["datastore"]["status"] == "healthy"
        assert components["watsonx"]["status"] == "healthy"
        assert components["file_system"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_vectordb_failure(self, async_client, mock_health_checks, auth_headers, mock_auth_middleware):
        """Test health check when vector DB fails."""
        mock_health_checks["vectordb"].return_value = {
            "status": "unhealthy",
            "message": "Connection failed"
        }
        
        response = await async_client.get("/api/health", headers=auth_headers)
        assert response.status_code == 503
        data = response.json()
        assert "vectordb" in data["detail"]
        assert "unhealthy" in data["detail"]

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, async_client, mock_auth_middleware):
        """Test health check endpoint without authentication."""
        response = await async_client.get("/api/health")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token(self, async_client, mock_auth_middleware):
        """Test health check with invalid token."""
        response = await async_client.get(
            "/api/health",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_watsonx_not_configured(self, async_client, mock_health_checks, auth_headers, mock_auth_middleware):
        """Test health check when WatsonX is not configured."""
        mock_health_checks["watsonx"].return_value = {
            "status": "skipped",
            "message": "WatsonX not configured"
        }
        
        response = await async_client.get("/api/health", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["components"]["watsonx"]["status"] == "skipped"