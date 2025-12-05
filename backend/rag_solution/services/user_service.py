from typing import Any

from pydantic import UUID4, EmailStr
from sqlalchemy.orm import Session

from core.config import Settings
from core.logging_utils import get_logger
from rag_solution.core.exceptions import NotFoundError, ValidationError
from rag_solution.repository.user_repository import UserRepository
from rag_solution.schemas.user_schema import UserInput, UserOutput
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.services.user_provider_service import UserProviderService

logger = get_logger(__name__)

# Minimum number of required templates for user initialization
# Includes: RAG_QUERY, QUESTION_GENERATION, PODCAST_GENERATION
MIN_REQUIRED_TEMPLATES = 3


class UserService:
    """Service for managing user-related operations."""

    def __init__(self: Any, db: Session, settings: Settings) -> None:
        """Initialize with database session and settings."""
        self.db = db
        self.settings = settings
        self.user_repository = UserRepository(db)
        self.user_provider_service = UserProviderService(db, settings)
        self.prompt_template_service = PromptTemplateService(db)

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

        # Validate that all required defaults were created (RAG, Question, Podcast)
        if not provider or not templates or len(templates) < MIN_REQUIRED_TEMPLATES or not parameters:
            self.db.rollback()
            raise ValidationError("Failed to initialize required user configuration")

        self.db.commit()
        return user

    def get_or_create_user_by_fields(self, ibm_id: str, email: EmailStr, name: str, role: str = "user") -> UserOutput:
        """Gets existing user or creates new one by fields."""
        return self.get_or_create_user(
            UserInput(ibm_id=ibm_id, email=email, name=name, role=role, preferred_provider_id=None)
        )

    def get_user_by_email(self, email: str) -> UserOutput:
        """Gets user by email address.

        Args:
            email: The email address to look up

        Returns:
            UserOutput: The user with the given email

        Raises:
            NotFoundError: If user not found
        """
        logger.info("Fetching user with email: %s", email)
        return self.user_repository.get_by_email(email)

    def get_or_create_by_email(self, email: EmailStr, name: str | None = None, role: str = "user") -> UserOutput:
        """Gets existing user by email or creates new one.

        This method first looks up the user by email address. If found, returns
        the existing user. If not found, creates a new user using the email
        as both the email and ibm_id (for trusted proxy scenarios).

        This is the preferred method for trusted proxy authentication where
        user identity comes from an email header.

        Args:
            email: The email address (used for lookup and as ibm_id for new users)
            name: Optional display name (defaults to email prefix if not provided)
            role: User role (defaults to "user")

        Returns:
            UserOutput: The existing or newly created user with all defaults initialized

        Note:
            For existing users, ensures required defaults (templates, parameters)
            are present, reinitializing them if necessary.
        """
        try:
            existing_user = self.user_repository.get_by_email(email)

            # Defensive check: Ensure user has required defaults
            templates = self.prompt_template_service.get_user_templates(existing_user.id)

            if not templates or len(templates) < MIN_REQUIRED_TEMPLATES:
                logger.warning(
                    "User %s (email=%s) exists but missing defaults - attempting recovery...",
                    existing_user.id,
                    email,
                )
                try:
                    _, reinit_templates, parameters = self.user_provider_service.initialize_user_defaults(
                        existing_user.id
                    )
                    logger.info(
                        "✅ Successfully recovered user %s: %d templates, %s parameters",
                        existing_user.id,
                        len(reinit_templates),
                        "created" if parameters else "failed",
                    )
                except Exception as e:
                    logger.error("❌ Failed to recover user %s: %s", existing_user.id, str(e))
                    raise ValidationError(
                        f"User {existing_user.id} missing required defaults and recovery failed: {e}",
                        field="user_initialization",
                    ) from e

            return existing_user
        except NotFoundError:
            # User doesn't exist by email, create with email as ibm_id
            display_name = name if name else email.split("@")[0]
            logger.info("Creating new user for email: %s", email)
            return self.create_user(
                UserInput(ibm_id=email, email=email, name=display_name, role=role, preferred_provider_id=None)
            )

    def get_or_create_user(self, user_input: UserInput) -> UserOutput:
        """Gets existing user or creates new one, ensuring all required defaults exist.

        This method provides defensive initialization to handle edge cases where users
        may exist in the database but are missing required defaults (e.g., after database
        wipes, failed initializations, or data migrations).

        Args:
            user_input: User data for creation or lookup

        Returns:
            UserOutput: User with all required defaults initialized

        Note:
            Automatically reinitializes missing defaults (templates, parameters, pipelines)
            for existing users. This adds one DB query per user access but prevents
            silent failures during collection creation or search operations.
        """
        try:
            existing_user = self.user_repository.get_by_ibm_id(user_input.ibm_id)

            # Defensive check: Ensure user has required defaults
            # Handles edge case where user exists after DB wipe but missing defaults
            templates = self.prompt_template_service.get_user_templates(existing_user.id)

            if not templates or len(templates) < MIN_REQUIRED_TEMPLATES:
                logger.warning(
                    "User %s exists but missing defaults (has %d/%d templates) - attempting recovery...",
                    existing_user.id,
                    len(templates) if templates else 0,
                    MIN_REQUIRED_TEMPLATES,
                )
                try:
                    _, reinit_templates, parameters = self.user_provider_service.initialize_user_defaults(
                        existing_user.id
                    )
                    logger.info(
                        "✅ Successfully recovered user %s: %d templates, %s parameters",
                        existing_user.id,
                        len(reinit_templates),
                        "created" if parameters else "failed",
                    )
                except Exception as e:
                    logger.error("❌ Failed to recover user %s: %s", existing_user.id, str(e))
                    raise ValidationError(
                        f"User {existing_user.id} missing required defaults and recovery failed: {e}",
                        field="user_initialization",
                    ) from e

            return existing_user
        except NotFoundError:
            # User doesn't exist, create with full initialization
            return self.create_user(user_input)

    def get_user_by_id(self, user_id: UUID4) -> UserOutput:
        """Gets user by ID.

        Raises:
            NotFoundError: If user not found
        """
        logger.info("Fetching user with id: %s", user_id)
        return self.user_repository.get_by_id(user_id)

    def get_user_by_ibm_id(self, ibm_id: str) -> UserOutput:
        """Gets user by IBM ID.

        Raises:
            NotFoundError: If user not found
        """
        logger.info("Fetching user with IBM ID: %s", ibm_id)
        return self.user_repository.get_by_ibm_id(ibm_id)

    def update_user(self, user_id: UUID4, user_update: UserInput) -> UserOutput:
        """Updates user.

        Raises:
            NotFoundError: If user not found
            AlreadyExistsError: If new IBM ID or email already exists
            ValidationError: If data is invalid
        """
        logger.info("Updating user %s", user_id)
        user = self.user_repository.update(user_id, user_update)
        logger.info("User %s updated successfully", user_id)
        return user

    def delete_user(self, user_id: UUID4) -> None:
        """Deletes user.

        Raises:
            NotFoundError: If user not found
        """
        logger.info("Deleting user: %s", user_id)
        self.user_repository.delete(user_id)
        logger.info("User %s deleted successfully", user_id)

    def list_users(self, skip: int = 0, limit: int = 100) -> list[UserOutput]:
        """Lists users with pagination."""
        logger.info("Listing users with skip=%s and limit=%s", skip, limit)
        users = self.user_repository.list_users(skip, limit)
        logger.info("Retrieved %s users", len(users))
        return users

    def get_user(self, user_id: UUID4) -> UserOutput:
        """Get user by ID (alias for get_user_by_id)."""
        return self.get_user_by_id(user_id)

    def set_user_preferred_provider(self, user_id: UUID4, provider_id: UUID4) -> UserOutput:
        """Set user's preferred provider."""
        from rag_solution.schemas.user_schema import UserInput

        logger.info("Setting preferred provider for user %s to %s", user_id, provider_id)
        # Get current user to preserve other fields
        current_user = self.user_repository.get_by_id(user_id)
        # Create UserInput with updated preferred_provider_id
        user_update = UserInput(
            ibm_id=current_user.ibm_id,
            email=current_user.email,
            name=current_user.name,
            role=current_user.role,
            preferred_provider_id=provider_id,
        )
        user = self.user_repository.update(user_id, user_update)
        logger.info("User %s preferred provider updated successfully", user_id)
        return user
