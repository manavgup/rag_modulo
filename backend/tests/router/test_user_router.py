import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from unittest.mock import patch
from backend.rag_solution.router.user_router import (
    create_user, get_user, update_user,
    delete_user, list_users, get_current_user_id
)
from main import app

client = TestClient(app)

UUID_EXAMPLE = uuid4()

@pytest.fixture
def user_data():
    return {
        "user_id": UUID_EXAMPLE,
        "user_name": "Mock User",
        "email": "mockuser@example.com"
        # Add other necessary fields
    }

@pytest.fixture
def headers():
    return {
        "Authorization": "Bearer mock_access_token",
    }

# Add your mocked settings and services here

# Example test cases

def test_create_user(user_data, headers):
    with patch('backend.rag_solution.services.user_service.UserService') as MockService:
        mock_service = MockService.return_value
        mock_service.create_user.return_value = user_data

        response = client.post("/users", json=user_data, headers=headers)

        assert response.status_code == 200
        
        mock_service.create_user.assert_called_once_with(
            user_data
        )

def test_get_user(user_data, headers):
    with patch('backend.rag_solution.services.user_service.UserService') as MockService:
        mock_service = MockService.return_value
        mock_service.get_user.return_value = user_data

        response = client.get(f"/users/{user_data['user_id']}", headers=headers)

        assert response.status_code == 200
        
        mock_service.get_user.assert_called_once_with(
            user_data["user_id"]
        )

def test_update_user(user_data, headers):
    with patch('backend.rag_solution.services.user_service.UserService') as MockService:
        mock_service = MockService.return_value
        mock_service.update_user.return_value = user_data

        response = client.put(f"/users/{user_data['user_id']}", json=user_data, headers=headers)

        assert response.status_code == 200
        
        mock_service.update_user.assert_called_once_with(
            user_data["user_id"], user_data
        )

def test_delete_user(user_data, headers):
    with patch('backend.rag_solution.services.user_service.UserService') as MockService:
        mock_service = MockService.return_value
        mock_service.delete_user.return_value = True

        response = client.delete(f"/users/{user_data['user_id']}", headers=headers)

        assert response.status_code == 200
        
        mock_service.delete_user.assert_called_once_with(
            user_data["user_id"]
        )

def test_list_users(headers):
    with patch('backend.rag_solution.services.user_service.UserService') as MockService:
        mock_service = MockService.return_value
        mock_service.list_users.return_value = []

        response = client.get("/users", headers=headers)

        assert response.status_code == 200
        
        mock_service.list_users.assert_called_once()