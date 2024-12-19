import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from unittest.mock import patch

from main import app

client = TestClient(app)

UUID_EXAMPLE = uuid4()

@pytest.fixture
def user_data():
    return {
        "user_id": UUID_EXAMPLE,
        "user_name": "Mock User",
        "email": "mockuser@example.com",
        "team_id": UUID_EXAMPLE,
        "collection_id": UUID_EXAMPLE
    }

@pytest.fixture
def headers():
    return {
        "Authorization": "Bearer mock_access_token",
    }

# Add your mocked settings and services here

# Example test cases

def test_create_user(user_data, headers):
    with patch('rag_solution.services.user_service.UserService') as MockService:
        mock_service = MockService.return_value
        mock_service.create_user.return_value = user_data

        response = client.post("/users", json=user_data, headers=headers)

        assert response.status_code == 200
        
        mock_service.create_user.assert_called_once_with(
            user_data
        )

def test_get_user(user_data, headers):
    with patch('rag_solution.services.user_service.UserService') as MockService:
        mock_service = MockService.return_value
        mock_service.get_user.return_value = user_data

        response = client.get(f"/users/{user_data['user_id']}", headers=headers)

        assert response.status_code == 200
        
        mock_service.get_user.assert_called_once_with(
            user_data["user_id"]
        )

def test_update_user(user_data, headers):
    with patch('rag_solution.services.user_service.UserService') as MockService:
        mock_service = MockService.return_value
        mock_service.update_user.return_value = user_data

        response = client.put(f"/users/{user_data['user_id']}", json=user_data, headers=headers)

        assert response.status_code == 200
        
        mock_service.update_user.assert_called_once_with(
            user_data["user_id"], user_data
        )

def test_delete_user(user_data, headers):
    with patch('rag_solution.services.user_service.UserService') as MockService:
        mock_service = MockService.return_value
        mock_service.delete_user.return_value = True

        response = client.delete(f"/users/{user_data['user_id']}", headers=headers)

        assert response.status_code == 200
        
        mock_service.delete_user.assert_called_once_with(
            user_data["user_id"]
        )

def test_list_users(headers):
    with patch('rag_solution.services.user_service.UserService') as MockService:
        mock_service = MockService.return_value
        mock_service.list_users.return_value = []

        response = client.get("/users", headers=headers)

        assert response.status_code == 200
        
        mock_service.list_users.assert_called_once()

def test_add_user_to_team(user_team_data):
    with patch('rag_solution.services.user_team_service.UserTeamService') as MockService:
        mock_service = MockService.return_value
        mock_service.add_user_to_team.return_value = None

        response = client.post(f"/api/users/{user_team_data["user_id"]}/teams/{user_team_data["team_id"]}", json=user_team_data)

        assert response.status_code == 200
        
        mock_service.add_user_to_team.assert_called_once_with(
            user_team_data["user_id"], user_team_data["team_id"]
        )

def test_remove_user_from_team(user_team_data):
    with patch('rag_solution.services.user_team_service.UserTeamService') as MockService:
        mock_service = MockService.return_value
        mock_service.remove_user_from_team.return_value = None

        response = client.delete(f"/api/users/{user_team_data['user_id']}/teams/{user_team_data['team_id']}")

        assert response.status_code == 200
        
        mock_service.remove_user_from_team.assert_called_once_with(
            user_team_data["user_id"], user_team_data["team_id"]
        )

def test_get_user_teams(user_team_data):
    with patch('rag_solution.services.user_team_service.UserTeamService') as MockService:
        mock_service = MockService.return_value
        mock_service.get_user_teams.return_value = []

        response = client.get(f"/api/users/{user_team_data['user_id']}/teams")

        assert response.status_code == 200
        
        mock_service.get_user_teams.assert_called_once_with(
            user_team_data["user_id"]
        )

def test_add_user_to_collection(user_team_data):
    with patch('rag_solution.services.user_collection_service.UserCollectionService') as MockService:
        mock_service = MockService.return_value
        mock_service.add_user_to_collection.return_value = None

        response = client.post(f"/api/users/{user_team_data["user_id"]}/collections/{user_team_data["collection_id"]}")

        assert response.status_code == 200
        
        mock_service.add_user_to_collection.assert_called_once_with(
            user_team_data["user_id"], user_team_data["collection_id"]
        )

def test_remove_user_from_collection(user_team_data):
    with patch('rag_solution.services.user_collection_service.UserCollectionService') as MockService:
        mock_service = MockService.return_value
        mock_service.remove_user_from_collection.return_value = None

        response = client.delete(f"/api/users/{user_team_data['user_id']}/collections/{user_team_data['collection_id']}")

        assert response.status_code == 200
        
        mock_service.remove_user_from_collection.assert_called_once_with(
            user_team_data["user_id"], user_team_data["collection_id"]
        )

def test_get_user_collections(user_team_data):
    with patch('rag_solution.services.user_collection_interaction_service.UserCollectionInteractionService') as MockService:
        mock_service = MockService.return_value
        mock_service.get_user_collections_with_files.return_value = []

        response = client.get(f"/api/users/{user_team_data['user_id']}/collections")

        assert response.status_code == 200
        
        mock_service.get_user_collections_with_files.assert_called_once_with(
            user_team_data["user_id"]
        )