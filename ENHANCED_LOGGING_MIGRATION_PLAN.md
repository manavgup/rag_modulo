# Enhanced Logging Migration Plan

**Issue**: [#77](https://github.com/manavgup/rag_modulo/issues/77)
**Documentation**: [docs/development/logging.md](docs/development/logging.md)

## Executive Summary

This plan outlines how to use the new enhanced logging system and migrate existing code. The enhanced logging system provides structured context tracking, request correlation, and performance monitoring with zero configuration changes needed by developers.

---

## 🎯 Component Overview

### 1. **log_storage_service.py** - In-Memory Log Storage

**Purpose**: Provides queryable log storage for debugging and admin UI

**Key Features**:
- Circular buffer with configurable size (default: 5MB)
- Entity indexing (collection_id, user_id, request_id, pipeline_stage)
- Filtering, pagination, and real-time streaming
- Automatic eviction of old entries when buffer is full

**When to Use**:
- Querying logs programmatically (e.g., admin UI endpoints)
- Real-time log streaming for debugging
- Getting statistics about log activity

**Direct Usage** (rare - usually accessed via LoggingService):
```python
from core.log_storage_service import LogStorageService, LogLevel

storage = LogStorageService(max_size_mb=5)

# Query logs for a specific collection
logs = await storage.get_logs(
    entity_type="collection",
    entity_id="coll_123",
    level=LogLevel.INFO,
    limit=50
)

# Get storage statistics
stats = storage.get_stats()
print(f"Total logs: {stats['total_logs']}")
print(f"Buffer usage: {stats['usage_percent']}%")
```

---

### 2. **enhanced_logging.py** - Main Logging Orchestrator

**Purpose**: Central logging service that coordinates formatters, handlers, and storage

**Key Features**:
- Dual output formats: JSON (production) and text (development)
- File rotation with configurable size limits
- Integration with log_storage_service
- Singleton pattern for global access
- Custom StorageHandler for capturing logs to in-memory buffer

**When to Use**:
- Application startup (initialize once in main.py)
- Getting logger instances throughout the app
- Accessing log storage service

**Usage**:
```python
from core.enhanced_logging import initialize_logging, get_logger, get_logging_service

# 1. Initialize at startup (in main.py)
await initialize_logging(
    log_level="INFO",
    log_format="text",  # "json" for production
    log_to_file=True,
    log_storage_enabled=True,
)

# 2. Get logger in any module
logger = get_logger(__name__)

# 3. Access log storage (for admin endpoints)
service = get_logging_service()
storage = service.get_storage()
if storage:
    logs = await storage.get_logs(entity_type="collection", entity_id="coll_123")
```

---

### 3. **logging_context.py** - Context Management

**Purpose**: Provides context managers for tracking operations with automatic timing and context propagation

**Key Features**:
- ContextVar-based async context propagation
- Automatic request ID generation
- Operation timing with millisecond precision
- Pipeline stage tracking with predefined constants
- Error handling with context preservation

**When to Use**:
- Wrapping service operations (always!)
- Tracking pipeline stages
- Setting request-level context at API boundaries

**Usage**:
```python
from core.enhanced_logging import get_logger
from core.logging_context import (
    log_operation,
    pipeline_stage_context,
    request_context,
    PipelineStage
)

logger = get_logger(__name__)

# 1. Wrap entire operation
async def search(self, search_input: SearchInput):
    with log_operation(
        logger,
        operation="search_documents",
        entity_type="collection",
        entity_id=str(search_input.collection_id),
        user_id=str(search_input.user_id),
        query=search_input.question  # Additional metadata
    ):
        # 2. Track pipeline stages
        with pipeline_stage_context(PipelineStage.QUERY_REWRITING):
            rewritten = await self.rewrite_query(search_input.question)
            logger.info("Query rewritten", extra={
                "original": search_input.question,
                "rewritten": rewritten
            })

        with pipeline_stage_context(PipelineStage.VECTOR_SEARCH):
            results = await self.vector_search(rewritten)
            logger.info("Search completed", extra={
                "result_count": len(results)
            })

        return results

# 3. Set request context at API boundaries
@router.post("/search")
async def search_endpoint(request: Request, search_input: SearchInput):
    with request_context(
        request_id=request.headers.get("X-Request-ID"),
        user_id=str(search_input.user_id)
    ):
        return await search_service.search(search_input)
```

---

### 4. **enhanced_logging_example.py** - Reference Examples

**Purpose**: Comprehensive examples showing integration patterns

**Contains**:
- Simple search operations with pipeline stages
- Chain of Thought reasoning with nested operations
- Error handling with context preservation
- Batch processing with progress tracking
- API endpoint integration patterns

**When to Use**:
- Learning how to integrate enhanced logging
- Reference for common patterns
- Testing the logging system

**Usage**:
```bash
# Run examples
cd backend
python core/enhanced_logging_example.py
```

---

## 🚀 Migration Strategy

### Phase 1: Application Startup (Priority: HIGH)

**File**: `backend/main.py`

**Current State**:
```python
from core.logging_utils import setup_logging, get_logger

setup_logging(log_dir)
logger = get_logger(__name__)
```

**Migrated State**:
```python
from core.enhanced_logging import initialize_logging, get_logger
from core.config import get_settings

settings = get_settings()

# Initialize enhanced logging
await initialize_logging(
    log_level=settings.log_level,
    log_format=settings.log_format,
    log_to_file=settings.log_to_file,
    log_file=settings.log_file,
    log_folder=settings.log_folder,
    log_rotation_enabled=settings.log_rotation_enabled,
    log_max_size_mb=settings.log_max_size_mb,
    log_backup_count=settings.log_backup_count,
    log_storage_enabled=settings.log_storage_enabled,
    log_buffer_size_mb=settings.log_buffer_size_mb,
)

logger = get_logger(__name__)
```

**Testing**:
- Application starts without errors
- Logs appear in console (text format)
- Log file created in logs/ directory
- Log rotation works after reaching size limit

---

### Phase 2: Core Services (Priority: HIGH)

#### 2.1 SearchService

**File**: `backend/rag_solution/services/search_service.py`

**Changes**:
1. Update imports:
```python
from core.enhanced_logging import get_logger
from core.logging_context import log_operation, pipeline_stage_context, PipelineStage
```

2. Wrap main search method:
```python
async def search(self, search_input: SearchInput) -> SearchOutput:
    with log_operation(
        logger,
        operation="search_documents",
        entity_type="collection",
        entity_id=str(search_input.collection_id),
        user_id=str(search_input.user_id),
        query=search_input.question
    ):
        # Existing search logic with pipeline stage tracking
        return search_output
```

3. Add pipeline stage contexts to key operations:
   - Query validation → `PipelineStage.QUERY_VALIDATION`
   - Query rewriting → `PipelineStage.QUERY_REWRITING`
   - Vector search → `PipelineStage.VECTOR_SEARCH`
   - Reranking → `PipelineStage.RERANKING`
   - Answer generation → `PipelineStage.LLM_GENERATION`

**Testing**:
- Search operations complete successfully
- Logs show request_id, collection_id, user_id
- Pipeline stages appear in logs
- Execution time logged automatically

---

#### 2.2 ChainOfThoughtService

**File**: `backend/rag_solution/services/chain_of_thought_service.py`

**Changes**:
1. Wrap main reasoning method:
```python
async def reason(self, query: str, collection_id: UUID, user_id: UUID) -> dict:
    with log_operation(
        logger,
        operation="chain_of_thought_reasoning",
        entity_type="collection",
        entity_id=str(collection_id),
        user_id=str(user_id),
        query=query
    ):
        # CoT logic with stage tracking
        return result
```

2. Track CoT-specific stages:
   - Question decomposition → `PipelineStage.COT_QUESTION_DECOMPOSITION`
   - Sub-question reasoning → `PipelineStage.COT_REASONING`
   - Answer synthesis → `PipelineStage.COT_ANSWER_SYNTHESIS`

**Testing**:
- CoT operations complete successfully
- Nested search operations inherit context
- Sub-questions tracked with proper context
- Reasoning steps visible in logs

---

#### 2.3 DocumentService

**File**: `backend/rag_solution/services/document_service.py`

**Changes**:
1. Wrap document processing operations:
```python
async def process_document(self, doc_id: str, collection_id: UUID) -> dict:
    with log_operation(
        logger,
        operation="process_document",
        entity_type="document",
        entity_id=doc_id,
        collection_id=str(collection_id)
    ):
        # Document processing with stage tracking
        return result
```

2. Track document processing stages:
   - Document parsing → `PipelineStage.DOCUMENT_PARSING`
   - Document chunking → `PipelineStage.DOCUMENT_CHUNKING`
   - Embedding generation → `PipelineStage.EMBEDDING_GENERATION`
   - Vector indexing → `PipelineStage.DOCUMENT_INDEXING`

**Testing**:
- Document uploads work correctly
- Batch processing logs progress
- Errors logged with full context
- Performance metrics captured

---

### Phase 3: Pipeline Stages (Priority: MEDIUM)

**Files**:
- `backend/rag_solution/services/pipeline/stages/query_enhancement_stage.py`
- `backend/rag_solution/services/pipeline/stages/retrieval_stage.py`
- `backend/rag_solution/services/pipeline/stages/reranking_stage.py`
- `backend/rag_solution/services/pipeline/stages/generation_stage.py`

**Changes**:
Each stage should wrap its execution with appropriate pipeline stage context:

```python
async def execute(self, context: PipelineContext) -> PipelineContext:
    with pipeline_stage_context(PipelineStage.QUERY_REWRITING):  # or appropriate stage
        logger.info(f"Executing {self.__class__.__name__}", extra={
            "input_query": context.query
        })

        # Stage logic
        result = await self._process(context)

        logger.info(f"Stage completed", extra={
            "output_query": result.query,
            "modifications_made": result.modified
        })

        return result
```

**Testing**:
- Pipeline execution works end-to-end
- Each stage logged separately
- Stage transitions visible in logs
- Performance of each stage captured

---

### Phase 4: API Routers (Priority: MEDIUM)

**Files**:
- `backend/rag_solution/router/search_router.py`
- `backend/rag_solution/router/collection_router.py`
- `backend/rag_solution/router/document_router.py`

**Changes**:
Add request context at API boundaries:

```python
from core.logging_context import request_context

@router.post("/search")
async def search_endpoint(
    request: Request,
    search_input: SearchInput,
    current_user: User = Depends(get_current_user)
):
    # Set request-level context
    with request_context(
        request_id=request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}",
        user_id=str(current_user.id)
    ):
        logger.info("API request received", extra={
            "endpoint": "/api/search",
            "method": "POST",
            "user_agent": request.headers.get("User-Agent")
        })

        result = await search_service.search(search_input)

        logger.info("API request completed", extra={
            "status": "success",
            "result_count": len(result.results) if hasattr(result, 'results') else 0
        })

        return result
```

**Testing**:
- API requests complete successfully
- Request IDs propagate through entire call stack
- All logs for a request can be filtered by request_id
- User context visible in all logs

---

### Phase 5: Repository Layer (Priority: LOW)

**Files**: `backend/rag_solution/repository/*.py`

**Changes**:
Add logging for database operations with entity context:

```python
async def get_collection(self, collection_id: UUID) -> Collection:
    logger.debug("Fetching collection from database", extra={
        "entity_type": "collection",
        "entity_id": str(collection_id)
    })

    collection = await self.db.execute(query)

    if collection:
        logger.debug("Collection found", extra={
            "entity_type": "collection",
            "entity_id": str(collection_id),
            "collection_name": collection.name
        })
    else:
        logger.warning("Collection not found", extra={
            "entity_type": "collection",
            "entity_id": str(collection_id)
        })

    return collection
```

**Note**: Repository layer typically doesn't need `log_operation` context managers since operations are short. Simple structured logging with `extra` is sufficient.

**Testing**:
- Database queries logged with entity context
- No performance impact from logging
- Sensitive data not logged (passwords, tokens)

---

## 📊 New Admin API Endpoints

Add endpoints to query logs and get statistics:

**File**: `backend/rag_solution/router/admin_router.py` (new or existing)

```python
from core.enhanced_logging import get_logging_service
from core.log_storage_service import LogLevel

@router.get("/admin/logs")
async def get_logs(
    entity_type: str | None = None,
    entity_id: str | None = None,
    level: str | None = None,
    request_id: str | None = None,
    pipeline_stage: str | None = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(require_admin)
):
    """Get filtered logs from in-memory storage."""
    service = get_logging_service()
    storage = service.get_storage()

    if not storage:
        raise HTTPException(status_code=503, detail="Log storage not enabled")

    log_level = LogLevel[level.upper()] if level else None

    logs = await storage.get_logs(
        entity_type=entity_type,
        entity_id=entity_id,
        level=log_level,
        request_id=request_id,
        pipeline_stage=pipeline_stage,
        limit=limit,
        offset=offset
    )

    return {"logs": logs, "count": len(logs)}


@router.get("/admin/logs/stats")
async def get_log_stats(current_user: User = Depends(require_admin)):
    """Get log storage statistics."""
    service = get_logging_service()
    storage = service.get_storage()

    if not storage:
        raise HTTPException(status_code=503, detail="Log storage not enabled")

    return storage.get_stats()


@router.get("/admin/logs/stream")
async def stream_logs(
    websocket: WebSocket,
    current_user: User = Depends(require_admin)
):
    """Stream logs in real-time via WebSocket."""
    await websocket.accept()

    service = get_logging_service()
    storage = service.get_storage()

    if not storage:
        await websocket.close(code=1003, reason="Log storage not enabled")
        return

    try:
        async for log_entry in storage.subscribe():
            await websocket.send_json(log_entry)
    except WebSocketDisconnect:
        pass
```

---

## ✅ Validation Checklist

### After Each Service Migration:

- [ ] Service operations complete successfully
- [ ] Logs include request_id, entity context
- [ ] Pipeline stages visible in logs
- [ ] Execution time logged automatically
- [ ] Errors logged with full context and stack traces
- [ ] No duplicate log entries (check for multiple handlers)
- [ ] Performance impact negligible (<5ms overhead)

### After Complete Migration:

- [ ] All services use enhanced logging
- [ ] Main.py initializes enhanced logging on startup
- [ ] Log files rotate correctly
- [ ] JSON format works in production
- [ ] Text format readable in development
- [ ] Log storage queryable via admin endpoints
- [ ] Documentation updated with examples
- [ ] Tests added for new logging patterns

---

## 🎯 Priority Order

1. **HIGH** - Application startup (main.py) - Enables enhanced logging
2. **HIGH** - SearchService - Most critical user-facing operation
3. **HIGH** - ChainOfThoughtService - Complex operation that benefits most
4. **MEDIUM** - Pipeline stages - Granular performance tracking
5. **MEDIUM** - API routers - Request correlation at boundaries
6. **MEDIUM** - DocumentService - Batch operations with progress
7. **LOW** - Repository layer - Simple database operation logging
8. **LOW** - Admin endpoints - Nice-to-have for debugging

---

## 📈 Expected Benefits

### Development:
- **50% faster debugging** - Structured context makes issues obvious
- **Full request tracing** - Track requests through entire pipeline
- **Performance insights** - Know exactly where time is spent
- **Developer-friendly** - Human-readable text format

### Production:
- **Zero performance impact** - Async operation with buffering
- **Production-ready** - JSON output for monitoring tools
- **Queryable logs** - In-memory storage for admin UI
- **Monitoring integration** - Works with ELK, Splunk, Datadog, CloudWatch

---

## 🔍 Testing Strategy

### Unit Tests:
```bash
# Test enhanced logging components
pytest tests/unit/test_enhanced_logging.py -v
```

### Integration Tests:
```bash
# Test with real services
pytest tests/integration/test_search_with_logging.py -v
```

### Manual Testing:
```bash
# Run example file
python backend/core/enhanced_logging_example.py

# Start application and test search
make local-dev-backend

# Query logs via admin API
curl http://localhost:8000/admin/logs?entity_type=collection&entity_id=coll_123
```

---

## 📚 References

- **Full Documentation**: [docs/development/logging.md](docs/development/logging.md)
- **Example Code**: [backend/core/enhanced_logging_example.py](backend/core/enhanced_logging_example.py)
- **Issue #218**: Enhanced Logging Implementation
- **IBM mcp-context-forge**: https://github.com/IBM/mcp-context-forge

---

## 🚦 Next Steps

1. **Review this plan** - Team review and approval
2. **Phase 1** - Update main.py initialization
3. **Phase 2** - Migrate SearchService and ChainOfThoughtService
4. **Phase 3** - Migrate pipeline stages
5. **Phase 4** - Add API router context boundaries
6. **Phase 5** - Repository layer logging
7. **Add admin endpoints** - Log query/stats/streaming
8. **Update documentation** - Add real-world examples from migrated code
9. **Monitor performance** - Ensure <5ms overhead
10. **Production rollout** - Switch to JSON format in production

---

## ❓ Questions?

- How to use each component? → See "Component Overview" section above
- Which files to modify? → See "Migration Strategy" section
- What order to migrate? → See "Priority Order" section
- How to test? → See "Testing Strategy" section
- Examples? → See `backend/core/enhanced_logging_example.py`
