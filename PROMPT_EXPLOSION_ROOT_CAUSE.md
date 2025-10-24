# Prompt Explosion Root Cause Analysis - October 24, 2025

## Executive Summary

The 6209→4459 character prompt is NOT caused by conversation context size, but by **storing LLM-generated instruction text as part of assistant messages**, which then gets included as "conversation context" in subsequent prompts, creating a feedback loop.

## The Smoking Gun

From `/tmp/watsonx_prompts/prompt_20251024_140413_ee76317f-3b6f-4fea-8b74-56483731f58c.txt`:

### The Prompt Structure (lines 11-77):

```
Question: On what date were the shares purchased?

Context: Conversation context: ...yond the context. Provide a concise answer.

Answer: The shares were purchased on Dec 20, 2024, Dec 6, 2024, Nov 22, 2024, and Nov 8, 2024. On what date were the shares purchased?

Answer: The shares were purchased on Dec 20, 2024, Dec 6, 2024, Nov 22, 2024, and Nov 8, 2024.

## Instruction: Correctly answer the question using the provided context. Do not introduce new information or go beyond the context. Provide a concise answer.

[REPEAT 10+ MORE TIMES]
```

This same Q+A+Instruction pattern is repeated **10+ times** in a single prompt!

## Root Cause Chain

### 1. LLM Generates Response with Instructions

When the LLM generates a response, it includes:
- The actual answer
- Instruction text (e.g., "## Instruction: Correctly answer...")
- Sometimes repeats the question

Example LLM response:
```
Answer: The shares were purchased on Dec 20, 2024, Dec 6, 2024, Nov 22, 2024, and Nov 8, 2024.

## Instruction: Correctly answer the question using the provided context. Do not introduce new information or go beyond the context. Provide a concise answer.
```

### 2. Full LLM Response is Stored as Assistant Message

In `conversation_service.py`, after getting the search result, the assistant message is saved with the **full generated text**:

```python
assistant_message_input = MessageInput(
    session_id=message_input.session_id,
    role="assistant",
    content=search_result.answer,  # <-- This includes "## Instruction:" and repetitions
    ...
)
await self.add_message(assistant_message_input)
```

The `search_result.answer` contains the full LLM response including instructions.

### 3. Messages are Retrieved and Used to Build Context

When processing the next user message, `_build_context_window()` retrieves messages from the database:

```python
messages = await self.get_messages(message_input.session_id, session.user_id)
context = await self.build_context_from_messages(message_input.session_id, messages)
```

### 4. Context Window Includes Full Assistant Responses

From CONTEXT TRACE #1 logs:
```
CONTEXT TRACE #1: context_window length: 2003 chars
CONTEXT TRACE #1: context_window preview: ...yond the context. Provide a concise answer.

Answer: The shares were purchased on Dec 20, 2024, Dec 6, 2024, Nov 22, 2024, and Nov 8, 2024. On what date were the shares purchased?

Answer: The shar...
```

The context window contains:
- The instruction text: "...yond the context. Provide a concise answer."
- The full answers with "Answer:" prefix
- Repeated questions

### 5. This Context is Passed to Next Search

The conversation context (2003 chars) is passed in `config_metadata` to the search service:

```python
search_input = SearchInput(
    question=original_question,
    ...
    config_metadata={
        "conversation_context": context.context_window,  # <-- 2003 chars with instructions
        ...
    }
)
```

### 6. Prompt Template Includes This Context

The prompt template (wherever it is) apparently includes the `conversation_context`, which results in the prompt containing:
- Original question
- "Context: Conversation context: [2003 chars of Q+A+Instructions]"
- The actual search results (not visible in the prompt file)
- The new question again

## Why My Fix Didn't Work

My `_build_context_window()` fix (lines 924-932) looks for these patterns:
```python
if any(pattern in line for pattern in [
    'Context:',
    'Previously discussed:',
    'Participant:',
    'referring to:',
    'in the context of'
]):
    break
```

But the actual patterns in assistant messages are:
- `"## Instruction:"`
- `"Answer:"`
- Question repetitions

These patterns are **NOT** in my removal list!

## The Feedback Loop

1. LLM generates: "Answer: X. ## Instruction: Y"
2. This is stored as assistant message content
3. Next turn, this becomes part of conversation_context
4. LLM sees its own instructions as "context"
5. LLM generates similar pattern again
6. Pattern accumulates over conversation
7. After 17 messages, prompt has 10+ repetitions of Q+A+Instruction

## Evidence from Logs

### Conversation Context at Turn 17 (2003 chars):
```
Building conversation context from 17 messages
context_window length: 2003 chars
```

### Final Prompt (4459 chars):
```
FORMATTED PROMPT LENGTH: 4459 chars
```

### Breakdown:
- Conversation context: 2003 chars (contains repeated Q+A+Instructions)
- Question: ~50 chars
- Template instructions: ~500 chars
- Search results: ~1900 chars
- **Total: ~4450 chars**

The 2003 chars of conversation context is itself mostly **repetitions** of previous Q+A+Instruction patterns.

## The Real Fix Needed

### Option A: Clean Assistant Responses Before Storing (RECOMMENDED)

Before saving assistant messages, strip out instruction text:

```python
# In conversation_service.py, before add_message()
cleaned_answer = self._clean_llm_response(search_result.answer)

assistant_message_input = MessageInput(
    ...
    content=cleaned_answer,  # Store only the answer, not instructions
    ...
)
```

Where `_clean_llm_response()` removes:
- Lines starting with "## Instruction:"
- Lines starting with "##" in general
- Repetitions of the question
- Multiple "Answer:" prefixes

### Option B: Update Pattern List in _build_context_window (PARTIAL FIX)

Add these patterns to the removal list:
```python
if any(pattern in line for pattern in [
    'Context:',
    'Previously discussed:',
    'Participant:',
    'referring to:',
    'in the context of',
    '## Instruction:',  # <-- Add this
    '## ',               # <-- Catch all "##" markdown headers
    'Answer:',           # <-- Add this
]):
    break
```

But this is fragile because:
1. It depends on specific text patterns
2. LLM might generate variations
3. We're fixing symptoms, not the root cause

### Option C: Only Include First Sentence of Assistant Responses

In `_build_context_window()`, for assistant messages:
```python
if msg.role == "assistant":
    # Extract only first sentence (the actual answer)
    sentences = msg.content.split('. ')
    if sentences:
        core_answer = sentences[0] + '.'
        context_parts.append(f"Assistant: {core_answer}")
```

### Recommended Approach

**Use Option A + Option C together**:

1. **Option A**: Clean responses before storing to prevent pollution
2. **Option C**: Only use first sentence in context window as additional safety

This provides defense in depth:
- Option A prevents bad data from entering the database
- Option C prevents any existing bad data from polluting prompts

## Impact Assessment

### Before Fixes:
- Prompt grows from ~1000 chars (turn 1) to ~6209 chars (turn 17)
- Contains 10+ repetitions of instruction text
- LLM starts repeating the pattern in its responses
- User sees repeated instructions in chat

### After Option A Fix:
- Prompt stays ~1000-2000 chars regardless of turn count
- Contains only actual Q&A content
- No instruction text in conversation context
- Clean, concise responses

### After Both Fixes:
- Maximum conversation context: ~200 chars per message * 10 messages = 2000 chars
- All instruction text removed
- Only first sentence of each answer included
- Prompt stable across all turns

## Next Steps

1. **Implement Option A**: Add `_clean_llm_response()` method
2. **Update _build_context_window**: Add missing patterns (Option B)
3. **Test with fresh conversation**: Verify prompts stay < 2000 chars
4. **Consider database migration**: Clean existing assistant messages

## Files to Modify

1. `backend/rag_solution/services/conversation_service.py`
   - Add `_clean_llm_response()` method
   - Call it before `add_message()` for assistant messages
   - Update `_build_context_window()` pattern list
   - Consider Option C (first sentence only)

2. Test script to verify:
   - Start new conversation
   - Ask 10+ questions
   - Check prompt size stays constant
   - Verify no instruction text in conversation context

---

**Analysis Date**: October 24, 2025
**Analyzer**: Claude Code
**Status**: Root cause identified, fix recommended
