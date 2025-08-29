"""Integration tests for UserService."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from rag_solution.models.team import Team
from rag_solution.models.user import User
from rag_solution.models.user_team import UserTeam
from rag_solution.schemas.team_schema import TeamOutput
from rag_solution.schemas.user_schema import UserInput, UserOutput
from rag_solution.services.user_service import UserService


@pytest.fixture
def test_user_input() -> UserInput:
    """Create a sample user input."""
    return UserInput(ibm_id="test_ibm_id_2", email="test2@example.com", name="Test User 2", role="user")


@pytest.mark.atomic
def test_create_user_success(db_session: Session, test_user_input: UserInput):
    """Test successful user creation."""
    service = UserService(db_session)

    result = service.create_user(test_user_input)

    assert isinstance(result, UserOutput)
    assert result.ibm_id == test_user_input.ibm_id
    assert result.email == test_user_input.email
    assert result.name == test_user_input.name
    assert result.role == test_user_input.role


@pytest.mark.atomic
def test_create_user_duplicate_ibm_id(db_session: Session, base_user: User, test_user_input: UserInput):
    """Test creating user with duplicate IBM ID."""
    service = UserService(db_session)
    duplicate_input = test_user_input.model_copy(update={"ibm_id": base_user.ibm_id})

    with pytest.raises(HTTPException) as exc_info:
        service.create_user(duplicate_input)
    assert exc_info.value.status_code == 400
    assert "IBM ID already exists" in str(exc_info.value.detail)


@pytest.mark.atomic
def test_get_or_create_user_by_fields(db_session: Session):
    """Test getting or creating user by fields."""
    service = UserService(db_session)

    # First call should create user
    result = service.get_or_create_user_by_fields(ibm_id="test_ibm_id_3", email="test3@example.com", name="Test User 3")
    assert isinstance(result, UserOutput)

    # Second call should return existing user
    same_result = service.get_or_create_user_by_fields(
        ibm_id="test_ibm_id_3", email="test3@example.com", name="Test User 3"
    )
    assert same_result.id == result.id


@pytest.mark.atomic
def test_get_user_by_id(db_session: Session, base_user: User):
    """Test getting user by ID."""
    service = UserService(db_session)

    result = service.get_user_by_id(base_user.id)

    assert isinstance(result, UserOutput)
    assert result.id == base_user.id
    assert result.name == base_user.name


@pytest.mark.atomic
def test_get_user_by_id_not_found(db_session: Session):
    """Test getting user by ID when not found."""
    service = UserService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        service.get_user_by_id(uuid4())
    assert exc_info.value.status_code == 404
    assert "User not found" in str(exc_info.value.detail)


@pytest.mark.atomic
def test_get_user_by_ibm_id(db_session: Session, base_user: User):
    """Test getting user by IBM ID."""
    service = UserService(db_session)

    result = service.get_user_by_ibm_id(base_user.ibm_id)

    assert isinstance(result, UserOutput)
    assert result.ibm_id == base_user.ibm_id
    assert result.name == base_user.name


@pytest.mark.atomic
def test_get_user_by_ibm_id_not_found(db_session: Session):
    """Test getting user by IBM ID when not found."""
    service = UserService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        service.get_user_by_ibm_id("non-existent-ibm-id")
    assert exc_info.value.status_code == 404
    assert "User not found" in str(exc_info.value.detail)


@pytest.mark.atomic
def test_update_user(db_session: Session, base_user: User):
    """Test updating a user."""
    service = UserService(db_session)
    update_input = UserInput(ibm_id=base_user.ibm_id, email="updated@example.com", name="Updated Name", role="admin")

    result = service.update_user(base_user.id, update_input)

    assert isinstance(result, UserOutput)
    assert result.id == base_user.id
    assert result.email == update_input.email
    assert result.name == update_input.name
    assert result.role == update_input.role


@pytest.mark.atomic
def test_update_user_not_found(db_session: Session, test_user_input: UserInput):
    """Test updating a user when not found."""
    service = UserService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        service.update_user(uuid4(), test_user_input)
    assert exc_info.value.status_code == 404
    assert "User not found" in str(exc_info.value.detail)


@pytest.mark.atomic
def test_delete_user(db_session: Session, base_user: User):
    """Test deleting a user."""
    service = UserService(db_session)

    result = service.delete_user(base_user.id)

    assert result is True
    # Verify user is deleted
    assert db_session.query(User).filter_by(id=base_user.id).first() is None


@pytest.mark.atomic
def test_delete_user_not_found(db_session: Session):
    """Test deleting a user when not found."""
    service = UserService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        service.delete_user(uuid4())
    assert exc_info.value.status_code == 404
    assert "User not found" in str(exc_info.value.detail)


@pytest.mark.atomic
def test_get_user_teams(db_session: Session, base_user: User):
    """Test getting user teams."""
    # Create a team and associate it with the user
    team = Team(name="Test Team")
    db_session.add(team)
    db_session.flush()

    user_team = UserTeam(user_id=base_user.id, team_id=team.id)
    db_session.add(user_team)
    db_session.commit()

    service = UserService(db_session)
    result = service.get_user_teams(base_user.id)

    assert len(result) == 1
    assert isinstance(result[0], TeamOutput)
    assert result[0].name == team.name


@pytest.mark.atomic
def test_list_users(db_session: Session, base_user: User):
    """Test listing users."""
    service = UserService(db_session)

    # Create additional user
    other_user = User(ibm_id="other_ibm_id", email="other@example.com", name="Other User")
    db_session.add(other_user)
    db_session.commit()

    result = service.list_users(skip=0, limit=10)

    assert len(result) == 2
    assert all(isinstance(user, UserOutput) for user in result)
    assert any(user.id == base_user.id for user in result)
    assert any(user.id == other_user.id for user in result)


@pytest.mark.atomic
def test_list_users_pagination(db_session: Session, base_user: User):
    """Test users listing with pagination."""
    service = UserService(db_session)

    # Create additional users
    for i in range(5):
        user = User(ibm_id=f"test_ibm_id_{i}", email=f"test{i}@example.com", name=f"Test User {i}")
        db_session.add(user)
    db_session.commit()

    # Test pagination
    page1 = service.list_users(skip=0, limit=3)
    page2 = service.list_users(skip=3, limit=3)

    assert len(page1) == 3
    assert len(page2) > 0
    assert set(u.id for u in page1).isdisjoint(set(u.id for u in page2))


if __name__ == "__main__":
    pytest.main([__file__])
