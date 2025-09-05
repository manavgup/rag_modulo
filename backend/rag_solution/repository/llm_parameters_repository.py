from pydantic import UUID4
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.logging_utils import get_logger
from rag_solution.core.exceptions import AlreadyExistsError, NotFoundError, ValidationError
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
                raise NotFoundError(resource_type="User", resource_id=str(parameters.user_id)) from e
            raise AlreadyExistsError(resource_type="LLMParameters", field="name", value=str(parameters.user_id)) from e
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception:
            self.db.rollback()
            raise

    def get_parameters(self, parameter_id: UUID4) -> LLMParametersOutput:
        """Get LLM Parameters by ID.

        Args:
            parameter_id: UUID of the parameters to retrieve

        Returns:
            LLMParametersOutput: Parameters

        Raises:
            NotFoundError: If parameters not found
        """
        try:
            db_params = self.db.query(LLMParameters).filter(LLMParameters.id == parameter_id).first()
            if not db_params:
                raise NotFoundError(resource_type="LLMParameters", resource_id=str(parameter_id))
            return LLMParametersOutput.model_validate(db_params)
        except NotFoundError:
            raise
        except Exception as e:
            raise Exception(f"Failed to get LLM parameters: {e!s}") from e

    def update(self, parameter_id: UUID4, parameters: LLMParametersInput) -> LLMParametersOutput:
        """Update existing LLM Parameters.

        Args:
            parameter_id: UUID of the parameters to update
            parameters: New parameter values

        Returns:
            LLMParametersOutput: Updated parameters

        Raises:
            NotFoundError: If parameters not found
            ValidationError: If validation fails
        """
        try:
            db_params = self.db.query(LLMParameters).filter(LLMParameters.id == parameter_id).first()
            if not db_params:
                raise NotFoundError(resource_type="LLMParameters", resource_id=str(parameter_id))

            # Validate that user_id cannot be changed
            if parameters.user_id != db_params.user_id:
                raise ValidationError("Cannot change user_id of existing parameters", field="user_id")

            param_dict = parameters.model_dump(exclude_unset=True)
            for field, value in param_dict.items():
                if field != "user_id":  # Skip user_id to prevent accidental changes
                    setattr(db_params, field, value)

            self.db.commit()
            self.db.refresh(db_params)
            return LLMParametersOutput.model_validate(db_params)
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to update LLM parameters: {e!s}") from e

    def delete(self, parameter_id: UUID4) -> None:
        """Delete LLM Parameters.

        Args:
            parameter_id: UUID of the parameters to delete

        Raises:
            NotFoundError: If parameters not found
        """
        db_params = self.db.query(LLMParameters).filter(LLMParameters.id == parameter_id).first()
        if not db_params:
            raise NotFoundError(resource_type="LLMParameters", resource_id=str(parameter_id))

        self.db.delete(db_params)
        self.db.commit()

    def delete_by_user_id(self, user_id: UUID4) -> int:
        """Delete all LLM Parameters for a user.

        Args:
            user_id: UUID4 of the user whose parameters should be deleted

        Returns:
            int: Number of parameters deleted
        """
        deleted_count = self.db.query(LLMParameters).filter(LLMParameters.user_id == user_id).delete()
        self.db.commit()
        return deleted_count

    def get_parameters_by_user_id(self, user_id: UUID4) -> list[LLMParametersOutput]:
        """Get all LLM Parameters for a user.

        Args:
            user_id: UUID4 of the user

        Returns:
            List[LLMParametersOutput]: List of all parameters for the user
        """
        db_params = self.db.query(LLMParameters).filter(LLMParameters.user_id == user_id).all()
        return [LLMParametersOutput.model_validate(p) for p in db_params]

    def get_default_parameters(self, user_id: UUID4) -> LLMParametersOutput | None:
        """Get default LLM Parameters for a user.

        Args:
            user_id: UUID4 of the user

        Returns:
            Optional[LLMParametersOutput]: Default parameters if they exist, None otherwise
        """
        db_params = self.db.query(LLMParameters).filter(LLMParameters.user_id == user_id, LLMParameters.is_default.is_(True)).first()
        return LLMParametersOutput.model_validate(db_params) if db_params else None

    def reset_default_parameters(self, user_id: UUID4) -> int:
        """Reset default flag for all of a user's parameters.

        Args:
            user_id: UUID4 of the user

        Returns:
            int: Number of parameters updated
        """
        updated_count = self.db.query(LLMParameters).filter(LLMParameters.user_id == user_id, LLMParameters.is_default.is_(True)).update({"is_default": False})
        self.db.commit()
        return updated_count
