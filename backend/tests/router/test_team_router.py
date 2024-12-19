import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from unittest.mock import patch

from main import app

client = TestClient(app)

UUID_EXAMPLE = uuid4()

@pytest.fixture
def team_data():
    return {
        "team_id": UUID_EXAMPLE,
        "team_name": "Mock Team",
        # Add other necessary fields
    }

@pytest.fixture
def headers():
    return {
        "Authorization": "Bearer mock_access_token",
    }

# Add your mocked settings and services here

# Example test cases

def test_create_team(team_data, headers):
    with patch('rag_solution.services.team_service.TeamService') as MockService:
        mock_service = MockService.return_value
        mock_service.create_team.return_value = team_data

        response = client.post("/teams", json=team_data, headers=headers)

        assert response.status_code == 200
        
        mock_service.create_team.assert_called_once_with(
            team_data
        )

def test_get_team(team_data, headers):
    with patch('rag_solution.services.team_service.TeamService') as MockService:
        mock_service = MockService.return_value
        mock_service.get_team.return_value = team_data

        response = client.get(f"/teams/{team_data['team_id']}", headers=headers)

        assert response.status_code == 200
        
        mock_service.get_team.assert_called_once_with(
            team_data["team_id"]
        )

def test_update_team(team_data, headers):
    with patch('rag_solution.services.team_service.TeamService') as MockService:
        mock_service = MockService.return_value
        mock_service.update_team.return_value = team_data

        response = client.put(f"/api/teams/{team_data['team_id']}", json=team_data, headers=headers)

        assert response.status_code == 200
        
        mock_service.update_team.assert_called_once_with(
            team_data["team_id"], team_data
        )

def test_delete_team(team_data, headers):
    with patch('rag_solution.services.team_service.TeamService') as MockService:
        mock_service = MockService.return_value
        mock_service.delete_team.return_value = True

        response = client.delete(f"/api/teams/{team_data['team_id']}", headers=headers)

        assert response.status_code == 200
        
        mock_service.delete_team.assert_called_once_with(
            team_data["team_id"]
        )

def test_list_teams(headers):
    with patch('rag_solution.services.team_service.TeamService') as MockService:
        mock_service = MockService.return_value
        mock_service.list_teams.return_value = []

        response = client.get("/api/teams", headers=headers)

        assert response.status_code == 200
        
        mock_service.list_teams.assert_called_once()

def test_get_team_users(user_team_data):
    with patch('rag_solution.services.user_team_service.UserTeamService') as MockService:
        mock_service = MockService.return_value
        mock_service.get_team_users.return_value = []

        response = client.get(f"/api/teams/{user_team_data['team_id']}")

        assert response.status_code == 200
        
        mock_service.get_team_users.assert_called_once_with(
            user_team_data["team_id"]
        )