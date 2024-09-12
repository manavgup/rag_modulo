from uuid import UUID

import pytest
from fastapi import HTTPException
from backend.rag_solution.repository.team_repository import TeamRepository
from backend.rag_solution.repository.user_team_repository import UserTeamRepository
from backend.rag_solution.schemas.team_schema import TeamInput, TeamOutput
from backend.rag_solution.services.team_service import TeamService
from backend.rag_solution.services.user_team_service import UserTeamService


@pytest.fixture
def team_input():
    return TeamInput(
        name="Test Team",
        description="A test team"
    )

@pytest.fixture
def team_repository(db_session):
    return TeamRepository(db_session)

@pytest.fixture
def user_team_repository(db_session):
    return UserTeamRepository(db_session)

@pytest.fixture
def user_team_service(user_team_repository):
    return UserTeamService(user_team_repository)

@pytest.fixture
def team_service(db_session, user_team_service):
    return TeamService(db_session, user_team_service)

def test_create_team(team_service, team_input):
    created_team = team_service.create_team(team_input)
    assert isinstance(created_team, TeamOutput)
    assert created_team.name == team_input.name
    assert created_team.description == team_input.description

def test_get_team(team_service, team_input):
    created_team = team_service.create_team(team_input)
    retrieved_team = team_service.get_team_by_id(created_team.id)
    assert retrieved_team.name == created_team.name

def test_get_non_existent_team(team_service):
    with pytest.raises(HTTPException) as exc_info:
        team_service.get_team_by_id(UUID('00000000-0000-0000-0000-000000000000'))
    assert exc_info.value.status_code == 404

def test_update_team(team_service, team_input):
    created_team = team_service.create_team(team_input)
    updated_data = TeamInput(name="Updated Team", description="Updated description")
    updated_team = team_service.update_team(created_team.id, updated_data)
    assert updated_team.name == "Updated Team"
    assert updated_team.description == "Updated description"

def test_delete_team(team_service, team_input):
    created_team = team_service.create_team(team_input)
    assert team_service.delete_team(created_team.id) is True
    with pytest.raises(HTTPException) as exc_info:
        team_service.get_team_by_id(created_team.id)
    assert exc_info.value.status_code == 404
