"""
Voice management service.

Handles custom voice upload, processing, and management:
1. Upload voice sample files
2. Process voice with TTS provider (ElevenLabs Phase 1, F5-TTS Phase 2)
3. List user's voices
4. Update voice metadata
5. Delete voice (with file cleanup)
6. Track voice usage in podcast generation
"""

import logging
from typing import ClassVar
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.core.exceptions import ValidationError
from rag_solution.models.voice import VoiceStatus
from rag_solution.repository.voice_repository import VoiceRepository
from rag_solution.schemas.voice_schema import (
    VoiceListResponse,
    VoiceOutput,
    VoiceProcessingInput,
    VoiceUpdateInput,
    VoiceUploadInput,
)
from rag_solution.services.file_management_service import FileManagementService

logger = logging.getLogger(__name__)


class VoiceService:
    """Service for voice management."""

    # Supported audio formats for voice samples
    SUPPORTED_FORMATS: ClassVar[list[str]] = ["mp3", "wav", "m4a", "flac", "ogg"]

    # Max file size (MB)
    MAX_FILE_SIZE_MB: ClassVar[int] = 10

    # Min/max sample duration (seconds)
    MIN_SAMPLE_DURATION: ClassVar[int] = 5
    MAX_SAMPLE_DURATION: ClassVar[int] = 300  # 5 minutes

    def __init__(self, session: Session, settings: Settings):
        """
        Initialize voice service.

        Args:
            session: Database session
            settings: Application settings
        """
        self.session = session
        self.settings = settings
        self.repository = VoiceRepository(session)
        self.file_service = FileManagementService(session, settings)

        logger.info("VoiceService initialized")

    async def upload_voice(
        self,
        voice_input: VoiceUploadInput,
        audio_file: UploadFile,
    ) -> VoiceOutput:
        """
        Upload voice sample file and create voice record.

        Args:
            voice_input: Voice upload request
            audio_file: Uploaded audio file

        Returns:
            VoiceOutput with UPLOADING status

        Raises:
            ValidationError: If validation fails (invalid format, file too large, etc.)
            HTTPException: If upload fails
        """
        try:
            # Validate user_id is set (should be auto-filled by router from auth)
            if not voice_input.user_id:
                raise ValidationError("user_id is required for voice upload", field="user_id")

            user_id = voice_input.user_id

            # Validate file
            self._validate_audio_file(audio_file)

            # Extract audio format from filename
            filename = audio_file.filename or "sample.mp3"
            audio_format = filename.split(".")[-1].lower()

            if audio_format not in self.SUPPORTED_FORMATS:
                raise ValidationError(
                    f"Unsupported audio format '{audio_format}'. Supported: {', '.join(self.SUPPORTED_FORMATS)}",
                    field="audio_format",
                )

            # Check user's voice limit
            voice_count = self.repository.count_voices_for_user(user_id)
            max_voices = getattr(self.settings, "voice_max_per_user", 10)

            if voice_count >= max_voices:
                raise ValidationError(
                    f"User has {voice_count} voices, maximum {max_voices} allowed. "
                    "Please delete unused voices before uploading new ones.",
                    field="voice_limit",
                )

            # Read file content
            file_content = await audio_file.read()
            file_size = len(file_content)

            # Check file size
            max_size_bytes = self.MAX_FILE_SIZE_MB * 1024 * 1024
            if file_size > max_size_bytes:
                raise ValidationError(
                    f"File size {file_size / 1024 / 1024:.1f}MB exceeds maximum {self.MAX_FILE_SIZE_MB}MB",
                    field="file_size",
                )

            logger.info(
                "Uploading voice sample: user=%s, name=%s, format=%s, size=%d bytes",
                user_id,
                voice_input.name,
                audio_format,
                file_size,
            )

            # Create voice record first
            voice = self.repository.create(
                user_id=user_id,
                name=voice_input.name,
                sample_file_url="",  # Will update after file storage
                description=voice_input.description,
                gender=voice_input.gender,
                sample_file_size=file_size,
            )

            # Store voice sample file
            try:
                file_path = self.file_service.save_voice_file(
                    user_id=user_id,
                    voice_id=voice.voice_id,
                    file_content=file_content,
                    audio_format=audio_format,
                )

                # Update voice record with file path
                updated_voice = self.repository.update_status(
                    voice_id=voice.voice_id,
                    status=VoiceStatus.UPLOADING,
                    provider_voice_id=None,
                    provider_name=None,
                    quality_score=None,
                    error_message=None,
                )

                if not updated_voice:
                    raise HTTPException(status_code=500, detail="Failed to update voice status")

                # Update sample_file_url to API endpoint
                sample_file_url = f"/api/voices/{voice.voice_id}/sample"

                # Need to manually update the field since update_status doesn't handle it
                updated_voice.sample_file_url = sample_file_url
                self.session.commit()
                self.session.refresh(updated_voice)

                logger.info(
                    "Voice sample uploaded successfully: voice_id=%s, path=%s",
                    updated_voice.voice_id,
                    file_path,
                )

                # Use updated voice for return
                voice = updated_voice

            except Exception as e:
                # Clean up voice record if file storage fails
                self.repository.delete(voice.voice_id)
                logger.error("Failed to store voice file, rolled back voice record: %s", e)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to store voice file: {e}",
                ) from e

            return self.repository.to_schema(voice)

        except ValidationError as e:
            logger.error("Voice upload validation failed: %s", e)
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            logger.exception("Voice upload failed: %s", e)
            raise HTTPException(
                status_code=500,
                detail=f"Voice upload failed: {e}",
            ) from e

    async def process_voice(
        self,
        voice_id: UUID,
        processing_input: VoiceProcessingInput,
        user_id: UUID,
    ) -> VoiceOutput:
        """
        Process voice with TTS provider for voice cloning.

        Args:
            voice_id: Voice ID
            processing_input: Processing request (provider name)
            user_id: User ID (for access control)

        Returns:
            VoiceOutput with PROCESSING status

        Raises:
            HTTPException: If voice not found, access denied, or processing fails
        """
        try:
            # Get voice and verify ownership
            voice = self.repository.get_by_id(voice_id)

            if not voice:
                raise HTTPException(status_code=404, detail="Voice not found")

            if voice.user_id != user_id:
                raise HTTPException(status_code=403, detail="Access denied")

            # Validate voice status
            if voice.status == VoiceStatus.READY:
                raise HTTPException(
                    status_code=409,
                    detail="Voice is already processed and ready",
                )

            if voice.status == VoiceStatus.PROCESSING:
                raise HTTPException(
                    status_code=409,
                    detail="Voice is currently being processed",
                )

            # Validate provider is supported
            supported_providers = getattr(self.settings, "voice_tts_providers", "elevenlabs").split(",")

            if processing_input.provider_name not in supported_providers:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported provider '{processing_input.provider_name}'. "
                    f"Supported: {', '.join(supported_providers)}",
                )

            logger.info(
                "Starting voice processing: voice_id=%s, provider=%s",
                voice_id,
                processing_input.provider_name,
            )

            # Update status to PROCESSING
            updated_voice = self.repository.update_status(
                voice_id=voice_id,
                status=VoiceStatus.PROCESSING,
                provider_name=processing_input.provider_name,
            )

            if not updated_voice:
                raise HTTPException(status_code=500, detail="Failed to update voice status to PROCESSING")

            # TODO: Implement actual TTS provider integration
            # Phase 1: ElevenLabs voice cloning
            # Phase 2: F5-TTS voice cloning
            #
            # For now, mark as failed with message about implementation
            updated_voice = self.repository.update_status(
                voice_id=voice_id,
                status=VoiceStatus.FAILED,
                error_message="TTS provider integration not yet implemented (Phase 1 in progress)",
            )

            if not updated_voice:
                raise HTTPException(status_code=500, detail="Failed to update voice status to FAILED")

            return self.repository.to_schema(updated_voice)

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Voice processing failed: %s", e)
            # Update voice status to FAILED
            self.repository.update_status(
                voice_id=voice_id,
                status=VoiceStatus.FAILED,
                error_message=str(e),
            )
            raise HTTPException(
                status_code=500,
                detail=f"Voice processing failed: {e}",
            ) from e

    async def list_user_voices(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> VoiceListResponse:
        """
        List voices for user with pagination.

        Args:
            user_id: User ID
            limit: Maximum results (1-100, default 100)
            offset: Pagination offset (default 0)

        Returns:
            VoiceListResponse with voices and total count
        """
        # Validate pagination parameters
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=400,
                detail="limit must be between 1 and 100",
            )

        if offset < 0:
            raise HTTPException(
                status_code=400,
                detail="offset must be >= 0",
            )

        voices = self.repository.get_by_user(user_id=user_id, limit=limit, offset=offset)

        total_count = self.repository.count_voices_for_user(user_id)

        return VoiceListResponse(
            voices=[self.repository.to_schema(v) for v in voices],
            total_count=total_count,
        )

    async def get_voice(
        self,
        voice_id: UUID,
        user_id: UUID,
    ) -> VoiceOutput:
        """
        Get voice by ID with access control.

        Args:
            voice_id: Voice ID
            user_id: User ID (for access control)

        Returns:
            VoiceOutput

        Raises:
            HTTPException: If not found or access denied
        """
        voice = self.repository.get_by_id(voice_id)

        if not voice:
            raise HTTPException(status_code=404, detail="Voice not found")

        if voice.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        return self.repository.to_schema(voice)

    async def update_voice(
        self,
        voice_id: UUID,
        update_input: VoiceUpdateInput,
        user_id: UUID,
    ) -> VoiceOutput:
        """
        Update voice metadata.

        Args:
            voice_id: Voice ID
            update_input: Update request
            user_id: User ID (for access control)

        Returns:
            Updated VoiceOutput

        Raises:
            HTTPException: If not found, access denied, or validation fails
        """
        try:
            # Get voice and verify ownership
            voice = self.repository.get_by_id(voice_id)

            if not voice:
                raise HTTPException(status_code=404, detail="Voice not found")

            if voice.user_id != user_id:
                raise HTTPException(status_code=403, detail="Access denied")

            # Update voice
            updated_voice = self.repository.update(
                voice_id=voice_id,
                name=update_input.name,
                description=update_input.description,
                gender=update_input.gender,
            )

            if not updated_voice:
                raise HTTPException(status_code=500, detail="Failed to update voice")

            logger.info("Updated voice metadata: voice_id=%s", voice_id)

            return self.repository.to_schema(updated_voice)

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Voice update failed: %s", e)
            raise HTTPException(
                status_code=500,
                detail=f"Voice update failed: {e}",
            ) from e

    async def delete_voice(
        self,
        voice_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Delete voice with access control and file cleanup.

        Args:
            voice_id: Voice ID
            user_id: User ID (for access control)

        Returns:
            True if deleted

        Raises:
            HTTPException: If not found or access denied
        """
        try:
            # Get voice and verify ownership
            voice = self.repository.get_by_id(voice_id)

            if not voice:
                raise HTTPException(status_code=404, detail="Voice not found")

            if voice.user_id != user_id:
                raise HTTPException(status_code=403, detail="Access denied")

            # Delete voice sample file
            try:
                file_deleted = self.file_service.delete_voice_file(
                    user_id=user_id,
                    voice_id=voice_id,
                )

                if file_deleted:
                    logger.info("Deleted voice sample file: voice_id=%s", voice_id)
                else:
                    logger.warning("Voice sample file not found: voice_id=%s", voice_id)

            except Exception as e:
                logger.warning("Failed to delete voice sample file: %s", e)
                # Continue with database deletion even if file deletion fails

            # Delete database record
            deleted = self.repository.delete(voice_id)

            if deleted:
                logger.info("Deleted voice: voice_id=%s", voice_id)
            else:
                logger.warning("Voice not found during deletion: voice_id=%s", voice_id)

            return deleted

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Voice deletion failed: %s", e)
            raise HTTPException(
                status_code=500,
                detail=f"Voice deletion failed: {e}",
            ) from e

    async def increment_usage(self, voice_id: UUID) -> None:
        """
        Increment voice usage counter.

        Called when voice is used in podcast generation.

        Args:
            voice_id: Voice ID
        """
        try:
            voice = self.repository.increment_usage(voice_id)

            if voice:
                logger.debug("Incremented usage for voice %s (now %d)", voice_id, voice.times_used)
            else:
                logger.warning("Voice %s not found for usage increment", voice_id)

        except Exception as e:
            # Don't fail podcast generation if usage tracking fails
            logger.warning("Failed to increment voice usage for %s: %s", voice_id, e)

    def _validate_audio_file(self, audio_file: UploadFile) -> None:
        """
        Validate uploaded audio file.

        Args:
            audio_file: Uploaded file

        Raises:
            ValidationError: If validation fails
        """
        # Check file exists
        if not audio_file or not audio_file.filename:
            raise ValidationError("No audio file provided", field="audio_file")

        # Check content type
        content_type = audio_file.content_type or ""
        valid_content_types = [
            "audio/mpeg",
            "audio/mp3",
            "audio/wav",
            "audio/x-wav",
            "audio/m4a",
            "audio/x-m4a",
            "audio/flac",
            "audio/x-flac",
            "audio/ogg",
            "audio/vorbis",
            "application/octet-stream",  # Sometimes used for audio files
        ]

        if content_type and content_type not in valid_content_types:
            logger.warning(
                "Unexpected content type: %s (continuing with validation based on file extension)",
                content_type,
            )

        # Check file extension
        filename = audio_file.filename.lower()
        if not any(filename.endswith(f".{fmt}") for fmt in self.SUPPORTED_FORMATS):
            raise ValidationError(
                f"Invalid file extension. Supported: {', '.join(self.SUPPORTED_FORMATS)}",
                field="audio_file",
            )

        logger.debug("Audio file validation passed: %s (%s)", audio_file.filename, content_type)
