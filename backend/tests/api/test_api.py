# test_collection.py

from uuid import uuid4

from .base_test import BaseTestRouter


@pytest.mark.api
class TestCollectionEndpoints(BaseTestRouter):
    """Test collection-related endpoints."""

    def test_create_collection(self):
        """Test POST /api/collections"""
        # Create test user first
        user_data = {"ibm_id": f"test_user_{uuid4()}", "email": f"test_{uuid4()}@example.com", "name": "Test User"}
        user_response = self.post("/api/users", json=user_data)
        self.assert_success(user_response)
        user = user_response.json()

        # Create collection
        collection_data = {
            "name": f"Test Collection {uuid4()}",
            "description": "A collection for testing",
            "is_private": True,
            "users": [user["id"]],
        }

        response = self.post("/api/collections", json=collection_data)
        self.assert_success(response)

        data = response.json()
        assert data["name"] == collection_data["name"]
        assert data["is_private"] == collection_data["is_private"]
        assert user["id"] in data["user_ids"]
        assert "id" in data

        # Clean up
        self.delete(f"/api/collections/{data['id']}")
        self.delete(f"/api/users/{user['id']}")

    def test_get_collection(self):
        """Test GET /api/collections/{collection_id}"""
        # Create test user
        user_data = {"ibm_id": f"test_user_{uuid4()}", "email": f"test_{uuid4()}@example.com", "name": "Test User"}
        user_response = self.post("/api/users", json=user_data)
        self.assert_success(user_response)
        user = user_response.json()

        # Create collection
        collection_data = {
            "name": f"Test Collection {uuid4()}",
            "description": "A collection for testing",
            "is_private": True,
            "users": [user["id"]],
        }
        create_response = self.post("/api/collections", json=collection_data)
        self.assert_success(create_response)
        collection = create_response.json()

        # Test getting the collection
        response = self.get(f"/api/collections/{collection['id']}")
        self.assert_success(response)
        data = response.json()
        assert data["id"] == collection["id"]
        assert data["name"] == collection["name"]

        # Cleanup
        self.delete(f"/api/collections/{collection['id']}")
        self.delete(f"/api/users/{user['id']}")

    def test_upload_file_to_collection(self):
        """Test file upload to collection."""
        # Create test user
        user_data = {"ibm_id": f"test_user_{uuid4()}", "email": f"test_{uuid4()}@example.com", "name": "Test User"}
        user_response = self.post("/api/users", json=user_data)
        self.assert_success(user_response)
        user = user_response.json()

        # Create collection
        collection_data = {
            "name": f"Test Collection {uuid4()}",
            "description": "A collection for testing",
            "is_private": True,
            "users": [user["id"]],
        }
        create_response = self.post("/api/collections", json=collection_data)
        self.assert_success(create_response)
        collection = create_response.json()

        # Upload file
        files = {"file": ("test.txt", b"Test content", "text/plain")}
        response = self.post(f"/api/collections/{collection['id']}/files", files=files)
        self.assert_success(response)
        data = response.json()
        assert "filename" in data
        assert data["filename"] == "test.txt"

        # Cleanup
        self.delete(f"/api/collections/{collection['id']}")
        self.delete(f"/api/users/{user['id']}")

    def test_unauthorized_access(self):
        """Test accessing endpoints without authentication."""
        test_id = uuid4()
        endpoints = [
            ("get", f"/api/collections/{test_id}"),
            ("post", "/api/collections"),
            ("delete", f"/api/collections/{test_id}"),
        ]

        for method, endpoint in endpoints:
            response = getattr(self, method)(endpoint, authenticated=False)
            self.assert_unauthorized(response)
