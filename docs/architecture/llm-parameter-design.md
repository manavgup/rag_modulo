# LLM Parameter Design Philosophy

## Overview

This document outlines the design philosophy for LLM parameter management in RAG Modulo, focusing on flexibility, safety, and user experience.

## Design Principles

### 1. **Sensible Defaults with Runtime Overrides** ✅ (Current Approach)

Your current design is optimal:

```
System Defaults → User Preferences → Context-Specific Overrides
```

**Example Flow:**
1. **System starts** with safe defaults (`max_new_tokens: 100`)
2. **User configures** via UI/API (stored in database)
3. **Service overrides** for specific use cases (podcast: `max_new_tokens: 8100`)

**Benefits:**
- ✅ Safe for new users (conservative defaults)
- ✅ Flexible for advanced users (UI configuration)
- ✅ Context-aware (services can override for specialized tasks)
- ✅ No restart required (runtime configuration)

### 2. **Layer Architecture**

```
┌─────────────────────────────────────────┐
│  Service-Specific Overrides (Highest)  │  ← Podcast, long-form content
├─────────────────────────────────────────┤
│  User Preferences (UI Configured)      │  ← Per-user customization
├─────────────────────────────────────────┤
│  System Defaults (Code/Config)         │  ← Safe fallback values
└─────────────────────────────────────────┘
```

## Implementation Details

### Default Values (Code)

**Location:** `backend/rag_solution/schemas/llm_parameters_schema.py`

```python
class LLMParametersInput(LLMParametersBase):
    max_new_tokens: int = Field(
        default=100,  # Conservative default
        ge=1,         # Minimum (must generate something)
        # NO upper limit - model-dependent
        description="Maximum tokens (WatsonX ~2K, GPT-4 ~128K, Claude ~200K)"
    )
```

**Design Rationale:**
- **No `le` (upper limit)**: Different models have vastly different capabilities
- **Low default (100)**: Safe for general Q&A, fast responses
- **Descriptive**: Documents model-specific limits

### User Configuration (Database)

**Location:** `llm_parameters` table

**Access Methods:**
1. **REST API:** `/api/users/{user_id}/llm-parameters`
2. **UI:** Settings page (to be implemented)
3. **CLI:** `rag-cli config llm-params set`

**User Benefits:**
- Persist preferences across sessions
- Different configs for different tasks
- Team-wide or personal settings

### Service Overrides (Runtime)

**Location:** Service-specific logic (e.g., `podcast_service.py`)

```python
# Override for long-form content
podcast_params = LLMParametersInput(
    user_id=user_id,
    max_new_tokens=max_word_count * 3,  # Context-specific calculation
    temperature=0.7,
    # ... other params
)

llm_provider.generate_text(model_parameters=podcast_params)
```

**When to Use Service Overrides:**
- Task requires significantly different parameters
- Safety-critical operations (lower temperature)
- Long-form content (higher token limits)
- Batch processing (higher batch sizes)

## Best Practices

### 1. **Progressive Disclosure**

```
Basic UI: [Temperature] [Max Tokens]
         ↓ "Show Advanced"
Advanced: [Top-K] [Top-P] [Repetition Penalty] [Batch Size] [etc.]
```

**Rationale:** Most users only need 2-3 parameters, advanced users get full control.

### 2. **Validation at Multiple Levels**

```python
# Schema-level: Basic constraints
max_new_tokens: int = Field(ge=1, description="...")

# Service-level: Business logic
if task == "podcast" and max_new_tokens < 1000:
    logger.warning("Podcast may be truncated with %d tokens", max_new_tokens)

# Provider-level: Model-specific limits
if model == "watsonx-granite" and max_new_tokens > 2048:
    logger.warning("WatsonX Granite limited to 2048 tokens, will truncate")
    max_new_tokens = 2048
```

### 3. **Document Model Capabilities**

**Maintain a model registry:**

```python
MODEL_CAPABILITIES = {
    "ibm/granite-3-8b-instruct": {
        "max_tokens": 2048,
        "context_window": 8192,
        "supports_streaming": True,
    },
    "gpt-4-turbo": {
        "max_tokens": 4096,
        "context_window": 128000,
        "supports_streaming": True,
    },
    "claude-3-opus": {
        "max_tokens": 4096,
        "context_window": 200000,
        "supports_streaming": True,
    },
}
```

**Use for:**
- UI hints: "Your model supports up to 2048 tokens"
- Automatic validation: Warn if exceeding model capability
- Smart defaults: Suggest optimal parameters per model

### 4. **Presets for Common Tasks**

```python
PARAMETER_PRESETS = {
    "qa_short": {
        "max_new_tokens": 100,
        "temperature": 0.3,  # More focused
        "top_p": 0.9,
    },
    "creative_writing": {
        "max_new_tokens": 2000,
        "temperature": 0.9,  # More creative
        "top_p": 0.95,
    },
    "podcast_15min": {
        "max_new_tokens": 8100,
        "temperature": 0.7,
        "top_p": 0.95,
        "repetition_penalty": 1.1,
    },
}
```

**UI Flow:**
```
[Preset: Custom ▼]
  - Short Q&A
  - Creative Writing
  - Podcast (15 min)
  - Podcast (30 min)
  - Custom...
```

## Migration Path

### Phase 1: ✅ **Current State**
- Sensible defaults in code
- Database storage for user preferences
- Service-level overrides working

### Phase 2: **UI Configuration** (Next)
```
Location: frontend/src/components/settings/LLMParametersSettings.tsx

Features:
- Edit default parameters
- Create named configurations
- Preview token costs
- Model-specific hints
```

### Phase 3: **Per-Collection Settings**
```
Allow different LLM parameters per collection:
- Legal documents: Higher accuracy (low temperature)
- Creative content: Higher creativity (high temperature)
- Technical docs: Balanced parameters
```

### Phase 4: **A/B Testing & Analytics**
```
Track which parameters work best:
- User satisfaction scores
- Completion rates
- Token efficiency
- Response quality metrics
```

## Configuration Hierarchy (Resolution Order)

```python
def resolve_llm_parameters(
    user_id: UUID4,
    task_type: str,
    collection_id: UUID4 | None = None,
    explicit_params: LLMParametersInput | None = None
) -> LLMParametersInput:
    """
    Resolve LLM parameters from multiple sources.

    Priority (highest to lowest):
    1. Explicit parameters (function argument)
    2. Task-specific overrides (service-level)
    3. Collection-specific settings
    4. User preferences (database)
    5. System defaults (schema)
    """

    # 5. Start with system defaults
    params = get_system_defaults()

    # 4. Override with user preferences
    if user_prefs := get_user_preferences(user_id):
        params.update(user_prefs)

    # 3. Override with collection settings
    if collection_id:
        if collection_prefs := get_collection_preferences(collection_id):
            params.update(collection_prefs)

    # 2. Override with task-specific settings
    if task_preset := TASK_PRESETS.get(task_type):
        params.update(task_preset)

    # 1. Override with explicit parameters (highest priority)
    if explicit_params:
        params.update(explicit_params)

    return params
```

## Security Considerations

### 1. **Token Limits = Cost Control**

```python
# Per-user monthly token budget
USER_MONTHLY_BUDGET = {
    "free": 100_000,      # ~$1-5/month
    "pro": 1_000_000,     # ~$10-50/month
    "enterprise": None,   # Unlimited
}

# Enforce at service level
if user_token_usage + requested_tokens > user_budget:
    raise QuotaExceededError("Monthly token limit reached")
```

### 2. **Rate Limiting**

```python
# Prevent abuse
MAX_CONCURRENT_REQUESTS = {
    "free": 1,
    "pro": 5,
    "enterprise": 20,
}
```

### 3. **Parameter Validation**

```python
# Prevent malicious/inefficient requests
if max_new_tokens > 100_000:
    # Even for Claude's 200K context, 100K output is excessive
    raise ValidationError("max_new_tokens exceeds reasonable limit")

if temperature > 1.5:
    # Very high temperature = gibberish
    logger.warning("Unusually high temperature, may produce poor results")
```

## Recommended UI/UX

### Settings Page Mock

```
┌─────────────────────────────────────────────────┐
│  LLM Parameters                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  Configuration: [My Default ▼] [New] [Delete]  │
│                                                 │
│  Basic Settings:                                │
│  ┌───────────────────────────────────────┐     │
│  │ Max Tokens:  [    2000     ]          │     │
│  │              Adjust based on response │     │
│  │              length (100-100K)        │     │
│  │                                       │     │
│  │ Temperature: [●─────────] 0.7        │     │
│  │              Lower = focused          │     │
│  │              Higher = creative        │     │
│  └───────────────────────────────────────┘     │
│                                                 │
│  [▼ Show Advanced Settings]                    │
│                                                 │
│  Model Info:                                    │
│  ┌───────────────────────────────────────┐     │
│  │ Current Model: ibm/granite-3-3-8b-inst│     │
│  │ Max Tokens:    2,048                  │     │
│  │ Context:       8,192 tokens           │     │
│  │                                       │     │
│  │ ⚠️  Your max_tokens (2000) is close  │     │
│  │    to the model limit.                │     │
│  └───────────────────────────────────────┘     │
│                                                 │
│  [Save]  [Reset to Defaults]  [Test]           │
└─────────────────────────────────────────────────┘
```

## Conclusion

**Your current design philosophy is optimal:**

✅ **Start with safe defaults** (code-level)
✅ **Allow user customization** (database + UI)
✅ **Enable context-specific overrides** (service-level)
✅ **No upper token limits** (model-dependent)
✅ **Runtime configuration** (no restarts needed)

**Next Steps:**
1. ✅ Remove `le=2048` limit (done)
2. 🔄 Build UI for parameter configuration
3. 🔄 Add parameter presets for common tasks
4. 🔄 Implement token budget/quota system
5. 🔄 Add model capability registry

This approach balances **flexibility** (power users), **safety** (new users), and **efficiency** (context-aware optimization).
