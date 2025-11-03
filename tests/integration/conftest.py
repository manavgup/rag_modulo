"""Integration test fixtures - Real services via testcontainers.

This module provides fixtures for integration tests that use real services
(PostgreSQL, Milvus, MinIO) running in Docker containers.

Key features:
- Separate test database (test_rag_db) to avoid polluting dev data
- Transaction rollback per test for fast cleanup
- Real service connections for integration testing
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import atomic fixtures
sys.path.append(str(Path(__file__).parent.parent / "atomic"))


@pytest.fixture(scope="session")
def test_database_url():
    """Provide test database URL for integration tests.

    Uses environment variables with fallback to development defaults.
    Integration tests use transaction rollback for isolation (no separate DB needed).
    """
    db_user = os.getenv("COLLECTIONDB_USER", "rag_modulo_user")
    db_pass = os.getenv("COLLECTIONDB_PASS", "rag_modulo_password")
    db_host = os.getenv("COLLECTIONDB_HOST", "localhost")
    db_port = os.getenv("COLLECTIONDB_PORT", "5432")
    db_name = os.getenv("COLLECTIONDB_NAME", "rag_modulo")

    return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"


@pytest.fixture(scope="session")
def db_engine(test_database_url):
    """Create database engine for integration tests.

    Uses session scope so the engine is created once per test session.
    """
    engine = create_engine(test_database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_session_factory(db_engine):
    """Create session factory for integration tests.

    Returns a sessionmaker that can create new sessions.
    """
    return sessionmaker(bind=db_engine, class_=Session)


@pytest.fixture(scope="function")
def real_db_session(db_session_factory):
    """Provide a real database session with transaction rollback.

    Each test gets a fresh session wrapped in a transaction.
    The transaction is rolled back after the test completes,
    ensuring no test data persists in the database.

    This provides:
    - Fast test execution (no database cleanup needed)
    - Test isolation (each test starts with clean state)
    - Real database integration (not mocked)
    """
    session = db_session_factory()
    session.begin()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="session")
def test_milvus_config():
    """Provide test Milvus configuration for integration tests."""
    return {
        "host": "localhost",
        "port": 19530,
        "collection_prefix": os.getenv("MILVUS_COLLECTION_PREFIX", "test_"),
    }


@pytest.fixture(scope="session")
def test_minio_config():
    """Provide test MinIO configuration for integration tests."""
    return {"endpoint": "localhost:9000", "access_key": "test", "secret_key": "test123", "bucket": "test-bucket"}


@pytest.fixture
def integration_settings():
    """Create settings for integration tests with real service configs."""
    # Import here to avoid circular dependencies
    from backend.core.config import Settings

    # Return actual Settings instance with test environment variables
    return Settings(
        # LLM settings (required)
        max_new_tokens=1024,
        temperature=0.7,
        top_k=50,
        top_p=1.0,
        repetition_penalty=1.1,
        # Database settings
        collectiondb_host=os.getenv("COLLECTIONDB_HOST", "localhost"),
        collectiondb_port=int(os.getenv("COLLECTIONDB_PORT", "5432")),
        collectiondb_user=os.getenv("COLLECTIONDB_USER", "rag_modulo_user"),
        collectiondb_pass=os.getenv("COLLECTIONDB_PASS", "rag_modulo_password"),
        collectiondb_name=os.getenv("COLLECTIONDB_NAME", "rag_modulo"),
    )


@pytest.fixture
def mock_watsonx_provider():
    """Create a mock WatsonX provider for integration tests."""
    provider = Mock()
    provider.generate_response.return_value = "Test response from WatsonX"
    provider.embed_text.return_value = [0.1, 0.2, 0.3, 0.4, 0.5] * 100  # 500-dim vector
    provider.is_available.return_value = True
    return provider


@pytest.fixture
def db_session():
    """Mock database session for integration tests."""
    session = Mock()
    session.execute.return_value.scalar.return_value = 1
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    return session


@pytest.fixture
def mock_llm_provider_service():
    """Mock LLM provider service that returns iterable objects."""
    service = Mock()

    # Mock provider object with required attributes
    mock_provider = Mock()
    mock_provider.id = "test-id"
    mock_provider.name = "watsonx"
    mock_provider.base_url = "https://test.watsonx.ai"
    mock_provider.is_active = True
    mock_provider.is_default = True

    # Make get_all_providers return a list instead of Mock
    service.get_all_providers.return_value = [mock_provider]
    service.create_provider.return_value = mock_provider
    service.get_by_name.return_value = mock_provider

    return service


@pytest.fixture
def mock_llm_model_service():
    """Mock LLM model service for integration tests."""
    service = Mock()
    service.get_models_by_provider.return_value = []
    service.create_model.return_value = Mock()

    return service
