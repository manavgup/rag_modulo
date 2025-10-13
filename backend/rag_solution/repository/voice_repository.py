"""
Repository for voice database operations.

Provides data access methods for Voice model with proper error handling
and transaction management.
"""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from rag_solution.models.voice import Voice, VoiceStatus
from rag_solution.schemas.voice_schema import VoiceOutput

logger = logging.getLogger(__name__)


class VoiceRepository:
    """Repository for voice data access operations."""

    def __init__(self, session: Session):
        """
        Initialize voice repository.

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def create(
        self,
        user_id: UUID,
        name: str,
        sample_file_url: str,
        description: str | None = None,
        gender: str = "neutral",
        sample_file_size: int | None = None,
    ) -> Voice:
        """
        Create new voice record.

        Args:
            user_id: User uploading the voice
            name: Voice name
            sample_file_url: URL to voice sample file
            description: Optional voice description
            gender: Voice gender classification
            sample_file_size: Size of sample file in bytes

        Returns:
            Created Voice model

        Raises:
            IntegrityError: If foreign key constraints fail
            SQLAlchemyError: For other database errors
        """
        try:
            voice = Voice(
                user_id=user_id,
                name=name,
                description=description,
                gender=gender,
                status=VoiceStatus.UPLOADING,
                sample_file_url=sample_file_url,
                sample_file_size=sample_file_size,
                times_used=0,
            )

            self.session.add(voice)
            self.session.commit()
            self.session.refresh(voice)

            logger.info(
                "Created voice %s for user %s: %s",
                voice.voice_id,
                user_id,
                name,
            )

            return voice

        except IntegrityError as e:
            self.session.rollback()
            logger.error("Integrity error creating voice: %s", e)
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error("Database error creating voice: %s", e)
            raise

    def get_by_id(self, voice_id: UUID) -> Voice | None:
        """
        Get voice by ID.

        Args:
            voice_id: Voice UUID

        Returns:
            Voice model or None if not found
        """
        try:
            result = self.session.execute(select(Voice).where(Voice.voice_id == voice_id))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error("Error fetching voice %s: %s", voice_id, e)
            raise

    def get_by_user(self, user_id: UUID, limit: int = 100, offset: int = 0) -> list[Voice]:
        """
        Get all voices for a user.

        Args:
            user_id: User UUID
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of Voice models
        """
        try:
            result = self.session.execute(
                select(Voice)
                .where(Voice.user_id == user_id)
                .order_by(desc(Voice.created_at))
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error("Error fetching voices for user %s: %s", user_id, e)
            raise

    def get_ready_voices_by_user(self, user_id: UUID) -> list[Voice]:
        """
        Get all ready voices for a user.

        Args:
            user_id: User UUID

        Returns:
            List of Voice models with status=READY
        """
        try:
            result = self.session.execute(
                select(Voice)
                .where(
                    and_(
                        Voice.user_id == user_id,
                        Voice.status == VoiceStatus.READY,
                    )
                )
                .order_by(desc(Voice.created_at))
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error("Error fetching ready voices for user %s: %s", user_id, e)
            raise

    def count_voices_for_user(self, user_id: UUID) -> int:
        """
        Count total voices for user.

        Args:
            user_id: User UUID

        Returns:
            Count of voices
        """
        try:
            result = self.session.execute(select(Voice).where(Voice.user_id == user_id))
            return len(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error("Error counting voices for user %s: %s", user_id, e)
            raise

    def update(
        self,
        voice_id: UUID,
        name: str | None = None,
        description: str | None = None,
        gender: str | None = None,
    ) -> Voice | None:
        """
        Update voice metadata.

        Args:
            voice_id: Voice UUID
            name: Updated name
            description: Updated description
            gender: Updated gender

        Returns:
            Updated Voice model or None if not found
        """
        try:
            voice = self.get_by_id(voice_id)
            if not voice:
                logger.warning("Voice %s not found for update", voice_id)
                return None

            if name is not None:
                voice.name = name
            if description is not None:
                voice.description = description
            if gender is not None:
                voice.gender = gender

            voice.updated_at = datetime.utcnow()

            self.session.commit()
            self.session.refresh(voice)

            logger.info("Updated voice %s metadata", voice_id)

            return voice

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error("Error updating voice %s: %s", voice_id, e)
            raise

    def update_status(
        self,
        voice_id: UUID,
        status: str,
        provider_voice_id: str | None = None,
        provider_name: str | None = None,
        quality_score: int | None = None,
        error_message: str | None = None,
    ) -> Voice | None:
        """
        Update voice processing status.

        Args:
            voice_id: Voice UUID
            status: New status (uploading, processing, ready, failed)
            provider_voice_id: Provider-specific voice ID (when ready)
            provider_name: TTS provider name
            quality_score: Voice quality score (0-100)
            error_message: Error message if failed

        Returns:
            Updated Voice model or None if not found
        """
        try:
            voice = self.get_by_id(voice_id)
            if not voice:
                logger.warning("Voice %s not found for status update", voice_id)
                return None

            voice.status = status
            voice.updated_at = datetime.utcnow()

            if provider_voice_id is not None:
                voice.provider_voice_id = provider_voice_id
            if provider_name is not None:
                voice.provider_name = provider_name
            if quality_score is not None:
                voice.quality_score = quality_score

            if status == VoiceStatus.FAILED:
                voice.error_message = error_message
            elif status == VoiceStatus.READY:
                voice.processed_at = datetime.utcnow()
                voice.error_message = None  # Clear any previous errors

            self.session.commit()
            self.session.refresh(voice)

            logger.info("Updated voice %s status to %s", voice_id, status)

            return voice

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error("Error updating voice %s status: %s", voice_id, e)
            raise

    def increment_usage(self, voice_id: UUID) -> Voice | None:
        """
        Increment times_used counter for voice.

        Args:
            voice_id: Voice UUID

        Returns:
            Updated Voice model or None if not found
        """
        try:
            voice = self.get_by_id(voice_id)
            if not voice:
                logger.warning("Voice %s not found for usage increment", voice_id)
                return None

            voice.times_used += 1
            voice.updated_at = datetime.utcnow()

            self.session.commit()
            self.session.refresh(voice)

            logger.debug("Incremented usage for voice %s (now %d)", voice_id, voice.times_used)

            return voice

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error("Error incrementing usage for voice %s: %s", voice_id, e)
            raise

    def delete(self, voice_id: UUID) -> bool:
        """
        Delete voice by ID.

        Args:
            voice_id: Voice UUID

        Returns:
            True if deleted, False if not found
        """
        try:
            voice = self.get_by_id(voice_id)
            if not voice:
                logger.warning("Voice %s not found for deletion", voice_id)
                return False

            self.session.delete(voice)
            self.session.commit()

            logger.info("Deleted voice %s", voice_id)

            return True

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error("Error deleting voice %s: %s", voice_id, e)
            raise

    def to_schema(self, voice: Voice) -> VoiceOutput:
        """
        Convert Voice model to schema.

        Args:
            voice: Voice database model

        Returns:
            VoiceOutput schema
        """
        return VoiceOutput(
            voice_id=voice.voice_id,
            user_id=voice.user_id,
            name=voice.name,
            description=voice.description,
            gender=voice.gender,
            status=voice.status,
            provider_voice_id=voice.provider_voice_id,
            provider_name=voice.provider_name,
            sample_file_url=voice.sample_file_url,
            sample_file_size=voice.sample_file_size,
            quality_score=voice.quality_score,
            error_message=voice.error_message,
            times_used=voice.times_used,
            created_at=voice.created_at,
            updated_at=voice.updated_at,
            processed_at=voice.processed_at,
        )
