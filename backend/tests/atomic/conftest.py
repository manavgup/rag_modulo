"""Atomic test fixtures - Pure data structures, no external dependencies."""

from typing import Any
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_env_vars() -> dict[str, str]:
    """Provide a standard set of mocked environment variables for testing."""
    return {
        "JWT_SECRET_KEY": "test-secret-key",
        "RAG_LLM": "watsonx",
        "WX_API_KEY": "test-api-key",
        "WX_PROJECT_ID": "test-project-id",
        "WX_URL": "https://test.watsonx.ai",
        "VECTOR_DB": "milvus",
        "MILVUS_HOST": "localhost",
        "MILVUS_PORT": "19530",
        "POSTGRES_URL": "postgresql://test:test@localhost:5432/test",
        "MINIO_ENDPOINT": "localhost:9000",
        "MINIO_ACCESS_KEY": "test",
        "MINIO_SECRET_KEY": "test123",
    }


@pytest.fixture
def isolated_test_env(mock_env_vars):
    """Provide an isolated test environment with mocked variables."""
    import os
    from unittest.mock import patch

    with patch.dict(os.environ, mock_env_vars, clear=True):
        yield mock_env_vars


@pytest.fixture
def user_input_data() -> dict[str, Any]:
    """Create user input data for testing."""
    return {
        "email": "test@example.com",
        "ibm_id": "test_user_123",
        "name": "Test User",
        "role": "user"
    }


@pytest.fixture
def collection_input_data() -> dict[str, Any]:
    """Create collection input data for testing."""
    return {
        "name": "Test Collection",
        "description": "A test collection",
        "user_id": 1
    }


@pytest.fixture
def team_input_data() -> dict[str, Any]:
    """Create team input data for testing."""
    return {
        "name": "Test Team",
        "description": "A test team",
        "user_id": 1
    }


@pytest.fixture
def mock_settings():
    """Create a mock settings object for testing."""
    settings = Mock()
    settings.jwt_secret_key = "test-secret-key"
    settings.rag_llm = "watsonx"
    settings.wx_api_key = "test-api-key"
    settings.wx_project_id = "test-project-id"
    settings.wx_url = "https://test.watsonx.ai"
    settings.vector_db = "milvus"
    settings.milvus_host = "localhost"
    settings.milvus_port = 19530
    settings.postgres_url = "postgresql://test:test@localhost:5432/test"
    settings.minio_endpoint = "localhost:9000"
    settings.minio_access_key = "test"
    settings.minio_secret_key = "test123"
    return settings
