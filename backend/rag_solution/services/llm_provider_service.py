"""Service module for LLM Provider management with strong typing and validation."""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import SecretStr, ValidationError as PydanticValidationError

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.config import settings
from core.custom_exceptions import (
    ProviderValidationError,
    ProviderConfigError,
    LLMProviderError,
    NotFoundException
)
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType
from rag_solution.repository.llm_provider_repository import LLMProviderRepository
from rag_solution.schemas.llm_provider_schema import (
    LLMProviderInput,
    LLMProviderOutput,
    LLMProviderModelInput,
    LLMProviderModelOutput,
    ModelType
)

logger = logging.getLogger(__name__)


class LLMProviderService:
    """Service for managing LLM Providers and their Models.
    
    This service handles the business logic for LLM providers and their associated models,
    including validation, initialization, and error handling.
    
    Attributes:
        repository (LLMProviderRepository): Repository for database operations
    """
    
    def __init__(self, db: Session) -> None:
        """Initialize service with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.repository = LLMProviderRepository(db)
        self._prompt_template_service = None

    @property
    def prompt_template_service(self) -> PromptTemplateService:
        """Lazy initialization of prompt template service."""
        if self._prompt_template_service is None:
            self._prompt_template_service = PromptTemplateService(self.db)
        return self._prompt_template_service

    # -------------------------------
    # PROVIDER METHODS
    # -------------------------------

    def create_provider(self, provider_input: LLMProviderInput) -> LLMProviderOutput:
        """Create a new LLM provider.
        
        Args:
            provider_input: Validated provider input data
            
        Returns:
            Created provider instance
            
        Raises:
            ProviderValidationError: If input validation fails
            LLMProviderError: If provider creation fails
        """
        try:
            provider = self.repository.create_provider(provider_input)
            return LLMProviderOutput.model_validate(provider)
        except PydanticValidationError as e:
            raise ProviderValidationError(
                provider_input.name if hasattr(provider_input, 'name') else 'unknown',
                e
            )
        except Exception as e:
            raise LLMProviderError(
                provider_input.name if hasattr(provider_input, 'name') else 'unknown',
                'creation',
                str(e)
            )

    def get_all_providers(self, is_active: Optional[bool] = None) -> List[LLMProviderOutput]:
        """Retrieve all providers, optionally filtering by active status.
        
        Args:
            is_active: Optional filter for active/inactive providers
            
        Returns:
            List of provider instances matching the filter
            
        Raises:
            LLMProviderError: If retrieval fails
        """
        try:
            providers = self.repository.get_all_providers(is_active)
            return [LLMProviderOutput.model_validate(p) for p in providers]
        except Exception as e:
            raise LLMProviderError(
                'unknown',
                'retrieval',
                f"Failed to retrieve providers: {str(e)}"
            )

    def get_provider_by_name(self, name: str) -> Optional[LLMProviderOutput]:
        """Retrieve a provider by its name.
        
        Args:
            name: Name of the provider to retrieve
            
        Returns:
            Provider instance if found, None otherwise
            
        Raises:
            LLMProviderError: If retrieval fails
        """
        try:
            providers = self.repository.get_all_providers()
            provider = next((p for p in providers if p.name.lower() == name.lower()), None)
            if not provider:
                return None
            return LLMProviderOutput.model_validate(provider)
        except Exception as e:
            raise LLMProviderError(
                name,
                'retrieval',
                f"Failed to retrieve provider {name}: {str(e)}"
            )

    def get_provider_by_id(self, provider_id: UUID) -> Optional[LLMProviderOutput]:
        """Retrieve a specific provider by ID.
        
        Args:
            provider_id: UUID of the provider to retrieve
            
        Returns:
            Provider instance if found, None otherwise
            
        Raises:
            LLMProviderError: If retrieval fails
        """
        try:
            provider = self.repository.get_provider_by_id(provider_id)
            if not provider:
                raise NotFoundException(resource_type="LLMProvider", 
                                        resource_id=str(provider_id),
                                        message="Provider not found")
            return LLMProviderOutput.model_validate(provider)
        except NotFoundException:
            return None
        except Exception as e:
            raise LLMProviderError(
                'unknown',
                'retrieval',
                f"Failed to retrieve provider {provider_id}: {str(e)}"
            )

    def update_provider(self, provider_id: UUID, updates: Dict[str, Any]) -> Optional[LLMProviderOutput]:
        """Update provider details.
        
        Args:
            provider_id: UUID of the provider to update
            updates: Dictionary of fields to update
            
        Returns:
            Updated provider instance if found, None otherwise
            
        Raises:
            ProviderValidationError: If validation fails
            LLMProviderError: If update fails
        """
        try:
            provider = self.repository.update_provider(provider_id, updates)
            if not provider:
                return None
            return LLMProviderOutput.model_validate(provider)
        except PydanticValidationError as e:
            raise ProviderValidationError(
                'unknown',  # We don't have the provider name in updates
                e,
                details={"updates": updates}
            )
        except Exception as e:
            raise LLMProviderError(
                'unknown',
                'update',
                f"Failed to update provider {provider_id}: {str(e)}"
            )

    def delete_provider(self, provider_id: UUID) -> bool:
        """Soft delete a provider by marking it inactive.
        
        Args:
            provider_id: UUID of the provider to delete
            
        Returns:
            True if provider was deleted, False if not found
            
        Raises:
            LLMProviderError: If deletion fails
        """
        try:
            return self.repository.delete_provider(provider_id)
        except Exception as e:
            raise LLMProviderError(
                'unknown',
                'deletion',
                f"Failed to delete provider {provider_id}: {str(e)}"
            )

    # -------------------------------
    # PROVIDER MODEL METHODS
    # -------------------------------

    def create_provider_model(self, model_input: LLMProviderModelInput) -> LLMProviderModelOutput:
        """Create a new model configuration for a provider.
        
        Args:
            model_input: Validated model input data
            
        Returns:
            Created model instance
            
        Raises:
            ProviderValidationError: If validation fails
            LLMProviderError: If model creation fails
        """
        try:
            if not model_input.provider_id:
                raise ProviderConfigError(
                    'unknown',
                    model_input.model_id,
                    'missing_provider',
                    "provider_id is required for model creation"
                )
            model = self.repository.create_provider_model(model_input)
            return LLMProviderModelOutput.model_validate(model)
        except PydanticValidationError as e:
            raise ProviderValidationError(
                str(model_input.provider_id),
                e,
                field="model",
                value=model_input.model_id
            )
        except Exception as e:
            raise LLMProviderError(
                str(model_input.provider_id),
                'model_creation',
                f"Failed to create model {model_input.model_id}: {str(e)}"
            )

    def get_models_by_provider(self, provider_id: UUID) -> List[LLMProviderModelOutput]:
        """Retrieve all models associated with a specific provider.
        
        Args:
            provider_id: UUID of the provider to get models for
            
        Returns:
            List of model instances for the provider
            
        Raises:
            LLMProviderError: If retrieval fails
        """
        try:
            models = self.repository.get_models_by_provider(provider_id)
            return [LLMProviderModelOutput.model_validate(m) for m in models]
        except Exception as e:
            raise LLMProviderError(
                str(provider_id),
                'model_retrieval',
                f"Failed to retrieve models: {str(e)}"
            )

    def get_models_by_type(self, model_type: ModelType) -> List[LLMProviderModelOutput]:
        """Retrieve all models of a specific type.
        
        Args:
            model_type: Type of models to retrieve
            
        Returns:
            List of model instances matching the type
            
        Raises:
            LLMProviderError: If retrieval fails
        """
        try:
            models = self.repository.get_models_by_type(model_type)
            return [LLMProviderModelOutput.model_validate(m) for m in models]
        except Exception as e:
            raise LLMProviderError(
                'unknown',
                'model_retrieval',
                f"Failed to retrieve models of type {model_type}: {str(e)}"
            )

    def get_model_by_id(self, model_id: UUID) -> Optional[LLMProviderModelOutput]:
        """Retrieve a specific model by ID.
        
        Args:
            model_id: UUID of the model to retrieve
            
        Returns:
            Model instance if found, None otherwise
            
        Raises:
            LLMProviderError: If retrieval fails
        """
        try:
            model = self.repository.get_model_by_id(model_id)
            if not model:
                raise NotFoundException(resource_type="LLMProviderModel", 
                                        resource_id=str(model_id),
                                        message="Model not found")
            return LLMProviderModelOutput.model_validate(model)
        except NotFoundException:
            return None
        except Exception as e:
            raise LLMProviderError(
                'unknown',
                'model_retrieval',
                f"Failed to retrieve model {model_id}: {str(e)}"
            )

    def update_model(self, model_id: UUID, updates: Dict[str, Any]) -> Optional[LLMProviderModelOutput]:
        """Update model configuration details.
        
        Args:
            model_id: UUID of the model to update
            updates: Dictionary of fields to update
            
        Returns:
            Updated model instance if found, None otherwise
            
        Raises:
            ProviderValidationError: If validation fails
            LLMProviderError: If update fails
        """
        try:
            model = self.repository.update_model(model_id, updates)
            if not model:
                return None
            return LLMProviderModelOutput.model_validate(model)
        except PydanticValidationError as e:
            raise ProviderValidationError(
                'unknown',
                e,
                field="model",
                details={"updates": updates}
            )
        except Exception as e:
            raise LLMProviderError(
                'unknown',
                'model_update',
                f"Failed to update model {model_id}: {str(e)}"
            )

    def delete_model(self, model_id: UUID) -> bool:
        """Soft delete a model by marking it inactive.
        
        Args:
            model_id: UUID of the model to delete
            
        Returns:
            True if model was deleted, False if not found
            
        Raises:
            LLMProviderError: If deletion fails
        """
        try:
            return self.repository.delete_model(model_id)
        except Exception as e:
            raise LLMProviderError(
                'unknown',
                'model_deletion',
                f"Failed to delete model {model_id}: {str(e)}"
            )

    def get_providers_for_user(self, user_id: UUID) -> List[LLMProviderOutput]:
        """Get all providers available for a user.
        
        Args:
            user_id: UUID of the user
            
        Returns:
            List of provider instances available for the user
            
        Raises:
            LLMProviderError: If retrieval fails
        """
        try:
            # For now, return all active providers
            # In future, we might want to filter based on user permissions
            providers = self.repository.get_all_providers(is_active=True)
            return [LLMProviderOutput.model_validate(p) for p in providers]
        except Exception as e:
            raise LLMProviderError(
                'unknown',
                'provider_retrieval',
                f"Failed to retrieve providers for user {user_id}: {str(e)}"
            )

    def get_available_models(self, provider_id: UUID) -> List[LLMProviderModelOutput]:
        """Get all available models for a provider.
        
        Args:
            provider_id: UUID of the provider
            
        Returns:
            List of model instances available for the provider
            
        Raises:
            LLMProviderError: If retrieval fails
        """
        try:
            # Get all active models for the provider
            models = self.repository.get_models_by_provider(provider_id)
            return [LLMProviderModelOutput.model_validate(m) for m in models]
        except Exception as e:
            raise LLMProviderError(
                str(provider_id),
                'model_retrieval',
                f"Failed to retrieve provider models: {str(e)}"
            )

    def get_user_provider(self, user_id: UUID) -> Optional[LLMProviderOutput]:
        """
        Get the appropriate provider for a user.
        Priority:
        1. User's preferred provider
        2. System default provider
        3. Any active provider
        4. None
        """
        try:
            # Try user's preferred provider
            provider = self.repository.get_user_preferred_provider(user_id)
            if provider:
                return LLMProviderOutput.model_validate(provider)

            # Try system default provider
            provider = self.repository.get_default_provider()
            if provider:
                return LLMProviderOutput.model_validate(provider)

            # Fall back to any active provider
            providers = self.repository.get_all_providers(is_active=True)
            if providers:
                return LLMProviderOutput.model_validate(providers[0])

            return None
            
        except Exception as e:
            raise LLMProviderError(
                'unknown',
                'provider_selection',
                f"Failed to get provider for user {user_id}: {str(e)}"
            )

    # -------------------------------
    # PROVIDER WITH MODELS
    # -------------------------------

    def get_provider_with_models(self, provider_id: UUID) -> Optional[Dict[str, Any]]:
        """Retrieve a provider along with its models.
        
        Args:
            provider_id: UUID of the provider to retrieve with models
            
        Returns:
            Dictionary containing provider and models if found, None otherwise
            
        Raises:
            LLMProviderError: If retrieval fails
        """
        try:
            provider = self.repository.get_provider_with_models(provider_id)
            if not provider:
                return None

            return {
                "provider": LLMProviderOutput.model_validate(provider),
                "models": [LLMProviderModelOutput.model_validate(m) for m in provider.models]
            }
        except Exception as e:
            raise LLMProviderError(
                str(provider_id),
                'provider_models_retrieval',
                f"Failed to retrieve provider with models: {str(e)}"
            )

    # -------------------------------
    # STARTUP INITIALIZATION
    # -------------------------------

    def initialize_providers(self, raise_on_error: bool = False) -> List[LLMProviderOutput]:
        """Initialize or update default LLM providers.
        
        This method ensures that all default providers exist and have the latest settings.
        If a provider already exists, it will be updated with the latest configuration.
        If it doesn't exist, it will be created.
        
        Args:
            raise_on_error: If True, raises exceptions instead of logging and continuing
            
        Returns:
            List of initialized/updated providers
            
        Raises:
            LLMProviderError: If initialization fails and raise_on_error is True
        """
        try:
            existing_providers = {
                p.name: p for p in self.repository.get_all_providers()
            }
            logger.info(f"Found existing providers: {list(existing_providers.keys())}")
        except Exception as e:
            logger.error(f"Error getting existing providers: {str(e)}")
            if raise_on_error:
                raise LLMProviderError(
                    'unknown',
                    'initialization',
                    f"Failed to get existing providers: {str(e)}"
                )
            return []

        default_configs: Dict[str, LLMProviderInput] = {}

        # Initialize WatsonX if credentials exist
        if settings.wx_api_key and settings.wx_project_id:
            default_configs["watsonx"] = LLMProviderInput(
                name="watsonx",
                base_url=settings.wx_url or "https://us-south.ml.cloud.ibm.com",
                api_key=SecretStr(settings.wx_api_key),
                project_id=settings.wx_project_id
            )
            logger.info("WatsonX provider configuration added")
        else:
            logger.info("Skipping WatsonX provider - missing required credentials")

        # Initialize OpenAI if API key exists
        if settings.openai_api_key:
            default_configs["openai"] = LLMProviderInput(
                name="openai",
                base_url="https://api.openai.com",
                api_key=SecretStr(settings.openai_api_key)
            )
            logger.info("OpenAI provider configuration added")
        else:
            logger.info("Skipping OpenAI provider - missing API key")

        # Initialize Anthropic if API key exists
        if settings.anthropic_api_key:
            default_configs["anthropic"] = LLMProviderInput(
                name="anthropic",
                base_url="https://api.anthropic.com",
                api_key=SecretStr(settings.anthropic_api_key)
            )
            logger.info("Anthropic provider configuration added")
        else:
            logger.info("Skipping Anthropic provider - missing API key")

        if not default_configs:
            logger.warning("No provider configurations available - no providers have required credentials")

        initialized_providers: List[LLMProviderOutput] = []

        for name, config in default_configs.items():
            try:
                if name in existing_providers:
                    # Update existing provider
                    logger.info(f"Updating existing provider: {name}")
                    provider = self.update_provider(
                        existing_providers[name].id,
                        config.model_dump(exclude_unset=True)
                    )
                    if not provider:
                        raise LLMProviderError(
                            name,
                            'update',
                            f"Failed to update provider {name}"
                        )
                else:
                    # Create new provider
                    logger.info(f"Creating new provider: {name}")
                    provider = self.create_provider(config)

                # Set up default models for WatsonX
                if name == "watsonx":
                    # Create default generation model
                    model_input = LLMProviderModelInput(
                        provider_id=provider.id,
                        model_id="ibm/granite-3-8b-instruct",  # Using the model from config
                        default_model_id="ibm/granite-3-8b-instruct",
                        model_type=ModelType.GENERATION,
                        timeout=30,
                        max_retries=3,
                        batch_size=10,
                        retry_delay=1.0,
                        concurrency_limit=10,
                        stream=False,
                        rate_limit=10,
                        is_default=True,
                        is_active=True
                    )
                    try:
                        self.create_provider_model(model_input)
                        logger.info(f"Created default generation model for {name}")
                    except Exception as e:
                        logger.error(f"Error creating default model for {name}: {str(e)}")
                        if raise_on_error:
                            raise

                initialized_providers.append(provider)
                logger.info(f"Successfully initialized provider: {name}")

            except Exception as e:
                logger.error(f"Error initializing provider {name}: {str(e)}")
                if raise_on_error:
                    raise LLMProviderError(
                        name,
                        'initialization',
                        f"Failed to initialize provider {name}: {str(e)}"
                    )

        logger.info(f"Completed provider initialization. Initialized {len(initialized_providers)} providers")
        return initialized_providers
