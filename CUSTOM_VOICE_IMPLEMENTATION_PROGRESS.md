# Custom Voice Upload Feature - Implementation Progress

**Issue**: #394 - Add support to generate podcast in specific voices

## Overview

This feature enables users to upload custom voice samples and use them for podcast generation, allowing personalized voice cloning for HOST and EXPERT speakers.

## Architecture

### Current System
- **TTS Provider**: OpenAI TTS (6 preset voices: alloy, echo, fable, onyx, nova, shimmer)
- **Voice Selection**: Hardcoded voice IDs in `PodcastGenerationInput`
- **Audio Generation**: `AudioProviderBase` with `OpenAIAudioProvider` implementation

### New System
- **Custom Voices**: User-uploaded voice samples stored in database
- **Voice Processing**: Integration with voice cloning providers (ElevenLabs, Play.ht, Resemble.ai)
- **Flexible Selection**: Users can choose between preset voices and custom voices
- **Storage**: Voice samples stored alongside podcast audio files

---

## ✅ Completed Tasks

### 1. Database Model (`backend/rag_solution/models/voice.py`)

**Fields**:
- `voice_id` (UUID, primary key)
- `user_id` (UUID, foreign key to users)
- `name` (str, required) - Human-readable voice name
- `description` (text, optional) - Voice description
- `gender` (str) - male/female/neutral classification
- `status` (str) - uploading/processing/ready/failed
- `provider_voice_id` (str, optional) - Provider-specific voice ID after cloning
- `provider_name` (str, optional) - TTS provider name
- `sample_file_url` (str, required) - Path to voice sample file
- `sample_file_size` (int, optional) - File size in bytes
- `quality_score` (int, optional) - Voice quality (0-100 scale)
- `error_message` (text, optional) - Error details if failed
- `times_used` (int, default 0) - Usage tracking
- `created_at`, `updated_at`, `processed_at` (datetime) - Timestamps

**Relationships**:
- `user` - Many-to-one relationship with User model
- Added `voices` relationship to User model

### 2. Pydantic Schemas (`backend/rag_solution/schemas/voice_schema.py`)

**Classes**:
- `VoiceUploadInput` - Schema for voice upload request
- `VoiceOutput` - Schema for voice information response
- `VoiceListResponse` - Schema for listing user's voices
- `VoiceProcessingInput` - Schema for processing voice with TTS provider
- `VoiceUpdateInput` - Schema for updating voice metadata

**Enums**:
- `VoiceStatus` - uploading/processing/ready/failed
- `VoiceGender` - male/female/neutral

**Validation**:
- Name must be non-empty, max 200 characters
- Gender must be valid value
- Provider must be supported (elevenlabs/playht/resemble)

---

## 📋 Remaining Tasks

### 3. Voice Sample Storage System
**Files to create**:
- `backend/rag_solution/services/storage/voice_storage.py`
- Similar to `AudioStorageBase` pattern used for podcasts
- Support local file storage initially (MinIO/S3 later)

**Functions needed**:
- `store_voice_sample(user_id, voice_id, audio_data, format) -> str`
- `delete_voice_sample(user_id, voice_id) -> bool`
- `get_voice_sample_path(user_id, voice_id) -> Path`

### 4. Voice Repository
**File**: `backend/rag_solution/repository/voice_repository.py`

**Functions needed**:
- `create(user_id, name, sample_file_url, ...) -> Voice`
- `get_by_id(voice_id) -> Voice | None`
- `get_by_user(user_id, limit, offset) -> list[Voice]`
- `update(voice_id, **kwargs) -> Voice`
- `delete(voice_id) -> bool`
- `update_status(voice_id, status, ...) -> Voice`
- `increment_usage(voice_id) -> None`

### 5. Voice Service
**File**: `backend/rag_solution/services/voice_service.py`

**Functions needed**:
- `upload_voice(voice_input, audio_file) -> VoiceOutput`
- `process_voice(voice_id, provider_name) -> VoiceOutput`
- `list_user_voices(user_id, limit, offset) -> VoiceListResponse`
- `get_voice(voice_id, user_id) -> VoiceOutput`
- `update_voice(voice_id, user_id, update_input) -> VoiceOutput`
- `delete_voice(voice_id, user_id) -> bool`

### 6. Voice API Endpoints
**File**: `backend/rag_solution/router/voice_router.py`

**Endpoints**:
- `POST /api/voices/upload` - Upload voice sample with metadata
- `POST /api/voices/{voice_id}/process` - Process voice with TTS provider
- `GET /api/voices` - List user's voices
- `GET /api/voices/{voice_id}` - Get voice details
- `PATCH /api/voices/{voice_id}` - Update voice metadata
- `DELETE /api/voices/{voice_id}` - Delete voice
- `GET /api/voices/{voice_id}/sample` - Download/stream voice sample

### 7. ElevenLabs Audio Provider
**File**: `backend/rag_solution/generation/audio/elevenlabs_audio.py`

**Features**:
- Implement `AudioProviderBase` interface
- Support custom voice IDs from ElevenLabs API
- Voice cloning API integration
- Multi-voice dialogue generation

**Integration**:
- Update `AudioProviderFactory` to register ElevenLabs
- Add ElevenLabs API key to settings

### 8. Update Podcast Schemas
**Changes to**: `backend/rag_solution/schemas/podcast_schema.py`

**Modifications**:
- `host_voice` and `expert_voice` fields should accept both preset voices and custom voice UUIDs
- Add `is_custom_voice` flag or voice type discriminator
- Update validation to check custom voice access

### 9. Integrate Custom Voices into Podcast Generation
**Changes to**: `backend/rag_solution/services/podcast_service.py`

**Modifications**:
- `_generate_audio()` - Resolve custom voice IDs to provider voice IDs
- Validate user has access to custom voices
- Track voice usage (increment `times_used`)
- Handle mixed scenarios (one custom + one preset voice)

### 10. Database Migration
**File**: `backend/rag_solution/migrations/versions/XXXX_add_voices_table.py`

**Changes**:
- Create `voices` table
- Add indexes on `user_id` and `status`
- Add foreign key constraint to users table

### 11. Tests

**Unit Tests** (`backend/tests/unit/test_voice_*.py`):
- `test_voice_repository.py` - CRUD operations
- `test_voice_service.py` - Business logic
- `test_voice_schemas.py` - Validation

**Integration Tests** (`backend/tests/integration/test_voice_integration.py`):
- Full voice upload → processing → usage workflow
- Custom voice podcast generation end-to-end

### 12. API Documentation
- Update OpenAPI/Swagger docs with voice endpoints
- Add examples for voice upload and usage
- Document supported TTS providers

---

## Technical Decisions

### 1. TTS Provider Support
**Decision**: Start with ElevenLabs for custom voice cloning

**Rationale**:
- ElevenLabs has robust voice cloning API
- Good quality output with minimal samples
- Supports multiple voice cloning strategies
- Well-documented API

**Alternatives Considered**:
- Play.ht - Good but more expensive
- Resemble.ai - Good but less popular
- OpenAI - Does NOT support custom voice cloning

### 2. Voice Sample Storage
**Decision**: Use same storage backend as podcasts (local/MinIO)

**Rationale**:
- Reuse existing storage infrastructure
- Consistent patterns across the codebase
- Easy to extend to S3/R2 later

### 3. Voice Processing Model
**Decision**: Async background processing

**Rationale**:
- Voice cloning can take 30-120 seconds
- Non-blocking user experience
- Status tracking via database
- Similar to podcast generation pattern

### 4. Voice ID Resolution
**Decision**: Store provider_voice_id in database

**Rationale**:
- Avoid repeated API calls to TTS provider
- Faster podcast generation
- Cache provider-specific IDs
- Support multiple TTS providers per voice (future)

---

## API Usage Examples

### Upload Voice Sample

```bash
curl -X POST http://localhost:8000/api/voices/upload \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: multipart/form-data" \
  -F "name=My Custom Voice" \
  -F "description=Professional narrator voice" \
  -F "gender=female" \
  -F "audio_file=@voice_sample.mp3"
```

Response:
```json
{
  "voice_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "uploading",
  "name": "My Custom Voice",
  "description": "Professional narrator voice",
  "gender": "female",
  ...
}
```

### Process Voice with Provider

```bash
curl -X POST http://localhost:8000/api/voices/{voice_id}/process \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_name": "elevenlabs"
  }'
```

### Generate Podcast with Custom Voice

```bash
curl -X POST http://localhost:8000/api/podcasts/generate \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_id": "col-uuid",
    "duration": 15,
    "host_voice": "custom:123e4567-e89b-12d3-a456-426614174000",
    "expert_voice": "alloy",
    ...
  }'
```

---

## Configuration

### New Environment Variables

```bash
# ElevenLabs API
ELEVENLABS_API_KEY=your_api_key_here
ELEVENLABS_MODEL=eleven_monolingual_v1

# Voice Storage
VOICE_STORAGE_BACKEND=local  # or minio, s3
VOICE_LOCAL_STORAGE_PATH=./storage/voices
VOICE_MAX_FILE_SIZE_MB=10
VOICE_ALLOWED_FORMATS=mp3,wav,m4a,flac

# Voice Processing
VOICE_MAX_PER_USER=10
VOICE_PROCESSING_TIMEOUT_SECONDS=300
```

---

## Next Steps

1. Review this implementation plan
2. Implement voice storage system
3. Create voice repository and service
4. Build voice API endpoints
5. Add ElevenLabs provider
6. Update podcast generation flow
7. Write comprehensive tests
8. Create database migration
9. Update documentation

---

## Estimated Timeline

- **Voice Storage + Repository**: 2-3 hours
- **Voice Service + API**: 3-4 hours
- **ElevenLabs Provider**: 2-3 hours
- **Podcast Integration**: 2-3 hours
- **Tests**: 3-4 hours
- **Migration + Docs**: 1-2 hours

**Total**: ~15-20 hours for complete implementation

---

## Questions for Review

1. Should we support multiple voice samples per voice (for better cloning quality)?
2. What should be the max file size for voice samples?
3. Should we auto-process voices after upload or require explicit processing?
4. Should we support voice sample preview (like podcast voice preview)?
5. What happens to podcasts when a custom voice is deleted?
