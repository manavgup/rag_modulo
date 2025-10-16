"""Integration tests for voice management feature.

Integration tests verify the complete voice management workflow including:
- Voice upload → database storage → file storage
- Voice processing workflow
- Voice usage in podcast generation
- Access control and validation
"""

from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import UploadFile
from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.repository.voice_repository import VoiceRepository
from rag_solution.schemas.voice_schema import VoiceGender, VoiceStatus, VoiceUpdateInput, VoiceUploadInput
from rag_solution.services.file_management_service import FileManagementService
from rag_solution.services.voice_service import VoiceService


@pytest.mark.integration
class TestVoiceIntegrationWorkflow:
    """Integration tests for complete voice workflow."""

    @pytest.fixture
    def test_session(self, db_session: Session) -> Session:
        """Fixture: Database session for testing."""
        return db_session

    @pytest.fixture
    def test_settings(self) -> Settings:
        """Fixture: Test settings."""
        from core.config import get_settings

        return get_settings()

    @pytest.fixture
    def voice_service(self, test_session: Session, test_settings: Settings) -> VoiceService:
        """Fixture: VoiceService with real dependencies."""
        return VoiceService(session=test_session, settings=test_settings)

    @pytest.fixture
    def file_service(self, test_session: Session, test_settings: Settings) -> FileManagementService:
        """Fixture: FileManagementService for cleanup."""
        return FileManagementService(db=test_session, settings=test_settings)

    @pytest.fixture
    def test_user_id(self) -> uuid4:
        """Fixture: Test user ID."""
        return uuid4()

    @pytest.mark.asyncio
    async def test_complete_voice_upload_workflow(
        self,
        voice_service: VoiceService,
        file_service: FileManagementService,
        test_user_id: uuid4,
    ) -> None:
        """Integration: Complete voice upload workflow from request to storage."""
        # Step 1: Create voice upload request
        voice_input = VoiceUploadInput(
            user_id=test_user_id,
            name="Integration Test Voice",
            description="Test voice for integration testing",
            gender=VoiceGender.FEMALE,
        )

        # Create fake audio file
        audio_content = b"fake_mp3_audio_content_for_testing" * 100  # Make it realistic size
        audio_file_obj = BytesIO(audio_content)
        audio_file = UploadFile(filename="test_voice.mp3", file=audio_file_obj)

        # Step 2: Upload voice
        result = await voice_service.upload_voice(voice_input, audio_file)

        # Step 3: Verify voice was created
        assert result.voice_id is not None
        assert result.user_id == test_user_id
        assert result.name == "Integration Test Voice"
        assert result.status == VoiceStatus.UPLOADING
        assert result.sample_file_url is not None

        # Step 4: Verify file was stored
        voice_id = result.voice_id
        stored_file_exists = file_service.voice_file_exists(test_user_id, voice_id)
        assert stored_file_exists is True

        # Cleanup
        await voice_service.delete_voice(voice_id, test_user_id)

    @pytest.mark.asyncio
    async def test_voice_update_workflow(
        self,
        voice_service: VoiceService,
        test_user_id: uuid4,
    ) -> None:
        """Integration: Voice update workflow."""
        # Step 1: Create voice
        voice_input = VoiceUploadInput(
            user_id=test_user_id,
            name="Original Name",
            description="Original description",
            gender=VoiceGender.MALE,
        )

        audio_content = b"test_audio"
        audio_file_obj = BytesIO(audio_content)
        audio_file = UploadFile(filename="test.mp3", file=audio_file_obj)

        voice = await voice_service.upload_voice(voice_input, audio_file)
        voice_id = voice.voice_id

        # Step 2: Update voice metadata
        update_input = VoiceUpdateInput(
            name="Updated Name",
            description="Updated description",
            gender=VoiceGender.FEMALE,
        )

        updated_voice = await voice_service.update_voice(voice_id, update_input, test_user_id)

        # Step 3: Verify updates
        assert updated_voice.name == "Updated Name"
        assert updated_voice.description == "Updated description"
        assert updated_voice.gender == VoiceGender.FEMALE

        # Cleanup
        await voice_service.delete_voice(voice_id, test_user_id)

    @pytest.mark.asyncio
    async def test_voice_list_and_pagination(
        self,
        voice_service: VoiceService,
        test_user_id: uuid4,
    ) -> None:
        """Integration: Voice listing and pagination."""
        # Step 1: Create multiple voices
        voice_ids = []
        for i in range(5):
            voice_input = VoiceUploadInput(
                user_id=test_user_id,
                name=f"Voice {i}",
                gender=VoiceGender.NEUTRAL,
            )

            audio_content = b"test_audio"
            audio_file_obj = BytesIO(audio_content)
            audio_file = UploadFile(filename=f"test{i}.mp3", file=audio_file_obj)

            voice = await voice_service.upload_voice(voice_input, audio_file)
            voice_ids.append(voice.voice_id)

        # Step 2: List all voices
        result = await voice_service.list_user_voices(test_user_id, limit=100, offset=0)

        assert result.total_count >= 5
        assert len(result.voices) >= 5

        # Step 3: Test pagination
        page1 = await voice_service.list_user_voices(test_user_id, limit=2, offset=0)
        assert len(page1.voices) == 2

        page2 = await voice_service.list_user_voices(test_user_id, limit=2, offset=2)
        assert len(page2.voices) == 2

        # Cleanup
        for voice_id in voice_ids:
            await voice_service.delete_voice(voice_id, test_user_id)

    @pytest.mark.asyncio
    async def test_voice_usage_tracking(
        self,
        voice_service: VoiceService,
        test_session: Session,
        test_user_id: uuid4,
    ) -> None:
        """Integration: Voice usage tracking."""
        # Step 1: Create voice
        voice_input = VoiceUploadInput(
            user_id=test_user_id,
            name="Usage Test Voice",
            gender=VoiceGender.NEUTRAL,
        )

        audio_content = b"test_audio"
        audio_file_obj = BytesIO(audio_content)
        audio_file = UploadFile(filename="test.mp3", file=audio_file_obj)

        voice = await voice_service.upload_voice(voice_input, audio_file)
        voice_id = voice.voice_id

        # Step 2: Increment usage
        await voice_service.increment_usage(voice_id)
        await voice_service.increment_usage(voice_id)
        await voice_service.increment_usage(voice_id)

        # Step 3: Verify usage count
        repository = VoiceRepository(test_session)
        updated_voice = repository.get_by_id(voice_id)
        assert updated_voice is not None
        assert updated_voice.times_used == 3

        # Cleanup
        await voice_service.delete_voice(voice_id, test_user_id)

    @pytest.mark.asyncio
    async def test_voice_deletion_cleanup(
        self,
        voice_service: VoiceService,
        file_service: FileManagementService,
        test_user_id: uuid4,
    ) -> None:
        """Integration: Voice deletion cleans up both database and files."""
        # Step 1: Create voice
        voice_input = VoiceUploadInput(
            user_id=test_user_id,
            name="Delete Test Voice",
            gender=VoiceGender.NEUTRAL,
        )

        audio_content = b"test_audio"
        audio_file_obj = BytesIO(audio_content)
        audio_file = UploadFile(filename="test.mp3", file=audio_file_obj)

        voice = await voice_service.upload_voice(voice_input, audio_file)
        voice_id = voice.voice_id

        # Step 2: Verify voice and file exist
        voice_before = await voice_service.get_voice(voice_id, test_user_id)
        assert voice_before is not None

        file_exists_before = file_service.voice_file_exists(test_user_id, voice_id)
        assert file_exists_before is True

        # Step 3: Delete voice
        deleted = await voice_service.delete_voice(voice_id, test_user_id)
        assert deleted is True

        # Step 4: Verify voice and file are deleted
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await voice_service.get_voice(voice_id, test_user_id)

        assert exc_info.value.status_code == 404

        file_exists_after = file_service.voice_file_exists(test_user_id, voice_id)
        assert file_exists_after is False


@pytest.mark.integration
class TestVoiceAccessControl:
    """Integration tests for voice access control."""

    @pytest.fixture
    def voice_service(self, db_session: Session) -> VoiceService:
        """Fixture: VoiceService with real dependencies."""
        from core.config import get_settings

        return VoiceService(session=db_session, settings=get_settings())

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_voices(
        self,
        voice_service: VoiceService,
    ) -> None:
        """Integration: Users cannot access voices owned by other users."""
        user1_id = uuid4()
        user2_id = uuid4()

        # User 1 creates a voice
        voice_input = VoiceUploadInput(
            user_id=user1_id,
            name="User 1 Voice",
            gender=VoiceGender.NEUTRAL,
        )

        audio_content = b"test_audio"
        audio_file_obj = BytesIO(audio_content)
        audio_file = UploadFile(filename="test.mp3", file=audio_file_obj)

        voice = await voice_service.upload_voice(voice_input, audio_file)
        voice_id = voice.voice_id

        # User 2 tries to access User 1's voice
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await voice_service.get_voice(voice_id, user2_id)

        assert exc_info.value.status_code == 403

        # Cleanup
        await voice_service.delete_voice(voice_id, user1_id)

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_users_voices(
        self,
        voice_service: VoiceService,
    ) -> None:
        """Integration: Users cannot delete voices owned by other users."""
        user1_id = uuid4()
        user2_id = uuid4()

        # User 1 creates a voice
        voice_input = VoiceUploadInput(
            user_id=user1_id,
            name="User 1 Voice",
            gender=VoiceGender.NEUTRAL,
        )

        audio_content = b"test_audio"
        audio_file_obj = BytesIO(audio_content)
        audio_file = UploadFile(filename="test.mp3", file=audio_file_obj)

        voice = await voice_service.upload_voice(voice_input, audio_file)
        voice_id = voice.voice_id

        # User 2 tries to delete User 1's voice
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await voice_service.delete_voice(voice_id, user2_id)

        assert exc_info.value.status_code == 403

        # Cleanup
        await voice_service.delete_voice(voice_id, user1_id)


@pytest.mark.integration
class TestVoiceValidation:
    """Integration tests for voice validation."""

    @pytest.fixture
    def voice_service(self, db_session: Session) -> VoiceService:
        """Fixture: VoiceService with real dependencies."""
        from core.config import get_settings

        return VoiceService(session=db_session, settings=get_settings())

    @pytest.mark.asyncio
    async def test_voice_limit_enforcement(
        self,
        voice_service: VoiceService,
    ) -> None:
        """Integration: System enforces maximum voices per user limit."""
        user_id = uuid4()

        # Mock settings to have low limit for testing
        voice_service.settings.voice_max_per_user = 2

        voice_ids = []

        # Create voices up to limit
        for i in range(2):
            voice_input = VoiceUploadInput(
                user_id=user_id,
                name=f"Voice {i}",
                gender=VoiceGender.NEUTRAL,
            )

            audio_content = b"test_audio"
            audio_file_obj = BytesIO(audio_content)
            audio_file = UploadFile(filename=f"test{i}.mp3", file=audio_file_obj)

            voice = await voice_service.upload_voice(voice_input, audio_file)
            voice_ids.append(voice.voice_id)

        # Try to create one more (should fail)
        voice_input = VoiceUploadInput(
            user_id=user_id,
            name="Voice Over Limit",
            gender=VoiceGender.NEUTRAL,
        )

        audio_content = b"test_audio"
        audio_file_obj = BytesIO(audio_content)
        audio_file = UploadFile(filename="test_over_limit.mp3", file=audio_file_obj)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await voice_service.upload_voice(voice_input, audio_file)

        assert exc_info.value.status_code == 400
        assert "maximum" in str(exc_info.value.detail).lower()

        # Cleanup
        for voice_id in voice_ids:
            await voice_service.delete_voice(voice_id, user_id)
