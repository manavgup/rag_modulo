"""API test fixtures - E2E testing with FastAPI TestClient."""

from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

# Define fixtures directly to avoid circular imports


@pytest.fixture
def mock_env_vars():
    """Provide a standard set of mocked environment variables for testing."""
    return {
        "JWT_SECRET_KEY": "test-secret-key",
        "RAG_LLM": "watsonx",
        "WX_API_KEY": "test-api-key",
        "WX_URL": "https://test.watsonx.ai",
        "WX_PROJECT_ID": "test-project-id",
        "WATSONX_INSTANCE_ID": "test-instance-id",
        "WATSONX_APIKEY": "test-api-key",
        "WATSONX_URL": "https://test.watsonx.ai",
        "VECTOR_DB": "milvus",
        "MILVUS_HOST": "test-milvus-host",
        "MILVUS_PORT": "19530",
        "PROJECT_NAME": "rag_modulo",
        "EMBEDDING_MODEL": "test-embedding-model",
        "DATA_DIR": "/test/data/dir",
    }


@pytest.fixture
def mock_settings(mock_env_vars):
    """Create a mocked settings object with test values."""
    import os
    from unittest.mock import patch

    with patch.dict(os.environ, mock_env_vars, clear=True):
        from core.config import Settings

        settings = Settings()
        return settings


@pytest.fixture
def db_session():
    """Mock database session for API tests."""
    session = Mock(spec=Session)
    session.execute.return_value.scalar.return_value = 1
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    return session


@pytest.fixture
def test_db(db_session: Session) -> Session:
    """Get test database session."""
    return db_session


@pytest.fixture
def test_empty_collection():
    """Create a test empty collection."""
    from datetime import datetime
    from uuid import uuid4

    from rag_solution.schemas.collection_schema import CollectionOutput, CollectionStatus

    return CollectionOutput(
        id=uuid4(),
        name="Test Collection",
        vector_db_name="test_collection",
        is_private=True,
        user_ids=[],
        files=[],
        status=CollectionStatus.CREATED,
        created_at=datetime(2024, 1, 1, 0, 0, 0),
        updated_at=datetime(2024, 1, 1, 0, 0, 0),
    )


@pytest.fixture
def test_llm_config():
    """Create test LLM configuration."""
    from rag_solution.schemas.llm_provider_schema import LLMProviderInput

    return LLMProviderInput(name="watsonx", url="https://test.watsonx.ai", api_key="test-api-key", project_id="test-project-id", is_active=True)


@pytest.fixture
def test_user():
    """Create a test user."""
    from datetime import datetime
    from uuid import uuid4

    from rag_solution.schemas.user_schema import UserOutput

    return UserOutput(
        id=uuid4(),
        email="test@example.com",
        ibm_id="test_user_123",
        name="Test User",
        role="user",
        preferred_provider_id=None,
        created_at=datetime(2024, 1, 1, 0, 0, 0),
        updated_at=datetime(2024, 1, 1, 0, 0, 0),
    )


@pytest.fixture
def base_collection(test_empty_collection):
    """Alias for test_empty_collection for backward compatibility."""
    return test_empty_collection


@pytest.fixture
def base_user(test_user):
    """Alias for test_user for backward compatibility."""
    return test_user


@pytest.fixture
def test_pipeline_config():
    """Create test pipeline configuration."""
    from unittest.mock import Mock
    from uuid import uuid4

    # Create a mock pipeline config that behaves like a database model
    pipeline = Mock()
    pipeline.id = uuid4()
    pipeline.name = "test-pipeline"
    pipeline.description = "Test pipeline for search debugging"
    pipeline.collection_id = None  # Will be set in tests
    pipeline.user_id = uuid4()
    pipeline.chunking_strategy = "fixed"
    pipeline.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
    pipeline.retriever = "vector"
    pipeline.context_strategy = "priority"
    pipeline.enable_logging = True
    pipeline.max_context_length = 2048
    pipeline.timeout = 30.0
    pipeline.config_metadata = {"top_k": 5, "similarity_threshold": 0.7}
    pipeline.is_default = True
    pipeline.provider_id = uuid4()

    return pipeline


@pytest.fixture
def indexed_documents():
    """Create test indexed documents."""
    return "Sample test document content for search testing"


@pytest.fixture
def base_file():
    """Create test file output."""
    from rag_solution.schemas.file_schema import FileOutput

    return FileOutput(file_id="test-file-1", name="test.txt", size=1024, content_type="text/plain", status="processed", created_at="2024-01-01T00:00:00Z", updated_at="2024-01-01T00:00:00Z")
