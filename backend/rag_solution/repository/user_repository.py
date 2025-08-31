from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from core.custom_exceptions import RepositoryError
from core.logging_utils import get_logger
from rag_solution.core.exceptions import AlreadyExistsError, NotFoundError, ValidationError
from rag_solution.models.user import User
from rag_solution.schemas.user_schema import UserInput, UserOutput

logger = get_logger(__name__)


class UserRepository:
    """Repository for handling User entity database operations."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db

    def create(self, user_input: UserInput) -> UserOutput:
        """Create a new user.

        Raises:
            AlreadyExistsError: If IBM ID or email already exists
            RepositoryError: For other database errors
        """
        try:
            user = User(**user_input.model_dump())
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return UserOutput.model_validate(user)
        except IntegrityError as e:
            self.db.rollback()
            if "ix_users_ibm_id" in str(e):
                raise AlreadyExistsError("User", "ibm_id", user_input.ibm_id) from e
            elif "ix_users_email" in str(e):
                raise AlreadyExistsError("User", "email", user_input.email) from e
            raise ValidationError("An error occurred while creating the user") from e
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating user: {e!s}")
            raise RepositoryError(f"Failed to create user: {e!s}") from e

    def get_by_id(self, user_id: UUID) -> UserOutput:
        """Fetches user by ID with team relationships.

        Raises:
            NotFoundError: If user not found
            RepositoryError: For database errors
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).options(joinedload(User.teams)).first()
            if not user:
                raise NotFoundError("User", resource_id=str(user_id))
            return UserOutput.model_validate(user, from_attributes=True)
        except NotFoundError:
            raise  # Re-raise domain exceptions
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e!s}")
            raise RepositoryError(f"Failed to get user by ID: {e!s}") from e

    def get_by_ibm_id(self, ibm_id: str) -> UserOutput:
        """Fetches user by IBM ID.

        Raises:
            NotFoundError: If user not found
            RepositoryError: For database errors
        """
        try:
            user = self.db.query(User).filter(User.ibm_id == ibm_id).options(joinedload(User.teams)).first()
            if not user:
                raise NotFoundError("User", identifier=f"ibm_id={ibm_id}")
            return UserOutput.model_validate(user)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting user by IBM ID {ibm_id}: {e!s}")
            raise RepositoryError(f"Failed to get user by IBM ID: {e!s}") from e

    def update(self, user_id: UUID, user_update: UserInput) -> UserOutput:
        """Updates user data with validation.

        Raises:
            NotFoundError: If user not found
            AlreadyExistsError: If IBM ID or email already exists
            RepositoryError: For database errors
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise NotFoundError("User", resource_id=str(user_id))

            # Update fields
            for key, value in user_update.model_dump(exclude_unset=True).items():
                setattr(user, key, value)

            self.db.commit()
            self.db.refresh(user)
            return UserOutput.model_validate(user)
        except NotFoundError:
            raise
        except IntegrityError as e:
            self.db.rollback()
            if "ix_users_ibm_id" in str(e):
                raise AlreadyExistsError("User", "ibm_id", user_update.ibm_id) from e
            elif "ix_users_email" in str(e):
                raise AlreadyExistsError("User", "email", user_update.email) from e
            raise ValidationError("An error occurred while updating the user") from e
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e!s}")
            self.db.rollback()
            raise RepositoryError(f"Failed to update user: {e!s}") from e

    def delete(self, user_id: UUID) -> bool:
        """Deletes a user and returns success status."""
        try:
            result = self.db.query(User).filter(User.id == user_id).delete()
            self.db.commit()
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e!s}")
            self.db.rollback()
            raise RepositoryError(f"Failed to delete user: {e!s}") from e

    def list_users(self, skip: int = 0, limit: int = 100) -> list[UserOutput]:
        """Lists users with pagination."""
        try:
            users = self.db.query(User).options(joinedload(User.teams)).offset(skip).limit(limit).all()
            return [UserOutput.model_validate(user) for user in users]
        except Exception as e:
            logger.error(f"Error listing users: {e!s}")
            raise RepositoryError(f"Failed to list users: {e!s}") from e
