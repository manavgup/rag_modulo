"""Factory for LLM providers with logging."""

from typing import Dict, Type
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

    def get_provider(self, provider_type: str) -> LLMProvider:
        """Get or create a provider instance with logging.
        
        Args:
            provider_type: Type of provider to create/retrieve
            
        Returns:
            LLMProvider: Instance of the requested provider
            
        Raises:
            LLMProviderError: If provider type is unknown or configuration invalid
        """
        provider_type = provider_type.lower()
        
        if provider_type not in self._providers:
            logger.error(f"Unknown provider type requested: {provider_type}")
            raise LLMProviderError(
                provider=provider_type,
                error_type="unknown_provider",
                message=f"Unknown provider type: {provider_type}"
            )

        # Check if we have a valid instance
        if (provider_type not in self._instances or 
            self._instances[provider_type].client is None):
            
            # If instance exists but client is None, clean it up first
            if provider_type in self._instances:
                logger.warning(f"Found stale {provider_type} provider instance, reinitializing")
                try:
                    self._instances[provider_type].close()
                except Exception as e:
                    logger.error(f"Error closing stale provider: {str(e)}")
                self._instances.pop(provider_type)

            # Create new instance with configuration
            logger.info(f"Creating new instance of {provider_type} provider")
            try:
                self._instances[provider_type] = self._providers[provider_type](
                    provider_config_service=self._provider_config_service
                )
            except Exception as e:
                logger.error(f"Failed to initialize {provider_type} provider: {str(e)}")
                raise LLMProviderError(
                    provider=provider_type,
                    error_type="initialization_error",
                    message=f"Failed to initialize provider: {str(e)}"
                )

            # Verify initialization
            if self._instances[provider_type].client is None:
                logger.error(f"Failed to initialize {provider_type} provider client")
                raise LLMProviderError(
                    provider=provider_type,
                    error_type="initialization_error",
                    message=f"Failed to initialize provider client"
                )

        return self._instances[provider_type]

    async def close_all(self) -> None:
        """Clean up all provider instances.
        
        Closes all active provider instances and clears the instance cache.
        Logs any errors that occur during cleanup.
        """
        logger.info("Closing all provider instances")
        for provider_type, provider in self._instances.items():
            try:
                provider.close()  # Remove the await since close() is sync
                logger.debug(f"Closed {provider_type} provider")
            except Exception as e:
                logger.error(f"Error closing {provider_type} provider: {str(e)}")
        self._instances.clear()
