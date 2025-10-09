# Atomic PR Plan

## Overview

This document outlines the atomic pull requests to be created from the current changes. Each PR is self-contained, independently testable, and focused on a single concern.

---

## PR #1: Infrastructure - Milvus Connection Stability Fix

**Priority:** HIGH
**Type:** Bug Fix
**Estimated Review Time:** 5 minutes

### Description
Fixes Milvus connection stability issues by explicitly disconnecting stale connections before reconnecting. Prevents connection caching problems when switching between different Milvus hosts.

### Files Changed
- `backend/vectordbs/milvus_store.py`

### Changes Summary
```python
# Added explicit disconnection before reconnect:
try:
    connections.disconnect("default")
    logging.info("Disconnected existing Milvus connection")
except Exception:
    pass  # No existing connection, continue
```

### Testing
- ✅ Unit tests pass
- ✅ Integration tests with Milvus pass
- ✅ Connection switching works correctly

### Risk Level
**LOW** - Defensive coding, fail-safe exception handling

---

## PR #2: Backend - Document Upload & Error Handling Improvements

**Priority:** HIGH
**Type:** Feature + Enhancement
**Estimated Review Time:** 12 minutes

### Description
Adds missing API endpoint for uploading documents to existing collections AND improves collection creation error handling. Completes the document management workflow by allowing users to add files after collection creation, with better error feedback for duplicate names.

### Files Changed
- `backend/rag_solution/router/collection_router.py`

### Changes Summary

**1. New Document Upload Endpoint (+73 lines at line 650)**
- Added `POST /api/collections/{collection_id}/documents` endpoint
- Reuses `_upload_files_and_trigger_processing()` method
- Triggers background document processing pipeline
- Proper error handling (401, 400, 404, 500)

```python
@router.post("/{collection_id}/documents")
async def upload_documents_to_collection(
    request: Request,
    collection_id: UUID4,
    files: list[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> list[FileOutput]
```

**2. Duplicate Name Error Handling (+4 lines at line 200)**
- Added `AlreadyExistsError` import
- Returns HTTP 409 Conflict for duplicate collection names
- Better error messages for users

```python
except AlreadyExistsError as e:
    logger.error("Collection already exists: %s", str(e))
    raise HTTPException(status_code=409, detail=str(e)) from e
```

### Testing
- ✅ New endpoint responds correctly
- ✅ Multi-file upload works
- ✅ Background processing triggered
- ✅ Duplicate collection name returns 409
- ✅ Error messages are user-friendly
- ✅ All error handling validated

### Risk Level
**LOW** - New endpoint uses existing service methods; error handling is defensive

---

## PR #3: Frontend - Document Upload Pipeline for Collection Creation

**Priority:** HIGH
**Type:** Feature
**Estimated Review Time:** 15 minutes

### Description
Implements complete document upload functionality for collection creation modal. Replaces fake upload simulation with real file upload and ingestion pipeline integration.

### Files Changed
- `frontend/src/services/apiClient.ts`
- `frontend/src/components/modals/LightweightCreateCollectionModal.tsx`

### Changes Summary

**apiClient.ts:**
- Added `createCollectionWithFiles()` method
- Uses FormData for multi-file upload
- Calls `/api/collections/with-files` endpoint

**LightweightCreateCollectionModal.tsx:**
- Stores actual File objects instead of mock metadata
- Removed fake upload simulation
- Conditional logic: uses `createCollectionWithFiles()` when files present
- Fixed drag-and-drop file handling

### Testing
- ✅ Collection creation without files works
- ✅ Collection creation with files works
- ✅ Multi-file upload works
- ✅ Drag-and-drop works
- ✅ Document ingestion pipeline triggered

### Risk Level
**MEDIUM** - User-facing feature, but well-tested

---

## PR #4: Frontend - Collections List Refresh (Optional)

**Priority:** LOW
**Type:** Enhancement
**Estimated Review Time:** 5 minutes

### Description
Minor improvements to collections list component (if any meaningful changes exist beyond cleanup).

### Files Changed
- `frontend/src/components/collections/LightweightCollections.tsx`

### Changes Summary
Review diff to determine if changes are substantial enough for separate PR or should be included in PR #3.

### Risk Level
**VERY LOW**

---

## PR #5: Infrastructure - Local Development Workflow Enhancements

**Priority:** MEDIUM
**Type:** Enhancement
**Estimated Review Time:** 10 minutes

### Description
Improves local development workflow with better Makefile targets, logging, and process management. Adds production deployment targets.

### Files Changed
- `Makefile`
- `frontend/package.json` (proxy configuration)

### Changes Summary

**Makefile:**
- Fixed `webui → frontend` directory references
- Added background logging to `/tmp/rag-backend.log`
- Updated process detection (vite → react-scripts)
- Added production deployment targets: `prod-start`, `prod-stop`, `prod-restart`, `prod-logs`, `prod-status`

**frontend/package.json:**
- Changed proxy from `http://backend:8000` to `http://localhost:8000` for local dev

### Testing
- ✅ `make local-dev-setup` works
- ✅ `make local-dev-backend` starts successfully
- ✅ `make local-dev-frontend` starts successfully
- ✅ `make local-dev-status` reports correctly
- ✅ `make prod-start` works with docker-compose.production.yml

### Risk Level
**LOW** - Developer tooling, doesn't affect production

---

## PR #6: Documentation - Project Documentation Updates

**Priority:** MEDIUM
**Type:** Documentation
**Estimated Review Time:** 15 minutes

### Description
Comprehensive documentation updates including getting started guide, CI/CD pipeline details, deployment options, and changelog.

### Files Changed
- `README.md`
- `AGENTS.md`
- `CHANGELOG.md` (new file)

### Changes Summary

**README.md:**
- Enhanced "Quick Start" with local development (recommended approach)
- Added comprehensive CI/CD Pipeline section
- Added Deployment & Packaging section with cloud options
- Improved getting started instructions

**AGENTS.md:**
- Updated current development phase
- Added October 8, 2025 accomplishments

**CHANGELOG.md (NEW):**
- Created project changelog following Keep a Changelog format
- Documented all unreleased changes
- Structured for semantic versioning

### Testing
- ✅ All markdown renders correctly
- ✅ Links are valid
- ✅ Code examples are accurate

### Risk Level
**VERY LOW** - Documentation only

---

## PR #7: Cleanup - Remove Tracked Log Files

**Priority:** LOW
**Type:** Cleanup
**Estimated Review Time:** 2 minutes

### Description
Removes accidentally tracked log files that are already covered by .gitignore.

### Files Changed
- `logs/rag_modulo.log.1` (deleted)
- `logs/rag_modulo.log.3` (deleted)

### Changes Summary
```bash
git rm logs/rag_modulo.log.1 logs/rag_modulo.log.3
```

### Testing
- ✅ Files ignored by .gitignore
- ✅ No impact on functionality

### Risk Level
**NONE** - File cleanup only

---

## PR #8: Infrastructure - Production Docker Compose (Optional)

**Priority:** LOW
**Type:** Enhancement
**Estimated Review Time:** 10 minutes

### Description
Adds production-ready docker-compose configuration if `docker-compose.production.yml` contains meaningful differences from the standard docker-compose.yml.

### Files Changed
- `docker-compose.production.yml` (new file)

### Review Required
Need to check if this file should be committed or if it's environment-specific.

### Risk Level
**LOW** - Infrastructure configuration

---

## Recommended PR Order

1. **PR #7** - Cleanup (quick win, no dependencies)
2. **PR #1** - Milvus stability (infrastructure fix)
3. **PR #2** - Document upload endpoint + error handling (backend improvements)
4. **PR #3** - Document upload UI (frontend feature, depends on PR #2)
5. **PR #5** - Local dev workflow (developer experience)
6. **PR #6** - Documentation (no code dependencies)
7. **PR #8** - Production compose (if needed)

**Total Review Time:** ~66 minutes (reduced from 72 by combining PRs #2 and #3)

## Testing Strategy

### Per-PR Testing
Each PR should be tested independently:
- Unit tests pass
- Integration tests pass (if applicable)
- Manual testing of changed functionality
- No regression in existing features

### Combined Testing
After all PRs merged:
- Full E2E testing
- Performance testing
- User acceptance testing

## Rollback Strategy

Each PR is independently revertible:
1. PRs #1-3: Backend changes can be reverted individually
2. PR #4: Frontend can be reverted without affecting backend
3. PRs #6-7: Tooling/docs don't affect runtime
4. PR #8: Cleanup has no functional impact

## Notes

- All PRs follow atomic commit principles
- Each PR has a clear, single purpose
- Dependencies are clearly marked
- Risk levels help prioritize review
- All changes are backward compatible
