import logging
from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from backend.rag_solution.repository.user_repository import UserRepository
from backend.rag_solution.repository.user_team_repository import UserTeamRepository
from backend.rag_solution.schemas.user_schema import UserInput, UserOutput
from backend.rag_solution.services.user_service import UserService
from backend.rag_solution.services.user_team_service import UserTeamService

logger = logging.getLogger(__name__)

@pytest.fixture
def user_input():
    return UserInput(
        ibm_id="test_ibm_id",
        email="test@example.com",
        name="Test User"
    )
@pytest.fixture
def user_team_repository(db_session):
    return UserTeamRepository(db_session)

@pytest.fixture
def user_repository(db_session):
    return UserRepository(db_session)

@pytest.fixture
def user_team_service(user_team_repository):
    return UserTeamService(user_team_repository)

@pytest.fixture
def user_service(db_session, user_team_service):
    return UserService(db_session, user_team_service)

def test_create_user(user_service: UserService):
    user_input = UserInput(ibm_id="test_ibm_id", email="test@example.com", name="Test User")
    user_output = user_service.create_user(user_input)

    assert user_output.ibm_id == user_input.ibm_id
    assert user_output.email == user_input.email
    assert user_output.name == user_input.name


def test_get_user(user_service, user_input):
    created_user = user_service.create_user(user_input)
    retrieved_user = user_service.get_user_by_id(created_user.id)
    assert isinstance(retrieved_user, UserOutput)
    assert retrieved_user.id == created_user.id


def test_get_non_existent_user(user_service):
    with pytest.raises(HTTPException) as exc_info:
        user_service.get_user_by_id(UUID('00000000-0000-0000-0000-000000000000'))
    assert exc_info.value.status_code == 404


def test_update_user(user_service, user_input):
    created_user = user_service.create_user(user_input)
    updated_input = UserInput(ibm_id="updated_ibm_id", email="updated@example.com", name="Updated User")
    updated_user = user_service.update_user(created_user.id, updated_input)

    assert updated_user.ibm_id == updated_input.ibm_id
    assert updated_user.email == updated_input.email
    assert updated_user.name == updated_input.name


def test_delete_user(user_service, user_input):
    created_user = user_service.create_user(user_input)
    assert user_service.delete_user(created_user.id) is True
    with pytest.raises(HTTPException) as exc_info:
        user_service.get_user_by_id(created_user.id)
    assert exc_info.value.status_code == 404


def test_get_user_by_ibm_id(user_service, user_input):
    created_user = user_service.create_user(user_input)
    retrieved_user = user_service.get_user_by_ibm_id(created_user.ibm_id)
    assert isinstance(retrieved_user, UserOutput)
    assert retrieved_user.ibm_id == created_user.ibm_id


def test_get_non_existent_user_by_ibm_id(user_service):
    with pytest.raises(HTTPException) as exc_info:
        user_service.get_user_by_ibm_id("non_existent_ibm_id")
    assert exc_info.value.status_code == 404


def test_update_non_existent_user(user_service, user_input):
    with pytest.raises(HTTPException) as exc_info:
        user_service.update_user(UUID('00000000-0000-0000-0000-000000000000'), user_input)
    assert exc_info.value.status_code == 404


def test_delete_non_existent_user(user_service):
    with pytest.raises(HTTPException) as exc_info:
        user_service.delete_user(UUID('00000000-0000-0000-0000-000000000000'))
    assert exc_info.value.status_code == 404

@pytest.mark.parametrize("invalid_input, error_message", [
    ({"ibm_id": "", "email": "test@example.com", "name": "Test User"}, "ibm_id"),
    ({"ibm_id": "test_ibm_id", "email": "invalid_email", "name": "Test User"}, "email"),
    ({"ibm_id": "test_ibm_id", "email": "test@example.com", "name": ""}, "name"),
])
def test_create_user_with_invalid_input(user_service, invalid_input, error_message):
    with pytest.raises(ValidationError) as exc_info:
        UserInput(**invalid_input)
    assert error_message in str(exc_info.value)


def test_create_duplicate_user(user_service, user_input):
    user_service.create_user(user_input)
    with pytest.raises(Exception):  # Assuming your system doesn't allow duplicate IBM IDs
        user_service.create_user(user_input)


def test_update_user_email(user_service, user_input):
    created_user = user_service.create_user(user_input)
    updated_data = UserInput(ibm_id=created_user.ibm_id, email="newemail@example.com", name=created_user.name)
    updated_user = user_service.update_user(created_user.id, updated_data)
    assert updated_user.email == "newemail@example.com"


def test_update_user_name(user_service, user_input):
    created_user = user_service.create_user(user_input)
    updated_data = UserInput(ibm_id=created_user.ibm_id, email=created_user.email, name="New Name")
    updated_user = user_service.update_user(created_user.id, updated_data)
    assert updated_user.name == "New Name"
