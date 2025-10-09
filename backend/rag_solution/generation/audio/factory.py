"""
Factory for creating audio provider instances.

Provides centralized creation of audio providers based on configuration.
Similar pattern to LLMProviderFactory but simpler (no database dependencies).
"""

import logging
from typing import ClassVar

from core.config import Settings

from .base import AudioProviderBase
from .ollama_audio import OllamaAudioProvider
from .openai_audio import OpenAIAudioProvider

logger = logging.getLogger(__name__)


class AudioProviderFactory:
    """Factory for creating audio generation providers."""

    # Registry of available providers
    _providers: ClassVar[dict[str, type[AudioProviderBase]]] = {
        "openai": OpenAIAudioProvider,
        "ollama": OllamaAudioProvider,
    }

    @classmethod
    def create_provider(
        cls,
        provider_type: str,
        settings: Settings,
    ) -> AudioProviderBase:
        """
        Create audio provider instance based on type.

        Args:
            provider_type: Provider name (openai, ollama)
            settings: Application settings

        Returns:
            Configured AudioProviderBase instance

        Raises:
            ValueError: If provider_type is not supported
            Exception: If provider initialization fails
        """
        provider_type = provider_type.lower()

        if provider_type not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(f"Unsupported audio provider: '{provider_type}'. Available providers: {available}")

        try:
            if provider_type == "openai":
                return cls._create_openai_provider(settings)
            elif provider_type == "ollama":
                return cls._create_ollama_provider(settings)
            else:
                # Should not reach here due to registry check above
                raise ValueError(f"No factory method for provider: {provider_type}")

        except Exception as e:
            logger.error(
                "Failed to create audio provider '%s': %s",
                provider_type,
                e,
            )
            raise

    @classmethod
    def _create_openai_provider(cls, settings: Settings) -> OpenAIAudioProvider:
        """
        Create OpenAI audio provider.

        Args:
            settings: Application settings

        Returns:
            Configured OpenAIAudioProvider

        Raises:
            ValueError: If required settings are missing
        """
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI audio provider")

        api_key = (
            settings.openai_api_key.get_secret_value()
            if hasattr(settings.openai_api_key, "get_secret_value")
            else str(settings.openai_api_key)
        )

        # Strip any whitespace
        api_key = api_key.strip()

        model = getattr(settings, "openai_tts_model", "tts-1-hd")

        logger.info(
            "Creating OpenAI audio provider with model=%s, api_key_length=%d",
            model,
            len(api_key),
        )

        return OpenAIAudioProvider(
            api_key=api_key,
            model=model,
            pause_duration_ms=500,
        )

    @classmethod
    def _create_ollama_provider(cls, settings: Settings) -> OllamaAudioProvider:
        """
        Create Ollama audio provider.

        Args:
            settings: Application settings

        Returns:
            Configured OllamaAudioProvider
        """
        base_url = getattr(settings, "ollama_base_url", "http://localhost:11434")
        model = getattr(settings, "ollama_tts_model", "orpheus")

        logger.info(
            "Creating Ollama audio provider: url=%s, model=%s",
            base_url,
            model,
        )

        return OllamaAudioProvider(
            base_url=base_url,
            model=model,
            pause_duration_ms=500,
            timeout=300.0,
        )

    @classmethod
    def register_provider(
        cls,
        name: str,
        provider_class: type[AudioProviderBase],
    ) -> None:
        """
        Register a custom audio provider.

        Args:
            name: Provider name (lowercase)
            provider_class: AudioProviderBase subclass
        """
        name = name.lower()
        cls._providers[name] = provider_class
        logger.info("Registered audio provider: %s", name)

    @classmethod
    def list_providers(cls) -> list[str]:
        """
        Get list of registered provider names.

        Returns:
            List of provider names
        """
        return list(cls._providers.keys())
