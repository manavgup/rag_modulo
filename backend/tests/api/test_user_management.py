# test_user_management.py

from uuid import uuid4

import pytest

from .base_test import BaseTestRouter


class TestUserManagement(BaseTestRouter):
    """Test user-related endpoints including teams."""

    @pytest.fixture
    def test_user_data(self):
        """Sample user data for testing."""
        return {
            "ibm_id": f"test_user_{uuid4()}",
            "email": f"test_{uuid4()}@example.com",
            "name": "Test User",
            "role": "user",
        }

    @pytest.fixture
    def test_team_data(self):
        """Sample team data for testing."""
        return {"name": f"Test Team {uuid4()}", "description": "A team for testing purposes"}

    # User Management Tests
    @pytest.mark.asyncio
    async def test_create_user(self, test_user_data):
        """Test POST /api/users"""
        response = self.post("/api/users", json=test_user_data)
        self.assert_success(response)
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["ibm_id"] == test_user_data["ibm_id"]
        assert "id" in data

        # Cleanup
        self.delete(f"/api/users/{data['id']}")

    @pytest.mark.asyncio
    async def test_get_user(self, base_user):
        """Test GET /api/users/{user_id}"""
        response = self.get(f"/api/users/{base_user.id}")
        self.assert_success(response)
        data = response.json()
        assert data["id"] == str(base_user.id)
        assert data["email"] == base_user.email

    # Team Management Tests
    @pytest.mark.asyncio
    async def test_create_team(self, test_team_data):
        """Test POST /api/teams"""
        response = self.post("/api/teams", json=test_team_data)
        self.assert_success(response)
        data = response.json()
        assert data["name"] == test_team_data["name"]
        assert "id" in data

        # Cleanup
        self.delete(f"/api/teams/{data['id']}")

    @pytest.mark.asyncio
    async def test_add_user_to_team(self, base_user, base_team):
        """Test adding user to team."""
        response = self.post(f"/api/teams/{base_team.id}/users", json={"user_id": str(base_user.id)})
        self.assert_success(response)
        assert response.json()["status"] == "success"

    @pytest.mark.asyncio
    async def test_update_team_member_role(self, base_team, base_user_team):
        """Test updating team member role."""
        update_data = {"role": "admin"}
        response = self.put(f"/api/teams/{base_team.id}/users/{base_user_team.user_id}", json=update_data)
        self.assert_success(response)
        assert response.json()["role"] == "admin"

    # Collection Tests
    @pytest.mark.asyncio
    async def test_get_user_collections(self, base_user, base_collection):
        """Test GET /api/users/{user_id}/collections"""
        response = self.get(f"/api/users/{base_user.id}/collections")
        self.assert_success(response)
        data = response.json()
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_upload_file_to_collection(self, base_user, base_collection):
        """Test file upload."""
        files = {"file": ("test.txt", b"Test content", "text/plain")}
        response = self.post(f"/api/users/{base_user.id}/collections/{base_collection.id}/files", files=files)
        self.assert_success(response)
        data = response.json()
        assert data["filename"] == "test.txt"
        assert "id" in data

    # Authorization Tests
    @pytest.mark.asyncio
    async def test_unauthorized_access(self):
        """Test accessing endpoints without authentication."""
        test_id = uuid4()
        endpoints = [
            ("get", f"/api/users/{test_id}"),
            ("post", "/api/users"),
            ("get", f"/api/teams/{test_id}"),
            ("post", "/api/teams"),
        ]

        for method, endpoint in endpoints:
            response = getattr(self, method)(endpoint, authenticated=False)
            self.assert_unauthorized(response)

    @pytest.mark.asyncio
    async def test_access_other_user(self, base_user):
        """Test accessing other user's data."""
        other_user_id = uuid4()
        response = self.get(f"/api/users/{other_user_id}")
        self.assert_forbidden(response)

    # Validation Tests
    @pytest.mark.asyncio
    async def test_invalid_input(self, test_user_data, test_team_data):
        """Test input validation."""
        # Invalid email
        test_user_data["email"] = "invalid-email"
        response = self.post("/api/users", json=test_user_data)
        assert response.status_code == 422

        # Invalid team name
        test_team_data["name"] = ""
        response = self.post("/api/teams", json=test_team_data)
        assert response.status_code == 422
