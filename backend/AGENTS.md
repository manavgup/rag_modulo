# Backend - AI Agent Context

## Overview

The backend is a Python 3.12+ FastAPI application providing the core RAG Modulo API, implementing enterprise-grade document processing, vector search, and AI-powered question answering with Chain of Thought reasoning.

## Directory Structure

```
backend/
├── rag_solution/           # Main application package
│   ├── services/           # Business logic layer
│   ├── models/             # SQLAlchemy database models
│   ├── schemas/            # Pydantic validation schemas
│   ├── router/             # FastAPI endpoint handlers
│   ├── repository/         # Data access layer
│   ├── generation/         # LLM provider integrations
│   ├── retrieval/          # Vector database operations
│   ├── data_ingestion/     # Document processing pipeline
│   ├── pipeline/           # RAG pipeline orchestration
│   ├── query_rewriting/    # Query enhancement
│   ├── file_management/    # File operations & MinIO
│   ├── cli/                # Command-line interface
│   └── utils/              # Utility functions
├── core/                   # Core configuration and utilities
├── auth/                   # Authentication modules
├── vectordbs/              # Vector database abstractions
├── tests/                  # Comprehensive test suite
│   ├── unit/               # Unit tests (fast, no deps)
│   ├── integration/        # Integration tests (with services)
│   ├── api/                # API endpoint tests
│   └── performance/        # Performance benchmarks
├── main.py                 # FastAPI application entry point
├── pyproject.toml          # Poetry dependency management
└── pytest.ini              # Test configuration
```

## Key Technologies

### Core Framework
- **FastAPI**: Modern async web framework with automatic OpenAPI docs
- **Uvicorn**: ASGI server with hot-reload support
- **SQLAlchemy 2.0**: Modern ORM with async support
- **Pydantic v2**: Data validation and settings management
- **Poetry**: Dependency management and packaging

### Data & Storage
- **PostgreSQL**: Primary database for metadata, users, collections
- **Milvus**: Vector database for embeddings and similarity search
- **MinIO**: S3-compatible object storage for documents
- **MLFlow**: Model tracking and experiment management

### AI & ML
- **IBM WatsonX**: Primary LLM provider
- **OpenAI**: Alternative LLM provider (also used for TTS)
- **Anthropic**: Alternative LLM provider
- **Docling**: Advanced document processing
- **Transformers**: HuggingFace models for embeddings
- **OpenAI TTS**: Text-to-speech for podcast generation

### Testing
- **pytest**: Test framework with extensive plugins
- **pytest-cov**: Code coverage reporting (>90% coverage)
- **pytest-asyncio**: Async test support
- **pytest-xdist**: Parallel test execution
- **pytest-mock**: Mocking and fixtures

## Architecture Patterns

### Layered Architecture
The application follows a strict layered architecture:

```
Router Layer (HTTP) → Service Layer (Business Logic) → Repository Layer (Data Access) → Models (ORM)
                                                     ↘ Schemas (Validation) ↙
```

1. **Router Layer** (`router/`)
   - HTTP endpoint definitions
   - Request/response serialization
   - Minimal logic, delegates to services
   - Returns appropriate HTTP status codes

2. **Service Layer** (`services/`)
   - All business logic resides here
   - Orchestrates operations across repositories
   - Implements business rules and validation
   - Uses dependency injection
   - Lazy initialization for dependencies

3. **Repository Layer** (`repository/`)
   - Database CRUD operations
   - Query building and optimization
   - Returns domain models
   - No business logic

4. **Model Layer** (`models/`)
   - SQLAlchemy ORM definitions
   - Database table schemas
   - Relationships and constraints

5. **Schema Layer** (`schemas/`)
   - Pydantic models for validation
   - Request/response DTOs
   - Data transformation

### Dependency Injection

Services use constructor injection for database and settings:

```python
class MyService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        self._dependent_service = None  # Lazy initialization

    @property
    def dependent_service(self) -> DependentService:
        if self._dependent_service is None:
            self._dependent_service = DependentService(self.db, self.settings)
        return self._dependent_service
```

### Error Handling

Custom exceptions defined in `core/custom_exceptions.py`:
- `NotFoundError`: Resource not found (404)
- `ValidationError`: Invalid input (400)
- `LLMProviderError`: LLM provider issues (500)
- `ConfigurationError`: Configuration problems (500)

## Entry Points

### Main Application
- **File**: `main.py`
- **Purpose**: FastAPI app initialization, router registration, middleware setup
- **Key Functions**:
  - `create_app()`: Factory function for app creation
  - Router registration from `rag_solution/router/`
  - CORS middleware configuration
  - Database connection initialization

### CLI Applications
1. **rag-cli** (`rag_solution/cli/main.py`)
   - General-purpose CLI for collections, documents, pipelines
   - Commands: collections, documents, search, providers, pipelines

2. **rag-search** (`rag_solution/cli/search_cli.py`)
   - Specialized search interface
   - Interactive and batch search modes

3. **rag-admin** (`rag_solution/cli/admin_cli.py`)
   - Administrative operations
   - User management, system configuration

## Common Development Tasks

### Running the Application

```bash
# Development mode with hot-reload
make dev-hotreload

# Production mode
make run-ghcr

# Run locally with uvicorn
cd backend
poetry run uvicorn main:app --reload --port 8000
```

### Testing

```bash
# Fast unit tests (no external dependencies)
make test-unit-fast

# Integration tests (requires PostgreSQL, Milvus)
make test-integration

# Specific test file
make test testfile=tests/unit/test_search_service.py

# Run tests with coverage
cd backend
poetry run pytest tests/ -m unit --cov=rag_solution --cov-report=html

# Run tests in parallel
poetry run pytest tests/ -n auto
```

### Code Quality

```bash
# Quick check (format + lint)
make quick-check

# Auto-fix formatting issues
make fix-all

# Run specific linters
cd backend
poetry run ruff check rag_solution/ --line-length 120
poetry run mypy rag_solution/ --ignore-missing-imports
poetry run pylint rag_solution/
poetry run pydocstyle rag_solution/
```

### Database Operations

```bash
# Access PostgreSQL
docker compose exec postgres psql -U raguser -d collectiondb

# Access Milvus CLI
docker compose exec milvus milvus-cli

# View logs
docker compose logs -f backend
```

## Configuration

### Environment Variables

Required variables in `.env`:

```bash
# Database
COLLECTIONDB_HOST=postgres
COLLECTIONDB_PORT=5432
COLLECTIONDB_NAME=collectiondb
COLLECTIONDB_USER=raguser
COLLECTIONDB_PASSWORD=ragpassword

# Vector Database
VECTOR_DB=milvus
MILVUS_HOST=milvus
MILVUS_PORT=19530

# LLM Providers (at least one required)
WATSONX_API_KEY=your_key
WATSONX_PROJECT_ID=your_project
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key

# Authentication
JWT_SECRET_KEY=your_secret_key
OIDC_CLIENT_ID=your_client_id
OIDC_CLIENT_SECRET=your_secret

# Storage
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_ENDPOINT=minio:9000
```

### Settings Management

Configuration loaded via `core/config.py`:
- Environment variables via Pydantic Settings
- Validation on startup
- Type-safe access throughout application

## Important Patterns

### Async/Await
- Use `async def` for I/O-bound operations (database, API calls)
- Use regular `def` for CPU-bound operations
- FastAPI handles async automatically

### Type Hints
- Required throughout codebase
- Use `from typing import TYPE_CHECKING` to avoid circular imports
- Use `|` for union types (Python 3.12+)

### Error Handling Decorator

```python
from core.custom_exceptions import NotFoundError, ValidationError
from fastapi import HTTPException

def handle_errors(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
    return wrapper
```

## Testing Guidelines

### Test Organization
- **Unit Tests** (`tests/unit/`): Test single components in isolation
- **Integration Tests** (`tests/integration/`): Test component interactions
- **API Tests** (`tests/api/`): Test HTTP endpoints
- **Performance Tests** (`tests/performance/`): Benchmark critical paths

### Test Markers
```python
@pytest.mark.unit          # Fast unit test
@pytest.mark.integration   # Integration test (requires services)
@pytest.mark.api           # API endpoint test
@pytest.mark.performance   # Performance benchmark
@pytest.mark.asyncio       # Async test
```

### Fixtures
Common fixtures in `tests/conftest.py`:
- `db_session`: Database session
- `test_client`: FastAPI test client
- `mock_settings`: Mock configuration
- `sample_collection`: Test collection data

## Common Issues & Solutions

### Circular Imports
**Solution**: Use lazy initialization and TYPE_CHECKING

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag_solution.services.other_service import OtherService

class MyService:
    def __init__(self):
        self._other_service: "OtherService | None" = None
```

### Database Session Issues
**Solution**: Always use dependency injection

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from core.database import get_db

@router.get("/items")
async def get_items(db: Session = Depends(get_db)):
    # Use db session
    pass
```

### LLM Provider Errors
**Solution**: Use provider abstraction layer

```python
from rag_solution.generation.providers import get_llm_provider

provider = get_llm_provider(provider_type="watsonx", settings=settings)
response = await provider.generate(prompt=prompt, **params)
```

## Performance Considerations

### Database Optimization
- Use `joinedload()` for eager loading relationships
- Use `selectinload()` for loading collections
- Add indexes on frequently queried columns
- Use pagination for large result sets

### Caching
- Service-level caching for expensive operations
- Redis integration for distributed caching (planned)
- LRU cache for in-memory caching

### Async Operations
- Use async database operations where possible
- Batch operations for bulk processing
- Connection pooling for external services

## Security

### Authentication
- JWT-based authentication
- OIDC integration for enterprise SSO
- Token refresh mechanism

### Authorization
- Role-based access control (RBAC)
- Collection-level permissions
- Team-based collaboration

### Input Validation
- All inputs validated via Pydantic schemas
- SQL injection protection via SQLAlchemy
- XSS protection via FastAPI

## Deployment

### Docker
```bash
# Build backend image
docker build -f Dockerfile.backend -t rag-modulo-backend .

# Run with docker-compose
docker compose up -d backend
```

### Environment-Specific Configs
- **Development**: `docker-compose.dev.yml` (hot-reload)
- **Production**: `docker-compose.yml` (optimized images)
- **Testing**: `docker-compose.test.yml` (CI/CD)

## Documentation References

- **API Docs**: Automatically generated at `/docs` (Swagger UI)
- **ReDoc**: Alternative API docs at `/redoc`
- **Project Docs**: `/docs` directory in repository root
- **Code Comments**: Docstrings following Google style

## Next Steps for New Features

1. **Define Schema** in `rag_solution/schemas/`
2. **Create Model** in `rag_solution/models/` (if database entity)
3. **Implement Repository** in `rag_solution/repository/`
4. **Build Service** in `rag_solution/services/`
5. **Add Router** in `rag_solution/router/`
6. **Write Tests** in `tests/unit/` and `tests/integration/`
7. **Update Documentation** in relevant AGENTS.md files
8. **Run Quality Checks**: `make quick-check && make test-unit-fast`
