"""E2E tests for search workflow."""

import pytest
from fastapi.testclient import TestClient

from rag_solution.main import app


@pytest.mark.e2e
def test_end_to_end_search_flow():
    """Test complete end-to-end search workflow."""
    client = TestClient(app)
    
    # Test complete search workflow
    response = client.post("/search", json={
        "question": "What is the main topic?",
        "collection_id": "test-collection-id",
        "user_id": 1
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "documents" in data


@pytest.mark.e2e
def test_search_performance():
    """Test search performance."""
    client = TestClient(app)
    
    # Test search performance
    # Add specific performance tests here
    pass


@pytest.mark.e2e
def test_search_error_scenarios():
    """Test search error scenarios."""
    client = TestClient(app)
    
    # Test error scenarios
    response = client.post("/search", json={
        "question": "",
        "collection_id": "invalid-id",
        "user_id": 1
    })
    
    assert response.status_code == 400
