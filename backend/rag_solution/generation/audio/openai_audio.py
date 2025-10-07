"""
OpenAI Text-to-Speech (TTS) audio provider.

Uses OpenAI's TTS API to generate high-quality podcast audio with multiple voices.
Implements turn-by-turn audio generation and combines segments with pauses.
"""

import io
import logging
from typing import Any, ClassVar

from openai import AsyncOpenAI
from pydub import AudioSegment

from rag_solution.schemas.podcast_schema import AudioFormat, PodcastScript, Speaker

from .base import AudioGenerationError, AudioProviderBase

logger = logging.getLogger(__name__)


class OpenAIAudioProvider(AudioProviderBase):
    """OpenAI TTS provider for podcast audio generation."""

    # Available OpenAI voices with metadata
    AVAILABLE_VOICES: ClassVar[list[dict[str, Any]]] = [
        {
            "voice_id": "alloy",
            "name": "Alloy",
            "gender": "neutral",
            "language": "en-US",
            "description": "Warm, conversational voice suitable for HOST",
        },
        {
            "voice_id": "echo",
            "name": "Echo",
            "gender": "male",
            "language": "en-US",
            "description": "Clear, authoritative male voice",
        },
        {
            "voice_id": "fable",
            "name": "Fable",
            "gender": "neutral",
            "language": "en-US",
            "description": "Expressive, storytelling voice",
        },
        {
            "voice_id": "onyx",
            "name": "Onyx",
            "gender": "male",
            "language": "en-US",
            "description": "Deep, authoritative voice suitable for EXPERT",
        },
        {
            "voice_id": "nova",
            "name": "Nova",
            "gender": "female",
            "language": "en-US",
            "description": "Bright, engaging female voice",
        },
        {
            "voice_id": "shimmer",
            "name": "Shimmer",
            "gender": "female",
            "language": "en-US",
            "description": "Warm, friendly female voice",
        },
    ]

    def __init__(
        self,
        api_key: str,
        model: str = "tts-1-hd",
        pause_duration_ms: int = 500,
    ):
        """
        Initialize OpenAI audio provider.

        Args:
            api_key: OpenAI API key
            model: TTS model to use (tts-1 or tts-1-hd)
            pause_duration_ms: Pause duration between speakers in milliseconds
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.pause_duration_ms = pause_duration_ms

        logger.info(
            "Initialized OpenAI audio provider with model=%s, pause=%dms",
            model,
            pause_duration_ms,
        )

    async def list_available_voices(self) -> list[dict[str, Any]]:
        """Get list of available OpenAI voices."""
        return self.AVAILABLE_VOICES

    async def generate_dialogue_audio(
        self,
        script: PodcastScript,
        host_voice: str = "alloy",
        expert_voice: str = "onyx",
        audio_format: AudioFormat = AudioFormat.MP3,
    ) -> bytes:
        """
        Generate podcast audio using OpenAI TTS with multiple voices.

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
                "Generating audio for %d turns (HOST=%s, EXPERT=%s)",
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
                        provider="openai",
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
                provider="openai",
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
        Generate audio for a single turn using OpenAI TTS.

        Args:
            text: Text to convert to speech
            voice_id: OpenAI voice ID
            audio_format: Audio format

        Returns:
            AudioSegment for this turn

        Raises:
            Exception: If API call fails
        """
        try:
            # Call OpenAI TTS API
            response = await self.client.audio.speech.create(
                model=self.model,
                voice=voice_id,
                input=text,
                response_format=audio_format.value,  # type: ignore[arg-type]
            )

            # Convert response to AudioSegment
            audio_bytes = response.content
            segment = AudioSegment.from_file(
                io.BytesIO(audio_bytes),
                format=audio_format.value,
            )

            return segment

        except Exception as e:
            logger.error(
                "OpenAI TTS API error for voice=%s, text_length=%d: %s",
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
