import logging
import re
from typing import Any
from uuid import UUID

import validators
from sqlalchemy.orm import Session

from core.custom_exceptions import LLMProviderError, ProviderValidationError
from rag_solution.repository.llm_provider_repository import LLMProviderRepository
from rag_solution.schemas.llm_provider_schema import LLMProviderConfig, LLMProviderInput, LLMProviderOutput

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
                field="name", message="Provider name can only contain alphanumeric characters, hyphens, and underscores"
            )

        if not validators.url(provider_input.base_url):
            raise ProviderValidationError(field="base_url", message="Invalid base URL format")

    def create_provider(self, provider_input: LLMProviderInput) -> LLMProviderOutput:
        """Create a new provider."""
        try:
            self._validate_provider_input(provider_input)
            provider = self.repository.create_provider(provider_input)
            return LLMProviderOutput.model_validate(provider)
        except Exception as e:
            raise LLMProviderError(provider=provider_input.name, error_type="creation", message=str(e))

    def get_provider_by_name(self, name: str) -> LLMProviderConfig | None:
        """Get provider configuration by name."""
        try:
            provider = self.repository.get_provider_by_name_with_credentials(name)
            return LLMProviderConfig.model_validate(provider) if provider else None
        except Exception as e:
            raise LLMProviderError(provider=name, error_type="retrieval", message=str(e))

    def get_provider_by_id(self, provider_id: UUID) -> LLMProviderOutput | None:
        """Get provider by ID."""
        provider = self.repository.get_provider_by_id(provider_id)
        return LLMProviderOutput.model_validate(provider) if provider else None

    def get_all_providers(self, is_active: bool | None = None) -> list[LLMProviderOutput]:
        """Get all providers."""
        providers = self.repository.get_all_providers(is_active)
        return [LLMProviderOutput.model_validate(p) for p in providers]

    def update_provider(self, provider_id: UUID, updates: dict[str, Any]) -> LLMProviderOutput | None:
        """Update provider details."""
        try:
            provider = self.repository.update_provider(provider_id, updates)
            return LLMProviderOutput.model_validate(provider) if provider else None
        except Exception as e:
            raise LLMProviderError(provider=str(provider_id), error_type="update", message=str(e))

    def delete_provider(self, provider_id: UUID) -> bool:
        """Soft delete a provider."""
        return self.repository.delete_provider(provider_id)

    def get_user_provider(self, user_id: UUID) -> LLMProviderOutput | None:
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

    def get_provider_models(self, provider_id: UUID) -> list[dict[str, Any]]:
        """Get available models for a specific provider."""
        # For now, return predefined models based on provider
        # In a real implementation, this would query the provider's API
        provider = self.repository.get_provider_by_id(provider_id)
        if not provider:
            return []

        # Return IBM Watson models as default
        return [
            {
                "id": str(UUID("11111111-1111-1111-1111-111111111111")),
                "provider_id": str(provider_id),
                "model_id": "meta-llama/llama-3-3-70b-instruct",
                "default_model_id": "meta-llama/llama-3-3-70b-instruct",
                "model_type": "generation",
                "timeout": 30,
                "max_retries": 3,
                "batch_size": 10,
                "retry_delay": 1.0,
                "concurrency_limit": 10,
                "stream": False,
                "rate_limit": 10,
                "is_default": True,
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        ]
