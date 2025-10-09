# Changelog

All notable changes to the RAG Modulo project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
