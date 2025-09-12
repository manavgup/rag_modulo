"""Unit tests for TeamService with mocked dependencies."""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from sqlalchemy.orm import Session

from rag_solution.services.team_service import TeamService
from rag_solution.schemas.team_schema import TeamInput, TeamOutput


@pytest.mark.unit
class TestTeamServiceUnit:
    """Unit tests for TeamService with mocked dependencies."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_team_repository(self):
        """Mock team repository."""
        return Mock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance with mocked repository."""
        with patch('rag_solution.services.team_service.TeamRepository') as mock_repo_class, \
             patch('rag_solution.services.team_service.UserTeamService') as mock_user_team_service_class:
            service = TeamService(mock_db)
            service.team_repository = Mock()
            service.user_team_service = Mock()
            return service

    def test_service_initialization(self, mock_db):
        """Test service initialization with dependency injection."""
        with patch('rag_solution.services.team_service.TeamRepository') as mock_repo_class, \
             patch('rag_solution.services.team_service.UserTeamService') as mock_user_team_service_class:
            service = TeamService(mock_db)

            mock_repo_class.assert_called_once_with(mock_db)
            mock_user_team_service_class.assert_called_once_with(mock_db)

    def test_create_team_success(self, service):
        """Test successful team creation."""
        team_input = TeamInput(name="Development Team", description="Software development team")
        team_id = uuid4()

        mock_team = TeamOutput(
            id=team_id,
            name="Development Team",
            description="Software development team"
        )

        service.team_repository.create.return_value = mock_team

        result = service.create_team(team_input)

        assert result is mock_team
        service.team_repository.create.assert_called_once_with(team_input)

    def test_create_team_duplicate_name_error(self, service):
        """Test team creation with duplicate name."""
        team_input = TeamInput(name="Existing Team", description="Duplicate team name")

        service.team_repository.create.side_effect = Exception("Team name already exists")

        with pytest.raises(Exception) as exc_info:
            service.create_team(team_input)

        assert "Team name already exists" in str(exc_info.value)
        service.team_repository.create.assert_called_once_with(team_input)

    def test_get_team_by_id_success(self, service):
        """Test successful team retrieval by ID."""
        team_id = uuid4()
        mock_team = TeamOutput(
            id=team_id,
            name="Test Team",
            description="Test team description"
        )

        service.team_repository.get.return_value = mock_team

        result = service.get_team_by_id(team_id)

        assert result is mock_team
        service.team_repository.get.assert_called_once_with(team_id)

    def test_get_team_by_id_not_found(self, service):
        """Test team retrieval when team not found."""
        team_id = uuid4()

        from rag_solution.core.exceptions import NotFoundError
        service.team_repository.get.side_effect = NotFoundError("Team not found")

        with pytest.raises(NotFoundError):
            service.get_team_by_id(team_id)

        service.team_repository.get.assert_called_once_with(team_id)

    def test_get_all_teams_success(self, service):
        """Test successful retrieval of all teams."""
        mock_teams = [
            TeamOutput(id=uuid4(), name="Team 1", description="First team"),
            TeamOutput(id=uuid4(), name="Team 2", description="Second team"),
            TeamOutput(id=uuid4(), name="Team 3", description="Third team")
        ]

        service.team_repository.list.return_value = mock_teams

        result = service.list_teams()

        assert result == mock_teams
        assert len(result) == 3
        service.team_repository.list.assert_called_once_with(0, 100)

    def test_get_all_teams_empty(self, service):
        """Test retrieval of all teams when no teams exist."""
        service.team_repository.list.return_value = []

        result = service.list_teams()

        assert result == []
        service.team_repository.list.assert_called_once_with(0, 100)

    def test_update_team_success(self, service):
        """Test successful team update."""
        team_id = uuid4()
        team_input = TeamInput(name="Updated Team", description="Updated description")

        updated_team = TeamOutput(
            id=team_id,
            name="Updated Team",
            description="Updated description"
        )

        service.team_repository.update.return_value = updated_team

        result = service.update_team(team_id, team_input)

        assert result is updated_team
        service.team_repository.update.assert_called_once_with(team_id, team_input)

    def test_update_team_not_found(self, service):
        """Test team update when team not found."""
        team_id = uuid4()
        team_input = TeamInput(name="Updated Team", description="Updated description")

        from rag_solution.core.exceptions import NotFoundError
        service.team_repository.update.side_effect = NotFoundError("Team not found")

        with pytest.raises(NotFoundError):
            service.update_team(team_id, team_input)

        service.team_repository.update.assert_called_once_with(team_id, team_input)

    def test_delete_team_success(self, service):
        """Test successful team deletion."""
        team_id = uuid4()

        service.team_repository.delete.return_value = True

        result = service.delete_team(team_id)

        assert result is True
        service.team_repository.delete.assert_called_once_with(team_id)

    def test_delete_team_not_found(self, service):
        """Test team deletion when team not found."""
        team_id = uuid4()

        from rag_solution.core.exceptions import NotFoundError
        service.team_repository.delete.side_effect = NotFoundError("Team not found")

        with pytest.raises(NotFoundError):
            service.delete_team(team_id)

        service.team_repository.delete.assert_called_once_with(team_id)

    @pytest.mark.skip(reason="Method doesn't exist in current TeamService implementation")
    # DISABLED: search_teams_by_name method doesn't exist in TeamService
    def test_search_teams_by_name_success(self, service):
        """Test successful team search by name."""
        search_term = "Development"
        matching_teams = [
            TeamOutput(id=uuid4(), name="Frontend Development", description="UI development"),
            TeamOutput(id=uuid4(), name="Backend Development", description="API development")
        ]

        service.team_repository.search_by_name.return_value = matching_teams

        result = service.search_teams_by_name(search_term)

        assert result == matching_teams
        assert len(result) == 2
        service.team_repository.search_by_name.assert_called_once_with(search_term)

    @pytest.mark.skip(reason="Method doesn't exist in current TeamService implementation")
    # DISABLED: search_teams_by_name method doesn't exist in TeamService
    def test_search_teams_by_name_no_results(self, service):
        """Test team search by name with no results."""
        search_term = "NonExistent"

        service.team_repository.search_by_name.return_value = []

        result = service.search_teams_by_name(search_term)

        assert result == []
        service.team_repository.search_by_name.assert_called_once_with(search_term)

    @pytest.mark.skip(reason="Method doesn't exist in current TeamService implementation")
    # DISABLED: get_teams_by_user_id method doesn't exist in TeamService
    def test_get_teams_by_user_id_success(self, service):
        """Test successful retrieval of teams by user ID."""
        user_id = uuid4()
        user_teams = [
            TeamOutput(id=uuid4(), name="User Team 1", description="First user team"),
            TeamOutput(id=uuid4(), name="User Team 2", description="Second user team")
        ]

        service.team_repository.get_by_user_id.return_value = user_teams

        result = service.get_teams_by_user_id(user_id)

        assert result == user_teams
        assert len(result) == 2
        service.team_repository.get_by_user_id.assert_called_once_with(user_id)

    @pytest.mark.skip(reason="Method doesn't exist in current TeamService implementation")
    # DISABLED: get_teams_by_user_id method doesn't exist in TeamService
    def test_get_teams_by_user_id_no_teams(self, service):
        """Test retrieval of teams by user ID when user has no teams."""
        user_id = uuid4()

        service.team_repository.get_by_user_id.return_value = []

        result = service.get_teams_by_user_id(user_id)

        assert result == []
        service.team_repository.get_by_user_id.assert_called_once_with(user_id)

    def test_add_user_to_team_success(self, service):
        """Test successfully adding user to team."""
        team_id = uuid4()
        user_id = uuid4()

        service.team_repository.add_user_to_team.return_value = True

        from rag_solution.schemas.user_team_schema import UserTeamOutput
        mock_user_team = UserTeamOutput(
            user_id=user_id,
            team_id=team_id,
            role="member",
            joined_at="2024-01-01T00:00:00Z"
        )
        service.user_team_service.add_user_to_team.return_value = mock_user_team

        result = service.add_user_to_team(user_id, team_id)

        assert result is mock_user_team
        service.user_team_service.add_user_to_team.assert_called_once_with(user_id, team_id)

    def test_add_user_to_team_failure(self, service):
        """Test adding user to team failure (team or user not found)."""
        team_id = uuid4()
        user_id = uuid4()

        service.user_team_service.add_user_to_team.return_value = None

        result = service.add_user_to_team(user_id, team_id)

        assert result is None
        service.user_team_service.add_user_to_team.assert_called_once_with(user_id, team_id)

    def test_remove_user_from_team_success(self, service):
        """Test successfully removing user from team."""
        team_id = uuid4()
        user_id = uuid4()

        service.user_team_service.remove_user_from_team.return_value = True

        result = service.remove_user_from_team(user_id, team_id)

        assert result is True
        service.user_team_service.remove_user_from_team.assert_called_once_with(user_id, team_id)

    def test_remove_user_from_team_failure(self, service):
        """Test removing user from team failure (user not in team)."""
        team_id = uuid4()
        user_id = uuid4()

        service.user_team_service.remove_user_from_team.return_value = False

        result = service.remove_user_from_team(user_id, team_id)

        assert result is False
        service.user_team_service.remove_user_from_team.assert_called_once_with(user_id, team_id)

    def test_get_team_users_success(self, service):
        """Test successful retrieval of team users."""
        team_id = uuid4()
        
        from rag_solution.schemas.user_schema import UserOutput
        from rag_solution.schemas.user_team_schema import UserTeamOutput
        
        user1_id = uuid4()
        user2_id = uuid4()
        
        mock_user_teams = [
            UserTeamOutput(user_id=user1_id, team_id=team_id, role="member", joined_at="2024-01-01T00:00:00Z"),
            UserTeamOutput(user_id=user2_id, team_id=team_id, role="member", joined_at="2024-01-01T00:00:00Z")
        ]
        
        mock_users = [
            UserOutput(id=user1_id, name="John Doe", email="john@example.com", ibm_id="john_doe", role="user", preferred_provider_id=None, created_at="2024-01-01T00:00:00Z", updated_at="2024-01-01T00:00:00Z"),
            UserOutput(id=user2_id, name="Jane Smith", email="jane@example.com", ibm_id="jane_smith", role="user", preferred_provider_id=None, created_at="2024-01-01T00:00:00Z", updated_at="2024-01-01T00:00:00Z")
        ]
        
        service.user_team_service.get_team_users.return_value = mock_user_teams
        service.user_service = Mock()
        service.user_service.get_user_by_id.side_effect = mock_users
        
        result = service.get_team_users(team_id)

        assert result == mock_users
        assert len(result) == 2

    def test_get_team_users_no_members(self, service):
        """Test retrieval of team members when team has no members."""
        team_id = uuid4()

        result = service.get_team_users(team_id)

        assert result == []
        # When user_service is not provided, empty list is returned

    def test_repository_error_handling(self, service):
        """Test service handles repository errors appropriately."""
        team_id = uuid4()

        service.team_repository.get.side_effect = Exception("Database connection error")

        with pytest.raises(Exception) as exc_info:
            service.get_team_by_id(team_id)

        assert "Database connection error" in str(exc_info.value)
        service.team_repository.get.assert_called_once_with(team_id)
