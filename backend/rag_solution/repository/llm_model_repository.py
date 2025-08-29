from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.custom_exceptions import RepositoryError
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
            raise RepositoryError(f"Failed to create model: {e!s}") from e

    def get_model_by_id(self, model_id: UUID) -> LLMModelOutput | None:
        """Fetches a specific model by ID, returns None if not found."""
        model = self.session.query(LLMModel).filter_by(id=model_id).first()
        return LLMModelOutput.model_validate(model) if model else None

    def get_models_by_provider(self, provider_id: UUID) -> list[LLMModelOutput]:
        """Fetches all models associated with a specific provider."""
        models = self.session.query(LLMModel).filter_by(provider_id=provider_id).all()
        return [LLMModelOutput.model_validate(m) for m in models]

    def get_models_by_type(self, model_type: ModelType) -> list[LLMModelOutput]:
        """Retrieve all models of a specific type."""
        try:
            models = self.session.query(LLMModel).filter(LLMModel.model_type == model_type).all()
            return [LLMModelOutput.model_validate(m) for m in models]
        except Exception as e:
            raise RepositoryError(f"Failed to get models by type: {e!s}") from e

    def update_model(self, model_id: UUID, updates: dict) -> LLMModelOutput | None:
        """Updates model details."""
        try:
            # Find the model first
            model = self.session.query(LLMModel).filter_by(id=model_id).first()
            if not model:
                return None

            # Apply updates
            for key, value in updates.items():
                setattr(model, key, value)

            self.session.commit()
            self.session.refresh(model)
            return LLMModelOutput.model_validate(model)
        except IntegrityError as e:
            self.session.rollback()
            raise RepositoryError(f"Failed to update model: {e!s}") from e

    def delete_model(self, model_id: UUID) -> bool:
        """Soft deletes a model by marking it inactive."""
        try:
            result = self.session.query(LLMModel).filter_by(id=model_id).update({"is_active": False})
            self.session.commit()
            return result > 0
        except Exception as e:
            self.session.rollback()
            raise RepositoryError(f"Failed to delete model: {e!s}") from e

    def clear_other_defaults(self, provider_id: UUID, model_type: ModelType) -> None:
        """Clear default flag from other models of the same type and provider."""
        try:
            (
                self.session.query(LLMModel)
                .filter(LLMModel.provider_id == provider_id)
                .filter(LLMModel.model_type == model_type)
                .update({"is_default": False})
            )
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise RepositoryError(f"Failed to clear default models: {e!s}") from e

    def get_default_model(self, provider_id: UUID, model_type: ModelType) -> LLMModelOutput | None:
        """Get the default model for a provider and type."""
        try:
            model = (
                self.session.query(LLMModel)
                .filter(LLMModel.provider_id == provider_id)
                .filter(LLMModel.model_type == model_type)
                .filter(LLMModel.is_default is True)
                .filter(LLMModel.is_active is True)
                .first()
            )
            return LLMModelOutput.model_validate(model) if model else None
        except Exception as e:
            raise RepositoryError(f"Failed to get default model: {e!s}") from e
