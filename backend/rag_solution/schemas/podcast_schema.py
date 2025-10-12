"""
Pydantic schemas for podcast generation feature.

This module defines data models for podcast generation, including:
- Enums for podcast status, audio formats, voices, and durations
- Voice settings configuration
- Podcast generation input/output schemas
- Q&A dialogue script models (PodcastTurn, PodcastScript)
- Progress tracking structures
"""

from datetime import datetime
from enum import Enum
from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def validate_non_empty_string(value: str, field_name: str) -> str:
    """
    Validate that a string is not empty or whitespace-only.

    Args:
        value: String to validate
        field_name: Name of field for error messages

    Returns:
        Stripped string value

    Raises:
        ValueError: If string is empty or whitespace-only
    """
    stripped = value.strip() if value else ""
    if not stripped:
        raise ValueError(f"{field_name} cannot be empty or whitespace-only")
    return stripped


class PodcastStatus(str, Enum):
    """Status of podcast generation process."""

    QUEUED = "queued"  # Podcast request received, queued for processing
    GENERATING = "generating"  # Actively generating podcast
    COMPLETED = "completed"  # Successfully generated
    FAILED = "failed"  # Generation failed
    CANCELLED = "cancelled"  # User cancelled generation


class AudioFormat(str, Enum):
    """Supported audio output formats."""

    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"
    FLAC = "flac"


class VoiceGender(str, Enum):
    """Voice gender options for TTS."""

    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


class PodcastDuration(int, Enum):
    """Predefined podcast duration options (in minutes)."""

    SHORT = 5  # 5 minutes
    MEDIUM = 15  # 15 minutes
    LONG = 20  # 20 minutes
    EXTENDED = 30  # 30 minutes
    MAXIMUM = 60  # 60 minutes


class Speaker(str, Enum):
    """Speaker roles in Q&A dialogue."""

    HOST = "HOST"  # Asks questions, provides introductions/transitions
    EXPERT = "EXPERT"  # Provides detailed answers and explanations


class VoiceSettings(BaseModel):
    """Voice configuration for text-to-speech generation."""

    voice_id: str = Field(
        ...,
        min_length=1,
        description="TTS provider-specific voice identifier (e.g., 'alloy', 'onyx')",
    )
    gender: VoiceGender = Field(default=VoiceGender.NEUTRAL, description="Voice gender preference")
    speed: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Speech speed multiplier (0.5 = half speed, 2.0 = double speed)",
    )
    pitch: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Voice pitch multiplier (0.5 = lower, 2.0 = higher)",
    )
    language: str | None = Field(
        default=None,
        description="Voice language/locale (e.g., 'en-US')",
    )
    name: str | None = Field(
        default=None,
        description="Human-readable voice name",
    )

    @field_validator("voice_id")
    @classmethod
    def validate_voice_id(cls, v: str) -> str:
        """Ensure voice_id is not empty."""
        return validate_non_empty_string(v, "voice_id")


class PodcastTurn(BaseModel):
    """Single turn in podcast Q&A dialogue."""

    speaker: Speaker = Field(..., description="Speaker for this turn (HOST or EXPERT)")
    text: str = Field(..., min_length=1, description="Text content for this turn")
    estimated_duration: float = Field(..., ge=0, description="Estimated duration in seconds")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Ensure text is not empty."""
        return validate_non_empty_string(v, "turn text")


class PodcastScript(BaseModel):
    """Complete podcast script with Q&A dialogue turns."""

    turns: list[PodcastTurn] = Field(..., min_length=1, description="List of dialogue turns")
    total_duration: float = Field(..., ge=0, description="Total duration in seconds")
    total_words: int = Field(..., ge=0, description="Total word count")

    @field_validator("turns")
    @classmethod
    def validate_turns(cls, v: list[PodcastTurn]) -> list[PodcastTurn]:
        """Ensure at least one turn exists."""
        if not v:
            raise ValueError("script must have at least one turn")
        return v


class ProgressStepDetails(BaseModel):
    """Detailed progress information for current step."""

    total_turns: int | None = Field(default=None, ge=0, description="Total number of dialogue turns (if applicable)")
    completed_turns: int | None = Field(default=None, ge=0, description="Number of completed turns (if applicable)")
    current_speaker: str | None = Field(default=None, description="Current speaker being processed (HOST/EXPERT)")


class PodcastGenerationInput(BaseModel):
    """Input schema for podcast generation request.

    Note: user_id is always set by the API router from the authenticated session token.
    Client-provided user_id values are ignored for security reasons.
    """

    # Valid OpenAI TTS voice IDs
    VALID_VOICE_IDS: ClassVar[set[str]] = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}

    user_id: UUID | None = Field(
        default=None,
        description=(
            "User requesting podcast generation. Always set by router from authenticated session. "
            "Client-provided values are ignored for security. Type is Optional for schema flexibility "
            "but router ensures it's always non-null before calling service layer."
        ),
    )
    collection_id: UUID = Field(..., description="Document collection to generate podcast from")
    duration: PodcastDuration = Field(..., description="Target podcast duration")
    voice_settings: VoiceSettings = Field(..., description="Voice configuration for TTS")
    title: str | None = Field(
        default=None,
        max_length=200,
        description="Optional custom title for podcast",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Optional podcast description",
    )
    format: AudioFormat = Field(default=AudioFormat.MP3, description="Desired audio output format", alias="format")
    host_voice: str = Field(default="alloy", description="Voice ID for HOST speaker")
    expert_voice: str = Field(default="onyx", description="Voice ID for EXPERT speaker")
    include_intro: bool = Field(
        default=False,
        description="Include introduction segment",
    )
    include_outro: bool = Field(
        default=False,
        description="Include conclusion/outro segment",
    )
    music_background: bool = Field(
        default=False,
        description="Add background music (future feature)",
    )

    # Advanced options
    podcast_style: str = Field(default="conversational_interview", description="Style of podcast")
    language: str = Field(default="en", description="Language for the podcast")
    complexity_level: str = Field(default="intermediate", description="Target audience complexity level")
    include_chapter_markers: bool = Field(default=False, description="Include chapter markers in podcast")
    generate_transcript: bool = Field(default=True, description="Generate transcript alongside audio")

    @field_validator("host_voice", "expert_voice")
    @classmethod
    def validate_voice_ids(cls, v: str) -> str:
        """Validate that voice IDs are valid OpenAI TTS voices."""
        if v not in cls.VALID_VOICE_IDS:
            raise ValueError(f"Invalid voice ID '{v}'. Must be one of: {', '.join(sorted(cls.VALID_VOICE_IDS))}")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        """Validate and clean title."""
        if v is not None:
            stripped = v.strip()
            if not stripped:
                return None
            return stripped
        return None

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """Validate and clean description."""
        if v is not None:
            stripped = v.strip()
            if not stripped:
                return None
            return stripped
        return None


class PodcastGenerationOutput(BaseModel):
    """Output schema for podcast generation response."""

    podcast_id: UUID = Field(..., description="Unique identifier for generated podcast")
    user_id: UUID = Field(..., description="User who owns this podcast")
    collection_id: UUID = Field(..., description="Source collection ID")
    status: PodcastStatus = Field(..., description="Current generation status")
    duration: PodcastDuration = Field(..., description="Target duration")
    format: AudioFormat = Field(..., description="Audio format")
    title: str | None = Field(default=None, description="Podcast title")
    audio_url: str | None = Field(default=None, description="URL to access generated audio (when COMPLETED)")
    transcript: str | None = Field(default=None, description="Full podcast script/transcript (when COMPLETED)")
    audio_size_bytes: int | None = Field(default=None, ge=0, description="Audio file size in bytes (when COMPLETED)")
    error_message: str | None = Field(default=None, description="Error details if FAILED")
    progress_percentage: int = Field(default=0, ge=0, le=100, description="Progress percentage (0-100)")
    current_step: str | None = Field(
        default=None,
        description="Current processing step (retrieving_content, generating_script, etc.)",
    )
    step_details: ProgressStepDetails | None = Field(default=None, description="Detailed progress for current step")
    estimated_time_remaining: int | None = Field(default=None, ge=0, description="Estimated seconds remaining")
    # Voice settings
    host_voice: str = Field(default="alloy", description="Voice ID for HOST speaker")
    expert_voice: str = Field(default="onyx", description="Voice ID for EXPERT speaker")
    # Collection information (populated by service)
    collection_name: str | None = Field(default=None, description="Name of the source collection")
    created_at: datetime = Field(..., description="Timestamp when request was created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of last status update")
    completed_at: datetime | None = Field(default=None, description="Timestamp when generation completed")

    model_config = {"from_attributes": True}


class PodcastListResponse(BaseModel):
    """Response schema for listing user's podcasts."""

    podcasts: list[PodcastGenerationOutput] = Field(..., description="List of user's podcasts")
    total_count: int = Field(..., ge=0, description="Total number of podcasts")


class ScriptParsingResult(BaseModel):
    """Result of parsing raw script text into structured turns."""

    script: PodcastScript = Field(..., description="Parsed podcast script")
    raw_text: str = Field(..., description="Original unparsed script text")
    parsing_warnings: list[str] = Field(default_factory=list, description="Any warnings during parsing")


class PodcastScriptGenerationInput(BaseModel):
    """
    Input schema for script-only generation (no audio synthesis).

    This is useful for:
    - Validating script quality before committing to TTS
    - Faster iteration (script generation ~30s vs full podcast ~90s)
    - Cost savings (skip TTS API calls during development/testing)
    - Script editing workflows (generate → review → edit → synthesize)
    """

    collection_id: UUID = Field(..., description="Collection ID to generate script from")
    user_id: UUID | None = Field(None, description="User ID (auto-filled from auth)")
    duration: PodcastDuration = Field(..., description="Target duration")
    title: str | None = Field(None, max_length=255, description="Podcast title")
    description: str | None = Field(None, max_length=1000, description="Topic or focus area for the podcast")

    # Voice settings are optional for script-only generation
    # (only needed if you want to validate against specific voice characteristics)
    voice_settings: VoiceSettings | None = Field(None, description="Optional voice configuration")

    # Advanced options (same as full podcast generation)
    podcast_style: str = Field(default="conversational_interview", description="Style of podcast")
    language: str = Field(default="en", description="Language for the podcast")
    complexity_level: str = Field(default="intermediate", description="Target audience complexity level")
    include_chapter_markers: bool = Field(default=False, description="Include chapter markers in podcast")
    generate_transcript: bool = Field(default=True, description="Generate transcript alongside audio")


class PodcastScriptOutput(BaseModel):
    """
    Output schema for script-only generation.

    Includes quality metrics to help validate the script before audio synthesis.
    """

    script_id: UUID = Field(..., description="Unique script ID for tracking")
    collection_id: UUID = Field(..., description="Source collection ID")
    user_id: UUID = Field(..., description="User who generated the script")
    title: str = Field(..., description="Script title")
    script_text: str = Field(..., description="Generated dialogue script (HOST/EXPERT format)")

    # Quality metrics
    word_count: int = Field(..., description="Actual word count in generated script")
    target_word_count: int = Field(..., description="Target word count based on duration")
    duration_minutes: int = Field(..., description="Target duration in minutes")
    estimated_duration_minutes: float = Field(..., description="Estimated actual duration (word_count / 150)")
    has_proper_format: bool = Field(..., description="Whether script has correct HOST/EXPERT format")

    # Metadata
    metadata: dict = Field(
        default_factory=dict, description="Additional metadata (has_host, has_expert, rag_results_length, etc.)"
    )
    created_at: datetime = Field(default_factory=datetime.now, description="Generation timestamp")


class PodcastAudioGenerationInput(BaseModel):
    """
    Input schema for generating audio from an existing script (no script generation).

    Use Cases:
    - Generate audio from previously generated script
    - Generate audio from user-edited script
    - Re-generate audio with different voices/settings
    - Skip LLM script generation step for faster/cheaper processing

    Workflow:
    1. POST /generate-script → Get script
    2. User reviews/edits script (optional)
    3. POST /script-to-audio → Convert to audio

    Cost: ~$0.05-0.80 (TTS only, no LLM)
    Time: ~30-90 seconds (depending on duration)
    """

    # Valid OpenAI TTS voice IDs
    VALID_VOICE_IDS: ClassVar[set[str]] = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}

    user_id: UUID | None = Field(default=None, description="User ID (auto-filled from auth token by router)")
    collection_id: UUID = Field(..., description="Collection ID for tracking/permissions")
    script_text: str = Field(..., min_length=100, description="Podcast script in HOST/EXPERT format")
    title: str = Field(..., max_length=200, description="Podcast title")
    duration: PodcastDuration = Field(..., description="Target podcast duration (for validation)")

    # Audio settings
    host_voice: str = Field(default="alloy", description="Voice ID for HOST speaker")
    expert_voice: str = Field(default="onyx", description="Voice ID for EXPERT speaker")
    audio_format: AudioFormat = Field(default=AudioFormat.MP3, description="Output audio format")

    # Optional metadata
    description: str | None = Field(default=None, max_length=500, description="Optional podcast description")
    include_intro: bool = Field(default=False, description="Include introduction segment")
    include_outro: bool = Field(default=False, description="Include conclusion/outro segment")

    @field_validator("host_voice", "expert_voice")
    @classmethod
    def validate_voice_ids(cls, v: str) -> str:
        """Validate that voice IDs are valid OpenAI TTS voices."""
        if v not in cls.VALID_VOICE_IDS:
            raise ValueError(f"Invalid voice ID '{v}'. Must be one of: {', '.join(sorted(cls.VALID_VOICE_IDS))}")
        return v

    @field_validator("script_text")
    @classmethod
    def validate_script_format(cls, v: str) -> str:
        """Validate that script has proper HOST/EXPERT format."""
        if "HOST:" not in v and "Host:" not in v:
            raise ValueError("Script must contain HOST speaker turns")
        if "EXPERT:" not in v and "Expert:" not in v:
            raise ValueError("Script must contain EXPERT speaker turns")
        return v
