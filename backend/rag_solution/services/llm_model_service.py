import logging
from typing import Any

from core.custom_exceptions import LLMProviderError, ModelConfigError, ModelValidationError
from pydantic import UUID4
from sqlalchemy.orm import Session

from rag_solution.repository.llm_model_repository import LLMModelRepository
from rag_solution.repository.llm_provider_repository import LLMProviderRepository
from rag_solution.schemas.llm_model_schema import LLMModelInput, LLMModelOutput, ModelType

logger = logging.getLogger("services.llm_model")


class LLMModelService:
    """Service for managing LLM Models."""

    def __init__(self, db: Session) -> None:
        self.repository = LLMModelRepository(db)
        self.provider_repository = LLMProviderRepository(db)
        self.session = db

    def _validate_model_input(self, model_input: LLMModelInput) -> None:
        """Validate model input."""
        if model_input.timeout <= 0:
            raise ModelValidationError(
                field="timeout", message="Timeout must be greater than 0", value=model_input.timeout
            )

        if model_input.max_retries < 0:
            raise ModelValidationError(
                field="max_retries", message="Max retries cannot be negative", value=model_input.max_retries
            )

        # Validate provider exists
        provider = self.provider_repository.get_provider_by_id(model_input.provider_id)
        if not provider:
            raise ModelConfigError(
                field="provider_id",
                message=f"Provider {model_input.provider_id} does not exist",
                provider_id=str(model_input.provider_id),
            )

    def create_model(self, model_input: LLMModelInput) -> LLMModelOutput:
        """Create a new model."""
        try:
            self._validate_model_input(model_input)
            return self.repository.create_model(model_input)
        except (ModelValidationError, ModelConfigError):
            raise
        except Exception as e:
            raise LLMProviderError(
                provider=str(model_input.provider_id), error_type="model_creation", message=str(e)
            ) from e

    def set_default_model(self, model_id: UUID4) -> LLMModelOutput | None:
        """Set a model as default and clear other defaults for the same provider."""
        try:
            model = self.repository.get_model_by_id(model_id)
            if not model:
                return None

            # Clear other defaults for this provider and type
            self.repository.clear_other_defaults(model.provider_id, model.model_type)

            # Set this model as default
            return self.repository.update_model(model_id, {"is_default": True})
        except Exception as e:
            raise LLMProviderError(provider="unknown", error_type="default_update", message=str(e)) from e

    def get_default_model(self, provider_id: UUID4, model_type: ModelType) -> LLMModelOutput | None:
        """Get the default model for a provider and type."""
        try:
            return self.repository.get_default_model(provider_id, model_type)
        except Exception as e:
            raise LLMProviderError(provider=str(provider_id), error_type="default_retrieval", message=str(e)) from e

    def get_model_by_id(self, model_id: UUID4) -> LLMModelOutput | None:
        """Get model by ID."""
        return self.repository.get_model_by_id(model_id)

    def get_models_by_provider(self, provider_id: UUID4) -> list[LLMModelOutput]:
        """Get all models for a provider."""
        try:
            return self.repository.get_models_by_provider(provider_id)
        except Exception as e:
            raise LLMProviderError(provider=str(provider_id), error_type="model_retrieval", message=str(e)) from e

    def get_models_by_type(self, model_type: ModelType) -> list[LLMModelOutput]:
        """Get all models of a specific type."""
        try:
            return self.repository.get_models_by_type(model_type)
        except Exception as e:
            raise LLMProviderError(provider="unknown", error_type="model_retrieval", message=str(e)) from e

    def update_model(self, model_id: UUID4, updates: dict[str, Any]) -> LLMModelOutput | None:
        """Update model details."""
        try:
            return self.repository.update_model(model_id, updates)
        except Exception as e:
            raise LLMProviderError(provider=str(model_id), error_type="model_update", message=str(e)) from e

    def delete_model(self, model_id: UUID4) -> bool:
        """Soft delete a model."""
        try:
            self.repository.delete_model(model_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting model {model_id}: {e}")
            return False
