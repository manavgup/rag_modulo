from uuid import UUID

from sqlalchemy.orm import Session

from core.custom_exceptions import NotFoundException
from core.logging_utils import get_logger
from rag_solution.repository.llm_parameters_repository import LLMParametersRepository
from rag_solution.schemas.llm_parameters_schema import (
    LLMParametersInput,
    LLMParametersOutput,
)

logger = get_logger("services.llm_parameters")


class LLMParametersService:
    """Service for managing LLM Parameters with clear CRUD operations."""

    def __init__(self, db: Session) -> None:
        self.repository = LLMParametersRepository(db)

    def create_parameters(self, parameters: LLMParametersInput) -> LLMParametersOutput:
        """Create new LLM parameters.

        Args:
            parameters: Parameters to create

        Returns:
            LLMParametersOutput: Created parameters
        """
        return self.repository.create(parameters)

    def get_parameters(self, parameter_id: UUID) -> LLMParametersOutput | None:
        """Retrieve specific LLM parameters.

        Args:
            parameter_id: UUID of the parameters to retrieve

        Returns:
            Optional[LLMParametersOutput]: Retrieved parameters or None
        """
        return self.repository.get_parameters(parameter_id)

    def get_user_parameters(self, user_id: UUID) -> list[LLMParametersOutput]:
        """Retrieve all parameters for a user.

        Args:
            user_id: UUID of the user

        Returns:
            List[LLMParametersOutput]: List of user's parameters
        """
        params = self.repository.get_parameters_by_user_id(user_id)

        # If user has no parameters, create default ones
        if not params:
            logger.info(f"No LLM parameters found for user {user_id}, creating default")
            try:
                default_params = self.initialize_default_parameters(user_id)
                if default_params:
                    return [default_params]
            except Exception as e:
                logger.error(f"Failed to create default parameters: {e!s}")

        return params if params else []

    def update_parameters(self, parameter_id: UUID, parameters: LLMParametersInput) -> LLMParametersOutput:
        """Update existing LLM parameters.

        Args:
            parameter_id: UUID of the parameters to update
            parameters: New parameter values

        Returns:
            LLMParametersOutput: Updated parameters

        Raises:
            NotFoundException: If parameters not found
        """
        return self.repository.update(parameter_id, parameters)

    def delete_parameters(self, parameter_id: UUID) -> None:
        """Delete specific LLM parameters.

        Args:
            parameter_id: UUID of the parameters to delete

        Raises:
            NotFoundException: If parameters not found
        """
        self.repository.delete(parameter_id)

    def set_default_parameters(self, parameter_id: UUID) -> LLMParametersOutput:
        """Set specific parameters as default for the user.

        Args:
            parameter_id: UUID of the parameters to make default

        Returns:
            LLMParametersOutput: Updated default parameters

        Raises:
            NotFoundException: If parameters not found
        """
        existing_params = self.repository.get_parameters(parameter_id)
        if not existing_params:
            raise NotFoundException(
                resource_type="LLM Parameters",
                resource_id=str(parameter_id),
                message=f"LLM Parameters with ID {parameter_id} not found.",
            )

        # Reset existing defaults for this user
        self.repository.reset_default_parameters(existing_params.user_id)

        # Create new input without duplicate is_default
        update_params = existing_params.to_input()
        update_params.is_default = True

        return self.repository.update(parameter_id, update_params)

    def initialize_default_parameters(self, user_id: UUID) -> LLMParametersOutput:
        """Initialize default parameters for a user if none exist.

        Args:
            user_id: UUID of the user

        Returns:
            LLMParametersOutput: Default parameters (existing or newly created)
        """
        existing_default = self.repository.get_default_parameters(user_id)
        if existing_default:
            return existing_default

        default_params = LLMParametersInput(
            user_id=user_id,
            name="Default Configuration",
            description="Default LLM parameters configuration",
            max_new_tokens=100,
            temperature=0.7,
            top_k=50,
            top_p=1.0,
            repetition_penalty=1.1,
            is_default=True,
        )

        return self.create_parameters(default_params)

    def get_latest_or_default_parameters(self, user_id: UUID) -> LLMParametersOutput | None:
        """Get default parameters or latest parameters if no default exists.

        Args:
            user_id: UUID of the user

        Returns:
            Optional[LLMParametersOutput]: Default or latest parameters, or None if creation fails
        """
        default_params = self.repository.get_default_parameters(user_id)
        if default_params:
            return default_params

        all_params = self.repository.get_parameters_by_user_id(user_id)
        if not all_params:
            # Auto-create default parameters for existing users
            logger.info(f"No parameters found for user {user_id}, initializing defaults")
            try:
                return self.initialize_default_parameters(user_id)
            except Exception as e:
                logger.error(f"Failed to initialize default parameters: {e!s}")
                return None

        return max(all_params, key=lambda p: p.updated_at)
