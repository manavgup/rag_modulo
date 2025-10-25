"""E2E test fixtures for system administration tests.

E2E tests validate full workflows including:
- API endpoint interactions
- Database persistence
- Service integrations
- End-to-end data flow

Test Isolation:
- Uses transaction rollback on rag_modulo database
- Can run locally (http://localhost:8000) or in CI (http://backend:8000)
- Mock authentication enabled via SKIP_AUTH=true (set in root tests/conftest.py)
"""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture(scope="session")
def base_url() -> str:
    """Provide base URL for E2E tests.

    Supports both local and CI modes:
    - Local: http://localhost:8000/api (backend running via make local-dev-backend)
    - CI: http://backend:8000/api (backend in Docker network)
    """
    # Check if running in CI (docker-compose network)
    if os.getenv("E2E_MODE") == "ci":
        return "http://backend:8000/api"
    # Default to localhost for local development
    return "http://localhost:8000/api"


@pytest.fixture(scope="session")
def e2e_database_url():
    """Provide E2E database URL.

    Uses transaction rollback for isolation (no separate database needed).
    """
    db_user = os.getenv("COLLECTIONDB_USER", "rag_modulo_user")
    db_pass = os.getenv("COLLECTIONDB_PASS", "rag_modulo_password")
    db_host = os.getenv("COLLECTIONDB_HOST", "localhost")
    db_port = os.getenv("COLLECTIONDB_PORT", "5432")
    db_name = os.getenv("COLLECTIONDB_NAME", "rag_modulo")

    return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"


@pytest.fixture(scope="session")
def e2e_db_engine(e2e_database_url):
    """Create database engine for E2E tests.

    Session-scoped so engine is reused across all tests.
    """
    engine = create_engine(e2e_database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def e2e_db_session_factory(e2e_db_engine):
    """Create session factory for E2E tests."""
    return sessionmaker(bind=e2e_db_engine, class_=Session)


@pytest.fixture(scope="function")
def e2e_db_session(e2e_db_session_factory):
    """Provide real database session with transaction rollback for E2E tests.

    Each E2E test gets a fresh session wrapped in a transaction.
    The transaction is rolled back after the test, ensuring:
    - Fast execution (no manual cleanup)
    - Test isolation (clean slate for each test)
    - Real database integration
    """
    session = e2e_db_session_factory()
    session.begin()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="session")
def auth_headers() -> dict[str, str]:
    """Provide authentication headers for E2E tests."""
    return {"Content-Type": "application/json", "Accept": "application/json"}


@pytest.fixture(scope="session")
def e2e_milvus_config():
    """Provide Milvus configuration for E2E tests."""
    return {
        "host": os.getenv("MILVUS_HOST", "localhost"),
        "port": int(os.getenv("MILVUS_PORT", "19530")),
        "collection_prefix": os.getenv("MILVUS_COLLECTION_PREFIX", "e2e_"),
    }
