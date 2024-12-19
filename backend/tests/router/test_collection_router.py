import pytest
from uuid import uuid4
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

UUID_EXAMPLE = uuid4()

@pytest.fixture
def input_data():
    return {
        "collection_id": UUID_EXAMPLE
    }

@pytest.fixture
def headers():
    return {
        "Authorization": "Bearer mock_access_token",
    }

def test_get_collection_users(input_data):
    with patch('rag_solution.services.user_collection_service.UserCollectionService') as MockService:
        mock_service = MockService.return_value
        mock_service.get_collection_users.return_value = []

        response = client.get(f"/api/collections/{input_data['collection_id']}/users")

        assert response.status_code == 200
        
        mock_service.get_collection_users.assert_called_once_with(
            input_data["collection_id"]
        )

def test_remove_all_users_from_collection(input_data):
    with patch('rag_solution.services.user_collection_service.UserCollectionService') as MockService:
        mock_service = MockService.return_value
        mock_service.remove_all_users_from_collection.return_value = []

        response = client.delete(f"/api/collections/{input_data['collection_id']}/users")

        assert response.status_code == 200
        
        mock_service.remove_all_users_from_collection.assert_called_once_with(
            input_data["collection_id"]
        )