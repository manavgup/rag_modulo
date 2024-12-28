"""Factory for LLM providers with logging."""

from typing import Dict, Type
from core.logging_utils import get_logger
from .base import LLMProvider
from .watsonx import WatsonXProvider
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from core.custom_exceptions import LLMProviderError

logger = get_logger("llm.providers.factory")

class LLMProviderFactory:
    """Factory for creating and managing LLM providers with logging.
    
    This factory manages the lifecycle of LLM provider instances and ensures
    only one instance of each provider type exists.
    
    Attributes:
        _providers: Mapping of provider names to their implementation classes
        _instances: Cache of provider instances
    """
    
    _providers: Dict[str, Type[LLMProvider]] = {
        "watsonx": WatsonXProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider
    }
    _instances: Dict[str, LLMProvider] = {}

    @classmethod
    def get_provider(cls, provider_type: str) -> LLMProvider:
        """Get or create a provider instance with logging.
        
        Args:
            provider_type: Type of provider to create/retrieve
            
        Returns:
            LLMProvider: Instance of the requested provider
            
        Raises:
            LLMProviderError: If provider type is unknown
        """
        provider_type = provider_type.lower()
        
        if provider_type not in cls._providers:
            logger.error(f"Unknown provider type requested: {provider_type}")
            raise LLMProviderError(f"Unknown provider type: {provider_type}")

        # Check if we have a valid instance
        if (provider_type not in cls._instances or 
            cls._instances[provider_type].client is None):
            
            # If instance exists but client is None, clean it up first
            if provider_type in cls._instances:
                logger.warning(f"Found stale {provider_type} provider instance, reinitializing")
                try:
                    cls._instances[provider_type].close()
                except Exception as e:
                    logger.error(f"Error closing stale provider: {str(e)}")
                cls._instances.pop(provider_type)

            # Create new instance
            logger.info(f"Creating new instance of {provider_type} provider")
            cls._instances[provider_type] = cls._providers[provider_type]()

            # Verify initialization
            if cls._instances[provider_type].client is None:
                logger.error(f"Failed to initialize {provider_type} provider client")
                raise LLMProviderError(f"Failed to initialize {provider_type} provider")

        return cls._instances[provider_type]

    @classmethod
    async def close_all(cls) -> None:
        """Clean up all provider instances.
        
        Closes all active provider instances and clears the instance cache.
        Logs any errors that occur during cleanup.
        """
        logger.info("Closing all provider instances")
        for provider_type, provider in cls._instances.items():
            try:
                provider.close()  # Remove the await since close() is sync
                logger.debug(f"Closed {provider_type} provider")
            except Exception as e:
                logger.error(f"Error closing {provider_type} provider: {str(e)}")
        cls._instances.clear()