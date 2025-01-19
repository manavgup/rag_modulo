import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from rag_solution.router.health_router import router
from main import app

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

def test_health_check(test_client, auth_headers, mock_services):
    response = test_client.get("/api/health", headers=auth_headers)
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

def test_health_check_failure(test_client, auth_headers, mock_services):
    mock_services["vectordb"].side_effect = Exception("Vector DB connection failed")
    response = test_client.get("/api/health", headers=auth_headers)
    assert response.status_code == 503
    assert "Vector DB health check failed" in response.json()["detail"]

# Component-specific tests
def test_check_vectordb(test_client, auth_headers, mock_services):
    with patch("rag_solution.router.health_router.check_vectordb", return_value={"status": "healthy", "message": "Vector DB is connected and operational"}):
        response = test_client.get("/api/health", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["components"]["vectordb"]["status"] == "healthy"

def test_check_datastore(test_client, auth_headers, mock_services):
    with patch("rag_solution.router.health_router.check_datastore", return_value={"status": "healthy", "message": "Relational DB is connected and operational"}):
        response = test_client.get("/api/health", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["components"]["datastore"]["status"] == "healthy"

def test_check_watsonx(test_client, auth_headers, mock_services):
    with patch("rag_solution.router.health_router.check_watsonx", return_value={"status": "healthy", "message": "WatsonX is connected and operational"}):
        response = test_client.get("/api/health", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["components"]["watsonx"]["status"] == "healthy"

def test_check_file_system(test_client, auth_headers, mock_services):
    with patch("rag_solution.router.health_router.check_file_system", return_value={"status": "healthy", "message": "File system is accessible and writable"}):
        response = test_client.get("/api/health", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["components"]["file_system"]["status"] == "healthy"

def test_multiple_component_failures(test_client, auth_headers, mock_services):
    """Test scenario where multiple components fail."""
    mock_services["vectordb"].side_effect = Exception("Vector DB connection failed")
    mock_services["datastore"].side_effect = Exception("Database connection failed")
    
    response = test_client.get("/api/health", headers=auth_headers)
    assert response.status_code == 503
    assert "Vector DB health check failed" in response.json()["detail"]

def test_watsonx_not_configured(test_client, auth_headers, mock_services):
    """Test scenario where WatsonX is not configured."""
    mock_services["watsonx"].return_value = {
        "status": "skipped",
        "message": "WatsonX not configured"
    }
    
    response = test_client.get("/api/health", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["components"]["watsonx"]["status"] == "skipped"

def test_file_system_permission_error(test_client, auth_headers, mock_services):
    """Test scenario with file system permission issues."""
    mock_services["file_system"].side_effect = Exception("Permission denied")
    
    response = test_client.get("/api/health", headers=auth_headers)
    assert response.status_code == 503
    assert "File system health check failed" in response.json()["detail"]
    assert "Permission denied" in response.json()["detail"]

def test_database_connection_error(test_client, auth_headers, mock_services):
    """Test scenario with database connection issues."""
    mock_services["datastore"].side_effect = Exception("Connection refused")
    
    response = test_client.get("/api/health", headers=auth_headers)
    assert response.status_code == 503
    assert "Relational DB health check failed" in response.json()["detail"]
    assert "Connection refused" in response.json()["detail"]

def test_vectordb_specific_error(test_client, auth_headers, mock_services):
    """Test scenario with specific vector DB error."""
    mock_services["vectordb"].side_effect = Exception("Invalid vector dimension")
    
    response = test_client.get("/api/health", headers=auth_headers)
    assert response.status_code == 503
    assert "Vector DB health check failed" in response.json()["detail"]
    assert "Invalid vector dimension" in response.json()["detail"]

def test_partial_system_health(test_client, auth_headers, mock_services):
    """Test scenario where some components are healthy and others are not."""
    mock_services["vectordb"].return_value = {"status": "healthy", "message": "Vector DB is connected"}
    mock_services["datastore"].return_value = {"status": "healthy", "message": "Database is connected"}
    mock_services["watsonx"].return_value = {"status": "skipped", "message": "WatsonX not configured"}
    mock_services["file_system"].side_effect = Exception("Permission denied")
    
    response = test_client.get("/api/health", headers=auth_headers)
    assert response.status_code == 503
    data = response.json()
    assert "File system health check failed" in data["detail"]
    assert "Permission denied" in data["detail"]

def test_health_check_with_empty_response(test_client, auth_headers, mock_services):
    """Test handling of empty or null responses from components."""
    mock_services["vectordb"].return_value = None
    
    response = test_client.get("/api/health", headers=auth_headers)
    assert response.status_code == 503
    assert "health check failed" in response.json()["detail"].lower()
