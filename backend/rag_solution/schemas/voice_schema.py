"""
Pydantic schemas for custom voice management.

This module defines data models for voice sample upload, storage, and usage.
"""

from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class VoiceStatus(str):
    """Voice processing status values."""

    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class VoiceGender(str):
    """Voice gender classification values."""

    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


class VoiceUploadInput(BaseModel):
    """Input schema for uploading a custom voice sample."""

    user_id: UUID | None = Field(
        default=None,
        description="User ID (auto-filled from auth token by router)",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Human-readable name for this voice",
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional description of the voice",
    )
    gender: str = Field(
        default=VoiceGender.NEUTRAL,
        description="Voice gender classification",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is not empty or whitespace-only."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("name cannot be empty or whitespace-only")
        return stripped

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        """Validate gender is one of the allowed values."""
        valid_genders = {VoiceGender.MALE, VoiceGender.FEMALE, VoiceGender.NEUTRAL}
        if v not in valid_genders:
            raise ValueError(f"gender must be one of: {', '.join(valid_genders)}")
        return v


class VoiceOutput(BaseModel):
    """Output schema for voice information."""

    voice_id: UUID = Field(..., description="Unique voice identifier")
    user_id: UUID = Field(..., description="Owner user ID")
    name: str = Field(..., description="Voice name")
    description: str | None = Field(default=None, description="Voice description")
    gender: str = Field(..., description="Voice gender")
    status: str = Field(..., description="Processing status")
    provider_voice_id: str | None = Field(
        default=None,
        description="Provider-specific voice ID (after processing)",
    )
    provider_name: str | None = Field(default=None, description="TTS provider name")
    sample_file_url: str = Field(..., description="URL to voice sample file")
    sample_file_size: int | None = Field(default=None, description="File size in bytes")
    quality_score: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Voice quality score (0-100)",
    )
    error_message: str | None = Field(default=None, description="Error details if failed")
    times_used: int = Field(default=0, description="Number of times used in podcasts")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    processed_at: datetime | None = Field(default=None, description="Processing completion timestamp")

    model_config = {"from_attributes": True}


class VoiceListResponse(BaseModel):
    """Response schema for listing user's voices."""

    voices: list[VoiceOutput] = Field(..., description="List of user's custom voices")
    total_count: int = Field(..., ge=0, description="Total number of voices")


class VoiceProcessingInput(BaseModel):
    """Input schema for processing a voice sample with a TTS provider."""

    voice_id: UUID = Field(..., description="Voice ID to process")
    provider_name: str = Field(
        ...,
        description="TTS provider to use for voice cloning",
    )

    # Supported TTS providers for custom voices
    SUPPORTED_PROVIDERS: ClassVar[set[str]] = {"elevenlabs", "playht", "resemble"}

    @field_validator("provider_name")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider is supported for custom voices."""
        v_lower = v.lower()
        if v_lower not in cls.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider '{v}'. Supported providers: {', '.join(sorted(cls.SUPPORTED_PROVIDERS))}"
            )
        return v_lower


class VoiceUpdateInput(BaseModel):
    """Input schema for updating voice metadata."""

    name: str | None = Field(default=None, min_length=1, max_length=200, description="Updated voice name")
    description: str | None = Field(default=None, max_length=1000, description="Updated description")
    gender: str | None = Field(default=None, description="Updated gender classification")

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str | None) -> str | None:
        """Validate gender if provided."""
        if v is not None:
            valid_genders = {VoiceGender.MALE, VoiceGender.FEMALE, VoiceGender.NEUTRAL}
            if v not in valid_genders:
                raise ValueError(f"gender must be one of: {', '.join(valid_genders)}")
        return v
