"""TDD Unit tests for TeamService - RED phase: Tests that describe expected behavior."""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from sqlalchemy.orm import Session

from rag_solution.services.team_service import TeamService
from rag_solution.schemas.team_schema import TeamInput, TeamOutput
from rag_solution.schemas.user_schema import UserOutput
from rag_solution.schemas.user_team_schema import UserTeamOutput
from core.custom_exceptions import NotFoundError


@pytest.mark.unit
class TestTeamServiceTDD:
    """TDD tests for TeamService - following Red-Green-Refactor cycle."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_team_repository(self):
        """Mock team repository."""
        return Mock()

    @pytest.fixture
    def mock_user_team_service(self):
        """Mock user team service."""
        return Mock()

    @pytest.fixture
    def mock_user_service(self):
        """Mock user service."""
        return Mock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance with mocked dependencies."""
        with patch('rag_solution.services.team_service.TeamRepository') as mock_repo_class, \
             patch('rag_solution.services.team_service.UserTeamService') as mock_user_team_class:

            service = TeamService(mock_db)
            service.team_repository = Mock()
            service.user_team_service = Mock()
            service.user_service = Mock()
            return service

    def test_create_team_success_red_phase(self, service):
        """RED: Test successful team creation - will fail initially."""
        team_input = TeamInput(name="Development Team", description="Software development team")
        team_id = uuid4()

        expected_team = TeamOutput(
            id=team_id,
            name="Development Team",
            description="Software development team"
        )

        service.team_repository.create.return_value = expected_team

        # RED PHASE: This should work but might reveal implementation issues
        result = service.create_team(team_input)

        assert result is expected_team
        assert result.name == "Development Team"
        assert result.description == "Software development team"
        service.team_repository.create.assert_called_once_with(team_input)

    def test_create_team_with_duplicate_name_red_phase(self, service):
        """RED: Test team creation with duplicate name - expecting specific error handling."""
        team_input = TeamInput(name="Existing Team", description="This team already exists")

        # Simulate repository raising an error for duplicate name
        service.team_repository.create.side_effect = Exception("UNIQUE constraint failed: teams.name")

        # RED PHASE: Should service handle this gracefully or let exception bubble up?
        # Based on code analysis, it should bubble up - this is the current behavior
        with pytest.raises(Exception) as exc_info:
            service.create_team(team_input)

        assert "UNIQUE constraint failed" in str(exc_info.value)

    def test_get_team_by_id_success_red_phase(self, service):
        """RED: Test successful team retrieval by ID."""
        team_id = uuid4()
        expected_team = TeamOutput(
            id=team_id,
            name="Test Team",
            description="Test team description"
        )

        service.team_repository.get.return_value = expected_team

        result = service.get_team_by_id(team_id)

        assert result is expected_team
        assert result.id == team_id
        service.team_repository.get.assert_called_once_with(team_id)

    def test_get_team_by_id_not_found_red_phase(self, service):
        """RED: Test team retrieval when team not found - should raise NotFoundError."""
        team_id = uuid4()

        # Repository should raise NotFoundError based on code comment
        service.team_repository.get.side_effect = NotFoundError("Team", team_id)

        # This should bubble up to the caller
        with pytest.raises(NotFoundError) as exc_info:
            service.get_team_by_id(team_id)

        assert str(team_id) in str(exc_info.value)
        service.team_repository.get.assert_called_once_with(team_id)

    def test_update_team_success_red_phase(self, service):
        """RED: Test successful team update."""
        team_id = uuid4()
        team_update = TeamInput(name="Updated Team", description="Updated description")

        updated_team = TeamOutput(
            id=team_id,
            name="Updated Team",
            description="Updated description"
        )

        service.team_repository.update.return_value = updated_team

        result = service.update_team(team_id, team_update)

        assert result is updated_team
        assert result.name == "Updated Team"
        service.team_repository.update.assert_called_once_with(team_id, team_update)

    def test_update_team_not_found_red_phase(self, service):
        """RED: Test team update when team not found - should raise NotFoundError."""
        team_id = uuid4()
        team_update = TeamInput(name="Updated Team", description="Updated description")

        service.team_repository.update.side_effect = NotFoundError("Team", team_id)

        with pytest.raises(NotFoundError) as exc_info:
            service.update_team(team_id, team_update)

        assert str(team_id) in str(exc_info.value)
        service.team_repository.update.assert_called_once_with(team_id, team_update)

    def test_delete_team_success_red_phase(self, service):
        """RED: Test successful team deletion."""
        team_id = uuid4()

        # Repository delete should succeed without returning anything
        service.team_repository.delete.return_value = None

        result = service.delete_team(team_id)

        assert result is True
        service.team_repository.delete.assert_called_once_with(team_id)

    def test_delete_team_not_found_red_phase(self, service):
        """RED: Test team deletion when team not found - should raise exception."""
        team_id = uuid4()

        service.team_repository.delete.side_effect = NotFoundError("Team", team_id)

        # Based on code analysis, exception should bubble up (no return False)
        with pytest.raises(NotFoundError):
            service.delete_team(team_id)

        service.team_repository.delete.assert_called_once_with(team_id)

    def test_delete_team_unexpected_error_red_phase(self, service):
        """RED: Test team deletion with unexpected error - should bubble up."""
        team_id = uuid4()

        service.team_repository.delete.side_effect = Exception("Database connection lost")

        # Code shows it re-raises the exception
        with pytest.raises(Exception) as exc_info:
            service.delete_team(team_id)

        assert "Database connection lost" in str(exc_info.value)

    def test_get_team_users_success_red_phase(self, service):
        """RED: Test successful retrieval of team users."""
        team_id = uuid4()
        user_id_1 = uuid4()
        user_id_2 = uuid4()

        # Mock user-team relationships
        user_teams = [
            UserTeamOutput(user_id=user_id_1, team_id=team_id, role="member", joined_at="2024-01-01T00:00:00Z"),
            UserTeamOutput(user_id=user_id_2, team_id=team_id, role="admin", joined_at="2024-01-01T00:00:00Z")
        ]

        # Mock actual users
        users = [
            UserOutput(id=user_id_1, email="user1@example.com", ibm_id="user1", name="User 1", role="user", preferred_provider_id=None, created_at="2024-01-01T00:00:00Z", updated_at="2024-01-01T00:00:00Z"),
            UserOutput(id=user_id_2, email="user2@example.com", ibm_id="user2", name="User 2", role="admin", preferred_provider_id=None, created_at="2024-01-01T00:00:00Z", updated_at="2024-01-01T00:00:00Z")
        ]

        service.user_team_service.get_team_users.return_value = user_teams
        service.user_service.get_user_by_id.side_effect = lambda uid: next(u for u in users if u.id == uid)

        result = service.get_team_users(team_id)

        assert len(result) == 2
        assert result[0].id == user_id_1
        assert result[1].id == user_id_2
        service.user_team_service.get_team_users.assert_called_once_with(team_id)
        assert service.user_service.get_user_by_id.call_count == 2

    def test_get_team_users_no_user_service_red_phase(self, service):
        """RED: Test get team users when no user service provided."""
        team_id = uuid4()

        # Simulate no user service
        service.user_service = None

        result = service.get_team_users(team_id)

        # Should return empty list when no user service
        assert result == []

    def test_get_team_users_user_fetch_fails_red_phase(self, service):
        """RED: Test get team users when individual user fetch fails."""
        team_id = uuid4()
        user_id_1 = uuid4()
        user_id_2 = uuid4()

        user_teams = [
            UserTeamOutput(user_id=user_id_1, team_id=team_id, role="member", joined_at="2024-01-01T00:00:00Z"),
            UserTeamOutput(user_id=user_id_2, team_id=team_id, role="admin", joined_at="2024-01-01T00:00:00Z")
        ]

        good_user = UserOutput(id=user_id_1, email="user1@example.com", ibm_id="user1", name="User 1", role="user", preferred_provider_id=None, created_at="2024-01-01T00:00:00Z", updated_at="2024-01-01T00:00:00Z")

        service.user_team_service.get_team_users.return_value = user_teams

        def mock_get_user(uid):
            if uid == user_id_1:
                return good_user
            else:
                raise NotFoundError("User", uid)

        service.user_service.get_user_by_id.side_effect = mock_get_user

        result = service.get_team_users(team_id)

        # Should continue and return only successful users
        assert len(result) == 1
        assert result[0].id == user_id_1

    def test_add_user_to_team_red_phase(self, service):
        """RED: Test adding user to team."""
        user_id = uuid4()
        team_id = uuid4()

        expected_user_team = UserTeamOutput(
            user_id=user_id,
            team_id=team_id,
            role="member",
            joined_at="2024-01-01T00:00:00Z"
        )

        service.user_team_service.add_user_to_team.return_value = expected_user_team

        result = service.add_user_to_team(user_id, team_id)

        assert result is expected_user_team
        service.user_team_service.add_user_to_team.assert_called_once_with(user_id, team_id)

    def test_remove_user_from_team_red_phase(self, service):
        """RED: Test removing user from team."""
        user_id = uuid4()
        team_id = uuid4()

        service.user_team_service.remove_user_from_team.return_value = True

        result = service.remove_user_from_team(user_id, team_id)

        assert result is True
        service.user_team_service.remove_user_from_team.assert_called_once_with(user_id, team_id)

    def test_list_teams_success_red_phase(self, service):
        """RED: Test successful team listing."""
        teams = [
            TeamOutput(id=uuid4(), name="Team 1", description="First team"),
            TeamOutput(id=uuid4(), name="Team 2", description="Second team"),
            TeamOutput(id=uuid4(), name="Team 3", description="Third team")
        ]

        service.team_repository.list.return_value = teams

        result = service.list_teams(skip=0, limit=100)

        assert result == teams
        assert len(result) == 3
        service.team_repository.list.assert_called_once_with(0, 100)

    def test_list_teams_with_pagination_red_phase(self, service):
        """RED: Test team listing with custom pagination."""
        teams = [
            TeamOutput(id=uuid4(), name="Team 4", description="Fourth team"),
            TeamOutput(id=uuid4(), name="Team 5", description="Fifth team")
        ]

        service.team_repository.list.return_value = teams

        result = service.list_teams(skip=10, limit=20)

        assert result == teams
        service.team_repository.list.assert_called_once_with(10, 20)

    def test_list_teams_error_red_phase(self, service):
        """RED: Test team listing with repository error."""
        service.team_repository.list.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception) as exc_info:
            service.list_teams()

        assert "Database connection failed" in str(exc_info.value)

    def test_service_initialization_with_dependencies_red_phase(self, mock_db):
        """RED: Test service initialization with provided dependencies."""
        mock_user_team_service = Mock()
        mock_user_service = Mock()

        with patch('rag_solution.services.team_service.TeamRepository') as mock_repo_class:
            service = TeamService(mock_db, mock_user_team_service, mock_user_service)

            assert service.user_team_service is mock_user_team_service
            assert service.user_service is mock_user_service
            mock_repo_class.assert_called_once_with(mock_db)

    def test_service_initialization_without_dependencies_red_phase(self, mock_db):
        """RED: Test service initialization without provided dependencies."""
        with patch('rag_solution.services.team_service.TeamRepository') as mock_repo_class, \
             patch('rag_solution.services.team_service.UserTeamService') as mock_user_team_class:

            service = TeamService(mock_db)

            assert service.user_service is None  # Not provided
            mock_repo_class.assert_called_once_with(mock_db)
            mock_user_team_class.assert_called_once_with(mock_db)

    def test_logging_behavior_red_phase(self, service):
        """RED: Test that logging calls are made appropriately."""
        team_id = uuid4()
        team_input = TeamInput(name="Logged Team", description="Testing logging")
        expected_team = TeamOutput(id=team_id, name="Logged Team", description="Testing logging")

        service.team_repository.create.return_value = expected_team

        with patch('rag_solution.services.team_service.logger') as mock_logger:
            service.create_team(team_input)

            # Should log creation start and success
            assert mock_logger.info.call_count == 2
            mock_logger.info.assert_any_call(f"Creating team with input: {team_input}")
            mock_logger.info.assert_any_call(f"Team created successfully: {team_id}")

# RED PHASE COMPLETE: Now let's run these tests to see what fails
# This will guide our GREEN phase implementation fixes
