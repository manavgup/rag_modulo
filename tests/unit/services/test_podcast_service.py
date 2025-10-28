"""
Comprehensive tests for PodcastService
Generated on: 2025-10-18
Coverage: Unit tests for podcast generation, script generation, audio synthesis, and file management
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from core.custom_exceptions import NotFoundError, ValidationError
from rag_solution.models.collection import Collection
from rag_solution.schemas.podcast_schema import (
    AudioFormat,
    PodcastAudioGenerationInput,
    PodcastDuration,
    PodcastGenerationInput,
    PodcastGenerationOutput,
    PodcastListResponse,
    PodcastScript,
    PodcastScriptGenerationInput,
    PodcastScriptOutput,
    PodcastStatus,
    PodcastTurn,
    ScriptParsingResult,
    Speaker,
    VoiceGender,
    VoiceSettings,
)
from rag_solution.services.podcast_service import PodcastService, SupportedLanguage
from fastapi import BackgroundTasks, HTTPException

# ============================================================================
# SHARED FIXTURES
# ============================================================================

@pytest.fixture
def mock_session():
    """Mock database session"""
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.refresh = Mock()
    session.rollback = Mock()
    session.delete = Mock()
    session.execute = Mock()
    return session


@pytest.fixture
def mock_repository():
    """Mock podcast repository"""
    repo = Mock()
    podcast_id = uuid4()
    user_id = uuid4()
    collection_id = uuid4()

    def create_podcast_model(**kwargs):
        """Create a proper podcast model with all required fields"""
        # Handle audio_format - can be AudioFormat enum or string
        audio_fmt = kwargs.get("audio_format", AudioFormat.MP3)
        if isinstance(audio_fmt, AudioFormat):
            audio_fmt_value = audio_fmt.value
            audio_fmt_enum = audio_fmt
        elif isinstance(audio_fmt, str):
            audio_fmt_value = audio_fmt
            audio_fmt_enum = AudioFormat(audio_fmt)
        else:
            audio_fmt_value = AudioFormat.MP3.value
            audio_fmt_enum = AudioFormat.MP3

        # Handle duration - can be PodcastDuration enum or int
        dur = kwargs.get("duration", PodcastDuration.MEDIUM)
        if isinstance(dur, PodcastDuration):
            dur_value = dur.value
            dur_enum = dur
        elif isinstance(dur, int):
            dur_value = dur
            dur_enum = PodcastDuration(dur)
        else:
            dur_value = PodcastDuration.MEDIUM.value
            dur_enum = PodcastDuration.MEDIUM

        return Mock(
            podcast_id=kwargs.get("podcast_id", podcast_id),
            user_id=kwargs.get("user_id", user_id),
            collection_id=kwargs.get("collection_id", collection_id),
            status=kwargs.get("status", PodcastStatus.QUEUED),
            progress_percentage=kwargs.get("progress_percentage", 0),
            duration=dur_enum,
            audio_format=audio_fmt_enum,
            host_voice=kwargs.get("host_voice", "alloy"),
            expert_voice=kwargs.get("expert_voice", "onyx"),
            voice_settings=kwargs.get("voice_settings", {}),
            title=kwargs.get("title", "Test Podcast"),
            description=kwargs.get("description"),
            audio_url=None,
            transcript=None,
            audio_size_bytes=None,
            error_message=None,
            current_step=None,
            step_details=None,
            estimated_time_remaining=None,
            collection_name=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            completed_at=None,
        )

    repo.create = Mock(side_effect=create_podcast_model)  # Not async - returns model directly
    repo.get_by_id = Mock(return_value=None)  # Not async
    repo.get_by_user = Mock(return_value=[])  # Not async
    repo.count_active_for_user = Mock(return_value=0)  # Not async - returns int directly
    repo.update_progress = Mock()
    repo.update_status = Mock()
    repo.mark_completed = Mock()
    repo.delete = Mock(return_value=True)  # Not async

    # Return a proper schema object
    def to_schema_side_effect(podcast_model):
        def safe_int(value):
            if value is None or isinstance(value, (Mock, MagicMock)):
                return None
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        def safe_str(value):
            if value is None or isinstance(value, (Mock, MagicMock)):
                return None
            return str(value)

        def safe_dict(value):
            if value is None or isinstance(value, (Mock, MagicMock)):
                return None
            return dict(value)

        def safe_audio_format(value):
            if isinstance(value, AudioFormat):
                return value
            if isinstance(value, str):
                try:
                    return AudioFormat(value)
                except ValueError:
                    return AudioFormat.MP3
            return AudioFormat.MP3

        return PodcastGenerationOutput(
            podcast_id=podcast_model.podcast_id,
            user_id=podcast_model.user_id,
            collection_id=podcast_model.collection_id,
            status=podcast_model.status,
            duration=podcast_model.duration if isinstance(podcast_model.duration, PodcastDuration) else PodcastDuration.MEDIUM,
            format=safe_audio_format(podcast_model.audio_format),
            title=podcast_model.title,
            progress_percentage=podcast_model.progress_percentage,
            host_voice=podcast_model.host_voice,
            expert_voice=podcast_model.expert_voice,
            audio_url=safe_str(podcast_model.audio_url),
            transcript=safe_str(podcast_model.transcript),
            audio_size_bytes=safe_int(podcast_model.audio_size_bytes),
            error_message=safe_str(podcast_model.error_message),
            current_step=safe_str(podcast_model.current_step),
            step_details=safe_dict(podcast_model.step_details),
            estimated_time_remaining=safe_int(podcast_model.estimated_time_remaining),
            collection_name=safe_str(podcast_model.collection_name),
            created_at=podcast_model.created_at,
            updated_at=podcast_model.updated_at,
            completed_at=podcast_model.completed_at,
        )

    repo.to_schema = Mock(side_effect=to_schema_side_effect)
    return repo


@pytest.fixture
def mock_collection_service():
    """Mock collection service"""
    service = Mock()
    collection = Mock(spec=Collection)
    collection.id = uuid4()
    collection.name = "Test Collection"
    collection.files = [Mock(), Mock(), Mock()]  # 3 files
    service.get_collection = Mock(return_value=collection)
    return service


@pytest.fixture
def mock_search_service():
    """Mock search service"""
    service = Mock()
    # Create 20 documents to satisfy all duration thresholds (EXTENDED needs 15 minimum)
    query_results = [Mock(chunk=Mock(text=f"Document {i} content " * 100)) for i in range(1, 21)]
    service.search = AsyncMock(return_value=Mock(
        query_results=query_results,
        metadata={"strategies_used": ["vector_search"]}
    ))
    return service


@pytest.fixture
def mock_settings():
    """Mock settings"""
    settings = Mock()
    settings.podcast_min_documents = 1
    settings.podcast_max_concurrent_per_user = 5
    settings.podcast_storage_backend = "local"
    settings.podcast_local_storage_path = "/tmp/podcasts"
    settings.podcast_audio_provider = "openai"
    settings.llm_provider = "openai"
    settings.podcast_retrieval_top_k_short = 10
    settings.podcast_retrieval_top_k_medium = 20
    settings.podcast_retrieval_top_k_long = 30
    settings.podcast_retrieval_top_k_extended = 50
    return settings


@pytest.fixture
def mock_audio_storage():
    """Mock audio storage"""
    storage = AsyncMock()
    storage.store_audio = AsyncMock(return_value="/api/podcasts/123/audio")
    storage.retrieve_audio = AsyncMock(return_value=b"audio_data")
    storage.delete_audio = AsyncMock(return_value=True)
    storage.exists = AsyncMock(return_value=True)
    return storage


@pytest.fixture
def mock_script_parser():
    """Mock script parser"""
    parser = Mock()
    parsed_script = PodcastScript(
        turns=[
            PodcastTurn(speaker=Speaker.HOST, text="Welcome", estimated_duration=2.0),
            PodcastTurn(speaker=Speaker.EXPERT, text="Thanks", estimated_duration=1.5),
        ],
        total_duration=3.5,
        total_words=2
    )
    parser.parse = Mock(return_value=ScriptParsingResult(
        script=parsed_script,
        raw_text="HOST: Welcome\nEXPERT: Thanks",
        parsing_warnings=[]
    ))
    parser.parse_script = Mock(return_value=ScriptParsingResult(
        script=parsed_script,
        raw_text="HOST: Welcome\nEXPERT: Thanks",
        parsing_warnings=[]
    ))
    return parser


@pytest.fixture
def service(mock_session, mock_collection_service, mock_search_service, mock_repository, mock_settings, mock_audio_storage, mock_script_parser):
    """Service instance with mocked dependencies"""
    with patch("rag_solution.services.podcast_service.get_settings", return_value=mock_settings):
        with patch("rag_solution.services.podcast_service.PodcastRepository", return_value=mock_repository):
            with patch("rag_solution.services.podcast_service.PodcastScriptParser", return_value=mock_script_parser):
                svc = PodcastService(
                    session=mock_session,
                    collection_service=mock_collection_service,
                    search_service=mock_search_service,
                )
                svc.audio_storage = mock_audio_storage
                return svc


@pytest.fixture
def valid_podcast_input():
    """Valid podcast generation input"""
    return PodcastGenerationInput(
        user_id=uuid4(),
        collection_id=uuid4(),
        duration=PodcastDuration.MEDIUM,
        voice_settings=VoiceSettings(
            voice_id="nova",
            gender=VoiceGender.FEMALE,
            speed=1.0,
            pitch=1.0,
        ),
        title="Test Podcast",
        description="Test description",
        format=AudioFormat.MP3,
        host_voice="alloy",
        expert_voice="onyx",
    )


# ============================================================================
# UNIT TESTS - PODCAST GENERATION
# ============================================================================

class TestPodcastGenerationUnit:
    """
    Unit tests for podcast generation with fully mocked dependencies.
    Focus: Individual method behavior, business logic, error handling.
    """

    @pytest.mark.asyncio
    async def test_generate_podcast_success(self, service, valid_podcast_input, mock_repository):
        """Test successful podcast generation queueing"""
        background_tasks = BackgroundTasks()

        result = await service.generate_podcast(valid_podcast_input, background_tasks)

        assert mock_repository.create.called
        assert mock_repository.to_schema.called

    @pytest.mark.asyncio
    async def test_generate_podcast_missing_user_id(self, service):
        """Test podcast generation fails without user_id"""
        podcast_input = PodcastGenerationInput(
            user_id=None,  # Missing
            collection_id=uuid4(),
            duration=PodcastDuration.MEDIUM,
            voice_settings=VoiceSettings(voice_id="nova"),
            host_voice="alloy",
            expert_voice="onyx",
        )
        background_tasks = BackgroundTasks()

        with pytest.raises((ValidationError, HTTPException)):
            await service.generate_podcast(podcast_input, background_tasks)

    @pytest.mark.asyncio
    async def test_generate_podcast_collection_not_found(self, service, valid_podcast_input, mock_collection_service):
        """Test podcast generation fails for non-existent collection"""
        mock_collection_service.get_collection.side_effect = NotFoundError(
            resource_type="Collection",
            resource_id=str(valid_podcast_input.collection_id),
            message="Collection not found"
        )
        background_tasks = BackgroundTasks()

        with pytest.raises(HTTPException) as exc_info:
            await service.generate_podcast(valid_podcast_input, background_tasks)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_podcast_insufficient_documents(self, service, valid_podcast_input, mock_collection_service, mock_settings):
        """Test podcast generation fails with insufficient documents"""
        collection = Mock()
        collection.files = []  # No files
        mock_collection_service.get_collection.return_value = collection
        mock_settings.podcast_min_documents = 3
        background_tasks = BackgroundTasks()

        with pytest.raises(HTTPException) as exc_info:
            await service.generate_podcast(valid_podcast_input, background_tasks)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_podcast_exceeds_concurrent_limit(self, service, valid_podcast_input, mock_repository, mock_settings):
        """Test podcast generation fails when user exceeds concurrent limit"""
        mock_repository.count_active_for_user.return_value = 5
        mock_settings.podcast_max_concurrent_per_user = 5
        background_tasks = BackgroundTasks()

        with pytest.raises(HTTPException) as exc_info:
            await service.generate_podcast(valid_podcast_input, background_tasks)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_generate_podcast_different_durations(self, service, mock_repository):
        """Test podcast generation with different duration settings"""
        background_tasks = BackgroundTasks()

        for duration in [PodcastDuration.SHORT, PodcastDuration.MEDIUM, PodcastDuration.LONG, PodcastDuration.EXTENDED]:
            podcast_input = PodcastGenerationInput(
                user_id=uuid4(),
                collection_id=uuid4(),
                duration=duration,
                voice_settings=VoiceSettings(voice_id="nova"),
                host_voice="alloy",
                expert_voice="onyx",
            )

            result = await service.generate_podcast(podcast_input, background_tasks)
            assert mock_repository.create.called

    @pytest.mark.asyncio
    async def test_generate_podcast_different_audio_formats(self, service, valid_podcast_input):
        """Test podcast generation with different audio formats"""
        background_tasks = BackgroundTasks()

        for audio_format in [AudioFormat.MP3, AudioFormat.WAV, AudioFormat.OGG, AudioFormat.FLAC]:
            valid_podcast_input.format = audio_format
            result = await service.generate_podcast(valid_podcast_input, background_tasks)
            assert result is not None


# ============================================================================
# UNIT TESTS - CONTENT RETRIEVAL
# ============================================================================

class TestContentRetrievalUnit:
    """Unit tests for RAG content retrieval"""

    @pytest.mark.asyncio
    async def test_retrieve_content_success(self, service, valid_podcast_input, mock_search_service):
        """Test successful content retrieval via RAG"""
        result = await service._retrieve_content(valid_podcast_input)

        assert isinstance(result, str)
        assert len(result) > 0
        assert mock_search_service.search.called

    @pytest.mark.asyncio
    async def test_retrieve_content_with_description(self, service, valid_podcast_input, mock_search_service):
        """Test content retrieval with custom description"""
        valid_podcast_input.description = "Machine learning basics"

        result = await service._retrieve_content(valid_podcast_input)

        assert "Machine learning basics" in mock_search_service.search.call_args[0][0].question

    @pytest.mark.asyncio
    async def test_retrieve_content_without_description(self, service, valid_podcast_input, mock_search_service):
        """Test content retrieval without description (general overview)"""
        valid_podcast_input.description = None

        result = await service._retrieve_content(valid_podcast_input)

        assert "comprehensive overview" in mock_search_service.search.call_args[0][0].question.lower()

    @pytest.mark.asyncio
    async def test_retrieve_content_insufficient_results(self, service, valid_podcast_input, mock_search_service):
        """Test content retrieval fails with insufficient results"""
        mock_search_service.search.return_value = Mock(
            query_results=[],  # No results
            metadata={}
        )

        with pytest.raises(ValidationError) as exc_info:
            await service._retrieve_content(valid_podcast_input)

        assert "Insufficient content retrieved" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_retrieve_content_top_k_mapping(self, service, mock_settings):
        """Test top_k values for different durations"""
        for duration, expected_top_k in [
            (PodcastDuration.SHORT, mock_settings.podcast_retrieval_top_k_short),
            (PodcastDuration.MEDIUM, mock_settings.podcast_retrieval_top_k_medium),
            (PodcastDuration.LONG, mock_settings.podcast_retrieval_top_k_long),
            (PodcastDuration.EXTENDED, mock_settings.podcast_retrieval_top_k_extended),
        ]:
            podcast_input = PodcastGenerationInput(
                user_id=uuid4(),
                collection_id=uuid4(),
                duration=duration,
                voice_settings=VoiceSettings(voice_id="nova"),
                host_voice="alloy",
                expert_voice="onyx",
            )

            await service._retrieve_content(podcast_input)

            call_args = service.search_service.search.call_args
            assert call_args[0][0].config_metadata["top_k"] == expected_top_k


# ============================================================================
# UNIT TESTS - SCRIPT GENERATION
# ============================================================================

class TestScriptGenerationUnit:
    """Unit tests for podcast script generation"""

    @pytest.mark.asyncio
    async def test_generate_script_success(self, service, valid_podcast_input):
        """Test successful script generation"""
        with patch("rag_solution.services.prompt_template_service.PromptTemplateService") as mock_template_service_class:
            mock_template_service_class.return_value.get_by_type.return_value = None

            with patch("rag_solution.services.podcast_service.LLMProviderFactory") as mock_factory:
                mock_provider = Mock()
                mock_provider.generate_text = Mock(return_value="HOST: Hello\nEXPERT: Hi there")
                mock_factory.return_value.get_provider.return_value = mock_provider

                result = await service._generate_script(valid_podcast_input, "RAG content here")

                assert isinstance(result, str)
                assert len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_script_missing_user_id(self, service, valid_podcast_input):
        """Test script generation fails without user_id"""
        valid_podcast_input.user_id = None

        # Could be either ValidationError type
        with pytest.raises((ValidationError, Exception)) as exc_info:
            await service._generate_script(valid_podcast_input, "RAG content")

        error_str = str(exc_info.value)
        assert "user_id" in error_str.lower() or "required" in error_str.lower()

    @pytest.mark.asyncio
    async def test_generate_script_word_count_calculation(self, service, valid_podcast_input):
        """Test word count calculation for different durations"""
        with patch("rag_solution.services.prompt_template_service.PromptTemplateService") as mock_template_service_class:
            mock_template_service_class.return_value.get_by_type.return_value = None

            with patch("rag_solution.services.podcast_service.LLMProviderFactory") as mock_factory:
                mock_provider = Mock()
                mock_provider.generate_text = Mock(return_value="Script text")
                mock_factory.return_value.get_provider.return_value = mock_provider

                duration_to_words = {
                    PodcastDuration.SHORT: 5 * 150,
                    PodcastDuration.MEDIUM: 15 * 150,
                    PodcastDuration.LONG: 30 * 150,
                    PodcastDuration.EXTENDED: 60 * 150,
                }

                for duration, expected_words in duration_to_words.items():
                    valid_podcast_input.duration = duration
                    await service._generate_script(valid_podcast_input, "RAG content")

                    # Verify word count was passed to template
                    call_args = mock_provider.generate_text.call_args
                    variables = call_args.kwargs.get("variables", {})
                    assert variables.get("word_count") == expected_words

    @pytest.mark.asyncio
    async def test_generate_script_different_languages(self, service, valid_podcast_input):
        """Test script generation for different languages"""
        with patch("rag_solution.services.prompt_template_service.PromptTemplateService") as mock_template_service_class:
            mock_template_service_class.return_value.get_by_type.return_value = None

            with patch("rag_solution.services.podcast_service.LLMProviderFactory") as mock_factory:
                mock_provider = Mock()
                mock_provider.generate_text = Mock(return_value="Script text")
                mock_factory.return_value.get_provider.return_value = mock_provider

                for lang in ["en", "es", "fr", "de", "ja"]:
                    valid_podcast_input.language = lang
                    await service._generate_script(valid_podcast_input, "RAG content")

                    call_args = mock_provider.generate_text.call_args
                    variables = call_args.kwargs.get("variables", {})
                    assert variables.get("language") == lang

    @pytest.mark.asyncio
    async def test_generate_script_list_response(self, service, valid_podcast_input):
        """Test script generation handles list responses from LLM"""
        with patch("rag_solution.services.prompt_template_service.PromptTemplateService") as mock_template_service_class:
            mock_template_service_class.return_value.get_by_type.return_value = None

            with patch("rag_solution.services.podcast_service.LLMProviderFactory") as mock_factory:
                mock_provider = Mock()
                mock_provider.generate_text = Mock(return_value=["Part 1", "Part 2"])
                mock_factory.return_value.get_provider.return_value = mock_provider

                result = await service._generate_script(valid_podcast_input, "RAG content")

                assert isinstance(result, str)
                assert "Part 1" in result
                assert "Part 2" in result

    @pytest.mark.asyncio
    async def test_generate_script_with_template_fallback(self, service, valid_podcast_input):
        """Test script generation falls back to default template when user template not found"""
        with patch("rag_solution.services.prompt_template_service.PromptTemplateService") as mock_template_service_class:
            mock_template_service_class.return_value.get_by_type.return_value = None

            with patch("rag_solution.services.podcast_service.LLMProviderFactory") as mock_factory:
                mock_provider = Mock()
                mock_provider.generate_text = Mock(return_value="Script text")
                mock_factory.return_value.get_provider.return_value = mock_provider

                result = await service._generate_script(valid_podcast_input, "RAG content")
                assert isinstance(result, str)


# ============================================================================
# UNIT TESTS - AUDIO GENERATION
# ============================================================================

# Audio generation tests removed - these require real audio processing
# and should be moved to integration tests if needed

# ============================================================================
# UNIT TESTS - FILE MANAGEMENT
# ============================================================================

class TestFileManagementUnit:
    """Unit tests for audio file storage operations"""

    @pytest.mark.asyncio
    async def test_store_audio_success(self, service, mock_audio_storage):
        """Test successful audio file storage"""
        podcast_id = uuid4()
        user_id = uuid4()
        audio_bytes = b"audio_data"

        result = await service._store_audio(podcast_id, user_id, audio_bytes, AudioFormat.MP3)

        assert result == "/api/podcasts/123/audio"
        mock_audio_storage.store_audio.assert_called_once_with(
            podcast_id=podcast_id,
            user_id=user_id,
            audio_data=audio_bytes,
            audio_format="mp3"
        )

    @pytest.mark.asyncio
    async def test_store_audio_different_formats(self, service, mock_audio_storage):
        """Test storing audio in different formats"""
        podcast_id = uuid4()
        user_id = uuid4()

        for audio_format in [AudioFormat.MP3, AudioFormat.WAV, AudioFormat.OGG, AudioFormat.FLAC]:
            await service._store_audio(podcast_id, user_id, b"audio", audio_format)

            call_args = mock_audio_storage.store_audio.call_args
            assert call_args.kwargs["audio_format"] == audio_format.value

    @pytest.mark.asyncio
    async def test_store_audio_large_file(self, service, mock_audio_storage):
        """Test storing large audio file"""
        podcast_id = uuid4()
        user_id = uuid4()
        large_audio = b"x" * (10 * 1024 * 1024)  # 10 MB

        result = await service._store_audio(podcast_id, user_id, large_audio, AudioFormat.MP3)

        assert result is not None
        assert len(mock_audio_storage.store_audio.call_args.kwargs["audio_data"]) == 10 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_delete_podcast_success(self, service, mock_repository, mock_audio_storage):
        """Test successful podcast deletion"""
        podcast_id = uuid4()
        user_id = uuid4()

        podcast = Mock()
        podcast.user_id = user_id
        podcast.audio_url = "/api/podcasts/123/audio"
        mock_repository.get_by_id.return_value = podcast

        result = await service.delete_podcast(podcast_id, user_id)

        assert result is True
        assert mock_audio_storage.delete_audio.called
        assert mock_repository.delete.called

    @pytest.mark.asyncio
    async def test_delete_podcast_not_found(self, service, mock_repository):
        """Test deleting non-existent podcast"""
        podcast_id = uuid4()
        user_id = uuid4()

        mock_repository.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await service.delete_podcast(podcast_id, user_id)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_podcast_access_denied(self, service, mock_repository):
        """Test deleting podcast with wrong user_id"""
        podcast_id = uuid4()
        user_id = uuid4()
        other_user_id = uuid4()

        podcast = Mock()
        podcast.user_id = other_user_id
        mock_repository.get_by_id.return_value = podcast

        with pytest.raises(HTTPException) as exc_info:
            await service.delete_podcast(podcast_id, user_id)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_podcast_cleanup_on_storage_error(self, service, mock_repository, mock_audio_storage):
        """Test podcast deletion continues even if audio cleanup fails"""
        podcast_id = uuid4()
        user_id = uuid4()

        podcast = Mock()
        podcast.user_id = user_id
        podcast.audio_url = "/api/podcasts/123/audio"
        mock_repository.get_by_id.return_value = podcast
        mock_audio_storage.delete_audio.side_effect = Exception("Storage error")

        result = await service.delete_podcast(podcast_id, user_id)

        assert result is True
        assert mock_repository.delete.called


# ============================================================================
# UNIT TESTS - PROGRESS TRACKING
# ============================================================================

class TestProgressTrackingUnit:
    """Unit tests for progress tracking"""

    @pytest.mark.asyncio
    async def test_update_progress_success(self, service, mock_repository):
        """Test successful progress update"""
        podcast_id = uuid4()

        await service._update_progress(
            podcast_id=podcast_id,
            progress=50,
            step="generating_script"
        )

        mock_repository.update_progress.assert_called_once_with(
            podcast_id=podcast_id,
            progress_percentage=50,
            current_step="generating_script",
            step_details=None
        )

    @pytest.mark.asyncio
    async def test_update_progress_with_details(self, service, mock_repository):
        """Test progress update with step details"""
        podcast_id = uuid4()
        step_details = {"total_turns": 10, "completed_turns": 5}

        await service._update_progress(
            podcast_id=podcast_id,
            progress=75,
            step="generating_audio",
            step_details=step_details
        )

        call_args = mock_repository.update_progress.call_args
        assert call_args.kwargs["step_details"] == step_details

    @pytest.mark.asyncio
    async def test_update_progress_with_status_change(self, service, mock_repository):
        """Test progress update with status change"""
        podcast_id = uuid4()

        await service._update_progress(
            podcast_id=podcast_id,
            progress=100,
            step="completed",
            status=PodcastStatus.COMPLETED
        )

        assert mock_repository.update_progress.called
        mock_repository.update_status.assert_called_once_with(
            podcast_id=podcast_id,
            status=PodcastStatus.COMPLETED
        )


# ============================================================================
# UNIT TESTS - PODCAST RETRIEVAL
# ============================================================================

class TestPodcastRetrievalUnit:
    """Unit tests for podcast retrieval operations"""

    @pytest.mark.asyncio
    async def test_get_podcast_success(self, service, mock_repository):
        """Test successful podcast retrieval"""
        podcast_id = uuid4()
        user_id = uuid4()
        collection_id = uuid4()

        podcast = Mock()
        podcast.podcast_id = podcast_id
        podcast.user_id = user_id
        podcast.collection_id = collection_id
        podcast.status = PodcastStatus.COMPLETED
        podcast.duration = PodcastDuration.MEDIUM
        podcast.audio_format = AudioFormat.MP3
        podcast.title = "Test"
        podcast.progress_percentage = 100
        podcast.host_voice = "alloy"
        podcast.expert_voice = "onyx"
        podcast.created_at = datetime.utcnow()
        podcast.updated_at = datetime.utcnow()
        podcast.completed_at = datetime.utcnow()
        mock_repository.get_by_id.return_value = podcast

        result = await service.get_podcast(podcast_id, user_id)

        assert mock_repository.to_schema.called
        assert isinstance(result, PodcastGenerationOutput)

    @pytest.mark.asyncio
    async def test_get_podcast_not_found(self, service, mock_repository):
        """Test retrieving non-existent podcast"""
        podcast_id = uuid4()
        user_id = uuid4()

        mock_repository.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await service.get_podcast(podcast_id, user_id)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_podcast_access_denied(self, service, mock_repository):
        """Test retrieving podcast with wrong user_id"""
        podcast_id = uuid4()
        user_id = uuid4()
        other_user_id = uuid4()

        podcast = Mock()
        podcast.user_id = other_user_id
        mock_repository.get_by_id.return_value = podcast

        with pytest.raises(HTTPException) as exc_info:
            await service.get_podcast(podcast_id, user_id)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_list_user_podcasts_success(self, service, mock_repository):
        """Test listing user podcasts"""
        user_id = uuid4()

        def create_mock_podcast():
            p = Mock()
            p.podcast_id = uuid4()
            p.user_id = user_id
            p.collection_id = uuid4()
            p.status = PodcastStatus.COMPLETED
            p.duration = PodcastDuration.MEDIUM
            p.audio_format = AudioFormat.MP3
            p.title = "Test"
            p.progress_percentage = 100
            p.host_voice = "alloy"
            p.expert_voice = "onyx"
            p.created_at = datetime.utcnow()
            p.updated_at = datetime.utcnow()
            p.completed_at = datetime.utcnow()
            return p

        podcasts = [create_mock_podcast(), create_mock_podcast(), create_mock_podcast()]
        mock_repository.get_by_user.return_value = podcasts

        result = await service.list_user_podcasts(user_id, limit=10, offset=0)

        assert isinstance(result, PodcastListResponse)
        assert result.total_count == 3

    @pytest.mark.asyncio
    async def test_list_user_podcasts_empty(self, service, mock_repository):
        """Test listing podcasts for user with no podcasts"""
        user_id = uuid4()

        mock_repository.get_by_user.return_value = []

        result = await service.list_user_podcasts(user_id)

        assert result.total_count == 0
        assert len(result.podcasts) == 0

    @pytest.mark.asyncio
    async def test_list_user_podcasts_pagination(self, service, mock_repository):
        """Test podcast list pagination"""
        user_id = uuid4()

        await service.list_user_podcasts(user_id, limit=50, offset=10)

        mock_repository.get_by_user.assert_called_once_with(
            user_id=user_id,
            limit=50,
            offset=10
        )


# ============================================================================
# UNIT TESTS - VOICE PREVIEW
# ============================================================================

class TestVoicePreviewUnit:
    """Unit tests for voice preview generation"""

    @pytest.mark.asyncio
    async def test_generate_voice_preview_success(self, service):
        """Test successful voice preview generation"""
        with patch("rag_solution.services.podcast_service.AudioProviderFactory") as mock_factory:
            mock_audio_provider = AsyncMock()
            mock_audio_provider.generate_single_turn_audio = AsyncMock(return_value=b"preview_audio")
            mock_factory.create_provider.return_value = mock_audio_provider

            result = await service.generate_voice_preview("nova")

            assert result == b"preview_audio"
            assert mock_audio_provider.generate_single_turn_audio.called

    @pytest.mark.asyncio
    async def test_generate_voice_preview_different_voices(self, service):
        """Test voice preview for different voice IDs"""
        with patch("rag_solution.services.podcast_service.AudioProviderFactory") as mock_factory:
            mock_audio_provider = AsyncMock()
            mock_audio_provider.generate_single_turn_audio = AsyncMock(return_value=b"audio")
            mock_factory.create_provider.return_value = mock_audio_provider

            for voice_id in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]:
                await service.generate_voice_preview(voice_id)

                call_args = mock_audio_provider.generate_single_turn_audio.call_args
                assert call_args.kwargs["voice_id"] == voice_id

    @pytest.mark.asyncio
    async def test_generate_voice_preview_provider_error(self, service):
        """Test voice preview handles provider errors"""
        with patch("rag_solution.services.podcast_service.AudioProviderFactory") as mock_factory:
            mock_audio_provider = AsyncMock()
            mock_audio_provider.generate_single_turn_audio = AsyncMock(
                side_effect=Exception("TTS provider unavailable")
            )
            mock_factory.create_provider.return_value = mock_audio_provider

            with pytest.raises(HTTPException) as exc_info:
                await service.generate_voice_preview("nova")

            assert exc_info.value.status_code == 500


# ============================================================================
# UNIT TESTS - SCRIPT-ONLY GENERATION
# ============================================================================

class TestScriptOnlyGenerationUnit:
    """Unit tests for script-only generation (no audio)"""

    @pytest.mark.asyncio
    async def test_generate_script_only_success(self, service, mock_collection_service):
        """Test successful script-only generation"""
        script_input = PodcastScriptGenerationInput(
            collection_id=uuid4(),
            user_id=uuid4(),
            duration=PodcastDuration.MEDIUM,
            title="Test Script",
            description="Test description"
        )

        with patch.object(service, "_retrieve_content", new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = "RAG content"

            with patch.object(service, "_generate_script", new_callable=AsyncMock) as mock_gen_script:
                mock_gen_script.return_value = "HOST: Hello\nEXPERT: Hi there"

                result = await service.generate_script_only(script_input)

                assert isinstance(result, PodcastScriptOutput)
                assert result.script_text == "HOST: Hello\nEXPERT: Hi there"
                assert result.has_proper_format is True

    @pytest.mark.asyncio
    async def test_generate_script_only_collection_not_found(self, service, mock_collection_service):
        """Test script-only generation with non-existent collection"""
        script_input = PodcastScriptGenerationInput(
            collection_id=uuid4(),
            user_id=uuid4(),
            duration=PodcastDuration.MEDIUM
        )

        mock_collection_service.get_collection.side_effect = NotFoundError(
            resource_type="Collection",
            resource_id=str(script_input.collection_id),
            message="Collection not found"
        )

        with pytest.raises(NotFoundError):
            await service.generate_script_only(script_input)

    @pytest.mark.asyncio
    async def test_generate_script_only_word_count_accuracy(self, service, mock_collection_service):
        """Test script-only generation calculates word count correctly"""
        script_input = PodcastScriptGenerationInput(
            collection_id=uuid4(),
            user_id=uuid4(),
            duration=PodcastDuration.MEDIUM
        )

        script_text = "HOST: " + " ".join(["word"] * 100) + "\nEXPERT: " + " ".join(["word"] * 100)

        with patch.object(service, "_retrieve_content", new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = "RAG content"

            with patch.object(service, "_generate_script", new_callable=AsyncMock) as mock_gen_script:
                mock_gen_script.return_value = script_text

                result = await service.generate_script_only(script_input)

                assert result.word_count > 0
                assert result.estimated_duration_minutes > 0

    @pytest.mark.asyncio
    async def test_generate_script_only_improper_format_detection(self, service, mock_collection_service):
        """Test script-only generation detects improper format"""
        script_input = PodcastScriptGenerationInput(
            collection_id=uuid4(),
            user_id=uuid4(),
            duration=PodcastDuration.MEDIUM
        )

        with patch.object(service, "_retrieve_content", new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = "RAG content"

            with patch.object(service, "_generate_script", new_callable=AsyncMock) as mock_gen_script:
                mock_gen_script.return_value = "Just plain text without speaker labels"

                result = await service.generate_script_only(script_input)

                assert result.has_proper_format is False


# ============================================================================
# UNIT TESTS - SCRIPT-TO-AUDIO
# ============================================================================

class TestScriptToAudioUnit:
    """Unit tests for converting existing script to audio"""

    @pytest.mark.asyncio
    async def test_generate_audio_from_script_success(self, service, mock_collection_service, mock_repository):
        """Test successful audio generation from existing script"""
        long_script = "HOST: " + " ".join(["Hello"] * 50) + "\nEXPERT: " + " ".join(["Hi there"] * 50)

        audio_input = PodcastAudioGenerationInput(
            user_id=uuid4(),
            collection_id=uuid4(),
            script_text=long_script,
            title="Test Audio",
            duration=PodcastDuration.MEDIUM,
            host_voice="alloy",
            expert_voice="onyx",
            format=AudioFormat.MP3
        )
        background_tasks = BackgroundTasks()

        result = await service.generate_audio_from_script(audio_input, background_tasks)

        assert mock_repository.create.called

    @pytest.mark.asyncio
    async def test_generate_audio_from_script_missing_user_id(self, service):
        """Test audio generation from script fails without user_id"""
        long_script = "HOST: " + " ".join(["Hello"] * 50) + "\nEXPERT: " + " ".join(["Hi"] * 50)

        audio_input = PodcastAudioGenerationInput(
            user_id=None,
            collection_id=uuid4(),
            script_text=long_script,
            title="Test",
            duration=PodcastDuration.MEDIUM
        )
        background_tasks = BackgroundTasks()

        with pytest.raises(ValidationError):
            await service.generate_audio_from_script(audio_input, background_tasks)

    @pytest.mark.asyncio
    async def test_generate_audio_from_script_collection_not_found(self, service, mock_collection_service):
        """Test audio generation fails for non-existent collection"""
        long_script = "HOST: " + " ".join(["Hello"] * 50) + "\nEXPERT: " + " ".join(["Hi"] * 50)

        audio_input = PodcastAudioGenerationInput(
            user_id=uuid4(),
            collection_id=uuid4(),
            script_text=long_script,
            title="Test",
            duration=PodcastDuration.MEDIUM
        )
        background_tasks = BackgroundTasks()

        mock_collection_service.get_collection.side_effect = NotFoundError(
            resource_type="Collection",
            resource_id=str(audio_input.collection_id),
            message="Collection not found"
        )

        with pytest.raises(NotFoundError):
            await service.generate_audio_from_script(audio_input, background_tasks)


# ============================================================================
# UNIT TESTS - ERROR HANDLING & CLEANUP
# ============================================================================

class TestErrorHandlingUnit:
    """Unit tests for error handling and cleanup"""

    @pytest.mark.asyncio
    async def test_cleanup_failed_podcast_success(self, service, mock_repository, mock_audio_storage):
        """Test cleanup of failed podcast generation"""
        podcast_id = uuid4()
        user_id = uuid4()

        await service._cleanup_failed_podcast(
            podcast_id=podcast_id,
            user_id=user_id,
            audio_stored=True,
            error_message="Generation failed"
        )

        assert mock_audio_storage.delete_audio.called
        mock_repository.update_status.assert_called_once_with(
            podcast_id=podcast_id,
            status=PodcastStatus.FAILED,
            error_message="Generation failed"
        )

    @pytest.mark.asyncio
    async def test_cleanup_failed_podcast_no_audio(self, service, mock_repository, mock_audio_storage):
        """Test cleanup when audio was not stored"""
        podcast_id = uuid4()
        user_id = uuid4()

        await service._cleanup_failed_podcast(
            podcast_id=podcast_id,
            user_id=user_id,
            audio_stored=False,
            error_message="Failed early"
        )

        assert not mock_audio_storage.delete_audio.called
        assert mock_repository.update_status.called

    @pytest.mark.asyncio
    async def test_cleanup_failed_podcast_storage_cleanup_error(self, service, mock_repository, mock_audio_storage):
        """Test cleanup handles storage cleanup errors gracefully"""
        podcast_id = uuid4()
        user_id = uuid4()

        mock_audio_storage.delete_audio.side_effect = Exception("Storage error")

        await service._cleanup_failed_podcast(
            podcast_id=podcast_id,
            user_id=user_id,
            audio_stored=True,
            error_message="Generation failed"
        )

        assert mock_repository.update_status.called


# ============================================================================
# UNIT TESTS - EDGE CASES
# ============================================================================

class TestEdgeCasesUnit:
    """Unit tests for edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_very_long_document_processing(self, service, valid_podcast_input, mock_search_service):
        """Test processing very long documents (100+ pages)"""
        # Simulate 100+ page documents
        long_results = [Mock(chunk=Mock(text="x" * 5000)) for _ in range(100)]
        mock_search_service.search.return_value = Mock(
            query_results=long_results,
            metadata={}
        )

        result = await service._retrieve_content(valid_podcast_input)

        assert len(result) > 100_000  # Should have lots of content

    @pytest.mark.asyncio
    async def test_empty_document_handling(self, service, valid_podcast_input, mock_search_service):
        """Test handling of empty documents"""
        mock_search_service.search.return_value = Mock(
            query_results=[Mock(chunk=Mock(text=""))],
            metadata={}
        )

        with pytest.raises(ValidationError) as exc_info:
            await service._retrieve_content(valid_podcast_input)

        assert "Insufficient content" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_special_characters_in_text(self, service, valid_podcast_input):
        """Test handling of special characters in podcast text"""
        script_with_special_chars = "HOST: Hello! How are you? 你好\nEXPERT: I'm good 😊"

        with patch("rag_solution.services.prompt_template_service.PromptTemplateService") as mock_template_service_class:
            mock_template_service_class.return_value.get_by_type.return_value = None

            with patch("rag_solution.services.podcast_service.LLMProviderFactory") as mock_factory:
                mock_provider = Mock()
                mock_provider.generate_text = Mock(return_value=script_with_special_chars)
                mock_factory.return_value.get_provider.return_value = mock_provider

                result = await service._generate_script(valid_podcast_input, "RAG content")

                assert "你好" in result
                assert "😊" in result

    def test_supported_language_enum(self):
        """Test SupportedLanguage enum properties"""
        assert SupportedLanguage.ENGLISH.value == "en"
        assert SupportedLanguage.ENGLISH.display_name == "English"
        assert SupportedLanguage.SPANISH.value == "es"
        assert SupportedLanguage.SPANISH.display_name == "Spanish"
        assert SupportedLanguage.JAPANESE.value == "ja"
        assert SupportedLanguage.JAPANESE.display_name == "Japanese"

    def test_language_names_dict_backward_compatibility(self):
        """Test backward compatibility of LANGUAGE_NAMES dict"""
        assert PodcastService.LANGUAGE_NAMES["en"] == "English"
        assert PodcastService.LANGUAGE_NAMES["es"] == "Spanish"
        assert PodcastService.LANGUAGE_NAMES["ja"] == "Japanese"

    @pytest.mark.asyncio
    async def test_maximum_concurrent_podcasts_boundary(self, service, valid_podcast_input, mock_repository, mock_settings):
        """Test boundary condition for maximum concurrent podcasts"""
        background_tasks = BackgroundTasks()

        # Test at limit
        mock_repository.count_active_for_user.return_value = 4
        mock_settings.podcast_max_concurrent_per_user = 5
        result = await service.generate_podcast(valid_podcast_input, background_tasks)
        assert result is not None

        # Test over limit
        mock_repository.count_active_for_user.return_value = 5
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_podcast(valid_podcast_input, background_tasks)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_minimum_document_count_boundary(self, service, valid_podcast_input, mock_collection_service, mock_settings):
        """Test boundary condition for minimum document count"""
        background_tasks = BackgroundTasks()

        # Test at minimum
        collection = Mock()
        collection.files = [Mock()]
        mock_collection_service.get_collection.return_value = collection
        mock_settings.podcast_min_documents = 1
        result = await service.generate_podcast(valid_podcast_input, background_tasks)
        assert result is not None

        # Test below minimum
        collection.files = []
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_podcast(valid_podcast_input, background_tasks)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_audio_storage_backend_not_implemented(self, service, mock_settings):
        """Test error when unsupported storage backend is configured"""
        mock_settings.podcast_storage_backend = "s3"  # Not yet implemented

        with pytest.raises(NotImplementedError):
            service._create_audio_storage()
