"""Team management fixtures for pytest."""

import pytest

from rag_solution.schemas.team_schema import TeamInput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.services.team_service import TeamService


@pytest.fixture(scope="session")
def base_team(team_service: TeamService):
    """Create a base team using service."""
    team_input = TeamInput(name="Test Team", description="A test team")
    return team_service.create_team(team_input)


@pytest.fixture(scope="session")
def user_team(team_service: TeamService, base_team, base_user: UserOutput):
    """Add user to team using service."""
    team_service.add_user_to_team(base_user.id, base_team.id)
    return base_team


@pytest.fixture(scope="session")
def base_user_team(team_service: TeamService, base_team, base_user: UserOutput):
    """Add base user to team using service."""
    team_service.add_user_to_team(base_user.id, base_team.id)
    return base_team
