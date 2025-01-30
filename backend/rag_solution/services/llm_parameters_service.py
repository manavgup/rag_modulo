from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from rag_solution.repository.llm_parameters_repository import LLMParametersRepository
from rag_solution.schemas.llm_parameters_schema import (
    LLMParametersInput,
    LLMParametersOutput,
)
from core.custom_exceptions import NotFoundException, ValidationError


class LLMParametersService:
    """Service for managing LLM Parameters with business logic."""

    def __init__(self, db: Session) -> None:
        """Initialize service with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.repository = LLMParametersRepository(db)

    def create_parameters(self, user_id: UUID, parameters: LLMParametersInput) -> LLMParametersOutput:
        """Create new LLM parameters.
        
        Args:
            user_id: UUID of the user
            parameters: Parameters to create
            
        Returns:
            LLMParametersOutput: Created parameters
        """
        return self.repository.create(user_id, parameters)

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
        updated_params = self.repository.update(parameter_id, parameters)
        if not updated_params:
            raise NotFoundException(
                resource_type="LLM Parameters",
                resource_id=str(parameter_id),
                message=f"LLM Parameters with id {parameter_id} not found."
            )
        return updated_params

    def create_or_update_parameters(self, user_id: UUID, parameters: LLMParametersInput) -> LLMParametersOutput:
        """Create new parameters or update existing default parameters.
        
        Args:
            user_id: UUID of the user
            parameters: Parameters to create or update
            
        Returns:
            LLMParametersOutput: Created or updated parameters
        """
        existing_params = self.repository.get_default_parameters(user_id)
        if existing_params:
            return self.update_parameters(existing_params.id, parameters)
        return self.create_parameters(user_id, parameters)

    def delete_parameters(self, parameter_id: UUID) -> None:
        """Delete LLM parameters.
        
        Args:
            parameter_id: UUID of the parameters to delete
            
        Raises:
            NotFoundException: If parameters not found
        """
        self.repository.delete(parameter_id)

    def set_default_parameters(self, parameter_id: UUID) -> LLMParametersOutput:
        """Set parameters as default, resetting any existing defaults.
        
        Args:
            parameter_id: UUID of the parameters to make default
            
        Returns:
            LLMParametersOutput: Updated parameters
            
        Raises:
            NotFoundException: If parameters not found
        """
        existing_params = self.repository.get_by_id(parameter_id)
        if not existing_params:
            raise NotFoundException(
                resource_type="LLM Parameters",
                resource_id=str(parameter_id),
                message=f"LLM Parameters with ID {parameter_id} not found."
            )

        self.repository.reset_default_parameters(existing_params.user_id)
        
        default_params = LLMParametersInput(
            **existing_params.model_dump(),
            is_default=True
        )
        
        return self.repository.update(parameter_id, default_params)

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
            name="Default Configuration",
            description="Default LLM parameters configuration",
            max_new_tokens=100,
            temperature=0.7,
            top_k=50,
            top_p=1.0,
            repetition_penalty=1.1,
            is_default=True
        )
        
        return self.create_parameters(user_id, default_params)

    def get_latest_or_default_parameters(self, user_id: UUID) -> LLMParametersOutput:
        """Get default parameters or latest parameters if no default exists.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            LLMParametersOutput: Default or latest parameters
            
        Raises:
            ValidationError: If no parameters exist for the user
        """
        default_params = self.repository.get_default_parameters(user_id)
        if default_params:
            return default_params

        all_params = self.repository.get_parameters_by_user_id(user_id)
        if not all_params:
            raise ValidationError("No parameters found for user")

        return max(all_params, key=lambda p: p.updated_at)