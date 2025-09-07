"""Integration tests for UserService."""

from typing import Any
from uuid import uuid4

import pytest
from fastapi import HTTPException

from rag_solution.schemas.user_schema import UserInput, UserOutput
from rag_solution.schemas.user_team_schema import UserTeamOutput


# -------------------------------------------
# 🔧 Test Fixtures
# -------------------------------------------
@pytest.fixture
def test_user_input() -> UserInput:
    """Create a sample user input."""
    return UserInput(ibm_id="test_ibm_id_2", email="test2@example.com", name="Test User 2", role="user")


# -------------------------------------------
# 🧪 User Creation Tests
# -------------------------------------------
def test_create_user_success(user_service: Any, test_user_input: UserInput) -> None:
    """Test successful user creation."""
    result = user_service.create_user(test_user_input)

    assert isinstance(result, UserOutput)
    assert result.ibm_id == test_user_input.ibm_id
    assert result.email == test_user_input.email
    assert result.name == test_user_input.name
    assert result.role == test_user_input.role


def test_create_user_duplicate_ibm_id(user_service: Any, base_user: UserOutput, test_user_input: UserInput) -> None:
    """Test creating user with duplicate IBM ID."""
    duplicate_input = test_user_input.model_copy(update={"ibm_id": base_user.ibm_id})

    with pytest.raises(HTTPException) as exc_info:
        user_service.create_user(duplicate_input)
    assert exc_info.value.status_code == 400
    assert "IBM ID already exists" in str(exc_info.value.detail)


def test_get_or_create_user_by_fields(user_service: Any) -> None:
    """Test getting or creating user by fields."""
    # First call should create user
    result = user_service.get_or_create_user_by_fields(ibm_id="test_ibm_id_3", email="test3@example.com", name="Test User 3")
    assert isinstance(result, UserOutput)

    # Second call should return existing user
    same_result = user_service.get_or_create_user_by_fields(ibm_id="test_ibm_id_3", email="test3@example.com", name="Test User 3")
    assert same_result.id == result.id


# -------------------------------------------
# 🧪 User Retrieval Tests
# -------------------------------------------
def test_get_user_by_id(user_service: Any, base_user: UserOutput) -> None:
    """Test getting user by ID."""
    result = user_service.get_user_by_id(base_user.id)

    assert isinstance(result, UserOutput)
    assert result.id == base_user.id
    assert result.name == base_user.name


def test_get_user_by_id_not_found(user_service: Any) -> None:
    """Test getting user by ID when not found."""
    with pytest.raises(HTTPException) as exc_info:
        user_service.get_user_by_id(uuid4())
    assert exc_info.value.status_code == 404
    assert "User not found" in str(exc_info.value.detail)


def test_get_user_by_ibm_id(user_service: Any, base_user: UserOutput) -> None:
    """Test getting user by IBM ID."""
    result = user_service.get_user_by_ibm_id(base_user.ibm_id)

    assert isinstance(result, UserOutput)
    assert result.ibm_id == base_user.ibm_id
    assert result.name == base_user.name


def test_get_user_by_ibm_id_not_found(user_service: Any) -> None:
    """Test getting user by IBM ID when not found."""
    with pytest.raises(HTTPException) as exc_info:
        user_service.get_user_by_ibm_id("non-existent-ibm-id")
    assert exc_info.value.status_code == 404
    assert "User not found" in str(exc_info.value.detail)


# -------------------------------------------
# 🧪 User Update Tests
# -------------------------------------------
def test_update_user(user_service: Any, base_user: UserOutput) -> None:
    """Test updating a user."""
    update_input = UserInput(ibm_id=base_user.ibm_id, email="updated@example.com", name="Updated Name", role="admin")

    result = user_service.update_user(base_user.id, update_input)

    assert isinstance(result, UserOutput)
    assert result.id == base_user.id
    assert result.email == update_input.email
    assert result.name == update_input.name
    assert result.role == update_input.role


def test_update_user_not_found(user_service: Any, test_user_input: UserInput) -> None:
    """Test updating a user when not found."""
    with pytest.raises(HTTPException) as exc_info:
        user_service.update_user(uuid4(), test_user_input)
    assert exc_info.value.status_code == 404
    assert "User not found" in str(exc_info.value.detail)


# -------------------------------------------
# 🧪 User Deletion Tests
# -------------------------------------------
def test_delete_user(user_service: Any, base_user: UserOutput) -> None:
    """Test deleting a user."""
    result = user_service.delete_user(base_user.id)

    assert result is True
    with pytest.raises(HTTPException) as exc_info:
        user_service.get_user_by_id(base_user.id)
    assert exc_info.value.status_code == 404


def test_delete_user_not_found(user_service: Any) -> None:
    """Test deleting a user when not found."""
    with pytest.raises(HTTPException) as exc_info:
        user_service.delete_user(uuid4())
    assert exc_info.value.status_code == 404
    assert "User not found" in str(exc_info.value.detail)


# -------------------------------------------
# 🧪 User Team Tests
# -------------------------------------------
def test_get_user_teams(user_service: Any, user_team_service: Any, base_user: UserOutput, base_team: Any, user_team: Any) -> None:
    """Test getting user teams."""
    result = user_team_service.get_team_users(base_team.id)

    assert len(result) == 1
    assert isinstance(result[0], UserTeamOutput)


# -------------------------------------------
# 🧪 User Listing Tests
# -------------------------------------------
def test_list_users(user_service: Any, base_user: UserOutput, db_session: Any, clean_db: Any) -> None:
    """Test listing users."""
    # Create additional user
    other_user = user_service.create_user(UserInput(ibm_id=f"other_user_{uuid4()}", email="other@example.com", name="Other User", role="user"))

    # Get list of users
    result = user_service.list_users(skip=0, limit=10)

    # Verify results
    assert len(result) > 1  # we add other users during our tests
    assert all(isinstance(user, UserOutput) for user in result)
    user_ids = {user.id for user in result}
    assert base_user.id in user_ids
    assert other_user.id in user_ids


if __name__ == "__main__":
    pytest.main([__file__])
