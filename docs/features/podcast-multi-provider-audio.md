# Multi-Provider Podcast Audio Generation

!!! info "Feature Status"
    **Status**: ✅ Production Ready
    **Since**: October 2025
    **Related Issues**: Custom Voice Support

## Overview

RAG Modulo's podcast generation system now supports **multi-provider audio generation**, enabling seamless mixing of custom voices (ElevenLabs) with predefined provider voices (OpenAI) in a single podcast. This feature provides per-turn TTS provider selection, custom voice resolution, and intelligent audio stitching.

## Key Features

### 1. Per-Turn Provider Selection

Each dialogue turn can use a different TTS provider based on the voice selected:

```python
# Example: HOST using custom ElevenLabs voice, EXPERT using OpenAI voice
{
  "host_voice": "38c79b5a-204c-427c-b794-6c3a9e3db956",  // Custom voice (UUID)
  "expert_voice": "nova"  // OpenAI predefined voice
}
```

The system automatically:

- Detects voice ID format (UUID = custom, string = predefined)
- Resolves custom voices from database
- Selects appropriate TTS provider per turn
- Generates audio segments
- Stitches segments together with natural pauses

### 2. Custom Voice Resolution

**UUID-Based Detection**:

```python
async def _resolve_voice_id(self, voice_id: str, user_id: UUID4) -> tuple[str, str | None]:
    """
    Resolve voice ID to provider-specific voice ID.

    UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    Returns: (provider_voice_id, provider_name)
    """
```

**Validation Steps**:

1. Parse voice ID as UUID
2. Look up custom voice in database
3. Validate ownership (user_id matches)
4. Check voice status (must be "ready")
5. Return provider-specific voice ID and provider name

### 3. Supported Providers

| Provider | Voice Types | Use Cases |
|----------|------------|-----------|
| **OpenAI TTS** | Predefined voices (alloy, echo, fable, onyx, nova, shimmer) | Quick generation, consistent quality |
| **ElevenLabs** | Custom cloned voices + presets | Brand voices, personalized podcasts |
| **WatsonX TTS** | IBM Watson voices | Enterprise deployments |

### 4. Audio Stitching

**Technical Implementation**:

```python
# Generate audio for each turn with appropriate provider
for turn in script.turns:
    voice_id = host_voice_id if turn.speaker == Speaker.HOST else expert_voice_id
    provider = get_provider(provider_type)
    segment = await provider._generate_turn_audio(...)
    audio_segments.append(segment)

    # Add 500ms pause between turns
    if idx < len(script.turns) - 1:
        pause = AudioSegment.silent(duration=500)
        audio_segments.append(pause)

# Combine all segments
combined = AudioSegment.empty()
for segment in audio_segments:
    combined += segment
```

**Benefits**:

- Seamless transitions between providers
- Natural pauses between speakers
- Single output file (MP3, WAV, OGG, FLAC)

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Default audio provider for podcasts
PODCAST_AUDIO_PROVIDER=openai  # Options: openai, elevenlabs, watsonx

# OpenAI TTS Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_TTS_MODEL=tts-1-hd
OPENAI_TTS_DEFAULT_VOICE=alloy

# ElevenLabs TTS Configuration
ELEVENLABS_API_KEY=your-elevenlabs-api-key
ELEVENLABS_API_BASE_URL=https://api.elevenlabs.io/v1
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
ELEVENLABS_VOICE_SETTINGS_STABILITY=0.5
ELEVENLABS_VOICE_SETTINGS_SIMILARITY=0.75
ELEVENLABS_REQUEST_TIMEOUT_SECONDS=30
ELEVENLABS_MAX_RETRIES=3
```

Get your API keys:

- **OpenAI**: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- **ElevenLabs**: [https://elevenlabs.io/app/settings/api-keys](https://elevenlabs.io/app/settings/api-keys)

### Provider Configuration

The system uses `AudioProviderFactory` to create provider instances:

```python
from rag_solution.generation.audio.factory import AudioProviderFactory

# Create provider from settings
provider = AudioProviderFactory.create_provider(
    provider_type="elevenlabs",  # or "openai", "watsonx"
    settings=settings
)

# List available providers
providers = AudioProviderFactory.list_providers()
# Returns: ["openai", "elevenlabs", "watsonx", "ollama"]
```

## Usage

### 1. Creating Custom Voices

**Upload and Clone Voice** (ElevenLabs):

```bash
POST /api/voices/upload-and-clone
Content-Type: multipart/form-data

Parameters:
- file: Audio file (MP3, WAV) - 1+ minute of clear speech
- name: Voice name (e.g., "Brand Voice")
- description: Optional voice description

Response:
{
  "voice_id": "38c79b5a-204c-427c-b794-6c3a9e3db956",
  "user_id": "ee76317f-3b6f-4fea-8b74-56483731f58c",
  "name": "Brand Voice",
  "status": "ready",
  "provider_name": "elevenlabs",
  "provider_voice_id": "21m00Tcm4TlvDq8ikWAM"
}
```

### 2. Generating Podcasts with Custom Voices

**Mixed Provider Example**:

```bash
POST /api/podcasts/script-to-audio
Content-Type: application/json

{
  "collection_id": "5eb82bd8-1fbd-454e-86d6-61199642757c",
  "title": "My Podcast",
  "duration": 5,
  "host_voice": "38c79b5a-204c-427c-b794-6c3a9e3db956",  # Custom ElevenLabs
  "expert_voice": "nova",  # OpenAI predefined
  "audio_format": "mp3",
  "script_text": "HOST: Welcome...\nEXPERT: Thank you..."
}
```

**Both Custom Voices**:

```json
{
  "host_voice": "38c79b5a-204c-427c-b794-6c3a9e3db956",  # Custom voice 1
  "expert_voice": "7d2e9f1a-8b3c-4d5e-9f6a-1b2c3d4e5f6a"   # Custom voice 2
}
```

**Both Predefined Voices**:

```json
{
  "host_voice": "alloy",  # OpenAI
  "expert_voice": "nova"  # OpenAI
}
```

### 3. Script Format Flexibility

The system now accepts multiple dialogue formats:

```text
HOST: Welcome to today's podcast...
EXPERT: Thank you for having me...

Host: Welcome to today's podcast...
Expert: Thank you for having me...

[HOST]: Welcome to today's podcast...
[EXPERT]: Thank you for having me...

[Host]: Welcome to today's podcast...
[Expert]: Thank you for having me...
```

All formats are parsed correctly and validated.

## Technical Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Podcast Service                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  _generate_audio() - Multi-Provider Orchestration   │   │
│  │  • Resolve voice IDs (UUID → provider mapping)      │   │
│  │  • Cache provider instances                         │   │
│  │  • Generate per-turn audio                          │   │
│  │  • Stitch segments with pauses                      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              AudioProviderFactory                           │
│  • create_provider(type, settings)                          │
│  • list_providers()                                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────┬─────────────────┬─────────────────┐
        ↓                 ↓                 ↓                 ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   OpenAI     │  │ ElevenLabs   │  │  WatsonX     │  │   Ollama     │
│   Provider   │  │   Provider   │  │   Provider   │  │   Provider   │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

### Key Classes

#### 1. PodcastService

**Location**: `backend/rag_solution/services/podcast_service.py`

**Key Methods**:

```python
async def _resolve_voice_id(self, voice_id: str, user_id: UUID4) -> tuple[str, str | None]:
    """
    Resolve voice ID to provider-specific voice ID.

    Logic:
    1. Try to parse as UUID
    2. If UUID: Look up in database, validate, return (provider_voice_id, provider_name)
    3. If not UUID: Return (voice_id, None) - it's a predefined voice

    Returns:
        Tuple of (resolved_voice_id, provider_name)
    """

async def _generate_audio(
    self,
    podcast_id: UUID4,
    podcast_script: PodcastScript,
    podcast_input: PodcastGenerationInput,
) -> bytes:
    """
    Generate audio from parsed script with multi-provider support.

    Strategy:
    1. Resolve both voices upfront to determine providers
    2. Create provider instances as needed (cached)
    3. Generate each turn with appropriate provider
    4. Stitch all segments with pauses
    5. Export to requested format
    """
```

#### 2. AudioProviderFactory

**Location**: `backend/rag_solution/generation/audio/factory.py`

```python
class AudioProviderFactory:
    """Factory for creating audio generation providers."""

    _providers: ClassVar[dict[str, type[AudioProviderBase]]] = {
        "openai": OpenAIAudioProvider,
        "elevenlabs": ElevenLabsAudioProvider,
        "watsonx": WatsonXAudioProvider,
        "ollama": OllamaAudioProvider,
    }

    @classmethod
    def create_provider(cls, provider_type: str, settings: Settings) -> AudioProviderBase:
        """Create audio provider instance from settings."""

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names."""
```

#### 3. ScriptParser

**Location**: `backend/rag_solution/utils/script_parser.py`

**Updated Patterns**:

```python
HOST_PATTERNS: ClassVar[list[str]] = [
    r"^HOST:\s*(.*)$",
    r"^Host:\s*(.*)$",
    r"^H:\s*(.*)$",
    r"^\[HOST\]:\s*(.*)$",  # [HOST]: format (with colon)
    r"^\[HOST\]\s*(.*)$",   # [HOST] format (without colon)
    r"^\[Host\]:\s*(.*)$",  # [Host]: format
]
```

## Performance & Cost

### Benchmarks

| Configuration | Generation Time | Cost (5 min podcast) |
|--------------|----------------|---------------------|
| OpenAI only | ~30-45 seconds | ~$0.05-0.10 |
| ElevenLabs only | ~45-60 seconds | ~$0.15-0.30 |
| Mixed (OpenAI + ElevenLabs) | ~40-55 seconds | ~$0.10-0.20 |

### Optimization

**Provider Caching**:

```python
# Cache provider instances to avoid recreation per turn
provider_cache: dict[str, AudioProviderBase] = {}

def get_provider(provider_type: str) -> AudioProviderBase:
    if provider_type not in provider_cache:
        provider_cache[provider_type] = AudioProviderFactory.create_provider(...)
    return provider_cache[provider_type]
```

**Benefits**:

- Reduces provider initialization overhead
- Reuses HTTP connections
- Faster per-turn generation

## Error Handling

### Common Errors

#### 1. Custom Voice Not Found

```json
{
  "error": "ValidationError",
  "message": "Custom voice '38c79b5a-...' not found",
  "field": "voice_id"
}
```

**Solution**: Verify voice ID exists in database and belongs to user.

#### 2. Voice Not Ready

```json
{
  "error": "ValidationError",
  "message": "Custom voice '38c79b5a-...' is not ready",
  "status": "processing"
}
```

**Solution**: Wait for voice cloning to complete (usually 30-60 seconds).

#### 3. Provider API Error

```json
{
  "error": "AudioGenerationError",
  "provider": "elevenlabs",
  "error_type": "api_error",
  "message": "HTTP 401: Invalid API key"
}
```

**Solution**: Check API key configuration in `.env`.

#### 4. Script Format Validation Error

```json
{
  "error": "ValidationError",
  "message": "Script must contain HOST speaker turns"
}
```

**Solution**: Ensure script has both HOST and EXPERT dialogue turns.

## Best Practices

### 1. Voice Selection

**Custom Voices**:

- Use for brand consistency
- Requires 1+ minute of clear audio
- Better for recognizable voices

**Predefined Voices**:

- Faster to set up (no cloning)
- Consistent quality
- Good for generic podcasts

### 2. Script Quality

**Good**:

```text
HOST: Welcome to today's podcast on machine learning.
EXPERT: Thank you for having me. Let me explain the core concepts.
```

**Avoid**:

```text
HOST: Welcome, [EXPERT NAME]!  # ❌ Placeholder names
EXPERT: [Placeholder response]  # ❌ Template text
```

### 3. API Rate Limits

**OpenAI**:

- 50 requests/minute (free tier)
- 500 requests/minute (paid tier)

**ElevenLabs**:

- 10,000 characters/month (free tier)
- Unlimited (paid tier)

**Recommendations**:

- Use provider caching
- Implement retry logic (already built-in)
- Monitor usage via provider dashboards

## Migration Guide

### From Single-Provider to Multi-Provider

**Before** (single provider for entire podcast):

```python
# Old approach - all turns use same provider
podcast_input = PodcastGenerationInput(
    host_voice="alloy",
    expert_voice="onyx",
    # Provider determined by PODCAST_AUDIO_PROVIDER setting
)
```

**After** (per-turn provider selection):

```python
# New approach - each voice can use different provider
podcast_input = PodcastGenerationInput(
    host_voice="38c79b5a-...",  # Custom ElevenLabs voice
    expert_voice="nova",          # OpenAI predefined voice
    # Providers automatically resolved per turn
)
```

**Backward Compatibility**:
All existing podcasts continue to work without changes. The system detects voice ID format and selects appropriate provider automatically.

## Troubleshooting

### Issue: Voice Cloning Fails

**Symptoms**: Custom voice stuck in "processing" status

**Solutions**:

1. Check audio quality (clear speech, minimal background noise)
2. Ensure file is 1+ minute duration
3. Verify API key is valid
4. Check ElevenLabs account quota

### Issue: Audio Stitching Produces Clicks

**Symptoms**: Audible clicks/pops between turns

**Solutions**:

1. Adjust pause duration (default 500ms)
2. Ensure all providers use same sample rate
3. Check audio format consistency

### Issue: Generation Times Out

**Symptoms**: Request times out after 120 seconds

**Solutions**:

1. Reduce podcast duration
2. Use faster provider (OpenAI typically faster)
3. Increase timeout in settings:

```python
ELEVENLABS_REQUEST_TIMEOUT_SECONDS=60  # Increase if needed
```

## Future Enhancements

### Planned Features

1. **Voice Style Control**
   - Emotion/tone settings per turn
   - Speaking rate variation

2. **Background Music**
   - Auto-mix background music
   - Fade in/out support

3. **Multi-Language Support**
   - Voice cloning for multiple languages
   - Automatic language detection

4. **Advanced Audio Processing**
   - Noise reduction
   - Volume normalization
   - EQ adjustments

## References

- [Podcast Generation Overview](podcast-generation.md)
- [API Documentation](../api/index.md)
- [ElevenLabs API Docs](https://elevenlabs.io/docs/api-reference/text-to-speech)
- [OpenAI TTS Docs](https://platform.openai.com/docs/guides/text-to-speech)

---

**Last Updated**: October 15, 2025
**Contributors**: Claude Code Assistant
