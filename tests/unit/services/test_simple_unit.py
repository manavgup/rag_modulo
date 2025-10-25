"""Simple unit tests to verify the unit test layer works."""

from unittest.mock import patch

import pytest


@pytest.mark.unit
def test_mock_user_service(mock_user_service) -> None:
    """Test that mock user service works."""
    user = mock_user_service.create_user({"email": "test@example.com"})
    assert user["email"] == "test@example.com"
    assert user["id"] == 1


@pytest.mark.unit
def test_mock_collection_service(mock_collection_service) -> None:
    """Test that mock collection service works."""
    collection = mock_collection_service.create_collection({"name": "Test Collection"})
    assert collection["name"] == "Test Collection"
    assert collection["id"] == 1


@pytest.mark.unit
def test_mock_team_service(mock_team_service) -> None:
    """Test that mock team service works."""
    team = mock_team_service.create_team({"name": "Test Team"})
    assert team["name"] == "Test Team"
    assert team["id"] == 1


@pytest.mark.unit
def test_mock_llm_provider(mock_llm_provider) -> None:
    """Test that mock LLM provider works."""
    response = mock_llm_provider.generate_response("Test prompt")
    assert response == "Test response"

    embeddings = mock_llm_provider.embed_text("Test text")
    assert len(embeddings) == 5
    assert embeddings[0] == 0.1


@pytest.mark.unit
def test_mock_vector_store(mock_vector_store) -> None:
    """Test that mock vector store works."""
    docs = mock_vector_store.add_documents([{"text": "Test document"}])
    assert len(docs) == 2
    assert "doc1" in docs

    results = mock_vector_store.search("test query", 1)
    assert len(results) == 1
    assert results[0]["id"] == "doc1"
    assert results[0]["score"] == 0.9


@pytest.mark.unit
def test_mock_database_session(mock_database_session) -> None:
    """Test that mock database session works."""
    mock_database_session.add("test_object")
    mock_database_session.commit()
    mock_database_session.rollback()

    # Verify methods were called
    mock_database_session.add.assert_called_once_with("test_object")
    mock_database_session.commit.assert_called_once()
    mock_database_session.rollback.assert_called_once()


@pytest.mark.unit
def test_mock_http_client(mock_http_client) -> None:
    """Test that mock HTTP client works."""
    response = mock_http_client.get("/test")
    assert response.status_code == 200
    assert response.json() == {"success": True}

    response = mock_http_client.post("/test", json={"data": "test"})
    assert response.status_code == 200


@pytest.mark.unit
def test_base_user_fixture(base_user) -> None:
    """Test that base_user fixture works."""
    assert base_user.email == "test@example.com"
    assert base_user.ibm_id == "test_user_123"
    assert base_user.name == "Test User"
    assert base_user.role == "user"
    assert base_user.id is not None


@pytest.mark.unit
def test_auth_headers_fixture(auth_headers) -> None:
    """Test that auth_headers fixture works."""
    assert "Authorization" in auth_headers
    assert "Bearer" in auth_headers["Authorization"]
    assert "X-User-Role" in auth_headers


@pytest.mark.unit
def test_test_collection_fixture(test_collection) -> None:
    """Test that test_collection fixture works."""
    assert test_collection["name"] == "Test Collection"
    assert test_collection["is_private"] is True
    assert test_collection["user_id"] == 1


@pytest.mark.unit
def test_test_llm_params_fixture(test_llm_params) -> None:
    """Test that test_llm_params fixture works."""
    assert test_llm_params["max_new_tokens"] == 100
    assert test_llm_params["temperature"] == 0.7
    assert test_llm_params["top_k"] == 50
    assert test_llm_params["top_p"] == 1.0
    assert test_llm_params["repetition_penalty"] == 1.1


@pytest.mark.unit
def test_pure_data_validation() -> None:
    """Test pure data validation without external dependencies."""
    from backend.rag_solution.schemas.user_schema import UserInput

    # Test valid user input
    user_input = UserInput(email="test@example.com", ibm_id="test_user_123", name="Test User", role="user")
    assert user_input.email == "test@example.com"
    assert user_input.ibm_id == "test_user_123"
    assert user_input.name == "Test User"
    assert user_input.role == "user"


@pytest.mark.unit
def test_pure_collection_validation() -> None:
    """Test pure collection validation without external dependencies."""
    from uuid import uuid4

    from backend.rag_solution.schemas.collection_schema import CollectionInput, CollectionStatus

    # Test valid collection input
    collection_input = CollectionInput(
        name="Test Collection", is_private=True, users=[uuid4(), uuid4(), uuid4()], status=CollectionStatus.CREATED
    )
    assert collection_input.name == "Test Collection"
    assert collection_input.is_private is True
    assert len(collection_input.users) == 3
    assert collection_input.status == CollectionStatus.CREATED


@pytest.mark.unit
def test_pure_team_validation() -> None:
    """Test pure team validation without external dependencies."""
    from backend.rag_solution.schemas.team_schema import TeamInput

    # Test valid team input
    team_input = TeamInput(name="Test Team", description="A test team")
    assert team_input.name == "Test Team"
    assert team_input.description == "A test team"


@pytest.mark.unit
def test_pure_search_validation() -> None:
    """Test pure search validation without external dependencies."""
    from uuid import uuid4

    from backend.rag_solution.schemas.search_schema import SearchInput

    # Test valid search input - no pipeline_id needed anymore
    search_input = SearchInput(question="What is machine learning?", collection_id=uuid4(), user_id=uuid4())
    assert search_input.question == "What is machine learning?"
    assert search_input.collection_id is not None
    assert search_input.user_id is not None
    # pipeline_id no longer exists - handled by backend


@pytest.mark.unit
def test_mock_patching() -> None:
    """Test that we can mock external dependencies."""
    with patch("builtins.print") as mock_print:
        print("Hello, World!")
        mock_print.assert_called_once_with("Hello, World!")


@pytest.mark.unit
def test_mock_context_manager() -> None:
    """Test that we can use mock context managers."""
    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True
        import os

        assert os.path.exists("/fake/path") is True
        mock_exists.assert_called_once_with("/fake/path")
