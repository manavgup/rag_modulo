from uuid import UUID

from pydantic import EmailStr
from sqlalchemy.orm import Session

from core.logging_utils import get_logger
from rag_solution.core.exceptions import NotFoundError, ValidationError
from rag_solution.repository.user_repository import UserRepository
from rag_solution.schemas.user_schema import UserInput, UserOutput
from rag_solution.services.user_provider_service import UserProviderService

logger = get_logger(__name__)


class UserService:
    """Service for managing user-related operations."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
        self.user_repository = UserRepository(db)
        self.user_provider_service = UserProviderService(db)

    def create_user(self, user_input: UserInput) -> UserOutput:
        """Creates a new user with validation.

        Raises:
            AlreadyExistsError: If user with IBM ID or email already exists
            ValidationError: If user data is invalid
        """
        # Create the user - repository will raise exceptions if needed
        user = self.user_repository.create(user_input)

        # Initialize user defaults
        provider, templates, parameters = self.user_provider_service.initialize_user_defaults(user.id)

        # Validate that all required defaults were created
        if not provider or not templates or len(templates) < 2 or not parameters:
            self.db.rollback()
            raise ValidationError("Failed to initialize required user configuration")

        self.db.commit()
        return user

    def get_or_create_user_by_fields(self, ibm_id: str, email: EmailStr, name: str, role: str = "user") -> UserOutput:
        """Gets existing user or creates new one by fields."""
        return self.get_or_create_user(UserInput(ibm_id=ibm_id, email=email, name=name, role=role, preferred_provider_id=None))

    def get_or_create_user(self, user_input: UserInput) -> UserOutput:
        """Gets existing user or creates new one from input model."""
        try:
            return self.user_repository.get_by_ibm_id(user_input.ibm_id)
        except NotFoundError:
            # User doesn't exist, create a new one
            return self.create_user(user_input)

    def get_user_by_id(self, user_id: UUID) -> UserOutput:
        """Gets user by ID.

        Raises:
            NotFoundError: If user not found
        """
        logger.info(f"Fetching user with id: {user_id}")
        return self.user_repository.get_by_id(user_id)

    def get_user_by_ibm_id(self, ibm_id: str) -> UserOutput:
        """Gets user by IBM ID.

        Raises:
            NotFoundError: If user not found
        """
        logger.info(f"Fetching user with IBM ID: {ibm_id}")
        return self.user_repository.get_by_ibm_id(ibm_id)

    def update_user(self, user_id: UUID, user_update: UserInput) -> UserOutput:
        """Updates user.

        Raises:
            NotFoundError: If user not found
            AlreadyExistsError: If new IBM ID or email already exists
            ValidationError: If data is invalid
        """
        logger.info(f"Updating user {user_id}")
        user = self.user_repository.update(user_id, user_update)
        logger.info(f"User {user_id} updated successfully")
        return user

    def delete_user(self, user_id: UUID) -> None:
        """Deletes user.

        Raises:
            NotFoundError: If user not found
        """
        logger.info(f"Deleting user: {user_id}")
        self.user_repository.delete(user_id)
        logger.info(f"User {user_id} deleted successfully")

    def list_users(self, skip: int = 0, limit: int = 100) -> list[UserOutput]:
        """Lists users with pagination."""
        logger.info(f"Listing users with skip={skip} and limit={limit}")
        users = self.user_repository.list_users(skip, limit)
        logger.info(f"Retrieved {len(users)} users")
        return users

    def get_user(self, user_id: UUID) -> UserOutput:
        """Get user by ID (alias for get_user_by_id)."""
        return self.get_user_by_id(user_id)

    def set_user_preferred_provider(self, user_id: UUID, _provider_id: UUID) -> UserOutput:
        """Set user's preferred provider."""
        # This would typically update the user's preferred_provider_id field
        # For now, return the user as-is
        return self.get_user_by_id(user_id)
