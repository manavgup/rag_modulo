from typing import List, Optional, Dict, Any
from uuid import UUID
import logging
import re
import validators
from sqlalchemy.orm import Session

from core.custom_exceptions import (
    ProviderValidationError,
    ProviderConfigError,
    LLMProviderError
)
from rag_solution.repository.llm_provider_repository import LLMProviderRepository
from rag_solution.schemas.llm_provider_schema import (
    LLMProviderInput,
    LLMProviderOutput,
    LLMProviderConfig
)

logger = logging.getLogger("services.llm_provider")

class LLMProviderService:
    """Service for managing LLM Providers."""
    
    def __init__(self, db: Session) -> None:
        self.repository = LLMProviderRepository(db)
        self.session = db

    def _validate_provider_input(self, provider_input: LLMProviderInput) -> None:
        """Validate provider input."""
        if not re.match(r'^[a-zA-Z0-9-_]+$', provider_input.name):
            raise ProviderValidationError(
                field="name",
                message="Provider name can only contain alphanumeric characters, hyphens, and underscores"
            )
        
        if not validators.url(provider_input.base_url):
            raise ProviderValidationError(
                field="base_url",
                message="Invalid base URL format"
            )

    def create_provider(self, provider_input: LLMProviderInput) -> LLMProviderOutput:
        """Create a new provider."""
        try:
            self._validate_provider_input(provider_input)
            provider = self.repository.create_provider(provider_input)
            return LLMProviderOutput.model_validate(provider)
        except Exception as e:
            raise LLMProviderError(
                provider=provider_input.name,
                error_type="creation",
                message=str(e)
            )

    def get_provider_by_name(self, name: str) -> Optional[LLMProviderConfig]:
        """Get provider configuration by name."""
        try:
            provider = self.repository.get_provider_by_name_with_credentials(name)
            return LLMProviderConfig.model_validate(provider) if provider else None
        except Exception as e:
            raise LLMProviderError(
                provider=name,
                error_type="retrieval",
                message=str(e)
            )

    def get_provider_by_id(self, provider_id: UUID) -> Optional[LLMProviderOutput]:
        """Get provider by ID."""
        provider = self.repository.get_provider_by_id(provider_id)
        return LLMProviderOutput.model_validate(provider) if provider else None

    def get_all_providers(self, is_active: Optional[bool] = None) -> List[LLMProviderOutput]:
        """Get all providers."""
        providers = self.repository.get_all_providers(is_active)
        return [LLMProviderOutput.model_validate(p) for p in providers]

    def update_provider(self, provider_id: UUID, updates: Dict[str, Any]) -> Optional[LLMProviderOutput]:
        """Update provider details."""
        try:
            provider = self.repository.update_provider(provider_id, updates)
            return LLMProviderOutput.model_validate(provider) if provider else None
        except Exception as e:
            raise LLMProviderError(
                provider=str(provider_id),
                error_type="update",
                message=str(e)
            )

    def delete_provider(self, provider_id: UUID) -> bool:
        """Soft delete a provider."""
        return self.repository.delete_provider(provider_id)