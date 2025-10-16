"""
ElevenLabs Text-to-Speech (TTS) audio provider with voice cloning support.

Uses ElevenLabs' TTS API to generate high-quality podcast audio with custom voices.
Supports voice cloning from uploaded voice samples for personalized podcast generation.
"""

import io
import logging
from typing import Any, ClassVar

import httpx
from pydub import AudioSegment

from core.config import Settings
from rag_solution.schemas.podcast_schema import AudioFormat, PodcastScript, Speaker

from .base import AudioGenerationError, AudioProviderBase

logger = logging.getLogger(__name__)


class ElevenLabsAudioProvider(AudioProviderBase):
    """ElevenLabs TTS provider for podcast audio generation with voice cloning."""

    # Default stability and similarity settings for voice generation
    DEFAULT_STABILITY: ClassVar[float] = 0.5
    DEFAULT_SIMILARITY: ClassVar[float] = 0.75

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.elevenlabs.io/v1",
        model_id: str = "eleven_multilingual_v2",
        stability: float = 0.5,
        similarity: float = 0.75,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        pause_duration_ms: int = 500,
    ):
        """
        Initialize ElevenLabs audio provider.

        Args:
            api_key: ElevenLabs API key
            base_url: API base URL
            model_id: Model to use for generation
            stability: Voice stability (0.0-1.0)
            similarity: Voice similarity boost (0.0-1.0)
            timeout_seconds: Request timeout
            max_retries: Maximum retry attempts
            pause_duration_ms: Pause duration between speakers in milliseconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self.stability = stability
        self.similarity = similarity
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.pause_duration_ms = pause_duration_ms

        # HTTP client for API requests
        # Note: Do NOT set Content-Type header here - let httpx handle it automatically
        # JSON requests will get "application/json", file uploads will get "multipart/form-data"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "xi-api-key": self.api_key,
            },
            timeout=httpx.Timeout(timeout_seconds),
        )

        logger.info(
            "Initialized ElevenLabs audio provider: model=%s, stability=%.2f, similarity=%.2f, pause=%dms",
            model_id,
            stability,
            similarity,
            pause_duration_ms,
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> "ElevenLabsAudioProvider":
        """
        Create provider from application settings.

        Args:
            settings: Application settings with ElevenLabs configuration

        Returns:
            Configured ElevenLabsAudioProvider instance

        Raises:
            ValueError: If ELEVENLABS_API_KEY is not configured
        """
        # Extract API key from settings
        if not hasattr(settings, "elevenlabs_api_key") or not settings.elevenlabs_api_key:
            raise ValueError("ELEVENLABS_API_KEY is required")

        # Handle both SecretStr and plain string
        api_key = (
            settings.elevenlabs_api_key.get_secret_value()
            if hasattr(settings.elevenlabs_api_key, "get_secret_value")
            else str(settings.elevenlabs_api_key)
        ).strip()

        return cls(
            api_key=api_key,
            base_url=getattr(settings, "elevenlabs_api_base_url", "https://api.elevenlabs.io/v1"),
            model_id=getattr(settings, "elevenlabs_model_id", "eleven_multilingual_v2"),
            stability=getattr(settings, "elevenlabs_voice_settings_stability", cls.DEFAULT_STABILITY),
            similarity=getattr(settings, "elevenlabs_voice_settings_similarity", cls.DEFAULT_SIMILARITY),
            timeout_seconds=getattr(settings, "elevenlabs_request_timeout_seconds", 30),
            max_retries=getattr(settings, "elevenlabs_max_retries", 3),
        )

    async def list_available_voices(self) -> list[dict[str, Any]]:
        """
        Get list of available voices from ElevenLabs.

        Returns:
            List of voice metadata dicts

        Raises:
            AudioGenerationError: If unable to fetch voices
        """
        try:
            response = await self.client.get("/voices")
            response.raise_for_status()

            data = response.json()
            voices = data.get("voices", [])

            # Convert to standard format
            return [
                {
                    "voice_id": voice["voice_id"],
                    "name": voice["name"],
                    "gender": voice.get("labels", {}).get("gender", "unknown"),
                    "language": voice.get("labels", {}).get("language", "en"),
                    "description": voice.get("description", ""),
                }
                for voice in voices
            ]

        except httpx.HTTPStatusError as e:
            raise AudioGenerationError(
                provider="elevenlabs",
                error_type="api_error",
                message=f"Failed to list voices: HTTP {e.response.status_code}",
                original_error=e,
            ) from e
        except Exception as e:
            raise AudioGenerationError(
                provider="elevenlabs",
                error_type="network_error",
                message=f"Failed to list voices: {e}",
                original_error=e,
            ) from e

    async def generate_dialogue_audio(
        self,
        script: PodcastScript,
        host_voice: str,
        expert_voice: str,
        audio_format: AudioFormat = AudioFormat.MP3,
    ) -> bytes:
        """
        Generate podcast audio using ElevenLabs TTS with custom voices.

        Args:
            script: Parsed podcast script with turns
            host_voice: Voice ID for HOST speaker (can be custom voice)
            expert_voice: Voice ID for EXPERT speaker (can be custom voice)
            audio_format: Output format

        Returns:
            Combined audio bytes

        Raises:
            AudioGenerationError: If generation fails
        """
        try:
            logger.info(
                "Generating audio for %d turns (HOST=%s, EXPERT=%s, model=%s)",
                len(script.turns),
                host_voice,
                expert_voice,
                self.model_id,
            )

            # Generate audio for each turn
            audio_segments = []
            for idx, turn in enumerate(script.turns):
                # Select voice based on speaker
                voice_id = host_voice if turn.speaker == Speaker.HOST else expert_voice

                # Generate audio for this turn
                try:
                    segment = await self._generate_turn_audio(
                        text=turn.text,
                        voice_id=voice_id,
                        audio_format=audio_format,
                    )
                    audio_segments.append(segment)

                    logger.debug(
                        "Generated turn %d/%d (%s, %d chars, voice=%s)",
                        idx + 1,
                        len(script.turns),
                        turn.speaker.value,
                        len(turn.text),
                        voice_id,
                    )

                except Exception as e:
                    raise AudioGenerationError(
                        provider="elevenlabs",
                        error_type="turn_generation_failed",
                        message=f"Failed to generate audio for turn {idx + 1}: {e}",
                        original_error=e,
                    ) from e

                # Add pause after turn (except last one)
                if idx < len(script.turns) - 1:
                    pause = AudioSegment.silent(duration=self.pause_duration_ms)
                    audio_segments.append(pause)

            # Combine all segments
            combined = self._combine_segments(audio_segments)

            # Export to bytes
            buffer = io.BytesIO()
            combined.export(buffer, format=audio_format.value)
            audio_bytes = buffer.getvalue()

            logger.info(
                "Generated complete podcast: %d turns, %d bytes, %.1f seconds",
                len(script.turns),
                len(audio_bytes),
                len(combined) / 1000.0,  # AudioSegment length is in milliseconds
            )

            return audio_bytes

        except AudioGenerationError:
            raise
        except Exception as e:
            raise AudioGenerationError(
                provider="elevenlabs",
                error_type="dialogue_generation_failed",
                message=f"Failed to generate dialogue audio: {e}",
                original_error=e,
            ) from e

    async def _generate_turn_audio(
        self,
        text: str,
        voice_id: str,
        audio_format: AudioFormat,
    ) -> AudioSegment:
        """
        Generate audio for a single turn using ElevenLabs TTS.

        Args:
            text: Text to convert to speech
            voice_id: ElevenLabs voice ID (preset or custom)
            audio_format: Audio format

        Returns:
            AudioSegment for this turn

        Raises:
            Exception: If API call fails
        """
        try:
            logger.debug("Calling ElevenLabs TTS: voice=%s, text_len=%d", voice_id, len(text))

            # ElevenLabs API payload
            payload = {
                "text": text,
                "model_id": self.model_id,
                "voice_settings": {
                    "stability": self.stability,
                    "similarity_boost": self.similarity,
                },
            }

            # Call ElevenLabs TTS API with retry logic
            for attempt in range(self.max_retries):
                try:
                    response = await self.client.post(
                        f"/text-to-speech/{voice_id}",
                        json=payload,
                    )

                    if response.status_code == 200:
                        break

                    # Handle specific error codes
                    if response.status_code == 401:
                        raise AudioGenerationError(
                            provider="elevenlabs",
                            error_type="authentication_error",
                            message="Invalid API key",
                        )

                    if response.status_code == 404:
                        raise AudioGenerationError(
                            provider="elevenlabs",
                            error_type="voice_not_found",
                            message=f"Voice ID '{voice_id}' not found",
                        )

                    if attempt < self.max_retries - 1:
                        logger.warning(
                            "ElevenLabs TTS request failed (attempt %d/%d): HTTP %d",
                            attempt + 1,
                            self.max_retries,
                            response.status_code,
                        )
                        continue

                    response.raise_for_status()

                except httpx.TimeoutException:
                    if attempt < self.max_retries - 1:
                        logger.warning(
                            "ElevenLabs TTS request timeout (attempt %d/%d)",
                            attempt + 1,
                            self.max_retries,
                        )
                        continue
                    raise

            logger.debug("ElevenLabs TTS response received: %d bytes", len(response.content))

            # Convert response to AudioSegment
            # ElevenLabs returns audio in the requested format (mp3 by default)
            segment = AudioSegment.from_file(
                io.BytesIO(response.content),
                format=audio_format.value,
            )

            return segment

        except AudioGenerationError:
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "ElevenLabs TTS API HTTP error for voice=%s: %d %s",
                voice_id,
                e.response.status_code,
                e.response.text,
            )
            raise AudioGenerationError(
                provider="elevenlabs",
                error_type="api_error",
                message=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
                original_error=e,
            ) from e
        except Exception as e:
            logger.error(
                "ElevenLabs TTS error for voice=%s, text_length=%d: %s",
                voice_id,
                len(text),
                e,
            )
            raise

    def _combine_segments(self, segments: list[AudioSegment]) -> AudioSegment:
        """
        Combine audio segments into single track.

        Args:
            segments: List of AudioSegment objects

        Returns:
            Combined AudioSegment

        Raises:
            ValueError: If segments list is empty
        """
        if not segments:
            raise ValueError("Cannot combine empty segments list")

        combined = AudioSegment.empty()
        for segment in segments:
            combined += segment

        return combined

    async def clone_voice(
        self,
        name: str,
        voice_sample_bytes: bytes,
        description: str | None = None,
    ) -> dict[str, Any]:
        """
        Clone a voice from uploaded sample using ElevenLabs voice cloning.

        This creates a new custom voice that can be used for TTS generation.

        Args:
            name: Name for the cloned voice
            voice_sample_bytes: Audio sample bytes (MP3, WAV, etc.)
            description: Optional description of the voice

        Returns:
            Dict with cloned voice metadata:
                - voice_id: Unique identifier for the cloned voice
                - name: Voice name
                - status: Cloning status

        Raises:
            AudioGenerationError: If voice cloning fails
        """
        try:
            logger.info(
                "Cloning voice: name=%s, sample_size=%d bytes",
                name,
                len(voice_sample_bytes),
            )

            # Prepare multipart form data
            files = {
                "files": ("voice_sample.mp3", voice_sample_bytes, "audio/mpeg"),
            }

            data = {
                "name": name,
            }

            if description:
                data["description"] = description

            # Call ElevenLabs voice cloning API
            response = await self.client.post(
                "/voices/add",
                files=files,
                data=data,
            )

            response.raise_for_status()
            result = response.json()

            logger.info("Voice cloned successfully: voice_id=%s", result.get("voice_id"))

            return {
                "voice_id": result["voice_id"],
                "name": name,
                "status": "ready",
            }

        except httpx.HTTPStatusError as e:
            logger.error(
                "ElevenLabs voice cloning failed: HTTP %d %s",
                e.response.status_code,
                e.response.text,
            )
            raise AudioGenerationError(
                provider="elevenlabs",
                error_type="voice_cloning_failed",
                message=f"HTTP {e.response.status_code}: {e.response.text[:200]}",
                original_error=e,
            ) from e
        except Exception as e:
            logger.exception("Voice cloning error: %s", e)
            raise AudioGenerationError(
                provider="elevenlabs",
                error_type="voice_cloning_failed",
                message=f"Voice cloning failed: {e}",
                original_error=e,
            ) from e

    async def delete_voice(self, voice_id: str) -> bool:
        """
        Delete a cloned voice from ElevenLabs.

        Args:
            voice_id: Voice ID to delete

        Returns:
            True if deleted successfully

        Raises:
            AudioGenerationError: If deletion fails
        """
        try:
            logger.info("Deleting voice: voice_id=%s", voice_id)

            response = await self.client.delete(f"/voices/{voice_id}")

            if response.status_code == 200:
                logger.info("Voice deleted successfully: voice_id=%s", voice_id)
                return True

            if response.status_code == 404:
                logger.warning("Voice not found for deletion: voice_id=%s", voice_id)
                return False

            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(
                "ElevenLabs voice deletion failed: HTTP %d %s",
                e.response.status_code,
                e.response.text,
            )
            raise AudioGenerationError(
                provider="elevenlabs",
                error_type="voice_deletion_failed",
                message=f"HTTP {e.response.status_code}",
                original_error=e,
            ) from e
        except Exception as e:
            logger.exception("Voice deletion error: %s", e)
            raise AudioGenerationError(
                provider="elevenlabs",
                error_type="voice_deletion_failed",
                message=str(e),
                original_error=e,
            ) from e

    async def __aenter__(self) -> "ElevenLabsAudioProvider":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: type, exc_val: Exception, exc_tb: Any) -> None:
        """Async context manager exit - close HTTP client."""
        await self.client.aclose()
