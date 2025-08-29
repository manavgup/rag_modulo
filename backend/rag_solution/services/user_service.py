from uuid import UUID

from fastapi import HTTPException
from pydantic import EmailStr
from sqlalchemy.orm import Session

from core.logging_utils import get_logger
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
        """Creates a new user with validation."""
        try:
            # First attempt to create the user
            user = self.user_repository.create(user_input)

            # Then initialize user defaults
            try:
                provider, templates, parameters = self.user_provider_service.initialize_user_defaults(user.id)
                if not provider or not templates or len(templates) < 2 or not parameters:
                    self.db.rollback()
                    raise HTTPException(status_code=500, detail="Failed to initialize required user configuration")

                self.db.commit()
                return user

            except Exception as e:
                # If default initialization fails, rollback user creation
                self.db.rollback()
                logger.error(f"Error initializing user defaults: {e!s}")
                raise HTTPException(status_code=500, detail="Failed to initialize user configuration") from e

        except ValueError as e:
            # Handle known validation errors from repository
            logger.warning(f"Validation error in user creation: {e!s}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error in user creation: {e!s}")
            raise HTTPException(status_code=500, detail="Internal server error during user creation") from e

    def get_or_create_user_by_fields(self, ibm_id: str, email: EmailStr, name: str, role: str = "user") -> UserOutput:
        """Gets existing user or creates new one by fields."""
        return self.get_or_create_user(UserInput(ibm_id=ibm_id, email=email, name=name, role=role))

    def get_or_create_user(self, user_input: UserInput) -> UserOutput:
        """Gets existing user or creates new one from input model."""
        try:
            user = self.user_repository.get_by_ibm_id(user_input.ibm_id)
            if not user:
                return self.create_user(user_input)
            return user
        except ValueError as e:
            logger.error(f"Failed to get/create user: {e!s}")
            raise HTTPException(status_code=400, detail=str(e)) from e

    def get_user_by_id(self, user_id: UUID) -> UserOutput:
        """Gets user by ID with validation."""
        logger.info(f"Fetching user with id: {user_id}")
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            logger.warning(f"User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        return user

    def get_user_by_ibm_id(self, ibm_id: str) -> UserOutput:
        """Gets user by IBM ID with validation."""
        logger.info(f"Fetching user with IBM ID: {ibm_id}")
        user = self.user_repository.get_by_ibm_id(ibm_id)
        if user is None:
            logger.warning(f"User not found with IBM ID: {ibm_id}")
            raise HTTPException(status_code=404, detail="User not found")
        return user

    def update_user(self, user_id: UUID, user_update: UserInput) -> UserOutput:
        """Updates user with validation."""
        logger.info(f"Updating user {user_id}")
        try:
            user = self.user_repository.update(user_id, user_update)
            if user is None:
                logger.warning(f"User not found for update: {user_id}")
                raise HTTPException(status_code=404, detail="User not found")
            logger.info(f"User {user_id} updated successfully")
            return user
        except ValueError as e:
            logger.error(f"Failed to update user: {e!s}")
            raise HTTPException(status_code=400, detail=str(e)) from e

    def delete_user(self, user_id: UUID) -> bool:
        """Deletes user with validation."""
        logger.info(f"Deleting user: {user_id}")
        if not self.user_repository.delete(user_id):
            logger.warning(f"User not found for deletion: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        logger.info(f"User {user_id} deleted successfully")
        return True

    def list_users(self, skip: int = 0, limit: int = 100) -> list[UserOutput]:
        """Lists users with pagination."""
        logger.info(f"Listing users with skip={skip} and limit={limit}")
        try:
            users = self.user_repository.list_users(skip, limit)
            logger.info(f"Retrieved {len(users)} users")
            return users
        except Exception as e:
            logger.error(f"Unexpected error listing users: {e!s}")
            raise HTTPException(status_code=500, detail="Internal server error") from e

    def get_user(self, user_id: UUID) -> UserOutput:
        """Get user by ID (alias for get_user_by_id)."""
        return self.get_user_by_id(user_id)

    def set_user_preferred_provider(self, user_id: UUID, provider_id: UUID) -> UserOutput:
        """Set user's preferred provider."""
        # This would typically update the user's preferred_provider_id field
        # For now, return the user as-is
        return self.get_user_by_id(user_id)
