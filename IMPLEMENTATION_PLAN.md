# Enhanced Logging Service Implementation Plan

**Issue**: #218 - Implement Enhanced Logging Service with Structured Context and Traceability
**Branch**: `claude/investigate-issue-218-011CUNPTpNNpBsdokV5zxHgu`
**Date**: 2025-10-22

## Overview

Implement enhanced logging based on patterns from IBM mcp-context-forge project, adapted for RAG Modulo's specific needs.

## Goals

1. **Structured Logging**: JSON output for production, text for development
2. **Context Tracking**: Automatic request correlation and entity tracking
3. **Traceability**: Full pipeline stage tracking for debugging
4. **Performance Monitoring**: Automatic timing for operations
5. **Queryable Logs**: In-memory storage for admin UI and debugging

## Architecture

```
core/
├── enhanced_logging.py      # Main LoggingService (orchestrator)
├── logging_context.py       # Context management and propagation
├── log_storage_service.py   # In-memory log storage with indexing
└── config.py                # Configuration updates
```

## Implementation Phases

### Phase 1: Core Infrastructure (Today)

#### 1.1 Dependencies
- **File**: `backend/pyproject.toml`
- **Changes**: Add `python-json-logger = "^2.0.7"`
- **Status**: Pending

#### 1.2 Context Management
- **File**: `backend/core/logging_context.py`
- **Purpose**: ContextVar-based async context propagation
- **Features**:
  - LogContext dataclass (request_id, user_id, collection_id, pipeline_stage, operation)
  - Context managers: `log_operation()`, `pipeline_stage_context()`
  - Context utilities: `set_context()`, `get_context()`, `clear_context()`
- **Status**: Pending

#### 1.3 Log Storage Service
- **File**: `backend/core/log_storage_service.py`
- **Purpose**: In-memory circular buffer for log storage
- **Features**:
  - LogEntry dataclass with entity context
  - Circular buffer with size limits (configurable MB)
  - Entity indexing (collection_id, user_id, request_id)
  - Filtering by entity, level, time range, search text
  - Real-time streaming via AsyncGenerator
  - Statistics and usage tracking
- **Status**: Pending

#### 1.4 Enhanced Logging Service
- **File**: `backend/core/enhanced_logging.py`
- **Purpose**: Main logging orchestrator
- **Features**:
  - Dual formatters (JSON + text)
  - LoggingService with initialize/shutdown
  - Custom StorageHandler for log capture
  - Context-aware logging
  - Performance timing integration
  - Logger hierarchy management
- **Status**: Pending

#### 1.5 Configuration Updates
- **File**: `backend/core/config.py`
- **Changes**: Add logging settings
  ```python
  # Logging configuration
  log_format: str = "text"  # or "json"
  log_to_file: bool = True
  log_file: str = "rag_modulo.log"
  log_folder: Optional[str] = "logs"
  log_rotation_enabled: bool = True
  log_max_size_mb: int = 10
  log_backup_count: int = 5

  # Log storage
  log_storage_enabled: bool = True
  log_buffer_size_mb: int = 5
  ```
- **Status**: Pending

### Phase 2: Service Integration (Next)

#### 2.1 SearchService Integration (Proof of Concept)
- **File**: `backend/rag_solution/services/search_service.py`
- **Changes**:
  - Import enhanced logging utilities
  - Wrap search operations with `log_operation()`
  - Add pipeline stage contexts
  - Add structured metadata to log messages
- **Example**:
  ```python
  with log_operation(logger, "search_documents", "collection", str(collection_id)):
      with pipeline_stage_context("query_rewriting"):
          rewritten = await rewrite_query(query)
          logger.info("Query rewritten", extra={"original": query, "rewritten": rewritten})
  ```
- **Status**: Pending

#### 2.2 Other Service Integrations
- CollectionService
- PipelineService
- FileManagementService
- LLMProviderService
- **Status**: Future

### Phase 3: Testing (Next)

#### 3.1 Unit Tests
- **File**: `backend/tests/unit/test_enhanced_logging.py`
- **Coverage**:
  - Context management
  - Log storage operations
  - Filtering and pagination
  - JSON/text formatting
- **Status**: Pending

#### 3.2 Integration Tests
- **File**: `backend/tests/integration/test_logging_integration.py`
- **Coverage**:
  - End-to-end request tracing
  - Pipeline stage tracking
  - Performance timing
- **Status**: Future

### Phase 4: Documentation (Next)

#### 4.1 CLAUDE.md Updates
- Usage examples
- Configuration guide
- Migration guide from old logging
- **Status**: Pending

#### 4.2 Developer Documentation
- API reference for logging utilities
- Best practices for service integration
- **Status**: Future

## File-by-File Changes

### 1. backend/pyproject.toml
```diff
[tool.poetry.dependencies]
python = "^3.11"
+ python-json-logger = "^2.0.7"
```

### 2. backend/core/logging_context.py (NEW FILE)
**Lines**: ~150
**Purpose**: Context management for async operation tracking
**Key Classes**: LogContext, log_operation, pipeline_stage_context

### 3. backend/core/log_storage_service.py (NEW FILE)
**Lines**: ~400
**Purpose**: In-memory log storage with indexing
**Key Classes**: LogEntry, LogStorageService

### 4. backend/core/enhanced_logging.py (NEW FILE)
**Lines**: ~500
**Purpose**: Main logging service
**Key Classes**: LoggingService, StorageHandler

### 5. backend/core/config.py (UPDATE)
```diff
class Settings(BaseSettings):
+     # Logging configuration
+     log_format: Annotated[str, Field(default="text", alias="LOG_FORMAT")]
+     log_to_file: Annotated[bool, Field(default=True, alias="LOG_TO_FILE")]
+     log_file: Annotated[str, Field(default="rag_modulo.log", alias="LOG_FILE")]
+     log_folder: Annotated[str | None, Field(default="logs", alias="LOG_FOLDER")]
+     log_rotation_enabled: Annotated[bool, Field(default=True, alias="LOG_ROTATION_ENABLED")]
+     log_max_size_mb: Annotated[int, Field(default=10, alias="LOG_MAX_SIZE_MB")]
+     log_backup_count: Annotated[int, Field(default=5, alias="LOG_BACKUP_COUNT")]
+     log_filemode: Annotated[str, Field(default="a", alias="LOG_FILEMODE")]
+
+     # Log storage
+     log_storage_enabled: Annotated[bool, Field(default=True, alias="LOG_STORAGE_ENABLED")]
+     log_buffer_size_mb: Annotated[int, Field(default=5, alias="LOG_BUFFER_SIZE_MB")]
```

### 6. backend/rag_solution/services/search_service.py (UPDATE)
**Changes**:
- Import enhanced logging utilities
- Wrap operations with context managers
- Add structured metadata

## Migration Strategy

### Backward Compatibility
- Keep `logging_utils.py` functional during migration
- Old `get_logger()` continues to work
- Gradual service-by-service migration

### Migration Path
1. Phase 1: Deploy new infrastructure (no breaking changes)
2. Phase 2: Migrate SearchService as proof of concept
3. Phase 3: Migrate other services incrementally
4. Phase 4: Deprecate old logging_utils.py (after all migrations)

## Success Metrics

- ✅ Structured JSON logs in production
- ✅ Request tracing across entire RAG pipeline
- ✅ Pipeline stage timing visible in logs
- ✅ Zero performance impact (< 1% overhead)
- ✅ All tests passing
- ✅ Log storage queryable via API (future)

## Testing Strategy

### Unit Tests
- Context propagation in async functions
- Log storage filtering and pagination
- JSON/text formatter output validation
- Context manager proper cleanup

### Integration Tests
- End-to-end search with full logging
- Pipeline stage tracking verification
- Performance timing accuracy

### Manual Testing
- Local development with text format
- Production simulation with JSON format
- Log storage queries

## Timeline

- **Day 1**: Core infrastructure (logging_context, log_storage_service, enhanced_logging)
- **Day 2**: Configuration updates, SearchService integration
- **Day 3**: Testing, documentation
- **Day 4**: Review, refinement, PR creation

## Notes

- Based on mcp-context-forge patterns but adapted for RAG domain
- Focus on minimal performance overhead
- Prioritize developer experience (easy to use context managers)
- Enable future admin UI for log viewing
