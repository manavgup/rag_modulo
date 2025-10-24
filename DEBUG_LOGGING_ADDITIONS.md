# Debug Logging Additions to Trace Prompt Construction

This document describes debug logging that should be added to trace how the 6209-character prompt is constructed.

## Flow Overview

```
User Question
    ↓
ConversationService.process_user_message()
    ├→ build_context_from_messages()  [conversation context]
    ├→ enhance_question_with_context()  [enhanced question]
    ├→ Creates SearchInput with config_metadata
    ↓
SearchService.search()
    ├→ Logs config_metadata received
    ├→ pipeline_service.execute_pipeline()
    ↓
PipelineService.execute_pipeline()
    ├→ Retrieves documents
    ├→ Builds prompt with conversation context
    ├→ Calls LLM provider
    ↓
WatsonXLLM.generate_text()
    ├→ Formats prompt with template
    ├→ Saves to /tmp/watsonx_prompts/
    ├→ Sends to IBM WatsonX
```

## Logging Points Needed

### 1. conversation_service.py - Context Building

```python
# In process_user_message() around line 307
logger.info("="*80)
logger.info("CONTEXT TRACE #1: Building conversation context")
context = await self.build_context_from_messages(message_input.session_id, messages)
logger.info("CONTEXT TRACE #1: conversation_context length: %d chars", len(context.context_window))
logger.info("CONTEXT TRACE #1: context_window preview: %s...", context.context_window[:200])
logger.info("CONTEXT TRACE #1: context_metadata: %s", context.context_metadata)
logger.info("="*80)

# In enhance_question_with_context() around line 318
logger.info("="*80)
logger.info("CONTEXT TRACE #2: Enhancing question with context")
logger.info("CONTEXT TRACE #2: original_question: %s", message_input.content)
logger.info("CONTEXT TRACE #2: conversation_context length: %d chars", len(context.context_window))
enhanced_question_for_llm = await self.enhance_question_with_context(...)
logger.info("CONTEXT TRACE #2: enhanced_question_for_llm: %s", enhanced_question_for_llm)
logger.info("CONTEXT TRACE #2: enhancement added: %d chars", len(enhanced_question_for_llm) - len(original_question))
logger.info("="*80)

# When creating SearchInput around line 335
logger.info("="*80)
logger.info("CONTEXT TRACE #3: Creating SearchInput")
search_input = SearchInput(...)
logger.info("CONTEXT TRACE #3: question (for embedding): %s", original_question)
logger.info("CONTEXT TRACE #3: config_metadata keys: %s", list(search_input.config_metadata.keys()))
logger.info("CONTEXT TRACE #3: conversation_context in metadata: %d chars",
            len(search_input.config_metadata.get('conversation_context', '')))
logger.info("CONTEXT TRACE #3: enhanced_question_for_llm in metadata: %s",
            search_input.config_metadata.get('enhanced_question_for_llm', '')[:100])
logger.info("CONTEXT TRACE #3: message_history count: %d",
            len(search_input.config_metadata.get('message_history', [])))
logger.info("="*80)
```

### 2. search_service.py - Search Entry

```python
# At start of search() method around line 598
logger.info("="*80)
logger.info("CONTEXT TRACE #4: SearchService.search() entry")
logger.info("CONTEXT TRACE #4: question: %s", search_input.question)
logger.info("CONTEXT TRACE #4: user_id: %s", search_input.user_id)
logger.info("CONTEXT TRACE #4: collection_id: %s", search_input.collection_id)
if search_input.config_metadata:
    logger.info("CONTEXT TRACE #4: config_metadata keys: %s", list(search_input.config_metadata.keys()))
    logger.info("CONTEXT TRACE #4: conversation_context length: %d chars",
                len(search_input.config_metadata.get('conversation_context', '')))
    logger.info("CONTEXT TRACE #4: conversation_context preview: %s...",
                search_input.config_metadata.get('conversation_context', '')[:200])
    logger.info("CONTEXT TRACE #4: enhanced_question_for_llm: %s",
                search_input.config_metadata.get('enhanced_question_for_llm', ''))
    logger.info("CONTEXT TRACE #4: cot_enabled: %s",
                search_input.config_metadata.get('cot_enabled', False))
logger.info("="*80)
```

### 3. pipeline_service.py - Pipeline Execution

```python
# In execute_pipeline() method
logger.info("="*80)
logger.info("CONTEXT TRACE #5: PipelineService.execute_pipeline() entry")
logger.info("CONTEXT TRACE #5: search_input.question: %s", search_input.question)
logger.info("CONTEXT TRACE #5: collection_name: %s", collection_name)
logger.info("CONTEXT TRACE #5: pipeline_id: %s", pipeline_id)
if search_input.config_metadata:
    logger.info("CONTEXT TRACE #5: config_metadata present: %s", list(search_input.config_metadata.keys()))
logger.info("="*80)

# Before calling generate_answer (wherever that is in pipeline)
logger.info("="*80)
logger.info("CONTEXT TRACE #6: Building prompt for LLM")
logger.info("CONTEXT TRACE #6: retrieved_chunks count: %d", len(retrieved_chunks))
logger.info("CONTEXT TRACE #6: total chunks text length: %d chars",
            sum(len(chunk.text) for chunk in retrieved_chunks))
logger.info("CONTEXT TRACE #6: conversation_context from metadata: %d chars",
            len(search_input.config_metadata.get('conversation_context', '') if search_input.config_metadata else ''))
logger.info("CONTEXT TRACE #6: enhanced_question_for_llm: %s",
            search_input.config_metadata.get('enhanced_question_for_llm', '') if search_input.config_metadata else '')
# Log the actual prompt being constructed
logger.info("CONTEXT TRACE #6: About to construct final prompt with template")
logger.info("="*80)
```

### 4. Chain of Thought Service (if CoT is used)

```python
# In execute_chain_of_thought() method
logger.info("="*80)
logger.info("CONTEXT TRACE #7: CoT Service - execute_chain_of_thought() entry")
logger.info("CONTEXT TRACE #7: cot_input.question: %s", cot_input.question)
logger.info("CONTEXT TRACE #7: context_documents count: %d", len(context_documents))
logger.info("CONTEXT TRACE #7: total context_documents length: %d chars",
            sum(len(doc) for doc in context_documents))
if hasattr(cot_input, 'config_metadata') and cot_input.config_metadata:
    logger.info("CONTEXT TRACE #7: config_metadata keys: %s", list(cot_input.config_metadata.keys()))
    logger.info("CONTEXT TRACE #7: conversation_context: %d chars",
                len(cot_input.config_metadata.get('conversation_context', '')))
logger.info("="*80)
```

### 5. Prompt Template Service - Template Formatting

```python
# In format_prompt_with_template() method
logger.info("="*80)
logger.info("CONTEXT TRACE #8: PromptTemplateService.format_prompt_with_template()")
logger.info("CONTEXT TRACE #8: template.name: %s", template.name if hasattr(template, 'name') else 'unknown')
logger.info("CONTEXT TRACE #8: template.content length: %d chars", len(template.content) if hasattr(template, 'content') else 0)
logger.info("CONTEXT TRACE #8: variables keys: %s", list(variables.keys()) if variables else [])
if variables:
    for key, value in variables.items():
        if isinstance(value, str):
            logger.info("CONTEXT TRACE #8: variable '%s': %d chars, preview: %s...",
                        key, len(value), value[:100])
        else:
            logger.info("CONTEXT TRACE #8: variable '%s': type %s", key, type(value).__name__)

# After formatting
formatted_prompt_length = len(formatted_prompt)
logger.info("CONTEXT TRACE #8: FINAL FORMATTED PROMPT LENGTH: %d chars", formatted_prompt_length)
if formatted_prompt_length > 2000:
    logger.warning("CONTEXT TRACE #8: ⚠️  LARGE PROMPT DETECTED: %d chars", formatted_prompt_length)
logger.info("CONTEXT TRACE #8: formatted_prompt preview (first 300 chars): %s...", formatted_prompt[:300])
logger.info("CONTEXT TRACE #8: formatted_prompt preview (last 300 chars): ...%s", formatted_prompt[-300:])
logger.info("="*80)
```

## Expected Output Pattern

When a search is executed, you should see logs like:

```
CONTEXT TRACE #1: conversation_context length: 1523 chars
CONTEXT TRACE #2: enhancement added: 87 chars
CONTEXT TRACE #3: conversation_context in metadata: 1523 chars
CONTEXT TRACE #4: conversation_context length: 1523 chars
CONTEXT TRACE #5: config_metadata present: ['conversation_context', 'enhanced_question_for_llm', ...]
CONTEXT TRACE #6: conversation_context from metadata: 1523 chars
CONTEXT TRACE #7: conversation_context: 1523 chars (if CoT)
CONTEXT TRACE #8: FINAL FORMATTED PROMPT LENGTH: 6209 chars  <-- THIS IS WHERE IT EXPLODES
CONTEXT TRACE #8: variable 'context': 3200 chars
CONTEXT TRACE #8: variable 'conversation_context': 1523 chars
CONTEXT TRACE #8: variable 'question': 150 chars
...
```

## What to Look For

1. **Where does the context grow?** - Trace lengths at each step
2. **What variables are in the template?** - See what gets substituted
3. **Is context doubled?** - Check if conversation_context appears multiple times
4. **Is enhanced_question used incorrectly?** - Should only be for LLM, not embedding
5. **Does template include conversation_context?** - Check if RAG template expects it

## Next Steps After Logging

1. Run a simple search query
2. Collect all CONTEXT TRACE logs
3. Identify which step causes the explosion (1523 chars → 6209 chars)
4. Examine the prompt template at that step
5. Fix the template or the context passing logic
