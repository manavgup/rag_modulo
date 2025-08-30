from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rag_solution.core.exceptions import NotFoundError, AlreadyExistsError, ValidationError
from rag_solution.models.llm_model import LLMModel
from rag_solution.schemas.llm_model_schema import LLMModelInput, LLMModelOutput, ModelType


class LLMModelRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_model(self, model_input: LLMModelInput) -> LLMModelOutput:
        """Creates a new model."""
        try:
            model = LLMModel(**model_input.model_dump(exclude_unset=True))
            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)
            return LLMModelOutput.model_validate(model)
        except IntegrityError as e:
            self.session.rollback()
            raise AlreadyExistsError(
                resource_type="LLMModel", field="model_id", value=model_input.model_id
            ) from e
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            self.session.rollback()
            raise

    def get_model_by_id(self, model_id: UUID) -> LLMModelOutput:
        """Fetches a specific model by ID.
        
        Raises:
            NotFoundError: If model not found
        """
        try:
            model = self.session.query(LLMModel).filter_by(id=model_id).first()
            if not model:
                raise NotFoundError(
                    resource_type="LLMModel", resource_id=str(model_id)
                )
            return LLMModelOutput.model_validate(model)
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            raise

    def get_models_by_provider(self, provider_id: UUID) -> list[LLMModelOutput]:
        """Fetches all models associated with a specific provider."""
        try:
            models = self.session.query(LLMModel).filter_by(provider_id=provider_id).all()
            return [LLMModelOutput.model_validate(m) for m in models]
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            raise

    def get_models_by_type(self, model_type: ModelType) -> list[LLMModelOutput]:
        """Retrieve all models of a specific type."""
        try:
            models = self.session.query(LLMModel).filter(LLMModel.model_type == model_type).all()  # type: ignore[arg-type]
            return [LLMModelOutput.model_validate(m) for m in models]
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            raise

    def update_model(self, model_id: UUID, updates: dict) -> LLMModelOutput:
        """Updates model details.
        
        Raises:
            NotFoundError: If model not found
        """
        try:
            # Find the model first
            model = self.session.query(LLMModel).filter_by(id=model_id).first()
            if not model:
                raise NotFoundError(
                    resource_type="LLMModel", resource_id=str(model_id)
                )

            # Apply updates
            for key, value in updates.items():
                setattr(model, key, value)

            self.session.commit()
            self.session.refresh(model)
            return LLMModelOutput.model_validate(model)
        except IntegrityError as e:
            self.session.rollback()
            raise AlreadyExistsError(
                resource_type="LLMModel", field="id", value=str(model_id)
            ) from e
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            self.session.rollback()
            raise

    def delete_model(self, model_id: UUID) -> None:
        """Soft deletes a model by marking it inactive.
        
        Raises:
            NotFoundError: If model not found
        """
        try:
            # First check if model exists - this will raise NotFoundError if not found
            self.get_model_by_id(model_id)
            
            # Mark as inactive
            self.session.query(LLMModel).filter_by(id=model_id).update({"is_active": False})
            self.session.commit()
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            self.session.rollback()
            raise Exception(f"Failed to delete model: {e!s}") from e

    def clear_other_defaults(self, provider_id: UUID, model_type: ModelType) -> None:
        """Clear default flag from other models of the same type and provider."""
        try:
            (
                self.session.query(LLMModel)
                .filter(LLMModel.provider_id == provider_id)
                .filter(LLMModel.model_type == model_type)
                .filter(LLMModel.is_default == True)
                .update({"is_default": False})
            )
            self.session.commit()
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            self.session.rollback()
            raise

    def get_default_model(self, provider_id: UUID, model_type: ModelType) -> LLMModelOutput:
        """Get the default model for a provider and type.
        
        Raises:
            NotFoundError: If no default model found
        """
        try:
            model = (
                self.session.query(LLMModel)
                .filter(LLMModel.provider_id == provider_id)
                .filter(LLMModel.model_type == model_type)
                .filter(LLMModel.is_default == True)
                .filter(LLMModel.is_active == True)
                .first()
            )
            if not model:
                raise NotFoundError(
                    resource_type="LLMModel", identifier=f"default {model_type} for provider {provider_id}"
                )
            return LLMModelOutput.model_validate(model)
        except (NotFoundError, AlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            raise
