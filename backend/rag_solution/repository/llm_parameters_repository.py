from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput, LLMParametersOutput
from core.custom_exceptions import NotFoundError
from core.logging_utils import get_logger

logger = get_logger("repository.llm_parameters")

class LLMParametersRepository:
    """Repository for managing LLM Parameters in the database."""

    def __init__(self, db: Session) -> None:
        """Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(self, user_id: UUID, params: LLMParametersInput) -> LLMParametersOutput:
        """Create new LLM Parameters for a user.
        
        Args:
            user_id: UUID of the user who owns these parameters
            params: Parameters to create
            
        Returns:
            LLMParametersOutput: Created parameters
        """
        db_params = LLMParameters(**params.model_dump(), user_id=user_id)
        self.db.add(db_params)
        self.db.commit()
        self.db.refresh(db_params)
        return LLMParametersOutput.model_validate(db_params)

    def get_by_id(self, parameter_id: UUID) -> Optional[LLMParametersOutput]:
        """Get LLM Parameters by ID.
        
        Args:
            parameter_id: UUID of the parameters to retrieve
            
        Returns:
            Optional[LLMParametersOutput]: Parameters if found, None otherwise
        """
        db_params = (
            self.db.query(LLMParameters)
            .filter(LLMParameters.id == parameter_id)
            .first()
        )
        return LLMParametersOutput.model_validate(db_params) if db_params else None

    def update(self, parameter_id: UUID, params: LLMParametersInput) -> LLMParametersOutput:
        """Update existing LLM Parameters.
        
        Args:
            parameter_id: UUID of the parameters to update
            params: New parameter values
            
        Returns:
            LLMParametersOutput: Updated parameters
            
        Raises:
            NotFoundError: If parameters not found
        """
        logger.debug(f"Type of params received in update: {type(params)}")
        db_params = (
            self.db.query(LLMParameters)
            .filter(LLMParameters.id == parameter_id)
            .first()
        )
        if not db_params:
            raise NotFoundError(
                resource_id=str(parameter_id),
                resource_type="LLMParameters",
                message=f"LLMParameters with ID {parameter_id} not found"
            )

        param_dict = params.model_dump(exclude_unset=True)
        for field, value in param_dict.items():
            setattr(db_params, field, value)

        self.db.commit()
        self.db.refresh(db_params)
        return LLMParametersOutput.model_validate(db_params)

    def delete(self, parameter_id: UUID) -> None:
        """Delete LLM Parameters.
        
        Args:
            parameter_id: UUID of the parameters to delete
            
        Raises:
            NotFoundError: If parameters not found
        """
        db_params = (
            self.db.query(LLMParameters)
            .filter(LLMParameters.id == parameter_id)
            .first()
        )
        if not db_params:
            raise NotFoundError(
                resource_id=str(parameter_id),
                resource_type="LLMParameters",
                message=f"LLMParameters with ID {parameter_id} not found"
            )

        self.db.delete(db_params)
        self.db.commit()

    def delete_by_user_id(self, user_id: UUID) -> None:
        """Delete all LLM Parameters for a user.
        
        Args:
            user_id: UUID of the user whose parameters should be deleted
        """
        (
            self.db.query(LLMParameters)
            .filter(LLMParameters.user_id == user_id)
            .delete()
        )
        self.db.commit()

    def get_default_parameters(self, user_id: UUID) -> Optional[LLMParametersOutput]:
        """Get default LLM Parameters for a user.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            Optional[LLMParametersOutput]: Default parameters if they exist, None otherwise
        """
        db_params = (
            self.db.query(LLMParameters)
            .filter(
                LLMParameters.user_id == user_id,
                LLMParameters.is_default.is_(True)
            )
            .first()
        )
        return LLMParametersOutput.model_validate(db_params) if db_params else None

    def reset_default_parameters(self, user_id: UUID) -> None:
        """Reset default flag for all of a user's parameters.
        
        Args:
            user_id: UUID of the user
        """
        (
            self.db.query(LLMParameters)
            .filter(
                LLMParameters.user_id == user_id,
                LLMParameters.is_default.is_(True)
            )
            .update({"is_default": False})
        )
        self.db.commit()

    def get_parameters_by_user_id(self, user_id: UUID) -> List[LLMParametersOutput]:
        """Get all LLM Parameters for a user.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            List[LLMParametersOutput]: List of all parameters for the user
        """
        db_params = (
            self.db.query(LLMParameters)
            .filter(LLMParameters.user_id == user_id)
            .all()
        )
        return [LLMParametersOutput.model_validate(p) for p in db_params]