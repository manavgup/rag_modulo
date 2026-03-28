# Issue #773: RAG Quality Investigation

## Problem Statement

Query: "what were the ibm results in 2020?"

- **Expected**: Financial figures (Revenue $73.6B, Net Income $5.59B, EPS $6.13)
- **Got (v1)**: Hallucinated data (Net Income $15.8B, EPS $7.52) — completely fabricated
- **Got (v2)**: Wall of narrative text about COVID/digital transformation — no financial figures
- **Got (v3)**: Same narrative, no financials, 23s response time

## Investigation Timeline

### Phase 1: Data Verification (Milvus Inspection)

**Connected directly to Milvus** and examined all 761 chunks in the IBM 2020 Annual Report collection.

**Key finding**: The financial data IS in Milvus.

| Chunk | Page | Content | Vector Search Rank |
|-------|------|---------|--------------------|
| 1 | 2 | Revenue $73.6B, cloud revenue $25.1B | #21 |
| 46 | 17 | **Net Income=$5,590M, EPS=$6.13, Revenue=$73,620M** | **#72** |
| 47 | 17 | Total debt, equity, shares outstanding | not in top 100 |
| 64 | 20 | Net Income=$5,590M (YoY -40.7%), EPS=$6.13 | not in top 100 |

**Root cause**: Chunk 46 (the financial summary table) ranks **72nd** in
vector search because flat table text `"Revenue, 2020 = $ 73,620"` has
low semantic similarity to `"what were the ibm results in 2020?"`.

### Phase 2: Vector Search Quality Testing

Tested 4 query formulations against Milvus using the IBM Slate embedding model:

| Query | Top result | Chunk 46 rank |
|-------|-----------|---------------|
| "what were the ibm results in 2020?" | Chunk 438 (empty revenue table) score=0.81 | **#72** |
| "IBM net income earnings per share 2020" | Chunk 329 (equity table) score=0.85 | not in top 100 |
| "IBM total revenue 2020" | Chunk 438 (empty revenue) score=0.90 | not in top 100 |
| "consolidated statements of earnings" | Chunk 294 (audit report) score=0.80 | not in top 100 |

**Conclusion**: Vector search systematically misses financial summary chunks for ANY query formulation.

### Phase 3: Retrieval Pipeline Analysis

**Current flow** (after all fixes applied):

```
User Query: "what were the ibm results in 2020?"
    │
    ▼
┌─────────────────────────────────────────────────┐
│ Stage 1: Pipeline Resolution (20ms)              │
│ - Looks up user's default pipeline from DB       │
│ - Sets context.pipeline_id                       │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│ Stage 2: Query Enhancement (0ms)                 │
│ - SimpleQueryRewriter: returns query unchanged   │
│ - HDE disabled by default                        │
│ - Output: same query                             │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│ Stage 3: Retrieval (5s)                          │
│ ┌─────────────────┐  ┌─────────────────────┐    │
│ │ Vector Search    │  │ Keyword Search      │    │
│ │ (Milvus ANN)    │  │ (TF-IDF)            │    │
│ │                  │  │                     │    │
│ │ embed query →    │  │ load 761 chunks →   │    │
│ │ cosine search →  │  │ build TF-IDF →      │    │
│ │ 50 results       │  │ cosine similarity   │    │
│ │                  │  │                     │    │
│ │ ✅ Working       │  │ ❌ CRASHES           │    │
│ │ 50 results       │  │ Source.PDF enum bug  │    │
│ │                  │  │ 0 results           │    │
│ └────────┬────────┘  └─────────┬───────────┘    │
│          │                     │                 │
│          └──────┬──────────────┘                 │
│                 ▼                                │
│      RRF Fusion (50 + 0 = 50 candidates)         │
│      → effectively pure vector search            │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│ Stage 4: Reranking (0.7s)                        │
│ - Cross-encoder: ms-marco-MiniLM-L-6-v2         │
│ - Input: 50 candidates                           │
│ - Output: top 5 (scores normalized 0-1)          │
│ - Top 5 are ALL narrative chunks:                │
│   #1 Page 92 (segment realignment) score=1.00    │
│   #2 Page 19 (financial section intro) score=0.97│
│   #3 Page 21 (COVID narrative) score=0.92        │
│   #4 Page 19 (mgmt discussion) score=0.90        │
│   #5 Page 15 (key initiatives) score=0.89        │
│ - ❌ NO financial data chunks                     │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│ Stage 5: Reasoning (0ms)                         │
│ - CoT not triggered for this query               │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│ Stage 6: Generation (5s)                         │
│ - Formats 5 chunks as context (~6100 chars)      │
│ - System prompt + faithfulness constraint +      │
│   markdown formatting + context + question       │
│ - Sends to WatsonX (granite-4-h-small)           │
│ - Response: narrative about COVID/transformation  │
│ - ❌ No financial figures (not in context)        │
└──────────────────────┬──────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│ Response to Frontend                             │
│ - Answer: narrative text (no financials)         │
│ - Sources: 5 chunks from Milvus                  │
│   shown truncated to ~200 chars in SourceCard    │
│ - Scores: cross-encoder scores as percentages    │
└─────────────────────────────────────────────────┘
```

### Phase 4: Timing Analysis (23s total)

| Phase | Duration | Details |
|-------|----------|---------|
| Pipeline Resolution | 20ms | DB lookup for default pipeline config |
| Query Enhancement | 0ms | SimpleRewriter no-op |
| Retrieval — embedding | ~4.5s | WatsonX API call to embed query |
| Retrieval — Milvus ANN | ~0.5s | Vector similarity search |
| Retrieval — TF-IDF | 30ms | **Crashed** (Source.PDF enum bug) |
| Reranking — model load | 1.4s | First-query cold start loading cross-encoder |
| Reranking — scoring | 0.7s | Score 50 candidates |
| Reasoning | 0ms | CoT not triggered |
| Generation — WatsonX API | ~5s | LLM inference (800 max tokens) |
| **DB overhead** | **~11s** | Repeated session/user queries |
| **Total** | **~23s** | |

### Phase 5: Source Display Analysis

**Q: Where do sources come from?**

- Source **texts** come from **Milvus chunks** (stored during ingestion)
- Source **document names** come from **Postgres files table**
- Frontend `SourceCard.tsx` truncates display to ~200 chars
- Full text available in modal overlay

**Q: Repeated DB queries**

- The conversation session query (massive JOIN: sessions + users + collections + messages + summaries) runs multiple
times per request
- Router fetches session for auth validation
- Orchestrator fetches it again to build conversation context
- SQLAlchemy eager-loading causes full object graph load each time
- Not a regression from this PR — pre-existing design issue

## Phase 6: Prompt Log Comparison (Two Queries)

Compared full LLM prompts from `/var/folders/.../watsonx_prompts/`:

### Query A: "what were the ibm results in 2020?" — BAD

**Context sent to LLM** (5 chunks from cross-encoder top 5):
| Rank | Page | Content | Problem |
|------|------|---------|---------|
| #1 | 92 | Segment realignment, recast revenue $0.3B | Boilerplate, NOT IBM's actual revenue |
| #2 | 19 | Financial section table of contents | Describes structure, no data |
| #3 | 21 | COVID-19 pandemic narrative | General impact, no figures |
| #4 | 19 | Management Discussion overview | Describes what sections exist |
| #5 | 15 | Key initiatives (racial equity, quantum) | CSR, not financial |

**Zero financial figures** in context. The LLM cited "$0.3B recast revenue" — which is a segment adjustment, not IBM's
actual revenue ($73.6B). The faithfulness constraint prevented hallucination but the answer is irrelevant.

### Query B: "Decisive moves for future growth" — GOOD

**Context sent to LLM** (5 chunks):

- Specific content about NewCo separation (4,600 clients, Fortune 100)
- 7 acquisitions for hybrid cloud/AI
- $1B ecosystem investment
- Salesforce/ServiceNow partnerships with specific details

The query text **directly matches section headings** in the annual report, so vector search finds the right chunks.
The LLM produces an accurate, detailed answer.

### Key Insight

**The problem is 100% retrieval, not generation.** When the right chunks reach the LLM, it performs well. The LLM is
faithful to context — it just gets bad context for financial queries because:

1. Financial summary tables (flat key-value pairs) have low vector similarity to natural language queries
2. Narrative chunks (CEO letter, COVID overview) have high vector similarity to broad queries like "results"
3. The cross-encoder reranker also prefers narrative over tabular data

### LLM Response Quality Issue

Both responses start with broken text:

- Query A: `"annual report\n\n## IBM Results"` — continues document structure
- Query B: `"was one of the most challenging periods"` — continues context text

This is a prompt boundary issue: the LLM treats the context as text to continue rather than reference material. The
`---` separator and "Do NOT continue" instruction help but don't fully prevent it with granite-4-h-small.

## Debugging Checklist

### Phase 1: Establish Baseline (vector-only)

- [ ] Set `RETRIEVAL_TYPE=vector` in `.env`
- [ ] Keep `RETRIEVAL_CANDIDATE_COUNT=50` and `RERANKER_TOP_K=5`
- [ ] Restart backend, test "what were the ibm results in 2020?"
- [ ] Log which 5 chunks the cross-encoder selects
- [ ] Does chunk 46 (page 17, financial summary) appear?

### Phase 2: Test keyword search in isolation

- [ ] Set `RETRIEVAL_TYPE=keyword` in `.env`
- [ ] Test same query — does chunk 46 appear in top 5?
- [ ] If yes → hybrid search will fix the problem
- [ ] If no → TF-IDF doesn't match either, need different approach

### Phase 3: Enable hybrid with enum fix

- [ ] Set `RETRIEVAL_TYPE=hybrid` in `.env`
- [ ] Source enum fix already applied (`Source.PDF` → `pdf`)
- [ ] Test same query — check logs for `keyword > 0`
- [ ] Verify chunk 46 appears in final top 5

### Phase 4: Evaluate cross-encoder bottleneck

- [ ] If chunk 46 IS in 50 candidates but NOT in top 5 after reranking
- [ ] Cross-encoder may rank narrative above tables
- [ ] Try `RERANKER_TOP_K=10` to give more room

## Bugs Found

### Bug 1: Source Enum Mismatch (BLOCKING keyword search)

- **File**: `backend/rag_solution/retrieval/retriever.py` line 119
- **Cause**: Milvus stores `"Source.PDF"` (from `str(Source.PDF)`). KeywordRetriever reads raw value and passes to
`DocumentChunkMetadata(source="Source.PDF")` which fails enum validation
- **Impact**: Keyword retriever returns 0 results → hybrid search degrades to pure vector
- **Fix**: Parse `"Source.PDF"` → `"pdf"` before creating metadata

### Bug 2: Existing user template not updated (cosmetic)

- **File**: User's RAG template in DB still has old system prompt
- **Cause**: `user_provider_service.py` change only affects NEW default templates
- **Impact**: Faithfulness constraint from `prompt_template_service.py` still applies (it's in markdown instructions,
not system prompt), so this is cosmetic

### Bug 3 (fixed): Reranker returning all 50 results

- Was returning all 50 candidates instead of top 5
- Fixed: `_get_reranking_top_k()` now reads `settings.reranker_top_k`

### Bug 4 (fixed): Pipeline schema blocking hybrid retriever

- `PipelineConfigInput` validator required `config_metadata` for hybrid
- Fixed: Removed overly strict validator

### Bug 5 (fixed): RETRIEVAL_TYPE setting ignored

- `PipelineService` passed `{}` to `RetrieverFactory`
- Fixed: Now passes `_build_retriever_config()` from settings

## Checklist

### Completed

- [x] Add faithfulness constraint to prompts (prompt_template_service.py, user_provider_service.py)
- [x] Add `retrieval_candidate_count=50` config setting
- [x] Rewrite HybridRetriever with RRF fusion
- [x] Fix PipelineService to wire RETRIEVAL_TYPE from settings
- [x] Fix reranking stage to use `settings.reranker_top_k`
- [x] Fix pipeline schema validator for hybrid retriever
- [x] Update .env to RETRIEVAL_TYPE=hybrid
- [x] Add 11 unit tests for RRF hybrid retriever (including source enum)
- [x] Add faithfulness constraint test
- [x] Update retrieval stage tests
- [x] Fix `Source.PDF` → `pdf` parsing in KeywordRetriever
- [x] Fix entity extraction appending redundant entities to query
- [x] Update user RAG template in DB (Question-first with labels)
- [x] Fix empty LLM response crash in orchestrator
- [x] Fix reranker returning all 50 instead of top 5

### Pending — Keyword Search (currently RETRIEVAL_TYPE=vector)

- [ ] Re-enable `RETRIEVAL_TYPE=hybrid` after verifying keyword retriever works
- [ ] Fix Milvus to store `source.value` ("pdf") instead of `str(source)` ("Source.PDF") at write time

## Phase 7: DB Call Audit (50 queries per search!)

### Measured from logs: 50 SELECT/INSERT queries for one search request

**Pre-Pipeline (17 queries — orchestrator layer):**
| # | Table | Purpose | Redundant? |
|---|-------|---------|------------|
| 1 | users | Auth/session validation in router | |
| 2 | prompt_templates | User defaults check | |
| 3 | llm_providers | Entity extraction provider init | Wasteful (regex fallback) |
| 4 | conversation_sessions | Massive JOIN: users+collections+messages+summaries | HEAVY |
| 5 | files | Eager-loaded with collection | Unnecessary |
| 6 | user_collection | Eager-loaded | Unnecessary |
| 7 | users | Eager-loaded with session | Redundant (#1) |
| 8 | conversation_sessions | Orchestrator re-fetches same session | **REDUNDANT (#4)** |
| 9 | files | Eager-loaded again | **REDUNDANT (#5)** |
| 10 | user_collection | Eager-loaded again | **REDUNDANT (#6)** |
| 11 | users | Eager-loaded again | **REDUNDANT (#1,#7)** |
| 12 | conversation_messages | INSERT user message | Required |
| 13 | conversation_messages | SELECT ALL messages right after insert | **REDUNDANT** |
| 14 | conversation_messages | Token count | Could combine with #13 |
| 15 | llm_providers | Entity extraction provider | **REDUNDANT (#3)** |
| 16 | llm_providers | Entity extraction provider | **REDUNDANT (#3)** |
| 17 | llm_models | Entity extraction model | Wasteful |

**Pipeline Stages (33 queries):**
| # | Stage | Table | Redundant? |
|---|-------|-------|------------|
| 18 | Resolution | pipeline_configs | Required |
| 19 | Resolution | llm_providers | |
| 20 | Retrieval | collections | Only need vector_db_name |
| 21 | Retrieval | files | Eager-loaded, not needed |
| 22 | Retrieval | user_collection | Eager-loaded, not needed |
| 23 | Retrieval | users | Eager-loaded, not needed |
| 24 | Retrieval | llm_providers | **REDUNDANT (#19)** |
| 25 | Retrieval | llm_models | For embedding |
| 26 | Retrieval | files | Document metadata for UI |
| 27 | Generation | pipeline_configs | **REDUNDANT (#18)** |
| 28 | Generation | llm_providers | **REDUNDANT (#19,#24)** |
| 29 | Generation | llm_parameters | Required |
| 30 | Generation | users | **REDUNDANT (#1,#7,#11,#23)** |
| 31 | Generation | llm_providers | **REDUNDANT** |
| 32 | Generation | llm_providers | **REDUNDANT** |
| 33 | Generation | llm_models | **REDUNDANT (#25)** |
| 34 | Generation | prompt_templates | Required |
| 35 | Generation | prompt_templates | **REDUNDANT (#34)** |

### Summary: 50 queries → ~8 needed

| Table | Current | Needed | Wasted |
|-------|:-------:|:------:|:------:|
| llm_providers | 9 | 1 | 8 |
| users | 6 | 1 | 5 |
| llm_models | 4 | 1 | 3 |
| collections | 3 | 1 | 2 |
| conversation_sessions | 2 | 1 | 1 |
| pipeline_configs | 2 | 1 | 1 |
| prompt_templates | 2 | 1 | 1 |
| files | 3 | 1 | 2 |
| conversation_messages (SELECT) | 2 | 0 | 2 |
| conversation_messages (INSERT) | 1 | 1 | 0 |
| user_collection | 2 | 0 | 2 |
| llm_parameters | 1 | 1 | 0 |
| **Total** | **50** | **~12** | **~38** |

### Code Smells

1. **Orchestrator re-fetches session** — `message_processing_orchestrator.py:153` queries `get_session_by_id()` even
though `conversation_router.py:415` already validated it
2. **Insert then re-fetch** — `message_processing_orchestrator.py:178-182` stores user message then immediately
queries ALL messages
3. **Services re-init from DB per call** — `LLMProviderFactory`, `PipelineService`, `generation_stage` all
independently query providers/models
4. **Entity extraction triple fallback** — LLM → spaCy (not installed) → regex. Always ends at regex. Adds 3 DB
queries for provider init
5. **Eager-loading everywhere** — Collection model loads files + user_collection even when only vector_db_name is needed
6. **No request-scoped caching** — Same data (provider, models, templates) fetched repeatedly across pipeline stages

### Optimization Checklist

#### High Impact (saves ~25 queries)

- [ ] **Cache LLM provider/models per request**: Store on SearchContext after first resolution, reuse in retrieval +
generation stages
  - Files: `pipeline_service.py`, `search_context.py`, `generation_stage.py`, `retrieval_stage.py`
  - Saves: ~15 queries (provider queried 9x, models 4x)

- [ ] **Pass session from router to orchestrator**: Router already fetched and validated it
  - Files: `conversation_router.py`, `message_processing_orchestrator.py`
  - Saves: ~4 queries (session + eager-loaded relations)

- [ ] **Skip entity extraction for first message**: No conversation context → extracted entities are already in the
question
  - Files: `conversation_context_service.py`, `message_processing_orchestrator.py`
  - Saves: ~3 queries (provider/model init) + avoids query mangling

#### Medium Impact (saves ~10 queries)

- [ ] **Append message in-memory instead of re-fetching**: After INSERT, add to existing list
  - File: `message_processing_orchestrator.py`
  - Saves: 1-2 queries

- [ ] **Lazy-load collection relationships**: Query only `vector_db_name` when that's all we need
  - Files: `pipeline_service.py`, collection model/queries
  - Saves: ~4 queries (files, user_collection loaded unnecessarily)

- [ ] **Cache pipeline_config across stages**: Resolve once in Stage 1, reuse in Stage 6
  - Files: `search_context.py`, `pipeline_resolution_stage.py`, `generation_stage.py`
  - Saves: 1 query

#### Low Impact / Future

- [ ] Cache cross-encoder model (1.4s cold start on first query per restart)
- [ ] Fix Milvus to store `source.value` ("pdf") not `str(source)` ("Source.PDF")
- [ ] Update existing user templates with faithfulness system prompt
- [ ] Reduce SQLAlchemy SQL logging verbosity (each query logged twice: once by engine, once by logger)
- [ ] Consider query enhancement for financial queries ("results" → "revenue, net income, earnings")

## Key Files

| File | Role |
|------|------|
| `backend/rag_solution/retrieval/retriever.py` | KeywordRetriever, HybridRetriever, VectorRetriever |
| `backend/rag_solution/services/pipeline_service.py` | Pipeline orchestration, retriever creation |
| `backend/rag_solution/services/pipeline/stages/retrieval_stage.py` | Retrieval stage execution |
| `backend/rag_solution/services/pipeline/stages/reranking_stage.py` | Cross-encoder reranking |
| `backend/rag_solution/services/pipeline/stages/generation_stage.py` | LLM context formatting and generation |
| `backend/rag_solution/services/prompt_template_service.py` | Prompt assembly with faithfulness constraint |
| `backend/vectordbs/milvus_store.py` | Milvus search, source enum storage (line 256, 657) |
| `backend/core/config.py` | Settings: retrieval_candidate_count, retrieval_type |
| `frontend/src/components/search/SourceCard.tsx` | Source display (200 char truncation) |

## Debug File Locations

| File | Contents |
|------|----------|
| `/var/folders/.../rag_debug/query_enhancement_*.txt` | Query before/after rewriting |
| `/var/folders/.../rag_debug/retrieval_params_*.txt` | Retrieval configuration |
| `/var/folders/.../rag_debug/chunks_retrieval_*.txt` | All 50 retrieved chunks with scores |
| `/var/folders/.../rag_debug/chunks_reranking_*.txt` | Top 5 reranked chunks with scores |
| `/var/folders/.../rag_debug/context_to_llm_*.txt` | Exact context sent to LLM |
| `/var/folders/.../watsonx_prompts/prompt_*.txt` | Full formatted LLM prompt + response |
