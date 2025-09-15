"""Factory for creating and managing LLM provider instances."""

from __future__ import annotations

from threading import Lock
from typing import TYPE_CHECKING, ClassVar

from core.custom_exceptions import LLMProviderError
from core.logging_utils import get_logger

from rag_solution.services.llm_model_service import LLMModelService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.prompt_template_service import PromptTemplateService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from .base import LLMBase

logger = get_logger("llm.providers.factory")


class LLMProviderFactory:
    """
    Factory for creating and managing LLM provider instances.

    This factory implements the singleton pattern for provider instances to ensure
    resource efficiency and consistent state. It handles provider registration,
    instance caching, and cleanup.

    Class Attributes:
        _providers (ClassVar[Dict[str, Type[LLMBase]]]): Registry of provider implementations
        _lock (ClassVar[Lock]): Lock for thread-safe provider registration

    Instance Attributes:
        _instances (Dict[str, LLMBase]): Cache of provider instances
        _db (Session): Database session
        _llm_provider_service (LLMProviderService): Service for provider configuration
        _llm_parameters_service (LLMParametersService): Service for LLM parameters
        _prompt_template_service (PromptTemplateService): Service for prompt templates
    """

    _providers: ClassVar[dict[str, type[LLMBase]]] = {}
    _lock: ClassVar[Lock] = Lock()

    def __init__(self, db: Session) -> None:
        """
        Initialize factory with database session and required services.

        Args:
            db: SQLAlchemy database session
        """
        self._db = db
        self._instances: dict[str, LLMBase] = {}

        # Initialize required services
        self._llm_provider_service = LLMProviderService(db)
        self._llm_parameters_service = LLMParametersService(db)
        self._prompt_template_service = PromptTemplateService(db)
        self._llm_model_service = LLMModelService(db)

    def _get_cache_key(self, provider_name: str, model_id: str | None = None) -> str:
        """
        Generate cache key for provider instance.

        Args:
            provider_name: Provider name
            model_id: Optional model ID

        Returns:
            Cache key string
        """
        return f"{provider_name.lower()}:{model_id}" if model_id else provider_name.lower()

    def _validate_provider_instance(self, provider: LLMBase, provider_name: str) -> None:
        """
        Validate provider instance is properly initialized.

        Args:
            provider: Provider instance to validate
            provider_name: Name of the provider for error reporting

        Raises:
            LLMProviderError: If provider validation fails
        """
        try:
            if provider.client is None:
                raise ValueError("Provider client initialization failed")
            provider.validate_client()
        except Exception as e:
            raise LLMProviderError(
                provider=provider_name,
                error_type="initialization_failed",
                message=f"Provider validation failed: {e!s}",
            ) from e

    def get_provider(self, provider_name: str, model_id: str | None = None) -> LLMBase:
        """
        Get a configured provider instance. Returns cached instance if available.

        Args:
            provider_name: Name of provider to get (case insensitive)
            model_id: Optional specific model ID to use

        Returns:
            Configured provider instance

        Raises:
            LLMProviderError: If provider creation or configuration fails
        """
        try:
            # Normalize provider name and get cache key
            provider_name = provider_name.lower()
            cache_key = self._get_cache_key(provider_name, model_id)

            # Check for cached instance
            if cache_key in self._instances:
                provider = self._instances[cache_key]
                try:
                    # Validate cached instance
                    self._validate_provider_instance(provider, provider_name)
                    logger.debug(f"Returning validated cached provider instance for {cache_key}")
                    return provider
                except LLMProviderError:
                    # Remove invalid instance from cache
                    logger.warning(f"Cached provider {cache_key} validation failed, reinitializing")
                    self.cleanup_provider(provider_name, model_id)

            # Validate provider type exists
            if provider_name not in self._providers:
                raise LLMProviderError(
                    provider=provider_name,
                    error_type="unknown_provider",
                    message=f"Unknown provider type: {provider_name}",
                )

            # Create new provider instance
            provider_class = self._providers[provider_name]
            provider = provider_class(
                self._llm_provider_service,
                self._llm_parameters_service,
                self._prompt_template_service,
                self._llm_model_service,
            )

            # Configure model if specified
            if model_id:
                provider.model_id = model_id

            # Validate new instance
            self._validate_provider_instance(provider, provider_name)

            # Cache validated instance
            self._instances[cache_key] = provider
            logger.debug(f"Cached new provider instance for {cache_key}")

            return provider

        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                provider=provider_name, error_type="creation_failed", message=f"Failed to create provider: {e!s}"
            ) from e

    def cleanup_provider(self, provider_name: str, model_id: str | None = None) -> None:
        """
        Clean up provider instance and remove from cache.

        Args:
            provider_name: Name of provider to clean up
            model_id: Optional model ID to specify which instance to clean up
        """
        cache_key = self._get_cache_key(provider_name, model_id)
        if cache_key in self._instances:
            provider = self._instances[cache_key]
            provider.close()
            del self._instances[cache_key]
            logger.debug(f"Cleaned up provider instance for {cache_key}")

    def cleanup_all(self) -> None:
        """Clean up all provider instances."""
        for cache_key, provider in list(self._instances.items()):
            provider.close()
            logger.debug(f"Cleaned up provider instance for {cache_key}")
        self._instances.clear()

    @classmethod
    def register_provider(cls, name: str, provider_class: type[LLMBase]) -> None:
        """
        Register a new provider implementation.

        This method is thread-safe and ensures no duplicate registrations.

        Args:
            name: Name to register the provider under
            provider_class: Provider class to register

        Raises:
            ValueError: If provider is already registered
        """
        with cls._lock:
            name = name.lower()
            if name in cls._providers:
                raise ValueError(f"Provider '{name}' is already registered")
            cls._providers[name] = provider_class
            logger.info(f"Registered new provider: {name}")
            logger.debug(f"Current providers: {cls._providers}")

    @classmethod
    def list_providers(cls) -> dict[str, type[LLMBase]]:
        """
        List all registered providers.

        Returns:
            A copy of the registered providers dictionary
        """
        with cls._lock:
            logger.debug(f"Listing providers: {cls._providers}")
            return cls._providers.copy()  # Return a copy to prevent modification
