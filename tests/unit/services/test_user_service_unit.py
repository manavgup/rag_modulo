"""Unit tests for UserService with mocked dependencies."""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from rag_solution.schemas.user_schema import UserInput, UserOutput
from rag_solution.services.user_service import UserService


@pytest.mark.unit
class TestUserServiceUnit:
    """Unit tests for UserService with mocked dependencies."""

    @pytest.fixture
    def mock_db(self) -> Mock:
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_user_repository(self):
        """Mock user repository."""
        return Mock()

    @pytest.fixture
    def service(self, mock_db, mock_settings):
        """Create service instance with mocked repository."""
        with (
            patch("rag_solution.services.user_service.UserRepository"),
            patch("rag_solution.services.user_service.UserProviderService"),
        ):
            service = UserService(mock_db, mock_settings)
            service.user_repository = Mock()
            service.user_provider_service = Mock()
            return service

    def test_service_initialization(self, mock_db, mock_settings):
        """Test service initialization with dependency injection."""
        with patch("rag_solution.services.user_service.UserRepository") as mock_repo_class:
            service = UserService(mock_db, mock_settings)

            assert service.db is mock_db
            assert service.settings is mock_settings
            mock_repo_class.assert_called_once_with(mock_db)

    def test_create_user_success(self, service):
        """Test successful user creation."""
        user_input = UserInput(email="test@example.com", ibm_id="test_user_123", name="Test User", role="user")
        user_id = uuid4()

        mock_user = UserOutput(
            id=user_id,
            email="test@example.com",
            ibm_id="test_user_123",
            name="Test User",
            role="user",
            preferred_provider_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        service.user_repository.create.return_value = mock_user

        # Mock initialize_user_defaults to return successful values
        mock_provider = Mock()
        mock_templates = [Mock(), Mock(), Mock()]  # Need 3 templates: RAG, QUESTION, PODCAST
        mock_parameters = Mock()
        service.user_provider_service.initialize_user_defaults.return_value = (
            mock_provider,
            mock_templates,
            mock_parameters,
        )

        result = service.create_user(user_input)

        assert result is mock_user
        service.user_repository.create.assert_called_once_with(user_input)
        service.user_provider_service.initialize_user_defaults.assert_called_once_with(user_id)

    def test_create_user_duplicate_email_error(self, service):
        """Test user creation with duplicate email."""
        user_input = UserInput(email="existing@example.com", ibm_id="existing_user", name="Existing User", role="user")

        service.user_repository.create.side_effect = Exception("Email already exists")

        with pytest.raises(Exception) as exc_info:
            service.create_user(user_input)

        assert "Email already exists" in str(exc_info.value)
        service.user_repository.create.assert_called_once_with(user_input)

    def test_get_user_by_id_success(self, service):
        """Test successful user retrieval by ID."""
        user_id = uuid4()
        mock_user = UserOutput(
            id=user_id,
            email="test@example.com",
            ibm_id="test_user",
            name="Test User",
            role="user",
            preferred_provider_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        service.user_repository.get_by_id.return_value = mock_user

        result = service.get_user_by_id(user_id)

        assert result is mock_user
        service.user_repository.get_by_id.assert_called_once_with(user_id)

    def test_get_user_by_id_not_found(self, service):
        """Test user retrieval when user not found."""
        user_id = uuid4()

        service.user_repository.get_by_id.return_value = None

        result = service.get_user_by_id(user_id)

        assert result is None
        service.user_repository.get_by_id.assert_called_once_with(user_id)

    @pytest.mark.skip(reason="Method doesn't exist in current UserService implementation")
    # DISABLED: get_user_by_email method doesn't exist in UserService
    def test_get_user_by_email_success_disabled(self, service):
        """Test successful user retrieval by email."""
        email = "test@example.com"
        mock_user = UserOutput(
            id=uuid4(),
            email=email,
            ibm_id="test_user",
            name="Test User",
            role="user",
            preferred_provider_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        service.user_repository.get_by_email.return_value = mock_user

        result = service.get_user_by_email(email)

        assert result is mock_user
        service.user_repository.get_by_email.assert_called_once_with(email)

    @pytest.mark.skip(reason="Method doesn't exist in current UserService implementation")
    # DISABLED: get_user_by_email method doesn't exist in UserService
    def test_get_user_by_email_not_found_disabled(self, service):
        """Test user retrieval by email when user not found."""
        email = "nonexistent@example.com"

        service.user_repository.get_by_email.return_value = None

        result = service.get_user_by_email(email)

        assert result is None
        service.user_repository.get_by_email.assert_called_once_with(email)

    def test_get_user_by_ibm_id_success(self, service):
        """Test successful user retrieval by IBM ID."""
        ibm_id = "test_user_123"
        mock_user = UserOutput(
            id=uuid4(),
            email="test@example.com",
            ibm_id=ibm_id,
            name="Test User",
            role="user",
            preferred_provider_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        service.user_repository.get_by_ibm_id.return_value = mock_user

        result = service.get_user_by_ibm_id(ibm_id)

        assert result is mock_user
        service.user_repository.get_by_ibm_id.assert_called_once_with(ibm_id)

    def test_list_users_success(self, service):
        """Test successful retrieval of all users."""
        mock_users = [
            UserOutput(
                id=uuid4(),
                email="user1@example.com",
                ibm_id="user1",
                name="User 1",
                role="user",
                preferred_provider_id=None,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            ),
            UserOutput(
                id=uuid4(),
                email="user2@example.com",
                ibm_id="user2",
                name="User 2",
                role="admin",
                preferred_provider_id=None,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            ),
            UserOutput(
                id=uuid4(),
                email="user3@example.com",
                ibm_id="user3",
                name="User 3",
                role="user",
                preferred_provider_id=None,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            ),
        ]

        service.user_repository.list_users.return_value = mock_users

        result = service.list_users()

        assert result == mock_users
        assert len(result) == 3
        service.user_repository.list_users.assert_called_once()

    def test_list_users_empty(self, service):
        """Test retrieval of all users when no users exist."""
        service.user_repository.list_users.return_value = []

        result = service.list_users()

        assert result == []
        service.user_repository.list_users.assert_called_once()

    def test_update_user_success(self, service):
        """Test successful user update."""
        user_id = uuid4()
        user_input = UserInput(email="updated@example.com", ibm_id="updated_user", name="Updated User", role="admin")

        updated_user = UserOutput(
            id=user_id,
            email="updated@example.com",
            ibm_id="updated_user",
            name="Updated User",
            role="admin",
            preferred_provider_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z",
        )

        service.user_repository.update.return_value = updated_user

        result = service.update_user(user_id, user_input)

        assert result is updated_user
        service.user_repository.update.assert_called_once_with(user_id, user_input)

    def test_update_user_not_found(self, service):
        """Test user update when user not found."""
        user_id = uuid4()
        user_input = UserInput(email="updated@example.com", ibm_id="updated_user", name="Updated User", role="admin")

        service.user_repository.update.return_value = None

        result = service.update_user(user_id, user_input)

        assert result is None
        service.user_repository.update.assert_called_once_with(user_id, user_input)

    def test_delete_user_success(self, service):
        """Test successful user deletion."""
        user_id = uuid4()

        service.user_repository.delete.return_value = None

        result = service.delete_user(user_id)

        assert result is None
        service.user_repository.delete.assert_called_once_with(user_id)

    def test_delete_user_not_found(self, service):
        """Test user deletion when user not found."""
        user_id = uuid4()

        from rag_solution.core.exceptions import NotFoundError

        service.user_repository.delete.side_effect = NotFoundError("User not found")

        with pytest.raises(NotFoundError):
            service.delete_user(user_id)

        service.user_repository.delete.assert_called_once_with(user_id)

    @pytest.mark.skip(reason="Method doesn't exist in current UserService implementation")
    # DISABLED: search_users_by_name method doesn't exist in UserService
    def test_search_users_by_name_success_disabled(self, service):
        """Test successful user search by name."""
        search_term = "John"
        matching_users = [
            UserOutput(
                id=uuid4(),
                email="john.doe@example.com",
                ibm_id="john_doe",
                name="John Doe",
                role="user",
                preferred_provider_id=None,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            ),
            UserOutput(
                id=uuid4(),
                email="john.smith@example.com",
                ibm_id="john_smith",
                name="John Smith",
                role="admin",
                preferred_provider_id=None,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            ),
        ]

        service.user_repository.search_by_name.return_value = matching_users

        result = service.search_users_by_name(search_term)

        assert result == matching_users
        assert len(result) == 2
        service.user_repository.search_by_name.assert_called_once_with(search_term)

    @pytest.mark.skip(reason="Method doesn't exist in current UserService implementation")
    # DISABLED: search_users_by_name method doesn't exist in UserService
    def test_search_users_by_name_no_results_disabled(self, service):
        """Test user search by name with no results."""
        search_term = "NonExistentName"

        service.user_repository.search_by_name.return_value = []

        result = service.search_users_by_name(search_term)

        assert result == []
        service.user_repository.search_by_name.assert_called_once_with(search_term)

    @pytest.mark.skip(reason="Method doesn't exist in current UserService implementation")
    # DISABLED: get_users_by_role method doesn't exist in UserService
    def test_get_users_by_role_success_disabled(self, service):
        """Test successful retrieval of users by role."""
        role = "admin"
        admin_users = [
            UserOutput(
                id=uuid4(),
                email="admin1@example.com",
                ibm_id="admin1",
                name="Admin 1",
                role="admin",
                preferred_provider_id=None,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            ),
            UserOutput(
                id=uuid4(),
                email="admin2@example.com",
                ibm_id="admin2",
                name="Admin 2",
                role="admin",
                preferred_provider_id=None,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            ),
        ]

        service.user_repository.get_by_role.return_value = admin_users

        result = service.get_users_by_role(role)

        assert result == admin_users
        assert len(result) == 2
        service.user_repository.get_by_role.assert_called_once_with(role)

    @pytest.mark.skip(reason="Method doesn't exist in current UserService implementation")
    # DISABLED: get_users_by_role method doesn't exist in UserService
    def test_get_users_by_role_no_users_disabled(self, service):
        """Test retrieval of users by role when no users found."""
        role = "super_admin"

        service.user_repository.get_by_role.return_value = []

        result = service.get_users_by_role(role)

        assert result == []
        service.user_repository.get_by_role.assert_called_once_with(role)

    def test_set_preferred_provider_success(self, service):
        """Test successfully setting user's preferred provider."""
        user_id = uuid4()
        provider_id = uuid4()

        # Mock get_by_id to return a UserOutput object
        current_user = UserOutput(
            id=user_id,
            email="test@example.com",
            ibm_id="test_user",
            name="Test User",
            role="user",
            preferred_provider_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        service.user_repository.get_by_id.return_value = current_user

        # Mock update to return updated user
        updated_user = UserOutput(
            id=user_id,
            email="test@example.com",
            ibm_id="test_user",
            name="Test User",
            role="user",
            preferred_provider_id=provider_id,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        service.user_repository.update.return_value = updated_user

        result = service.set_user_preferred_provider(user_id, provider_id)

        assert result is updated_user
        assert result.preferred_provider_id == provider_id
        service.user_repository.get_by_id.assert_called_once_with(user_id)
        service.user_repository.update.assert_called_once()

    def test_set_preferred_provider_failure(self, service):
        """Test setting preferred provider failure (user not found)."""
        user_id = uuid4()
        provider_id = uuid4()

        from rag_solution.core.exceptions import NotFoundError

        service.user_repository.get_by_id.side_effect = NotFoundError("User not found")

        with pytest.raises(NotFoundError):
            service.set_user_preferred_provider(user_id, provider_id)

        service.user_repository.get_by_id.assert_called_once_with(user_id)

    @pytest.mark.skip(reason="Method doesn't exist in current UserService implementation")
    # DISABLED: activate_user method doesn't exist in UserService
    def test_activate_user_success_disabled(self, service):
        """Test successful user activation."""
        user_id = uuid4()

        service.user_repository.activate_user.return_value = True

        result = service.activate_user(user_id)

        assert result is True
        service.user_repository.activate_user.assert_called_once_with(user_id)

    @pytest.mark.skip(reason="Method doesn't exist in current UserService implementation")
    # DISABLED: deactivate_user method doesn't exist in UserService
    def test_deactivate_user_success_disabled(self, service):
        """Test successful user deactivation."""
        user_id = uuid4()

        service.user_repository.deactivate_user.return_value = True

        result = service.deactivate_user(user_id)

        assert result is True
        service.user_repository.deactivate_user.assert_called_once_with(user_id)

    @pytest.mark.skip(reason="Method doesn't exist in current UserService implementation")
    # DISABLED: is_user_admin method doesn't exist in UserService
    def test_is_user_admin_true_disabled(self, service):
        """Test checking if user is admin - returns True."""
        user_id = uuid4()

        service.user_repository.is_admin.return_value = True

        result = service.is_user_admin(user_id)

        assert result is True
        service.user_repository.is_admin.assert_called_once_with(user_id)

    @pytest.mark.skip(reason="Method doesn't exist in current UserService implementation")
    # DISABLED: is_user_admin method doesn't exist in UserService
    def test_is_user_admin_false_disabled(self, service):
        """Test checking if user is admin - returns False."""
        user_id = uuid4()

        service.user_repository.is_admin.return_value = False

        result = service.is_user_admin(user_id)

        assert result is False
        service.user_repository.is_admin.assert_called_once_with(user_id)

    def test_repository_error_handling(self, service):
        """Test service handles repository errors appropriately."""
        user_id = uuid4()

        service.user_repository.get_by_id.side_effect = Exception("Database connection error")

        with pytest.raises(Exception) as exc_info:
            service.get_user_by_id(user_id)

        assert "Database connection error" in str(exc_info.value)
        service.user_repository.get_by_id.assert_called_once_with(user_id)
