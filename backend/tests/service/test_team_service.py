"""Integration tests for TeamService."""

import pytest
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from fastapi import HTTPException

from rag_solution.services.team_service import TeamService
from rag_solution.services.user_team_service import UserTeamService
from rag_solution.schemas.team_schema import TeamInput, TeamOutput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.models.team import Team
from rag_solution.models.user import User
from rag_solution.models.user_team import UserTeam

@pytest.fixture
def test_team_input() -> TeamInput:
    """Create a sample team input."""
    return TeamInput(
        name="Test Team",
        description="This is a test team",
        is_private=False
    )

@pytest.fixture
def test_team(db_session: Session, test_team_input: TeamInput) -> Team:
    """Create a test team in the database."""
    team = Team(
        name=test_team_input.name,
        description=test_team_input.description,
        is_private=test_team_input.is_private
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team

@pytest.mark.atomic
def test_create_team_success(
    db_session: Session,
    test_team_input: TeamInput
):
    """Test successful team creation."""
    service = TeamService(db_session)
    
    result = service.create_team(test_team_input)
    
    assert isinstance(result, TeamOutput)
    assert result.name == test_team_input.name
    assert result.description == test_team_input.description
    assert result.is_private == test_team_input.is_private

@pytest.mark.atomic
def test_create_team_duplicate_name(
    db_session: Session,
    test_team: Team,
    test_team_input: TeamInput
):
    """Test team creation with duplicate name."""
    service = TeamService(db_session)
    
    with pytest.raises(HTTPException) as exc_info:
        service.create_team(test_team_input)
    assert exc_info.value.status_code == 400
    assert "Team name already exists" in str(exc_info.value.detail)

@pytest.mark.atomic
def test_get_team_by_id_success(
    db_session: Session,
    test_team: Team
):
    """Test successful team retrieval."""
    service = TeamService(db_session)
    
    result = service.get_team_by_id(test_team.id)
    
    assert isinstance(result, TeamOutput)
    assert result.id == test_team.id
    assert result.name == test_team.name

@pytest.mark.atomic
def test_get_team_by_id_not_found(db_session: Session):
    """Test team retrieval when not found."""
    service = TeamService(db_session)
    
    with pytest.raises(HTTPException) as exc_info:
        service.get_team_by_id(uuid4())
    assert exc_info.value.status_code == 404
    assert "Team not found" in str(exc_info.value.detail)

@pytest.mark.atomic
def test_update_team_success(
    db_session: Session,
    test_team: Team
):
    """Test successful team update."""
    service = TeamService(db_session)
    update_input = TeamInput(
        name="Updated Team",
        description="Updated description",
        is_private=True
    )
    
    result = service.update_team(test_team.id, update_input)
    
    assert isinstance(result, TeamOutput)
    assert result.name == update_input.name
    assert result.description == update_input.description
    assert result.is_private == update_input.is_private

@pytest.mark.atomic
def test_update_team_not_found(
    db_session: Session,
    test_team_input: TeamInput
):
    """Test team update when not found."""
    service = TeamService(db_session)
    
    with pytest.raises(HTTPException) as exc_info:
        service.update_team(uuid4(), test_team_input)
    assert exc_info.value.status_code == 404
    assert "Team not found" in str(exc_info.value.detail)

@pytest.mark.atomic
def test_delete_team_success(
    db_session: Session,
    test_team: Team
):
    """Test successful team deletion."""
    service = TeamService(db_session)
    
    result = service.delete_team(test_team.id)
    
    assert result is True
    # Verify team is deleted
    assert db_session.query(Team).filter_by(id=test_team.id).first() is None

@pytest.mark.atomic
def test_delete_team_not_found(db_session: Session):
    """Test team deletion when not found."""
    service = TeamService(db_session)
    
    result = service.delete_team(uuid4())
    
    assert result is False

@pytest.mark.atomic
def test_get_team_users(
    db_session: Session,
    test_team: Team,
    base_user: User
):
    """Test retrieving team users."""
    # Add user to team
    user_team = UserTeam(user_id=base_user.id, team_id=test_team.id)
    db_session.add(user_team)
    db_session.commit()
    
    service = TeamService(db_session)
    result = service.get_team_users(test_team.id)
    
    assert len(result) == 1
    assert isinstance(result[0], UserOutput)
    assert result[0].id == base_user.id

@pytest.mark.atomic
def test_add_user_to_team(
    db_session: Session,
    test_team: Team,
    base_user: User
):
    """Test adding user to team."""
    service = TeamService(db_session)
    
    result = service.add_user_to_team(base_user.id, test_team.id)
    
    assert result is True
    # Verify relationship exists
    user_team = db_session.query(UserTeam).filter_by(
        user_id=base_user.id,
        team_id=test_team.id
    ).first()
    assert user_team is not None

@pytest.mark.atomic
def test_remove_user_from_team(
    db_session: Session,
    test_team: Team,
    base_user: User
):
    """Test removing user from team."""
    # First add user to team
    user_team = UserTeam(user_id=base_user.id, team_id=test_team.id)
    db_session.add(user_team)
    db_session.commit()
    
    service = TeamService(db_session)
    result = service.remove_user_from_team(base_user.id, test_team.id)
    
    assert result is True
    # Verify relationship is removed
    user_team = db_session.query(UserTeam).filter_by(
        user_id=base_user.id,
        team_id=test_team.id
    ).first()
    assert user_team is None

@pytest.mark.atomic
def test_list_teams(
    db_session: Session,
    test_team: Team
):
    """Test listing teams."""
    service = TeamService(db_session)
    
    result = service.list_teams(skip=0, limit=10)
    
    assert len(result) > 0
    assert isinstance(result[0], TeamOutput)
    assert any(team.id == test_team.id for team in result)

@pytest.mark.atomic
def test_list_teams_pagination(
    db_session: Session,
    test_team: Team
):
    """Test teams listing with pagination."""
    service = TeamService(db_session)
    
    # Create additional teams
    for i in range(5):
        team = Team(
            name=f"Test Team {i}",
            description=f"Description {i}",
            is_private=False
        )
        db_session.add(team)
    db_session.commit()
    
    # Test pagination
    page1 = service.list_teams(skip=0, limit=3)
    page2 = service.list_teams(skip=3, limit=3)
    
    assert len(page1) == 3
    assert len(page2) > 0
    assert set(t.id for t in page1).isdisjoint(set(t.id for t in page2))

if __name__ == "__main__":
    pytest.main([__file__])
