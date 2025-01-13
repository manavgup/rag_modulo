import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from rag_solution.router.health_router import router
from main import app

client = TestClient(app)

# Fixture for headers
@pytest.fixture
def headers():
    return {
        "Authorization": "Bearer mock_access_token",
    }

# Mocked services
@pytest.fixture
def mock_services():
    with patch("rag_solution.router.health_router.check_vectordb") as mock_vectordb, \
         patch("rag_solution.router.health_router.check_datastore") as mock_datastore, \
         patch("rag_solution.router.health_router.check_watsonx") as mock_watsonx, \
         patch("rag_solution.router.health_router.check_file_system") as mock_file_system:
        mock_vectordb.return_value = {"status": "healthy", "message": "Vector DB is connected and operational"}
        mock_datastore.return_value = {"status": "healthy", "message": "Relational DB is connected and operational"}
        mock_watsonx.return_value = {"status": "healthy", "message": "WatsonX is connected and operational"}
        mock_file_system.return_value = {"status": "healthy", "message": "File system is accessible and writable"}
        yield {
            "vectordb": mock_vectordb,
            "datastore": mock_datastore,
            "watsonx": mock_watsonx,
            "file_system": mock_file_system
        }

# Test cases

def test_health_check(headers, mock_services):
    response = client.get("/api/health", headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "components": {
            "vectordb": {"status": "healthy", "message": "Vector DB is connected and operational"},
            "datastore": {"status": "healthy", "message": "Relational DB is connected and operational"},
            "watsonx": {"status": "healthy", "message": "WatsonX is connected and operational"},
            "file_system": {"status": "healthy", "message": "File system is accessible and writable"}
        }
    }
    for mock in mock_services.values():
        mock.assert_called_once()

def test_health_check_failure(headers, mock_services):
    mock_services["vectordb"].side_effect = Exception("Vector DB connection failed")
    response = client.get("/api/health", headers=headers)
    assert response.status_code == 503
    assert "Vector DB health check failed" in response.json()["detail"]

# Component-specific tests
def test_check_vectordb(headers, mock_services):
    with patch("rag_solution.router.health_router.check_vectordb", return_value={"status": "healthy", "message": "Vector DB is connected and operational"}):
        response = client.get("/api/health", headers=headers)
        assert response.status_code == 200
        assert response.json()["components"]["vectordb"]["status"] == "healthy"

def test_check_datastore(headers, mock_services):
    with patch("rag_solution.router.health_router.check_datastore", return_value={"status": "healthy", "message": "Relational DB is connected and operational"}):
        response = client.get("/api/health", headers=headers)
        assert response.status_code == 200
        assert response.json()["components"]["datastore"]["status"] == "healthy"

def test_check_watsonx(headers, mock_services):
    with patch("rag_solution.router.health_router.check_watsonx", return_value={"status": "healthy", "message": "WatsonX is connected and operational"}):
        response = client.get("/api/health", headers=headers)
        assert response.status_code == 200
        assert response.json()["components"]["watsonx"]["status"] == "healthy"

def test_check_file_system(headers, mock_services):
    with patch("rag_solution.router.health_router.check_file_system", return_value={"status": "healthy", "message": "File system is accessible and writable"}):
        response = client.get("/api/health", headers=headers)
        assert response.status_code == 200
        assert response.json()["components"]["file_system"]["status"] == "healthy"
