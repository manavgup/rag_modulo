# Embedding Dimension Mismatch Debug - October 24, 2025

## Problem

When trying to create a collection and upload documents, getting error:
```
MilvusException: (code=65535, message=the length(18048) of float data should divide the dim(768))
```

Analysis:
- 18048 floats / 768 dimensions = 23.5 vectors (not a whole number!)
- This means we're trying to insert 23.5 vectors when we should have exactly 23 or 24
- Root cause: At least one embedding has the wrong dimension

## Debug Logging Added

### 1. Ingestion Pipeline (`backend/rag_solution/data_ingestion/ingestion.py`)

Added comprehensive dimension checking at lines 105-138:
- Checks each embedding dimension as it comes from the provider
- Logs dimension distribution (e.g., "384: 2, 768: 21" would show 2 embeddings with 384 dims, 21 with 768)
- Reports inconsistent dimensions with error log
- Output format:
  ```
  DIMENSION DEBUG (INGESTION): Checking 23 embeddings from provider
  DIMENSION DEBUG (INGESTION): First embedding dimension: 768
  DIMENSION DEBUG (INGESTION): Dimension distribution: {768: 23}
  DIMENSION DEBUG (INGESTION): ✓ All embeddings have consistent dimension: 768
  ```

### 2. Milvus Store (`backend/vectordbs/milvus_store.py`)

Added validation before insertion at lines 195-232:
- Checks each embedding before Milvus insert
- Calculates total floats across all embeddings
- Validates total floats is divisible by expected dimension
- Reports problematic embeddings with chunk IDs
- Output format:
  ```
  DIMENSION DEBUG: Preparing to insert 23 chunks into collection 'test-collection'
  DIMENSION DEBUG: Expected embedding dimension: 768
  DIMENSION DEBUG: Total embeddings: 23
  DIMENSION DEBUG: Total floats: 17664
  DIMENSION DEBUG: Expected total floats: 17664
  DIMENSION DEBUG: Floats per expected dim: 23.00
  ```

If mismatch detected:
  ```
  DIMENSION DEBUG: ⚠️ MISMATCH DETECTED: 18048 floats is not divisible by 768!
  DIMENSION DEBUG: Problematic embedding at index 5: dim=1536, chunk_id=chunk_abc123
  ```

## How to Test

### Option 1: Via Web UI (Recommended)

1. **Restart backend** to load the new logging:
   ```bash
   # If using local dev:
   make local-dev-stop
   make local-dev-all

   # Or kill and restart uvicorn process:
   pkill -f "uvicorn main:app"
   cd backend && poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Open frontend** at http://localhost:3000

3. **Create a new collection**:
   - Go to Collections page
   - Click "Create Collection"
   - Name it "dimension_test"
   - Submit

4. **Upload a document**:
   - Select the new collection
   - Click "Upload Document"
   - Choose any PDF file
   - Submit

5. **Check backend logs**:
   ```bash
   # If using local dev:
   tail -f logs/backend.log | grep "DIMENSION DEBUG"

   # Or Docker:
   docker compose logs -f backend | grep "DIMENSION DEBUG"
   ```

### Option 2: Via CLI

```bash
# Create collection
./rag-cli collection create --name dimension_test --description "Test dimension debugging"

# Upload document (replace with your file path)
./rag-cli collection upload dimension_test /path/to/test.pdf

# Check logs
tail -f logs/backend.log | grep "DIMENSION DEBUG"
```

## Expected Outcomes

### If Embeddings are Correct (All 768-dim):

```
DIMENSION DEBUG (INGESTION): Dimension distribution: {768: 23}
DIMENSION DEBUG (INGESTION): ✓ All embeddings have consistent dimension: 768

DIMENSION DEBUG: Total embeddings: 23
DIMENSION DEBUG: Total floats: 17664
DIMENSION DEBUG: Expected total floats: 17664
```

Document upload succeeds.

### If Dimension Mismatch Exists:

```
DIMENSION DEBUG (INGESTION): Dimension distribution: {768: 22, 1536: 1}
DIMENSION DEBUG (INGESTION): ⚠️ INCONSISTENT DIMENSIONS DETECTED!
DIMENSION DEBUG (INGESTION): Embedding 22 has different dimension: 1536 (expected 768)

DIMENSION DEBUG: Total floats: 18432
DIMENSION DEBUG: Expected total floats: 17664
DIMENSION DEBUG: ⚠️ MISMATCH DETECTED: 18432 floats is not divisible by 768!
DIMENSION DEBUG: Problematic embedding at index 22: dim=1536, chunk_id=chunk_xyz
```

Document upload fails with MilvusException.

## Possible Root Causes

Based on the expected output, potential issues:

1. **Wrong Embedding Model**: The .env specifies one model, but a different model is being used
   - Check: `grep EMBEDDING_MODEL .env`
   - Should be: `EMBEDDING_MODEL=ibm/slate-30m-english-rtrvr-v2` (768-dim)

2. **Model Dimension Mismatch**: The model in .env doesn't match EMBEDDING_DIM
   - Check: `grep EMBEDDING_DIM .env`
   - Should match the actual model output dimension

3. **Batching Issue**: Some chunks get different embedding models
   - Look for: Mixed dimensions in INGESTION debug logs

4. **WatsonX API Issue**: The API is returning inconsistent dimensions
   - Look for: Consistent pattern (e.g., always chunk 22 has wrong dim)

5. **Chunking Issue**: Partial chunks are being created
   - Look for: Non-integer division (23.5 vectors)

## Next Steps After Test

1. **Share the debug logs** with the exact DIMENSION DEBUG output
2. **Identify the pattern**:
   - Are ALL embeddings wrong, or just some?
   - Is it always the same chunk/position?
   - What dimension are the wrong embeddings?
3. **Fix based on root cause**:
   - Update .env configuration
   - Fix chunking logic
   - Fix embedding generation
   - Fix provider model selection

## Files Modified

1. `backend/rag_solution/data_ingestion/ingestion.py`
   - Lines 105-138: Dimension validation in `_embed_documents_batch()`

2. `backend/vectordbs/milvus_store.py`
   - Lines 195-232: Dimension validation in `add_documents()`

3. `backend/test_dimension_mismatch.py` (new)
   - Standalone test script (not working due to poetry env issues)

## Rollback

If you need to remove the debug logging:
```bash
git diff backend/rag_solution/data_ingestion/ingestion.py
git diff backend/vectordbs/milvus_store.py

# To revert:
git checkout backend/rag_solution/data_ingestion/ingestion.py
git checkout backend/vectordbs/milvus_store.py
```

---

**Created**: October 24, 2025
**Status**: Debug logging added, awaiting test results
