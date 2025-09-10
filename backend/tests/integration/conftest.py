"""Integration test fixtures - Real services via testcontainers."""

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
def test_database_url():
    """Provide test database URL for integration tests."""
    return "postgresql://test:test@localhost:5432/test_db"


@pytest.fixture(scope="session")
def test_milvus_config():
    """Provide test Milvus configuration for integration tests."""
    return {"host": "localhost", "port": 19530, "collection_name": "test_collection"}


@pytest.fixture(scope="session")
def test_minio_config():
    """Provide test MinIO configuration for integration tests."""
    return {"endpoint": "localhost:9000", "access_key": "test", "secret_key": "test123", "bucket": "test-bucket"}


@pytest.fixture
def integration_settings(mock_settings):
    """Create settings for integration tests with real service configs."""
    settings = Mock()
    settings.jwt_secret_key = "test-secret-key"
    settings.rag_llm = "watsonx"
    settings.wx_api_key = os.getenv("WX_API_KEY", "test-api-key")
    settings.wx_project_id = os.getenv("WX_PROJECT_ID", "test-project-id")
    settings.wx_url = os.getenv("WX_URL", "https://test.watsonx.ai")
    settings.vector_db = "milvus"
    settings.milvus_host = "localhost"
    settings.milvus_port = 19530
    settings.postgres_url = "postgresql://test:test@localhost:5432/test_db"
    settings.minio_endpoint = "localhost:9000"
    settings.minio_access_key = "test"
    settings.minio_secret_key = "test123"
    return settings


@pytest.fixture
def mock_watsonx_provider():
    """Create a mock WatsonX provider for integration tests."""
    provider = Mock()
    provider.generate_response.return_value = "Test response from WatsonX"
    provider.embed_text.return_value = [0.1, 0.2, 0.3, 0.4, 0.5] * 100  # 500-dim vector
    provider.is_available.return_value = True
    return provider
