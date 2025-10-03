# ADR-002: Audio Generation Provider Selection (TTS vs Multi-Modal LLMs)

- **Status:** Proposed
- **Date:** 2025-10-02
- **Deciders:** Engineering Team, Product

## Context

For podcast generation (Issue #240), we need to convert generated text scripts into high-quality audio. There are two main approaches:

1. **Traditional Text-to-Speech (TTS) APIs** - Specialized services like OpenAI TTS, IBM WatsonX TTS, Google Cloud TTS
2. **Multi-Modal Large Language Models (LLMs)** - Models like IBM Granite Speech 3.3, LLaMA-Omni that can generate speech directly

The choice affects audio quality, latency, cost, infrastructure complexity, and future capabilities.

### Key Requirements

- **Quality:** Natural-sounding, professional audio suitable for podcasts
- **Latency:** Reasonable generation time for 5-60 minute podcasts
- **Cost:** Sustainable pricing at scale
- **Flexibility:** Support for voice customization (gender, speed, pitch)
- **Maintainability:** Simple integration and operation
- **Scalability:** Handle concurrent podcast generations

## Decision

**We will use Traditional Text-to-Speech (TTS) APIs as the primary audio generation method, with OpenAI TTS as the default provider and IBM WatsonX TTS as an alternative.**

We will design an abstraction layer (`AudioProviderBase`) that allows future integration of multi-modal LLMs when they mature.

## Consequences

### ✨ Positive Consequences (TTS Approach)

1. **Production-Ready Quality**
   - OpenAI TTS provides studio-quality voices (Alloy, Echo, Fable, Onyx, Nova, Shimmer)
   - Optimized specifically for speech synthesis
   - Consistent quality across different content types

2. **Simplicity & Reliability**
   - REST API calls - no model hosting required
   - Managed service with high availability
   - Simple integration (send text, receive audio)
   - No GPU infrastructure needed

3. **Low Latency**
   - Real-time or near-real-time generation
   - Streaming support for long-form content
   - 5-minute podcast: ~30-60 seconds generation time

4. **Cost Predictable**
   - OpenAI TTS: $15 per 1M characters (~$0.015 per 1000 chars)
   - WatsonX TTS: ~$0.02 per 1000 characters
   - 15-minute podcast (~2250 words = 13,500 chars) ≈ $0.20-$0.27

5. **Voice Customization**
   - Multiple pre-built voices
   - Speed control (0.25x - 4.0x)
   - Pitch adjustment
   - Different languages/accents

6. **Proven at Scale**
   - Used by major podcast platforms
   - Handles concurrent requests
   - Enterprise SLAs available

### ⚠️ Potential Limitations (TTS)

1. **External Dependency**
   - Requires API availability
   - Subject to rate limits
   - **Mitigation:** Multi-provider support (OpenAI + WatsonX fallback)

2. **Vendor Lock-in Risk**
   - API changes could break functionality
   - **Mitigation:** Abstraction layer allows provider swapping

3. **Limited Expressiveness**
   - Cannot control emotion/tone as precisely as human narration
   - **Mitigation:** Craft script with expressive language

## Alternatives Considered

### Option 1: Multi-Modal LLMs (IBM Granite Speech 3.3)

**Model:** [ibm-granite/granite-speech-3.3-8b](https://huggingface.co/ibm-granite/granite-speech-3.3-8b)

| Aspect | Details |
|--------|---------|
| **Pros** | • End-to-end text-to-speech in single model<br>• Potential for better contextual understanding<br>• IBM integration alignment<br>• No per-character pricing |
| **Cons** | • Requires self-hosting (GPU infrastructure needed)<br>• 8B parameters - needs significant compute<br>• Model loading time + inference time = higher latency<br>• Audio quality may not match specialized TTS<br>• Maintenance burden (model updates, hardware)<br>• Unproven at scale for long-form podcast generation |
| **Cost** | • GPU instance: ~$500-1000/month (NVIDIA A100/H100)<br>• DevOps overhead for model serving<br>• Higher total cost for low-moderate usage |
| **Latency** | • Model loading: 10-30 seconds (if not cached)<br>• 15-min podcast: Estimated 5-10 minutes generation<br>• Not suitable for real-time/interactive use |
| **Why Not** | ⛔ Higher infrastructure complexity and cost for unproven audio quality gains. Better suited for research than production. |

### Option 2: LLaMA-Omni

**Model:** [ictnlp/LLaMA-Omni](https://github.com/ictnlp/LLaMA-Omni)

| Aspect | Details |
|--------|---------|
| **Pros** | • Open-source multi-modal capabilities<br>• Potential for speech understanding + generation<br>• Community-driven improvements |
| **Cons** | • Experimental/research-stage model<br>• Requires extensive self-hosting infrastructure<br>• Limited documentation for production use<br>• Audio quality uncertain for long-form content<br>• No enterprise support |
| **Cost** | • Similar GPU costs to Granite Speech<br>• Higher engineering time for integration |
| **Latency** | • Likely higher than Granite due to larger model size<br>• 15-min podcast: Estimated 10-15 minutes |
| **Why Not** | ⛔ Too experimental for production podcast generation. Lacks proven track record and enterprise support. |

### Option 3: Google Cloud TTS / AWS Polly

| Aspect | Details |
|--------|---------|
| **Pros** | • Similar to OpenAI TTS in quality and API simplicity<br>• Good voice options<br>• Enterprise reliability |
| **Cons** | • Similar cost structure to OpenAI/WatsonX<br>• Less impressive voice quality than OpenAI's latest models<br>• Additional vendor to manage |
| **Why Not** | ✅ **Actually viable** - Could be added as third provider option. OpenAI/WatsonX chosen for initial implementation due to existing platform integrations. |

### Comparison Matrix

| Factor | TTS APIs (✅ Chosen) | Granite Speech 3.3 | LLaMA-Omni |
|--------|---------------------|-------------------|------------|
| **Audio Quality** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Good (unproven) | ⭐⭐ Experimental |
| **Latency (15-min)** | 30-60s ⚡ | 5-10 min 🐌 | 10-15 min 🐌🐌 |
| **Infrastructure** | None (API) ⚡ | GPU hosting needed 🏗️ | GPU hosting needed 🏗️ |
| **Cost (per podcast)** | $0.20-0.27 💰 | $0.50+ (amortized GPU) 💰💰 | $0.50+ 💰💰 |
| **Ease of Integration** | ⭐⭐⭐⭐⭐ Simple | ⭐⭐ Complex | ⭐ Very Complex |
| **Scalability** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Moderate | ⭐⭐ Limited |
| **Vendor Lock-in** | ⚠️ Moderate (mitigated) | ✅ None | ✅ None |
| **Production Readiness** | ⭐⭐⭐⭐⭐ Battle-tested | ⭐⭐ Emerging | ⭐ Research |

## Implementation Architecture

### Multi-Voice Q&A Dialogue Format

**Design Decision:** Podcasts use a two-voice conversational Q&A format with distinct speakers:
- **HOST**: Asks questions, provides introductions and transitions
- **EXPERT**: Provides detailed answers and explanations

This approach is more engaging than monologue narration and leverages multi-voice TTS capabilities.

**Voice Assignment:**
- HOST: `alloy` (warm, conversational)
- EXPERT: `onyx` (authoritative, clear)
- Users can customize voice selection via `VoiceSettings`

### Audio Provider Abstraction

```python
from abc import ABC, abstractmethod
from enum import Enum

class AudioProviderType(str, Enum):
    OPENAI = "openai"
    WATSONX = "watsonx"
    GRANITE_SPEECH = "granite_speech"  # Future
    LLAMA_OMNI = "llama_omni"  # Future

class AudioProviderBase(ABC):
    """Abstract base for audio generation providers."""

    @abstractmethod
    async def generate_audio(
        self,
        text: str,
        voice_settings: VoiceSettings,
        audio_format: AudioFormat,
    ) -> bytes:
        """Generate audio from text.

        Args:
            text: Script text to convert to audio
            voice_settings: Voice configuration (voice_id, speed, pitch)
            audio_format: Output format (mp3, wav, etc.)

        Returns:
            Audio file bytes

        Raises:
            AudioGenerationError: If generation fails
        """
        pass

    @abstractmethod
    async def list_available_voices(self) -> list[VoiceInfo]:
        """Get list of available voices."""
        pass
```

### Script Turn Model

Q&A dialogue scripts are structured as a sequence of turns:

```python
from pydantic import BaseModel
from enum import Enum

class Speaker(str, Enum):
    HOST = "HOST"
    EXPERT = "EXPERT"

class PodcastTurn(BaseModel):
    """Single turn in podcast dialogue."""
    speaker: Speaker
    text: str
    estimated_duration: float  # seconds

class PodcastScript(BaseModel):
    """Complete podcast script."""
    turns: list[PodcastTurn]
    total_duration: float
    total_words: int
```

### OpenAI TTS Implementation

```python
class OpenAIAudioProvider(AudioProviderBase):
    """OpenAI Text-to-Speech provider with multi-voice support."""

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate_audio(
        self,
        text: str,
        voice_settings: VoiceSettings,
        audio_format: AudioFormat,
    ) -> bytes:
        """Generate audio using OpenAI TTS API."""
        response = await self.client.audio.speech.create(
            model="tts-1-hd",  # High quality
            voice=voice_settings.voice_id,  # alloy, echo, fable, onyx, nova, shimmer
            input=text,
            speed=voice_settings.speed,  # 0.25 to 4.0
            response_format=audio_format.value,  # mp3, opus, aac, flac
        )

        return response.content

    async def generate_dialogue_audio(
        self,
        script: PodcastScript,
        host_voice: str = "alloy",
        expert_voice: str = "onyx",
        audio_format: AudioFormat = AudioFormat.MP3,
        pause_duration_ms: int = 500,
    ) -> bytes:
        """Generate audio for Q&A dialogue with multiple voices.

        Args:
            script: Parsed podcast script with turns
            host_voice: Voice ID for HOST speaker
            expert_voice: Voice ID for EXPERT speaker
            audio_format: Output format
            pause_duration_ms: Pause between speakers in milliseconds

        Returns:
            Combined audio bytes with pauses between speakers
        """
        audio_segments = []

        for turn in script.turns:
            # Select voice based on speaker
            voice_id = host_voice if turn.speaker == Speaker.HOST else expert_voice

            # Generate audio for this turn
            segment = await self.generate_audio(
                text=turn.text,
                voice_settings=VoiceSettings(voice_id=voice_id),
                audio_format=audio_format,
            )

            audio_segments.append(segment)

            # Add pause after each turn (except last)
            if turn != script.turns[-1]:
                pause = self._generate_silence(pause_duration_ms, audio_format)
                audio_segments.append(pause)

        # Combine all segments into single audio file
        return self._combine_audio_segments(audio_segments, audio_format)
```

### WatsonX TTS Implementation (Fallback)

```python
class WatsonXAudioProvider(AudioProviderBase):
    """IBM WatsonX Text-to-Speech provider."""

    def __init__(self, api_key: str, service_url: str):
        from ibm_watson import TextToSpeechV1
        from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

        authenticator = IAMAuthenticator(api_key)
        self.tts = TextToSpeechV1(authenticator=authenticator)
        self.tts.set_service_url(service_url)

    async def generate_audio(
        self,
        text: str,
        voice_settings: VoiceSettings,
        audio_format: AudioFormat,
    ) -> bytes:
        """Generate audio using WatsonX TTS."""
        response = self.tts.synthesize(
            text=text,
            voice=voice_settings.voice_id,  # en-US_AllisonV3Voice, etc.
            accept=f'audio/{audio_format.value}',
            rate_percentage=int((voice_settings.speed - 1.0) * 100),
            pitch_percentage=int((voice_settings.pitch - 1.0) * 100),
        ).get_result()

        return response.content
```

### Provider Factory

```python
class AudioProviderFactory:
    """Factory for creating audio providers."""

    @staticmethod
    def create_provider(
        provider_type: AudioProviderType,
        settings: Settings,
    ) -> AudioProviderBase:
        """Create audio provider instance."""
        if provider_type == AudioProviderType.OPENAI:
            return OpenAIAudioProvider(
                api_key=settings.openai_api_key
            )
        elif provider_type == AudioProviderType.WATSONX:
            return WatsonXAudioProvider(
                api_key=settings.watsonx_api_key,
                service_url=settings.watsonx_tts_url,
            )
        else:
            raise ValueError(f"Unsupported provider: {provider_type}")
```

## Configuration

```python
# core/config.py
class Settings(BaseSettings):
    # Audio generation
    podcast_audio_provider: AudioProviderType = AudioProviderType.OPENAI
    podcast_fallback_provider: AudioProviderType = AudioProviderType.WATSONX

    # OpenAI TTS
    openai_api_key: str
    openai_tts_model: str = "tts-1-hd"  # or "tts-1" for faster/cheaper

    # WatsonX TTS (fallback)
    watsonx_tts_api_key: str | None = None
    watsonx_tts_url: str | None = None
```

## Future Migration Path to Multi-Modal LLMs

When multi-modal LLMs mature (better quality, lower latency), we can add them via the same abstraction:

```python
class GraniteSpeechAudioProvider(AudioProviderBase):
    """IBM Granite Speech multi-modal provider (future)."""

    def __init__(self, model_path: str, device: str = "cuda"):
        from transformers import AutoModelForSpeechGeneration
        self.model = AutoModelForSpeechGeneration.from_pretrained(model_path)
        self.model.to(device)

    async def generate_audio(
        self,
        text: str,
        voice_settings: VoiceSettings,
        audio_format: AudioFormat,
    ) -> bytes:
        """Generate audio using Granite Speech model."""
        # Model inference logic
        audio_array = await self.model.generate_speech(
            text=text,
            voice_config=voice_settings,
        )
        return self._convert_to_format(audio_array, audio_format)
```

**Migration criteria:**
- Audio quality matches or exceeds TTS APIs
- Latency under 2 minutes for 15-minute podcasts
- Cost competitive with TTS (including infrastructure)
- Proven reliability at scale

## Status

**Proposed** - Pending team review.

**Recommendation:** Start with TTS APIs (OpenAI + WatsonX), monitor multi-modal LLM progress, migrate when advantageous.

## References

- [OpenAI TTS Documentation](https://platform.openai.com/docs/guides/text-to-speech)
- [IBM Granite Speech 3.3](https://huggingface.co/ibm-granite/granite-speech-3.3-8b)
- [LLaMA-Omni GitHub](https://github.com/ictnlp/LLaMA-Omni)
- [IBM WatsonX Text to Speech](https://cloud.ibm.com/docs/text-to-speech)
