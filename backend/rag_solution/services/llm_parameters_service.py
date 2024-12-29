"""Service for managing LLM generation parameters."""

from typing import List, Optional
from sqlalchemy.orm import Session

from core.logging_utils import get_logger
from core.custom_exceptions import (
    NotFoundException,
    ValidationError,
    LLMParameterError,
    DuplicateParameterError,
    DefaultParameterError
)
from rag_solution.repository.llm_parameters_repository import LLMParametersRepository
from rag_solution.schemas.llm_parameters_schema import (
    LLMParametersCreate,
    LLMParametersUpdate,
    LLMParametersResponse
)

logger = get_logger("service.llm_parameters")

class LLMParametersService:
    """Service for managing LLM generation parameters."""

    def __init__(self, db: Session) -> None:
        """Initialize service with database session."""
        self.repository = LLMParametersRepository(db)

    def create_parameters(self, params: LLMParametersCreate) -> LLMParametersResponse:
        """Create new LLM parameters.
        
        Args:
            params: Parameter set to create
            
        Returns:
            Created parameter set
            
        Raises:
            DuplicateParameterError: If parameters with same name already exist
            LLMParameterError: If parameter creation fails
        """
        try:
            # Check if parameters with same name already exist
            existing = self.repository.get_by_name(params.name)
            if existing:
                raise DuplicateParameterError(param_name=params.name)

            created_params = self.repository.create(params)
            logger.info(f"Created LLM parameters: {created_params.name}")
            return created_params
        except DuplicateParameterError:
            raise
        except Exception as e:
            logger.error(f"Error creating parameters: {str(e)}")
            raise LLMParameterError(
                param_name=params.name,
                error_type="creation_failed",
                message=f"Failed to create parameter set: {str(e)}"
            )

    def get_parameters(self, params_id: int) -> LLMParametersResponse:
        """Get LLM parameters by ID.
        
        Args:
            params_id: ID of parameters to retrieve
            
        Returns:
            Retrieved parameter set
            
        Raises:
            NotFoundException: If parameters not found
        """
        params = self.repository.get(params_id)
        if not params:
            raise NotFoundException(
                resource_type="LLMParameters",
                resource_id=params_id
            )
        return params

    def get_parameters_by_name(self, name: str) -> LLMParametersResponse:
        """Get LLM parameters by name.
        
        Args:
            name: Name of parameters to retrieve
            
        Returns:
            Retrieved parameter set
            
        Raises:
            NotFoundException: If parameters not found
        """
        params = self.repository.get_by_name(name)
        if not params:
            raise NotFoundException(
                resource_type="LLMParameters",
                resource_id=name,
                message=f"Parameter set with name '{name}' not found"
            )
        return params

    def get_default_parameters(self) -> LLMParametersResponse:
        """Get default LLM parameters.
        
        Returns:
            Default parameter set
            
        Raises:
            NotFoundException: If no default parameters found
        """
        params = self.repository.get_default()
        if not params:
            raise NotFoundException(
                resource_type="LLMParameters",
                resource_id="default",
                message="No default parameter set found"
            )
        return params

    def list_parameters(self, skip: int = 0, limit: int = 100) -> List[LLMParametersResponse]:
        """List all LLM parameters with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of parameter sets
        """
        return self.repository.list(skip=skip, limit=limit)

    def update_parameters(
        self, params_id: int, params: LLMParametersUpdate
    ) -> LLMParametersResponse:
        """Update LLM parameters.
        
        Args:
            params_id: ID of parameters to update
            params: Updated parameter values
            
        Returns:
            Updated parameter set
            
        Raises:
            NotFoundException: If parameters not found
            DuplicateParameterError: If update would create duplicate name
            LLMParameterError: If update fails
        """
        try:
            # If name is being updated, check for duplicates
            if params.name:
                existing = self.repository.get_by_name(params.name)
                if existing and existing.id != params_id:
                    raise DuplicateParameterError(param_name=params.name)

            updated_params = self.repository.update(params_id, params)
            if not updated_params:
                raise NotFoundException(
                    resource_type="LLMParameters",
                    resource_id=params_id
                )
                
            logger.info(f"Updated LLM parameters: {updated_params.name}")
            return updated_params
        except (NotFoundException, DuplicateParameterError):
            raise
        except Exception as e:
            logger.error(f"Error updating parameters: {str(e)}")
            raise LLMParameterError(
                param_name=str(params_id),
                error_type="update_failed",
                message=f"Failed to update parameter set: {str(e)}"
            )

    def delete_parameters(self, params_id: int) -> bool:
        """Delete LLM parameters.
        
        Args:
            params_id: ID of parameters to delete
            
        Returns:
            True if deleted successfully
            
        Raises:
            NotFoundException: If parameters not found
            DefaultParameterError: If attempting to delete default parameters
            LLMParameterError: If deletion fails
        """
        try:
            # Check if parameters exist and are not default
            params = self.repository.get(params_id)
            if not params:
                raise NotFoundException(
                    resource_type="LLMParameters",
                    resource_id=params_id
                )
                
            if params.is_default:
                raise DefaultParameterError(
                    operation="delete",
                    param_name=params.name
                )

            if self.repository.delete(params_id):
                logger.info(f"Deleted LLM parameters: {params.name}")
                return True
            return False
        except (NotFoundException, DefaultParameterError):
            raise
        except Exception as e:
            logger.error(f"Error deleting parameters: {str(e)}")
            raise LLMParameterError(
                param_name=str(params_id),
                error_type="deletion_failed",
                message=f"Failed to delete parameter set: {str(e)}"
            )

    def set_default_parameters(self, params_id: int) -> LLMParametersResponse:
        """Set parameters as default.
        
        Args:
            params_id: ID of parameters to set as default
            
        Returns:
            Updated parameter set
            
        Raises:
            NotFoundException: If parameters not found
            LLMParameterError: If operation fails
        """
        try:
            # Check if parameters exist
            params = self.repository.get(params_id)
            if not params:
                raise NotFoundException(
                    resource_type="LLMParameters",
                    resource_id=params_id
                )

            # Update to set as default
            update = LLMParametersUpdate(is_default=True)
            updated_params = self.repository.update(params_id, update)
            if not updated_params:
                raise NotFoundException(
                    resource_type="LLMParameters",
                    resource_id=params_id
                )

            logger.info(f"Set LLM parameters as default: {updated_params.name}")
            return updated_params
        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error setting default parameters: {str(e)}")
            raise LLMParameterError(
                param_name=str(params_id),
                error_type="set_default_failed",
                message=f"Failed to set parameter set as default: {str(e)}"
            )
