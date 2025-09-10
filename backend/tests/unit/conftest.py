"""Unit test fixtures - Mocked dependencies for unit tests."""

# Import atomic fixtures from the atomic layer
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.append(str(Path(__file__).parent.parent / "atomic"))


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
