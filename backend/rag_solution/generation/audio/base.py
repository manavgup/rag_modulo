"""
Base class for audio generation providers.

Provides abstract interface for generating podcast audio from dialogue scripts.
Similar to LLMBase but focused on audio generation rather than text generation.
"""

from abc import ABC, abstractmethod
from typing import Any

from rag_solution.schemas.podcast_schema import AudioFormat, PodcastScript


class AudioProviderBase(ABC):
    """
    Abstract base class for audio generation providers.

    Audio providers convert podcast scripts (text) into audio files (bytes).
    Unlike LLM providers, audio providers are stateless and don't require
    database services or complex parameter management.
    """

    @abstractmethod
    async def generate_dialogue_audio(
        self,
        script: PodcastScript,
        host_voice: str,
        expert_voice: str,
        audio_format: AudioFormat = AudioFormat.MP3,
    ) -> bytes:
        """
        Generate audio from podcast dialogue script.

        Args:
            script: Parsed podcast script with HOST/EXPERT turns
            host_voice: Voice ID for HOST speaker
            expert_voice: Voice ID for EXPERT speaker
            audio_format: Output audio format (mp3, wav, etc.)

        Returns:
            Audio file bytes

        Raises:
            AudioGenerationError: If audio generation fails
        """

    @abstractmethod
    async def list_available_voices(self) -> list[dict[str, Any]]:
        """
        Get list of available voices from provider.

        Returns:
            List of voice metadata dicts with keys:
                - voice_id: Unique voice identifier
                - name: Human-readable voice name
                - gender: Voice gender (if applicable)
                - language: Voice language/locale
                - description: Voice description (optional)

        Raises:
            AudioGenerationError: If unable to fetch voices
        """

    async def validate_voices(self, host_voice: str, expert_voice: str) -> bool:
        """
        Validate that voice IDs are available.

        Args:
            host_voice: HOST speaker voice ID
            expert_voice: EXPERT speaker voice ID

        Returns:
            True if both voices are valid

        Raises:
            ValueError: If either voice is invalid
        """
        available_voices = await self.list_available_voices()
        voice_ids = {v["voice_id"] for v in available_voices}

        if host_voice not in voice_ids:
            raise ValueError(f"Invalid host_voice '{host_voice}'. Available voices: {sorted(voice_ids)}")

        if expert_voice not in voice_ids:
            raise ValueError(f"Invalid expert_voice '{expert_voice}'. Available voices: {sorted(voice_ids)}")

        return True


class AudioGenerationError(Exception):
    """Exception raised for audio generation failures."""

    def __init__(
        self,
        provider: str,
        error_type: str,
        message: str,
        original_error: Exception | None = None,
    ):
        """
        Initialize audio generation error.

        Args:
            provider: Name of audio provider (openai, ollama, etc.)
            error_type: Error category (api_error, network_error, etc.)
            message: Human-readable error message
            original_error: Original exception that caused this error
        """
        self.provider = provider
        self.error_type = error_type
        self.message = message
        self.original_error = original_error

        super().__init__(
            f"[{provider}] {error_type}: {message}" + (f" (caused by {original_error})" if original_error else "")
        )
