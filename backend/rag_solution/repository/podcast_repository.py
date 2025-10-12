"""
Repository for podcast database operations.

Provides data access methods for Podcast model with proper error handling
and transaction management.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from rag_solution.models.podcast import Podcast
from rag_solution.schemas.podcast_schema import (
    PodcastGenerationOutput,
    PodcastStatus,
    ProgressStepDetails,
)

logger = logging.getLogger(__name__)


class PodcastRepository:
    """Repository for podcast data access operations."""

    def __init__(self, session: Session):
        """
        Initialize podcast repository.

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def create(
        self,
        user_id: UUID,
        collection_id: UUID,
        duration: int,
        voice_settings: dict[str, Any],
        host_voice: str,
        expert_voice: str,
        audio_format: str,
        title: str | None = None,
    ) -> Podcast:
        """
        Create new podcast record.

        Args:
            user_id: User requesting podcast
            collection_id: Collection to generate from
            duration: Target duration
            voice_settings: Voice configuration dict
            host_voice: HOST speaker voice ID
            expert_voice: EXPERT speaker voice ID
            audio_format: Audio format
            title: Optional podcast title

        Returns:
            Created Podcast model

        Raises:
            IntegrityError: If foreign key constraints fail
            SQLAlchemyError: For other database errors
        """
        try:
            podcast = Podcast(
                user_id=user_id,
                collection_id=collection_id,
                title=title,
                duration=duration,
                voice_settings=voice_settings,
                host_voice=host_voice,
                expert_voice=expert_voice,
                audio_format=audio_format,
                status=PodcastStatus.QUEUED,
                progress_percentage=0,
            )

            self.session.add(podcast)
            self.session.commit()
            self.session.refresh(podcast)

            logger.info(
                "Created podcast %s for user %s, collection %s",
                podcast.podcast_id,
                user_id,
                collection_id,
            )

            return podcast

        except IntegrityError as e:
            self.session.rollback()
            logger.error("Integrity error creating podcast: %s", e)
            raise
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error("Database error creating podcast: %s", e)
            raise

    def get_by_id(self, podcast_id: UUID) -> Podcast | None:
        """
        Get podcast by ID.

        Args:
            podcast_id: Podcast UUID

        Returns:
            Podcast model or None if not found
        """
        try:
            result = self.session.execute(select(Podcast).where(Podcast.podcast_id == podcast_id))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error("Error fetching podcast %s: %s", podcast_id, e)
            raise

    def get_by_user(self, user_id: UUID, limit: int = 100, offset: int = 0) -> list[Podcast]:
        """
        Get all podcasts for a user.

        Args:
            user_id: User UUID
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of Podcast models
        """
        try:
            result = self.session.execute(
                select(Podcast)
                .where(Podcast.user_id == user_id)
                .order_by(desc(Podcast.created_at))
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error("Error fetching podcasts for user %s: %s", user_id, e)
            raise

    def get_by_user_and_collection(self, user_id: UUID, collection_id: UUID) -> list[Podcast]:
        """
        Get podcasts for specific user and collection.

        Args:
            user_id: User UUID
            collection_id: Collection UUID

        Returns:
            List of Podcast models
        """
        try:
            result = self.session.execute(
                select(Podcast)
                .where(
                    and_(
                        Podcast.user_id == user_id,
                        Podcast.collection_id == collection_id,
                    )
                )
                .order_by(desc(Podcast.created_at))
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(
                "Error fetching podcasts for user %s, collection %s: %s",
                user_id,
                collection_id,
                e,
            )
            raise

    def count_active_for_user(self, user_id: UUID) -> int:
        """
        Count active (QUEUED or GENERATING) podcasts for user.

        Args:
            user_id: User UUID

        Returns:
            Count of active podcasts
        """
        try:
            result = self.session.execute(
                select(Podcast).where(
                    and_(
                        Podcast.user_id == user_id,
                        Podcast.status.in_([PodcastStatus.QUEUED, PodcastStatus.GENERATING]),
                    )
                )
            )
            return len(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error("Error counting active podcasts for user %s: %s", user_id, e)
            raise

    def update_progress(
        self,
        podcast_id: UUID,
        progress_percentage: int,
        current_step: str | None = None,
        step_details: dict[str, Any] | None = None,
    ) -> Podcast | None:
        """
        Update podcast progress.

        Args:
            podcast_id: Podcast UUID
            progress_percentage: Progress (0-100)
            current_step: Current processing step
            step_details: Additional step details

        Returns:
            Updated Podcast model or None if not found
        """
        try:
            podcast = self.get_by_id(podcast_id)
            if not podcast:
                logger.warning("Podcast %s not found for progress update", podcast_id)
                return None

            podcast.progress_percentage = progress_percentage
            podcast.current_step = current_step
            podcast.step_details = step_details
            podcast.updated_at = datetime.utcnow()

            self.session.commit()
            self.session.refresh(podcast)

            logger.debug(
                "Updated progress for podcast %s: %d%% - %s",
                podcast_id,
                progress_percentage,
                current_step,
            )

            return podcast

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error("Error updating podcast %s progress: %s", podcast_id, e)
            raise

    def update_status(
        self, podcast_id: UUID, status: PodcastStatus, error_message: str | None = None
    ) -> Podcast | None:
        """
        Update podcast status.

        Args:
            podcast_id: Podcast UUID
            status: New status
            error_message: Error message if FAILED

        Returns:
            Updated Podcast model or None if not found
        """
        try:
            podcast = self.get_by_id(podcast_id)
            if not podcast:
                logger.warning("Podcast %s not found for status update", podcast_id)
                return None

            podcast.status = status
            podcast.updated_at = datetime.utcnow()

            if status == PodcastStatus.FAILED:
                podcast.error_message = error_message
                podcast.completed_at = datetime.utcnow()
            elif status == PodcastStatus.COMPLETED:
                podcast.completed_at = datetime.utcnow()

            self.session.commit()
            self.session.refresh(podcast)

            logger.info("Updated podcast %s status to %s", podcast_id, status.value)

            return podcast

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error("Error updating podcast %s status: %s", podcast_id, e)
            raise

    def mark_completed(
        self,
        podcast_id: UUID,
        audio_url: str,
        transcript: str,
        audio_size_bytes: int,
    ) -> Podcast | None:
        """
        Mark podcast as completed with results.

        Args:
            podcast_id: Podcast UUID
            audio_url: URL to generated audio
            transcript: Full podcast script
            audio_size_bytes: Audio file size

        Returns:
            Updated Podcast model or None if not found
        """
        try:
            podcast = self.get_by_id(podcast_id)
            if not podcast:
                logger.warning("Podcast %s not found for completion", podcast_id)
                return None

            podcast.status = PodcastStatus.COMPLETED
            podcast.audio_url = audio_url
            podcast.transcript = transcript
            podcast.audio_size_bytes = audio_size_bytes
            podcast.progress_percentage = 100
            podcast.current_step = None
            podcast.step_details = None
            podcast.completed_at = datetime.utcnow()
            podcast.updated_at = datetime.utcnow()

            self.session.commit()
            self.session.refresh(podcast)

            logger.info("Marked podcast %s as completed", podcast_id)

            return podcast

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error("Error marking podcast %s completed: %s", podcast_id, e)
            raise

    def delete(self, podcast_id: UUID) -> bool:
        """
        Delete podcast by ID.

        Args:
            podcast_id: Podcast UUID

        Returns:
            True if deleted, False if not found
        """
        try:
            podcast = self.get_by_id(podcast_id)
            if not podcast:
                logger.warning("Podcast %s not found for deletion", podcast_id)
                return False

            self.session.delete(podcast)
            self.session.commit()

            logger.info("Deleted podcast %s", podcast_id)

            return True

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error("Error deleting podcast %s: %s", podcast_id, e)
            raise

    def to_schema(self, podcast: Podcast) -> PodcastGenerationOutput:
        """
        Convert Podcast model to schema.

        Args:
            podcast: Podcast database model

        Returns:
            PodcastGenerationOutput schema
        """
        step_details = None
        if podcast.step_details:
            step_details = ProgressStepDetails(**podcast.step_details)

        return PodcastGenerationOutput(
            podcast_id=podcast.podcast_id,
            user_id=podcast.user_id,
            collection_id=podcast.collection_id,
            status=podcast.status,
            duration=podcast.duration,
            format=podcast.audio_format,
            title=podcast.title,
            audio_url=podcast.audio_url,
            transcript=podcast.transcript,
            audio_size_bytes=podcast.audio_size_bytes,
            error_message=podcast.error_message,
            progress_percentage=podcast.progress_percentage,
            current_step=podcast.current_step,
            step_details=step_details,
            estimated_time_remaining=podcast.estimated_time_remaining,
            # Voice settings
            host_voice=podcast.host_voice,
            expert_voice=podcast.expert_voice,
            # Collection information (will be populated by service if needed)
            collection_name=getattr(podcast.collection, "name", None)
            if hasattr(podcast, "collection") and podcast.collection
            else None,
            created_at=podcast.created_at,
            updated_at=podcast.updated_at,
            completed_at=podcast.completed_at,
        )
