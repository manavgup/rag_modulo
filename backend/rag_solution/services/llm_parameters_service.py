from typing import Any

from pydantic import UUID4
from sqlalchemy.orm import Session

from core.config import Settings
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

    def __init__(self, db: Session, settings: Settings) -> None:
        self.repository = LLMParametersRepository(db)
        self.settings = settings

    @staticmethod
    def _to_output(value: Any) -> LLMParametersOutput:
        """Coerce repository return into LLMParametersOutput.

        Supports ORM instances and mocks by using from_attributes=True.
        """
        if isinstance(value, LLMParametersOutput):
            return value
        return LLMParametersOutput.model_validate(value, from_attributes=True)

    def create_parameters(self, parameters: LLMParametersInput) -> LLMParametersOutput:
        """Create new LLM parameters.

        Args:
            parameters: Parameters to create

        Returns:
            LLMParametersOutput: Created parameters
        """
        created = self.repository.create(parameters)
        return self._to_output(created)

    def get_parameters(self, parameter_id: UUID4) -> LLMParametersOutput | None:
        """Retrieve specific LLM parameters.

        Args:
            parameter_id: UUID of the parameters to retrieve

        Returns:
            Optional[LLMParametersOutput]: Retrieved parameters or None
        """
        result = self.repository.get_parameters(parameter_id)
        return None if result is None else self._to_output(result)

    def get_user_parameters(self, user_id: UUID4) -> list[LLMParametersOutput]:
        """Retrieve all parameters for a user.

        Args:
            user_id: UUID4 of the user

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

        return [self._to_output(p) for p in params] if params else []

    def update_parameters(self, parameter_id: UUID4, parameters: LLMParametersInput) -> LLMParametersOutput:
        """Update existing LLM parameters.

        Args:
            parameter_id: UUID of the parameters to update
            parameters: New parameter values

        Returns:
            LLMParametersOutput: Updated parameters

        Raises:
            NotFoundException: If parameters not found
        """
        updated = self.repository.update(parameter_id, parameters)
        return self._to_output(updated)

    def delete_parameters(self, parameter_id: UUID4) -> None:
        """Delete specific LLM parameters.

        Args:
            parameter_id: UUID of the parameters to delete

        Raises:
            NotFoundException: If parameters not found
        """
        self.repository.delete(parameter_id)

    def set_default_parameters(self, parameter_id: UUID4) -> LLMParametersOutput:
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

        updated = self.repository.update(parameter_id, update_params)
        return self._to_output(updated)

    def initialize_default_parameters(self, user_id: UUID4) -> LLMParametersOutput:
        """Initialize default parameters for a user if none exist.

        Args:
            user_id: UUID4 of the user

        Returns:
            LLMParametersOutput: Default parameters (existing or newly created)
        """
        existing_default = self.repository.get_default_parameters(user_id)
        if existing_default:
            return self._to_output(existing_default)

        default_params = LLMParametersInput(
            user_id=user_id,
            name="Default Configuration",
            description="Default LLM parameters configuration from .env settings",
            max_new_tokens=self.settings.max_new_tokens,
            temperature=self.settings.temperature,
            top_k=self.settings.top_k,
            top_p=self.settings.top_p,
            repetition_penalty=self.settings.repetition_penalty,
            is_default=True,
        )

        return self.create_parameters(default_params)

    def get_latest_or_default_parameters(self, user_id: UUID4) -> LLMParametersOutput | None:
        """Get default parameters or latest parameters if no default exists.

        Args:
            user_id: UUID4 of the user

        Returns:
            Optional[LLMParametersOutput]: Default or latest parameters, or None if creation fails
        """
        default_params = self.repository.get_default_parameters(user_id)
        if default_params:
            return self._to_output(default_params)

        all_params = self.repository.get_parameters_by_user_id(user_id)
        if not all_params:
            # Auto-create default parameters for existing users
            logger.info(f"No parameters found for user {user_id}, initializing defaults")
            try:
                return self.initialize_default_parameters(user_id)
            except Exception as e:
                logger.error(f"Failed to initialize default parameters: {e!s}")
                return None

        outputs = [self._to_output(p) for p in all_params]
        return max(outputs, key=lambda p: p.updated_at)
