"""
Ollama TTS audio provider.

Uses Ollama-hosted TTS models (Orpheus, ChatTTS, etc.) for self-hosted
podcast audio generation. Provides zero-cost alternative to API-based TTS.
"""

import io
import logging
from typing import Any

import httpx
from pydub import AudioSegment  # type: ignore[import-not-found]

from rag_solution.schemas.podcast_schema import AudioFormat, PodcastScript, Speaker

from .base import AudioGenerationError, AudioProviderBase

logger = logging.getLogger(__name__)


class OllamaAudioProvider(AudioProviderBase):
    """Ollama TTS provider for self-hosted podcast audio generation."""

    # Orpheus voices (8 available in Orpheus model)
    ORPHEUS_VOICES = [
        {
            "voice_id": "voice_1",
            "name": "Voice 1",
            "gender": "neutral",
            "language": "en-US",
            "description": "Warm, conversational voice",
        },
        {
            "voice_id": "voice_2",
            "name": "Voice 2",
            "gender": "neutral",
            "language": "en-US",
            "description": "Clear, authoritative voice",
        },
        {
            "voice_id": "voice_3",
            "name": "Voice 3",
            "gender": "neutral",
            "language": "en-US",
            "description": "Expressive voice",
        },
        {
            "voice_id": "voice_4",
            "name": "Voice 4",
            "gender": "neutral",
            "language": "en-US",
            "description": "Deep, authoritative voice",
        },
        {
            "voice_id": "voice_5",
            "name": "Voice 5",
            "gender": "neutral",
            "language": "en-US",
            "description": "Bright, engaging voice",
        },
        {
            "voice_id": "voice_6",
            "name": "Voice 6",
            "gender": "neutral",
            "language": "en-US",
            "description": "Warm, friendly voice",
        },
        {
            "voice_id": "voice_7",
            "name": "Voice 7",
            "gender": "neutral",
            "language": "en-US",
            "description": "Professional voice",
        },
        {
            "voice_id": "voice_8",
            "name": "Voice 8",
            "gender": "neutral",
            "language": "en-US",
            "description": "Dynamic voice",
        },
    ]

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "orpheus",
        pause_duration_ms: int = 500,
        timeout: float = 300.0,
    ):
        """
        Initialize Ollama audio provider.

        Args:
            base_url: Ollama server URL
            model: TTS model name (orpheus, chattts, etc.)
            pause_duration_ms: Pause duration between speakers in milliseconds
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.pause_duration_ms = pause_duration_ms
        self.timeout = timeout

        logger.info(
            "Initialized Ollama audio provider: url=%s, model=%s, pause=%dms",
            base_url,
            model,
            pause_duration_ms,
        )

    async def generate_speech_from_text(
        self,
        text: str,
        voice_id: str,
        audio_format: AudioFormat = AudioFormat.MP3,
    ) -> bytes:
        """
        Generate audio from a single text string using Ollama TTS.

        Args:
            text: Text to convert to speech.
            voice_id: Ollama voice ID.
            audio_format: Output audio format.

        Returns:
            Audio file bytes.

        Raises:
            AudioGenerationError: If TTS generation fails.
        """
        try:
            # Call Ollama TTS API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": f"[{voice_id}] {text}",
                        "stream": False,
                    },
                    timeout=60.0,
                )
                response.raise_for_status()

            # Convert response to audio bytes
            audio_segment = AudioSegment.from_file(
                io.BytesIO(response.content),
                format="wav",  # Ollama typically outputs WAV
            )

            # Export to requested format
            output = io.BytesIO()
            audio_segment.export(output, format=audio_format.value)
            return output.getvalue()

        except Exception as e:
            logger.error("Ollama TTS error for voice=%s, text_length=%d: %s", voice_id, len(text), e)
            raise AudioGenerationError(
                provider="ollama",
                error_type="api_error",
                message=f"Failed to generate speech from text: {e}",
                original_error=e,
            ) from e

    async def list_available_voices(self) -> list[dict[str, Any]]:
        """Get list of available voices for current model."""
        # TODO: Could be extended based on model type
        if self.model == "orpheus":
            return self.ORPHEUS_VOICES
        else:
            # Default voice set for unknown models
            return [
                {
                    "voice_id": "default",
                    "name": "Default Voice",
                    "gender": "neutral",
                    "language": "en-US",
                    "description": f"Default voice for {self.model}",
                }
            ]

    async def generate_dialogue_audio(
        self,
        script: PodcastScript,
        host_voice: str = "voice_1",
        expert_voice: str = "voice_2",
        audio_format: AudioFormat = AudioFormat.MP3,
    ) -> bytes:
        """
        Generate podcast audio using Ollama TTS.

        Args:
            script: Parsed podcast script with turns
            host_voice: Voice ID for HOST speaker
            expert_voice: Voice ID for EXPERT speaker
            audio_format: Output format

        Returns:
            Combined audio bytes

        Raises:
            AudioGenerationError: If generation fails
        """
        try:
            # Validate voices
            await self.validate_voices(host_voice, expert_voice)

            logger.info(
                "Generating audio for %d turns via Ollama (HOST=%s, EXPERT=%s)",
                len(script.turns),
                host_voice,
                expert_voice,
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
                        "Generated turn %d/%d (%s, %d chars)",
                        idx + 1,
                        len(script.turns),
                        turn.speaker.value,
                        len(turn.text),
                    )

                except Exception as e:
                    raise AudioGenerationError(
                        provider="ollama",
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
                "Generated complete podcast via Ollama: %d turns, %d bytes, %.1f seconds",
                len(script.turns),
                len(audio_bytes),
                len(combined) / 1000.0,
            )

            return audio_bytes

        except AudioGenerationError:
            raise
        except Exception as e:
            raise AudioGenerationError(
                provider="ollama",
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
        Generate audio for a single turn using Ollama TTS.

        Args:
            text: Text to convert to speech
            voice_id: Voice identifier
            audio_format: Audio format

        Returns:
            AudioSegment for this turn

        Raises:
            Exception: If Ollama API call fails
        """
        try:
            # Call Ollama TTS API
            # Note: This is a simplified implementation
            # Actual Ollama TTS API may vary by model
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": text,
                        "voice": voice_id,
                        "format": audio_format.value,
                        "stream": False,
                    },
                )

                if response.status_code != 200:
                    raise Exception(f"Ollama API error: {response.status_code} - {response.text}")

                # Extract audio from response
                # Note: Response format depends on Ollama TTS model
                result = response.json()
                if "audio" in result:
                    audio_bytes = bytes.fromhex(result["audio"])
                else:
                    raise Exception("No audio data in Ollama response")

            # Convert to AudioSegment
            segment = AudioSegment.from_file(
                io.BytesIO(audio_bytes),
                format=audio_format.value,
            )

            return segment

        except Exception as e:
            logger.error(
                "Ollama TTS API error for voice=%s, text_length=%d: %s",
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
