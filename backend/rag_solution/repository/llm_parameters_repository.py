from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.custom_exceptions import NotFoundError, RepositoryError
from core.logging_utils import get_logger
from rag_solution.models.llm_parameters import LLMParameters
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput, LLMParametersOutput

logger = get_logger("repository.llm_parameters")


class LLMParametersRepository:
    """Repository for managing LLM Parameters in the database."""

    def __init__(self, db: Session) -> None:
        """Initialize repository with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(self, parameters: LLMParametersInput) -> LLMParametersOutput:
        """Create new LLM Parameters for a user.

        Args:
            parameters: Parameters to create including user_id

        Returns:
            LLMParametersOutput: Created parameters
        """
        try:
            db_params = LLMParameters(**parameters.model_dump())
            self.db.add(db_params)
            self.db.commit()
            self.db.refresh(db_params)
            return LLMParametersOutput.model_validate(db_params)
        except IntegrityError as e:
            self.db.rollback()
            if "violates foreign key constraint" in str(e):
                raise RepositoryError(
                    message=f"Referenced user {parameters.user_id} does not exist",
                    details={"user_id": str(parameters.user_id), "constraint": "foreign_key", "table": "users"},
                )
            raise RepositoryError(message=f"Database constraint violation: {e!s}", details={"error": str(e)})

    def get_parameters(self, parameter_id: UUID) -> LLMParametersOutput | None:
        """Get LLM Parameters by ID.

        Args:
            parameter_id: UUID of the parameters to retrieve

        Returns:
            Optional[LLMParametersOutput]: Parameters if found, None otherwise
        """
        db_params = self.db.query(LLMParameters).filter(LLMParameters.id == parameter_id).first()
        return LLMParametersOutput.model_validate(db_params) if db_params else None

    def update(self, parameter_id: UUID, parameters: LLMParametersInput) -> LLMParametersOutput:
        """Update existing LLM Parameters.

        Args:
            parameter_id: UUID of the parameters to update
            parameters: New parameter values

        Returns:
            LLMParametersOutput: Updated parameters

        Raises:
            NotFoundError: If parameters not found
        """
        db_params = self.db.query(LLMParameters).filter(LLMParameters.id == parameter_id).first()
        if not db_params:
            raise NotFoundError(
                resource_id=str(parameter_id),
                resource_type="LLMParameters",
                message=f"LLMParameters with ID {parameter_id} not found",
            )

        # Validate that user_id cannot be changed
        if parameters.user_id != db_params.user_id:
            raise RepositoryError(
                message="Cannot change user_id of existing parameters",
                details={"current_user_id": str(db_params.user_id), "attempted_user_id": str(parameters.user_id)},
            )

        param_dict = parameters.model_dump(exclude_unset=True)
        for field, value in param_dict.items():
            if field != "user_id":  # Skip user_id to prevent accidental changes
                setattr(db_params, field, value)

        self.db.commit()
        self.db.refresh(db_params)
        return LLMParametersOutput.model_validate(db_params)

    def delete(self, parameter_id: UUID) -> bool:
        """Delete LLM Parameters.

        Args:
            parameter_id: UUID of the parameters to delete

        Returns:
            bool: True if deletion was successful

        Raises:
            NotFoundError: If parameters not found
        """
        db_params = self.db.query(LLMParameters).filter(LLMParameters.id == parameter_id).first()
        if not db_params:
            raise NotFoundError(
                resource_id=str(parameter_id),
                resource_type="LLMParameters",
                message=f"LLMParameters with ID {parameter_id} not found",
            )

        self.db.delete(db_params)
        self.db.commit()
        return True

    def delete_by_user_id(self, user_id: UUID) -> int:
        """Delete all LLM Parameters for a user.

        Args:
            user_id: UUID of the user whose parameters should be deleted

        Returns:
            int: Number of parameters deleted
        """
        deleted_count = self.db.query(LLMParameters).filter(LLMParameters.user_id == user_id).delete()
        self.db.commit()
        return deleted_count

    def get_parameters_by_user_id(self, user_id: UUID) -> list[LLMParametersOutput]:
        """Get all LLM Parameters for a user.

        Args:
            user_id: UUID of the user

        Returns:
            List[LLMParametersOutput]: List of all parameters for the user
        """
        db_params = self.db.query(LLMParameters).filter(LLMParameters.user_id == user_id).all()
        return [LLMParametersOutput.model_validate(p) for p in db_params]

    def get_default_parameters(self, user_id: UUID) -> LLMParametersOutput | None:
        """Get default LLM Parameters for a user.

        Args:
            user_id: UUID of the user

        Returns:
            Optional[LLMParametersOutput]: Default parameters if they exist, None otherwise
        """
        db_params = (
            self.db.query(LLMParameters)
            .filter(LLMParameters.user_id == user_id, LLMParameters.is_default.is_(True))
            .first()
        )
        return LLMParametersOutput.model_validate(db_params) if db_params else None

    def reset_default_parameters(self, user_id: UUID) -> int:
        """Reset default flag for all of a user's parameters.

        Args:
            user_id: UUID of the user

        Returns:
            int: Number of parameters updated
        """
        updated_count = (
            self.db.query(LLMParameters)
            .filter(LLMParameters.user_id == user_id, LLMParameters.is_default.is_(True))
            .update({"is_default": False})
        )
        self.db.commit()
        return updated_count
