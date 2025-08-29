"""Integration tests for TeamService."""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from rag_solution.schemas.team_schema import TeamInput, TeamOutput
from rag_solution.schemas.user_schema import UserOutput


# -------------------------------------------
# 🔧 Test Fixtures
# -------------------------------------------
@pytest.fixture
def test_team_input() -> TeamInput:
    """Create a sample team input."""
    return TeamInput(name="Test Team", description="This is a test team", is_private=False)


# -------------------------------------------
# 🧪 Team Creation Tests
# -------------------------------------------
@pytest.mark.atomic
def test_create_team_success(team_service, test_team_input: TeamInput):
    """Test successful team creation."""
    result = team_service.create_team(test_team_input)

    assert isinstance(result, TeamOutput)
    assert result.name == test_team_input.name
    assert result.description == test_team_input.description


@pytest.mark.atomic
def test_create_team_duplicate_name(team_service, base_team, test_team_input: TeamInput):
    """Test team creation with duplicate name."""
    with pytest.raises(HTTPException) as exc_info:
        team_service.create_team(test_team_input)
    assert exc_info.value.status_code == 400
    assert "Team name already exists" in str(exc_info.value.detail)


# -------------------------------------------
# 🧪 Team Retrieval Tests
# -------------------------------------------
@pytest.mark.atomic
def test_get_team_by_id_success(team_service, base_team):
    """Test successful team retrieval."""
    result = team_service.get_team_by_id(base_team.id)

    assert isinstance(result, TeamOutput)
    assert result.id == base_team.id
    assert result.name == base_team.name


@pytest.mark.atomic
def test_get_team_by_id_not_found(team_service):
    """Test team retrieval when not found."""
    with pytest.raises(HTTPException) as exc_info:
        team_service.get_team_by_id(uuid4())
    assert exc_info.value.status_code == 404
    assert "Team not found" in str(exc_info.value.detail)


# -------------------------------------------
# 🧪 Team Update Tests
# -------------------------------------------
@pytest.mark.atomic
def test_update_team_success(team_service, base_team):
    """Test successful team update."""
    update_input = TeamInput(name="Updated Team", description="Updated description", is_private=True)

    result = team_service.update_team(base_team.id, update_input)

    assert isinstance(result, TeamOutput)
    assert result.name == update_input.name
    assert result.description == update_input.description
    assert result.is_private == update_input.is_private


@pytest.mark.atomic
def test_update_team_not_found(team_service, test_team_input: TeamInput):
    """Test team update when not found."""
    with pytest.raises(HTTPException) as exc_info:
        team_service.update_team(uuid4(), test_team_input)
    assert exc_info.value.status_code == 404
    assert "Team not found" in str(exc_info.value.detail)


# -------------------------------------------
# 🧪 Team Deletion Tests
# -------------------------------------------
@pytest.mark.atomic
def test_delete_team_success(team_service, base_team):
    """Test successful team deletion."""
    result = team_service.delete_team(base_team.id)

    assert result is True
    with pytest.raises(HTTPException) as exc_info:
        team_service.get_team_by_id(base_team.id)
    assert exc_info.value.status_code == 404


@pytest.mark.atomic
def test_delete_team_not_found(team_service):
    """Test team deletion when not found."""
    result = team_service.delete_team(uuid4())
    assert result is False


# -------------------------------------------
# 🧪 Team Membership Tests
# -------------------------------------------
@pytest.mark.atomic
def test_get_team_users(team_service, base_team, base_user: UserOutput):
    """Test retrieving team users."""
    # Add user to team first
    team_service.add_user_to_team(base_user.id, base_team.id)
    result = team_service.get_team_users(base_team.id)

    assert len(result) == 1
    assert isinstance(result[0], UserOutput)
    assert result[0].id == base_user.id


@pytest.mark.atomic
def test_add_user_to_team(team_service, base_team, base_user: UserOutput):
    """Test adding user to team."""
    result = team_service.add_user_to_team(base_user.id, base_team.id)

    assert result is True

    # Verify user was added
    team_users = team_service.get_team_users(base_team.id)
    assert any(u.id == base_user.id for u in team_users)


@pytest.mark.atomic
def test_remove_user_from_team(team_service, base_team, base_user: UserOutput):
    """Test removing user from team."""
    # First add user to team
    team_service.add_user_to_team(base_user.id, base_team.id)

    # Then remove user
    result = team_service.remove_user_from_team(base_user.id, base_team.id)

    assert result is True

    # Verify user was removed
    team_users = team_service.get_team_users(base_team.id)
    assert not any(u.id == base_user.id for u in team_users)


# -------------------------------------------
# 🧪 Team Listing Tests
# -------------------------------------------
@pytest.mark.atomic
def test_list_teams(team_service, base_team):
    """Test listing teams."""
    result = team_service.list_teams(skip=0, limit=10)

    assert len(result) > 0
    assert isinstance(result[0], TeamOutput)
    assert any(team.id == base_team.id for team in result)


@pytest.mark.atomic
def test_list_teams_pagination(team_service, base_team):
    """Test teams listing with pagination."""
    # Create additional teams
    for i in range(5):
        team_service.create_team(TeamInput(name=f"Test Team {i}", description=f"Description {i}", is_private=False))

    # Test pagination
    page1 = team_service.list_teams(skip=0, limit=3)
    page2 = team_service.list_teams(skip=3, limit=3)

    assert len(page1) == 3
    assert len(page2) > 0
    assert set(t.id for t in page1).isdisjoint(set(t.id for t in page2))


if __name__ == "__main__":
    pytest.main([__file__])
