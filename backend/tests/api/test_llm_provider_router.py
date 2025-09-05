"""Tests for LLM Provider Router with comprehensive coverage."""

from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from rag_solution.schemas.llm_model_schema import ModelType
from rag_solution.services.llm_provider_service import LLMProviderService


@pytest.fixture
def db_session() -> Mock:
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def service(db_session: Any) -> Mock:
    """Create a mock LLMProviderService instance."""
    return Mock(spec=LLMProviderService)


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_provider() -> dict[str, Any]:
    """Create a sample provider data."""
    return {
        "id": uuid4(),
        "name": "watsonx",
        "base_url": "https://api.example.com",
        "api_key": "test-api-key",
        "project_id": "test-project",
        "is_active": True,
    }


@pytest.fixture
def sample_model() -> dict[str, Any]:
    """Create a sample model data."""
    return {
        "id": uuid4(),
        "provider_id": uuid4(),
        "name": "test-model",
        "model_type": ModelType.GENERATION,
        "parameters": {"temperature": 0.7},
        "is_active": True,
    }


@pytest.mark.api
class TestProviderRoutes:
    def test_create_provider_success(self, client: TestClient, service: Mock, sample_provider: dict[str, Any]) -> None:
        """Test successful provider creation."""
        service.create_provider.return_value = sample_provider

        provider_input = {
            "name": sample_provider["name"],
            "base_url": sample_provider["base_url"],
            "api_key": sample_provider["api_key"],
            "project_id": sample_provider["project_id"],
        }

        response = client.post("/api/llm-providers/", json=provider_input)
        assert response.status_code == 200
        assert response.json()["name"] == sample_provider["name"]
        assert response.json()["base_url"] == sample_provider["base_url"]

    def test_get_all_providers_success(self, client: TestClient, service: Mock, sample_provider: dict[str, Any]) -> None:
        """Test successful retrieval of all providers."""
        service.get_all_providers.return_value = [sample_provider]

        response = client.get("/api/llm-providers/")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == sample_provider["name"]

    def test_get_all_providers_with_filter(self, client: TestClient, service: Mock, sample_provider: dict[str, Any]) -> None:
        """Test retrieving providers with active filter."""
        service.get_all_providers.return_value = [sample_provider]

        response = client.get("/api/llm-providers/?is_active=true")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["is_active"] is True

    def test_get_provider_success(self, client: TestClient, service: Mock, sample_provider: dict[str, Any]) -> None:
        """Test successful provider retrieval."""
        service.get_provider_by_id.return_value = sample_provider

        response = client.get(f"/api/llm-providers/{sample_provider['id']}")
        assert response.status_code == 200
        assert response.json()["name"] == sample_provider["name"]

    def test_get_provider_not_found(self, client: TestClient, service: Mock) -> None:
        """Test provider retrieval when not found."""
        service.get_provider_by_id.return_value = None

        response = client.get(f"/api/llm-providers/{uuid4()}")
        assert response.status_code == 404
        assert "Provider not found" in response.json()["detail"]

    def test_update_provider_success(self, client: TestClient, service: Mock, sample_provider: dict[str, Any]) -> None:
        """Test successful provider update."""
        updated_provider = dict(sample_provider)
        updated_provider["name"] = "updated-name"
        service.update_provider.return_value = updated_provider

        updates = {"name": "updated-name"}
        response = client.put(f"/api/llm-providers/{sample_provider['id']}", json=updates)
        assert response.status_code == 200
        assert response.json()["name"] == "updated-name"

    def test_update_provider_not_found(self, client: TestClient, service: Mock) -> None:
        """Test provider update when not found."""
        service.update_provider.return_value = None

        response = client.put(f"/api/llm-providers/{uuid4()}", json={"name": "new-name"})
        assert response.status_code == 404
        assert "Provider not found" in response.json()["detail"]

    def test_delete_provider_success(self, client: TestClient, service: Mock, sample_provider: dict[str, Any]) -> None:
        """Test successful provider deletion."""
        service.delete_provider.return_value = True

        response = client.delete(f"/api/llm-providers/{sample_provider['id']}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    def test_delete_provider_not_found(self, client: TestClient, service: Mock) -> None:
        """Test provider deletion when not found."""
        service.delete_provider.return_value = False

        response = client.delete(f"/api/llm-providers/{uuid4()}")
        assert response.status_code == 404
        assert "Provider not found" in response.json()["detail"]


class TestProviderModelRoutes:
    def test_create_model_success(self, client: TestClient, service: Mock, sample_model: dict[str, Any]) -> None:
        """Test successful model creation."""
        service.create_provider_model.return_value = sample_model

        model_input = {
            "provider_id": str(sample_model["provider_id"]),
            "name": sample_model["name"],
            "model_type": sample_model["model_type"],
            "parameters": sample_model["parameters"],
        }

        response = client.post("/api/llm-providers/models/", json=model_input)
        assert response.status_code == 200
        assert response.json()["name"] == sample_model["name"]
        assert response.json()["model_type"] == sample_model["model_type"]

    def test_get_models_by_provider_success(self, client: TestClient, service: Mock, sample_model: dict[str, Any]) -> None:
        """Test successful retrieval of models by provider."""
        service.get_models_by_provider.return_value = [sample_model]

        response = client.get(f"/api/llm-providers/models/provider/{sample_model['provider_id']}")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["name"] == sample_model["name"]

    def test_get_models_by_type_success(self, client: TestClient, service: Mock, sample_model: dict[str, Any]) -> None:
        """Test successful retrieval of models by type."""
        service.get_models_by_type.return_value = [sample_model]

        response = client.get("/api/llm-providers/models/type/generation")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["model_type"] == "generation"

    def test_get_model_by_id_success(self, client: TestClient, service: Mock, sample_model: dict[str, Any]) -> None:
        """Test successful model retrieval by ID."""
        service.get_model_by_id.return_value = sample_model

        response = client.get(f"/api/llm-providers/models/{sample_model['id']}")
        assert response.status_code == 200
        assert response.json()["name"] == sample_model["name"]

    def test_get_model_by_id_not_found(self, client: TestClient, service: Mock) -> None:
        """Test model retrieval when not found."""
        service.get_model_by_id.return_value = None

        response = client.get(f"/api/llm-providers/models/{uuid4()}")
        assert response.status_code == 404
        assert "Model not found" in response.json()["detail"]

    def test_update_model_success(self, client: TestClient, service: Mock, sample_model: dict[str, Any]) -> None:
        """Test successful model update."""
        updated_model = dict(sample_model)
        updated_model["name"] = "updated-model"
        service.update_model.return_value = updated_model

        updates = {"name": "updated-model"}
        response = client.put(f"/api/llm-providers/models/{sample_model['id']}", json=updates)
        assert response.status_code == 200
        assert response.json()["name"] == "updated-model"

    def test_update_model_not_found(self, client: TestClient, service: Mock) -> None:
        """Test model update when not found."""
        service.update_model.return_value = None

        response = client.put(f"/api/llm-providers/models/{uuid4()}", json={"name": "new-name"})
        assert response.status_code == 404
        assert "Model not found" in response.json()["detail"]

    def test_delete_model_success(self, client: TestClient, service: Mock, sample_model: dict[str, Any]) -> None:
        """Test successful model deletion."""
        service.delete_model.return_value = True

        response = client.delete(f"/api/llm-providers/models/{sample_model['id']}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    def test_delete_model_not_found(self, client: TestClient, service: Mock) -> None:
        """Test model deletion when not found."""
        service.delete_model.return_value = False

        response = client.delete(f"/api/llm-providers/models/{uuid4()}")
        assert response.status_code == 404
        assert "Model not found" in response.json()["detail"]


class TestProviderWithModels:
    def test_get_provider_with_models_success(self, client: TestClient, service: Mock, sample_provider: dict[str, Any], sample_model: dict[str, Any]) -> None:
        """Test successful retrieval of provider with models."""
        provider_with_models = dict(sample_provider)
        provider_with_models["models"] = [sample_model]
        service.get_provider_with_models.return_value = provider_with_models

        response = client.get(f"/api/llm-providers/{sample_provider['id']}/with-models")
        assert response.status_code == 200
        assert response.json()["name"] == sample_provider["name"]
        assert len(response.json()["models"]) == 1
        assert response.json()["models"][0]["name"] == sample_model["name"]

    def test_get_provider_with_models_not_found(self, client: TestClient, service: Mock) -> None:
        """Test provider with models retrieval when not found."""
        service.get_provider_with_models.return_value = None

        response = client.get(f"/api/llm-providers/{uuid4()}/with-models")
        assert response.status_code == 404
        assert "Provider not found" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__])
