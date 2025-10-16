# Podcast Implementation Plan

## Current State Analysis

### ✅ What We Have

1. **Script Generation Endpoint** (`POST /api/podcasts/generate-script`)
   - ✅ Supports all new fields: `podcast_style`, `language`, `complexity_level`, `include_chapter_markers`, `generate_transcript`
   - ✅ Returns quality metrics (word count, duration, format validation)
   - ✅ Fast (~30s) and cost-effective (~$0.01-0.05)

2. **Full Podcast Generation** (`POST /api/podcasts/generate`)
   - ✅ Supports all new fields in schema
   - ✅ Generates script + audio asynchronously
   - ❓ **Need to verify**: Are new fields actually used in the prompt generation?

3. **Other Endpoints**
   - ✅ `GET /api/podcasts/{podcast_id}` - Get status
   - ✅ `GET /api/podcasts/` - List podcasts
   - ✅ `DELETE /api/podcasts/{podcast_id}` - Delete podcast
   - ✅ `GET /api/podcasts/voice-preview/{voice_id}` - Preview voices

### ❌ What We're Missing

**Script-to-Audio Endpoint** - No dedicated endpoint to convert an existing script to audio.

---

## Recommendations

### **Item 1: Script-to-Audio Endpoint**

#### **Should We Add It?**

**YES** - This is valuable for the following workflow:

```
1. Generate Script → Review/Edit → Convert to Audio
   ↓                  ↓              ↓
   POST /generate-    User reviews   POST /script-to-audio
   script             & edits        (NEW ENDPOINT)
```

#### **Use Cases**

- **Quality Control**: Generate script, review it, then synthesize only if satisfied
- **Cost Optimization**: Skip TTS for bad scripts
- **Script Editing**: Users can edit the generated script before audio generation
- **Batch Processing**: Generate multiple scripts, review them, then batch-convert the good ones
- **A/B Testing**: Generate same script with different voices/speeds

#### **Proposed Endpoint**

```python
@router.post(
    "/script-to-audio",
    response_model=PodcastGenerationOutput,
    status_code=202,
    summary="Convert script to audio (no script generation)",
)
async def generate_audio_from_script(
    audio_input: PodcastAudioGenerationInput,
    background_tasks: BackgroundTasks,
    ...
) -> PodcastGenerationOutput:
    """
    Convert an existing podcast script to audio.

    Use Cases:
    - Generate audio from previously generated script
    - Generate audio from user-edited script
    - Re-generate audio with different voices/settings

    Cost: ~$0.05-0.80 (TTS only, no LLM)
    Time: ~30-90 seconds (depending on duration)
    """
```

#### **New Schema Required**

```python
class PodcastAudioGenerationInput(BaseModel):
    """Input for generating audio from existing script."""

    collection_id: UUID  # For tracking/permissions
    script_text: str = Field(..., min_length=100)  # The actual script
    title: str
    duration: PodcastDuration

    # Audio settings
    host_voice: str = Field(default="alloy")
    expert_voice: str = Field(default="onyx")
    audio_format: AudioFormat = Field(default=AudioFormat.MP3)

    # Optional
    description: str | None = None
    include_intro: bool = False
    include_outro: bool = False
```

#### **Implementation Steps**

1. **Add Schema** (`podcast_schema.py`)
   - Create `PodcastAudioGenerationInput`
   - Validate script format (must have HOST/EXPERT structure)

2. **Add Service Method** (`podcast_service.py`)
   - Create `generate_audio_from_script()` method
   - Reuse existing `_parse_script()` and `_generate_audio()` methods
   - Skip RAG retrieval and LLM script generation

3. **Add Router Endpoint** (`podcast_router.py`)
   - Add `POST /script-to-audio` endpoint
   - Background task for async processing
   - Same status tracking as full generation

4. **Test Workflow**

   ```bash
   # Step 1: Generate script
   SCRIPT=$(curl -X POST /api/podcasts/generate-script ... | jq -r '.script_text')

   # Step 2: Review script (user edits if needed)

   # Step 3: Generate audio
   curl -X POST /api/podcasts/script-to-audio \
     -d "{ \"script_text\": \"$SCRIPT\", ...}"
   ```

---

### **Item 2: New Field Support**

#### **Fields to Test**

1. `podcast_style`: `conversational_interview`, `narrative`, `educational`, `discussion`
2. `complexity_level`: `beginner`, `intermediate`, `advanced`
3. `language`: `en`, `es`, `fr`, `de`, etc.
4. `include_chapter_markers`: `true`/`false`
5. `generate_transcript`: `true`/`false`

#### **What Needs to Happen**

The schemas already support these fields, but we need to ensure they're **used in the prompt**.

**Check Required**:

1. Are these fields passed to the LLM prompt template?
2. Does the prompt template use them to guide generation?
3. Are they stored in the database for later reference?

#### **Current Prompt Template Location**

- `backend/rag_solution/services/podcast_service.py` → `_generate_script()` method
- Uses `PromptTemplateService` to load `PODCAST_GENERATION` template
- Template stored in database (`prompt_templates` table)

#### **Implementation Steps**

1. **Review Prompt Template** (`podcast_service.py`)

   ```python
   # In _generate_script() method
   prompt = loaded_template.system_prompt.format(
       duration_minutes=duration_minutes,
       podcast_style=podcast_input.podcast_style,  # ← ADD THIS
       language=podcast_input.language,            # ← ADD THIS
       complexity_level=podcast_input.complexity_level,  # ← ADD THIS
       rag_results=rag_results,
       ...
   )
   ```

2. **Update Prompt Template** (database or code)

   ```
   System: You are a podcast script writer.

   Generate a {podcast_style} podcast script in {language} language.
   Target audience: {complexity_level} level.
   Duration: {duration_minutes} minutes.

   Style Guidelines:
   - conversational_interview: Q&A format with engaging questions
   - narrative: Storytelling approach with smooth transitions
   - educational: Structured learning with clear explanations
   - discussion: Debate-style with multiple perspectives

   Complexity Guidelines:
   - beginner: Simple language, basic concepts, more explanations
   - intermediate: Standard terminology, moderate depth
   - advanced: Technical language, deep analysis, assume prior knowledge

   Content: {rag_results}
   ```

3. **Test Each Field**

   ```bash
   # Test podcast_style
   curl -X POST /api/podcasts/generate-script \
     -d '{"podcast_style": "narrative", ...}'

   # Test complexity_level
   curl -X POST /api/podcasts/generate-script \
     -d '{"complexity_level": "beginner", ...}'

   # Test language
   curl -X POST /api/podcasts/generate-script \
     -d '{"language": "es", ...}'
   ```

4. **Verify ALL Endpoints**
   - ✅ `POST /generate-script` - Already has fields
   - ❓ `POST /generate` - Has fields in schema, verify they're used
   - 🆕 `POST /script-to-audio` - New endpoint, will support from start

---

## Recommended Implementation Order

### **Phase 1: Verify & Fix Current Endpoints** (30 minutes)

1. ✅ Check if `POST /generate` uses new fields in prompt
2. ✅ Update prompt template to include new fields
3. ✅ Test `POST /generate-script` with different field values
4. ✅ Verify output quality changes based on fields

### **Phase 2: Add Script-to-Audio Endpoint** (1-2 hours)

1. ✅ Create `PodcastAudioGenerationInput` schema
2. ✅ Add `generate_audio_from_script()` service method
3. ✅ Add `POST /script-to-audio` router endpoint
4. ✅ Test complete workflow (script → edit → audio)

### **Phase 3: Integration Testing** (30 minutes)

1. ✅ Test all endpoints with new fields
2. ✅ Verify different podcast styles produce different outputs
3. ✅ Test different languages (if supported by model)
4. ✅ Document findings and limitations

---

## Testing Strategy

### **Test Matrix**

| Field | Values to Test | Expected Impact |
|-------|---------------|-----------------|
| `podcast_style` | `conversational_interview`, `narrative`, `educational`, `discussion` | Script structure and tone changes |
| `complexity_level` | `beginner`, `intermediate`, `advanced` | Language complexity and depth changes |
| `language` | `en`, `es` (if supported) | Generated script in target language |
| `include_chapter_markers` | `true`, `false` | Chapter markers in output |
| `generate_transcript` | `true`, `false` | Transcript generation |

### **Success Criteria**

1. **Prompt Integration**
   - ✅ All fields are passed to LLM prompt
   - ✅ Prompt template uses fields effectively
   - ✅ Output quality varies based on field values

2. **Script-to-Audio Endpoint**
   - ✅ Successfully converts script to audio
   - ✅ Respects voice and format settings
   - ✅ Returns proper status tracking
   - ✅ Cost: TTS only (~60% cheaper than full generation)

3. **All Endpoints**
   - ✅ `POST /generate` - Full generation with new fields
   - ✅ `POST /generate-script` - Script only with new fields
   - ✅ `POST /script-to-audio` - Audio from script (NEW)

---

## Next Steps

**Your Decision Point:**

**Option A: Quick Win (Recommended for MVP)**

1. Verify current endpoints use new fields (15 min)
2. Test with different field values (15 min)
3. Document any limitations
4. **Skip** script-to-audio endpoint for now

**Option B: Complete Implementation**

1. Verify current endpoints (15 min)
2. Update prompt templates (15 min)
3. Add script-to-audio endpoint (1-2 hours)
4. Full integration testing (30 min)

**My Recommendation**: **Option B** - The script-to-audio endpoint is highly valuable for quality control and cost optimization. It's a natural complement to the script-only generation endpoint.

**Estimated Total Time**: 2-3 hours for complete implementation and testing.

---

## Questions for User

1. **Priority**: Do you want the script-to-audio endpoint now, or is it lower priority?
2. **Language Support**: Should we test multi-language support, or focus on English for now?
3. **Prompt Templates**: Should we update the prompt template in code or database?
4. **Testing Depth**: Quick smoke tests or comprehensive testing across all field combinations?
