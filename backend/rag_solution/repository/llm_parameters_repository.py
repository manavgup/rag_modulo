from typing import List, Optional, cast
from sqlalchemy.orm import Session
from sqlalchemy import select, update, desc
from datetime import datetime

from core.logging_utils import get_logger
from core.custom_exceptions import LLMParameterError
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.schemas.llm_parameters_schema import (
    LLMParametersCreate,
    LLMParametersUpdate,
    LLMParametersResponse
)

logger = get_logger("repository.llm_parameters")

class LLMParametersRepository:
    """Repository for managing LLM parameters in the database."""

    def __init__(self, session: Session) -> None:
        """Initialize repository with database session."""
        self.session = session
        self.logger = get_logger(__name__)

    def create(self, params: LLMParametersCreate) -> LLMParametersResponse:
        """Create new LLM parameters.
        
        Args:
            params: Parameter set to create
            
        Returns:
            Created parameter set
            
        Raises:
            LLMParameterError: If creation fails
        """
        try:
            # If this set is marked as default, unset any existing defaults
            if params.is_default:
                self._unset_default_parameters()

            # Exclude computed fields when creating SQLAlchemy model
            db_params = LLMParameters(**params.model_dump(exclude={'is_deterministic'}))
            self.session.add(db_params)
            self.session.commit()
            self.session.refresh(db_params)
            
            created = self._to_response(db_params)
            if created is None:
                raise ValueError("Failed to create parameter set")
                
            self.logger.info(f"Created LLM parameters: {created.name}")
            return created
        except Exception as e:
            self.logger.error(f"Error creating LLM parameters: {str(e)}")
            self.session.rollback()
            raise LLMParameterError(
                param_name=params.name,
                error_type="creation_error",
                message=f"Failed to create parameter set: {str(e)}"
            )

    def get(self, params_id: int) -> Optional[LLMParametersResponse]:
        """Get LLM parameters by ID.
        
        Args:
            params_id: ID of parameters to retrieve
            
        Returns:
            Parameter set if found, None otherwise
            
        Raises:
            LLMParameterError: If database error occurs
        """
        try:
            stmt = (
                select(LLMParameters)
                .where(LLMParameters.id == params_id)
            )
            result = self.session.execute(stmt).scalar_one_or_none()
            return self._to_response(result) if result else None
        except Exception as e:
            self.logger.error(f"Error getting LLM parameters {params_id}: {str(e)}")
            raise LLMParameterError(
                param_name=str(params_id),
                error_type="retrieval_error",
                message=f"Failed to retrieve parameter set: {str(e)}"
            )

    def get_by_name(self, name: str) -> Optional[LLMParametersResponse]:
        """Get LLM parameters by name.
        
        Args:
            name: Name of parameters to retrieve
            
        Returns:
            Parameter set if found, None otherwise
            
        Raises:
            LLMParameterError: If database error occurs
        """
        try:
            stmt = (
                select(LLMParameters)
                .where(LLMParameters.name == name)
            )
            result = self.session.execute(stmt).scalar_one_or_none()
            return self._to_response(result) if result else None
        except Exception as e:
            self.logger.error(f"Error getting LLM parameters by name {name}: {str(e)}")
            raise LLMParameterError(
                param_name=name,
                error_type="retrieval_error",
                message=f"Failed to retrieve parameter set: {str(e)}"
            )

    def get_default(self) -> Optional[LLMParametersResponse]:
        """Get default LLM parameters.
        
        Returns:
            Default parameter set if found, None otherwise
            
        Raises:
            LLMParameterError: If database error occurs
        """
        try:
            stmt = (
                select(LLMParameters)
                .where(LLMParameters.is_default == True)
                .order_by(desc(LLMParameters.updated_at))
                .limit(1)
            )
            result = self.session.execute(stmt).scalar_one_or_none()
            return self._to_response(result) if result else None
        except Exception as e:
            self.logger.error(f"Error getting default LLM parameters: {str(e)}")
            raise LLMParameterError(
                param_name="default",
                error_type="retrieval_error",
                message=f"Failed to retrieve default parameter set: {str(e)}"
            )

    def list(self, skip: int = 0, limit: int = 100) -> List[LLMParametersResponse]:
        """List all LLM parameters with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of parameter sets
            
        Raises:
            LLMParameterError: If database error occurs
        """
        try:
            self.logger.debug(f"Listing LLM parameters with skip={skip}, limit={limit}")
            stmt = (
                select(LLMParameters)
                .order_by(desc(LLMParameters.updated_at))
                .offset(skip)
                .limit(limit)
            )
            results = self.session.execute(stmt).scalars().all()
            self.logger.debug(f"Retrieved {len(results)} LLM parameter sets")
            return [self._to_response(result) for result in results]
        except Exception as e:
            self.logger.error(f"Error listing LLM parameters: {str(e)}")
            raise LLMParameterError(
                param_name="list",
                error_type="retrieval_error",
                message=f"Failed to list parameter sets: {str(e)}"
            )

    def update(self, params_id: int, params: LLMParametersUpdate) -> Optional[LLMParametersResponse]:
        """Update LLM parameters.
        
        Args:
            params_id: ID of parameters to update
            params: Updated parameter values
            
        Returns:
            Updated parameter set if found, None otherwise
            
        Raises:
            LLMParameterError: If update fails
        """
        try:
            # Get existing parameters
            stmt = select(LLMParameters).where(LLMParameters.id == params_id)
            db_params = self.session.execute(stmt).scalar_one_or_none()
            
            if not db_params:
                return None

            # If updating is_default to True, unset any existing defaults
            if params.is_default:
                self._unset_default_parameters()

            # Update parameters
            update_data = params.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_params, key, value)

            # Update timestamp
            db_params.updated_at = datetime.utcnow()

            self.session.commit()
            self.session.refresh(db_params)
            
            updated = self._to_response(db_params)
            if updated is not None:
                self.logger.info(f"Updated LLM parameters: {updated.name}")
            return updated
        except Exception as e:
            self.logger.error(f"Error updating LLM parameters {params_id}: {str(e)}")
            self.session.rollback()
            raise LLMParameterError(
                param_name=str(params_id),
                error_type="update_error",
                message=f"Failed to update parameter set: {str(e)}"
            )

    def delete(self, params_id: int) -> bool:
        """Delete LLM parameters.
        
        Args:
            params_id: ID of parameters to delete
            
        Returns:
            True if deleted successfully, False if not found
            
        Raises:
            LLMParameterError: If deletion fails
        """
        try:
            stmt = select(LLMParameters).where(LLMParameters.id == params_id)
            db_params = self.session.execute(stmt).scalar_one_or_none()
            
            if not db_params:
                return False

            param_name = db_params.name
            self.session.delete(db_params)
            self.session.commit()
            
            self.logger.info(f"Deleted LLM parameters: {param_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting LLM parameters {params_id}: {str(e)}")
            self.session.rollback()
            raise LLMParameterError(
                param_name=str(params_id),
                error_type="deletion_error",
                message=f"Failed to delete parameter set: {str(e)}"
            )

    def _unset_default_parameters(self) -> None:
        """Unset any existing default parameters.
        
        Raises:
            LLMParameterError: If database error occurs
        """
        try:
            stmt = (
                update(LLMParameters)
                .where(LLMParameters.is_default == True)
                .values(
                    is_default=False,
                    updated_at=datetime.utcnow()
                )
            )
            self.session.execute(stmt)
            self.session.commit()
        except Exception as e:
            self.logger.error(f"Error unsetting default parameters: {str(e)}")
            self.session.rollback()
            raise LLMParameterError(
                param_name="default",
                error_type="update_error",
                message=f"Failed to unset default parameters: {str(e)}"
            )

    @staticmethod
    def _to_response(params: Optional[LLMParameters]) -> Optional[LLMParametersResponse]:
        """Convert database model to response schema.
        
        Args:
            params: Database model instance or None
            
        Returns:
            Response schema instance if params is not None, otherwise None
        """
        if params is None:
            return None
        return cast(
            LLMParametersResponse,
            LLMParametersResponse.model_validate(params)
        )
