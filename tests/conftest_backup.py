"""Pytest configuration file.

This file serves as the main pytest configuration, handling:
1. Logging setup and configuration
2. Test isolation fixtures for atomic tests
3. General test configuration
"""

import logging
import os
from unittest.mock import Mock, patch

import pytest
from backend.core.config import Settings
from backend.core.logging_utils import get_logger, setup_logging

logger = get_logger("tests.conftest")

# Define collect_ignore at module level
collect_ignore = ["backend/tests.bak", "backend/tests_backup"]
collect_ignore_glob = ["tests.bak/*", "tests_backup/*"]


@pytest.fixture(autouse=True)
def capture_logs(caplog):
    """Capture logs during tests."""
    caplog.set_level(logging.INFO)


@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Configure logging for tests.

    This fixture:
    - Sets up basic logging configuration
    - Configures log levels for different components
    - Runs automatically at the start of test session
    """
    setup_logging()

    # Set root logger to DEBUG for tests
    logging.getLogger().setLevel(logging.DEBUG)

    # Configure specific loggers
    loggers_config = {
        # Database loggers - keep at CRITICAL to reduce noise
        "sqlalchemy": logging.CRITICAL,
        "sqlalchemy.engine": logging.CRITICAL,
        "sqlalchemy.engine.base.Engine": logging.CRITICAL,
        "sqlalchemy.dialects": logging.CRITICAL,
        "sqlalchemy.pool": logging.CRITICAL,
        "sqlalchemy.orm": logging.CRITICAL,
        # Network loggers - keep at CRITICAL to reduce noise
        "urllib3": logging.CRITICAL,
        "asyncio": logging.CRITICAL,
        "aiohttp": logging.CRITICAL,
        # Application loggers - set to DEBUG for detailed info
        "ibm_watsonx_ai": logging.DEBUG,
        "llm.providers": logging.DEBUG,
        "tests.conftest": logging.DEBUG,
        "tests.fixtures": logging.DEBUG,
    }

    for logger_name, level in loggers_config.items():
        logging.getLogger(logger_name).setLevel(level)

    logger.info("Test logging configured")


# Test Isolation Fixtures for Atomic Tests
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
        "MILVUS_HOST": "localhost",
        "MILVUS_PORT": "19530",
        "PROJECT_NAME": "rag_modulo",
        "EMBEDDING_MODEL": "test-embedding-model",
        "DATA_DIR": "/test/data/dir",
    }


@pytest.fixture
def mock_settings(mock_env_vars):
    """Create a mocked settings object with test values."""
    with patch.dict(os.environ, mock_env_vars, clear=True):
        settings = Settings()
        return settings


@pytest.fixture
def e2e_settings():
    """Create a real settings object for E2E tests using actual environment variables."""
    # Import here to avoid circular imports
    from backend.core.config import get_settings

    return get_settings()


@pytest.fixture
def mock_watsonx_provider():
    """Create a mocked WatsonX provider for testing."""
    mock_provider = Mock()
    mock_provider.get_embeddings.return_value = [0.1, 0.2, 0.3]
    mock_provider.generate_questions.return_value = [
        "What is the main topic?",
        "What are the key points?",
        "What is the conclusion?",
    ]
    mock_provider.generate_answer.return_value = "This is a test answer."
    return mock_provider


@pytest.fixture
def mock_vector_store():
    """Create a mocked vector store for testing."""
    mock_store = Mock()
    mock_store.create_collection = Mock()
    mock_store.delete_collection = Mock()
    mock_store.add_documents = Mock()
    mock_store.retrieve_documents = Mock(return_value=[])
    mock_store.search = Mock(return_value=[])
    mock_store._connect = Mock()
    return mock_store


@pytest.fixture
def mock_provider_factory(mock_watsonx_provider):
    """Create a mocked provider factory for testing."""
    mock_factory = Mock()
    mock_factory.get_provider.return_value = mock_watsonx_provider
    return mock_factory


@pytest.fixture
def isolated_test_env():
    """Provide a completely isolated test environment with no real env vars."""
    with patch.dict(os.environ, {}, clear=True):
        yield


@pytest.fixture
def minimal_test_env():
    """Provide minimal required environment variables for testing."""
    minimal_vars = {
        "JWT_SECRET_KEY": "minimal-secret",
        "RAG_LLM": "watsonx",
        "WATSONX_INSTANCE_ID": "minimal-instance",
        "WATSONX_APIKEY": "minimal-key",
        "WATSONX_URL": "https://minimal.watsonx.ai",
        "WATSONX_PROJECT_ID": "minimal-project",
    }
    with patch.dict(os.environ, minimal_vars, clear=True):
        yield


def create_mock_document(text: str = "Test document content"):
    """Create a mock document for testing."""
    from datetime import datetime
    from unittest.mock import Mock

    # Create a simple mock document without importing complex dependencies
    mock_doc = Mock()
    mock_doc.document_id = "test-doc-1"
    mock_doc.name = "test.txt"
    mock_doc.chunks = [
        Mock(
            chunk_id="chunk-1",
            text=text,
            vectors=[0.1, 0.2, 0.3],
            metadata=Mock(
                source="OTHER",
                created_at=datetime.now().isoformat() + "Z",
            ),
        )
    ]
    return mock_doc


def mock_embeddings_call(*args, **kwargs):
    """Mock function for get_embeddings calls."""
    return [0.1, 0.2, 0.3]


def mock_get_datastore(*args, **kwargs):
    """Mock function for get_datastore calls."""
    return Mock()
