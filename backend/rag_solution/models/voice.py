"""
Database model for custom voice samples.

Tracks user-uploaded voice samples for podcast generation with custom voices.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.identity_service import IdentityService
from rag_solution.file_management.database import Base


class VoiceStatus(str):
    """Voice processing status enum values."""

    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class VoiceGender(str):
    """Voice gender classification."""

    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


class Voice(Base):
    """Database model for custom voice samples."""

    __tablename__ = "voices"

    # Primary key
    voice_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=IdentityService.generate_id,
        nullable=False,
        index=True,
    )

    # Foreign key
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Voice metadata
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    gender: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=VoiceGender.NEUTRAL,
    )

    # Voice processing status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=VoiceStatus.UPLOADING,
        index=True,
    )

    # Voice provider information
    # This stores the provider-specific voice ID after processing
    # For ElevenLabs, this would be the voice_id returned after cloning
    provider_voice_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # File storage information
    # Path to the original voice sample file(s)
    sample_file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    sample_file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Voice quality metrics (optional, populated during processing)
    quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-100 scale

    # Error tracking (populated when status = FAILED)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Usage tracking
    times_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="voices")

    def __repr__(self) -> str:
        """String representation of Voice."""
        return f"<Voice(voice_id={self.voice_id}, user_id={self.user_id}, name={self.name}, status={self.status})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary for API responses."""
        return {
            "voice_id": self.voice_id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "gender": self.gender,
            "status": self.status,
            "provider_voice_id": self.provider_voice_id,
            "provider_name": self.provider_name,
            "sample_file_url": self.sample_file_url,
            "sample_file_size": self.sample_file_size,
            "quality_score": self.quality_score,
            "error_message": self.error_message,
            "times_used": self.times_used,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "processed_at": self.processed_at,
        }
