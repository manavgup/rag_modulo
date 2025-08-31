"""Tests for team router endpoints."""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from rag_solution.models.team import Team
from rag_solution.models.user import User
from rag_solution.models.user_team import UserTeam
from rag_solution.file_management.database import get_db

@pytest.fixture
def test_db(db: Session):
    """Get test database session."""
    return db

@pytest.fixture
def client(test_db: Session):
    """Create test client with database override."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()

@pytest.fixture
def test_user(test_db: Session):
    """Create a test user."""
    user = User(
        ibm_id="test-ibm-id",
        email="test@example.com",
        name="Test User"
    )
    test_db.add(user)
    test_db.commit()
    return user

@pytest.fixture
def test_team(test_db: Session):
    """Create a test team."""
    team = Team(
        name="Test Team",
        description="A team for testing"
    )
    test_db.add(team)
    test_db.commit()
    return team

@pytest.fixture
def test_user_team(test_db: Session, test_user: User, test_team: Team):
    """Create a test user-team association."""
    user_team = UserTeam(
        user_id=test_user.id,
        team_id=test_team.id,
        role="member"
    )
    test_db.add(user_team)
    test_db.commit()
    return user_team

class TestTeamManagement:
    def test_create_team_success(self, client: TestClient):
        """Test successful team creation."""
        team_input = {
            "name": "New Team",
            "description": "A new test team"
        }
        
        response = client.post("/api/teams", json=team_input)
        assert response.status_code == 201
        assert response.json()["name"] == "New Team"
        assert response.json()["description"] == "A new test team"

    def test_create_team_invalid_input(self, client: TestClient):
        """Test team creation with invalid input."""
        team_input = {
            # Missing required name field
            "description": "Invalid team"
        }
        
        response = client.post("/api/teams", json=team_input)
        assert response.status_code == 422

    def test_get_team_success(self, client: TestClient, test_team: Team):
        """Test successful team retrieval."""
        response = client.get(f"/api/teams/{test_team.id}")
        assert response.status_code == 200
        assert response.json()["name"] == test_team.name
        assert response.json()["description"] == test_team.description

    def test_get_team_not_found(self, client: TestClient):
        """Test team retrieval when not found."""
        response = client.get(f"/api/teams/{uuid4()}")
        assert response.status_code == 404
        assert "Team not found" in response.json()["detail"]

    def test_update_team_success(self, client: TestClient, test_team: Team):
        """Test successful team update."""
        update_data = {
            "name": "Updated Team",
            "description": "Updated description"
        }
        
        response = client.put(f"/api/teams/{test_team.id}", json=update_data)
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Team"
        assert response.json()["description"] == "Updated description"

    def test_update_team_not_found(self, client: TestClient):
        """Test team update when not found."""
        update_data = {
            "name": "Updated Team",
            "description": "Updated description"
        }
        
        response = client.put(f"/api/teams/{uuid4()}", json=update_data)
        assert response.status_code == 404
        assert "Team not found" in response.json()["detail"]

    def test_delete_team_success(self, client: TestClient, test_team: Team):
        """Test successful team deletion."""
        response = client.delete(f"/api/teams/{test_team.id}")
        assert response.status_code == 200
        assert response.json() is True

    def test_delete_team_not_found(self, client: TestClient):
        """Test team deletion when not found."""
        response = client.delete(f"/api/teams/{uuid4()}")
        assert response.status_code == 200
        assert response.json() is False

    def test_list_teams_success(
        self, client: TestClient, test_team: Team
    ):
        """Test successful teams listing."""
        response = client.get("/api/teams")
        assert response.status_code == 200
        teams = response.json()
        assert len(teams) > 0
        assert any(team["id"] == str(test_team.id) for team in teams)

    def test_list_teams_pagination(
        self, client: TestClient, test_team: Team
    ):
        """Test teams listing with pagination."""
        # Create additional teams
        team_input = {
            "name": "Another Team",
            "description": "Another test team"
        }
        client.post("/api/teams", json=team_input)
        
        # Test with limit
        response = client.get("/api/teams?limit=1")
        assert response.status_code == 200
        assert len(response.json()) == 1
        
        # Test with skip
        response = client.get("/api/teams?skip=1&limit=1")
        assert response.status_code == 200
        assert len(response.json()) == 1

class TestTeamUsers:
    def test_get_team_users_success(
        self, client: TestClient, test_team: Team, test_user_team: UserTeam
    ):
        """Test successful team users retrieval."""
        response = client.get(f"/api/teams/{test_team.id}/users")
        assert response.status_code == 200
        users = response.json()
        assert len(users) > 0
        assert users[0]["role"] == "member"

    def test_get_team_users_empty(
        self, client: TestClient, test_team: Team
    ):
        """Test team users retrieval when team has no users."""
        # Create a new team without users
        team_input = {
            "name": "Empty Team",
            "description": "Team with no users"
        }
        create_response = client.post("/api/teams", json=team_input)
        team_id = create_response.json()["id"]
        
        response = client.get(f"/api/teams/{team_id}/users")
        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_get_team_users_team_not_found(self, client: TestClient):
        """Test team users retrieval when team not found."""
        response = client.get(f"/api/teams/{uuid4()}/users")
        assert response.status_code == 200
        assert len(response.json()) == 0

if __name__ == "__main__":
    pytest.main([__file__])
