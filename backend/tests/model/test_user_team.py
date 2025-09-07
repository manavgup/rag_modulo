from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from pydantic import UUID4

from rag_solution.repository.user_team_repository import UserTeamRepository
from rag_solution.schemas.team_schema import TeamInput
from rag_solution.schemas.user_schema import UserInput
from rag_solution.services.team_service import TeamService
from rag_solution.services.user_service import UserService
from rag_solution.services.user_team_service import UserTeamService


@pytest.fixture
def user_team_repository(db_session: Mock) -> UserTeamRepository:
    return UserTeamRepository(db_session)


@pytest.fixture
def user_team_service(db_session: Mock) -> UserTeamService:
    return UserTeamService(db_session)


@pytest.fixture
def user_service(db_session: Mock) -> UserService:
    return UserService(db_session)


@pytest.fixture
def team_service(db_session: Mock, user_team_service: UserTeamService) -> TeamService:
    return TeamService(db_session, user_team_service)


def test_add_user_to_team(user_team_service: UserTeamService, user_service: UserService, team_service: TeamService) -> None:
    user = user_service.create_user(UserInput(ibm_id="test_ibm_id", email="test@example.com", name="Test User"))
    team = team_service.create_team(TeamInput(name="Test Team"))

    result = user_team_service.add_user_to_team(user.id, team.id)
    assert result is not None

    user_teams = user_team_service.get_user_teams(user.id)
    assert len(user_teams) == 1
    assert user_teams[0].team_id == team.id


def test_remove_user_from_team(user_team_service: UserTeamService, user_service: UserService, team_service: TeamService) -> None:
    user = user_service.create_user(UserInput(ibm_id="test_ibm_id", email="test@example.com", name="Test User"))
    team = team_service.create_team(TeamInput(name="Test Team"))
    user_team_service.add_user_to_team(user.id, team.id)

    result = user_team_service.remove_user_from_team(user.id, team.id)
    assert result is True

    user_teams = user_team_service.get_user_teams(user.id)
    assert len(user_teams) == 0


def test_get_user_teams(user_team_service: UserTeamService, user_service: UserService, team_service: TeamService) -> None:
    user = user_service.create_user(UserInput(ibm_id="test_ibm_id", email="test@example.com", name="Test User"))
    team1 = team_service.create_team(TeamInput(name="Test Team 1"))
    team2 = team_service.create_team(TeamInput(name="Test Team 2"))

    user_team_service.add_user_to_team(user.id, team1.id)
    user_team_service.add_user_to_team(user.id, team2.id)

    user_teams = user_team_service.get_user_teams(user.id)
    assert len(user_teams) == 2
    assert {team1.id, team2.id} == {user_team.team_id for user_team in user_teams}


def test_get_team_users(user_team_service: UserTeamService, user_service: UserService, team_service: TeamService) -> None:
    user1 = user_service.create_user(UserInput(ibm_id="test_ibm_id1", email="test1@example.com", name="Test User 1"))
    user2 = user_service.create_user(UserInput(ibm_id="test_ibm_id2", email="test2@example.com", name="Test User 2"))
    team = team_service.create_team(TeamInput(name="Test Team"))

    user_team_service.add_user_to_team(user1.id, team.id)
    user_team_service.add_user_to_team(user2.id, team.id)

    team_users = user_team_service.get_team_users(team.id)
    assert len(team_users) == 2
    assert {user1.id, user2.id} == {user_team.user_id for user_team in team_users}


def test_add_user_to_nonexistent_team(user_team_service: UserTeamService, user_service: UserService) -> None:
    user = user_service.create_user(UserInput(ibm_id="test_ibm_id", email="test@example.com", name="Test User"))
    with pytest.raises(HTTPException) as exc_info:
        user_team_service.add_user_to_team(user.id, UUID4("00000000-0000-0000-0000-000000000000"))
    assert exc_info.value.status_code == 404


def test_remove_user_from_nonexistent_team(user_team_service: UserTeamService, user_service: UserService) -> None:
    user = user_service.create_user(UserInput(ibm_id="test_ibm_id", email="test@example.com", name="Test User"))
    with pytest.raises(HTTPException) as exc_info:
        user_team_service.remove_user_from_team(user.id, UUID4("00000000-0000-0000-0000-000000000000"))
    assert exc_info.value.status_code == 404


def test_get_teams_for_nonexistent_user(user_team_service: UserTeamService) -> None:
    teams = user_team_service.get_user_teams(UUID4("00000000-0000-0000-0000-000000000000"))
    assert len(teams) == 0


def test_get_users_for_nonexistent_team(user_team_service: UserTeamService) -> None:
    users = user_team_service.get_team_users(UUID4("00000000-0000-0000-0000-000000000000"))
    assert len(users) == 0
