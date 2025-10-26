"""Unit tests for the TeamService, covering business logic and interactions.

These tests follow a TDD approach, starting with RED phase tests that define
the expected behavior and will fail until the implementation is complete.
"""

from unittest.mock import Mock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from backend.core.config import Settings
from backend.core.custom_exceptions import DuplicateEntryError, NotFoundError, ValidationError
from backend.rag_solution.schemas.team_schema import TeamInput, TeamOutput
from backend.rag_solution.services.user_service import UserService
from backend.rag_solution.services.team_service import TeamService


@pytest.mark.unit
class TestTeamServiceTDD:
    """TDD tests for TeamService - RED phase."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Mock settings."""
        return Mock(spec=Settings)

    @pytest.fixture
    def service(self, mock_db, mock_settings) -> TeamService:
        """Create a TeamService instance with mocked dependencies."""
        service = TeamService(mock_db, mock_settings)
        service.team_repository = MagicMock()
        service.team_repository.db = mock_db  # Add the missing 'db' attribute
        service.user_team_service = MagicMock()
        service.user_service = MagicMock()
        return service

    def test_service_initialization_red_phase(self, service, mock_db):
        """RED: Test service initialization."""
        assert service.team_repository.db is mock_db

    def test_service_initialization_with_user_service_red_phase(self, mock_db, mock_settings):
        """RED: Test service initialization with user_service."""
        user_service = Mock(spec=UserService)
        service = TeamService(mock_db, mock_settings, user_service=user_service)
        assert service.user_service is user_service

    def test_create_team_success_red_phase(self, service):
        """RED: Test successful team creation."""
        team_input = TeamInput(name="New Team", description="A new team")
        team_id = uuid4()

        service.team_repository.create.return_value = TeamOutput(
            id=team_id, name=team_input.name, description=team_input.description
        )

        result = service.create_team(team_input)

        assert isinstance(result, TeamOutput)
        assert result.name == team_input.name
        service.team_repository.create.assert_called_once_with(team_input)

    def test_create_team_duplicate_name_red_phase(self, service):
        """RED: Test team creation with a duplicate name."""
        team_input = TeamInput(name="Existing Team", description="A new team")

        # Mock repository to indicate duplicate name
        service.team_repository.create.side_effect = DuplicateEntryError("team_name", "Team with name='Existing Team' already exists")

        with pytest.raises(DuplicateEntryError) as exc_info:
            service.create_team(team_input)

        assert "Team with name='Existing Team' already exists" in str(exc_info.value)

    def test_get_team_success_red_phase(self, service):
        """RED: Test retrieving an existing team."""
        team_id = uuid4()
        mock_team = TeamOutput(id=team_id, name="Test Team", description="A test team")

        service.team_repository.get.return_value = mock_team

        result = service.get_team(team_id)

        assert result == mock_team
        service.team_repository.get.assert_called_once_with(team_id)

    def test_get_team_not_found_red_phase(self, service):
        """RED: Test retrieving a non-existent team."""
        team_id = uuid4()

        service.team_repository.get.side_effect = NotFoundError("Team", team_id)

        with pytest.raises(NotFoundError):
            service.get_team(team_id)

    def test_list_teams_exception_red_phase(self, service):
        """RED: Test listing teams when an unexpected error occurs."""
        service.team_repository.list.side_effect = Exception("Some unexpected error")

        with pytest.raises(Exception) as exc_info:
            service.list_teams()

        assert "Some unexpected error" in str(exc_info.value)

    def test_update_team_success_red_phase(self, service):
        """RED: Test successfully updating a team."""
        team_id = uuid4()
        update_data = TeamInput(name="Updated Team", description="Updated desc")

        service.team_repository.update.return_value = TeamOutput(
            id=team_id, name=update_data.name, description=update_data.description
        )

        result = service.update_team(team_id, update_data)

        assert result.name == update_data.name
        service.team_repository.update.assert_called_once_with(team_id, update_data)

    def test_update_team_duplicate_name_red_phase(self, service):
        """RED: Test updating a team with a duplicate name."""
        team_id = uuid4()
        update_data = TeamInput(name="Existing Team", description="Updated desc")

        service.team_repository.update.side_effect = DuplicateEntryError("team_name", "Team with name='Existing Team' already exists")

        with pytest.raises(DuplicateEntryError) as exc_info:
            service.update_team(team_id, update_data)

        assert "Team with name='Existing Team' already exists" in str(exc_info.value)

    def test_delete_team_success_red_phase(self, service):
        """RED: Test successfully deleting a team."""
        team_id = uuid4()

        service.team_repository.delete.return_value = True

        service.delete_team(team_id)

        service.team_repository.delete.assert_called_once_with(team_id)

    def test_delete_team_exception_red_phase(self, service):
        """RED: Test deleting a team when an unexpected error occurs."""
        team_id = uuid4()

        service.team_repository.delete.side_effect = Exception("Some unexpected error")

        with pytest.raises(Exception) as exc_info:
            service.delete_team(team_id)

        assert "Some unexpected error" in str(exc_info.value)

    def test_add_user_to_team_success_red_phase(self, service):
        """RED: Test successfully adding a user to a team."""
        team_id = uuid4()
        user_id = uuid4()

        service.user_team_service.add_user_to_team.return_value = True

        service.add_user_to_team(user_id, team_id)

        service.user_team_service.add_user_to_team.assert_called_once_with(user_id, team_id)

    def test_add_user_to_team_user_or_team_not_found_red_phase(self, service):
        """RED: Test adding a user to a team when user or team not found."""
        team_id = uuid4()
        user_id = uuid4()

        service.user_team_service.add_user_to_team.side_effect = NotFoundError("User or Team", "not found")

        with pytest.raises(NotFoundError):
            service.add_user_to_team(user_id, team_id)

    def test_remove_user_from_team_success_red_phase(self, service):
        """RED: Test successfully removing a user from a team."""
        team_id = uuid4()
        user_id = uuid4()

        service.user_team_service.remove_user_from_team.return_value = True

        service.remove_user_from_team(user_id, team_id)

        service.user_team_service.remove_user_from_team.assert_called_once_with(user_id, team_id)

    def test_remove_user_from_team_user_or_team_not_found_red_phase(self, service):
        """RED: Test removing a user from a team when user or team not found."""
        team_id = uuid4()
        user_id = uuid4()

        service.user_team_service.remove_user_from_team.side_effect = NotFoundError("User or Team", "not found")

        with pytest.raises(NotFoundError):
            service.remove_user_from_team(user_id, team_id)

    def test_get_team_users_exception_red_phase(self, service):
        """RED: Test retrieving team users when an exception occurs."""
        team_id = uuid4()
        user_id = uuid4()
        user_team = Mock()
        user_team.user_id = user_id

        service.user_team_service.get_team_users.return_value = [user_team]
        service.user_service.get_user_by_id.side_effect = Exception("Some unexpected error")

        result = service.get_team_users(team_id)

        assert result == []
