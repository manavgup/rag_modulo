# test_search_collection.py

from uuid import uuid4

import pytest

from rag_solution.schemas.collection_schema import CollectionStatus

from .base_test import BaseTestRouter


class TestSearchAndCollections(BaseTestRouter):
    """Test search and collection-related endpoints."""

    @pytest.fixture
    def test_collection_data(self, base_user):
        """Sample collection data for testing."""
        return {
            "name": f"Test Collection {uuid4()}",
            "description": "A collection for testing",
            "is_private": False,
            "users": [str(base_user.id)],
            "status": CollectionStatus.COMPLETED,
        }

    @pytest.fixture
    def test_search_input(self, base_collection):
        """Sample search input data."""
        return {"question": "What is this document about?", "collection_id": str(base_collection.id)}

    @pytest.fixture
    def test_search_context(self):
        """Sample search context data."""
        return {"user_role": "student", "language": "en", "detail_level": "high"}

    # Collection Management Tests
    @pytest.mark.asyncio
    async def test_create_collection(self, test_collection_data):
        """Test POST /api/collections"""
        response = self.post("/api/collections", json=test_collection_data)
        self.assert_success(response)
        data = response.json()
        assert data["name"] == test_collection_data["name"]
        assert "id" in data

        # Cleanup
        self.delete(f"/api/collections/{data['id']}")

    @pytest.mark.asyncio
    async def test_create_collection_with_files(self, base_user):
        """Test POST /api/collections/with-files"""
        files = [("files", ("test.txt", b"Test document content", "text/plain"))]
        form_data = {
            "collection_name": f"Test Collection {uuid4()}",
            "is_private": "false",
            "user_id": str(base_user.id),
        }

        response = self.post("/api/collections/with-files", data=form_data, files=files)
        self.assert_success(response)
        data = response.json()
        assert "files" in data
        assert len(data["files"]) == 1
        assert data["files"][0]["filename"] == "test.txt"

    @pytest.mark.asyncio
    async def test_get_collection(self, base_collection):
        """Test GET /api/collections/{collection_id}"""
        response = self.get(f"/api/collections/{base_collection.id}")
        self.assert_success(response)
        data = response.json()
        assert data["id"] == str(base_collection.id)
        assert data["name"] == base_collection.name

    # Collection Files Tests
    @pytest.mark.asyncio
    def test_upload_files(self, base_user, base_collection):
        """Test POST /api/collections/with-files instead."""
        files = [("files", ("test.txt", b"Test document content", "text/plain"))]
        form_data = {"collection_name": base_collection.name, "is_private": False, "user_id": str(base_user.id)}
        response = self.post("/api/collections/with-files", data=form_data, files=files)
        self.assert_success(response)

    @pytest.mark.asyncio
    async def test_get_files(self, base_collection, base_file):
        """Test GET /api/collections/{collection_id}/files"""
        response = self.get(f"/api/collections/{base_collection.id}/files")
        self.assert_success(response)
        files = response.json()
        assert len(files) >= 1
        assert files[0]["id"] == str(base_file.id)

    # Search Tests
    @pytest.mark.asyncio
    async def test_search_success(self, test_search_input):
        """Test POST /api/search - successful search."""
        response = self.post("/api/search", json={"search_input": test_search_input})
        self.assert_success(response)
        data = response.json()
        assert "answer" in data
        assert "documents" in data
        assert len(data["documents"]) > 0

    @pytest.mark.asyncio
    async def test_search_with_context(self, test_search_input, test_search_context):
        """Test search with additional context."""
        response = self.post("/api/search", json=test_search_input, params=test_search_context)
        self.assert_success(response)
        data = response.json()
        assert data["rewritten_query"] != test_search_input["question"]
        assert len(data["documents"]) > 0

    @pytest.mark.asyncio
    async def test_search_collection_not_found(self, test_search_input):
        """Test search with non-existent collection."""
        test_search_input["collection_id"] = str(uuid4())
        response = self.post("/api/search", json={"search_input": test_search_input})
        assert response.status_code == 422

    # Error Cases
    @pytest.mark.asyncio
    async def test_search_validation(self, test_search_input):
        """Test search validation."""
        # Empty query
        test_search_input["question"] = "   "
        response = self.post("/api/search", json={"search_input": test_search_input})
        assert response.status_code == 422

    # Authorization Tests
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, test_search_input):
        """Test endpoints without authentication."""
        test_id = uuid4()
        endpoints = [
            ("get", f"/api/collections/{test_id}"),
            ("post", "/api/collections"),
            ("post", "/api/search"),
        ]

        for method, endpoint in endpoints:
            response = getattr(self, method)(endpoint, authenticated=False)
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_access_unauthorized_collection(self, base_collection):
        """Test accessing collection without permission."""
        headers = {**self.auth_headers, "X-User-UUID": str(uuid4())}
        response = self.get(f"/api/collections/{base_collection.id}", headers=headers)
        self.assert_forbidden(response)
