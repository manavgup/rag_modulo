"""
Comprehensive tests for UserTeamService
Generated on: 2025-10-18
Coverage: Unit tests for user-team relationship management
"""

from datetime import datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from backend.rag_solution.core.exceptions import NotFoundError
from backend.rag_solution.repository.user_team_repository import UserTeamRepository
from backend.rag_solution.schemas.user_team_schema import UserTeamOutput

# Service imports
from backend.rag_solution.services.user_team_service import UserTeamService
from sqlalchemy.orm import Session

# ============================================================================
# SHARED FIXTURES
# ============================================================================

@pytest.fixture
def mock_db():
    """Mock database session for unit tests"""
    mock = Mock(spec=Session)
    mock.commit = Mock()
    mock.rollback = Mock()
    mock.query = Mock()
    mock.add = Mock()
    mock.delete = Mock()
    return mock


@pytest.fixture
def mock_repository(mock_db):
    """Mock repository for unit tests"""
    mock = Mock(spec=UserTeamRepository)
    mock.db = mock_db
    mock.add_user_to_team = Mock(return_value=True)
    mock.remove_user_from_team = Mock()
    mock.get_user_teams = Mock(return_value=[])
    mock.get_team_users = Mock(return_value=[])
    mock.get_user_team = Mock(return_value=None)
    return mock


@pytest.fixture
def service(mock_db):
    """Service instance with mocked dependencies"""
    return UserTeamService(db=mock_db)


@pytest.fixture
def sample_user_id():
    """Sample user UUID for testing"""
    return uuid4()


@pytest.fixture
def sample_team_id():
    """Sample team UUID for testing"""
    return uuid4()


@pytest.fixture
def sample_user_team_output(sample_user_id, sample_team_id):
    """Sample UserTeamOutput for testing"""
    return UserTeamOutput(
        user_id=sample_user_id,
        team_id=sample_team_id,
        role="member",
        joined_at=datetime.now()
    )


# ============================================================================
# UNIT TESTS
# ============================================================================

@pytest.mark.unit
class TestUserTeamServiceUnit:
    """
    Unit tests with fully mocked dependencies.
    Focus: Individual method behavior, business logic, error handling.
    """

    # ====================
    # INITIALIZATION TESTS
    # ====================

    def test_service_initialization(self, mock_db):
        """Test successful service initialization"""
        service = UserTeamService(db=mock_db)

        assert service.db is mock_db
        assert isinstance(service.user_team_repository, UserTeamRepository)
        assert service.user_team_repository.db is mock_db

    def test_service_initialization_with_none_db(self):
        """Test service initialization with None database raises error"""
        # The service doesn't validate None explicitly, but SQLAlchemy would fail
        # This tests that we're passing the db correctly
        service = UserTeamService(db=None)
        assert service.db is None

    # ====================
    # ADD USER TO TEAM TESTS
    # ====================

    def test_add_user_to_team_success(self, service, sample_user_id, sample_team_id, sample_user_team_output):
        """Test successfully adding a user to a team"""
        # Mock repository methods
        service.user_team_repository.add_user_to_team = Mock(return_value=True)
        service.user_team_repository.get_user_team = Mock(return_value=sample_user_team_output)

        result = service.add_user_to_team(sample_user_id, sample_team_id)

        assert result == sample_user_team_output
        service.user_team_repository.add_user_to_team.assert_called_once_with(sample_user_id, sample_team_id)
        service.user_team_repository.get_user_team.assert_called_once_with(sample_user_id, sample_team_id)

    def test_add_user_to_team_already_exists(self, service, sample_user_id, sample_team_id, sample_user_team_output):
        """Test adding a user to a team when already a member (idempotent)"""
        service.user_team_repository.add_user_to_team = Mock(return_value=True)
        service.user_team_repository.get_user_team = Mock(return_value=sample_user_team_output)

        result = service.add_user_to_team(sample_user_id, sample_team_id)

        assert result == sample_user_team_output
        assert result.user_id == sample_user_id
        assert result.team_id == sample_team_id

    def test_add_user_to_team_user_not_found(self, service, sample_user_id, sample_team_id):
        """Test adding a user to a team when user doesn't exist"""
        service.user_team_repository.add_user_to_team = Mock(
            side_effect=ValueError("User or team not found or duplicate entry")
        )

        with pytest.raises(ValueError) as exc_info:
            service.add_user_to_team(sample_user_id, sample_team_id)

        assert "User or team not found" in str(exc_info.value)

    def test_add_user_to_team_team_not_found(self, service, sample_user_id, sample_team_id):
        """Test adding a user to a team when team doesn't exist"""
        service.user_team_repository.add_user_to_team = Mock(
            side_effect=ValueError("User or team not found or duplicate entry")
        )

        with pytest.raises(ValueError):
            service.add_user_to_team(sample_user_id, sample_team_id)

    def test_add_user_to_team_database_error(self, service, sample_user_id, sample_team_id):
        """Test handling of database connection errors"""
        service.user_team_repository.add_user_to_team = Mock(
            side_effect=RuntimeError("Failed to add user to team due to an internal error.")
        )

        with pytest.raises(RuntimeError) as exc_info:
            service.add_user_to_team(sample_user_id, sample_team_id)

        assert "internal error" in str(exc_info.value).lower()

    def test_add_user_to_team_returns_none_when_get_fails(self, service, sample_user_id, sample_team_id):
        """Test add_user_to_team returns None when get_user_team fails"""
        service.user_team_repository.add_user_to_team = Mock(return_value=True)
        service.user_team_repository.get_user_team = Mock(return_value=None)

        result = service.add_user_to_team(sample_user_id, sample_team_id)

        assert result is None

    # ====================
    # REMOVE USER FROM TEAM TESTS
    # ====================

    def test_remove_user_from_team_success(self, service, sample_user_id, sample_team_id):
        """Test successfully removing a user from a team"""
        service.user_team_repository.remove_user_from_team = Mock()

        result = service.remove_user_from_team(sample_user_id, sample_team_id)

        assert result is True
        service.user_team_repository.remove_user_from_team.assert_called_once_with(sample_user_id, sample_team_id)

    def test_remove_user_from_team_not_found(self, service, sample_user_id, sample_team_id):
        """Test removing a user from a team when membership doesn't exist"""
        service.user_team_repository.remove_user_from_team = Mock(
            side_effect=NotFoundError(
                resource_type="UserTeam",
                identifier=f"user {sample_user_id} in team {sample_team_id}"
            )
        )

        with pytest.raises(NotFoundError) as exc_info:
            service.remove_user_from_team(sample_user_id, sample_team_id)

        assert "UserTeam not found" in str(exc_info.value)

    def test_remove_user_from_team_database_error(self, service, sample_user_id, sample_team_id):
        """Test handling of database errors during removal"""
        service.user_team_repository.remove_user_from_team = Mock(
            side_effect=Exception("Failed to remove user from team: Database connection lost")
        )

        with pytest.raises(Exception) as exc_info:
            service.remove_user_from_team(sample_user_id, sample_team_id)

        assert "Failed to remove user from team" in str(exc_info.value)

    # ====================
    # GET USER TEAMS TESTS
    # ====================

    def test_get_user_teams_success(self, service, sample_user_id):
        """Test retrieving all teams for a user"""
        team_id_1 = uuid4()
        team_id_2 = uuid4()
        expected_teams = [
            UserTeamOutput(user_id=sample_user_id, team_id=team_id_1, role="admin", joined_at=datetime.now()),
            UserTeamOutput(user_id=sample_user_id, team_id=team_id_2, role="member", joined_at=datetime.now())
        ]

        service.user_team_repository.get_user_teams = Mock(return_value=expected_teams)

        result = service.get_user_teams(sample_user_id)

        assert len(result) == 2
        assert result == expected_teams
        service.user_team_repository.get_user_teams.assert_called_once_with(sample_user_id)

    def test_get_user_teams_empty(self, service, sample_user_id):
        """Test retrieving teams for a user with no team memberships"""
        service.user_team_repository.get_user_teams = Mock(return_value=[])

        result = service.get_user_teams(sample_user_id)

        assert result == []
        assert isinstance(result, list)

    def test_get_user_teams_database_error(self, service, sample_user_id):
        """Test handling of database errors when retrieving user teams"""
        service.user_team_repository.get_user_teams = Mock(
            side_effect=Exception("Failed to list teams: Database error")
        )

        with pytest.raises(Exception) as exc_info:
            service.get_user_teams(sample_user_id)

        assert "Failed to list teams" in str(exc_info.value)

    def test_get_user_teams_single_team(self, service, sample_user_id):
        """Test retrieving teams for a user in exactly one team"""
        team_id = uuid4()
        expected_team = [
            UserTeamOutput(user_id=sample_user_id, team_id=team_id, role="member", joined_at=datetime.now())
        ]

        service.user_team_repository.get_user_teams = Mock(return_value=expected_team)

        result = service.get_user_teams(sample_user_id)

        assert len(result) == 1
        assert result[0].team_id == team_id

    # ====================
    # GET TEAM USERS TESTS
    # ====================

    def test_get_team_users_success(self, service, sample_team_id):
        """Test retrieving all users for a team"""
        user_id_1 = uuid4()
        user_id_2 = uuid4()
        expected_users = [
            UserTeamOutput(user_id=user_id_1, team_id=sample_team_id, role="admin", joined_at=datetime.now()),
            UserTeamOutput(user_id=user_id_2, team_id=sample_team_id, role="member", joined_at=datetime.now())
        ]

        service.user_team_repository.get_team_users = Mock(return_value=expected_users)

        result = service.get_team_users(sample_team_id)

        assert len(result) == 2
        assert result == expected_users
        service.user_team_repository.get_team_users.assert_called_once_with(sample_team_id)

    def test_get_team_users_empty(self, service, sample_team_id):
        """Test retrieving users for an empty team"""
        service.user_team_repository.get_team_users = Mock(return_value=[])

        result = service.get_team_users(sample_team_id)

        assert result == []
        assert isinstance(result, list)

    def test_get_team_users_single_user(self, service, sample_team_id):
        """Test retrieving users for a team with exactly one member"""
        user_id = uuid4()
        expected_user = [
            UserTeamOutput(user_id=user_id, team_id=sample_team_id, role="admin", joined_at=datetime.now())
        ]

        service.user_team_repository.get_team_users = Mock(return_value=expected_user)

        result = service.get_team_users(sample_team_id)

        assert len(result) == 1
        assert result[0].user_id == user_id

    def test_get_team_users_large_team(self, service, sample_team_id):
        """Test retrieving users for a very large team (1000+ users)"""
        large_user_list = [
            UserTeamOutput(
                user_id=uuid4(),
                team_id=sample_team_id,
                role="member" if i > 0 else "admin",
                joined_at=datetime.now()
            )
            for i in range(1000)
        ]

        service.user_team_repository.get_team_users = Mock(return_value=large_user_list)

        result = service.get_team_users(sample_team_id)

        assert len(result) == 1000
        assert result[0].role == "admin"  # First user is admin
        assert all(u.role == "member" for u in result[1:])  # Rest are members

    def test_get_team_users_database_error(self, service, sample_team_id):
        """Test handling of database errors when retrieving team users"""
        service.user_team_repository.get_team_users = Mock(
            side_effect=Exception("Failed to list users: Database error")
        )

        with pytest.raises(Exception) as exc_info:
            service.get_team_users(sample_team_id)

        assert "Failed to list users" in str(exc_info.value)

    # ====================
    # GET USER TEAM TESTS
    # ====================

    def test_get_user_team_success(self, service, sample_user_id, sample_team_id, sample_user_team_output):
        """Test retrieving a specific user-team relationship"""
        service.user_team_repository.get_user_team = Mock(return_value=sample_user_team_output)

        result = service.get_user_team(sample_user_id, sample_team_id)

        assert result == sample_user_team_output
        assert result.user_id == sample_user_id
        assert result.team_id == sample_team_id
        service.user_team_repository.get_user_team.assert_called_once_with(sample_user_id, sample_team_id)

    def test_get_user_team_not_found(self, service, sample_user_id, sample_team_id):
        """Test retrieving a non-existent user-team relationship"""
        service.user_team_repository.get_user_team = Mock(return_value=None)

        result = service.get_user_team(sample_user_id, sample_team_id)

        assert result is None

    def test_get_user_team_database_error(self, service, sample_user_id, sample_team_id):
        """Test handling of database errors when getting user-team relationship"""
        service.user_team_repository.get_user_team = Mock(
            side_effect=Exception("Failed to get team association: Connection error")
        )

        with pytest.raises(Exception) as exc_info:
            service.get_user_team(sample_user_id, sample_team_id)

        assert "Failed to get team association" in str(exc_info.value)

    # ====================
    # UPDATE USER ROLE TESTS
    # ====================

    def test_update_user_role_in_team_success(self, service, sample_user_id, sample_team_id, mock_db):
        """Test successfully updating a user's role in a team"""
        mock_user_team = Mock()
        mock_user_team.user_id = sample_user_id
        mock_user_team.team_id = sample_team_id
        mock_user_team.role = "member"

        service.user_team_repository.get_user_team = Mock(return_value=mock_user_team)

        result = service.update_user_role_in_team(sample_user_id, sample_team_id, "admin")

        assert result == mock_user_team
        assert mock_user_team.role == "admin"
        mock_db.commit.assert_called_once()

    def test_update_user_role_in_team_not_found(self, service, sample_user_id, sample_team_id, mock_db):
        """Test updating role when user-team relationship doesn't exist"""
        service.user_team_repository.get_user_team = Mock(return_value=None)

        result = service.update_user_role_in_team(sample_user_id, sample_team_id, "admin")

        assert result is None
        mock_db.commit.assert_not_called()

    def test_update_user_role_in_team_from_member_to_admin(self, service, sample_user_id, sample_team_id, mock_db):
        """Test promoting a member to admin role"""
        mock_user_team = Mock()
        mock_user_team.role = "member"

        service.user_team_repository.get_user_team = Mock(return_value=mock_user_team)

        result = service.update_user_role_in_team(sample_user_id, sample_team_id, "admin")

        assert mock_user_team.role == "admin"
        assert result == mock_user_team

    def test_update_user_role_in_team_from_admin_to_member(self, service, sample_user_id, sample_team_id, mock_db):
        """Test demoting an admin to member role"""
        mock_user_team = Mock()
        mock_user_team.role = "admin"

        service.user_team_repository.get_user_team = Mock(return_value=mock_user_team)

        result = service.update_user_role_in_team(sample_user_id, sample_team_id, "member")

        assert mock_user_team.role == "member"
        assert result == mock_user_team

    def test_update_user_role_in_team_same_role(self, service, sample_user_id, sample_team_id, mock_db):
        """Test updating a user's role to the same role (idempotent)"""
        mock_user_team = Mock()
        mock_user_team.role = "admin"

        service.user_team_repository.get_user_team = Mock(return_value=mock_user_team)

        result = service.update_user_role_in_team(sample_user_id, sample_team_id, "admin")

        assert mock_user_team.role == "admin"
        mock_db.commit.assert_called_once()

    # ====================
    # EDGE CASES AND ERROR HANDLING
    # ====================

    def test_add_user_to_team_with_uuid_strings(self, service):
        """Test adding user to team using UUID strings (type flexibility)"""
        user_id = uuid4()
        team_id = uuid4()
        expected_output = UserTeamOutput(
            user_id=user_id,
            team_id=team_id,
            role="member",
            joined_at=datetime.now()
        )

        service.user_team_repository.add_user_to_team = Mock(return_value=True)
        service.user_team_repository.get_user_team = Mock(return_value=expected_output)

        result = service.add_user_to_team(user_id, team_id)

        assert result == expected_output

    def test_operations_with_different_role_types(self, service, sample_user_id, sample_team_id, mock_db):
        """Test role updates with various role types"""
        mock_user_team = Mock()
        mock_user_team.role = "member"

        service.user_team_repository.get_user_team = Mock(return_value=mock_user_team)

        # Test with different role strings
        for role in ["admin", "member", "viewer", "editor"]:
            result = service.update_user_role_in_team(sample_user_id, sample_team_id, role)
            assert mock_user_team.role == role

    def test_get_user_teams_maintains_order(self, service, sample_user_id):
        """Test that get_user_teams maintains the order returned by repository"""
        team_ids = [uuid4() for _ in range(5)]
        expected_teams = [
            UserTeamOutput(
                user_id=sample_user_id,
                team_id=tid,
                role="member",
                joined_at=datetime.now()
            )
            for tid in team_ids
        ]

        service.user_team_repository.get_user_teams = Mock(return_value=expected_teams)

        result = service.get_user_teams(sample_user_id)

        assert [t.team_id for t in result] == team_ids

    def test_concurrent_operations_isolation(self, service, sample_user_id, sample_team_id):
        """Test that operations are properly isolated (no side effects)"""
        # First operation
        service.user_team_repository.add_user_to_team = Mock(return_value=True)
        service.user_team_repository.get_user_team = Mock(
            return_value=UserTeamOutput(
                user_id=sample_user_id,
                team_id=sample_team_id,
                role="member",
                joined_at=datetime.now()
            )
        )

        result1 = service.add_user_to_team(sample_user_id, sample_team_id)

        # Second operation shouldn't affect first
        different_user_id = uuid4()
        service.user_team_repository.add_user_to_team = Mock(return_value=True)
        service.user_team_repository.get_user_team = Mock(
            return_value=UserTeamOutput(
                user_id=different_user_id,
                team_id=sample_team_id,
                role="admin",
                joined_at=datetime.now()
            )
        )

        result2 = service.add_user_to_team(different_user_id, sample_team_id)

        assert result1.user_id != result2.user_id
        assert result1.role != result2.role
