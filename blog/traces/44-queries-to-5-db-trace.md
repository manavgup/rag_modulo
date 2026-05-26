# From 44 DB Queries to 5: A Complete Query-by-Query Trace (Issue #777)

*Every SQL query during a single search request, mapped to its source file and elimination plan.*

![Query reduction](../diagrams/05-query-reduction.svg)

## Complete Query Map (post-PipelineContext PR)

Every query during a search, with its source and elimination plan.

### Pre-Search: Orchestrator Construction (Q1-Q8)

These happen BEFORE `process_user_message()` — during FastAPI `Depends()` resolution
when constructing the orchestrator.

| # | Time | Table | Source | Fix |
|:-:|------|-------|--------|-----|
| Q1 | :44,021 | sessions JOIN all | `conversation_router` → `get_session()` for auth | **A**: Pass session to orchestrator |
| Q2 | :44,044 | sessions JOIN all | `conversation_router` → `get_conversations()` (frontend) | **Frontend**: stop duplicate call |
| Q3 | :44,088 | sessions JOIN all | Same — frontend duplicate | **Frontend**: deduplicate |
| Q4 | :44,091 | sessions JOIN all | `get_session()` by id (frontend detail view) | **Frontend**: already fetched in Q1 |
| Q5 | :44,094 | messages (by pk) | `get_messages()` (frontend) | **Frontend**: separate request |
| Q6 | :44,110 | llm_providers (default) | `dependencies.py:406` → `get_default_provider()` for CoT check | **B**: Remove CoT eager init |
| Q7 | :44,120 | sessions JOIN all | WebSocket handler re-fetches session | **Frontend**: deduplicate |
| Q8 | :44,131 | sessions JOIN all | Orchestrator `process_user_message` → `get_session_by_id()` | **A**: Use session from Q1 |

### Search Start: Message Storage + Context (Q9-Q11)

| # | Time | Table | Source | Fix |
|:-:|------|-------|--------|-----|
| Q9 | :44,133 | INSERT messages | Store user question | **KEEP** (required) |
| Q10 | :44,137 | messages (by pk) | `db.refresh()` after insert | **C**: Skip refresh, use returned object |
| Q11 | :44,138 | messages (by pk) | `get_messages_by_session()` for context | **C**: Append Q9 result to existing list |

### PipelineContext Fetch (Q12-Q17)

| # | Time | Table | Source | Fix |
|:-:|------|-------|--------|-----|
| Q12 | :44,143 | llm_providers (default) | PipelineContextRepository query #1 | **KEEP** (PipelineContext) |
| Q13 | :44,147 | llm_models | PipelineContextRepository query #2 | **KEEP** (PipelineContext) |
| Q14 | :44,149 | llm_parameters | PipelineContextRepository query #3 | **KEEP** (PipelineContext) |
| Q15 | :44,152 | users (by ibm_id) | PipelineContextRepository — user lookup | **D**: Include in JOIN or remove |
| Q16 | :44,153 | prompt_templates (by type) | PipelineContextRepository query #4 | **KEEP** (PipelineContext) |
| Q17 | :44,155 | collections (simple) | PipelineContextRepository query #5 | **KEEP** (PipelineContext) |

### Search Service Init (Q18-Q22)

| # | Time | Table | Source | Fix |
|:-:|------|-------|--------|-----|
| Q18 | :44,316 | user_collection JOIN | `search_service._search_with_pipeline()` → `collection_service.get_collection()` | **E**: Already have collection from Q17 |
| Q19 | :44,331 | user_collection JOIN | Duplicate (eager loading cascade) | **E**: Same fix |
| Q20 | :44,334 | llm_providers (default) | `LLMProviderFactory.get_provider()` → `get_default_provider()` | **F**: Use PipelineContext.provider |
| Q21 | :44,336 | llm_providers (by name) | `WatsonXLLM.initialize_client()` → `get_provider_by_name()` | **F**: Pass config from PipelineContext |
| Q22 | :45,575 | llm_models | `LLMModelService.get_models_by_provider()` during WatsonX init | **F**: Use PipelineContext.models |

### Pipeline Stage 3: Retrieval (Q23-Q26)

| # | Time | Table | Source | Fix |
|:-:|------|-------|--------|-----|
| Q23 | :47,289 | collections (simple) | `pipeline_service._retrieve_documents()` → collection lookup | **E**: Already in PipelineContext |
| Q24 | :47,305 | llm_providers (by name) | `get_embeddings_for_vector_store()` → new `LLMProviderFactory` | **G**: Pass factory/provider |
| Q25 | :48,216 | llm_models | Same — models for embedding provider | **G**: Pass from PipelineContext |
| Q26 | :50,324 | files | `file_management_service.get_files_by_collection()` for doc metadata | **KEEP** (needed for UI sources) |

### Frontend Interrupt During Reranking (Q27-Q28)

| # | Time | Table | Source | Fix |
|:-:|------|-------|--------|-----|
| Q27 | :51,747 | sessions JOIN all | Frontend GET /api/conversations (polling) | **Frontend**: debounce |
| Q28 | :51,758 | user_collection JOIN | Frontend GET /api/collections (polling) | **Frontend**: debounce |

### Pipeline Stage 6: Generation (Q29-Q37)

| # | Time | Table | Source | Fix |
|:-:|------|-------|--------|-----|
| Q29 | :51,941 | pipeline_configs | `_validate_configuration()` → `pipeline_repository.get_by_id()` | **H**: Use PipelineContext |
| Q30 | :51,943 | llm_providers (by pk) | `_validate_configuration()` → `get_provider_by_id()` | **H**: Use PipelineContext |
| Q31 | :51,944 | llm_parameters | `_validate_configuration()` → `get_latest_or_default()` | **H**: Use PipelineContext |
| Q32 | :51,945 | users (by ibm_id) | `_validate_configuration()` → user lookup for provider | **H**: Use PipelineContext |
| Q33 | :51,946 | llm_providers (default) | `LLMProviderFactory.get_provider()` in generation | **H**: Reuse provider from retrieval |
| Q34 | :51,946 | llm_providers (by name) | `WatsonXLLM.initialize_client()` (3rd time!) | **H**: Reuse provider |
| Q35 | :53,058 | llm_models | Models for generation provider | **H**: Use PipelineContext |
| Q36 | :54,154 | prompt_templates (by type) | `_get_templates()` → `get_rag_template()` | **H**: Use PipelineContext |
| Q37 | :54,160 | prompt_templates (by id) | `format_prompt_by_id()` → re-fetches template | **H**: Already have it |

### Post-Generation: Token Tracking + Store (Q38-Q44)

| # | Time | Table | Source | Fix |
|:-:|------|-------|--------|-----|
| Q38 | :56,035 | users (by ibm_id) | `_serialize_response()` → `get_user_provider()` | **I**: Use PipelineContext |
| Q39 | :56,036 | llm_providers (default) | Same → `get_default_provider()` fallback | **I**: Use PipelineContext |
| Q40 | :56,038 | SUM(token_count) | `token_tracking_service.check_usage_warning()` | **KEEP** (live count) |
| Q41 | :56,040 | users (by ibm_id) | `_generate_token_warning()` → user lookup | **I**: Already have user |
| Q42 | :56,041 | llm_providers (default) | `_generate_token_warning()` → provider lookup | **I**: Use PipelineContext |
| Q43 | :56,043 | INSERT messages | Store assistant response | **KEEP** (required) |
| Q44 | :56,048 | messages (by pk) | `db.refresh()` after insert | **C**: Skip refresh |

---

## Fix Map

### KEEP (7 queries — irreducible minimum)

| Query | Purpose |
|:-----:|---------|
| Q9 | INSERT user message |
| Q12 | PipelineContext: llm_providers |
| Q13 | PipelineContext: llm_models |
| Q14 | PipelineContext: llm_parameters |
| Q16 | PipelineContext: prompt_templates |
| Q17 | PipelineContext: collections |
| Q26 | Files for document metadata (UI sources) |
| Q40 | SUM(token_count) for usage warning |
| Q43 | INSERT assistant message |

Actually 9 queries. But Q12-Q17 could be 1 JOIN query → **5 total**.

### Fix A: Pass session from router (eliminates Q1, Q8)

Router already fetches session for auth. Pass it to orchestrator.

**Files**: `conversation_router.py`, `message_processing_orchestrator.py`

### Fix B: Lazy-init CoT service (eliminates Q6)

`dependencies.py:406` calls `get_default_provider()` to check if CoT is
available. Move this check to first use, not construction time.

**File**: `core/dependencies.py`

### Fix C: Skip db.refresh() + append in-memory (eliminates Q10, Q11, Q44)

After INSERT, use the returned object. Don't re-fetch.
After storing user message, append to list. Don't re-query all messages.

**File**: `message_processing_orchestrator.py`, `conversation_repository.py`

### Fix D: Remove user lookup from PipelineContext (eliminates Q15)

PipelineContextRepository queries users table. Not needed — user_id is
already available from auth.

**File**: `repository/pipeline_context_repository.py`

### Fix E: Use PipelineContext for collection (eliminates Q18, Q19, Q23)

`search_service._search_with_pipeline()` re-fetches collection even though
PipelineContext already has `vector_db_name`. Same for retrieval stage.

**Files**: `search_service.py`, `pipeline_service.py`

### Fix F: Use PipelineContext for provider init (eliminates Q20, Q21, Q22)

`LLMProviderFactory.get_provider()` creates WatsonXLLM which calls
`initialize_client()` → `get_provider_by_name()`. Instead, build provider
from PipelineContext values.

**Files**: `generation/providers/factory.py`, `generation/providers/watsonx.py`

### Fix G: Pass provider to embedding function (eliminates Q24, Q25)

`get_embeddings_for_vector_store()` creates its own factory. Accept the
already-initialized provider or factory as param.

**File**: `vectordbs/utils/embeddings.py`

### Fix H: Generation stage uses PipelineContext (eliminates Q29-Q37)

`_validate_configuration()` re-queries pipeline, provider, params, user,
template. ALL of these are already in PipelineContext.

**File**: `services/pipeline/stages/generation_stage.py`, `services/pipeline_service.py`

### Fix I: Post-generation uses PipelineContext (eliminates Q38, Q39, Q41, Q42)

Token tracking and response serialization re-fetch user and provider.
Use values already available.

**File**: `services/message_processing_orchestrator.py`

### Frontend fixes (eliminates Q2, Q3, Q4, Q5, Q7, Q27, Q28)

React makes 7 redundant API calls (duplicate session fetches, polling
during search). These are frontend architecture issues.

**File**: Frontend React components (separate PR)

---

## Summary

| Fix | Queries Eliminated | Queries |
|-----|:-:|:-:|
| Keep (irreducible) | — | Q9, Q12-Q17, Q26, Q40, Q43 = 9 |
| Merge Q12-Q17 into 1 JOIN | -4 | → 5 |
| A: Pass session | Q1, Q8 | -2 |
| B: Lazy CoT init | Q6 | -1 |
| C: Skip refresh + append | Q10, Q11, Q44 | -3 |
| D: Remove user from PipelineCtx | Q15 | -1 |
| E: Use PipelineCtx for collection | Q18, Q19, Q23 | -3 |
| F: Use PipelineCtx for provider | Q20, Q21, Q22 | -3 |
| G: Pass provider to embedding | Q24, Q25 | -2 |
| H: Generation uses PipelineCtx | Q29-Q37 | -9 |
| I: Post-gen uses PipelineCtx | Q38, Q39, Q41, Q42 | -4 |
| Frontend: deduplicate | Q2-Q5, Q7, Q27, Q28 | -7 |
| **TOTAL** | **-39** | **5** |

**Target: 5 queries** (1 PipelineContext JOIN + 1 files + 1 SUM + 2 INSERTs)

---

## Files to Modify (Backend Only — Frontend Separate PR)

| File | Fixes |
|------|-------|
| `repository/pipeline_context_repository.py` | D: Remove user query, merge into JOIN |
| `core/dependencies.py` | B: Lazy CoT init |
| `router/conversation_router.py` | A: Pass session |
| `services/message_processing_orchestrator.py` | A, C, I: Accept session, skip refresh, use PipelineCtx |
| `repository/conversation_repository.py` | C: Return object from create, skip refresh |
| `services/search_service.py` | E: Use PipelineCtx.vector_db_name |
| `services/pipeline_service.py` | E, H: Use PipelineCtx, remove _validate_configuration DB calls |
| `services/pipeline/stages/generation_stage.py` | H: Read from PipelineCtx |
| `generation/providers/factory.py` | F: Build from PipelineCtx |
| `generation/providers/watsonx.py` | F: Accept config in init |
| `generation/providers/base.py` | F: Accept config in init |
| `vectordbs/utils/embeddings.py` | G: Accept provider/factory param |
| `schemas/pipeline_context.py` | D: Remove unnecessary fields |
