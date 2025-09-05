# test_llm_provider.py

from typing import Any
from uuid import uuid4

import pytest

from rag_solution.schemas.llm_model_schema import ModelType
from rag_solution.schemas.llm_provider_schema import LLMProviderOutput

from .base_test import BaseTestRouter


@pytest.mark.api
class TestLLMProvider(BaseTestRouter):
    """Test LLM provider and model configuration endpoints."""

    @pytest.fixture
    def test_provider_data(self) -> dict[str, Any]:
        """Sample provider data for testing."""
        return {
            "name": f"test-provider-{uuid4()}",
            "base_url": "https://api.test.com",
            "api_key": "test-key",
            "project_id": "test-project",
            "is_default": True,
        }

    @pytest.fixture
    def test_model_data(self, ensure_watsonx_provider: LLMProviderOutput) -> dict[str, Any]:
        """Sample model data for testing."""
        return {
            "provider_id": str(ensure_watsonx_provider.id),
            "model_id": f"test-model-{uuid4()}",
            "default_model_id": "test-model",
            "model_type": ModelType.GENERATION,
            "timeout": 30,
            "max_retries": 3,
            "batch_size": 10,
            "retry_delay": 1.0,
            "stream": False,
            "rate_limit": 10,
            "is_default": True,
        }

    # Provider Management Tests
    async def test_create_provider(self, test_provider_data: dict[str, Any]) -> None:
        """Test POST /api/llm-providers/"""
        response = await self.post("/api/llm-providers/", json=test_provider_data)
        self.assert_success(response)
        data = response.json()
        assert data["name"] == test_provider_data["name"]
        assert data["base_url"] == test_provider_data["base_url"]
        assert "id" in data

        # Cleanup
        await self.delete(f"/api/llm-providers/{data['id']}")

    async def test_get_all_providers(self, ensure_watsonx_provider: LLMProviderOutput) -> None:  # noqa: ARG002
        """Test GET /api/llm-providers/"""
        response = await self.get("/api/llm-providers/")
        self.assert_success(response)
        providers = response.json()
        assert len(providers) > 0
        assert any(p["name"] == "watsonx" for p in providers)

    async def test_update_provider(self, ensure_watsonx_provider: LLMProviderOutput) -> None:
        """Test PUT /api/llm-providers/{id}"""
        update_data = {"base_url": "https://updated-api.test.com", "project_id": f"updated-project-{uuid4()}"}
        response = await self.put(f"/api/llm-providers/{ensure_watsonx_provider.id}", json=update_data)
        self.assert_success(response)
        data = response.json()
        assert data["base_url"] == update_data["base_url"]
        assert data["project_id"] == update_data["project_id"]

    # Model Management Tests
    async def test_create_model(self, test_model_data: dict[str, Any]) -> None:
        """Test POST /api/llm-providers/models/"""
        response = await self.post("/api/llm-providers/models/", json=test_model_data)
        self.assert_success(response)
        data = response.json()
        assert data["model_id"] == test_model_data["model_id"]
        assert data["model_type"] == test_model_data["model_type"]
        assert "id" in data

        # Cleanup
        await self.delete(f"/api/llm-providers/models/{data['id']}")

    async def test_get_provider_models(self, ensure_watsonx_provider: LLMProviderOutput) -> None:
        """Test GET /api/llm-providers/{id}/models"""
        response = await self.get(f"/api/llm-providers/{ensure_watsonx_provider.id}/models")
        self.assert_success(response)
        models = response.json()
        assert len(models) > 0
        assert all("model_id" in model for model in models)

    async def test_get_models_by_type(self) -> None:
        """Test GET /api/llm-providers/models/type/{type}"""
        response = await self.get("/api/llm-providers/models/type/GENERATION")
        self.assert_success(response)
        models = response.json()
        assert all(model["model_type"] == "GENERATION" for model in models)

    async def test_update_model(self, test_model_data: dict[str, Any]) -> None:
        """Test PUT /api/llm-providers/models/{id}"""
        # First create a model
        create_response = await self.post("/api/llm-providers/models/", json=test_model_data)
        self.assert_success(create_response)
        model_id = create_response.json()["id"]

        # Update it
        update_data = {"timeout": 60, "max_retries": 5}
        response = await self.put(f"/api/llm-providers/models/{model_id}", json=update_data)
        self.assert_success(response)
        data = response.json()
        assert data["timeout"] == update_data["timeout"]
        assert data["max_retries"] == update_data["max_retries"]

        # Cleanup
        await self.delete(f"/api/llm-providers/models/{model_id}")

    # Validation Tests
    async def test_invalid_provider_data(self) -> None:
        """Test provider creation with invalid data."""
        invalid_data = {
            "name": "test",  # Missing required fields
        }
        response = await self.post("/api/llm-providers/", json=invalid_data)
        assert response.status_code == 422

    async def test_invalid_model_data(self, ensure_watsonx_provider: LLMProviderOutput) -> None:
        """Test model creation with invalid data."""
        invalid_data = {
            "provider_id": str(ensure_watsonx_provider.id),
            "model_id": "",  # Invalid empty model_id
            "timeout": -1,  # Invalid negative timeout
        }
        response = await self.post("/api/llm-providers/models/", json=invalid_data)
        assert response.status_code == 422

    # Authorization Tests
    async def test_unauthorized_access(self) -> None:
        """Test endpoints without authentication."""
        test_id = uuid4()
        endpoints = [
            ("get", "/api/llm-providers/"),
            ("post", "/api/llm-providers/"),
            ("get", f"/api/llm-providers/{test_id}"),
            ("get", "/api/llm-providers/models/"),
            ("post", "/api/llm-providers/models/"),
        ]

        for method, endpoint in endpoints:
            response = await getattr(self, method)(endpoint, authenticated=False)
            self.assert_unauthorized(response)

    async def test_not_found_cases(self) -> None:
        """Test accessing non-existent resources."""
        non_existent_id = uuid4()

        # Non-existent provider
        response = await self.get(f"/api/llm-providers/{non_existent_id}")
        assert response.status_code == 404

        # Non-existent model
        response = await self.get(f"/api/llm-providers/models/{non_existent_id}")
        assert response.status_code == 404
