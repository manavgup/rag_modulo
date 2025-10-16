# Custom Voice Upload Feature - Implementation Progress

**Issue**: #394 - Add support to generate podcast in specific voices

## Overview

This feature enables users to upload custom voice samples and use them for podcast generation, allowing personalized voice cloning for HOST and EXPERT speakers.

## 🎯 Implementation Strategy: Phased Approach

### Phase 1: ElevenLabs Integration (Current Phase) 🚀
**Goal**: Fast time to market with proven cloud-based voice cloning

**Why Start with ElevenLabs**:
- ✅ **Fast Implementation**: Well-documented REST API, no infrastructure setup
- ✅ **High Quality**: Industry-leading voice cloning (5/5 quality)
- ✅ **Reliable**: Managed service with SLA guarantees
- ✅ **Proven**: Used by thousands of production applications
- ✅ **Quick Validation**: Test user adoption before infrastructure investment

**Timeline**: ~15-20 hours for complete implementation

---

### Phase 2: F5-TTS Self-Hosted Option (Future) 🔧
**Goal**: Cost optimization and data sovereignty for power users

**Why Add F5-TTS** (based on [comprehensive analysis](https://github.com/manavgup/rag_modulo/issues/394#issuecomment-3395705696)):
- ✅ **Zero-shot cloning**: Instant voice cloning (no training wait!)
- ✅ **Cost Savings**: 20-80% cheaper than ElevenLabs at scale (50+ podcasts/month)
- ✅ **Privacy**: Voice samples stay on our infrastructure
- ✅ **Control**: We manage quality, latency, and availability
- ✅ **No vendor lock-in**: Open-source (MIT license)
- ✅ **Customization**: Can fine-tune model for our domain

**F5-TTS Model Specs**:
- **Zero-shot voice cloning** (instant embedding extraction)
- **Flow Matching** architecture for high quality
- **10-20x realtime** inference on GPU
- **Multilingual** support (English, Chinese, more)
- **4GB-6GB VRAM** requirement (RTX 3060+)
- **Quality**: 4/5 vs ElevenLabs' 5/5 (marginal difference, acceptable for podcasts)

**Timeline**: ~20-25 hours (Docker setup, GPU config, model integration)

---

### Runtime Provider Selection
Users can choose their preferred provider based on needs:
- **ElevenLabs**: Best quality, managed service, pay-per-use
- **F5-TTS**: Cost-effective, privacy-focused, self-hosted

**Implementation**:
```python
# User can select provider when processing voice
POST /api/voices/{voice_id}/process
{
    "provider_name": "elevenlabs"  # or "f5-tts"
}

# System configuration determines available providers
VOICE_TTS_PROVIDERS=elevenlabs,f5-tts
VOICE_DEFAULT_PROVIDER=elevenlabs
```

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

### 7. ElevenLabs Audio Provider (Phase 1) 🚀
**File**: `backend/rag_solution/generation/audio/elevenlabs_audio.py`

**Features**:
- Implement `AudioProviderBase` interface
- Voice cloning via ElevenLabs API
- Support for instant voice cloning (Professional Voice Cloning)
- Multi-voice dialogue generation
- Voice ID management and caching

**API Integration**:
- `/v1/voices/add` - Create cloned voice from sample
- `/v1/text-to-speech/{voice_id}` - Generate audio with custom voice
- `/v1/voices/{voice_id}` - Get voice details
- `/v1/voices/{voice_id}` - Delete voice (cleanup)

**Integration**:
- Update `AudioProviderFactory` to register ElevenLabs provider
- Add ElevenLabs API key to environment configuration
- Implement retry logic and error handling
- Track API usage and costs

---

### 8. F5-TTS Audio Provider (Phase 2 - Future) 🔧
**File**: `backend/rag_solution/generation/audio/f5_tts_audio.py`

**Status**: Planned for Phase 2

**Features**:
- Implement `AudioProviderBase` interface
- Support zero-shot voice cloning from uploaded samples
- Voice embedding extraction (instant, no training!)
- Multi-voice dialogue generation
- Local model inference (no API calls)
- GPU-accelerated synthesis (10-20x realtime)

**Integration**:
- Update `AudioProviderFactory` to register F5-TTS provider
- Add F5-TTS Docker service to docker-compose (GPU-enabled)
- Configure model path, GPU settings, and voice embedding storage
- Create FastAPI microservice for /clone-voice and /synthesize endpoints

### 9. Update Podcast Schemas (Phase 1)
**Changes to**: `backend/rag_solution/schemas/podcast_schema.py`

**Modifications**:
- `host_voice` and `expert_voice` fields should accept both preset voices and custom voice UUIDs
- Add `is_custom_voice` flag or voice type discriminator
- Update validation to check custom voice access

### 10. Integrate Custom Voices into Podcast Generation (Phase 1)
**Changes to**: `backend/rag_solution/services/podcast_service.py`

**Modifications**:
- `_generate_audio()` - Resolve custom voice IDs to provider voice IDs
- Validate user has access to custom voices
- Track voice usage (increment `times_used`)
- Handle mixed scenarios (one custom + one preset voice)

### 11. Database Migration (Phase 1)
**File**: `backend/rag_solution/migrations/versions/XXXX_add_voices_table.py`

**Changes**:
- Create `voices` table
- Add indexes on `user_id` and `status`
- Add foreign key constraint to users table

### 12. Tests (Phase 1)

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
# Voice TTS Providers (Phase 1: ElevenLabs, Phase 2: F5-TTS)
VOICE_TTS_PROVIDERS=elevenlabs  # Comma-separated: elevenlabs,f5-tts
VOICE_DEFAULT_PROVIDER=elevenlabs

# ElevenLabs Configuration (Phase 1) 🚀
ELEVENLABS_API_KEY=<your-api-key>  # Get from elevenlabs.io
ELEVENLABS_API_BASE_URL=https://api.elevenlabs.io/v1
ELEVENLABS_MODEL_ID=eleven_multilingual_v2  # Voice cloning model
ELEVENLABS_VOICE_SETTINGS_STABILITY=0.5
ELEVENLABS_VOICE_SETTINGS_SIMILARITY=0.75
ELEVENLABS_REQUEST_TIMEOUT_SECONDS=30
ELEVENLABS_MAX_RETRIES=3

# F5-TTS Configuration (Phase 2 - Future) 🔧
F5_TTS_SERVICE_URL=http://localhost:8001  # F5-TTS microservice URL
F5_TTS_MODEL_PATH=/models/f5-tts  # Model storage path
F5_TTS_GPU_ENABLED=true  # Use GPU for inference
F5_TTS_LANGUAGE=en  # Default language
F5_TTS_CACHE_DIR=/cache  # Voice embedding cache

# Voice Storage (Both Phases)
VOICE_STORAGE_BACKEND=local  # or minio, s3
VOICE_LOCAL_STORAGE_PATH=./storage/voices
VOICE_MAX_FILE_SIZE_MB=10
VOICE_ALLOWED_FORMATS=mp3,wav,m4a,flac,ogg

# Voice Processing (Both Phases)
VOICE_MAX_PER_USER=10
VOICE_PROCESSING_TIMEOUT_SECONDS=30  # ElevenLabs cloning time
VOICE_MIN_SAMPLE_DURATION_SECONDS=5  # Minimum voice sample length
VOICE_MAX_SAMPLE_DURATION_SECONDS=300  # Maximum 5 minutes
```

---

## Next Steps

### Phase 1: ElevenLabs Integration (Current) 🚀

1. ✅ ~~Voice storage system~~ (Completed - integrated into FileManagementService)
2. ✅ ~~Voice repository~~ (Completed - voice_repository.py)
3. ✅ ~~Database model and schemas~~ (Completed)
4. 🚧 Create voice service layer
5. 🚧 Build voice API endpoints (7 endpoints)
6. 🚧 Add ElevenLabs audio provider
7. 🚧 Update podcast schemas for custom voices
8. 🚧 Integrate custom voices into podcast generation
9. 🚧 Write comprehensive tests
10. 🚧 Create database migration
11. 🚧 Update API documentation

**Phase 1 Timeline**: ~12-15 hours remaining

### Phase 2: F5-TTS Self-Hosted (Future) 🔧

1. Set up F5-TTS Docker service with GPU support
2. Create F5-TTS audio provider implementation
3. Build FastAPI microservice for voice cloning
4. Implement voice embedding caching
5. Add provider selection UI in frontend
6. Write tests for F5-TTS provider
7. Update documentation with deployment guide
8. Performance benchmarking and optimization

**Phase 2 Timeline**: ~20-25 hours

---

## Estimated Timeline

### Phase 1 (ElevenLabs)
- **Voice Service + API**: 3-4 hours
- **ElevenLabs Provider**: 2-3 hours
- **Podcast Integration**: 2-3 hours
- **Tests**: 3-4 hours
- **Migration + Docs**: 1-2 hours

**Total Phase 1**: ~12-15 hours remaining for complete implementation

### Phase 2 (F5-TTS - Future)
- **Docker + GPU Setup**: 4-5 hours
- **F5-TTS Provider**: 5-6 hours
- **Microservice**: 4-5 hours
- **Tests**: 3-4 hours
- **Docs**: 2-3 hours

**Total Phase 2**: ~20-25 hours for self-hosted option

---

## Questions for Review

1. Should we support multiple voice samples per voice (for better cloning quality)?
2. What should be the max file size for voice samples?
3. Should we auto-process voices after upload or require explicit processing?
4. Should we support voice sample preview (like podcast voice preview)?
5. What happens to podcasts when a custom voice is deleted?
