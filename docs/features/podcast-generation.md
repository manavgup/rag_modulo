# Podcast Generation

## Overview

The RAG Modulo podcast generation feature creates AI-powered podcasts from document collections using a multi-stage pipeline that combines RAG search, LLM script generation, and text-to-speech audio synthesis.

## Architecture

### Complete Pipeline Flow

```
1. Content Retrieval (0-30%)
   └─> RAG Search → Retrieve relevant chunks from collection

2. Script Generation (30-40%)
   └─> LLM (WatsonX) → Generate HOST/EXPERT dialogue

3. Script Parsing (40-50%)
   └─> Parser → Extract turns with speaker labels

4. Audio Generation (50-90%)
   └─> OpenAI TTS → Multi-voice audio synthesis

5. Audio Storage (90-100%)
   └─> LocalFileStorage → Save MP3 file
```

## API Endpoints

### Generate Podcast

**Endpoint**: `POST /api/podcasts/generate`

**Request Body**:
```json
{
  "user_id": "uuid",
  "collection_id": "uuid",
  "duration": 5,  // 5, 15, 30, or 60 minutes
  "voice_settings": {
    "voice_id": "alloy",
    "speed": 1.0,
    "pitch": 1.0
  },
  "format": "mp3",  // mp3, wav, ogg, flac
  "host_voice": "alloy",
  "expert_voice": "onyx",
  "include_intro": false,
  "include_outro": false,
  "title": "Optional Podcast Title"
}
```

**Response** (202 Accepted):
```json
{
  "podcast_id": "uuid",
  "status": "queued",
  "progress_percentage": 0,
  "created_at": "2025-10-09T16:55:34.505223"
}
```

### Check Podcast Status

**Endpoint**: `GET /api/podcasts/{podcast_id}?user_id={user_id}`

**Response**:
```json
{
  "podcast_id": "uuid",
  "status": "completed",  // queued, generating, completed, failed
  "progress_percentage": 100,
  "current_step": null,
  "audio_url": "/podcasts/{user_id}/{podcast_id}/audio.mp3",
  "audio_size_bytes": 93836,
  "transcript": "HOST: Welcome to today's podcast...",
  "completed_at": "2025-10-09T16:56:14.455209"
}
```

## Configuration

### Environment Variables

```bash
# Required for OpenAI TTS (default provider)
OPENAI_API_KEY=sk-proj-your-key-here

# Optional: Podcast settings
PODCAST_MIN_DOCUMENTS=1              # Minimum documents required (default: 1)
PODCAST_MAX_CONCURRENT_PER_USER=3    # Max concurrent generations (default: 3)
PODCAST_STORAGE_BACKEND=local        # Storage: local, minio, s3 (default: local)
PODCAST_LOCAL_STORAGE_PATH=./data/podcasts  # Local storage path

# Optional: TTS model selection
OPENAI_TTS_MODEL=tts-1-hd  # or tts-1 (default: tts-1-hd)
```

### Podcast Durations

| Duration | Minutes | Target Words | Retrieval Top-K |
|----------|---------|--------------|-----------------|
| SHORT    | 5       | 750          | 30 chunks       |
| MEDIUM   | 15      | 2,250        | 50 chunks       |
| LONG     | 30      | 4,500        | 75 chunks       |
| EXTENDED | 60      | 9,000        | 100 chunks      |

## Available Voices

### OpenAI TTS Voices

| Voice ID | Name    | Gender  | Description                      | Best For |
|----------|---------|---------|----------------------------------|----------|
| alloy    | Alloy   | Neutral | Warm, conversational             | HOST     |
| echo     | Echo    | Male    | Clear, authoritative             | EXPERT   |
| fable    | Fable   | Neutral | Expressive, storytelling         | HOST     |
| onyx     | Onyx    | Male    | Deep, authoritative              | EXPERT   |
| nova     | Nova    | Female  | Bright, engaging                 | HOST     |
| shimmer  | Shimmer | Female  | Warm, friendly                   | EXPERT   |

## Usage Examples

### Generate a Podcast

```bash
curl -X POST http://localhost:8000/api/podcasts/generate \
  -H "Content-Type: application/json" \
  -H "X-User-UUID: your-user-id" \
  -d '{
    "user_id": "your-user-id",
    "collection_id": "your-collection-id",
    "duration": 5,
    "voice_settings": {
      "voice_id": "alloy",
      "speed": 1.0,
      "pitch": 1.0
    },
    "format": "mp3",
    "host_voice": "alloy",
    "expert_voice": "onyx",
    "title": "My First Podcast"
  }'
```

### Monitor Progress

```bash
# Poll for status (check every 5 seconds)
PODCAST_ID="your-podcast-id"
USER_ID="your-user-id"

while true; do
  STATUS=$(curl -s "http://localhost:8000/api/podcasts/$PODCAST_ID?user_id=$USER_ID" \
    | jq -r '.status')
  PROGRESS=$(curl -s "http://localhost:8000/api/podcasts/$PODCAST_ID?user_id=$USER_ID" \
    | jq -r '.progress_percentage')

  echo "Status: $STATUS - Progress: $PROGRESS%"

  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi

  sleep 5
done
```

### Download Podcast

```bash
# Get the audio URL from status endpoint
AUDIO_URL=$(curl -s "http://localhost:8000/api/podcasts/$PODCAST_ID?user_id=$USER_ID" \
  | jq -r '.audio_url')

# Download the podcast
curl -o my_podcast.mp3 "http://localhost:8000$AUDIO_URL"
```

## Implementation Details

### Service Layer

**File**: `backend/rag_solution/services/podcast_service.py`

The `PodcastService` orchestrates the complete podcast generation pipeline:

```python
class PodcastService:
    def __init__(self, session: Session, collection_service, search_service):
        self.session = session
        self.collection_service = collection_service
        self.search_service = search_service
        self.repository = PodcastRepository(session)
        self.script_parser = PodcastScriptParser(average_wpm=150)
        self.audio_storage = self._create_audio_storage()
```

**Key Methods**:
- `generate_podcast()`: Queue podcast generation (returns immediately)
- `_process_podcast_generation()`: Background task processing
- `_retrieve_content()`: RAG-based content retrieval
- `_generate_script()`: LLM script generation
- `_generate_audio()`: TTS audio synthesis
- `_store_audio()`: Save audio file

### Repository Layer

**File**: `backend/rag_solution/repository/podcast_repository.py`

Handles podcast database operations with **synchronous Session** (matches codebase pattern):

```python
class PodcastRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, ...) -> Podcast:
        """Create podcast record with QUEUED status"""

    def update_progress(self, podcast_id, progress, step):
        """Update generation progress"""

    def mark_completed(self, podcast_id, audio_url, transcript, size):
        """Mark podcast as COMPLETED"""
```

### Audio Generation

**File**: `backend/rag_solution/generation/audio/openai_audio.py`

OpenAI TTS provider with multi-voice support:

```python
class OpenAIAudioProvider(AudioProviderBase):
    def __init__(self, api_key: str, model: str = "tts-1-hd"):
        self.client = AsyncOpenAI(api_key=api_key.strip())  # Strip whitespace!

    async def generate_dialogue_audio(self, script, host_voice, expert_voice):
        """Generate audio for complete podcast script"""
```

**Important**: API key must be stripped of whitespace to avoid HTTP header errors.

### Script Parser

**File**: `backend/rag_solution/utils/script_parser.py`

Parses LLM-generated scripts into structured dialogue:

```python
class PodcastScriptParser:
    # Regex patterns allow speaker labels on separate lines
    HOST_PATTERNS = [r"^HOST:\s*(.*)$", ...]  # .* allows empty text
    EXPERT_PATTERNS = [r"^EXPERT:\s*(.*)$", ...]

    def parse(self, raw_script: str) -> ScriptParsingResult:
        """Parse raw script into PodcastScript with turns"""
```

## Troubleshooting

### Connection Error: "Illegal header value"

**Cause**: Trailing whitespace in `OPENAI_API_KEY` environment variable

**Solution**:
```bash
# Ensure no trailing spaces in .env file
OPENAI_API_KEY=sk-proj-your-key-here  # No spaces after key!
```

**Code Fix**: Added `.strip()` in `AudioProviderFactory._create_openai_provider()`

### AttributeError: 'DocumentMetadata' object has no attribute 'chunk_text'

**Cause**: Content retrieval used wrong data structure

**Solution**: Use `result.chunk.text` from `query_results` instead of `doc.chunk_text` from `documents`

```python
# ❌ WRONG
formatted_results = [doc.chunk_text for doc in search_result.documents]

# ✅ CORRECT
formatted_results = [
    result.chunk.text
    for result in search_result.query_results
    if result.chunk
]
```

### No dialogue turns found in script

**Cause**: LLM puts speaker labels on separate lines

**Solution**: Changed regex from `(.+)` to `(.*)` to allow speaker-only lines

```python
# Now handles both formats:
HOST: Question here         # Single line
# AND
HOST:                       # Multiline
Question here
```

### Template is required for text generation

**Cause**: WatsonX provider requires template parameter

**Solution**: Create `PromptTemplateBase` with required fields:

```python
from rag_solution.schemas.prompt_template_schema import (
    PromptTemplateBase,
    PromptTemplateType
)

template = PromptTemplateBase(
    name="podcast_script_generation",
    user_id=user_id,
    template_type=PromptTemplateType.CUSTOM,
    template_format="{prompt}",
    input_variables={"prompt": "description"},
)
```

## Cost Estimates

### OpenAI TTS Pricing

Based on $15.00 per 1M characters (as of Oct 2025):

| Duration | Words | Characters (est.) | Cost  |
|----------|-------|-------------------|-------|
| SHORT    | 750   | ~3,750            | $0.06 |
| MEDIUM   | 2,250 | ~11,250           | $0.17 |
| LONG     | 4,500 | ~22,500           | $0.34 |
| EXTENDED | 9,000 | ~45,000           | $0.68 |

## Testing

### Manual Testing

```bash
# 1. Ensure collection has status=COMPLETED
# 2. Generate podcast
curl -X POST http://localhost:8000/api/podcasts/generate \
  -H "Content-Type: application/json" \
  -d @test_podcast_request.json

# 3. Monitor progress (takes 30-60 seconds)
# 4. Download and play the generated audio
```

### Automated Testing

```bash
# Unit tests (mocked TTS)
cd backend
poetry run pytest tests/unit/test_podcast_service.py -v

# Integration tests (requires OpenAI API key)
export OPENAI_API_KEY=your-key
poetry run pytest tests/integration/test_podcast_integration.py -v
```

## Future Enhancements

- [ ] Background music support
- [ ] Custom intro/outro segments
- [ ] Multiple language support
- [ ] Voice cloning capabilities
- [ ] Real-time progress WebSocket updates
- [ ] Podcast episode management
- [ ] RSS feed generation
- [ ] Automatic distribution to podcast platforms
