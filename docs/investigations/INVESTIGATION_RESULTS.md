# Investigation Results: RAG System Issues

**Date**: 2025-10-20
**Issues Investigated**: Milvus errors, Multiple DB calls, Irrelevant retrieval, Token limit overrides

**Related GitHub Issue**: #227 - Implement Comprehensive Runtime Configuration Service

---

## Issue 1: max_new_tokens = 100 (Expected: 800)

### ⚠️ THIS IS A SYMPTOM OF A LARGER ARCHITECTURAL PROBLEM (Issue #227)

### Root Cause
The system uses **per-user LLM parameters stored in PostgreSQL**, NOT .env settings!

### Location of Bug
**File**: `rag_solution/services/llm_parameters_service.py:138`

```python
def get_or_create_default_parameters(self, user_id: UUID4) -> LLMParametersOutput:
    # ...
    default_params = LLMParametersInput(
        user_id=user_id,
        name="Default Configuration",
        description="Default LLM parameters configuration",
        max_new_tokens=100,  # ❌ HARDCODED! Should use settings.max_new_tokens
        temperature=0.7,
        top_k=50,
        top_p=1.0,
        repetition_penalty=1.1,
        is_default=True,
    )
```

### How It Works
1. User makes first request → No DB params exist
2. System calls `get_or_create_default_parameters()`
3. Creates DB record with `max_new_tokens=100` (hardcoded)
4. All future requests use this DB value, **ignoring .env**

### The Fix
```python
def get_or_create_default_parameters(self, user_id: UUID4) -> LLMParametersOutput:
    existing_default = self.repository.get_default_parameters(user_id)
    if existing_default:
        return existing_default

    # ✅ Use settings from .env
    default_params = LLMParametersInput(
        user_id=user_id,
        name="Default Configuration",
        description="Default LLM parameters configuration from .env",
        max_new_tokens=self.settings.max_new_tokens,  # ✅ From .env (800)
        temperature=self.settings.temperature,         # ✅ From .env (0.7)
        top_k=self.settings.top_k,                     # ✅ From .env (5)
        top_p=self.settings.top_p,                     # ✅ From .env (0.95)
        repetition_penalty=self.settings.repetition_penalty,  # ✅ From .env (1.1)
        is_default=True,
    )

    return self.create_parameters(default_params)
```

### Impact
- **Current**: All users get 100 tokens max (truncated responses)
- **After Fix**: Users get 800 tokens (full responses from .env)

---

## Issue 2: Milvus "Channel closed" Error

### Error
```
pymilvus.decorators - ERROR - Unexpected error: [query], Cannot invoke RPC: Channel closed!
services.collection - WARNING - Error getting batch chunk counts
```

### Root Cause
**Database session closes BEFORE Milvus operations complete**

### Location
The error occurs in `collection_service.py` after successful queries:
1. DB session closes: `Database session closed.`
2. Milvus tries to query: `Cannot invoke RPC: Channel closed!`

### Why This Happens
```python
# Typical pattern causing issue:
async with get_db_session() as db:
    # Query documents
    docs = collection_service.get_documents(db)

# DB session closes here ←

# Milvus operations happen here (too late!)
chunks = milvus.get_batch_chunk_counts(collection_id, doc_ids)  # ❌ FAILS
```

### The Fix
**Option 1**: Keep session alive longer
```python
async with get_db_session() as db:
    docs = collection_service.get_documents(db)
    # Move Milvus operations inside context
    chunks = milvus.get_batch_chunk_counts(collection_id, doc_ids)  # ✅ Works
```

**Option 2**: Separate Milvus operations (recommended)
```python
# Get document IDs first
async with get_db_session() as db:
    doc_ids = [doc.id for doc in collection_service.get_documents(db)]

# Query Milvus separately (no DB dependency)
chunks = milvus.get_batch_chunk_counts(collection_id, doc_ids)  # ✅ Works
```

### Impact
- **Current**: Warning messages, potential data inconsistency
- **After Fix**: Clean operation, no warnings

---

## Issue 3: Multiple DB Calls

### Observed Behavior
```
2025-10-20 21:15:02,606 - Batch query for 1 documents returned 953 total chunks
2025-10-20 21:15:02,610 - Batch query for 1 documents returned 953 total chunks  # ← DUPLICATE
```

### Root Cause
**Multiple services calling the same query during search**

### Where It Happens
Based on logs, likely in:
1. `SearchService` - Gets documents for retrieval
2. `QueryRewriter` - Might query for context
3. `ChainOfThoughtService` - Queries for sub-questions
4. `SourceAttributionService` - Queries for source tracking

### Investigation Needed
Need to trace call stack:
```python
import traceback

def get_batch_chunks(self, ...):
    logger.info("=" * 80)
    logger.info("CALL STACK:")
    traceback.print_stack()
    logger.info("=" * 80)
    # ... rest of method
```

### Potential Fix
**Caching layer**:
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_batch_chunks(collection_id: str, document_ids: tuple):
    # Query only once, cache result
    return milvus.query(...)
```

---

## Issue 4: Irrelevant Chunk Retrieved

### Query
```
"What are IBM key financial metrics?"
```

### Retrieved Chunk
```
Chunk 943 (distance: 0.785):
"IBM common stock is listed on the New York Stock Exchange under the symbol 'IBM'."
```

### Why This Happens
1. **Vector Embedding Similarity**:
   - Query mentions: "IBM", "financial", "metrics"
   - Chunk contains: "IBM", "stock" (financial term), "listed" (metric)
   - Semantic embedding finds similarity!

2. **Query Expansion Made It Worse**:
   ```
   Original: "What are IBM key financial metrics?"
   Expanded: "What are IBM key financial metrics? AND (relevant OR important OR key)"
   ```
   - Added vague terms that match more broadly

3. **No Re-ranking**:
   - System retrieves top-5 by vector distance only
   - No second-pass filtering or re-ranking

### Solutions

**Option 1: Add Re-Ranker** (Best)
```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')

# After vector retrieval
initial_results = vector_db.search(query, top_k=20)  # Get more candidates

# Re-rank by actual relevance
scores = reranker.predict([(query, chunk.text) for chunk in initial_results])
final_results = sorted(zip(initial_results, scores), key=lambda x: x[1], reverse=True)[:5]
```

**Option 2: Metadata Filtering**
```python
# Filter by document section
results = vector_db.search(
    query,
    filter={
        "section": {"$in": ["Financial Highlights", "Revenue", "Income Statement"]}
    }
)
```

**Option 3: Hybrid Search** (Vector + Keyword)
```python
# Combine vector similarity with keyword matching
vector_results = vector_search(query, top_k=10)
keyword_results = keyword_search(query, top_k=10)

# Merge with weighted scores
final_results = merge_results(vector_results, keyword_results, weights=[0.7, 0.3])
```

**Option 4: Better Query Decomposition**
```python
# Instead of generic expansion, decompose into specific sub-queries
query = "What are IBM key financial metrics?"
sub_queries = [
    "IBM revenue 2022",
    "IBM operating income 2022",
    "IBM earnings per share 2022",
    "IBM cash flow 2022"
]
```

---

## Issue 5: Variable Length Responses

### Current Behavior
**All responses are same length** (determined by max_new_tokens)

### Problem
- Simple questions get bloated responses
- Complex questions get truncated responses

### How Other LLMs Do It
Modern LLMs use **dynamic stopping**:
1. **Stop Tokens**: `</answer>`, `\n\n`, `###`
2. **Confidence Thresholds**: Stop when confidence drops
3. **Min/Max Bounds**: Range instead of fixed length

### Solution for RAG Modulo

**Option 1: Use min/max tokens** (already in .env!)
```python
# .env
MAX_NEW_TOKENS=800  # Upper bound
MIN_NEW_TOKENS=200  # Lower bound

# WatsonX provider
model_params = {
    'max_new_tokens': 800,
    'min_new_tokens': 200,  # ✅ Already supported!
    'stop_sequences': ['</answer>', '\n\nUser:', '---'],
}
```

**Option 2: Dynamic based on question complexity**
```python
def estimate_required_tokens(question: str, context: str) -> int:
    """Estimate tokens needed based on question complexity."""
    base_tokens = 200

    # Add tokens for complexity indicators
    if any(word in question.lower() for word in ['explain', 'describe', 'how']):
        base_tokens += 300  # Detailed explanation needed

    if any(word in question.lower() for word in ['list', 'what are']):
        base_tokens += 200  # Enumeration needed

    if '?' in question:
        base_tokens += question.count('?') * 100  # Multiple questions

    # Add tokens based on context length
    context_tokens = len(context.split()) * 1.3  # Rough estimation
    if context_tokens > 500:
        base_tokens += 200  # More context = more comprehensive answer

    return min(max(base_tokens, 200), 800)  # Clamp to min/max

# In generation
required_tokens = estimate_required_tokens(question, context)
model_params['max_new_tokens'] = required_tokens
```

**Option 3: Adaptive streaming**
```python
def generate_with_quality_check(prompt: str) -> str:
    """Generate response and check if it's complete."""
    response = llm.generate(prompt, max_tokens=400)

    # Check if response is complete
    if response.endswith(('.', '!', '?')) and len(response) > 100:
        return response  # Good stopping point

    # Continue generating if incomplete
    if len(response) >= 350:  # Near token limit
        extended = llm.generate(
            prompt + response,
            max_tokens=400  # Generate more
        )
        return response + extended

    return response
```

---

## Recommended Fixes Priority

| Priority | Issue | Impact | Effort |
|----------|-------|--------|--------|
| 🔴 HIGH | max_new_tokens=100 | Users get truncated answers | 5 min |
| 🟡 MEDIUM | Irrelevant chunks | Poor search quality | 2-4 hours |
| 🟡 MEDIUM | Variable length responses | Better UX | 1-2 hours |
| 🟢 LOW | Multiple DB calls | Performance (minor) | 1 hour |
| 🟢 LOW | Milvus channel closed | Warnings only | 30 min |

---

## Implementation Plan

### Phase 1: Critical Fixes (30 min)
1. Fix max_new_tokens in llm_parameters_service.py
2. Add Milvus operation retry logic

### Phase 2: Search Quality (4 hours)
1. Implement re-ranker for top-k results
2. Add metadata filtering options
3. Improve query decomposition

### Phase 3: UX Improvements (2 hours)
1. Implement dynamic token estimation
2. Add stop sequences
3. Test with various question types

### Phase 4: Performance (2 hours)
1. Add query result caching
2. Reduce duplicate DB calls
3. Profile and optimize hot paths

---

## Testing Plan

### Test max_new_tokens Fix
```bash
# 1. Delete existing user parameters
psql -d rag_modulo -c "DELETE FROM llm_parameters WHERE user_id = '<user-uuid>';"

# 2. Make search request
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain IBM hybrid cloud strategy", "collection_id": "..."}'

# 3. Check response length (should be ~800 tokens, not 100)
```

### Test Re-ranker
```bash
# Query that currently returns irrelevant results
curl -X POST http://localhost:8000/api/search \
  -d '{"question": "What are IBM key financial metrics?"}'

# Before: Chunk 943 (stock listing)
# After: Chunks with actual revenue, income, EPS data
```

---

## Notes

- The .env file is meant for **default settings**
- User-specific parameters override .env
- This design allows per-user customization but creates confusion when .env is ignored
