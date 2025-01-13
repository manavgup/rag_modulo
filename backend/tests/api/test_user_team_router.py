import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from unittest.mock import patch
from rag_solution.router.user_team_router import (
    add_user_to_team, remove_user_from_team,
    get_user_teams, get_team_users
)
from main import app

client = TestClient(app)

UUID_EXAMPLE = uuid4()

@pytest.fixture
def user_team_data():
    return {
        "user_id": str(UUID_EXAMPLE),
        "team_id": str(UUID_EXAMPLE)
    }

@pytest.fixture
def headers():
    return {
        "Authorization": "Bearer mock_access_token",
    }

@pytest.fixture(autouse=True)
def authenticate_user():
    with client as c:
        c.headers.update(headers())
        with c.websocket_connect("/docs") as websocket:
            session_cookie = c.cookies.get("session")
            if session_cookie:
                c.cookie_jar.set("session", session_cookie)

        yield

# Example test cases

def test_add_user_to_team(user_team_data):
    with patch('rag_solution.services.user_team_service.UserTeamService') as MockService:
        mock_service = MockService.return_value
        mock_service.add_user_to_team.return_value = None

        response = client.post("/api/user_teams/add", json=user_team_data)

        assert response.status_code == 200
        
        mock_service.add_user_to_team.assert_called_once_with(
            user_team_data["user_id"], user_team_data["team_id"]
        )

def test_remove_user_from_team(user_team_data):
    with patch('rag_solution.services.user_team_service.UserTeamService') as MockService:
        mock_service = MockService.return_value
        mock_service.remove_user_from_team.return_value = None

        response = client.delete(f"/api/user_teams/remove/{user_team_data['user_id']}/{user_team_data['team_id']}")

        assert response.status_code == 200
        
        mock_service.remove_user_from_team.assert_called_once_with(
            user_team_data["user_id"], user_team_data["team_id"]
        )

def test_get_user_teams(user_team_data):
    with patch('rag_solution.services.user_team_service.UserTeamService') as MockService:
        mock_service = MockService.return_value
        mock_service.get_user_teams.return_value = []

        response = client.get(f"/api/user_teams/user/{user_team_data['user_id']}")

        assert response.status_code == 200
        
        mock_service.get_user_teams.assert_called_once_with(
            user_team_data["user_id"]
        )

def test_get_team_users(user_team_data):
    with patch('rag_solution.services.user_team_service.UserTeamService') as MockService:
        mock_service = MockService.return_value
        mock_service.get_team_users.return_value = []

        response = client.get(f"/api/user_teams/team/{user_team_data['team_id']}")

        assert response.status_code == 200
        
        mock_service.get_team_users.assert_called_once_with(
            user_team_data["team_id"]
        )
