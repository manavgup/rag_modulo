import logging
import re
from typing import Any

import validators
from pydantic import UUID4
from sqlalchemy.orm import Session

from core.custom_exceptions import LLMProviderError, ProviderValidationError
from core.identity_service import IdentityService
from rag_solution.repository.llm_provider_repository import LLMProviderRepository
from rag_solution.schemas.llm_model_schema import LLMModelOutput, LLMModelUpdate, ModelType
from rag_solution.schemas.llm_provider_schema import (
    LLMProviderConfig,
    LLMProviderInput,
    LLMProviderOutput,
    LLMProviderUpdate,
)

logger = logging.getLogger("services.llm_provider")


class LLMProviderService:
    """Service for managing LLM Providers."""

    def __init__(self, db: Session) -> None:
        self.repository = LLMProviderRepository(db)
        self.session = db

    def _validate_provider_input(self, provider_input: LLMProviderInput) -> None:
        """Validate provider input."""
        if not re.match(r"^[a-zA-Z0-9-_]+$", provider_input.name):
            raise ProviderValidationError(
                provider_name=provider_input.name,
                validation_error="Provider name can only contain alphanumeric characters, hyphens, and underscores",
                field="name",
            )

        if not validators.url(provider_input.base_url):
            raise ProviderValidationError(
                provider_name=provider_input.name, validation_error="Invalid base URL format", field="base_url"
            )

    def create_provider(self, provider_input: LLMProviderInput) -> LLMProviderOutput:
        """Create a new provider."""
        try:
            self._validate_provider_input(provider_input)
            provider = self.repository.create_provider(provider_input)
            return LLMProviderOutput.model_validate(provider)
        except Exception as e:
            raise LLMProviderError(provider=provider_input.name, error_type="creation", message=str(e)) from e

    def get_provider_by_name(self, name: str) -> LLMProviderConfig | None:
        """Get provider configuration by name."""
        try:
            provider = self.repository.get_provider_by_name_with_credentials(name)
            return LLMProviderConfig.model_validate(provider) if provider else None
        except Exception as e:
            raise LLMProviderError(provider=name, error_type="retrieval", message=str(e)) from e

    def get_provider_by_id(self, provider_id: UUID4) -> LLMProviderOutput | None:
        """Get provider by ID."""
        provider = self.repository.get_provider_by_id(provider_id)
        return LLMProviderOutput.model_validate(provider) if provider else None

    def get_all_providers(self, is_active: bool | None = None) -> list[LLMProviderOutput]:
        """Get all providers."""
        providers = self.repository.get_all_providers(is_active)
        return [LLMProviderOutput.model_validate(p) for p in providers]

    def update_provider(self, provider_id: UUID4, updates: LLMProviderUpdate) -> LLMProviderOutput:
        """Update provider details with partial updates.

        Args:
            provider_id: ID of the provider to update
            updates: LLMProviderUpdate with optional fields for partial updates

        Returns:
            Updated provider

        Raises:
            NotFoundError: If provider not found
            LLMProviderError: If update fails
        """
        try:
            provider = self.repository.update_provider(provider_id, updates)
            return LLMProviderOutput.model_validate(provider)
        except Exception as e:
            raise LLMProviderError(provider=str(provider_id), error_type="update", message=str(e)) from e

    def delete_provider(self, provider_id: UUID4) -> bool:
        """Soft delete a provider."""
        try:
            self.repository.delete_provider(provider_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting provider {provider_id}: {e}")
            return False

    def get_user_provider(self, user_id: UUID4) -> LLMProviderOutput | None:
        """Get user's preferred provider or default provider.

        Args:
            user_id: User UUID

        Returns:
            Optional[LLMProviderOutput]: Provider configuration if found
        """
        try:
            # Try to get user's preferred provider first
            from rag_solution.models.user import User

            user = self.session.query(User).filter(User.id == user_id).first()
            if user and user.preferred_provider_id:
                provider = self.repository.get_provider_by_id(user.preferred_provider_id)
                if provider:
                    return LLMProviderOutput.model_validate(provider)

            # Fall back to system default provider
            default_provider = self.repository.get_default_provider()
            if default_provider:
                return LLMProviderOutput.model_validate(default_provider)

            # Return first active provider if no default
            providers = self.repository.get_all_providers(is_active=True)
            if providers:
                return LLMProviderOutput.model_validate(providers[0])

            return None
        except Exception as e:
            logger.error(f"Error getting user provider: {e!s}")
            return None

    def get_default_provider(self) -> LLMProviderOutput | None:
        """Get the system default provider.

        Returns:
            Optional[LLMProviderOutput]: Default provider configuration if found
        """
        try:
            default_provider = self.repository.get_default_provider()
            return LLMProviderOutput.model_validate(default_provider) if default_provider else None
        except Exception as e:
            logger.warning(f"Error getting default provider, falling back to first active: {e!s}")
            # Fall back to first active provider if no default
            providers = self.repository.get_all_providers(is_active=True)
            if providers:
                return LLMProviderOutput.model_validate(providers[0])
            return None

    def get_provider_models(self, provider_id: UUID4) -> list[LLMModelOutput]:
        """Get available models for a specific provider."""
        # For now, return predefined models based on provider
        # In a real implementation, this would query the provider's API
        provider = self.repository.get_provider_by_id(provider_id)
        if not provider:
            return []

        # Return IBM Watson models as default
        from datetime import datetime

        return [
            LLMModelOutput(
                id=IdentityService.MOCK_LLM_PROVIDER_ID,
                provider_id=provider_id,
                model_id="meta-llama/llama-3-3-70b-instruct",
                default_model_id="meta-llama/llama-3-3-70b-instruct",
                model_type=ModelType.GENERATION,
                timeout=30,
                max_retries=3,
                batch_size=10,
                retry_delay=1.0,
                concurrency_limit=10,
                stream=False,
                rate_limit=10,
                is_default=True,
                is_active=True,
                created_at=datetime.fromisoformat("2024-01-01T00:00:00"),
                updated_at=datetime.fromisoformat("2024-01-01T00:00:00"),
            )
        ]

    def create_provider_model(self, provider_id: UUID4, model_data: dict[str, Any]) -> LLMModelOutput:
        """Create a new model for a provider."""
        # This would typically create a model record in the database
        # For now, return the model data with an ID
        from datetime import datetime

        return LLMModelOutput(
            id=IdentityService.MOCK_LLM_MODEL_ID,
            provider_id=provider_id,
            model_id=model_data.get("model_id", "default-model"),
            default_model_id=model_data.get("default_model_id", "default-model"),
            model_type=ModelType(model_data.get("model_type", "generation")),
            timeout=model_data.get("timeout", 30),
            max_retries=model_data.get("max_retries", 3),
            batch_size=model_data.get("batch_size", 10),
            retry_delay=model_data.get("retry_delay", 1.0),
            concurrency_limit=model_data.get("concurrency_limit", 10),
            stream=model_data.get("stream", False),
            rate_limit=model_data.get("rate_limit", 10),
            is_default=model_data.get("is_default", False),
            is_active=model_data.get("is_active", True),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def get_models_by_provider(self, provider_id: UUID4) -> list[LLMModelOutput]:
        """Get all models for a specific provider."""
        return self.get_provider_models(provider_id)

    def get_models_by_type(self, _model_type: str) -> list[LLMModelOutput]:
        """Get all models of a specific type."""
        # This would typically query the database for models by type
        # For now, return an empty list
        return []

    def get_model_by_id(self, model_id: UUID4) -> LLMModelOutput:
        """Get a specific model by ID.

        NOTE: This is a stub implementation. In production, this should delegate
        to LLMModelService.

        Raises:
            NotFoundError: Always raises as this is a stub
        """
        from rag_solution.core.exceptions import NotFoundError

        raise NotFoundError(resource_type="LLMModel", resource_id=str(model_id))

    def update_model(self, model_id: UUID4, updates: LLMModelUpdate) -> LLMModelOutput:
        """Update a model.

        NOTE: This is a stub implementation. In production, this should delegate
        to LLMModelService.

        Args:
            model_id: ID of the model to update
            updates: Partial updates to apply

        Returns:
            Mock updated model (stub implementation)

        Raises:
            NotFoundError: If model not found
        """
        # This would typically update the model in the database via LLMModelService
        # For now, return a mock updated model
        from datetime import datetime

        # Convert Pydantic model to dict
        updates_dict = updates.model_dump(exclude_unset=True)

        return LLMModelOutput(
            id=model_id,
            provider_id=IdentityService.MOCK_LLM_PROVIDER_ID,  # Mock provider_id
            model_id=updates_dict.get("model_id", "default-model"),
            default_model_id=updates_dict.get("default_model_id", "default-model"),
            model_type=ModelType(updates_dict.get("model_type", "generation")),
            timeout=updates_dict.get("timeout", 30),
            max_retries=updates_dict.get("max_retries", 3),
            batch_size=updates_dict.get("batch_size", 10),
            retry_delay=updates_dict.get("retry_delay", 1.0),
            concurrency_limit=updates_dict.get("concurrency_limit", 10),
            stream=updates_dict.get("stream", False),
            rate_limit=updates_dict.get("rate_limit", 10),
            is_default=updates_dict.get("is_default", False),
            is_active=updates_dict.get("is_active", True),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def delete_model(self, _model_id: UUID4) -> bool:
        """Delete a model."""
        # This would typically delete the model from the database
        # For now, return True to indicate success
        return True

    def get_provider_with_models(self, provider_id: UUID4) -> dict[str, Any] | None:
        """Get a provider with all its models."""
        provider = self.repository.get_provider_by_id(provider_id)
        if not provider:
            return None

        provider_data = LLMProviderOutput.model_validate(provider).model_dump()
        provider_data["models"] = self.get_provider_models(provider_id)
        return provider_data
