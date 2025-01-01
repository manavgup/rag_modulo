"""Service for managing LLM provider configurations."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from core.logging_utils import get_logger
from core.custom_exceptions import ProviderConfigError, LLMParameterError
from rag_solution.repository.provider_config_repository import ProviderConfigRepository
from rag_solution.repository.llm_parameters_repository import LLMParametersRepository
from rag_solution.schemas.provider_config_schema import (
    ProviderModelConfigInput,
    ProviderModelConfigInDB,
    ProviderModelConfigOutput,
    ProviderModelConfigUpdate,
    ProviderRegistryResponse
)
from rag_solution.schemas.llm_parameters_schema import LLMParametersCreate
from rag_solution.schemas.prompt_template_schema import PromptTemplateCreate

logger = get_logger("service.provider_config")

class ProviderConfigService:
    """Service for managing LLM provider configurations."""

    def __init__(self, db: Session) -> None:
        """Initialize service with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.provider_repo = ProviderConfigRepository(db)
        self.parameters_repo = LLMParametersRepository(db)
        self.logger = get_logger(__name__)

    def register_provider_model(
        self,
        provider: str,
        model_id: str,
        parameters: LLMParametersCreate,
        provider_config: ProviderModelConfigInput,
        prompt_template: Optional[PromptTemplateCreate] = None
    ) -> ProviderModelConfigOutput:
        """Register a new provider model with parameters.
        
        Args:
            provider: Provider name
            model_id: Model identifier
            parameters: LLM parameters for the model
            provider_config: Provider configuration with credentials and settings
            prompt_template: Optional prompt template
            
        Returns:
            Created provider configuration
            
        Raises:
            ProviderConfigError: If registration fails
        """
        try:
            # Check if provider/model already exists
            existing = self.provider_repo.get_by_provider_and_model(provider, model_id)
            if existing:
                raise ProviderConfigError(
                    provider=provider,
                    model_id=model_id,
                    error_type="duplicate_error",
                    message="Provider model configuration already exists"
                )

            # Create LLM parameters
            created_params = self.parameters_repo.create(parameters)

            # Create prompt template if provided
            if prompt_template:
                from rag_solution.repository.prompt_template_repository import PromptTemplateRepository
                template_repo = PromptTemplateRepository(self.db)
                template_repo.create(prompt_template)

            # Create provider config with credentials, settings, and the new parameters ID
            config = ProviderModelConfigInput(
                provider_name=provider,
                model_id=model_id,
                parameters_id=created_params.id,
                api_key=provider_config.api_key,
                api_url=provider_config.api_url,
                project_id=provider_config.project_id,
                org_id=provider_config.org_id,
                default_model_id=provider_config.default_model_id,
                embedding_model=provider_config.embedding_model,
                timeout=provider_config.timeout,
                max_retries=provider_config.max_retries,
                batch_size=provider_config.batch_size,
                is_active=True
            )
            return self.provider_repo.create(config)

        except LLMParameterError as e:
            self.logger.error(
                f"Failed to create parameters for {provider}/{model_id}: {str(e)}"
            )
            raise ProviderConfigError(
                provider=provider,
                model_id=model_id,
                error_type="parameter_error",
                message=f"Failed to create LLM parameters: {str(e)}"
            )
        except Exception as e:
            self.logger.error(f"Error registering provider model: {str(e)}")
            if "already exists" in str(e):
                raise ProviderConfigError(
                    provider=provider,
                    model_id=model_id,
                    error_type="duplicate_error",
                    message=f"Provider model configuration already exists"
                )
            else:
                raise ProviderConfigError(
                    provider=provider,
                    model_id=model_id,
                    error_type="registration_error",
                    message=f"Failed to register provider model: {str(e)}"
                )

    def get_provider_config(
        self,
        provider_name: str
    ) -> Optional[ProviderModelConfigOutput]:
        """Get provider configuration by name.
        
        Args:
            provider_name: Name of the provider (e.g. 'watsonx')
            
        Returns:
            Provider configuration if found, None otherwise
            
        Raises:
            ProviderConfigError: If retrieval fails
        """
        try:
            # Get active config for provider
            configs = self.provider_repo.list(active_only=True)
            for config in configs.providers:
                if config.provider_name == provider_name and config.is_active:
                    return ProviderModelConfigOutput.model_validate(config)
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting provider config for {provider_name}: {str(e)}")
            raise ProviderConfigError(
                provider=provider_name,
                model_id="",
                error_type="retrieval_error",
                message=f"Failed to get provider config: {str(e)}"
            )

    def get_provider_model(
        self,
        provider: str,
        model_id: str
    ) -> Optional[ProviderModelConfigOutput]:
        """Get provider model configuration.
        
        Args:
            provider: Provider name
            model_id: Model identifier
            
        Returns:
            Provider configuration if found, None otherwise
            
        Raises:
            ProviderConfigError: If retrieval fails
        """
        return self.provider_repo.get_by_provider_and_model(provider, model_id)

    def list_providers(
        self,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False
    ) -> ProviderRegistryResponse:
        """List all provider configurations.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: If True, only return active configurations
            
        Returns:
            Registry response with configurations and counts
            
        Raises:
            ProviderConfigError: If listing fails
        """
        return self.provider_repo.list(skip, limit, active_only)

    def update_provider_model(
        self,
        provider: str,
        model_id: str,
        updates: Dict[str, Any]
    ) -> Optional[ProviderModelConfigOutput]:
        """Update provider model configuration.
        
        Args:
            provider: Provider name
            model_id: Model identifier
            updates: Dictionary of fields to update
            
        Returns:
            Updated configuration if found, None otherwise
            
        Raises:
            ProviderConfigError: If update fails
        """
        try:
            # Get existing config
            existing = self.provider_repo.get_by_provider_and_model(provider, model_id)
            if not existing:
                return None

            # Update configuration
            config = ProviderModelConfigUpdate(**updates)
            return self.provider_repo.update(existing.id, config)

        except Exception as e:
            self.logger.error(
                f"Error updating provider model {provider}/{model_id}: {str(e)}"
            )
            raise ProviderConfigError(
                provider=provider,
                model_id=model_id,
                error_type="update_error",
                message=f"Failed to update provider model: {str(e)}"
            )

    def verify_provider_model(
        self,
        provider: str,
        model_id: str
    ) -> Optional[ProviderModelConfigOutput]:
        """Verify provider model and update verification timestamp.
        
        Args:
            provider: Provider name
            model_id: Model identifier
            
        Returns:
            Updated configuration if found, None otherwise
            
        Raises:
            ProviderConfigError: If verification fails
        """
        try:
            # Get existing config
            existing = self.provider_repo.get_by_provider_and_model(provider, model_id)
            if not existing:
                return None

            # TODO: Add actual verification logic here
            # This could include:
            # - Checking API connectivity
            # - Validating credentials
            # - Testing basic model functionality
            
            # Update verification timestamp
            return self.provider_repo.update_verification(existing.id)

        except Exception as e:
            self.logger.error(
                f"Error verifying provider model {provider}/{model_id}: {str(e)}"
            )
            raise ProviderConfigError(
                provider=provider,
                model_id=model_id,
                error_type="verification_error",
                message=f"Failed to verify provider model: {str(e)}"
            )

    def deactivate_provider_model(
        self,
        provider: str,
        model_id: str
    ) -> Optional[ProviderModelConfigOutput]:
        """Deactivate a provider model configuration.
        
        Args:
            provider: Provider name
            model_id: Model identifier
            
        Returns:
            Updated configuration if found, None otherwise
            
        Raises:
            ProviderConfigError: If deactivation fails
        """
        try:
            # Get existing config
            existing = self.provider_repo.get_by_provider_and_model(provider, model_id)
            if not existing:
                return None

            # Deactivate configuration
            updates = ProviderModelConfigUpdate(is_active=False)
            return self.provider_repo.update(existing.id, updates)

        except Exception as e:
            self.logger.error(
                f"Error deactivating provider model {provider}/{model_id}: {str(e)}"
            )
            raise ProviderConfigError(
                provider=provider,
                model_id=model_id,
                error_type="deactivation_error",
                message=f"Failed to deactivate provider model: {str(e)}"
            )

    def delete_provider_model(
        self,
        provider: str,
        model_id: str
    ) -> bool:
        """Delete a provider model configuration.
        
        Args:
            provider: Provider name
            model_id: Model identifier
            
        Returns:
            True if deleted successfully, False if not found
            
        Raises:
            ProviderConfigError: If deletion fails
        """
        try:
            # Get existing config
            existing = self.provider_repo.get_by_provider_and_model(provider, model_id)
            if not existing:
                return False

            return self.provider_repo.delete(existing.id)

        except Exception as e:
            self.logger.error(
                f"Error deleting provider model {provider}/{model_id}: {str(e)}"
            )
            raise ProviderConfigError(
                provider=provider,
                model_id=model_id,
                error_type="deletion_error",
                message=f"Failed to delete provider model: {str(e)}"
            )