"""
Database model for podcast generation.

Tracks podcast generation requests, status, progress, and results.
"""

from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.identity_service import IdentityService
from rag_solution.file_management.database import Base
from rag_solution.schemas.podcast_schema import AudioFormat, PodcastDuration, PodcastStatus


class Podcast(Base):
    """Database model for podcast generation tracking."""

    __tablename__ = "podcasts"
    __table_args__: ClassVar[dict] = {"extend_existing": True}

    # Primary key
    podcast_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=IdentityService.generate_id,
        nullable=False,
        index=True,
    )

    # Foreign keys
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    collection_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Podcast metadata
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    duration: Mapped[PodcastDuration] = mapped_column(
        SQLEnum(PodcastDuration, name="podcast_duration_enum"),
        nullable=False,
        default=PodcastDuration.MEDIUM,
    )

    # Status and progress tracking
    status: Mapped[PodcastStatus] = mapped_column(
        SQLEnum(PodcastStatus, name="podcast_status_enum"),
        nullable=False,
        default=PodcastStatus.QUEUED,
        index=True,
    )
    progress_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    step_details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    estimated_time_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Voice settings (stored as JSON for flexibility)
    voice_settings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    host_voice: Mapped[str] = mapped_column(String(50), nullable=False, default="alloy")
    expert_voice: Mapped[str] = mapped_column(String(50), nullable=False, default="onyx")

    # Audio format
    audio_format: Mapped[AudioFormat] = mapped_column(
        SQLEnum(AudioFormat, name="audio_format_enum"),
        nullable=False,
        default=AudioFormat.MP3,
    )

    # Results (populated when status = COMPLETED)
    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    chapters: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Dynamic chapter markers with timestamps (title, start_time, end_time, word_count)",
    )
    audio_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Error tracking (populated when status = FAILED)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="podcasts")
    collection = relationship("Collection", back_populates="podcasts")

    def __repr__(self) -> str:
        """String representation of Podcast."""
        return (
            f"<Podcast(podcast_id={self.podcast_id}, "
            f"user_id={self.user_id}, "
            f"collection_id={self.collection_id}, "
            f"status={self.status}, "
            f"progress={self.progress_percentage}%)>"
        )

    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "podcast_id": self.podcast_id,
            "user_id": self.user_id,
            "collection_id": self.collection_id,
            "title": self.title,
            "duration": self.duration,
            "status": self.status,
            "progress_percentage": self.progress_percentage,
            "current_step": self.current_step,
            "step_details": self.step_details,
            "estimated_time_remaining": self.estimated_time_remaining,
            "audio_url": self.audio_url,
            "transcript": self.transcript,
            "chapters": self.chapters or [],
            "audio_size_bytes": self.audio_size_bytes,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
        }
