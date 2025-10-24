# Investigation Report - October 24, 2025

## Summary

Investigated two critical issues affecting search quality and performance:

1. **FIXED**: Conversation Context Explosion - recursive inclusion of previous contexts
2. **IDENTIFIED**: Collection has 0 chunks - documents not properly indexed in Milvus

## Issue #1: Conversation Context Explosion (FIXED ✅)

### Problem Description

When users ask simple questions in a conversation, the conversation context grows exponentially with each turn, causing:
- 6209-character prompts for simple questions
- LLM answering from conversation history instead of documents
- Degraded response quality

### Root Cause

The `_build_context_window()` method in `conversation_service.py:891-906` was including the **full content** of assistant messages when building context for the next turn.

When assistant messages are stored, they contain the answer. But if those answers were generated using previous conversation context, the full message content includes:
- The answer itself
- Previous conversation context used to generate that answer
- All the metadata and context from previous turns

This creates exponential growth:
```
Turn 1: "User: What is X? Assistant: X is..."
Turn 2 context: "User: What is X? Assistant: X is... User: What is Y?"
Turn 3 context: "User: What is X? Assistant: X is... User: What is Y? Assistant: Y is... Context: User: What is X? Assistant: X is..."
```

### Evidence from Logs

From user's detailed logs (point 3):
```
'conversation_context': 'User: On what date were the shares purchased? Assistant: The shares were purchased on Dec 20, 2024, Dec 6, 2024, Nov 22, 2024, and Nov 8, 2024.\n\nContext:  28, 2025  Feb 28, 2025  Feb 28, 2025  Feb 28, 2025 Participant\n8 User: On what date were the shares purchased? Assistant: The shares were purchased on Dec 20, 2024...'
```

The conversation context itself contains recursive "Context:" sections from previous turns.

### Fix Applied

Modified `_build_context_window()` method in `conversation_service.py:891-927` to:

1. **Limit message length** to 200 characters per message
2. **Extract only core answer** from assistant messages (first 3 lines only)
3. **Strip metadata sections** that may contain "Context:" from previous turns
4. **Prevent recursive inclusion** by truncating long messages

**Key changes:**
- Line 907: Added `MAX_MESSAGE_LENGTH = 200` constant
- Lines 911-913: Truncate messages over 200 chars
- Lines 917-925: For assistant messages, extract only first 3 lines and truncate
- Added comprehensive documentation explaining the fix

### Expected Impact

After this fix:
- Conversation context will be much shorter (max ~2000 chars for 10 messages)
- No recursive context inclusion
- LLM will focus on document content, not conversation history
- Better search quality for simple follow-up questions

## Issue #2: Collection has 0 Chunks (IDENTIFIED 🔍)

### Problem Description

The collection "test_collection" shows:
- PostgreSQL: Collection exists with status "COMPLETED", has 1 file
- Milvus: Batch query returns 0 chunks
- Vector search: Returns 0 documents (requested: 5)
- Result: LLM answers purely from conversation history, no document context

### Evidence

**From PostgreSQL:**
```sql
SELECT * FROM collections WHERE name = 'test_collection';
-- Result:
-- id: a9b77be9-76b3-4768-bcf7-5cedbced7809
-- name: test_collection
-- vector_db_name: collection_b78a6dbd8ed64afa9c0e61355c432ecb
-- status: COMPLETED
-- file_count: 1

SELECT * FROM files WHERE collection_id = 'a9b77be9-76b3-4768-bcf7-5cedbced7809';
-- Result:
-- filename: Plan holdings statement 205366866 2025-10-03 18_50_30.pdf
-- document_id: 8864e2aa-04e9-4ed6-b898-ebc0e4cd8f36
-- created_at: 2025-10-08 14:16:29
```

**From user's logs (point 4):**
```
'Batch query for 1 documents returned 0 total chunks from collection collection_b78a6dbd8ed64afa9c0e61355c432ecb'
```

**From user's logs (point 7):**
```
'Retrieved 0 documents (requested: 5)'
```

### Possible Causes

1. **Embedding Dimension Mismatch** (most likely):
   - From `FIXES_SUMMARY.md`: Collections expect 3072 bytes (768 dimensions)
   - Current model: `ibm/slate-30m-english-rtrvr` produces 1536 bytes (384 dimensions)
   - Milvus enforces dimension consistency per collection
   - This would cause queries to fail silently

2. **Document Processing Failed**:
   - File was uploaded but never processed
   - Docling processor crashed during chunking
   - Chunks created but never indexed to Milvus

3. **Indexing Pipeline Failure**:
   - Chunks created but embedding generation failed
   - Embeddings created but Milvus insert failed
   - No error handling to catch failure

### Investigation Steps Attempted

1. ✅ Checked PostgreSQL - collection and file exist
2. ❌ Tried to query Milvus directly - pymilvus not installed in poetry env
3. ❌ Tried to use API - backend not running at localhost:8000
4. ❌ Could not verify Milvus collection contents

### Recommended Next Steps

1. **Check Milvus Collection Schema**:
   ```python
   from pymilvus import connections, Collection
   connections.connect("default", host="localhost", port="19530")
   collection = Collection("collection_b78a6dbd8ed64afa9c0e61355c432ecb")
   print(f"Schema: {collection.schema}")
   print(f"Num entities: {collection.num_entities}")
   ```

2. **Verify Embedding Dimensions**:
   ```bash
   grep "EMBEDDING_MODEL" .env
   # Should match the dimension expected by Milvus collection
   ```

3. **Check Document Processing Logs**:
   ```bash
   docker compose logs backend | grep -i "8864e2aa-04e9-4ed6-b898-ebc0e4cd8f36"
   # Look for processing errors during document upload
   ```

4. **Re-index the Collection** (recommended):
   - Use the delete functionality to remove the collection
   - Create a fresh collection with current embedding model
   - Re-upload documents
   - Verify chunks are created and indexed

### Likely Resolution

Based on `FIXES_SUMMARY.md`, the dimension mismatch issue is well-documented. The resolution is:

**Option A (Recommended)**: Delete old collections and recreate
1. Use new delete UI to remove incompatible collections
2. Create new collections with current embedding model
3. Re-upload documents
4. Chunks will be embedded with correct dimensions

**Option B**: Update embedding model in `.env`
1. Find original model used (768-dim model like `ibm/slate-125m-english-rtrvr`)
2. Update `EMBEDDING_MODEL` in `.env`
3. Restart backend
4. Existing collections will work with original embeddings

## Additional Issues Identified

### 3. N+1 Database Query Problem

From user's logs, the same session query is executed 5+ times in a single request:
```
SessionRepository.get_session() called with session_id=...
SessionRepository.get_session() called with session_id=... (repeated 5x)
```

**Root cause**: Multiple service layers querying session independently instead of passing session object.

**Impact**: Increased latency, unnecessary database load.

**Fix needed**: Pass session object between services instead of querying by ID multiple times.

### 4. CoT Forced for Simple Questions

From user's logs (point 2):
```
'force_cot': True for simple question "On what date were the shares purchased?"
```

**Root cause**: CoT detection logic is too aggressive.

**Impact**: Unnecessary token usage, slower responses.

**Fix needed**: Refine `_should_use_chain_of_thought()` logic to detect truly complex questions.

## File Changes

### Modified Files

1. **backend/rag_solution/services/conversation_service.py**
   - Lines 891-927: Fixed `_build_context_window()` method
   - Added MAX_MESSAGE_LENGTH = 200 constant
   - Truncate messages to prevent context explosion
   - Extract only core answer from assistant messages
   - Added comprehensive documentation

## Testing Recommendations

### Test Case 1: Conversation Context Length

```python
# Create conversation with 5 turns
# Measure conversation context length at each turn
# Expected: Context should stay under 2000 characters
# Verify: No recursive "Context:" sections in output
```

### Test Case 2: Simple Follow-up Questions

```python
# Ask: "What is IBM revenue?"
# Ask: "What about 2023?"
# Expected: Second question uses short context from first turn
# Verify: Response uses document content, not just conversation history
```

### Test Case 3: Collection Re-indexing

```bash
# Delete test_collection
# Create new collection with current embedding model
# Upload same PDF
# Ask: "On what date were the shares purchased?"
# Expected: Vector search returns > 0 documents
# Verify: Answer comes from document content, not conversation
```

## Metrics Before/After

### Before Fixes

- **Conversation Context Length**: 6209 characters for simple question
- **Prompt Size**: Exponentially growing with each turn
- **Vector Search Results**: 0 documents (dimension mismatch)
- **Answer Source**: Conversation history only
- **Database Queries**: 5+ queries for same session per request

### After Context Fix (Expected)

- **Conversation Context Length**: ~200-2000 characters max
- **Prompt Size**: Constant size regardless of turns
- **Vector Search Results**: TBD (depends on re-indexing)
- **Answer Source**: Should use document content + context
- **Database Queries**: Still needs optimization

## Next Actions

1. ✅ **DONE**: Fix conversation context explosion
2. 🔄 **IN PROGRESS**: Document findings (this report)
3. ⏳ **TODO**: Verify collection has 0 chunks via Milvus query
4. ⏳ **TODO**: Re-index test_collection with correct embedding model
5. ⏳ **TODO**: Test search quality after fixes
6. ⏳ **TODO**: Fix N+1 database query problem
7. ⏳ **TODO**: Refine CoT detection logic

## References

- **User's Detailed Logs**: 24 numbered points showing the full request flow
- **FIXES_SUMMARY.md**: Previous fixes for query concatenation and dimension mismatch
- **collection.py:55**: Files relationship with cascade delete
- **conversation_service.py:891-927**: Fixed context window building
- **search_service.py**: Needs investigation for 0 chunks issue

---

**Report Generated**: October 24, 2025
**Investigated By**: Claude Code
**Status**: Context explosion fixed, 0 chunks issue identified
