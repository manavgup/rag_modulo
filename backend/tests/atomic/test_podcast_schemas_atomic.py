"""TDD Red Phase: Atomic tests for podcast schemas and validation.

Atomic tests focus on the smallest units of functionality - individual
data structures, validation rules, enums, and basic field validation.

These tests define the schema structure for podcast generation from Issue #240.
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

# These imports will fail initially - that's expected for TDD Red phase
from rag_solution.schemas.podcast_schema import (
    AudioFormat,
    PodcastDuration,
    PodcastGenerationInput,
    PodcastGenerationOutput,
    PodcastStatus,
    VoiceGender,
    VoiceSettings,
)


@pytest.mark.atomic
class TestPodcastEnums:
    """Atomic tests for podcast enum values."""

    def test_podcast_status_enum_values(self) -> None:
        """Atomic: Test podcast status enum has correct string values."""
        assert PodcastStatus.QUEUED == "queued"
        assert PodcastStatus.GENERATING == "generating"
        assert PodcastStatus.COMPLETED == "completed"
        assert PodcastStatus.FAILED == "failed"
        assert PodcastStatus.CANCELLED == "cancelled"

    def test_audio_format_enum_values(self) -> None:
        """Atomic: Test audio format enum has correct string values."""
        assert AudioFormat.MP3 == "mp3"
        assert AudioFormat.WAV == "wav"
        assert AudioFormat.OGG == "ogg"
        assert AudioFormat.FLAC == "flac"

    def test_voice_gender_enum_values(self) -> None:
        """Atomic: Test voice gender enum has correct string values."""
        assert VoiceGender.MALE == "male"
        assert VoiceGender.FEMALE == "female"
        assert VoiceGender.NEUTRAL == "neutral"

    def test_podcast_duration_enum_values(self) -> None:
        """Atomic: Test podcast duration enum has correct minute values."""
        assert PodcastDuration.SHORT == 5
        assert PodcastDuration.MEDIUM == 15
        assert PodcastDuration.LONG == 30
        assert PodcastDuration.EXTENDED == 60


@pytest.mark.atomic
class TestVoiceSettings:
    """Atomic tests for voice settings data structure."""

    def test_voice_settings_minimal_valid(self) -> None:
        """Atomic: Voice settings created with only required fields."""
        voice = VoiceSettings(
            voice_id="voice-123",
            gender=VoiceGender.FEMALE,
        )
        assert voice.voice_id == "voice-123"
        assert voice.gender == VoiceGender.FEMALE
        assert voice.speed == 1.0  # default
        assert voice.pitch == 1.0  # default

    def test_voice_settings_all_fields(self) -> None:
        """Atomic: Voice settings created with all fields."""
        voice = VoiceSettings(
            voice_id="voice-456",
            gender=VoiceGender.MALE,
            speed=1.2,
            pitch=0.9,
            language="en-US",
            name="Professional Voice",
        )
        assert voice.voice_id == "voice-456"
        assert voice.gender == VoiceGender.MALE
        assert voice.speed == 1.2
        assert voice.pitch == 0.9
        assert voice.language == "en-US"
        assert voice.name == "Professional Voice"

    def test_voice_settings_speed_validation_min(self) -> None:
        """Atomic: Voice speed must be >= 0.5."""
        with pytest.raises(ValidationError) as exc_info:
            VoiceSettings(
                voice_id="voice-123",
                gender=VoiceGender.FEMALE,
                speed=0.4,
            )
        assert "speed" in str(exc_info.value).lower()

    def test_voice_settings_speed_validation_max(self) -> None:
        """Atomic: Voice speed must be <= 2.0."""
        with pytest.raises(ValidationError) as exc_info:
            VoiceSettings(
                voice_id="voice-123",
                gender=VoiceGender.FEMALE,
                speed=2.1,
            )
        assert "speed" in str(exc_info.value).lower()

    def test_voice_settings_pitch_validation_min(self) -> None:
        """Atomic: Voice pitch must be >= 0.5."""
        with pytest.raises(ValidationError) as exc_info:
            VoiceSettings(
                voice_id="voice-123",
                gender=VoiceGender.FEMALE,
                pitch=0.4,
            )
        assert "pitch" in str(exc_info.value).lower()

    def test_voice_settings_pitch_validation_max(self) -> None:
        """Atomic: Voice pitch must be <= 2.0."""
        with pytest.raises(ValidationError) as exc_info:
            VoiceSettings(
                voice_id="voice-123",
                gender=VoiceGender.FEMALE,
                pitch=2.1,
            )
        assert "pitch" in str(exc_info.value).lower()

    def test_voice_settings_voice_id_not_empty(self) -> None:
        """Atomic: Voice ID cannot be empty string."""
        with pytest.raises(ValidationError) as exc_info:
            VoiceSettings(
                voice_id="",
                gender=VoiceGender.FEMALE,
            )
        assert "voice_id" in str(exc_info.value).lower()


@pytest.mark.atomic
class TestPodcastGenerationInput:
    """Atomic tests for podcast generation input schema."""

    def test_podcast_input_minimal_valid(self) -> None:
        """Atomic: Podcast input created with minimal required fields."""
        user_id = uuid4()
        collection_id = uuid4()

        podcast_input = PodcastGenerationInput(
            user_id=user_id,
            collection_id=collection_id,
            duration=PodcastDuration.MEDIUM,
            voice_settings=VoiceSettings(
                voice_id="voice-123",
                gender=VoiceGender.FEMALE,
            ),
        )
        assert podcast_input.user_id == user_id
        assert podcast_input.collection_id == collection_id
        assert podcast_input.duration == PodcastDuration.MEDIUM
        assert podcast_input.title is None
        assert podcast_input.description is None
        assert podcast_input.format == AudioFormat.MP3  # default

    def test_podcast_input_all_fields(self) -> None:
        """Atomic: Podcast input created with all optional fields."""
        user_id = uuid4()
        collection_id = uuid4()

        podcast_input = PodcastGenerationInput(
            user_id=user_id,
            collection_id=collection_id,
            duration=PodcastDuration.LONG,
            voice_settings=VoiceSettings(
                voice_id="voice-456",
                gender=VoiceGender.MALE,
            ),
            title="AI Innovations Podcast",
            description="Exploring recent advances in AI",
            format=AudioFormat.WAV,
            include_intro=True,
            include_outro=True,
            music_background=True,
        )
        assert podcast_input.title == "AI Innovations Podcast"
        assert podcast_input.description == "Exploring recent advances in AI"
        assert podcast_input.format == AudioFormat.WAV
        assert podcast_input.include_intro is True
        assert podcast_input.include_outro is True
        assert podcast_input.music_background is True

    def test_podcast_input_user_id_optional(self) -> None:
        """Atomic: User ID is optional in schema (filled by router from auth)."""
        # user_id is optional in schema - router fills it from authenticated session
        podcast_input = PodcastGenerationInput(
            collection_id=uuid4(),
            duration=PodcastDuration.MEDIUM,
            voice_settings=VoiceSettings(
                voice_id="voice-123",
                gender=VoiceGender.FEMALE,
            ),
            host_voice="alloy",
            expert_voice="onyx",
        )
        assert podcast_input.user_id is None  # Not set in schema, router will set it

    def test_podcast_input_collection_id_required(self) -> None:
        """Atomic: Collection ID is required."""
        with pytest.raises(ValidationError) as exc_info:
            PodcastGenerationInput(  # type: ignore[call-arg]
                user_id=uuid4(),
                duration=PodcastDuration.MEDIUM,
                voice_settings=VoiceSettings(
                    voice_id="voice-123",
                    gender=VoiceGender.FEMALE,
                ),
                host_voice="alloy",
                expert_voice="onyx",
            )
        assert "collection_id" in str(exc_info.value).lower()

    def test_podcast_input_duration_required(self) -> None:
        """Atomic: Duration is required."""
        with pytest.raises(ValidationError) as exc_info:
            PodcastGenerationInput(  # type: ignore[call-arg]
                user_id=uuid4(),
                collection_id=uuid4(),
                voice_settings=VoiceSettings(
                    voice_id="voice-123",
                    gender=VoiceGender.FEMALE,
                ),
                host_voice="alloy",
                expert_voice="onyx",
            )
        assert "duration" in str(exc_info.value).lower()

    def test_podcast_input_voice_settings_required(self) -> None:
        """Atomic: Voice settings are required."""
        with pytest.raises(ValidationError) as exc_info:
            PodcastGenerationInput(  # type: ignore[call-arg]
                user_id=uuid4(),
                collection_id=uuid4(),
                duration=PodcastDuration.MEDIUM,
                host_voice="alloy",
                expert_voice="onyx",
            )
        assert "voice_settings" in str(exc_info.value).lower()

    def test_podcast_input_title_max_length(self) -> None:
        """Atomic: Title has maximum length of 200 characters."""
        with pytest.raises(ValidationError) as exc_info:
            PodcastGenerationInput(
                user_id=uuid4(),
                collection_id=uuid4(),
                duration=PodcastDuration.MEDIUM,
                voice_settings=VoiceSettings(
                    voice_id="voice-123",
                    gender=VoiceGender.FEMALE,
                ),
                title="A" * 201,  # Exceeds max length
            )
        assert "title" in str(exc_info.value).lower()


@pytest.mark.atomic
class TestPodcastGenerationOutput:
    """Atomic tests for podcast generation output schema."""

    def test_podcast_output_minimal_valid(self) -> None:
        """Atomic: Podcast output created with minimal fields."""
        podcast_id = uuid4()
        user_id = uuid4()
        collection_id = uuid4()

        output = PodcastGenerationOutput(
            podcast_id=podcast_id,
            user_id=user_id,
            collection_id=collection_id,
            status=PodcastStatus.QUEUED,
            duration=PodcastDuration.MEDIUM,
            format=AudioFormat.MP3,
            created_at=datetime.utcnow(),
        )
        assert output.podcast_id == podcast_id
        assert output.user_id == user_id
        assert output.collection_id == collection_id
        assert output.status == PodcastStatus.QUEUED
        assert output.audio_url is None
        assert output.transcript is None
        assert output.error_message is None

    def test_podcast_output_completed_with_url(self) -> None:
        """Atomic: Completed podcast has audio URL."""
        output = PodcastGenerationOutput(
            podcast_id=uuid4(),
            user_id=uuid4(),
            collection_id=uuid4(),
            status=PodcastStatus.COMPLETED,
            duration=PodcastDuration.MEDIUM,
            format=AudioFormat.MP3,
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            audio_url="https://storage.example.com/podcasts/abc123.mp3",
            audio_size_bytes=5242880,  # 5MB
            transcript="This is the podcast transcript...",
        )
        assert output.status == PodcastStatus.COMPLETED
        assert output.audio_url == "https://storage.example.com/podcasts/abc123.mp3"
        assert output.audio_size_bytes == 5242880
        assert output.transcript == "This is the podcast transcript..."
        assert output.completed_at is not None

    def test_podcast_output_failed_with_error(self) -> None:
        """Atomic: Failed podcast has error message."""
        output = PodcastGenerationOutput(
            podcast_id=uuid4(),
            user_id=uuid4(),
            collection_id=uuid4(),
            status=PodcastStatus.FAILED,
            duration=PodcastDuration.MEDIUM,
            format=AudioFormat.MP3,
            created_at=datetime.utcnow(),
            error_message="Insufficient content in collection for podcast generation",
        )
        assert output.status == PodcastStatus.FAILED
        assert output.error_message is not None
        assert "content" in output.error_message.lower()

    def test_podcast_output_id_is_uuid(self) -> None:
        """Atomic: Podcast ID must be valid UUID."""
        podcast_id = uuid4()
        output = PodcastGenerationOutput(
            podcast_id=podcast_id,
            user_id=uuid4(),
            collection_id=uuid4(),
            status=PodcastStatus.QUEUED,
            duration=PodcastDuration.MEDIUM,
            format=AudioFormat.MP3,
            created_at=datetime.utcnow(),
        )
        assert isinstance(output.podcast_id, UUID)
        assert str(output.podcast_id) == str(podcast_id)
