# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG Modulo is a modular Retrieval-Augmented Generation (RAG) solution with flexible vector database support, customizable embedding models, and document processing capabilities. The project uses a service-based architecture with clean separation of concerns.

**Recent Update**: The system has been simplified with automatic pipeline resolution, eliminating client-side pipeline management complexity while maintaining full RAG functionality.

## Architecture

### Backend (Python/FastAPI)
- **Service Layer**: Business logic in `backend/rag_solution/services/`
- **Repository Pattern**: Data access in `backend/rag_solution/repository/`
- **Provider System**: LLM providers in `backend/rag_solution/generation/providers/`
- **Router Layer**: API endpoints in `backend/rag_solution/router/`
- **Models**: SQLAlchemy models in `backend/rag_solution/models/`
- **Schemas**: Pydantic schemas in `backend/rag_solution/schemas/`

### Frontend (React/Carbon Design)
- React 18 with Carbon Design System
- Located in `webui/` directory
- Uses axios for API calls

### Infrastructure
- PostgreSQL for metadata
- Milvus for vector storage (configurable)
- MLFlow for model tracking
- MinIO for object storage
- Docker Compose for orchestration

## Common Development Commands

### Running the Application
```bash
# Quick start with pre-built images (recommended)
make run-ghcr

# Build and run locally
make build-all
make run-app

# Access points
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# MLFlow: http://localhost:5001
```

### Testing
```bash
# Run specific test file
make test testfile=tests/api/test_auth.py

# Run test categories
make unit-tests          # Unit tests with coverage
make integration-tests   # Integration tests
make api-tests          # API endpoint tests
make performance-tests  # Performance benchmarks

# Local testing without Docker
cd backend && poetry run pytest tests/ -m unit
```

### Code Quality
```bash
# Quick quality check (formatting + linting)
make quick-check

# Auto-fix formatting and import issues
make fix-all

# Full linting (Ruff + MyPy)
make lint

# Run linting with Poetry directly
cd backend && poetry run ruff check rag_solution/ tests/ --line-length 120
cd backend && poetry run mypy rag_solution/ --ignore-missing-imports

# Security checks
make security-check
```

### Dependency Management
```bash
# Backend dependencies (using Poetry)
cd backend
poetry install --with dev,test  # Install all dependencies
poetry add <package>            # Add new dependency
poetry lock                     # Update lock file

# Frontend dependencies
cd webui
npm install                     # Install dependencies
npm run dev                    # Development mode with hot reload
```

## Key Environment Variables

Required environment variables (see `env.example` for full list):
- `COLLECTIONDB_*`: PostgreSQL configuration
- `VECTOR_DB`: Vector database type (default: milvus)
- `MILVUS_*`: Milvus configuration
- `WATSONX_*`: WatsonX API credentials
- `OPENAI_API_KEY`: OpenAI API key (optional)
- `ANTHROPIC_API_KEY`: Anthropic API key (optional)
- `JWT_SECRET_KEY`: JWT secret for authentication

## Testing Strategy

### Test Markers
- `@pytest.mark.unit`: Fast unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.api`: API endpoint tests
- `@pytest.mark.performance`: Performance tests
- `@pytest.mark.atomic`: Atomic model tests

### Test Organization
- Unit tests: `backend/tests/services/`, `backend/tests/test_*.py`
- Integration tests: `backend/tests/integration/`
- Performance tests: `backend/tests/performance/`
- API tests: `backend/tests/api/`

## CI/CD Pipeline

### GitHub Actions Workflow
1. **Lint and Unit Tests**: Fast feedback without infrastructure
2. **Build Images**: Docker images built and pushed to GHCR
3. **Integration Tests**: Full stack testing with all services

### Local CI Validation
```bash
# Run same checks as CI locally
make ci-local

# Validate CI workflows
make validate-ci
```

## Important Notes

### Current Status
- ✅ **Simplified Pipeline Resolution**: Automatic pipeline selection implemented (GitHub Issue #222)
- ✅ Infrastructure and containers working
- ✅ Comprehensive test suite implemented and passing
- ✅ API documentation updated for simplified architecture
- ⚠️ Authentication system needs fixing (OIDC issues blocking some features)

### Development Best Practices
1. **Service Architecture**: Always implement features as services with dependency injection
2. **Type Hints**: Use type hints throughout the codebase
3. **Async/Await**: Use async operations where appropriate
4. **Error Handling**: Proper error handling with custom exceptions
5. **Testing**: Write tests for new features (unit + integration)
6. **Line Length**: 120 characters for Python code

### Vector Database Support
The system supports multiple vector databases through a common interface:
- Milvus (default)
- Elasticsearch
- Pinecone
- Weaviate
- ChromaDB

### LLM Provider Integration
Providers are abstracted through a common interface:
- WatsonX (IBM)
- OpenAI
- Anthropic

Each provider implementation is in `backend/rag_solution/generation/providers/`.

## Troubleshooting

### Container Issues
```bash
# Check container health
docker compose ps

# View logs
make logs

# Restart services
make stop-containers
make run-services
```

### Test Failures
```bash
# Run specific test with verbose output
make test testfile=tests/api/test_auth.py

# Check test logs
docker compose logs test
```

### Dependency Issues
```bash
# Regenerate Poetry lock file
cd backend && poetry lock

# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
```

## API and Search System

### Simplified Search Architecture

The search system now uses automatic pipeline resolution:

**Search Input Schema** (simplified):
```python
class SearchInput(BaseModel):
    question: str
    collection_id: UUID4
    user_id: UUID4
    config_metadata: dict[str, Any] | None = None
    # pipeline_id removed - handled automatically
```

**Key Benefits**:
- No client-side pipeline management required
- Automatic pipeline creation for new users
- Intelligent error handling for configuration issues
- Simplified CLI and API interfaces

### Search API Usage

```python
# Simple search request
search_input = SearchInput(
    question="What is machine learning?",
    collection_id=collection_uuid,
    user_id=user_uuid
)

# Backend automatically:
# 1. Resolves user's default pipeline
# 2. Creates pipeline if none exists
# 3. Uses user's LLM provider settings
# 4. Executes search and returns results
```

### CLI Search Commands

```bash
# Simple search - no pipeline management needed
./rag-cli search query col_123abc "What is machine learning?"

# System automatically handles:
# - Pipeline resolution
# - LLM provider selection
# - Configuration management
```

## Documentation References

### API Documentation
- **API Overview**: `docs/api/index.md` - Complete API documentation
- **Search API**: `docs/api/search_api.md` - Search system with automatic pipeline resolution
- **Search Schemas**: `docs/api/search_schemas.md` - Data structures and validation
- **Service Configuration**: `docs/api/service_configuration.md` - Backend service setup
- **Provider Configuration**: `docs/api/provider_configuration.md` - LLM provider management

### CLI Documentation
- **CLI Overview**: `docs/cli/index.md` - Command-line interface guide
- **Search Commands**: `docs/cli/commands/search.md` - Search operations
- **Authentication**: `docs/cli/authentication.md` - CLI authentication setup
- **Configuration**: `docs/cli/configuration.md` - CLI configuration management

### Development Documentation
- **Backend Development**: `docs/development/backend/index.md` - Backend development guidelines
- **Development Workflow**: `docs/development/workflow.md` - Development process
- **Contributing**: `docs/development/contributing.md` - Contribution guidelines
- **Testing Guide**: `docs/testing/index.md` - Comprehensive testing documentation

### Other References
- **Installation**: `docs/installation.md` - Setup and installation guide
- **Configuration**: `docs/configuration.md` - System configuration
- **Getting Started**: `docs/getting-started.md` - Quick start guide
- **Main README**: `README.md` - Project overview

## Key Architecture Changes

### Simplified Pipeline Resolution (GitHub Issue #222)

**What Changed**:
- Removed `pipeline_id` from `SearchInput` schema (`rag_solution/schemas/search_schema.py`)
- Added automatic pipeline resolution in `SearchService` (`rag_solution/services/search_service.py`)
- Simplified CLI search commands by removing pipeline parameters
- Enhanced error handling for configuration issues

**Implementation Details**:
- `SearchService._resolve_user_default_pipeline()` method handles automatic pipeline selection
- Creates default pipelines for new users using their LLM provider
- Validates pipeline accessibility and handles errors gracefully
- CLI commands simplified to only require collection_id and query

**Testing**:
- Unit tests: `tests/unit/test_search_service_pipeline_resolution.py`
- Integration tests: `tests/integration/test_search_integration.py`
- All tests passing with automatic pipeline resolution

**Breaking Changes**:
- SearchInput schema no longer accepts `pipeline_id` field
- CLI search commands no longer require `--pipeline-id` parameter
- API clients must update to use simplified schema

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
