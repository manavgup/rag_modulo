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
                "Generating audio for %d turns (HOST=%s, EXPERT=%s, model=%s)",
                len(script.turns),
                host_voice,
                expert_voice,
                self.model,
            )
            logger.info("OpenAI client configured: %s", self.client is not None)

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

    def _chunk_text(self, text: str, max_length: int = 4000) -> list[str]:
        """
        Split text into chunks that fit within OpenAI's character limit.

        OpenAI TTS has a 4096 character limit. We use 4000 to leave buffer for edge cases.
        Splits on sentence boundaries when possible.

        Args:
            text: Text to chunk
            max_length: Maximum characters per chunk

        Returns:
            List of text chunks
        """
        if len(text) <= max_length:
            return [text]

        chunks = []
        current_chunk = ""

        # Split on sentences (., !, ?)
        sentences = []
        current_sentence = ""
        for char in text:
            current_sentence += char
            if char in {".", "!", "?"} and len(current_sentence) > 10:
                sentences.append(current_sentence.strip())
                current_sentence = ""

        # Add remaining text as last sentence
        if current_sentence.strip():
            sentences.append(current_sentence.strip())

        # Group sentences into chunks
        for sentence in sentences:
            # If a single sentence exceeds limit, split it forcefully
            if len(sentence) > max_length:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                # Split long sentence at word boundaries
                words = sentence.split()
                temp_chunk = ""
                for word in words:
                    if len(temp_chunk) + len(word) + 1 <= max_length:
                        temp_chunk += (" " + word) if temp_chunk else word
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk)
                        temp_chunk = word
                if temp_chunk:
                    chunks.append(temp_chunk)
            elif len(current_chunk) + len(sentence) + 1 <= max_length:
                current_chunk += (" " + sentence) if current_chunk else sentence
            else:
                chunks.append(current_chunk)
                current_chunk = sentence

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)

        logger.info("Split text of %d chars into %d chunks", len(text), len(chunks))
        return chunks

    async def _generate_turn_audio(
        self,
        text: str,
        voice_id: str,
        audio_format: AudioFormat,
    ) -> AudioSegment:
        """
        Generate audio for a single turn using OpenAI TTS.

        Automatically chunks text if it exceeds OpenAI's 4096 character limit.

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
            # ALWAYS log text length for debugging
            logger.info("Processing turn audio: text_len=%d chars, voice=%s", len(text), voice_id)

            # Check if text needs chunking - use 3500 to be extra safe
            # OpenAI limit is 4096, but we want a larger buffer
            if len(text) > 3500:
                logger.warning("Turn text exceeds 3500 chars (%d), will chunk it", len(text))
                chunks = self._chunk_text(text, max_length=3500)

                # Validate ALL chunks are safe
                for i, chunk in enumerate(chunks):
                    if len(chunk) > 4095:
                        logger.error("Chunk %d exceeds limit: %d chars", i + 1, len(chunk))
                        raise ValueError(f"Chunk {i + 1} exceeds OpenAI limit: {len(chunk)} chars")
                    logger.info("Chunk %d/%d: %d chars (safe)", i + 1, len(chunks), len(chunk))

                # Generate audio for each chunk
                chunk_segments = []
                for i, chunk in enumerate(chunks):
                    logger.info("Generating audio for chunk %d/%d", i + 1, len(chunks))

                    response = await self.client.audio.speech.create(
                        model=self.model,
                        voice=voice_id,  # type: ignore[arg-type]
                        input=chunk,
                        response_format=audio_format.value,  # type: ignore[arg-type]
                    )

                    audio_bytes = response.content
                    segment = AudioSegment.from_file(
                        io.BytesIO(audio_bytes),
                        format=audio_format.value,
                    )
                    chunk_segments.append(segment)
                    logger.info("Chunk %d/%d audio generated successfully", i + 1, len(chunks))

                # Combine chunks with tiny pause between them
                combined = AudioSegment.empty()
                for i, segment in enumerate(chunk_segments):
                    combined += segment
                    # Add 100ms pause between chunks (except last)
                    if i < len(chunk_segments) - 1:
                        combined += AudioSegment.silent(duration=100)

                logger.info("Combined %d chunks into single turn audio", len(chunks))
                return combined
            else:
                # Text fits in single request - normal flow
                logger.info("Text fits in single request (%d chars), sending to OpenAI TTS", len(text))

                response = await self.client.audio.speech.create(
                    model=self.model,
                    voice=voice_id,  # type: ignore[arg-type]
                    input=text,
                    response_format=audio_format.value,  # type: ignore[arg-type]
                )

                logger.info("OpenAI TTS response received successfully")

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
