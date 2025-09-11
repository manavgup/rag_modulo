"""Unit test fixtures - Mocked dependencies for unit tests."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest

# Add atomic tests to path for imports
sys.path.append(str(Path(__file__).parent.parent / "atomic"))

# Import fixtures from other layers
from rag_solution.schemas.user_schema import UserOutput
from tests.fixtures.auth import test_client as auth_test_client


@pytest.fixture
def mock_user_service():
    """Create a mocked user service for unit tests."""
    service = Mock()
    service.create_user.return_value = {"id": 1, "email": "test@example.com"}
    service.get_user.return_value = {"id": 1, "email": "test@example.com"}
    service.update_user.return_value = {"id": 1, "email": "updated@example.com"}
    service.delete_user.return_value = True
    return service


@pytest.fixture
def mock_collection_service():
    """Create a mocked collection service for unit tests."""
    service = Mock()
    service.create_collection.return_value = {"id": 1, "name": "Test Collection"}
    service.get_collection.return_value = {"id": 1, "name": "Test Collection"}
    service.update_collection.return_value = {"id": 1, "name": "Updated Collection"}
    service.delete_collection.return_value = True
    return service


@pytest.fixture
def mock_team_service():
    """Create a mocked team service for unit tests."""
    service = Mock()
    service.create_team.return_value = {"id": 1, "name": "Test Team"}
    service.get_team.return_value = {"id": 1, "name": "Test Team"}
    service.update_team.return_value = {"id": 1, "name": "Updated Team"}
    service.delete_team.return_value = True
    return service


@pytest.fixture
def mock_llm_provider():
    """Create a mocked LLM provider for unit tests."""
    provider = Mock()
    provider.generate_response.return_value = "Test response"
    provider.embed_text.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
    provider.is_available.return_value = True
    return provider


@pytest.fixture
def mock_vector_store():
    """Create a mocked vector store for unit tests."""
    store = Mock()
    store.add_documents.return_value = ["doc1", "doc2"]
    store.search.return_value = [{"id": "doc1", "score": 0.9}]
    store.delete.return_value = True
    store.get_collection_info.return_value = {"count": 100}
    return store


@pytest.fixture
def mock_database_session():
    """Create a mocked database session for unit tests."""
    session = Mock()
    session.add.return_value = None
    session.commit.return_value = None
    session.rollback.return_value = None
    session.query.return_value = Mock()
    return session


@pytest.fixture
def mock_http_client():
    """Create a mocked HTTP client for unit tests."""
    client = Mock()
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"success": True}
    client.post.return_value = response
    client.get.return_value = response
    client.put.return_value = response
    client.delete.return_value = response
    return client


# Re-export fixtures from other layers for unit tests
@pytest.fixture
def test_client() -> Any:
    """Re-export test_client fixture for unit tests."""
    return auth_test_client


@pytest.fixture
def mock_auth_token() -> str:
    """Create a mock JWT token for unit tests."""
    return "mock_token_for_testing"


@pytest.fixture
def auth_headers(mock_auth_token: str, base_user: UserOutput) -> dict[str, str]:
    """Create regular user authentication headers for unit tests."""
    return {"Authorization": f"Bearer {mock_auth_token}", "X-User-UUID": str(base_user.id), "X-User-Role": "user"}


@pytest.fixture
def base_user() -> UserOutput:
    """Create a base user for unit tests."""
    return UserOutput(id=uuid4(), email="test@example.com", ibm_id="test_user_123", name="Test User", role="user", preferred_provider_id=None, created_at=datetime.now(), updated_at=datetime.now())


@pytest.fixture
def test_collection() -> dict:
    """Create test collection data for unit tests."""
    return {"id": 1, "name": "Test Collection", "description": "A test collection", "is_private": True, "user_id": 1}


@pytest.fixture
def test_llm_params() -> dict:
    """Create test LLM parameters for unit tests."""
    return {"max_new_tokens": 100, "temperature": 0.7, "top_k": 50, "top_p": 1.0, "repetition_penalty": 1.1}


@pytest.fixture
def integration_settings():
    """Mock integration settings for unit tests."""
    from unittest.mock import Mock

    settings = Mock()
    settings.jwt_secret_key = "test-secret-key"
    settings.rag_llm = "watsonx"
    settings.vector_db = "milvus"
    settings.postgres_url = "postgresql://test:test@localhost:5432/test_db"
    return settings
