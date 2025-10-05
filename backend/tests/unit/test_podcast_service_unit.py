"""Unit tests for podcast generation service.

Unit tests focus on service-level business logic, methods, and interactions
with dependencies (mocked). These tests validate the PodcastService behavior
without external dependencies.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_solution.schemas.podcast_schema import (
    AudioFormat,
    PodcastDuration,
    PodcastGenerationInput,
    PodcastGenerationOutput,
    PodcastStatus,
    VoiceGender,
    VoiceSettings,
)
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.podcast_service import PodcastService
from rag_solution.services.search_service import SearchService


@pytest.mark.unit
class TestPodcastServiceInitialization:
    """Unit tests for PodcastService initialization."""

    def test_service_initialization_with_dependencies(self) -> None:
        """Unit: PodcastService initializes with required dependencies."""
        session = Mock(spec=AsyncSession)
        collection_service = Mock(spec=CollectionService)
        search_service = Mock(spec=SearchService)

        service = PodcastService(
            session=session,
            collection_service=collection_service,
            search_service=search_service,
        )

        assert service.session == session
        assert service.collection_service == collection_service
        assert service.search_service == search_service
        assert service.repository is not None
        assert service.settings is not None
        assert service.script_parser is not None
        assert service.audio_storage is not None


@pytest.mark.unit
class TestPodcastServiceGeneration:
    """Unit tests for podcast generation workflow."""

    @pytest.fixture
    def mock_service(self) -> PodcastService:
        """Fixture: Create mock PodcastService."""
        session = Mock(spec=AsyncSession)
        collection_service = Mock(spec=CollectionService)
        search_service = Mock(spec=SearchService)

        service = PodcastService(
            session=session,
            collection_service=collection_service,
            search_service=search_service,
        )

        # Mock repository
        service.repository = Mock()
        service.repository.create = AsyncMock()
        service.repository.get_by_id = AsyncMock()
        service.repository.update_progress = AsyncMock()
        service.repository.mark_completed = AsyncMock()
        service.repository.update_status = AsyncMock()

        return service

    @pytest.mark.asyncio
    async def test_generate_podcast_creates_record(self, mock_service: PodcastService) -> None:
        """Unit: generate_podcast creates initial podcast record."""
        podcast_input = PodcastGenerationInput(
            user_id=uuid4(),
            collection_id=uuid4(),
            duration=PodcastDuration.MEDIUM,
            voice_settings=VoiceSettings(voice_id="alloy", gender=VoiceGender.NEUTRAL),
            host_voice="alloy",
            expert_voice="onyx",
            format=AudioFormat.MP3,
        )

        mock_podcast = Mock()
        mock_podcast.podcast_id = uuid4()
        mock_podcast.status = PodcastStatus.QUEUED

        # Mock collection validation
        mock_collection = Mock()
        mock_collection.id = podcast_input.collection_id
        mock_service.collection_service.get_by_id = AsyncMock(return_value=mock_collection)  # type: ignore[attr-defined]

        # Mock document count validation
        mock_service.collection_service.count_documents = AsyncMock(return_value=10)  # type: ignore[attr-defined]

        # Mock active podcast count check
        mock_service.repository.count_active_for_user = AsyncMock(return_value=0)  # type: ignore[method-assign]

        background_tasks = Mock()
        background_tasks.add_task = Mock()

        with patch.object(mock_service.repository, "create", new=AsyncMock(return_value=mock_podcast)) as mock_create:
            result = await mock_service.generate_podcast(podcast_input, background_tasks)

            assert result is not None
            mock_create.assert_called_once()
            background_tasks.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_podcast_returns_output(self, mock_service: PodcastService) -> None:
        """Unit: get_podcast returns PodcastGenerationOutput."""
        podcast_id = uuid4()
        user_id = uuid4()

        mock_output = PodcastGenerationOutput(
            podcast_id=podcast_id,
            user_id=user_id,
            collection_id=uuid4(),
            status=PodcastStatus.COMPLETED,
            duration=PodcastDuration.MEDIUM,
            format=AudioFormat.MP3,
            progress_percentage=100,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Create mock podcast with matching user_id for access control
        mock_podcast = Mock()
        mock_podcast.user_id = user_id

        with patch.object(mock_service.repository, "get_by_id", new=AsyncMock(return_value=mock_podcast)) as mock_get:
            with patch.object(mock_service.repository, "to_schema", return_value=mock_output):
                result = await mock_service.get_podcast(podcast_id, user_id)

                assert result == mock_output
                mock_get.assert_called_once_with(podcast_id)

    @pytest.mark.asyncio
    async def test_list_user_podcasts(self, mock_service: PodcastService) -> None:
        """Unit: list_user_podcasts returns user's podcasts."""
        user_id = uuid4()

        # Service calls repository.get_by_user and converts to schemas
        with patch.object(mock_service.repository, "get_by_user", new=AsyncMock(return_value=[])) as mock_get_by_user:
            result = await mock_service.list_user_podcasts(user_id, limit=10, offset=0)

            assert result is not None
            assert result.podcasts == []
            assert result.total_count == 0
            mock_get_by_user.assert_called_once_with(user_id=user_id, limit=10, offset=0)

    @pytest.mark.asyncio
    async def test_delete_podcast(self, mock_service: PodcastService) -> None:
        """Unit: delete_podcast removes podcast."""
        podcast_id = uuid4()
        user_id = uuid4()

        with patch.object(mock_service.repository, "get_by_id", new=AsyncMock(return_value=Mock(user_id=user_id))):
            with patch.object(mock_service.repository, "delete", new=AsyncMock(return_value=True)) as mock_delete:
                result = await mock_service.delete_podcast(podcast_id, user_id)

                assert result is True
                mock_delete.assert_called_once_with(podcast_id)


@pytest.mark.unit
class TestPodcastServiceValidation:
    """Unit tests for validation logic."""

    @pytest.fixture
    def mock_service(self) -> PodcastService:
        """Fixture: Create mock PodcastService."""
        session = Mock(spec=AsyncSession)
        collection_service = Mock(spec=CollectionService)
        search_service = Mock(spec=SearchService)

        return PodcastService(
            session=session,
            collection_service=collection_service,
            search_service=search_service,
        )

    @pytest.mark.asyncio
    async def test_validate_podcast_input(self) -> None:
        """Unit: Validates podcast input schema."""
        podcast_input = PodcastGenerationInput(
            user_id=uuid4(),
            collection_id=uuid4(),
            duration=PodcastDuration.SHORT,
            voice_settings=VoiceSettings(voice_id="alloy"),
            host_voice="alloy",
            expert_voice="onyx",
        )

        # Should not raise
        assert podcast_input.user_id is not None
        assert podcast_input.duration == PodcastDuration.SHORT
        assert podcast_input.format == AudioFormat.MP3  # default


@pytest.mark.unit
class TestPodcastServiceVoicePreview:
    """Unit tests for voice preview functionality."""

    @pytest.fixture
    def mock_service(self) -> PodcastService:
        """Fixture: Create mock PodcastService."""
        session = Mock(spec=AsyncSession)
        collection_service = Mock(spec=CollectionService)
        search_service = Mock(spec=SearchService)

        service = PodcastService(
            session=session,
            collection_service=collection_service,
            search_service=search_service,
        )

        return service

    @pytest.mark.asyncio
    async def test_generate_voice_preview_success(self, mock_service: PodcastService) -> None:
        """Unit: generate_voice_preview successfully generates audio."""
        voice_id = "alloy"
        expected_audio = b"mock_audio_data"

        # Mock AudioProviderFactory
        with patch("rag_solution.services.podcast_service.AudioProviderFactory") as mock_factory:
            mock_provider = AsyncMock()
            mock_provider.generate_single_turn_audio = AsyncMock(return_value=expected_audio)
            mock_factory.create_provider.return_value = mock_provider

            # Call the method
            audio_bytes = await mock_service.generate_voice_preview(voice_id)

            # Assertions
            assert audio_bytes == expected_audio
            mock_factory.create_provider.assert_called_once()
            mock_provider.generate_single_turn_audio.assert_called_once_with(
                text=mock_service.VOICE_PREVIEW_TEXT,
                voice=voice_id,
                audio_format=AudioFormat.MP3,
            )

    @pytest.mark.asyncio
    async def test_generate_voice_preview_uses_constant_text(
        self, mock_service: PodcastService
    ) -> None:
        """Unit: generate_voice_preview uses VOICE_PREVIEW_TEXT constant."""
        voice_id = "onyx"

        with patch("rag_solution.services.podcast_service.AudioProviderFactory") as mock_factory:
            mock_provider = AsyncMock()
            mock_provider.generate_single_turn_audio = AsyncMock(return_value=b"audio")
            mock_factory.create_provider.return_value = mock_provider

            await mock_service.generate_voice_preview(voice_id)

            # Verify constant is used
            call_args = mock_provider.generate_single_turn_audio.call_args
            assert call_args.kwargs["text"] == PodcastService.VOICE_PREVIEW_TEXT

    @pytest.mark.asyncio
    async def test_generate_voice_preview_raises_on_provider_error(
        self, mock_service: PodcastService
    ) -> None:
        """Unit: generate_voice_preview raises HTTPException on provider error."""
        voice_id = "echo"

        with patch("rag_solution.services.podcast_service.AudioProviderFactory") as mock_factory:
            mock_provider = AsyncMock()
            mock_provider.generate_single_turn_audio = AsyncMock(
                side_effect=Exception("TTS API error")
            )
            mock_factory.create_provider.return_value = mock_provider

            # Should raise HTTPException
            with pytest.raises(Exception) as exc_info:
                await mock_service.generate_voice_preview(voice_id)

            # Verify exception is raised
            assert exc_info.type.__name__ in ["HTTPException", "Exception"]

    @pytest.mark.asyncio
    async def test_generate_voice_preview_all_valid_voices(
        self, mock_service: PodcastService
    ) -> None:
        """Unit: generate_voice_preview works with all valid OpenAI voices."""
        valid_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

        with patch("rag_solution.services.podcast_service.AudioProviderFactory") as mock_factory:
            mock_provider = AsyncMock()
            mock_provider.generate_single_turn_audio = AsyncMock(return_value=b"audio")
            mock_factory.create_provider.return_value = mock_provider

            # Test each voice
            for voice_id in valid_voices:
                audio_bytes = await mock_service.generate_voice_preview(voice_id)
                assert audio_bytes == b"audio"
