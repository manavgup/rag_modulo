"""E2E test fixtures - Full stack for end-to-end tests."""

import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import atomic fixtures
sys.path.append(str(Path(__file__).parent.parent / "atomic"))


@pytest.fixture(scope="session")
def full_database_setup():
    """Set up full database for E2E tests."""
    # This would set up the complete database schema
    # For now, we'll use a mock
    return Mock()


@pytest.fixture(scope="session")
def full_llm_provider_setup():
    """Set up full LLM provider for E2E tests."""
    # This would set up the complete LLM provider
    # For now, we'll use a mock
    return Mock()


@pytest.fixture(scope="session")
def full_vector_store_setup():
    """Set up full vector store for E2E tests."""
    # This would set up the complete vector store
    # For now, we'll use a mock
    return Mock()


@pytest.fixture(scope="session")
def base_user_e2e(full_database_setup, full_llm_provider_setup):
    """Create a test user for E2E tests."""
    # This would create a real user in the database
    # For now, we'll use a mock
    return {
        "id": 1,
        "email": "e2e-test@example.com",
        "name": "E2E Test User",
        "role": "user"
    }


@pytest.fixture(scope="session")
def base_collection_e2e(full_database_setup, base_user_e2e):
    """Create a test collection for E2E tests."""
    # This would create a real collection in the database
    # For now, we'll use a mock
    return {
        "id": 1,
        "name": "E2E Test Collection",
        "description": "A collection for E2E testing",
        "user_id": base_user_e2e["id"]
    }


@pytest.fixture(scope="session")
def base_team_e2e(full_database_setup, base_user_e2e):
    """Create a test team for E2E tests."""
    # This would create a real team in the database
    # For now, we'll use a mock
    return {
        "id": 1,
        "name": "E2E Test Team",
        "description": "A team for E2E testing",
        "user_id": base_user_e2e["id"]
    }


@pytest.fixture
def e2e_settings(mock_settings):
    """Create settings for E2E tests with full configuration."""
    settings = Mock()
    settings.jwt_secret_key = "e2e-test-secret-key"
    settings.rag_llm = "watsonx"
    settings.wx_api_key = os.getenv("WX_API_KEY", "e2e-test-api-key")
    settings.wx_project_id = os.getenv("WX_PROJECT_ID", "e2e-test-project-id")
    settings.wx_url = os.getenv("WX_URL", "https://test.watsonx.ai")
    settings.vector_db = "milvus"
    settings.milvus_host = "localhost"
    settings.milvus_port = 19530
    settings.postgres_url = "postgresql://test:test@localhost:5432/e2e_test_db"
    settings.minio_endpoint = "localhost:9000"
    settings.minio_access_key = "test"
    settings.minio_secret_key = "test123"
    return settings
