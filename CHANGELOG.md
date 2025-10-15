# Changelog

All notable changes to the RAG Modulo project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Multi-Provider Podcast Audio Generation** (PR #TBD): Comprehensive custom voice support with multi-provider TTS
  - **Per-Turn Provider Selection**: Each dialogue turn can use different TTS provider (OpenAI, ElevenLabs)
  - **Custom Voice Resolution**: Automatic UUID-based voice detection, database lookup, and provider mapping
  - **ElevenLabs Integration**: Added ElevenLabs provider with voice cloning support
  - **Audio Stitching**: Seamless combination of audio segments from different providers with 500ms pauses
  - **Script Format Flexibility**: Support for multiple dialogue formats (HOST:, [HOST]:, [Host]:, etc.)
  - **LLM Prompt Improvements**: Prevents placeholder names ([HOST NAME], [EXPERT NAME]) in generated scripts
  - **Provider Caching**: Efficient provider instance management to avoid recreation per turn
  - **Type Safety**: Replaced `Any` types with proper `AudioProviderBase` type hints
  - **Configuration**: Added ElevenLabs settings to env.example with comprehensive defaults
  - **Code Quality**: All linting checks passed (Ruff, Pylint 9.37/10)

- **Reusable UI Components Library** (Issue #395, PR #402): Comprehensive UI component system for consistent frontend design
  - **8 New Components**: Button, Input, TextArea, Select, Modal, Card, Badge, FileUpload
  - **Design System**: Carbon Design System principles with Tailwind CSS styling
  - **Accessibility**: ARIA labels, keyboard navigation, focus management, screen reader support
  - **Type Safety**: Full TypeScript support with exported interfaces
  - **Documentation**: Component README and comprehensive mkdocs documentation
  - **Migration Example**: Refactored LightweightCreateCollectionModal (44% code reduction)
  - **Features**: Multiple variants, sizes, loading states, error handling, drag & drop file upload
  - **Quality**: All components pass ESLint, proper focus trap in modals, file validation

### Fixed

- **UI Component Accessibility & Validation** (PR #402): Addressed all PR review items
  - **Modal Focus Management**: Added focus trap, Escape key handler, focus return on close
  - **FileUpload Validation**: File size and type validation with error messages
  - **ID Generation**: Replaced Math.random() with React 18 useId hook (Input, TextArea, Select, FileUpload)
  - **Button ARIA**: Added aria-busy and aria-label for loading states
  - **Impact**: 100% accessibility compliance, zero ID collisions, proper error feedback

- **Comprehensive Code Review Fixes** (PR #360): Resolved all 13 critical issues from code review
  - **Authentication Security**: Added error state, user-friendly messages, retry mechanism in AuthContext
  - **API Performance**: Implemented 5-minute caching for user info (95% reduction in API calls)
  - **Role Management**: Centralized role mapping and permission management
  - **User Feedback**: Added collection load error notifications
  - **Polling Efficiency**: Implemented exponential backoff (5s → 10s → 30s → 60s max) for podcast generation
  - **Voice Validation**: Added schema-level validation for TTS voice IDs
  - **Error Handling**: Comprehensive error handling with automatic resource cleanup in podcast service
  - **Audio Streaming**: Full RFC 7233 HTTP Range request support for seek functionality
  - **Type Safety**: Standardized UUID types throughout backend
  - **Merge Conflicts**: Resolved Makefile (streamlined version) and dependencies.py (SKIP_AUTH logic)
  - **Impact**: 95% reduction in user API calls, 75% reduction in polling load, zero storage leaks

- **Podcast Generation Endpoint** (PR #TBD): Fixed complete podcast generation pipeline
  - Fixed API route prefix from `/podcasts` to `/api/podcasts` (404 → 202)
  - Converted `PodcastRepository` from `AsyncSession` to `Session` (matching codebase pattern)
  - Updated `PodcastService` to use synchronous database operations
  - Fixed content retrieval to use `result.chunk.text` instead of `doc.chunk_text`
  - Fixed `LLMProviderFactory` usage (static method → instance method pattern)
  - Added required template parameter for WatsonX script generation
  - Updated script parser regex patterns to handle multiline speaker labels
  - Added `.strip()` to OpenAI API key to prevent "Illegal header value" errors
  - Reduced minimum document requirement from 5 to 1 (`PODCAST_MIN_DOCUMENTS`)
  - Successfully generates podcasts with RAG → LLM → TTS pipeline (0% → 100%)

### Added

- **CI/CD Pipeline Optimization** (#349, PR #354): Significantly improved GitHub Actions workflow efficiency
  - Reduced PR feedback time from ~15 min to ~2-3 min (85% improvement)
  - Added concurrency control to cancel outdated runs (~1,500 min/month savings)
  - Renamed workflows with numbered prefixes (01- through 07-) for clarity
  - Added frontend linting workflow (07-frontend-lint.yml) with ESLint
  - Created Issue #355 for comprehensive frontend tests
  - Added IBM-style documentation to workflows with numbered steps
  - Smart path filtering: Docker builds only on Dockerfile/dependency changes
  - Weekly security audits with jq-based vulnerability parsing
  - Follows IBM's mcp-context-forge pattern: one workflow per purpose

- **Document Upload Pipeline**: Full document ingestion pipeline for collection creation
  - New `/api/collections/with-files` endpoint for creating collections with documents
  - New `/api/collections/{collection_id}/documents` endpoint for adding documents to existing collections
  - Frontend `createCollectionWithFiles()` method in apiClient
  - Automatic background processing with PipelineService integration

- **Production Deployment Support**: Added Makefile targets for production deployment
  - `make prod-start`: Start all services with docker-compose.production.yml
  - `make prod-stop`: Stop production environment
  - `make prod-restart`: Restart production environment
  - `make prod-logs`: View production logs
  - `make prod-status`: Check production service status

### Changed
- **Milvus Connection Stability**: Improved connection handling in MilvusStore
  - Added explicit disconnection before reconnecting to prevent stale connections
  - Fixes issues with connection caching when switching between hosts

- **Local Development Workflow**: Enhanced Makefile for better developer experience
  - Fixed frontend directory references (webui → frontend)
  - Added log file outputs for easier debugging
  - Updated process detection for react-scripts instead of vite
  - Improved local development status reporting

- **Frontend Configuration**: Updated for local development
  - Changed proxy from `http://backend:8000` to `http://localhost:8000`
  - Supports containerless local development workflow

- **Collection Creation**: Enhanced error handling
  - Added 409 Conflict response for duplicate collection names
  - Proper AlreadyExistsError handling in collection router

- **Frontend Collection Creation**: Improved UX for document uploads
  - Real file upload instead of simulated progress
  - Support for creating collections with initial documents
  - Proper FormData handling for multi-file uploads

### Fixed
- **Collection Creation Modal**: Fixed document upload functionality
  - Removed fake upload simulation
  - Store actual File objects for upload
  - Fixed drag-and-drop file handling
  - Properly invoke document ingestion pipeline

### Technical Debt
- Removed log file modifications from git tracking (already in .gitignore)
- Cleaned up orphaned log files (logs/rag_modulo.log.1, logs/rag_modulo.log.3)

---

## [Previous Releases]

### [0.1.0] - 2025-09-30

#### Major Features
- Collection creation and management
- Document processing and chunking
- Vector store integration (Milvus)
- Search functionality with CoT reasoning
- Chat interface with WebSocket support
- Dashboard analytics
- Multi-provider LLM support (WatsonX, OpenAI, Anthropic)

#### Infrastructure
- Docker Compose orchestration
- PostgreSQL for metadata
- MLFlow for model tracking
- MinIO for object storage
- Comprehensive test suite (unit, integration, API, performance)
- CI/CD pipeline with GitHub Actions

---

## Release Notes

### Version Numbering
- **Major version** (X.0.0): Breaking changes, major architectural updates
- **Minor version** (0.X.0): New features, non-breaking changes
- **Patch version** (0.0.X): Bug fixes, minor improvements

### Categories
- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security fixes
- **Technical Debt**: Code quality improvements
