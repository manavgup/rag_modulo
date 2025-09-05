import pytest
from fastapi import HTTPException
from pydantic import UUID4
from sqlalchemy.orm import Session

from rag_solution.repository.team_repository import TeamRepository
from rag_solution.repository.user_team_repository import UserTeamRepository
from rag_solution.schemas.team_schema import TeamInput, TeamOutput
from rag_solution.services.team_service import TeamService
from rag_solution.services.user_team_service import UserTeamService


@pytest.fixture
def team_input() -> TeamInput:
    """Provides a sample TeamInput object for tests."""
    return TeamInput(name="Test Team", description="A test team")


@pytest.fixture
def team_repository(db_session: Session) -> TeamRepository:
    """Provides a TeamRepository instance."""
    return TeamRepository(db_session)


@pytest.fixture
def user_team_repository(db_session: Session) -> UserTeamRepository:
    """Provides a UserTeamRepository instance."""
    return UserTeamRepository(db_session)


@pytest.fixture
def user_team_service(db_session: Session) -> UserTeamService:
    """Provides a UserTeamService instance."""
    return UserTeamService(db_session)


@pytest.fixture
def team_service(db_session: Session, user_team_service: UserTeamService) -> TeamService:
    """Provides a TeamService instance."""
    return TeamService(db_session, user_team_service)


@pytest.mark.atomic
def test_create_team(team_service: TeamService, team_input: TeamInput) -> None:
    """Tests team creation success."""
    created_team = team_service.create_team(team_input)
    assert isinstance(created_team, TeamOutput)
    assert created_team.name == team_input.name
    assert created_team.description == team_input.description


def test_get_team(team_service: TeamService, team_input: TeamInput) -> None:
    """Tests retrieval of an existing team by its ID."""
    created_team = team_service.create_team(team_input)
    retrieved_team = team_service.get_team_by_id(created_team.id)
    assert retrieved_team.name == created_team.name


def test_get_non_existent_team(team_service: TeamService) -> None:
    """Tests handling of a non-existent team ID."""
    with pytest.raises(HTTPException) as exc_info:
        team_service.get_team_by_id(UUID4("00000000-0000-0000-0000-000000000000"))
    assert exc_info.value.status_code == 404


def test_update_team(team_service: TeamService, team_input: TeamInput) -> None:
    """Tests updating an existing team."""
    created_team = team_service.create_team(team_input)
    updated_data = TeamInput(name="Updated Team", description="Updated description")
    updated_team = team_service.update_team(created_team.id, updated_data)
    assert updated_team.name == "Updated Team"
    assert updated_team.description == "Updated description"


def test_delete_team(team_service: TeamService, team_input: TeamInput) -> None:
    """Tests successful deletion of a team."""
    created_team = team_service.create_team(team_input)
    assert team_service.delete_team(created_team.id)
    with pytest.raises(HTTPException) as exc_info:
        team_service.get_team_by_id(created_team.id)
    assert exc_info.value.status_code == 404
