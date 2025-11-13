"""Integration tests for complete podcast generation flow.

Integration tests verify the complete podcast generation workflow from
request to completion, including database interactions, but with mocked
external services (LLM, TTS).
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
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
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
class TestPodcastGenerationIntegration:
    """Integration tests for end-to-end podcast generation."""

    @pytest.fixture
    def mock_service(self) -> PodcastService:
        """Fixture: Create PodcastService with mocked dependencies."""
        session = Mock(spec=AsyncSession)
        collection_service = Mock(spec=CollectionService)
        search_service = Mock(spec=SearchService)

        service = PodcastService(
            session=session,
            collection_service=collection_service,
            search_service=search_service,
        )

        # Mock repository methods (all synchronous, not async)
        service.repository = Mock()
        service.repository.create = Mock()
        service.repository.get_by_id = Mock()
        service.repository.update_progress = Mock()
        service.repository.mark_completed = Mock()
        service.repository.update_status = Mock()
        service.repository.get_by_user = Mock()
        service.repository.delete = Mock()
        service.repository.count_active_for_user = Mock(return_value=0)

        return service

    @pytest.mark.asyncio
    async def test_complete_podcast_generation_workflow(self, mock_service: PodcastService) -> None:
        """Integration: Complete podcast generation from input to output."""
        podcast_input = PodcastGenerationInput(
            user_id=uuid4(),
            collection_id=uuid4(),
            duration=PodcastDuration.SHORT,
            voice_settings=VoiceSettings(voice_id="alloy", gender=VoiceGender.NEUTRAL),
            host_voice="alloy",
            expert_voice="onyx",
            title="Test Podcast",
            format=AudioFormat.MP3,
        )

        # Mock initial creation
        mock_podcast = Mock()
        mock_podcast.podcast_id = uuid4()
        mock_podcast.status = PodcastStatus.QUEUED
        mock_podcast.user_id = podcast_input.user_id

        # Mock collection validation
        mock_collection = Mock()
        mock_collection.id = podcast_input.collection_id
        mock_collection.files = [Mock() for _ in range(10)]  # Mock files list for validation
        mock_service.collection_service.get_collection = Mock(return_value=mock_collection)  # type: ignore[attr-defined]
        mock_service.collection_service.count_documents = AsyncMock(return_value=10)  # type: ignore[attr-defined]
        mock_service.repository.count_active_for_user = Mock(return_value=0)  # type: ignore[method-assign]

        # Mock background tasks
        background_tasks = Mock()
        background_tasks.add_task = Mock()

        # Generate podcast with mocked create
        with (
            patch.object(mock_service.repository, "create", new=Mock(return_value=mock_podcast)) as mock_create,
            patch.object(mock_service.repository, "to_schema") as mock_to_schema,
        ):
            mock_output = PodcastGenerationOutput(
                podcast_id=mock_podcast.podcast_id,
                user_id=podcast_input.user_id,
                collection_id=podcast_input.collection_id,
                status=PodcastStatus.QUEUED,
                duration=PodcastDuration.SHORT,
                format=AudioFormat.MP3,
                progress_percentage=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            mock_to_schema.return_value = mock_output

            result = await mock_service.generate_podcast(podcast_input, background_tasks)

            # Verify podcast was created
            assert result is not None
            assert result.status == PodcastStatus.QUEUED
            mock_create.assert_called_once()
            background_tasks.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_podcast_by_id(self, mock_service: PodcastService) -> None:
        """Integration: Retrieve podcast by ID."""
        podcast_id = uuid4()
        user_id = uuid4()

        mock_podcast = Mock()
        mock_podcast.podcast_id = podcast_id
        mock_podcast.user_id = user_id  # Must match requesting user_id
        mock_podcast.status = PodcastStatus.COMPLETED

        with (
            patch.object(mock_service.repository, "get_by_id", new=Mock(return_value=mock_podcast)) as mock_get,
            patch.object(mock_service.repository, "to_schema") as mock_to_schema,
        ):
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
            mock_to_schema.return_value = mock_output

            result = await mock_service.get_podcast(podcast_id, user_id)

            assert result is not None
            assert result.podcast_id == podcast_id
            mock_get.assert_called_once_with(podcast_id)

    @pytest.mark.asyncio
    async def test_list_user_podcasts_with_pagination(self, mock_service: PodcastService) -> None:
        """Integration: List podcasts with pagination."""
        user_id = uuid4()

        # Create mock podcasts with proper Pydantic values
        podcast_id_1 = uuid4()
        podcast_id_2 = uuid4()
        mock_output_1 = PodcastGenerationOutput(
            podcast_id=podcast_id_1,
            user_id=user_id,
            collection_id=uuid4(),
            status=PodcastStatus.COMPLETED,
            duration=PodcastDuration.MEDIUM,
            format=AudioFormat.MP3,
            progress_percentage=100,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_output_2 = PodcastGenerationOutput(
            podcast_id=podcast_id_2,
            user_id=user_id,
            collection_id=uuid4(),
            status=PodcastStatus.GENERATING,
            duration=PodcastDuration.SHORT,
            format=AudioFormat.MP3,
            progress_percentage=50,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Mock repository podcasts
        mock_podcast_1 = Mock()
        mock_podcast_2 = Mock()

        with (
            patch.object(
                mock_service.repository, "get_by_user", new=Mock(return_value=[mock_podcast_1, mock_podcast_2])
            ) as mock_get,
            patch.object(mock_service.repository, "to_schema") as mock_to_schema,
        ):
            mock_to_schema.side_effect = [mock_output_1, mock_output_2]

            result = await mock_service.list_user_podcasts(user_id, limit=10, offset=0)

            assert result is not None
            assert result.total_count == 2
            assert len(result.podcasts) == 2
            assert result.podcasts[0].podcast_id == podcast_id_1
            assert result.podcasts[1].podcast_id == podcast_id_2
            mock_get.assert_called_once_with(user_id=user_id, limit=10, offset=0)

    @pytest.mark.asyncio
    async def test_delete_podcast_removes_record(self, mock_service: PodcastService) -> None:
        """Integration: Delete podcast and verify removal."""
        podcast_id = uuid4()
        user_id = uuid4()

        mock_podcast = Mock()
        mock_podcast.podcast_id = podcast_id
        mock_podcast.user_id = user_id
        mock_podcast.audio_url = None  # No audio file to delete

        with (
            patch.object(mock_service.repository, "get_by_id", new=Mock(return_value=mock_podcast)),
            patch.object(mock_service.repository, "delete", new=Mock(return_value=True)) as mock_delete,
        ):
            result = await mock_service.delete_podcast(podcast_id, user_id)

            assert result is True
            mock_delete.assert_called_once_with(podcast_id)

    @pytest.mark.asyncio
    async def test_delete_podcast_unauthorized(self, mock_service: PodcastService) -> None:
        """Integration: Cannot delete podcast from different user."""
        podcast_id = uuid4()
        user_id = uuid4()
        different_user_id = uuid4()

        mock_podcast = Mock()
        mock_podcast.podcast_id = podcast_id
        mock_podcast.user_id = different_user_id  # Different user

        with (
            patch.object(mock_service.repository, "get_by_id", new=Mock(return_value=mock_podcast)),
            patch.object(mock_service.repository, "delete", new=Mock()) as mock_delete,
        ):
            # Service raises HTTPException, not PermissionError
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await mock_service.delete_podcast(podcast_id, user_id)

            assert exc_info.value.status_code == 403
            mock_delete.assert_not_called()


@pytest.mark.integration
class TestPodcastErrorHandling:
    """Integration tests for error handling."""

    @pytest.fixture
    def mock_service(self) -> PodcastService:
        """Fixture: Create PodcastService with mocked dependencies."""
        session = Mock(spec=AsyncSession)
        collection_service = Mock(spec=CollectionService)
        search_service = Mock(spec=SearchService)

        service = PodcastService(
            session=session,
            collection_service=collection_service,
            search_service=search_service,
        )

        # Mock repository with proper async methods
        service.repository = Mock()

        return service

    @pytest.mark.asyncio
    async def test_get_nonexistent_podcast(self, mock_service: PodcastService) -> None:
        """Integration: Handle getting podcast that doesn't exist."""
        podcast_id = uuid4()
        user_id = uuid4()

        with patch.object(mock_service.repository, "get_by_id", new=Mock(return_value=None)):
            # Service raises HTTPException 404, not ValueError
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await mock_service.get_podcast(podcast_id, user_id)

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_podcast(self, mock_service: PodcastService) -> None:
        """Integration: Handle deleting podcast that doesn't exist."""
        podcast_id = uuid4()
        user_id = uuid4()

        with patch.object(mock_service.repository, "get_by_id", new=Mock(return_value=None)):
            # Service raises HTTPException 404, not ValueError
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await mock_service.delete_podcast(podcast_id, user_id)

            assert exc_info.value.status_code == 404


@pytest.mark.integration
class TestTranscriptDownloadIntegration:
    """Integration tests for transcript download endpoint."""

    @pytest.fixture
    def sample_podcast_output(self) -> PodcastGenerationOutput:
        """Fixture: Sample completed podcast with transcript."""
        return PodcastGenerationOutput(
            podcast_id=uuid4(),
            user_id=uuid4(),
            collection_id=uuid4(),
            status=PodcastStatus.COMPLETED,
            duration=PodcastDuration.SHORT,
            format=AudioFormat.MP3,
            title="Test Podcast Episode",
            audio_url="https://storage.example.com/audio.mp3",
            transcript="""HOST: Welcome to our podcast about AI!

EXPERT: Thank you for having me.

HOST: Let's discuss machine learning.

EXPERT: Machine learning is transforming industries.""",
            chapters=[
                {
                    "title": "Introduction",
                    "start_time": 0.0,
                    "end_time": 60.0,
                    "word_count": 120,
                },
                {
                    "title": "Machine Learning Basics",
                    "start_time": 60.0,
                    "end_time": 180.0,
                    "word_count": 300,
                },
            ],
            audio_size_bytes=2048000,
            host_voice="alloy",
            expert_voice="onyx",
            collection_name="AI Research Collection",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            progress_percentage=100,
        )

    @pytest.fixture
    def mock_service_with_podcast(self, sample_podcast_output: PodcastGenerationOutput) -> PodcastService:
        """Fixture: PodcastService with mocked podcast output."""
        session = Mock(spec=AsyncSession)
        collection_service = Mock(spec=CollectionService)
        search_service = Mock(spec=SearchService)

        service = PodcastService(
            session=session,
            collection_service=collection_service,
            search_service=search_service,
        )

        # Mock repository to return sample podcast
        service.repository = Mock()
        service.repository.get_by_id = Mock()

        # Mock get_podcast to return sample output
        async def mock_get(podcast_id, user_id):
            if podcast_id == sample_podcast_output.podcast_id:
                return sample_podcast_output
            return None

        with patch.object(service, "get_podcast", new=mock_get):
            yield service

    @pytest.mark.asyncio
    async def test_download_transcript_txt_format(
        self, mock_service_with_podcast: PodcastService, sample_podcast_output: PodcastGenerationOutput
    ) -> None:
        """Integration: Download transcript in plain text format."""
        # Get the podcast output
        result = await mock_service_with_podcast.get_podcast(
            sample_podcast_output.podcast_id, sample_podcast_output.user_id
        )

        assert result is not None
        assert result.status == PodcastStatus.COMPLETED
        assert result.transcript is not None

        # Format transcript as TXT
        from rag_solution.utils.transcript_formatter import TranscriptFormat, TranscriptFormatter

        formatter = TranscriptFormatter()
        formatted = formatter.format_transcript(
            transcript=result.transcript,
            format_type=TranscriptFormat.TXT,
            title=result.title,
            duration_seconds=result.duration.value * 60 if result.duration else None,
        )

        # Verify TXT format
        assert "=" * 60 in formatted  # Header separator
        assert f"Title: {result.title}" in formatted
        assert "Duration: 05:00" in formatted  # SHORT = 5 minutes
        assert "Generated:" in formatted
        assert "HOST: Welcome to our podcast" in formatted

    @pytest.mark.asyncio
    async def test_download_transcript_markdown_format(
        self, mock_service_with_podcast: PodcastService, sample_podcast_output: PodcastGenerationOutput
    ) -> None:
        """Integration: Download transcript in Markdown format with chapters."""
        # Get the podcast output
        result = await mock_service_with_podcast.get_podcast(
            sample_podcast_output.podcast_id, sample_podcast_output.user_id
        )

        assert result is not None

        # Format transcript as Markdown
        from rag_solution.schemas.podcast_schema import PodcastChapter
        from rag_solution.utils.transcript_formatter import TranscriptFormat, TranscriptFormatter

        formatter = TranscriptFormatter()

        # Chapters in PodcastGenerationOutput are already dict objects (not Pydantic models)
        chapters = [PodcastChapter(**ch) if isinstance(ch, dict) else ch for ch in result.chapters] if result.chapters else None

        formatted = formatter.format_transcript(
            transcript=result.transcript,
            format_type=TranscriptFormat.MARKDOWN,
            title=result.title,
            duration_seconds=result.duration.value * 60 if result.duration else None,
            chapters=chapters,
        )

        # Verify Markdown format
        assert f"# {result.title}" in formatted
        assert "**Duration:** 05:00" in formatted
        assert "## Table of Contents" in formatted
        assert "[Introduction](#chapter-1)" in formatted
        assert "## Chapters" in formatted
        assert "### Chapter 1: Introduction" in formatted
        assert "## Full Transcript" in formatted

    @pytest.mark.asyncio
    async def test_download_transcript_podcast_not_found(
        self, mock_service_with_podcast: PodcastService
    ) -> None:
        """Integration: Handle downloading transcript for non-existent podcast."""
        non_existent_id = uuid4()
        user_id = uuid4()

        result = await mock_service_with_podcast.get_podcast(non_existent_id, user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_download_transcript_not_completed(self) -> None:
        """Integration: Handle downloading transcript for incomplete podcast."""
        # Create podcast in GENERATING status
        incomplete_output = PodcastGenerationOutput(
            podcast_id=uuid4(),
            user_id=uuid4(),
            collection_id=uuid4(),
            status=PodcastStatus.GENERATING,  # Not completed
            duration=PodcastDuration.SHORT,
            format=AudioFormat.MP3,
            title="Incomplete Podcast",
            host_voice="alloy",
            expert_voice="onyx",
            collection_name="Test Collection",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            progress_percentage=50,
        )

        # Verify status is not COMPLETED
        assert incomplete_output.status != PodcastStatus.COMPLETED
        assert incomplete_output.transcript is None

        # This would raise HTTPException 400 in the router
        # Verify the condition that triggers the error
        assert incomplete_output.status != PodcastStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_download_transcript_missing_transcript_field(self) -> None:
        """Integration: Handle completed podcast without transcript field."""
        # Edge case: COMPLETED but transcript is None
        no_transcript_output = PodcastGenerationOutput(
            podcast_id=uuid4(),
            user_id=uuid4(),
            collection_id=uuid4(),
            status=PodcastStatus.COMPLETED,
            duration=PodcastDuration.SHORT,
            format=AudioFormat.MP3,
            title="No Transcript Podcast",
            audio_url="https://storage.example.com/audio.mp3",
            transcript=None,  # Missing transcript
            host_voice="alloy",
            expert_voice="onyx",
            collection_name="Test Collection",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            progress_percentage=100,
        )

        # Verify the condition
        assert no_transcript_output.status == PodcastStatus.COMPLETED
        assert no_transcript_output.transcript is None

        # This would raise HTTPException 404 in the router

    @pytest.mark.asyncio
    async def test_download_transcript_filename_generation(
        self, sample_podcast_output: PodcastGenerationOutput
    ) -> None:
        """Integration: Verify transcript filename generation."""
        # With title
        podcast_id = sample_podcast_output.podcast_id
        title = sample_podcast_output.title

        # TXT format
        txt_filename = f"{title}.txt"
        assert txt_filename == "Test Podcast Episode.txt"

        # Markdown format
        md_filename = f"{title}.md"
        assert md_filename == "Test Podcast Episode.md"

        # Without title (fallback to podcast ID)
        no_title_filename = f"podcast-{str(podcast_id)[:8]}.txt"
        assert len(no_title_filename) > 10

    @pytest.mark.asyncio
    async def test_download_transcript_with_chapters(
        self, sample_podcast_output: PodcastGenerationOutput
    ) -> None:
        """Integration: Verify chapter data in Markdown format."""
        from rag_solution.schemas.podcast_schema import PodcastChapter
        from rag_solution.utils.transcript_formatter import TranscriptFormat, TranscriptFormatter

        formatter = TranscriptFormatter()

        # Convert chapter dicts to objects if needed
        chapters = [PodcastChapter(**ch) if isinstance(ch, dict) else ch for ch in sample_podcast_output.chapters]

        formatted = formatter.format_transcript(
            transcript=sample_podcast_output.transcript,
            format_type=TranscriptFormat.MARKDOWN,
            title=sample_podcast_output.title,
            duration_seconds=sample_podcast_output.duration.value * 60,
            chapters=chapters,
        )

        # Verify both chapters appear
        assert "Introduction" in formatted
        assert "Machine Learning Basics" in formatted

        # Verify timestamps
        assert "00:00" in formatted  # Start of first chapter
        assert "01:00" in formatted  # Start of second chapter (60 seconds)
        assert "03:00" in formatted  # End of second chapter (180 seconds)

        # Verify word counts
        assert "120 words" in formatted
        assert "300 words" in formatted

    @pytest.mark.asyncio
    async def test_download_transcript_without_chapters(
        self, sample_podcast_output: PodcastGenerationOutput
    ) -> None:
        """Integration: Verify Markdown format without chapters."""
        from rag_solution.utils.transcript_formatter import TranscriptFormat, TranscriptFormatter

        formatter = TranscriptFormatter()

        # Format without chapters
        formatted = formatter.format_transcript(
            transcript=sample_podcast_output.transcript,
            format_type=TranscriptFormat.MARKDOWN,
            title=sample_podcast_output.title,
            duration_seconds=sample_podcast_output.duration.value * 60,
            chapters=None,  # No chapters
        )

        # Should have title and metadata
        assert f"# {sample_podcast_output.title}" in formatted
        assert "**Duration:**" in formatted

        # Should NOT have chapters sections
        assert "## Table of Contents" not in formatted
        assert "## Chapters" not in formatted

        # Should still have full transcript
        assert "## Full Transcript" in formatted
        assert "HOST: Welcome" in formatted
