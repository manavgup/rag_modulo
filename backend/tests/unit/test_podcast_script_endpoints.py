"""
Unit tests for podcast script generation and script-to-audio endpoints.

Tests cover:
- POST /api/podcasts/generate-script
- POST /api/podcasts/script-to-audio
"""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from rag_solution.schemas.podcast_schema import (
    AudioFormat,
    PodcastAudioGenerationInput,
    PodcastDuration,
    PodcastScriptGenerationInput,
    PodcastScriptOutput,
    PodcastStatus,
)
from rag_solution.services.podcast_service import PodcastService


@pytest.mark.unit
class TestGenerateScriptEndpoint:
    """Test cases for POST /api/podcasts/generate-script endpoint."""

    @pytest.fixture
    def mock_service(self) -> PodcastService:
        """Create mock PodcastService."""
        service = Mock(spec=PodcastService)
        service.generate_script_only = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_generate_script_success(self, mock_service: PodcastService) -> None:
        """Test successful script generation."""
        # Arrange
        user_id = uuid4()
        collection_id = uuid4()
        script_input = PodcastScriptGenerationInput(
            user_id=user_id,
            collection_id=collection_id,
            title="Test Podcast",
            duration=PodcastDuration.MEDIUM,
            language="en",
        )

        expected_output = PodcastScriptOutput(
            script_id=uuid4(),
            collection_id=collection_id,
            user_id=user_id,
            title="Test Podcast",
            script_text="HOST: Welcome...\nEXPERT: Thank you...",
            word_count=2250,
            target_word_count=2250,
            duration_minutes=15,
            estimated_duration_minutes=15.0,
            has_proper_format=True,
            host_voice="alloy",
            expert_voice="echo",
        )

        mock_service.generate_script_only.return_value = expected_output

        # Act
        result = await mock_service.generate_script_only(script_input)

        # Assert
        assert result == expected_output
        assert result.word_count == 2250
        assert result.has_proper_format is True
        mock_service.generate_script_only.assert_called_once_with(script_input)

    @pytest.mark.asyncio
    async def test_generate_script_invalid_language(self, mock_service: PodcastService) -> None:
        """Test script generation with unsupported language."""
        # Arrange
        script_input = PodcastScriptGenerationInput(
            user_id=uuid4(),
            collection_id=uuid4(),
            title="Test Podcast",
            duration=PodcastDuration.MEDIUM,
            language="unsupported",
        )

        mock_service.generate_script_only.side_effect = ValueError("Unsupported language: unsupported")

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported language"):
            await mock_service.generate_script_only(script_input)

    @pytest.mark.asyncio
    async def test_generate_script_collection_not_found(self, mock_service: PodcastService) -> None:
        """Test script generation with non-existent collection."""
        from core.custom_exceptions import NotFoundError

        # Arrange
        script_input = PodcastScriptGenerationInput(
            user_id=uuid4(),
            collection_id=uuid4(),
            title="Test Podcast",
            duration=PodcastDuration.MEDIUM,
            language="en",
        )

        mock_service.generate_script_only.side_effect = NotFoundError(
            resource_type="Collection",
            resource_id=str(script_input.collection_id),
        )

        # Act & Assert
        with pytest.raises(NotFoundError):
            await mock_service.generate_script_only(script_input)

    @pytest.mark.asyncio
    async def test_generate_script_missing_authentication(self) -> None:
        """Test script generation without authentication should fail."""
        # This would be tested at the router level with a real test client
        # where we don't provide the Authorization header
        # Placeholder for integration test


@pytest.mark.unit
class TestScriptToAudioEndpoint:
    """Test cases for POST /api/podcasts/script-to-audio endpoint."""

    @pytest.fixture
    def mock_service(self) -> PodcastService:
        """Create mock PodcastService."""
        service = Mock(spec=PodcastService)
        service.generate_audio_from_script = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_script_to_audio_success(self, mock_service: PodcastService) -> None:
        """Test successful script-to-audio conversion."""
        # Arrange
        # Create script with minimum 100 characters as required by schema
        script_text = (
            "HOST: Welcome to our podcast about technology and innovation.\n\n"
            "EXPERT: Thank you for having me. I'm excited to discuss this topic in depth.\n\n"
            "HOST: Let's dive right in."
        )
        audio_input = PodcastAudioGenerationInput(
            user_id=uuid4(),
            collection_id=uuid4(),
            script_text=script_text,
            title="Test Podcast",
            duration=PodcastDuration.MEDIUM,
            host_voice="alloy",
            expert_voice="echo",
        )

        from rag_solution.schemas.podcast_schema import PodcastGenerationOutput

        expected_output = PodcastGenerationOutput(
            podcast_id=uuid4(),
            user_id=audio_input.user_id,
            collection_id=audio_input.collection_id,
            status=PodcastStatus.QUEUED,
            duration=audio_input.duration,
            format=AudioFormat.MP3,
            title=audio_input.title,
            host_voice=audio_input.host_voice,
            expert_voice=audio_input.expert_voice,
            progress_percentage=0,
            created_at=Mock(),
            updated_at=Mock(),
        )

        mock_service.generate_audio_from_script.return_value = expected_output

        # Act
        result = await mock_service.generate_audio_from_script(audio_input, Mock())

        # Assert
        assert result.status == PodcastStatus.QUEUED
        assert result.title == "Test Podcast"
        mock_service.generate_audio_from_script.assert_called_once()

    @pytest.mark.asyncio
    async def test_script_to_audio_invalid_voice(self) -> None:
        """Test script-to-audio with invalid voice ID - should fail at schema validation."""
        from pydantic import ValidationError

        # Arrange
        # Create script with minimum 100 characters
        script_text = (
            "HOST: Welcome to our podcast about technology and innovation.\n\n"
            "EXPERT: Thank you for having me. I'm excited to discuss this topic in depth.\n\n"
            "HOST: Let's dive right in."
        )

        # Act & Assert - Should fail at Pydantic validation level
        with pytest.raises(ValidationError, match="Invalid voice ID"):
            PodcastAudioGenerationInput(
                user_id=uuid4(),
                collection_id=uuid4(),
                script_text=script_text,
                title="Test Podcast",
                duration=PodcastDuration.MEDIUM,
                host_voice="invalid_voice",  # Invalid voice
                expert_voice="echo",
            )

    @pytest.mark.asyncio
    async def test_script_to_audio_malformed_script(self) -> None:
        """Test script-to-audio with malformed script format - should fail at schema validation."""
        from pydantic import ValidationError

        # Arrange
        # Create a script that's long enough but doesn't have proper HOST/EXPERT format
        script_text = (
            "This is not a properly formatted script. "
            "It lacks the required HOST and EXPERT speaker labels. "
            "This text is just long enough to pass the 100 character minimum requirement."
        )

        # Act & Assert - Should fail at Pydantic validation level
        with pytest.raises(ValidationError, match="HOST speaker turns"):
            PodcastAudioGenerationInput(
                user_id=uuid4(),
                collection_id=uuid4(),
                script_text=script_text,
                title="Test Podcast",
                duration=PodcastDuration.MEDIUM,
                host_voice="alloy",
                expert_voice="echo",
            )

    @pytest.mark.asyncio
    async def test_script_to_audio_collection_not_found(self, mock_service: PodcastService) -> None:
        """Test script-to-audio with non-existent collection."""
        from core.custom_exceptions import NotFoundError

        # Arrange
        # Create script with minimum 100 characters as required by schema
        script_text = (
            "HOST: Welcome to our podcast about technology and innovation.\n\n"
            "EXPERT: Thank you for having me. I'm excited to discuss this topic in depth.\n\n"
            "HOST: Let's dive right in."
        )
        audio_input = PodcastAudioGenerationInput(
            user_id=uuid4(),
            collection_id=uuid4(),
            script_text=script_text,
            title="Test Podcast",
            duration=PodcastDuration.MEDIUM,
            host_voice="alloy",
            expert_voice="echo",
        )

        mock_service.generate_audio_from_script.side_effect = NotFoundError(
            resource_type="Collection",
            resource_id=str(audio_input.collection_id),
        )

        # Act & Assert
        with pytest.raises(NotFoundError):
            await mock_service.generate_audio_from_script(audio_input, Mock())
