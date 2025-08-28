# test_llm_config.py

import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4
from .base_test import BaseTestRouter
from rag_solution.schemas.prompt_template_schema import PromptTemplateType

class TestLLMConfiguration(BaseTestRouter):
    """Test LLM-related configuration endpoints."""

    @pytest.fixture
    def test_parameters_data(self):
        """Sample LLM parameters data."""
        return {
            "name": "Test Parameters",
            "description": "Parameters for testing",
            "max_new_tokens": 100,
            "temperature": 0.7,
            "top_k": 50,
            "top_p": 1.0,
            "repetition_penalty": 1.1,
            "is_default": False
        }

    @pytest.fixture
    def test_template_data(self, base_user):
        """Sample prompt template data."""
        return {
            "user_id": str(base_user.id),
            "name": "Test Template",
            "template_type": PromptTemplateType.RAG_QUERY,
            "system_prompt": "You are a helpful assistant",
            "template_format": "Context: {context}\nQuestion: {question}\nAnswer:",
            "input_variables": {
                "context": "The context to consider",
                "question": "The question to answer"
            },
            "example_inputs": {
                "context": "Example context",
                "question": "Example question"
            },
            "context_strategy": {"type": "simple"},
            "max_context_length": 1000,
            "is_default": False
        }

    # LLM Parameters Tests
    @pytest.mark.asyncio
    async def test_create_parameters(self, base_user, test_parameters_data):
        """Test creating LLM parameters."""
        response = self.post(
            f"/api/users/{base_user.id}/llm-parameters",
            json=test_parameters_data
        )
        self.assert_success(response)
        data = response.json()
        assert data["name"] == test_parameters_data["name"]
        assert data["max_new_tokens"] == test_parameters_data["max_new_tokens"]
        
        # Cleanup
        self.delete(f"/api/users/{base_user.id}/llm-parameters/{data['id']}")

    @pytest.mark.asyncio
    async def test_get_user_parameters(self, base_user):
        """Test getting user's LLM parameters."""
        # Create test parameters first
        test_params = {
            "name": "Test Parameters",
            "description": "Parameters for testing",
            "max_new_tokens": 100,
            "temperature": 0.7,
            "top_k": 50,
            "top_p": 1.0,
            "repetition_penalty": 1.1,
            "is_default": False
        }
        
        # Create parameters
        create_response = self.post(
            f"/api/users/{base_user.id}/llm-parameters",
            json=test_params
        )
        self.assert_success(create_response)
        created_params = create_response.json()
        
        # Now get and verify parameters
        response = self.get(f"/api/users/{base_user.id}/llm-parameters")
        self.assert_success(response)
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["user_id"] == str(base_user.id)
        assert data[0]["name"] == test_params["name"]
        
        # Cleanup
        self.delete(f"/api/users/{base_user.id}/llm-parameters/{created_params['id']}")

    # Prompt Template Tests
    @pytest.mark.asyncio
    async def test_create_template(self, base_user, test_template_data):
        """Test creating prompt template."""
        response = self.post(
            f"/api/users/{base_user.id}/prompt-templates",
            json=test_template_data
        )
        self.assert_success(response)
        data = response.json()
        assert data["name"] == test_template_data["name"]
        assert data["template_type"] == test_template_data["template_type"]
        
        # Cleanup
        cleanup_response = self.delete(f"/api/users/{base_user.id}/prompt-templates/{data['id']}")
        assert cleanup_response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_templates_by_type(self, base_user, base_multiple_prompt_templates):
        """Test getting templates by type."""
        response = self.get(
            f"/api/users/{base_user.id}/prompt-templates/type/RAG_QUERY"
        )
        self.assert_success(response)
        data = response.json()
        assert isinstance(data, list)
        assert all(t["template_type"] == "RAG_QUERY" for t in data)

    # Authorization Tests
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, base_user):
        """Test accessing endpoints without authentication."""
        endpoints = [
            ("get", f"/api/users/{base_user.id}/llm-parameters"),
            ("get", f"/api/users/{base_user.id}/prompt-templates"),
        ]
        
        for method, endpoint in endpoints:
            response = getattr(self, method)(endpoint, authenticated=False)
            self.assert_unauthorized(response)

    @pytest.mark.asyncio
    async def test_wrong_user_access(self, test_parameters_data):
        """Test accessing with wrong user ID."""
        wrong_user_id = uuid4()
        response = self.post(
            f"/api/users/{wrong_user_id}/llm-parameters",
            json=test_parameters_data
        )
        self.assert_forbidden(response)

    # Validation Tests
    @pytest.mark.asyncio
    async def test_invalid_parameters(self, base_user):
        """Test parameter validation."""
        invalid_data = {
            "name": "Test",
            "temperature": 2.0  # Invalid temperature value
        }
        response = self.post(
            f"/api/users/{base_user.id}/llm-parameters",
            json=invalid_data
        )
        assert response.status_code == 422
