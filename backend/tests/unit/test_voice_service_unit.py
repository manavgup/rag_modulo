"""Unit tests for voice management service.

Unit tests focus on VoiceService business logic, validation, and interactions
with dependencies (mocked). These tests validate VoiceService behavior
without external dependencies.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.models.voice import Voice
from rag_solution.schemas.voice_schema import (
    VoiceGender,
    VoiceListResponse,
    VoiceOutput,
    VoiceProcessingInput,
    VoiceStatus,
    VoiceUpdateInput,
    VoiceUploadInput,
)
from rag_solution.services.voice_service import VoiceService


@pytest.mark.unit
class TestVoiceServiceInitialization:
    """Unit tests for VoiceService initialization."""

    def test_service_initialization_with_dependencies(self) -> None:
        """Unit: VoiceService initializes with required dependencies."""
        session = Mock(spec=Session)
        settings = Mock(spec=Settings)

        service = VoiceService(session=session, settings=settings)

        assert service.session == session
        assert service.settings == settings
        assert service.repository is not None
        assert service.file_service is not None


@pytest.mark.unit
class TestVoiceServiceUpload:
    """Unit tests for voice upload functionality."""

    @pytest.fixture
    def mock_service(self) -> VoiceService:
        """Fixture: Create mock VoiceService."""
        session = Mock(spec=Session)
        settings = Mock(spec=Settings)

        service = VoiceService(session=session, settings=settings)

        # Mock repository
        service.repository = Mock()
        service.repository.create = Mock()
        service.repository.update_status = Mock()
        service.repository.count_voices_for_user = Mock(return_value=0)
        service.repository.to_schema = Mock()

        # Mock file service
        service.file_service = Mock()
        service.file_service.save_voice_file = Mock(return_value="/path/to/voice/sample.mp3")

        return service

    @pytest.mark.asyncio
    async def test_upload_voice_success(self, mock_service: VoiceService) -> None:
        """Unit: upload_voice successfully uploads voice sample."""
        user_id = uuid4()
        voice_id = uuid4()

        voice_input = VoiceUploadInput(
            user_id=user_id,
            name="Test Voice",
            description="Test description",
            gender=VoiceGender.FEMALE,
        )

        # Mock audio file
        audio_file = Mock(spec=UploadFile)
        audio_file.filename = "sample.mp3"
        audio_file.content_type = "audio/mpeg"
        audio_file.read = AsyncMock(return_value=b"fake_audio_data")

        # Mock voice creation
        mock_voice = Mock(spec=Voice)
        mock_voice.voice_id = voice_id
        mock_voice.user_id = user_id
        mock_voice.name = "Test Voice"
        mock_voice.status = VoiceStatus.UPLOADING
        mock_voice.sample_file_url = f"/api/voices/{voice_id}/sample"

        mock_service.repository.create.return_value = mock_voice
        mock_service.repository.update_status.return_value = mock_voice
        mock_service.repository.to_schema.return_value = VoiceOutput(
            voice_id=voice_id,
            user_id=user_id,
            name="Test Voice",
            status=VoiceStatus.UPLOADING,
            gender=VoiceGender.FEMALE,
            sample_file_url=f"/api/voices/{voice_id}/sample",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Mock session for commit/refresh
        mock_service.session.commit = Mock()
        mock_service.session.refresh = Mock()

        result = await mock_service.upload_voice(voice_input, audio_file)

        assert result.voice_id == voice_id
        assert result.status == VoiceStatus.UPLOADING
        mock_service.repository.create.assert_called_once()
        mock_service.file_service.save_voice_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_voice_validates_user_id(self, mock_service: VoiceService) -> None:
        """Unit: upload_voice raises HTTPException if user_id missing."""
        voice_input = VoiceUploadInput(
            user_id=None,  # Missing user_id
            name="Test Voice",
            gender=VoiceGender.NEUTRAL,
        )

        audio_file = Mock(spec=UploadFile)
        audio_file.filename = "sample.mp3"

        with pytest.raises(HTTPException) as exc_info:
            await mock_service.upload_voice(voice_input, audio_file)

        assert exc_info.value.status_code == 400
        assert "user_id is required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_voice_validates_format(self, mock_service: VoiceService) -> None:
        """Unit: upload_voice rejects unsupported audio formats."""
        voice_input = VoiceUploadInput(
            user_id=uuid4(),
            name="Test Voice",
            gender=VoiceGender.NEUTRAL,
        )

        # Unsupported format
        audio_file = Mock(spec=UploadFile)
        audio_file.filename = "sample.aac"  # Unsupported
        audio_file.content_type = "audio/aac"
        audio_file.read = AsyncMock(return_value=b"fake_audio_data")

        with pytest.raises(HTTPException) as exc_info:
            await mock_service.upload_voice(voice_input, audio_file)

        assert exc_info.value.status_code == 400
        assert "Invalid file extension" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_voice_validates_file_size(self, mock_service: VoiceService) -> None:
        """Unit: upload_voice rejects files exceeding size limit."""
        voice_input = VoiceUploadInput(
            user_id=uuid4(),
            name="Test Voice",
            gender=VoiceGender.NEUTRAL,
        )

        # File too large (>10MB)
        large_data = b"x" * (11 * 1024 * 1024)  # 11MB
        audio_file = Mock(spec=UploadFile)
        audio_file.filename = "sample.mp3"
        audio_file.content_type = "audio/mpeg"
        audio_file.read = AsyncMock(return_value=large_data)

        with pytest.raises(HTTPException) as exc_info:
            await mock_service.upload_voice(voice_input, audio_file)

        assert exc_info.value.status_code == 400
        assert "exceeds maximum" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_voice_enforces_user_limit(self, mock_service: VoiceService) -> None:
        """Unit: upload_voice enforces maximum voices per user."""
        user_id = uuid4()

        voice_input = VoiceUploadInput(
            user_id=user_id,
            name="Test Voice",
            gender=VoiceGender.NEUTRAL,
        )

        audio_file = Mock(spec=UploadFile)
        audio_file.filename = "sample.mp3"
        audio_file.content_type = "audio/mpeg"
        audio_file.read = AsyncMock(return_value=b"fake_audio_data")

        # Mock user has reached limit
        mock_service.repository.count_voices_for_user.return_value = 10
        mock_service.settings.voice_max_per_user = 10

        with pytest.raises(HTTPException) as exc_info:
            await mock_service.upload_voice(voice_input, audio_file)

        assert exc_info.value.status_code == 400
        assert "maximum" in str(exc_info.value.detail).lower()


@pytest.mark.unit
class TestVoiceServiceProcessing:
    """Unit tests for voice processing functionality."""

    @pytest.fixture
    def mock_service(self) -> VoiceService:
        """Fixture: Create mock VoiceService."""
        session = Mock(spec=Session)
        settings = Mock(spec=Settings)
        settings.voice_tts_providers = "elevenlabs,f5-tts"

        service = VoiceService(session=session, settings=settings)

        # Mock repository
        service.repository = Mock()
        service.repository.get_by_id = Mock()
        service.repository.update_status = Mock()

        return service

    @pytest.mark.asyncio
    async def test_process_voice_validates_ownership(self, mock_service: VoiceService) -> None:
        """Unit: process_voice validates user owns the voice."""
        voice_id = uuid4()
        user_id = uuid4()
        other_user_id = uuid4()

        processing_input = VoiceProcessingInput(provider_name="elevenlabs", voice_id=str(voice_id))

        # Mock voice owned by different user
        mock_voice = Mock(spec=Voice)
        mock_voice.voice_id = voice_id
        mock_voice.user_id = other_user_id
        mock_voice.status = VoiceStatus.UPLOADING

        mock_service.repository.get_by_id.return_value = mock_voice

        with pytest.raises(HTTPException) as exc_info:
            await mock_service.process_voice(voice_id, processing_input, user_id)

        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_process_voice_rejects_invalid_provider(self) -> None:
        """Unit: Schema validation rejects unsupported providers."""
        from pydantic import ValidationError

        # Pydantic schema validation should reject invalid provider before service is called
        with pytest.raises(ValidationError) as exc_info:
            VoiceProcessingInput(provider_name="invalid_provider")

        # Verify validation error contains provider name
        assert "provider_name" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_process_voice_rejects_already_ready(self, mock_service: VoiceService) -> None:
        """Unit: process_voice rejects voices that are already ready."""
        voice_id = uuid4()
        user_id = uuid4()

        processing_input = VoiceProcessingInput(provider_name="elevenlabs", voice_id=str(voice_id))

        mock_voice = Mock(spec=Voice)
        mock_voice.voice_id = voice_id
        mock_voice.user_id = user_id
        mock_voice.status = VoiceStatus.READY  # Already processed

        mock_service.repository.get_by_id.return_value = mock_voice

        with pytest.raises(HTTPException) as exc_info:
            await mock_service.process_voice(voice_id, processing_input, user_id)

        assert exc_info.value.status_code == 409
        assert "already processed" in str(exc_info.value.detail)


@pytest.mark.unit
class TestVoiceServiceRetrieval:
    """Unit tests for voice retrieval functionality."""

    @pytest.fixture
    def mock_service(self) -> VoiceService:
        """Fixture: Create mock VoiceService."""
        session = Mock(spec=Session)
        settings = Mock(spec=Settings)

        service = VoiceService(session=session, settings=settings)

        # Mock repository
        service.repository = Mock()
        service.repository.get_by_id = Mock()
        service.repository.get_by_user = Mock()
        service.repository.count_voices_for_user = Mock()
        service.repository.to_schema = Mock()

        return service

    @pytest.mark.asyncio
    async def test_list_user_voices_returns_list(self, mock_service: VoiceService) -> None:
        """Unit: list_user_voices returns list of user's voices."""
        user_id = uuid4()

        mock_voices = [Mock(spec=Voice) for _ in range(3)]
        mock_service.repository.get_by_user.return_value = mock_voices
        mock_service.repository.count_voices_for_user.return_value = 3
        mock_service.repository.to_schema.side_effect = [
            VoiceOutput(
                voice_id=uuid4(),
                user_id=user_id,
                name=f"Voice {i}",
                status=VoiceStatus.READY,
                gender=VoiceGender.NEUTRAL,
                sample_file_url=f"/api/voices/{i}/sample",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            for i in range(3)
        ]

        result = await mock_service.list_user_voices(user_id, limit=100, offset=0)

        assert isinstance(result, VoiceListResponse)
        assert len(result.voices) == 3
        assert result.total_count == 3
        mock_service.repository.get_by_user.assert_called_once_with(user_id=user_id, limit=100, offset=0)

    @pytest.mark.asyncio
    async def test_list_user_voices_validates_pagination(self, mock_service: VoiceService) -> None:
        """Unit: list_user_voices validates pagination parameters."""
        user_id = uuid4()

        # Invalid limit (too high)
        with pytest.raises(HTTPException) as exc_info:
            await mock_service.list_user_voices(user_id, limit=200, offset=0)

        assert exc_info.value.status_code == 400
        assert "limit must be between 1 and 100" in str(exc_info.value.detail)

        # Invalid offset (negative)
        with pytest.raises(HTTPException) as exc_info:
            await mock_service.list_user_voices(user_id, limit=10, offset=-1)

        assert exc_info.value.status_code == 400
        assert "offset must be >= 0" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_voice_validates_ownership(self, mock_service: VoiceService) -> None:
        """Unit: get_voice validates user owns the voice."""
        voice_id = uuid4()
        user_id = uuid4()
        other_user_id = uuid4()

        mock_voice = Mock(spec=Voice)
        mock_voice.voice_id = voice_id
        mock_voice.user_id = other_user_id

        mock_service.repository.get_by_id.return_value = mock_voice

        with pytest.raises(HTTPException) as exc_info:
            await mock_service.get_voice(voice_id, user_id)

        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value.detail)


@pytest.mark.unit
class TestVoiceServiceUpdate:
    """Unit tests for voice update functionality."""

    @pytest.fixture
    def mock_service(self) -> VoiceService:
        """Fixture: Create mock VoiceService."""
        session = Mock(spec=Session)
        settings = Mock(spec=Settings)

        service = VoiceService(session=session, settings=settings)

        # Mock repository
        service.repository = Mock()
        service.repository.get_by_id = Mock()
        service.repository.update = Mock()
        service.repository.to_schema = Mock()

        return service

    @pytest.mark.asyncio
    async def test_update_voice_success(self, mock_service: VoiceService) -> None:
        """Unit: update_voice successfully updates voice metadata."""
        voice_id = uuid4()
        user_id = uuid4()

        update_input = VoiceUpdateInput(
            name="Updated Voice Name",
            description="Updated description",
            gender=VoiceGender.MALE,
        )

        mock_voice = Mock(spec=Voice)
        mock_voice.voice_id = voice_id
        mock_voice.user_id = user_id

        mock_updated_voice = Mock(spec=Voice)
        mock_updated_voice.voice_id = voice_id
        mock_updated_voice.user_id = user_id
        mock_updated_voice.name = "Updated Voice Name"

        mock_service.repository.get_by_id.return_value = mock_voice
        mock_service.repository.update.return_value = mock_updated_voice
        mock_service.repository.to_schema.return_value = VoiceOutput(
            voice_id=voice_id,
            user_id=user_id,
            name="Updated Voice Name",
            status=VoiceStatus.READY,
            gender=VoiceGender.MALE,
            sample_file_url=f"/api/voices/{voice_id}/sample",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        result = await mock_service.update_voice(voice_id, update_input, user_id)

        assert result.name == "Updated Voice Name"
        mock_service.repository.update.assert_called_once()


@pytest.mark.unit
class TestVoiceServiceDeletion:
    """Unit tests for voice deletion functionality."""

    @pytest.fixture
    def mock_service(self) -> VoiceService:
        """Fixture: Create mock VoiceService."""
        session = Mock(spec=Session)
        settings = Mock(spec=Settings)

        service = VoiceService(session=session, settings=settings)

        # Mock repository
        service.repository = Mock()
        service.repository.get_by_id = Mock()
        service.repository.delete = Mock(return_value=True)

        # Mock file service
        service.file_service = Mock()
        service.file_service.delete_voice_file = Mock(return_value=True)

        return service

    @pytest.mark.asyncio
    async def test_delete_voice_success(self, mock_service: VoiceService) -> None:
        """Unit: delete_voice successfully deletes voice and files."""
        voice_id = uuid4()
        user_id = uuid4()

        mock_voice = Mock(spec=Voice)
        mock_voice.voice_id = voice_id
        mock_voice.user_id = user_id

        mock_service.repository.get_by_id.return_value = mock_voice

        result = await mock_service.delete_voice(voice_id, user_id)

        assert result is True
        mock_service.file_service.delete_voice_file.assert_called_once()
        mock_service.repository.delete.assert_called_once_with(voice_id)

    @pytest.mark.asyncio
    async def test_delete_voice_continues_on_file_error(self, mock_service: VoiceService) -> None:
        """Unit: delete_voice continues even if file deletion fails."""
        voice_id = uuid4()
        user_id = uuid4()

        mock_voice = Mock(spec=Voice)
        mock_voice.voice_id = voice_id
        mock_voice.user_id = user_id

        mock_service.repository.get_by_id.return_value = mock_voice
        # File deletion fails
        mock_service.file_service.delete_voice_file.side_effect = Exception("File not found")

        result = await mock_service.delete_voice(voice_id, user_id)

        # Should still succeed (database deletion happens regardless)
        assert result is True
        mock_service.repository.delete.assert_called_once_with(voice_id)


@pytest.mark.unit
class TestVoiceServiceUsageTracking:
    """Unit tests for voice usage tracking."""

    @pytest.fixture
    def mock_service(self) -> VoiceService:
        """Fixture: Create mock VoiceService."""
        session = Mock(spec=Session)
        settings = Mock(spec=Settings)

        service = VoiceService(session=session, settings=settings)

        # Mock repository
        service.repository = Mock()
        service.repository.increment_usage = Mock()

        return service

    @pytest.mark.asyncio
    async def test_increment_usage_success(self, mock_service: VoiceService) -> None:
        """Unit: increment_usage successfully increments counter."""
        voice_id = uuid4()

        mock_voice = Mock(spec=Voice)
        mock_voice.voice_id = voice_id
        mock_voice.times_used = 5

        mock_service.repository.increment_usage.return_value = mock_voice

        # Should not raise
        await mock_service.increment_usage(voice_id)

        mock_service.repository.increment_usage.assert_called_once_with(voice_id)

    @pytest.mark.asyncio
    async def test_increment_usage_handles_not_found(self, mock_service: VoiceService) -> None:
        """Unit: increment_usage handles voice not found gracefully."""
        voice_id = uuid4()

        mock_service.repository.increment_usage.return_value = None

        # Should not raise (just logs warning)
        await mock_service.increment_usage(voice_id)

        mock_service.repository.increment_usage.assert_called_once_with(voice_id)
