# Podcast Duration Control: Problem Analysis & Recommendations

## Executive Summary

**Tests Created:** 33 comprehensive tests exposing fundamental problems

- **Atomic tests:** 12 tests documenting duration calculation gaps
- **Unit tests (duration control):** 11 tests exposing validation failures
- **Unit tests (audio serving):** 10 tests exposing missing endpoint

**Test Results:** ✅ All 33 tests pass (they document problems, not failures)

**Critical Findings:**

1. ❌ **No audio serving endpoint** - Files generated but inaccessible to frontend
2. ❌ **No LLM word count validation** - System accepts any output length
3. ❌ **No actual duration measurement** - Never validates TTS output
4. ❌ **No retry mechanism** - Duration mismatches go uncorrected
5. ❌ **No quality gates** - Podcasts marked COMPLETED regardless of duration

---

## Problem 1: Missing Audio Serving Endpoint

### Current State

```
Generation Flow: ✅ WORKING
├── 1. Generate script ✅
├── 2. Generate audio ✅
├── 3. Store to disk ✅  -> ./data/podcasts/{user_id}/{podcast_id}/audio.mp3
├── 4. Update DB ✅      -> audio_url = "/podcasts/{user_id}/{podcast_id}/audio.mp3"
└── 5. Return to frontend ✅

Frontend Access Flow: ❌ BROKEN
├── 1. Get podcast details ✅  -> { audio_url: "/podcasts/.../audio.mp3" }
├── 2. Create <audio> element ✅
├── 3. Browser tries: http://localhost:8000/podcasts/.../audio.mp3
└── 4. Result: 404 Not Found ❌
    └── Error: "The element has no supported sources"
```

### Root Cause

- **Files exist on disk** but no HTTP endpoint serves them
- **podcast_router.py** has no GET /audio route
- **main.py** has no static file mounting

### Solution: Add Static File Mounting

**Recommended Implementation** (backend/main.py):

```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# After router includes, add:
# Mount podcast audio files (local development)
podcast_storage_path = Path(get_settings().podcast_local_storage_path)
if podcast_storage_path.exists():
    app.mount(
        "/podcasts",
        StaticFiles(directory=str(podcast_storage_path)),
        name="podcasts"
    )
    logger.info("Mounted podcast audio files from %s", podcast_storage_path)
```

**Why this solution:**

- ✅ Simple and fast (no Python overhead)
- ✅ Browser can cache files
- ✅ Supports HTTP Range requests (seek functionality)
- ✅ CORS headers handled by middleware
- ⚠️ No per-file access control (anyone with URL can access)
- ⚠️ Only works for local storage (not S3/MinIO)

**For production**, use presigned URLs for cloud storage.

---

## Problem 2: No Duration Control Guarantees

### Research: Industry Comparison

I researched how other podcast generators handle duration:

| System | Duration Control | Word Count Control | Validation |
|--------|-----------------|-------------------|------------|
| **NotebookLM** (Google) | ❌ "Typically 6-15 min" | ❌ None | ❌ None |
| **podgenai** (GitHub) | ❌ "Loosely 1 hour" | ❌ Uses sections | ❌ None |
| **Jellypod** | ⚠️ ~3-4 min/section | ⚠️ Add/remove sections | ❌ None |
| **Our System** | ❌ 5/15/30/60 min | ⚠️ 150 WPM × duration | ❌ None |

**Key Finding:** **NO system has precise duration control.** This is a UNIVERSAL problem.

### Current Prompt Analysis

**Our Prompt** (`backend/rag_solution/services/podcast_service.py:50-82`):

```python
PODCAST_SCRIPT_PROMPT = """You are a professional podcast script writer. Create an engaging podcast dialogue between a HOST and an EXPERT.

Topic/Focus: {user_topic}

Content from documents:
{rag_results}

Duration: {duration_minutes} minutes (approximately {word_count} words at 150 words/minute)

Format your script as a natural conversation with these guidelines:

1. **Structure:**
   - HOST asks insightful questions to guide the conversation
   - EXPERT provides detailed, engaging answers with examples
   - Include natural transitions and follow-up questions
   - Start with a brief introduction from HOST
   - End with a conclusion from HOST

2. **Script Format (IMPORTANT):**
   Use this exact format for each turn:

   HOST: [Question or introduction]
   EXPERT: [Detailed answer with examples]
   HOST: [Follow-up or transition]
   EXPERT: [Further explanation]

3. **Content Guidelines:**
   - Make it conversational and engaging
   - Use examples and analogies to clarify complex topics
   - Keep language accessible but informative
   - Include natural pauses and transitions

Generate the complete dialogue script now:"""
```

**Strengths:**

- ✅ Clear structure with HOST/EXPERT format
- ✅ Specifies word count target explicitly
- ✅ Includes conversational guidelines
- ✅ Emphasizes natural flow and transitions

**Weaknesses:**

- ❌ No enforcement mechanism for word count
- ❌ Phrase "approximately" gives LLM too much leeway
- ❌ No penalties for deviation
- ❌ No examples of desired length
- ❌ Single-shot generation (no iteration)

### NotebookLM Approach (Inferred from Research)

Based on research, NotebookLM appears to use:

- **Section-based approach**: Break into 3-4 minute segments
- **Conversational markers**: "Right," "Exactly," rhetorical questions
- **Structured flow**: Broad intro → narrow specifics → conclusion
- **Energetic tone**: Informal, engaging style
- **Custom instructions**: User can guide focus and tone

**They still don't have precise duration control.**

---

## Recommended Solutions

### Solution 1: Iterative Generation with Validation (Recommended)

```python
async def _generate_script_with_validation(
    self,
    podcast_input: PodcastGenerationInput,
    rag_results: str,
    max_attempts: int = 3,
) -> str:
    """Generate script with word count validation and retry."""

    target_word_count = self._calculate_target_word_count(podcast_input)
    tolerance = 0.15  # Allow 15% deviation

    for attempt in range(1, max_attempts + 1):
        # Adjust prompt based on previous attempt
        if attempt == 1:
            prompt = self._build_initial_prompt(podcast_input, rag_results, target_word_count)
        else:
            # Adapt prompt based on previous result
            deviation = (actual_word_count - target_word_count) / target_word_count
            if deviation < 0:  # Too short
                prompt = self._build_expansion_prompt(podcast_input, rag_results, target_word_count, actual_word_count)
            else:  # Too long
                prompt = self._build_condensation_prompt(podcast_input, rag_results, target_word_count, actual_word_count)

        # Generate script
        script = await self._call_llm(prompt)

        # Validate word count
        actual_word_count = len(script.split())
        deviation_pct = abs(actual_word_count - target_word_count) / target_word_count

        logger.info(
            "Script generation attempt %d/%d: target=%d, actual=%d, deviation=%.1f%%",
            attempt, max_attempts, target_word_count, actual_word_count, deviation_pct * 100
        )

        if deviation_pct <= tolerance:
            logger.info("Script word count within tolerance, accepting")
            return script

        if attempt == max_attempts:
            logger.warning(
                "Script word count still off after %d attempts, using best effort",
                max_attempts
            )
            return script

    return script


def _calculate_target_word_count(self, podcast_input: PodcastGenerationInput) -> int:
    """Calculate target word count accounting for voice speed."""
    duration_map = {
        PodcastDuration.SHORT: 5,
        PodcastDuration.MEDIUM: 15,
        PodcastDuration.LONG: 30,
        PodcastDuration.EXTENDED: 60,
    }

    base_wpm = 150  # Base words per minute
    duration_minutes = duration_map[podcast_input.duration]

    # Adjust for voice speed setting
    voice_speed = podcast_input.voice_settings.speed
    effective_wpm = base_wpm * voice_speed

    return int(duration_minutes * effective_wpm)
```

### Solution 2: Measure Actual Audio Duration

```python
async def _store_audio_with_validation(
    self,
    podcast_id: UUID4,
    user_id: UUID4,
    audio_bytes: bytes,
    audio_format: AudioFormat,
    expected_duration_minutes: int,
) -> tuple[str, float]:
    """Store audio and measure actual duration."""

    # Measure actual duration
    actual_duration_seconds = await self._measure_audio_duration(audio_bytes, audio_format)

    # Calculate deviation
    expected_duration_seconds = expected_duration_minutes * 60
    deviation_pct = abs(actual_duration_seconds - expected_duration_seconds) / expected_duration_seconds

    logger.info(
        "Audio duration: expected=%ds, actual=%ds, deviation=%.1f%%",
        expected_duration_seconds,
        actual_duration_seconds,
        deviation_pct * 100
    )

    # Store audio
    audio_url = await self.audio_storage.store_audio(
        podcast_id=podcast_id,
        user_id=user_id,
        audio_data=audio_bytes,
        audio_format=audio_format.value,
    )

    return audio_url, actual_duration_seconds


async def _measure_audio_duration(self, audio_bytes: bytes, audio_format: AudioFormat) -> float:
    """Measure duration of audio file in seconds."""
    import io
    from pydub import AudioSegment

    # Load audio from bytes
    audio = AudioSegment.from_file(
        io.BytesIO(audio_bytes),
        format=audio_format.value
    )

    # Duration in seconds
    return len(audio) / 1000.0
```

### Solution 3: Enhanced Output Schema

```python
# Update PodcastGenerationOutput schema
class PodcastGenerationOutput(BaseModel):
    # Existing fields...
    duration: PodcastDuration  # Requested duration (5, 15, 30, 60)

    # NEW FIELDS:
    actual_duration_seconds: Optional[float] = None  # Measured audio duration
    duration_accuracy_percentage: Optional[float] = None  # (actual / requested) * 100
    word_count: Optional[int] = None  # Actual script word count
    duration_warning: Optional[str] = None  # Warning if significantly off

    @validator('duration_warning', always=True)
    def set_duration_warning(cls, v, values):
        """Set warning if actual duration is >20% off from requested."""
        if values.get('actual_duration_seconds') and values.get('duration'):
            requested_seconds = values['duration'] * 60
            actual_seconds = values['actual_duration_seconds']
            deviation = abs(actual_seconds - requested_seconds) / requested_seconds

            if deviation > 0.2:  # 20% threshold
                minutes_off = (actual_seconds - requested_seconds) / 60
                return (
                    f"Podcast duration is {abs(minutes_off):.1f} minutes "
                    f"{'longer' if minutes_off > 0 else 'shorter'} than requested "
                    f"({deviation * 100:.0f}% deviation)"
                )
        return None
```

### Solution 4: Improved Prompt with Stricter Instructions

```python
PODCAST_SCRIPT_PROMPT = """You are a professional podcast script writer. Create an engaging podcast dialogue between a HOST and an EXPERT.

Topic/Focus: {user_topic}

Content from documents:
{rag_results}

DURATION REQUIREMENT (CRITICAL):
- Target duration: {duration_minutes} minutes
- Target word count: {word_count} words (at 150 words/minute)
- STRICT REQUIREMENT: Your script MUST be between {min_word_count} and {max_word_count} words
- If you generate too few words, the podcast will be too short and disappoint users
- If you generate too many words, the podcast will exceed the requested duration

Word Count Checkpoints:
- Introduction (HOST): ~{intro_words} words
- Main dialogue: ~{main_words} words
- Conclusion (HOST): ~{conclusion_words} words
- Total: {word_count} words

Example length reference:
[Include a sample dialogue of the correct length]

Format your script as a natural conversation with these guidelines:
[... rest of existing guidelines ...]

BEFORE submitting your script, count the words and ensure you are within the target range.

Generate the complete dialogue script now:"""
```

---

## Implementation Priority

### Critical (Fix Immediately)

1. ✅ **Add static file mounting** for audio serving (1 hour)
2. ✅ **Measure actual audio duration** after generation (2 hours)
3. ✅ **Add duration validation** to output schema (1 hour)

### High Priority (Next Sprint)

4. ⚠️ **Implement word count validation** with retry (4 hours)
5. ⚠️ **Account for voice speed** in word count calculation (2 hours)
6. ⚠️ **Validate collection content** sufficiency (3 hours)

### Medium Priority (Future Enhancement)

7. ⏳ **Adaptive prompt engineering** based on attempt history (8 hours)
8. ⏳ **Section-based generation** like NotebookLM (12 hours)
9. ⏳ **Quality gates** preventing COMPLETED status if duration way off (4 hours)

---

## Test Coverage

### Tests Created

**Location:** `backend/tests/`

1. **Atomic Tests** - `/atomic/test_podcast_duration_atomic.py`
   - Duration calculation verification
   - Validation gap documentation
   - Edge case identification
   - **12 tests, all passing** ✅

2. **Unit Tests (Duration)** - `/unit/test_podcast_duration_control_unit.py`
   - Script generation validation
   - Audio duration measurement
   - Feedback loop testing
   - Voice speed impact analysis
   - **11 tests, all passing** ✅

3. **Unit Tests (Audio Serving)** - `/unit/test_podcast_audio_serving_unit.py`
   - Missing endpoint documentation
   - Solution alternatives
   - CORS requirements
   - **10 tests, all passing** ✅

### Running the Tests

```bash
# Run all podcast duration tests
poetry run pytest tests/atomic/test_podcast_duration_atomic.py -v
poetry run pytest tests/unit/test_podcast_duration_control_unit.py -v
poetry run pytest tests/unit/test_podcast_audio_serving_unit.py -v

# Run all podcast tests
poetry run pytest tests/ -k podcast -v
```

---

## Conclusion

**The fundamental problem:** Podcast generation systems (including ours, NotebookLM, and others) have **NO GUARANTEES** that generated podcasts match requested duration.

**Why it's hard:**

1. LLMs don't reliably respect word count instructions
2. Speaking rate varies with content, voice settings, and TTS implementation
3. No industry-standard solution exists yet

**Our current state:**

- ❌ Files generated but not accessible (audio serving broken)
- ❌ No validation that LLM respects word count
- ❌ No measurement of actual duration
- ❌ No quality gates or warnings

**Recommended path forward:**

1. **Fix audio serving** (critical blocker)
2. **Measure actual duration** (visibility)
3. **Add validation with retry** (quality improvement)
4. **Iterate on prompt engineering** (continuous improvement)

**Realistic expectations:**

- Even with all improvements, expect ±15-20% duration variation
- This is better than current state (no control) but still imperfect
- Similar to NotebookLM's "typically 6-15 minutes" for requested 10-minute podcasts

---

## References

- NotebookLM FAQ: <https://notebooklm.in/notebooklm-podcast-faq/>
- NotebookLM Prompt Engineering: <https://nicolehennig.com/notebooklm-reverse-engineering-the-system-prompt-for-audio-overviews/>
- podgenai (GitHub): <https://github.com/impredicative/podgenai>
- Jellypod Duration Control: <https://jellypod.ai/blog/change-length-duration-notebooklm-podcast>

---

**Document Status:** Analysis Complete
**Tests:** 33 tests created and passing
**Next Steps:** Implement critical fixes (audio serving, duration measurement)
