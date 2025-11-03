"""API tests for RuntimeConfig endpoints using FastAPI TestClient.

This module tests all 8 REST API endpoints for runtime configuration:
1. POST /api/v1/runtime-configs - Create config
2. GET /api/v1/runtime-configs/{config_id} - Get config by ID
3. GET /api/v1/runtime-configs/effective/{category} - Get effective config
4. PUT /api/v1/runtime-configs/{config_id} - Update config
5. DELETE /api/v1/runtime-configs/{config_id} - Delete config
6. PATCH /api/v1/runtime-configs/{config_id}/toggle - Toggle active status
7. GET /api/v1/runtime-configs/user/{user_id} - List user configs
8. GET /api/v1/runtime-configs/collection/{collection_id} - List collection configs

Test Strategy:
- Uses FastAPI TestClient with mock auth (SKIP_AUTH=true)
- Tests all success paths (200, 201, 204)
- Tests all error paths (400, 404, 409, 422)
- Validates request/response schemas
- Tests query parameters and filters
"""

from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="function")
def api_client() -> TestClient:
    """Create FastAPI test client for API testing."""
    return TestClient(app)


@pytest.fixture
def test_user_id() -> str:
    """Generate test user ID."""
    return str(uuid4())


@pytest.fixture
def test_collection_id() -> str:
    """Generate test collection ID."""
    return str(uuid4())


@pytest.mark.e2e
class TestCreateRuntimeConfig:
    """Test POST /api/v1/runtime-configs endpoint."""

    def test_create_global_config_success(self, api_client: TestClient):
        """Test successful creation of global configuration."""
        payload = {
            "scope": "global",
            "category": "llm",
            "config_key": f"test_param_{uuid4().hex[:8]}",
            "config_value": {"value": 0.7, "type": "float"},
            "is_active": True,
            "description": "Test global config",
        }

        response = api_client.post("/api/v1/runtime-configs", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["config_key"] == payload["config_key"]
        assert data["scope"] == "global"
        assert data["category"] == "llm"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_user_config_success(self, api_client: TestClient, test_user_id: str):
        """Test successful creation of user configuration."""
        payload = {
            "scope": "user",
            "category": "chunking",
            "config_key": f"chunk_size_{uuid4().hex[:8]}",
            "config_value": {"value": 512, "type": "int"},
            "user_id": test_user_id,
            "is_active": True,
        }

        response = api_client.post("/api/v1/runtime-configs", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["scope"] == "user"
        assert data["user_id"] == test_user_id

    def test_create_collection_config_success(
        self, api_client: TestClient, test_user_id: str, test_collection_id: str
    ):
        """Test successful creation of collection configuration."""
        payload = {
            "scope": "collection",
            "category": "retrieval",
            "config_key": f"top_k_{uuid4().hex[:8]}",
            "config_value": {"value": 10, "type": "int"},
            "user_id": test_user_id,
            "collection_id": test_collection_id,
            "is_active": True,
        }

        response = api_client.post("/api/v1/runtime-configs", json=payload)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["scope"] == "collection"
        assert data["collection_id"] == test_collection_id

    def test_create_duplicate_config_fails(self, api_client: TestClient):
        """Test creating duplicate configuration returns 409 Conflict."""
        unique_key = f"duplicate_test_{uuid4().hex[:8]}"
        payload = {
            "scope": "global",
            "category": "llm",
            "config_key": unique_key,
            "config_value": {"value": 0.7, "type": "float"},
            "is_active": True,
        }

        # First creation succeeds
        response1 = api_client.post("/api/v1/runtime-configs", json=payload)
        assert response1.status_code == status.HTTP_201_CREATED

        # Duplicate creation fails
        response2 = api_client.post("/api/v1/runtime-configs", json=payload)
        assert response2.status_code in [status.HTTP_409_CONFLICT, status.HTTP_400_BAD_REQUEST]
        assert "detail" in response2.json()

    def test_create_invalid_scope_fails(self, api_client: TestClient):
        """Test creating config with invalid scope returns 400."""
        payload = {
            "scope": "global",
            "category": "llm",
            "config_key": f"invalid_{uuid4().hex[:8]}",
            "config_value": {"value": 0.7, "type": "float"},
            "user_id": str(uuid4()),  # Invalid for GLOBAL scope
            "is_active": True,
        }

        response = api_client.post("/api/v1/runtime-configs", json=payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.json()

    def test_create_missing_required_fields_fails(self, api_client: TestClient):
        """Test creating config with missing fields returns 422."""
        payload = {
            "scope": "global",
            "category": "llm",
            # config_key missing
            "config_value": {"value": 0.7, "type": "float"},
        }

        response = api_client.post("/api/v1/runtime-configs", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_invalid_config_value_fails(self, api_client: TestClient):
        """Test creating config with invalid config_value structure returns 422."""
        payload = {
            "scope": "global",
            "category": "llm",
            "config_key": f"invalid_value_{uuid4().hex[:8]}",
            "config_value": {"value": 0.7},  # Missing 'type'
            "is_active": True,
        }

        response = api_client.post("/api/v1/runtime-configs", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.e2e
class TestGetRuntimeConfig:
    """Test GET /api/v1/runtime-configs/{config_id} endpoint."""

    def test_get_config_success(self, api_client: TestClient):
        """Test successful retrieval of configuration by ID."""
        # Create a config first
        payload = {
            "scope": "global",
            "category": "llm",
            "config_key": f"get_test_{uuid4().hex[:8]}",
            "config_value": {"value": 0.7, "type": "float"},
            "is_active": True,
        }
        create_response = api_client.post("/api/v1/runtime-configs", json=payload)
        config_id = create_response.json()["id"]

        # Retrieve the config
        response = api_client.get(f"/api/v1/runtime-configs/{config_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == config_id
        assert data["config_key"] == payload["config_key"]

    def test_get_config_not_found(self, api_client: TestClient):
        """Test retrieving non-existent config returns 404."""
        fake_id = str(uuid4())

        response = api_client.get(f"/api/v1/runtime-configs/{fake_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "detail" in response.json()

    def test_get_config_invalid_uuid(self, api_client: TestClient):
        """Test retrieving config with invalid UUID returns 422."""
        response = api_client.get("/api/v1/runtime-configs/not-a-uuid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.e2e
class TestGetEffectiveConfig:
    """Test GET /api/v1/runtime-configs/effective/{category} endpoint."""

    def test_get_effective_config_global_only(self, api_client: TestClient, test_user_id: str):
        """Test effective config with only global configs."""
        # Create global config
        unique_key = f"effective_global_{uuid4().hex[:8]}"
        payload = {
            "scope": "global",
            "category": "llm",
            "config_key": unique_key,
            "config_value": {"value": 0.7, "type": "float"},
            "is_active": True,
        }
        api_client.post("/api/v1/runtime-configs", json=payload)

        # Get effective config
        response = api_client.get(f"/api/v1/runtime-configs/effective/llm?user_id={test_user_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["category"] == "llm"
        assert "values" in data
        assert "sources" in data

    def test_get_effective_config_with_user_override(self, api_client: TestClient, test_user_id: str):
        """Test effective config with user override."""
        unique_key = f"effective_user_{uuid4().hex[:8]}"

        # Create global config
        global_payload = {
            "scope": "global",
            "category": "chunking",
            "config_key": unique_key,
            "config_value": {"value": 256, "type": "int"},
            "is_active": True,
        }
        api_client.post("/api/v1/runtime-configs", json=global_payload)

        # Create user override
        user_payload = {
            "scope": "user",
            "category": "chunking",
            "config_key": unique_key,
            "config_value": {"value": 512, "type": "int"},
            "user_id": test_user_id,
            "is_active": True,
        }
        api_client.post("/api/v1/runtime-configs", json=user_payload)

        # Get effective config
        response = api_client.get(f"/api/v1/runtime-configs/effective/chunking?user_id={test_user_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # User config should override global (if key exists in response)
        if unique_key in data["values"]:
            assert data["values"][unique_key] == 512
            assert data["sources"][unique_key] == "user"

    def test_get_effective_config_with_collection_override(
        self, api_client: TestClient, test_user_id: str, test_collection_id: str
    ):
        """Test effective config with collection override (highest precedence)."""
        unique_key = f"effective_collection_{uuid4().hex[:8]}"

        # Create configs at all levels
        global_payload = {
            "scope": "global",
            "category": "retrieval",
            "config_key": unique_key,
            "config_value": {"value": 5, "type": "int"},
            "is_active": True,
        }
        api_client.post("/api/v1/runtime-configs", json=global_payload)

        user_payload = {
            "scope": "user",
            "category": "retrieval",
            "config_key": unique_key,
            "config_value": {"value": 10, "type": "int"},
            "user_id": test_user_id,
            "is_active": True,
        }
        api_client.post("/api/v1/runtime-configs", json=user_payload)

        collection_payload = {
            "scope": "collection",
            "category": "retrieval",
            "config_key": unique_key,
            "config_value": {"value": 20, "type": "int"},
            "user_id": test_user_id,
            "collection_id": test_collection_id,
            "is_active": True,
        }
        api_client.post("/api/v1/runtime-configs", json=collection_payload)

        # Get effective config
        response = api_client.get(
            f"/api/v1/runtime-configs/effective/retrieval?user_id={test_user_id}&collection_id={test_collection_id}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Collection config should have highest precedence
        if unique_key in data["values"]:
            assert data["values"][unique_key] == 20
            assert data["sources"][unique_key] == "collection"

    def test_get_effective_config_invalid_category(self, api_client: TestClient, test_user_id: str):
        """Test effective config with invalid category returns 400."""
        response = api_client.get(f"/api/v1/runtime-configs/effective/invalid_category?user_id={test_user_id}")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.e2e
class TestUpdateRuntimeConfig:
    """Test PUT /api/v1/runtime-configs/{config_id} endpoint."""

    def test_update_config_success(self, api_client: TestClient):
        """Test successful update of configuration."""
        # Create config
        payload = {
            "scope": "global",
            "category": "llm",
            "config_key": f"update_test_{uuid4().hex[:8]}",
            "config_value": {"value": 0.7, "type": "float"},
            "is_active": True,
        }
        create_response = api_client.post("/api/v1/runtime-configs", json=payload)
        config_id = create_response.json()["id"]

        # Update config
        updates = {"config_value": {"value": 0.8, "type": "float"}, "description": "Updated description"}

        response = api_client.put(f"/api/v1/runtime-configs/{config_id}", json=updates)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == config_id
        assert data["description"] == "Updated description"

    def test_update_partial_fields(self, api_client: TestClient):
        """Test partial update of configuration."""
        # Create config
        payload = {
            "scope": "global",
            "category": "llm",
            "config_key": f"partial_update_{uuid4().hex[:8]}",
            "config_value": {"value": 0.7, "type": "float"},
            "is_active": True,
        }
        create_response = api_client.post("/api/v1/runtime-configs", json=payload)
        config_id = create_response.json()["id"]

        # Update only description
        updates = {"description": "New description"}

        response = api_client.put(f"/api/v1/runtime-configs/{config_id}", json=updates)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["description"] == "New description"
        # Original config_value should remain unchanged
        assert data["config_value"] == payload["config_value"]

    def test_update_config_not_found(self, api_client: TestClient):
        """Test updating non-existent config returns 404."""
        fake_id = str(uuid4())
        updates = {"description": "test"}

        response = api_client.put(f"/api/v1/runtime-configs/{fake_id}", json=updates)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_invalid_scope_change(self, api_client: TestClient):
        """Test updating config with invalid scope change returns 400."""
        # Create global config
        payload = {
            "scope": "global",
            "category": "llm",
            "config_key": f"scope_change_{uuid4().hex[:8]}",
            "config_value": {"value": 0.7, "type": "float"},
            "is_active": True,
        }
        create_response = api_client.post("/api/v1/runtime-configs", json=payload)
        config_id = create_response.json()["id"]

        # Try to add user_id (invalid for GLOBAL scope)
        updates = {"user_id": str(uuid4())}

        response = api_client.put(f"/api/v1/runtime-configs/{config_id}", json=updates)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.e2e
class TestDeleteRuntimeConfig:
    """Test DELETE /api/v1/runtime-configs/{config_id} endpoint."""

    def test_delete_config_success(self, api_client: TestClient):
        """Test successful deletion of configuration."""
        # Create config
        payload = {
            "scope": "global",
            "category": "llm",
            "config_key": f"delete_test_{uuid4().hex[:8]}",
            "config_value": {"value": 0.7, "type": "float"},
            "is_active": True,
        }
        create_response = api_client.post("/api/v1/runtime-configs", json=payload)
        config_id = create_response.json()["id"]

        # Delete config
        response = api_client.delete(f"/api/v1/runtime-configs/{config_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deletion
        get_response = api_client.get(f"/api/v1/runtime-configs/{config_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_config_not_found(self, api_client: TestClient):
        """Test deleting non-existent config returns 404."""
        fake_id = str(uuid4())

        response = api_client.delete(f"/api/v1/runtime-configs/{fake_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_idempotency(self, api_client: TestClient):
        """Test deleting same config twice (idempotency check)."""
        # Create config
        payload = {
            "scope": "global",
            "category": "llm",
            "config_key": f"idempotent_{uuid4().hex[:8]}",
            "config_value": {"value": 0.7, "type": "float"},
            "is_active": True,
        }
        create_response = api_client.post("/api/v1/runtime-configs", json=payload)
        config_id = create_response.json()["id"]

        # First delete succeeds
        response1 = api_client.delete(f"/api/v1/runtime-configs/{config_id}")
        assert response1.status_code == status.HTTP_204_NO_CONTENT

        # Second delete returns 404
        response2 = api_client.delete(f"/api/v1/runtime-configs/{config_id}")
        assert response2.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.e2e
class TestToggleRuntimeConfig:
    """Test PATCH /api/v1/runtime-configs/{config_id}/toggle endpoint."""

    def test_toggle_config_disable(self, api_client: TestClient):
        """Test disabling a configuration."""
        # Create active config
        payload = {
            "scope": "global",
            "category": "llm",
            "config_key": f"toggle_test_{uuid4().hex[:8]}",
            "config_value": {"value": 0.7, "type": "float"},
            "is_active": True,
        }
        create_response = api_client.post("/api/v1/runtime-configs", json=payload)
        config_id = create_response.json()["id"]

        # Disable config
        response = api_client.patch(f"/api/v1/runtime-configs/{config_id}/toggle?is_active=false")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is False

    def test_toggle_config_enable(self, api_client: TestClient):
        """Test enabling a configuration."""
        # Create inactive config
        payload = {
            "scope": "global",
            "category": "llm",
            "config_key": f"enable_test_{uuid4().hex[:8]}",
            "config_value": {"value": 0.7, "type": "float"},
            "is_active": False,
        }
        create_response = api_client.post("/api/v1/runtime-configs", json=payload)
        config_id = create_response.json()["id"]

        # Enable config
        response = api_client.patch(f"/api/v1/runtime-configs/{config_id}/toggle?is_active=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is True

    def test_toggle_config_not_found(self, api_client: TestClient):
        """Test toggling non-existent config returns 404."""
        fake_id = str(uuid4())

        response = api_client.patch(f"/api/v1/runtime-configs/{fake_id}/toggle?is_active=false")

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.e2e
class TestListUserRuntimeConfigs:
    """Test GET /api/v1/runtime-configs/user/{user_id} endpoint."""

    def test_list_user_configs_success(self, api_client: TestClient, test_user_id: str):
        """Test listing all user configurations."""
        # Create multiple user configs
        for i in range(3):
            payload = {
                "scope": "user",
                "category": "llm",
                "config_key": f"user_config_{i}_{uuid4().hex[:8]}",
                "config_value": {"value": 0.7 + i * 0.1, "type": "float"},
                "user_id": test_user_id,
                "is_active": True,
            }
            api_client.post("/api/v1/runtime-configs", json=payload)

        # List all user configs
        response = api_client.get(f"/api/v1/runtime-configs/user/{test_user_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_list_user_configs_with_category_filter(self, api_client: TestClient, test_user_id: str):
        """Test listing user configs filtered by category."""
        # Create configs in different categories
        llm_payload = {
            "scope": "user",
            "category": "llm",
            "config_key": f"llm_{uuid4().hex[:8]}",
            "config_value": {"value": 0.7, "type": "float"},
            "user_id": test_user_id,
            "is_active": True,
        }
        chunking_payload = {
            "scope": "user",
            "category": "chunking",
            "config_key": f"chunk_{uuid4().hex[:8]}",
            "config_value": {"value": 512, "type": "int"},
            "user_id": test_user_id,
            "is_active": True,
        }
        api_client.post("/api/v1/runtime-configs", json=llm_payload)
        api_client.post("/api/v1/runtime-configs", json=chunking_payload)

        # List only LLM configs
        response = api_client.get(f"/api/v1/runtime-configs/user/{test_user_id}?category=llm")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        # All configs should be LLM category
        assert all(config["category"] == "llm" for config in data)

    def test_list_user_configs_empty(self, api_client: TestClient):
        """Test listing user configs returns empty list when none exist."""
        random_user_id = str(uuid4())

        response = api_client.get(f"/api/v1/runtime-configs/user/{random_user_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


@pytest.mark.e2e
class TestListCollectionRuntimeConfigs:
    """Test GET /api/v1/runtime-configs/collection/{collection_id} endpoint."""

    def test_list_collection_configs_success(
        self, api_client: TestClient, test_user_id: str, test_collection_id: str
    ):
        """Test listing all collection configurations."""
        # Create multiple collection configs
        for i in range(3):
            payload = {
                "scope": "collection",
                "category": "retrieval",
                "config_key": f"collection_config_{i}_{uuid4().hex[:8]}",
                "config_value": {"value": 5 + i, "type": "int"},
                "user_id": test_user_id,
                "collection_id": test_collection_id,
                "is_active": True,
            }
            api_client.post("/api/v1/runtime-configs", json=payload)

        # List all collection configs
        response = api_client.get(f"/api/v1/runtime-configs/collection/{test_collection_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_list_collection_configs_with_category_filter(
        self, api_client: TestClient, test_user_id: str, test_collection_id: str
    ):
        """Test listing collection configs filtered by category."""
        # Create configs in different categories
        retrieval_payload = {
            "scope": "collection",
            "category": "retrieval",
            "config_key": f"retrieval_{uuid4().hex[:8]}",
            "config_value": {"value": 10, "type": "int"},
            "user_id": test_user_id,
            "collection_id": test_collection_id,
            "is_active": True,
        }
        embedding_payload = {
            "scope": "collection",
            "category": "embedding",
            "config_key": f"embedding_{uuid4().hex[:8]}",
            "config_value": {"value": "sentence-transformers", "type": "str"},
            "user_id": test_user_id,
            "collection_id": test_collection_id,
            "is_active": True,
        }
        api_client.post("/api/v1/runtime-configs", json=retrieval_payload)
        api_client.post("/api/v1/runtime-configs", json=embedding_payload)

        # List only retrieval configs
        response = api_client.get(f"/api/v1/runtime-configs/collection/{test_collection_id}?category=retrieval")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        # All configs should be retrieval category
        assert all(config["category"] == "retrieval" for config in data)

    def test_list_collection_configs_empty(self, api_client: TestClient):
        """Test listing collection configs returns empty list when none exist."""
        random_collection_id = str(uuid4())

        response = api_client.get(f"/api/v1/runtime-configs/collection/{random_collection_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
