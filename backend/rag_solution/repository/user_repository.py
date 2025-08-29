from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from core.logging_utils import get_logger
from rag_solution.models.user import User
from rag_solution.schemas.user_schema import UserInput, UserOutput

logger = get_logger(__name__)


class UserRepository:
    """Repository for handling User entity database operations."""

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db

    def create(self, user_input: UserInput) -> UserOutput:
        try:
            user = User(**user_input.model_dump())
            self.db.add(user)
            self.db.commit()  # Assume service manages rollback if needed
            self.db.refresh(user)
            return UserOutput.model_validate(user)
        except IntegrityError as e:
            self.db.rollback()  # Only rollback in case of failure
            if "ix_users_ibm_id" in str(e):
                raise ValueError("IBM ID already exists")
            elif "ix_users_email" in str(e):
                raise ValueError("Email already exists")
            raise ValueError("An error occurred while creating the user")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating user: {e!s}")
            raise

    def get_by_id(self, user_id: UUID) -> UserOutput | None:
        """Fetches user by ID with team relationships."""
        try:
            user = self.db.query(User).filter(User.id == user_id).options(joinedload(User.teams)).first()
            return UserOutput.model_validate(user, from_attributes=True) if user else None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e!s}")
            raise

    def get_by_ibm_id(self, ibm_id: str) -> UserOutput | None:
        """Fetches user by IBM ID."""
        try:
            user = self.db.query(User).filter(User.ibm_id == ibm_id).options(joinedload(User.teams)).first()
            return UserOutput.model_validate(user) if user else None
        except Exception as e:
            logger.error(f"Error getting user by IBM ID {ibm_id}: {e!s}")
            raise

    def update(self, user_id: UUID, user_update: UserInput) -> UserOutput | None:
        """Updates user data with validation."""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return None

            # Update fields
            for key, value in user_update.model_dump(exclude_unset=True).items():
                setattr(user, key, value)

            self.db.commit()
            self.db.refresh(user)
            return UserOutput.model_validate(user)
        except IntegrityError as e:
            self.db.rollback()
            if "ix_users_ibm_id" in str(e):
                raise ValueError("IBM ID already exists")
            elif "ix_users_email" in str(e):
                raise ValueError("Email already exists")
            raise ValueError("An error occurred while updating the user")
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e!s}")
            self.db.rollback()
            raise

    def delete(self, user_id: UUID) -> bool:
        """Deletes a user and returns success status."""
        try:
            result = self.db.query(User).filter(User.id == user_id).delete()
            self.db.commit()
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e!s}")
            self.db.rollback()
            raise

    def list_users(self, skip: int = 0, limit: int = 100) -> list[UserOutput]:
        """Lists users with pagination."""
        try:
            users = self.db.query(User).options(joinedload(User.teams)).offset(skip).limit(limit).all()
            return [UserOutput.model_validate(user) for user in users]
        except Exception as e:
            logger.error(f"Error listing users: {e!s}")
            raise
