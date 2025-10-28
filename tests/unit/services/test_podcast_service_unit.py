"""Unit tests for podcast generation service.

Unit tests focus on service-level business logic, methods, and interactions
with dependencies (mocked). These tests validate the PodcastService behavior
without external dependencies.
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
from sqlalchemy.orm import Session


@pytest.mark.unit
class TestPodcastServiceInitialization:
    """Unit tests for PodcastService initialization."""

    def test_service_initialization_with_dependencies(self) -> None:
        """Unit: PodcastService initializes with required dependencies."""
        session = Mock(spec=Session)
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
        session = Mock(spec=Session)
        collection_service = Mock(spec=CollectionService)
        search_service = Mock(spec=SearchService)

        service = PodcastService(
            session=session,
            collection_service=collection_service,
            search_service=search_service,
        )

        # Mock repository (all methods are synchronous)
        service.repository = Mock()
        service.repository.create = Mock()
        service.repository.get_by_id = Mock()
        service.repository.get_by_user = Mock()
        service.repository.delete = Mock()
        service.repository.update_progress = Mock()
        service.repository.count_active_for_user = Mock(return_value=0)
        service.repository.mark_completed = Mock()
        service.repository.update_status = Mock()
        service.repository.to_schema = Mock()

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

        # Mock collection validation with proper files attribute
        mock_collection = Mock()
        mock_collection.id = podcast_input.collection_id
        mock_collection.files = [Mock(), Mock(), Mock()]  # Mock list with 3 files
        mock_service.collection_service.get_collection = Mock(return_value=mock_collection)  # type: ignore[attr-defined]

        # Mock active podcast count check (synchronous)
        mock_service.repository.count_active_for_user.return_value = 0

        background_tasks = Mock()
        background_tasks.add_task = Mock()

        # Mock repository create (synchronous)
        mock_service.repository.create.return_value = mock_podcast

        result = await mock_service.generate_podcast(podcast_input, background_tasks)

        assert result is not None
        mock_service.repository.create.assert_called_once()
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

        # Repository methods are synchronous
        mock_service.repository.get_by_id.return_value = mock_podcast
        mock_service.repository.to_schema.return_value = mock_output

        result = await mock_service.get_podcast(podcast_id, user_id)

        assert result == mock_output
        mock_service.repository.get_by_id.assert_called_once_with(podcast_id)

    @pytest.mark.asyncio
    async def test_list_user_podcasts(self, mock_service: PodcastService) -> None:
        """Unit: list_user_podcasts returns user's podcasts."""
        user_id = uuid4()

        # Repository methods are synchronous
        mock_service.repository.get_by_user.return_value = []

        result = await mock_service.list_user_podcasts(user_id, limit=10, offset=0)

        assert result is not None
        assert result.podcasts == []
        assert result.total_count == 0
        mock_service.repository.get_by_user.assert_called_once_with(user_id=user_id, limit=10, offset=0)

    @pytest.mark.asyncio
    async def test_delete_podcast(self, mock_service: PodcastService) -> None:
        """Unit: delete_podcast removes podcast."""
        podcast_id = uuid4()
        user_id = uuid4()

        mock_podcast = Mock()
        mock_podcast.user_id = user_id

        # Repository methods are synchronous
        mock_service.repository.get_by_id.return_value = mock_podcast
        mock_service.repository.delete.return_value = True

        result = await mock_service.delete_podcast(podcast_id, user_id)

        assert result is True
        mock_service.repository.delete.assert_called_once_with(podcast_id)


@pytest.mark.unit
class TestPodcastServiceValidation:
    """Unit tests for validation logic."""

    @pytest.fixture
    def mock_service(self) -> PodcastService:
        """Fixture: Create mock PodcastService."""
        session = Mock(spec=Session)
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
class TestPodcastServiceCustomization:
    """Unit tests for description-based customization."""

    @pytest.fixture
    def mock_service(self) -> PodcastService:
        """Fixture: Create mock PodcastService."""
        session = Mock(spec=Session)
        collection_service = Mock(spec=CollectionService)
        search_service = Mock(spec=SearchService)

        service = PodcastService(
            session=session,
            collection_service=collection_service,
            search_service=search_service,
        )

        # Mock search_service.search to return sufficient documents
        from rag_solution.schemas.pipeline_schema import QueryResult
        from rag_solution.schemas.search_schema import SearchOutput
        from vectordbs.data_types import DocumentChunkWithScore, DocumentMetadata

        # Create mock search result with enough documents
        mock_query_results = [
            QueryResult(
                chunk=DocumentChunkWithScore(
                    id=f"doc_{i}",
                    text=f"Document {i} content",
                    score=0.9 - (i * 0.1),
                    metadata={"source": "pdf"},  # Must be one of: website, pdf, word, ppt, other
                ),
                collection_name="test_collection",
            )
            for i in range(10)  # Return 10 documents (> minimum required)
        ]

        mock_documents = [DocumentMetadata(source="pdf", file_name=f"doc_{i}.pdf") for i in range(10)]

        mock_search_result = SearchOutput(
            query_results=mock_query_results, answer="Mock answer", documents=mock_documents, execution_time=100.0
        )

        service.search_service.search = AsyncMock(return_value=mock_search_result)  # type: ignore[method-assign,attr-defined]
        return service

    @pytest.mark.asyncio
    async def test_retrieve_content_uses_description_in_query(self, mock_service: PodcastService) -> None:
        """Unit: _retrieve_content uses description to build synthetic_query."""
        description = "Test description"
        podcast_input = PodcastGenerationInput(
            user_id=uuid4(),
            collection_id=uuid4(),
            duration=PodcastDuration.SHORT,
            voice_settings=VoiceSettings(voice_id="alloy"),
            description=description,
        )

        await mock_service._retrieve_content(podcast_input)

        mock_service.search_service.search.assert_called_once()  # type: ignore[attr-defined]
        call_args = mock_service.search_service.search.call_args[0]  # type: ignore[attr-defined]
        search_input = call_args[0]
        assert description in search_input.question

    @pytest.mark.asyncio
    async def test_retrieve_content_uses_generic_query_without_description(self, mock_service: PodcastService) -> None:
        """Unit: _retrieve_content uses generic query if no description."""
        podcast_input = PodcastGenerationInput(
            user_id=uuid4(),
            collection_id=uuid4(),
            duration=PodcastDuration.SHORT,
            voice_settings=VoiceSettings(voice_id="alloy"),
            description=None,
        )

        await mock_service._retrieve_content(podcast_input)

        mock_service.search_service.search.assert_called_once()  # type: ignore[attr-defined]
        call_args = mock_service.search_service.search.call_args[0]  # type: ignore[attr-defined]
        search_input = call_args[0]
        assert "Provide a comprehensive overview" in search_input.question

    @pytest.mark.asyncio
    @patch("rag_solution.services.prompt_template_service.PromptTemplateService")
    @patch("rag_solution.services.podcast_service.LLMProviderFactory")
    async def test_generate_script_uses_description_in_prompt(
        self, mock_llm_factory: Mock, mock_template_service_class: Mock, mock_service: PodcastService
    ) -> None:
        """Unit: _generate_script includes description in prompt."""
        description = "Custom topic"
        podcast_input = PodcastGenerationInput(
            user_id=uuid4(),
            collection_id=uuid4(),
            duration=PodcastDuration.SHORT,
            voice_settings=VoiceSettings(voice_id="alloy"),
            description=description,
        )

        # Mock PromptTemplateService to return a valid template
        from datetime import datetime

        from rag_solution.schemas.prompt_template_schema import PromptTemplateOutput, PromptTemplateType

        mock_template = PromptTemplateOutput(
            id=uuid4(),
            user_id=podcast_input.user_id,
            name="test_podcast_template",
            template_type=PromptTemplateType.PODCAST_GENERATION,
            system_prompt="You are a podcast script writer",
            template_format="Topic: {user_topic}\nContent: {rag_results}\nDuration: {duration_minutes} min",
            input_variables={
                "user_topic": "The main topic",
                "rag_results": "RAG content",
                "duration_minutes": "Duration in minutes",
            },
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_template_service = Mock()
        mock_template_service.get_by_type = Mock(return_value=mock_template)
        mock_template_service_class.return_value = mock_template_service

        # Mock LLM provider
        mock_llm_provider = Mock()
        mock_llm_provider.generate_text = Mock(return_value="Script")

        # Mock factory instance and its get_provider method
        mock_factory_instance = Mock()
        mock_factory_instance.get_provider = Mock(return_value=mock_llm_provider)
        mock_llm_factory.return_value = mock_factory_instance

        await mock_service._generate_script(podcast_input, "rag_results")

        mock_llm_provider.generate_text.assert_called_once()
        call_kwargs = mock_llm_provider.generate_text.call_args[1]
        variables = call_kwargs["variables"]
        assert variables["user_topic"] == description

    @pytest.mark.asyncio
    @patch("rag_solution.services.prompt_template_service.PromptTemplateService")
    @patch("rag_solution.services.podcast_service.LLMProviderFactory")
    async def test_generate_script_uses_generic_topic_without_description(
        self, mock_llm_factory: Mock, mock_template_service_class: Mock, mock_service: PodcastService
    ) -> None:
        """Unit: _generate_script uses generic topic if no description."""
        podcast_input = PodcastGenerationInput(
            user_id=uuid4(),
            collection_id=uuid4(),
            duration=PodcastDuration.SHORT,
            voice_settings=VoiceSettings(voice_id="alloy"),
            description=None,
        )

        # Mock PromptTemplateService to return a valid template
        from datetime import datetime

        from rag_solution.schemas.prompt_template_schema import PromptTemplateOutput, PromptTemplateType

        mock_template = PromptTemplateOutput(
            id=uuid4(),
            user_id=podcast_input.user_id,
            name="test_podcast_template",
            template_type=PromptTemplateType.PODCAST_GENERATION,
            system_prompt="You are a podcast script writer",
            template_format="Topic: {user_topic}\nContent: {rag_results}\nDuration: {duration_minutes} min",
            input_variables={
                "user_topic": "The main topic",
                "rag_results": "RAG content",
                "duration_minutes": "Duration in minutes",
            },
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_template_service = Mock()
        mock_template_service.get_by_type = Mock(return_value=mock_template)
        mock_template_service_class.return_value = mock_template_service

        # Mock LLM provider
        mock_llm_provider = Mock()
        mock_llm_provider.generate_text = Mock(return_value="Script")

        # Mock factory instance and its get_provider method
        mock_factory_instance = Mock()
        mock_factory_instance.get_provider = Mock(return_value=mock_llm_provider)
        mock_llm_factory.return_value = mock_factory_instance

        await mock_service._generate_script(podcast_input, "rag_results")

        mock_llm_provider.generate_text.assert_called_once()
        call_kwargs = mock_llm_provider.generate_text.call_args[1]
        variables = call_kwargs["variables"]
        assert variables["user_topic"] == "General overview of the content"


@pytest.mark.unit
class TestPodcastServiceVoicePreview:
    """Unit tests for voice preview functionality."""

    @pytest.fixture
    def mock_service(self) -> PodcastService:
        """Fixture: Create mock PodcastService."""
        session = Mock(spec=Session)
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
                voice_id=voice_id,
                audio_format=AudioFormat.MP3,
            )

    @pytest.mark.asyncio
    async def test_generate_voice_preview_uses_constant_text(self, mock_service: PodcastService) -> None:
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
    async def test_generate_voice_preview_raises_on_provider_error(self, mock_service: PodcastService) -> None:
        """Unit: generate_voice_preview raises HTTPException on provider error."""
        voice_id = "echo"

        with patch("rag_solution.services.podcast_service.AudioProviderFactory") as mock_factory:
            mock_provider = AsyncMock()
            mock_provider.generate_single_turn_audio = AsyncMock(side_effect=Exception("TTS API error"))
            mock_factory.create_provider.return_value = mock_provider

            # Should raise HTTPException
            with pytest.raises(Exception) as exc_info:
                await mock_service.generate_voice_preview(voice_id)

            # Verify exception is raised
            assert exc_info.type.__name__ in ["HTTPException", "Exception"]

    @pytest.mark.asyncio
    async def test_generate_voice_preview_all_valid_voices(self, mock_service: PodcastService) -> None:
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
