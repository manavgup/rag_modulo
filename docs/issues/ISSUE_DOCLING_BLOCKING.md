# Docling Document Processing Blocks System During 3+ Minute PDF Conversion

## Problem

When Docling processes large PDFs (143+ pages), the system grinds to a halt for 3+ minutes, blocking all other operations. This creates a poor user experience and prevents effective testing of the RAG pipeline components.

## Current Behavior

1. User uploads PDF to collection
2. `background_tasks.add_task()` is called to process document
3. Docling takes 3+ minutes to convert PDF to text (CPU-intensive)
4. During this time, the **entire system appears unresponsive**
5. No other API requests can be processed effectively

## Root Cause Analysis

While the code correctly uses FastAPI's `BackgroundTasks`:

```python
# collection_service.py:765
background_tasks.add_task(
    self.process_documents,
    file_paths,
    collection_id,
    collection_vector_db_name,
    document_ids,
    user_id,
)
```

The issue is that:

1. **FastAPI's BackgroundTasks runs in the same event loop** with `run_in_threadpool`
2. **Docling is CPU-intensive**, not I/O-bound
3. **Python's GIL (Global Interpreter Lock)** prevents true parallelism for CPU work
4. The thread pool becomes saturated with Docling's heavy processing

## Expected Behavior

Document processing should:

1. Not block other API requests
2. Run in a separate process (not just thread)
3. Allow users to continue using the system while documents process
4. Provide progress updates via webhooks/polling

## Proposed Solutions

### Option 1: Process Pool (Recommended)

Use `concurrent.futures.ProcessPoolExecutor` for Docling work:

```python
from concurrent.futures import ProcessPoolExecutor

process_pool = ProcessPoolExecutor(max_workers=2)

# In collection_service.py
background_tasks.add_task(
    run_in_process_pool,
    process_pool,
    self._docling_convert_pdf,
    file_path
)
```

**Pros**: True parallelism, doesn't block GIL
**Cons**: Additional memory overhead, need to handle process communication

### Option 2: Celery/RQ Task Queue

Move Docling processing to dedicated worker processes:

```python
@celery_app.task
def process_document_task(file_path, collection_id):
    # Docling processing here
    pass
```

**Pros**: Industry-standard, handles retries, monitoring
**Cons**: Additional infrastructure (Redis/RabbitMQ)

### Option 3: Async Docling with Process Pool

Wrap Docling in async process pool:

```python
async def async_docling_process(file_path):
    loop = asyncio.get_event_loop()
    with ProcessPoolExecutor() as pool:
        return await loop.run_in_executor(
            pool,
            docling_convert_pdf,
            file_path
        )
```

**Pros**: Non-blocking, integrates well with FastAPI
**Cons**: Still requires process pool setup

## Impact

This affects:

1. **User Experience**: System appears frozen during uploads
2. **Testing**: Embedding model comparison tests take 40+ minutes (8 models × 5 min each)
3. **Scalability**: Can't process multiple documents concurrently
4. **API Responsiveness**: All endpoints slow down during processing

## Testing Implications

The current blocking behavior makes testing inefficient:

- **What we want to test**: Embedding quality, chunking strategy, retrieval ranking
- **What we're actually waiting for**: Docling PDF conversion (3+ min per document)
- **Result**: 8-model comparison takes 40+ minutes instead of 10 minutes

## Acceptance Criteria

- [ ] Docling processing runs in separate process pool
- [ ] API remains responsive during document processing
- [ ] Multiple documents can be processed concurrently
- [ ] Processing status can be queried via API
- [ ] Tests can skip Docling processing and use pre-converted text

## Priority

**MEDIUM** - Affects development velocity and user experience, but system is functional

## Labels

- `performance`
- `ux`
- `document-processing`
- `technical-debt`

## Related Issues

- #461 - CoT reasoning (blocked by slow testing)
- Issue #xxx - Embedding model comparison (takes 40+ min due to this issue)
