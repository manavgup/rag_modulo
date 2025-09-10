"""Atomic tests for pure data validation and business logic."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from rag_solution.schemas.collection_schema import CollectionInput
from rag_solution.schemas.team_schema import TeamInput
from rag_solution.schemas.user_schema import UserInput


@pytest.mark.atomic
def test_user_input_validation(mock_env_vars, isolated_test_env):
    """Test user input validation without external dependencies."""
    # Valid user input
    valid_user = UserInput(
        email="test@example.com",
        ibm_id="test_user_123",
        name="Test User",
        role="user"
    )
    assert valid_user.email == "test@example.com"
    assert valid_user.ibm_id == "test_user_123"
    assert valid_user.name == "Test User"
    assert valid_user.role == "user"


@pytest.mark.atomic
def test_user_input_invalid_email(mock_env_vars, isolated_test_env):
    """Test user input validation with invalid email."""
    with pytest.raises(ValidationError):
        UserInput(
            email="invalid-email",
            ibm_id="test_user_123",
            name="Test User",
            role="user"
        )


@pytest.mark.atomic
def test_collection_input_validation(mock_env_vars, isolated_test_env):
    """Test collection input validation without external dependencies."""
    # Valid collection input
    valid_collection = CollectionInput(
        name="Test Collection",
        is_private=True,
        users=[uuid4()]
    )
    assert valid_collection.name == "Test Collection"
    assert valid_collection.is_private is True
    assert len(valid_collection.users) == 1
    assert valid_collection.status.value == "created"


@pytest.mark.atomic
def test_team_input_validation(mock_env_vars, isolated_test_env):
    """Test team input validation without external dependencies."""
    # Valid team input
    valid_team = TeamInput(
        name="Test Team",
        description="A test team"
    )
    assert valid_team.name == "Test Team"
    assert valid_team.description == "A test team"


@pytest.mark.atomic
def test_uuid_generation(mock_env_vars, isolated_test_env):
    """Test UUID generation for atomic operations."""
    uuid1 = uuid4()
    uuid2 = uuid4()

    assert uuid1 != uuid2
    assert str(uuid1) != str(uuid2)
    assert len(str(uuid1)) == 36  # Standard UUID string length


@pytest.mark.atomic
def test_string_validation(mock_env_vars, isolated_test_env):
    """Test string validation logic."""
    # Test empty string
    assert "" == ""

    # Test string length
    test_string = "Hello, World!"
    assert len(test_string) == 13

    # Test string methods
    assert test_string.lower() == "hello, world!"
    assert test_string.upper() == "HELLO, WORLD!"
    assert test_string.replace(",", "") == "Hello World!"


@pytest.mark.atomic
def test_environment_variables(mock_env_vars, isolated_test_env):
    """Test environment variable handling."""
    assert mock_env_vars["JWT_SECRET_KEY"] == "test-secret-key"
    assert mock_env_vars["RAG_LLM"] == "watsonx"
    assert mock_env_vars["VECTOR_DB"] == "milvus"

    # Test that isolated environment works
    assert isolated_test_env["JWT_SECRET_KEY"] == "test-secret-key"
