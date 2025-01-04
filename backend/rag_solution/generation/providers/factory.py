"""Factory for LLM providers with logging."""

from typing import Dict, Type, Optional, Any
from sqlalchemy.orm import Session
from core.logging_utils import get_logger
from .base import LLMProvider
from .watsonx import WatsonXProvider
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from core.custom_exceptions import LLMProviderError
from rag_solution.services.provider_config_service import ProviderConfigService

logger = get_logger("llm.providers.factory")

class LLMProviderFactory:
    """Factory for creating and managing LLM providers with logging.
    
    This factory manages the lifecycle of LLM provider instances and ensures
    only one instance of each provider type exists.
    
    Attributes:
        _providers: Mapping of provider names to their implementation classes
        _instances: Cache of provider instances
        _provider_config_service: Service for provider configuration
    """
    
    _providers: Dict[str, Type[LLMProvider]] = {
        "watsonx": WatsonXProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider
    }
    _instances: Dict[str, LLMProvider] = {}

    def __init__(self, db: Session) -> None:
        """Initialize factory with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self._provider_config_service = ProviderConfigService(db)

    def get_provider(
        self, 
        provider_name: str, 
        model_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> LLMProvider:
        """Get or create a provider instance with logging.
        
        Args:
            provider_name: Name of provider to create/retrieve
            model_id: Optional model ID to use
            parameters: Optional parameters for the provider
            
        Returns:
            LLMProvider: Instance of the requested provider
            
        Raises:
            LLMProviderError: If provider type is unknown or configuration invalid
        """
        provider_name = provider_name.lower()
        
        if provider_name not in self._providers:
            logger.error(f"Unknown provider type requested: {provider_name}")
            raise LLMProviderError(
                provider=provider_name,
                error_type="unknown_provider",
                message=f"Unknown provider type: {provider_name}"
            )

        # Generate a unique key for this configuration
        config_key = f"{provider_name}"
        if model_id:
            config_key += f"_{model_id}"
        if parameters:
            config_key += f"_{hash(frozenset(parameters.items()))}"

        # Check if we have a valid instance with this configuration
        if (config_key not in self._instances or 
            self._instances[config_key].client is None):
            
            # If instance exists but client is None, clean it up first
            if config_key in self._instances:
                logger.warning(f"Found stale {provider_name} provider instance, reinitializing")
                try:
                    self._instances[config_key].close()
                except Exception as e:
                    logger.error(f"Error closing stale provider: {str(e)}")
                self._instances.pop(config_key)

            # Create new instance with configuration
            logger.info(f"Creating new instance of {provider_name} provider")
            try:
                provider_class = self._providers[provider_name]
                provider_instance = provider_class(
                    provider_config_service=self._provider_config_service
                )
                
                # Configure the provider with model and parameters if provided
                if model_id:
                    provider_instance.model_id = model_id
                if parameters:
                    provider_instance.parameters = parameters
                
                self._instances[config_key] = provider_instance
                
            except Exception as e:
                logger.error(f"Failed to initialize {provider_name} provider: {str(e)}")
                raise LLMProviderError(
                    provider=provider_name,
                    error_type="initialization_error",
                    message=f"Failed to initialize provider: {str(e)}"
                )

            # Verify initialization
            if self._instances[config_key].client is None:
                logger.error(f"Failed to initialize {provider_name} provider client")
                raise LLMProviderError(
                    provider=provider_name,
                    error_type="initialization_error",
                    message=f"Failed to initialize provider client"
                )

        return self._instances[config_key]

    def close_all(self) -> None:
        """Clean up all provider instances.
        
        Closes all active provider instances and clears the instance cache.
        Logs any errors that occur during cleanup.
        """
        logger.info("Closing all provider instances")
        for provider_type, provider in self._instances.items():
            try:
                provider.close()
                logger.debug(f"Closed {provider_type} provider")
            except Exception as e:
                logger.error(f"Error closing {provider_type} provider: {str(e)}")
        self._instances.clear()
