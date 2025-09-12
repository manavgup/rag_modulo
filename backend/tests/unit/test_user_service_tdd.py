"""TDD Unit tests for UserService - RED phase: Tests that describe expected behavior."""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.services.user_service import UserService
from rag_solution.schemas.user_schema import UserInput, UserOutput
from rag_solution.core.exceptions import NotFoundError, ValidationError


@pytest.mark.unit
class TestUserServiceTDD:
    """TDD tests for UserService - following Red-Green-Refactor cycle."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Mock settings."""
        return Mock(spec=Settings)

    @pytest.fixture
    def mock_user_repository(self):
        """Mock user repository."""
        return Mock()

    @pytest.fixture
    def mock_user_provider_service(self):
        """Mock user provider service."""
        return Mock()

    @pytest.fixture
    def service(self, mock_db, mock_settings):
        """Create service instance with mocked dependencies."""
        with patch('rag_solution.services.user_service.UserRepository') as mock_repo_class, \
             patch('rag_solution.services.user_service.UserProviderService') as mock_provider_class:

            service = UserService(mock_db, mock_settings)
            service.user_repository = Mock()
            service.user_provider_service = Mock()
            return service

    def test_create_user_success_red_phase(self, service, mock_db):
        """RED: Test successful user creation with proper transaction management."""
        user_input = UserInput(
            ibm_id="test_user",
            email="test@example.com",
            name="Test User",
            role="user",
            preferred_provider_id=None
        )
        user_id = uuid4()

        expected_user = UserOutput(
            id=user_id,
            ibm_id="test_user",
            email="test@example.com",
            name="Test User",
            role="user",
            preferred_provider_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        # Mock successful creation flow
        service.user_repository.create.return_value = expected_user
        service.user_provider_service.initialize_user_defaults.return_value = (
            Mock(),  # provider
            [Mock(), Mock()],  # templates (2 required)
            Mock()   # parameters
        )

        result = service.create_user(user_input)

        assert result is expected_user
        assert result.name == "Test User"
        service.user_repository.create.assert_called_once_with(user_input)
        service.user_provider_service.initialize_user_defaults.assert_called_once_with(user_id)
        mock_db.commit.assert_called_once()
        mock_db.rollback.assert_not_called()

    def test_create_user_initialization_failure_red_phase(self, service, mock_db):
        """RED: Test user creation when defaults initialization fails - should rollback."""
        user_input = UserInput(
            ibm_id="test_user",
            email="test@example.com",
            name="Test User",
            role="user",
            preferred_provider_id=None
        )
        user_id = uuid4()

        expected_user = UserOutput(
            id=user_id,
            ibm_id="test_user",
            email="test@example.com",
            name="Test User",
            role="user",
            preferred_provider_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        service.user_repository.create.return_value = expected_user

        # Simulate initialization failure - missing provider
        service.user_provider_service.initialize_user_defaults.return_value = (
            None,  # provider missing
            [Mock(), Mock()],  # templates
            Mock()   # parameters
        )

        # Should raise ValidationError and rollback
        with pytest.raises(ValidationError) as exc_info:
            service.create_user(user_input)

        assert "Failed to initialize required user configuration" in str(exc_info.value)
        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()

    def test_create_user_insufficient_templates_red_phase(self, service, mock_db):
        """RED: Test user creation when fewer than 2 templates created - should rollback."""
        user_input = UserInput(
            ibm_id="test_user",
            email="test@example.com",
            name="Test User",
            role="user",
            preferred_provider_id=None
        )
        user_id = uuid4()

        expected_user = UserOutput(
            id=user_id,
            ibm_id="test_user",
            email="test@example.com",
            name="Test User",
            role="user",
            preferred_provider_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        service.user_repository.create.return_value = expected_user

        # Only 1 template created (needs 2)
        service.user_provider_service.initialize_user_defaults.return_value = (
            Mock(),  # provider
            [Mock()],  # only 1 template
            Mock()   # parameters
        )

        with pytest.raises(ValidationError):
            service.create_user(user_input)

        mock_db.rollback.assert_called_once()

    def test_get_or_create_user_existing_user_red_phase(self, service):
        """RED: Test get_or_create when user already exists."""
        user_input = UserInput(
            ibm_id="existing_user",
            email="existing@example.com",
            name="Existing User",
            role="user",
            preferred_provider_id=None
        )

        existing_user = UserOutput(
            id=uuid4(),
            ibm_id="existing_user",
            email="existing@example.com",
            name="Existing User",
            role="user",
            preferred_provider_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        service.user_repository.get_by_ibm_id.return_value = existing_user

        result = service.get_or_create_user(user_input)

        assert result is existing_user
        service.user_repository.get_by_ibm_id.assert_called_once_with("existing_user")
        service.user_repository.create.assert_not_called()

    def test_get_or_create_user_new_user_red_phase(self, service, mock_db):
        """RED: Test get_or_create when user doesn't exist - should create new."""
        user_input = UserInput(
            ibm_id="new_user",
            email="new@example.com",
            name="New User",
            role="user",
            preferred_provider_id=None
        )

        new_user = UserOutput(
            id=uuid4(),
            ibm_id="new_user",
            email="new@example.com",
            name="New User",
            role="user",
            preferred_provider_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        # User not found, then created successfully
        service.user_repository.get_by_ibm_id.side_effect = NotFoundError("User", "new_user")
        service.user_repository.create.return_value = new_user
        service.user_provider_service.initialize_user_defaults.return_value = (
            Mock(), [Mock(), Mock()], Mock()
        )

        result = service.get_or_create_user(user_input)

        assert result is new_user
        service.user_repository.get_by_ibm_id.assert_called_once_with("new_user")
        service.user_repository.create.assert_called_once_with(user_input)

    def test_get_or_create_user_by_fields_red_phase(self, service):
        """RED: Test get_or_create_user_by_fields convenience method."""
        existing_user = UserOutput(
            id=uuid4(),
            ibm_id="field_user",
            email="field@example.com",
            name="Field User",
            role="admin",
            preferred_provider_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        service.user_repository.get_by_ibm_id.return_value = existing_user

        result = service.get_or_create_user_by_fields(
            ibm_id="field_user",
            email="field@example.com",
            name="Field User",
            role="admin"
        )

        assert result is existing_user
        service.user_repository.get_by_ibm_id.assert_called_once_with("field_user")

    def test_get_user_by_id_success_red_phase(self, service):
        """RED: Test successful user retrieval by ID."""
        user_id = uuid4()
        expected_user = UserOutput(
            id=user_id,
            ibm_id="test_user",
            email="test@example.com",
            name="Test User",
            role="user",
            preferred_provider_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        service.user_repository.get_by_id.return_value = expected_user

        result = service.get_user_by_id(user_id)

        assert result is expected_user
        assert result.id == user_id
        service.user_repository.get_by_id.assert_called_once_with(user_id)

    def test_get_user_by_id_not_found_red_phase(self, service):
        """RED: Test user retrieval when user not found."""
        user_id = uuid4()

        service.user_repository.get_by_id.side_effect = NotFoundError("User", user_id)

        with pytest.raises(NotFoundError) as exc_info:
            service.get_user_by_id(user_id)

        assert str(user_id) in str(exc_info.value)
        service.user_repository.get_by_id.assert_called_once_with(user_id)

    def test_get_user_by_ibm_id_success_red_phase(self, service):
        """RED: Test successful user retrieval by IBM ID."""
        expected_user = UserOutput(
            id=uuid4(),
            ibm_id="test_ibm_id",
            email="test@example.com",
            name="Test User",
            role="user",
            preferred_provider_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        service.user_repository.get_by_ibm_id.return_value = expected_user

        result = service.get_user_by_ibm_id("test_ibm_id")

        assert result is expected_user
        assert result.ibm_id == "test_ibm_id"
        service.user_repository.get_by_ibm_id.assert_called_once_with("test_ibm_id")

    def test_update_user_success_red_phase(self, service):
        """RED: Test successful user update."""
        user_id = uuid4()
        user_update = UserInput(
            ibm_id="updated_user",
            email="updated@example.com",
            name="Updated User",
            role="admin",
            preferred_provider_id=None
        )

        updated_user = UserOutput(
            id=user_id,
            ibm_id="updated_user",
            email="updated@example.com",
            name="Updated User",
            role="admin",
            preferred_provider_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        service.user_repository.update.return_value = updated_user

        result = service.update_user(user_id, user_update)

        assert result is updated_user
        assert result.name == "Updated User"
        service.user_repository.update.assert_called_once_with(user_id, user_update)

    def test_update_user_not_found_red_phase(self, service):
        """RED: Test user update when user not found."""
        user_id = uuid4()
        user_update = UserInput(
            ibm_id="updated_user",
            email="updated@example.com",
            name="Updated User",
            role="admin",
            preferred_provider_id=None
        )

        service.user_repository.update.side_effect = NotFoundError("User", user_id)

        with pytest.raises(NotFoundError) as exc_info:
            service.update_user(user_id, user_update)

        assert str(user_id) in str(exc_info.value)
        service.user_repository.update.assert_called_once_with(user_id, user_update)

    def test_delete_user_success_red_phase(self, service):
        """RED: Test successful user deletion."""
        user_id = uuid4()

        service.user_repository.delete.return_value = None

        result = service.delete_user(user_id)

        assert result is None
        service.user_repository.delete.assert_called_once_with(user_id)

    def test_delete_user_not_found_red_phase(self, service):
        """RED: Test user deletion when user not found."""
        user_id = uuid4()

        service.user_repository.delete.side_effect = NotFoundError("User", user_id)

        with pytest.raises(NotFoundError):
            service.delete_user(user_id)

        service.user_repository.delete.assert_called_once_with(user_id)

    def test_list_users_success_red_phase(self, service):
        """RED: Test successful user listing."""
        users = [
            UserOutput(id=uuid4(), ibm_id="user1", email="user1@example.com", name="User 1", role="user", preferred_provider_id=None, created_at="2024-01-01T00:00:00Z", updated_at="2024-01-01T00:00:00Z"),
            UserOutput(id=uuid4(), ibm_id="user2", email="user2@example.com", name="User 2", role="admin", preferred_provider_id=None, created_at="2024-01-01T00:00:00Z", updated_at="2024-01-01T00:00:00Z"),
            UserOutput(id=uuid4(), ibm_id="user3", email="user3@example.com", name="User 3", role="user", preferred_provider_id=None, created_at="2024-01-01T00:00:00Z", updated_at="2024-01-01T00:00:00Z")
        ]

        service.user_repository.list_users.return_value = users

        result = service.list_users(skip=0, limit=100)

        assert result == users
        assert len(result) == 3
        service.user_repository.list_users.assert_called_once_with(0, 100)

    def test_list_users_with_pagination_red_phase(self, service):
        """RED: Test user listing with custom pagination."""
        users = [
            UserOutput(id=uuid4(), ibm_id="user4", email="user4@example.com", name="User 4", role="user", preferred_provider_id=None, created_at="2024-01-01T00:00:00Z", updated_at="2024-01-01T00:00:00Z"),
            UserOutput(id=uuid4(), ibm_id="user5", email="user5@example.com", name="User 5", role="admin", preferred_provider_id=None, created_at="2024-01-01T00:00:00Z", updated_at="2024-01-01T00:00:00Z")
        ]

        service.user_repository.list_users.return_value = users

        result = service.list_users(skip=10, limit=20)

        assert result == users
        service.user_repository.list_users.assert_called_once_with(10, 20)

    def test_get_user_alias_red_phase(self, service):
        """RED: Test get_user method (alias for get_user_by_id)."""
        user_id = uuid4()
        expected_user = UserOutput(
            id=user_id,
            ibm_id="test_user",
            email="test@example.com",
            name="Test User",
            role="user",
            preferred_provider_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        service.user_repository.get_by_id.return_value = expected_user

        result = service.get_user(user_id)

        assert result is expected_user
        service.user_repository.get_by_id.assert_called_once_with(user_id)

    def test_set_user_preferred_provider_incomplete_implementation_red_phase(self, service):
        """GREEN: Test set_user_preferred_provider - NOW CORRECTLY UPDATES."""
        user_id = uuid4()
        provider_id = uuid4()

        # Mock get_by_id to return current user
        current_user = UserOutput(
            id=user_id,
            ibm_id="test_user",
            email="test@example.com",
            name="Test User",
            role="user",
            preferred_provider_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        service.user_repository.get_by_id.return_value = current_user

        # Mock update to return updated user
        updated_user = UserOutput(
            id=user_id,
            ibm_id="test_user",
            email="test@example.com",
            name="Test User",
            role="user",
            preferred_provider_id=provider_id,  # Now correctly updated
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        service.user_repository.update.return_value = updated_user

        result = service.set_user_preferred_provider(user_id, provider_id)

        # Now the method correctly updates the preferred_provider_id
        assert result.preferred_provider_id == provider_id
        service.user_repository.get_by_id.assert_called_once_with(user_id)
        # Repository update is now correctly called

    def test_service_initialization_red_phase(self, mock_db, mock_settings):
        """RED: Test service initialization with dependencies."""
        with patch('rag_solution.services.user_service.UserRepository') as mock_repo_class, \
             patch('rag_solution.services.user_service.UserProviderService') as mock_provider_class:

            service = UserService(mock_db, mock_settings)

            assert service.db is mock_db
            assert service.settings is mock_settings
            mock_repo_class.assert_called_once_with(mock_db)
            mock_provider_class.assert_called_once_with(mock_db, mock_settings)

    def test_logging_behavior_red_phase(self, service):
        """RED: Test that logging calls are made appropriately."""
        user_id = uuid4()
        expected_user = UserOutput(
            id=user_id,
            ibm_id="logged_user",
            email="logged@example.com",
            name="Logged User",
            role="user",
            preferred_provider_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )

        service.user_repository.get_by_id.return_value = expected_user

        with patch('rag_solution.services.user_service.logger') as mock_logger:
            service.get_user_by_id(user_id)

            # Should log fetching start (using lazy % formatting)
            mock_logger.info.assert_called_once_with("Fetching user with id: %s", user_id)

    def test_transaction_rollback_on_repository_exception_red_phase(self, service, mock_db):
        """RED: Test transaction handling when repository creation fails."""
        user_input = UserInput(
            ibm_id="test_user",
            email="test@example.com",
            name="Test User",
            role="user",
            preferred_provider_id=None
        )

        # Repository creation fails
        service.user_repository.create.side_effect = Exception("Database constraint violation")

        # Should bubble up exception (no rollback because commit/rollback only in defaults validation)
        with pytest.raises(Exception) as exc_info:
            service.create_user(user_input)

        assert "Database constraint violation" in str(exc_info.value)
        # No rollback should be called because exception happens before defaults validation
        mock_db.rollback.assert_not_called()
        mock_db.commit.assert_not_called()

# RED PHASE COMPLETE: These tests will reveal several logic issues:
# 1. set_user_preferred_provider doesn't actually update the provider
# 2. Transaction management is inconsistent
# 3. Method duplication (get_user vs get_user_by_id)
# Let's run these to see what fails and needs fixing
