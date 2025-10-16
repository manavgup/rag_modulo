# Custom Voice API

## Overview

The Custom Voice API allows users to upload voice samples and use them for personalized podcast generation. This feature integrates with voice cloning providers to create custom voices that can be used alongside preset TTS voices.

## Implementation Strategy

### Phase 1: ElevenLabs Integration (Current) 🚀

**Focus**: Fast time to market with proven cloud-based voice cloning

**Available Providers**:
- **ElevenLabs**: Industry-leading voice cloning (5/5 quality), managed service

**Timeline**: Phase 1 is currently being implemented (~12-15 hours remaining)

### Phase 2: Self-Hosted Option (Future) 🔧

**Focus**: Cost optimization and data sovereignty for power users

**Planned Providers**:
- **F5-TTS**: Self-hosted voice cloning with zero-shot capabilities
  - 20-80% cheaper than ElevenLabs at scale (50+ podcasts/month)
  - Privacy-focused (voice samples stay on-premise)
  - Open-source (MIT license)

**Timeline**: Phase 2 planned for future release (~20-25 hours)

### Runtime Provider Selection

Users can choose their preferred provider when processing voices:

```json
POST /api/voices/{voice_id}/process
{
  "provider_name": "elevenlabs"  // Phase 1
  // "provider_name": "f5-tts"   // Phase 2 (future)
}
```

---

## Architecture

### Components

```
1. Voice Upload
   └─> FileManagementService → Store voice sample files

2. Voice Processing
   └─> TTS Provider API → Clone voice from sample

3. Voice Storage
   └─> Voice Database → Track voice metadata and status

4. Voice Usage
   └─> Podcast Generation → Use custom or preset voices
```

### Database Model

**Table**: `voices`

| Field | Type | Description |
|-------|------|-------------|
| voice_id | UUID | Primary key |
| user_id | UUID | Foreign key to users |
| name | VARCHAR(200) | Human-readable voice name |
| description | TEXT | Optional voice description |
| gender | VARCHAR(20) | male/female/neutral |
| status | VARCHAR(20) | uploading/processing/ready/failed |
| provider_voice_id | VARCHAR(200) | Provider-specific voice ID (after cloning) |
| provider_name | VARCHAR(50) | TTS provider name (elevenlabs, playht, resemble) |
| sample_file_url | VARCHAR(500) | Path to voice sample file |
| sample_file_size | INTEGER | File size in bytes |
| quality_score | INTEGER | Voice quality (0-100) |
| error_message | TEXT | Error details if failed |
| times_used | INTEGER | Usage counter |
| created_at | TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | Last update time |
| processed_at | TIMESTAMP | Processing completion time |

### Voice File Storage

**Structure**: `{storage_path}/{user_id}/voices/{voice_id}/sample.{format}`

**Supported Formats**:
- mp3
- wav
- m4a
- flac
- ogg

## API Endpoints

### 1. Upload Voice Sample

Upload a voice sample file for custom voice creation.

**Endpoint**: `POST /api/voices/upload`

**Authentication**: Required (JWT token)

**Content-Type**: `multipart/form-data`

**Form Fields**:
```
name: string (required, 1-200 chars)
description: string (optional, max 1000 chars)
gender: string (required, one of: male, female, neutral)
audio_file: file (required, max 10MB)
```

**Request Example**:
```bash
curl -X POST http://localhost:8000/api/voices/upload \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -F "name=Professional Narrator Voice" \
  -F "description=Clear, authoritative voice for podcasts" \
  -F "gender=male" \
  -F "audio_file=@voice_sample.mp3"
```

**Response** (201 Created):
```json
{
  "voice_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "ee76317f-3b6f-4fea-8b74-56483731f58c",
  "name": "Professional Narrator Voice",
  "description": "Clear, authoritative voice for podcasts",
  "gender": "male",
  "status": "uploading",
  "provider_voice_id": null,
  "provider_name": null,
  "sample_file_url": "/api/voices/123e4567-e89b-12d3-a456-426614174000/sample",
  "sample_file_size": 2457600,
  "quality_score": null,
  "error_message": null,
  "times_used": 0,
  "created_at": "2025-10-13T10:30:00Z",
  "updated_at": "2025-10-13T10:30:00Z",
  "processed_at": null
}
```

**Error Responses**:
- `400 Bad Request`: Invalid input (empty name, unsupported format, file too large)
- `401 Unauthorized`: Missing or invalid JWT token
- `413 Payload Too Large`: File exceeds size limit
- `415 Unsupported Media Type`: Invalid audio format

### 2. Process Voice with TTS Provider

Process an uploaded voice sample with a TTS provider for voice cloning.

**Endpoint**: `POST /api/voices/{voice_id}/process`

**Authentication**: Required (JWT token)

**Content-Type**: `application/json`

**Request Body**:
```json
{
  "provider_name": "elevenlabs"
}
```

**Supported Providers** (Phase 1):
- `elevenlabs` - ElevenLabs voice cloning (available now)

**Future Providers** (Phase 2):
- `f5-tts` - Self-hosted F5-TTS voice cloning (planned)

**Request Example**:
```bash
curl -X POST http://localhost:8000/api/voices/{voice_id}/process \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_name": "elevenlabs"
  }'
```

**Response** (202 Accepted):
```json
{
  "voice_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing",
  "provider_name": "elevenlabs",
  "message": "Voice processing started. This may take 30-120 seconds."
}
```

**Error Responses**:
- `400 Bad Request`: Unsupported provider, voice not in uploadable state
- `401 Unauthorized`: Missing or invalid JWT token
- `403 Forbidden`: User doesn't own this voice
- `404 Not Found`: Voice not found
- `409 Conflict`: Voice already processed or processing

### 3. List User's Voices

Get a list of all voices owned by the authenticated user.

**Endpoint**: `GET /api/voices`

**Authentication**: Required (JWT token)

**Query Parameters**:
- `limit` (optional, integer, 1-100, default: 100) - Maximum number of results
- `offset` (optional, integer, >=0, default: 0) - Pagination offset

**Request Example**:
```bash
curl -X GET "http://localhost:8000/api/voices?limit=10&offset=0" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Response** (200 OK):
```json
{
  "voices": [
    {
      "voice_id": "123e4567-e89b-12d3-a456-426614174000",
      "user_id": "ee76317f-3b6f-4fea-8b74-56483731f58c",
      "name": "Professional Narrator Voice",
      "description": "Clear, authoritative voice for podcasts",
      "gender": "male",
      "status": "ready",
      "provider_voice_id": "elvenlabs_voice_abc123",
      "provider_name": "elevenlabs",
      "sample_file_url": "/api/voices/123e4567-e89b-12d3-a456-426614174000/sample",
      "sample_file_size": 2457600,
      "quality_score": 85,
      "error_message": null,
      "times_used": 3,
      "created_at": "2025-10-13T10:30:00Z",
      "updated_at": "2025-10-13T10:32:15Z",
      "processed_at": "2025-10-13T10:32:15Z"
    }
  ],
  "total_count": 1
}
```

**Error Responses**:
- `401 Unauthorized`: Missing or invalid JWT token

### 4. Get Voice Details

Get details of a specific voice.

**Endpoint**: `GET /api/voices/{voice_id}`

**Authentication**: Required (JWT token)

**Request Example**:
```bash
curl -X GET http://localhost:8000/api/voices/{voice_id} \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Response** (200 OK):
```json
{
  "voice_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "ee76317f-3b6f-4fea-8b74-56483731f58c",
  "name": "Professional Narrator Voice",
  "description": "Clear, authoritative voice for podcasts",
  "gender": "male",
  "status": "ready",
  "provider_voice_id": "elvenlabs_voice_abc123",
  "provider_name": "elevenlabs",
  "sample_file_url": "/api/voices/123e4567-e89b-12d3-a456-426614174000/sample",
  "sample_file_size": 2457600,
  "quality_score": 85,
  "error_message": null,
  "times_used": 3,
  "created_at": "2025-10-13T10:30:00Z",
  "updated_at": "2025-10-13T10:32:15Z",
  "processed_at": "2025-10-13T10:32:15Z"
}
```

**Error Responses**:
- `401 Unauthorized`: Missing or invalid JWT token
- `403 Forbidden`: User doesn't own this voice
- `404 Not Found`: Voice not found

### 5. Update Voice Metadata

Update voice name, description, or gender classification.

**Endpoint**: `PATCH /api/voices/{voice_id}`

**Authentication**: Required (JWT token)

**Content-Type**: `application/json`

**Request Body** (all fields optional):
```json
{
  "name": "Updated Voice Name",
  "description": "Updated description",
  "gender": "female"
}
```

**Request Example**:
```bash
curl -X PATCH http://localhost:8000/api/voices/{voice_id} \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Updated Voice",
    "description": "New description"
  }'
```

**Response** (200 OK):
```json
{
  "voice_id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "My Updated Voice",
  "description": "New description",
  ...
}
```

**Error Responses**:
- `400 Bad Request`: Invalid input (empty name, invalid gender)
- `401 Unauthorized`: Missing or invalid JWT token
- `403 Forbidden`: User doesn't own this voice
- `404 Not Found`: Voice not found

### 6. Delete Voice

Delete a voice and its associated sample file.

**Endpoint**: `DELETE /api/voices/{voice_id}`

**Authentication**: Required (JWT token)

**Request Example**:
```bash
curl -X DELETE http://localhost:8000/api/voices/{voice_id} \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Response** (204 No Content)

**Error Responses**:
- `401 Unauthorized`: Missing or invalid JWT token
- `403 Forbidden`: User doesn't own this voice
- `404 Not Found`: Voice not found
- `409 Conflict`: Voice is currently being used in podcast generation

### 7. Download Voice Sample

Download or stream the voice sample file.

**Endpoint**: `GET /api/voices/{voice_id}/sample`

**Authentication**: Required (JWT token)

**Request Example**:
```bash
curl -X GET http://localhost:8000/api/voices/{voice_id}/sample \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -o voice_sample.mp3
```

**Response** (200 OK):
- Content-Type: `audio/mpeg` (or appropriate MIME type)
- Binary audio data

**Supports HTTP Range Requests**: Yes (for streaming/seeking)

**Error Responses**:
- `401 Unauthorized`: Missing or invalid JWT token
- `403 Forbidden`: User doesn't own this voice
- `404 Not Found`: Voice or sample file not found

## Voice Status Workflow

```
1. UPLOADING → Upload in progress
   ↓
2. PROCESSING → Voice cloning with TTS provider
   ↓
3. READY → Voice is ready for use
   ↓
4. FAILED → Processing failed (see error_message)
```

## Using Custom Voices in Podcasts

### Voice ID Format

Custom voices use UUID format:
```
custom:{voice_id}
```

Preset voices use string names:
```
alloy, echo, fable, onyx, nova, shimmer
```

### Example: Generate Podcast with Custom Voice

```bash
curl -X POST http://localhost:8000/api/podcasts/generate \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_id": "your-collection-id",
    "duration": 15,
    "host_voice": "custom:123e4567-e89b-12d3-a456-426614174000",
    "expert_voice": "nova",
    "title": "Podcast with Custom Voice"
  }'
```

### Mixed Voice Scenarios

You can mix custom and preset voices:

**Scenario 1**: Custom HOST + Preset EXPERT
```json
{
  "host_voice": "custom:voice-uuid",
  "expert_voice": "onyx"
}
```

**Scenario 2**: Preset HOST + Custom EXPERT
```json
{
  "host_voice": "alloy",
  "expert_voice": "custom:voice-uuid"
}
```

**Scenario 3**: Both Custom
```json
{
  "host_voice": "custom:voice-uuid-1",
  "expert_voice": "custom:voice-uuid-2"
}
```

## Configuration

### Environment Variables

#### Phase 1: ElevenLabs Configuration 🚀

```bash
# Voice TTS Providers
VOICE_TTS_PROVIDERS=elevenlabs              # Available providers
VOICE_DEFAULT_PROVIDER=elevenlabs           # Default provider

# Voice Storage
VOICE_STORAGE_BACKEND=local                 # Storage backend (default: local)
VOICE_LOCAL_STORAGE_PATH=./data/voices      # Local storage path
VOICE_MAX_FILE_SIZE_MB=10                   # Max upload size (default: 10)
VOICE_MAX_PER_USER=10                       # Max voices per user (default: 10)
VOICE_ALLOWED_FORMATS=mp3,wav,m4a,flac,ogg  # Supported formats

# ElevenLabs API Configuration
ELEVENLABS_API_KEY=<your-api-key>           # Get from elevenlabs.io
ELEVENLABS_API_BASE_URL=https://api.elevenlabs.io/v1
ELEVENLABS_MODEL_ID=eleven_multilingual_v2  # Voice cloning model
ELEVENLABS_VOICE_SETTINGS_STABILITY=0.5     # Voice stability (0.0-1.0)
ELEVENLABS_VOICE_SETTINGS_SIMILARITY=0.75   # Voice similarity boost (0.0-1.0)
ELEVENLABS_REQUEST_TIMEOUT_SECONDS=30       # API timeout
ELEVENLABS_MAX_RETRIES=3                    # Retry attempts

# Voice Processing
VOICE_PROCESSING_TIMEOUT_SECONDS=30         # Timeout for voice cloning
VOICE_MIN_SAMPLE_DURATION_SECONDS=5         # Minimum sample length
VOICE_MAX_SAMPLE_DURATION_SECONDS=300       # Maximum 5 minutes
```

#### Phase 2: F5-TTS Configuration (Future) 🔧

```bash
# F5-TTS Self-Hosted Provider (Phase 2)
VOICE_TTS_PROVIDERS=elevenlabs,f5-tts       # Multiple providers
F5_TTS_SERVICE_URL=http://localhost:8001    # F5-TTS microservice
F5_TTS_MODEL_PATH=/models/f5-tts            # Model storage
F5_TTS_GPU_ENABLED=true                     # Use GPU for inference
F5_TTS_LANGUAGE=en                          # Default language
F5_TTS_CACHE_DIR=/cache                     # Voice embedding cache
```

### File Size Limits

| Format | Recommended Size | Max Size |
|--------|------------------|----------|
| MP3    | 1-5 MB          | 10 MB    |
| WAV    | 5-20 MB         | 10 MB    |
| M4A    | 1-5 MB          | 10 MB    |
| FLAC   | 10-30 MB        | 10 MB    |
| OGG    | 1-5 MB          | 10 MB    |

### Voice Sample Requirements

For best results, voice samples should:
- Be 30 seconds to 2 minutes long
- Have clear, high-quality audio
- Be free of background noise
- Contain natural, conversational speech
- Be in a supported audio format

## Cost Estimates

### ElevenLabs Pricing

Based on ElevenLabs pricing (as of Oct 2025):

| Operation | Cost | Notes |
|-----------|------|-------|
| Voice cloning | $0.30 | One-time per voice |
| TTS generation | $0.18/1K chars | Per podcast generation |

### Example Costs

**Scenario**: Create 1 custom voice, generate 5 podcasts (15 min each)

| Item | Calculation | Cost |
|------|-------------|------|
| Voice cloning (1x) | 1 × $0.30 | $0.30 |
| Podcast TTS (5x) | 5 × ~2,250 words × 5 chars × $0.18/1K | $10.13 |
| **Total** | | **$10.43** |

## Troubleshooting

### Voice Upload Fails: "Unsupported format"

**Cause**: Audio file format not supported

**Solution**: Convert to supported format (MP3, WAV, M4A, FLAC, OGG)

```bash
# Convert using ffmpeg
ffmpeg -i voice.aac -c:a libmp3lame -q:a 2 voice.mp3
```

### Voice Processing Stuck in "processing" Status

**Cause**: TTS provider API timeout or error

**Solution**:
1. Check provider API status
2. Verify API keys are correct
3. Check voice sample meets requirements
4. Retry processing after 5 minutes

### Voice Quality Score is Low

**Cause**: Poor quality audio sample

**Solution**:
- Re-record with better microphone
- Remove background noise
- Ensure clear, natural speech
- Use lossless format (WAV, FLAC) for upload

### Cannot Use Voice in Podcast: "Voice not ready"

**Cause**: Voice status is not "ready"

**Solution**:
1. Check voice status via GET /api/voices/{voice_id}
2. If status is "processing", wait for completion
3. If status is "failed", check error_message and re-upload

## Security Considerations

### Access Control

- Users can only access their own voices
- Voice sample files are access-controlled via JWT
- Cross-user voice sharing is not supported (by design)

### File Validation

- File type validation (magic number check)
- File size limits enforced
- Virus scanning (recommended in production)

### API Rate Limiting

Recommended rate limits:
- Voice upload: 5 per hour per user
- Voice processing: 10 per hour per user
- Voice listing: 100 per hour per user

## Testing

### Manual Testing

```bash
# 1. Upload voice sample
VOICE_ID=$(curl -X POST http://localhost:8000/api/voices/upload \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -F "name=Test Voice" \
  -F "gender=male" \
  -F "audio_file=@test_voice.mp3" \
  | jq -r '.voice_id')

# 2. Process voice
curl -X POST http://localhost:8000/api/voices/$VOICE_ID/process \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider_name": "elevenlabs"}'

# 3. Check status (wait for "ready")
curl -X GET http://localhost:8000/api/voices/$VOICE_ID \
  -H "Authorization: Bearer $JWT_TOKEN"

# 4. Use in podcast generation
curl -X POST http://localhost:8000/api/podcasts/generate \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"collection_id\": \"$COLLECTION_ID\",
    \"duration\": 5,
    \"host_voice\": \"custom:$VOICE_ID\",
    \"expert_voice\": \"alloy\"
  }"
```

### Automated Testing

```bash
# Unit tests
cd backend
poetry run pytest tests/unit/test_voice_service.py -v

# Integration tests (requires provider API keys)
export ELEVENLABS_API_KEY=your-key
poetry run pytest tests/integration/test_voice_integration.py -v
```

## Future Enhancements

- [ ] Multi-sample voice cloning (upload multiple samples for better quality)
- [ ] Voice preview before processing
- [ ] Voice sharing between team members
- [ ] Voice templates/presets
- [ ] Batch voice processing
- [ ] Voice analytics (usage metrics, quality trends)
- [ ] Voice versioning (update voice samples)
- [ ] Automatic voice enhancement (noise reduction, normalization)
