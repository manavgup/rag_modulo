from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, List
from rag_solution.repository.llm_parameters_repository import LLMParametersRepository
from rag_solution.schemas.llm_parameters_schema import (
    LLMParametersInput,
    LLMParametersOutput,
    LLMParametersInDB
)
from rag_solution.models.llm_parameters import LLMParameters
from core.custom_exceptions import NotFoundException


class LLMParametersService:
    """
    Service layer for managing LLM Parameters.
    Handles business logic, validation, and repository interaction.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = LLMParametersRepository(db)
    
    def create_parameters(self, user_id: UUID, parameters_input: LLMParametersInput) -> LLMParametersOutput:
        """
        Create new LLM Parameters for a user.

        Args:
            user_id (UUID): ID of the user.
            parameters_input (LLMParametersInput): Input data for creating parameters.

        Returns:
            LLMParametersOutput: Created parameters.
        """
        new_params = self.repository.create_or_update_by_user_id(user_id, parameters_input)
        return LLMParametersOutput.model_validate(new_params)

    def update_parameters(self, parameter_id: UUID, parameters_input: LLMParametersInput) -> LLMParametersOutput:
        """
        Update existing LLM Parameters.

        Args:
            parameter_id (UUID): ID of the parameters to update.
            parameters_input (LLMParametersInput): Updated parameters data.

        Returns:
            LLMParametersOutput: Updated parameters.
        """
        updated_params = self.repository.update(parameter_id, parameters_input)
        return LLMParametersOutput.model_validate(updated_params)

    def create_or_update_parameters(self, user_id: UUID, parameters_input: LLMParametersInput) -> LLMParametersOutput:
        """
        Create new or update existing LLM Parameters for a user.

        Args:
            user_id (UUID): ID of the user.
            parameters_input (LLMParametersInput): Input data for creating/updating parameters.

        Returns:
            LLMParametersOutput: Created or updated parameters.
        """
        existing_params = self.repository.get_by_user_id(user_id)
        if existing_params:
            # Update existing parameters
            updated_params = self.repository.update(existing_params.id, parameters_input)
            return LLMParametersOutput.model_validate(updated_params)
        else:
            # Create new parameters
            new_params = self.repository.create_or_update_by_user_id(user_id, parameters_input)
            return LLMParametersOutput.model_validate(new_params)

    def delete_parameters(self, parameter_id: UUID) -> bool:
        """
        Delete LLM Parameters.

        Args:
            parameter_id (UUID): ID of the parameters to delete.

        Returns:
            bool: True if deletion was successful.
        """
        return self.repository.delete(parameter_id)

    def set_default_parameters(self, parameter_id: UUID) -> LLMParametersOutput:
        """
        Set specific parameters as default for a user.

        Args:
            parameter_id (UUID): ID of the parameters to set as default.

        Returns:
            LLMParametersOutput: Updated default parameters.
        """
        existing_params = self.repository.get_by_id(parameter_id)
        if not existing_params:
            raise NotFoundException("LLM Parameters", parameter_id)

        # Reset other default parameters for the same user
        self.repository.reset_user_default_parameters(existing_params.user_id)

        # Create an input with is_default set to True
        default_input = LLMParametersInput(
            **existing_params.__dict__,
            is_default=True
        )

        # Update parameters to set as default
        updated_params = self.repository.update(parameter_id, default_input)
        return LLMParametersOutput.model_validate(updated_params)

    def get_parameters(self, user_id: UUID) -> List[LLMParametersOutput]:
        """
        Fetch LLM Parameters for a specific user.

        Args:
            user_id (UUID): ID of the user.

        Returns:
            List[LLMParametersOutput]: List of user's parameters.
        """
        llm_params = self.repository.get_by_user_id(user_id)
        return [LLMParametersOutput.model_validate(params) for params in llm_params]