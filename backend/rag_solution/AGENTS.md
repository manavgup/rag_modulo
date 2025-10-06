# RAG Solution Package - AI Agent Context

## Overview

The `rag_solution` package is the core application package containing all business logic, data models, API endpoints, and supporting infrastructure for the RAG Modulo platform. This package implements the complete RAG pipeline from document ingestion through to AI-powered search and generation.

## Package Structure

```
rag_solution/
├── services/           # Business logic layer (core operations)
├── models/             # SQLAlchemy ORM models (database entities)
├── schemas/            # Pydantic validation schemas (API contracts)
├── router/             # FastAPI endpoint handlers (HTTP layer)
├── repository/         # Data access layer (database queries)
├── generation/         # LLM provider integrations
├── retrieval/          # Vector database operations
├── data_ingestion/     # Document processing & chunking
├── pipeline/           # RAG pipeline orchestration
├── query_rewriting/    # Query enhancement & reformulation
├── file_management/    # File operations & MinIO integration
├── cli/                # Command-line interface
├── utils/              # Utility functions & helpers
├── config/             # Configuration management
├── core/               # Core utilities (config, exceptions, logging)
├── ci_cd/              # CI/CD utilities (health checks)
└── evaluation/         # RAG quality evaluation
```

## Key Responsibilities

### Core RAG Pipeline
The package orchestrates the complete RAG workflow:

1. **Document Ingestion** (`data_ingestion/`)
   - PDF, DOCX, TXT, HTML processing via Docling
   - Hierarchical chunking strategies
   - Metadata extraction
   - Embedding generation

2. **Vector Storage** (`retrieval/`)
   - Multiple vector DB support (Milvus, Elasticsearch, etc.)
   - Similarity search
   - Hybrid search strategies

3. **Query Processing** (`query_rewriting/`)
   - Query enhancement
   - Query expansion
   - Semantic reformulation

4. **Generation** (`generation/`)
   - Multi-LLM provider support
   - Chain of Thought reasoning
   - Source attribution
   - Token tracking

### API Layer
- **HTTP Endpoints** (`router/`): FastAPI routers for all API operations
- **Validation** (`schemas/`): Request/response validation via Pydantic
- **Authentication** (`router/auth_router.py`): JWT & OIDC auth

### Data Layer
- **Models** (`models/`): SQLAlchemy ORM definitions for PostgreSQL
- **Repositories** (`repository/`): Clean data access abstraction
- **File Management** (`file_management/`): MinIO object storage integration

### Business Logic
- **Services** (`services/`): All business logic and orchestration
  - SearchService: RAG search orchestration
  - CollectionService: Collection management
  - ConversationService: Chat & conversation management
  - ChainOfThoughtService: Complex reasoning
  - PipelineService: Pipeline configuration

## Architecture Patterns

### Layered Architecture

```
Router (HTTP) → Service (Business Logic) → Repository (Data Access) → Model (ORM)
                                        ↘ External Services (LLM, Vector DB) ↙
```

**Rules**:
- Routers delegate to services, never call repositories directly
- Services contain ALL business logic
- Repositories handle only data access
- No business logic in models or repositories

### Dependency Injection

All services use constructor injection for database and settings:

```python
class MyService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        # Lazy initialization for dependencies
        self._dependency_service: DependencyService | None = None

    @property
    def dependency_service(self) -> DependencyService:
        """Lazy load to avoid circular imports."""
        if self._dependency_service is None:
            self._dependency_service = DependencyService(self.db, self.settings)
        return self._dependency_service
```

### Error Handling

Custom exceptions in `core/custom_exceptions.py`:
- `NotFoundError`: Resource not found (404)
- `ValidationError`: Invalid input (400)
- `LLMProviderError`: LLM provider issues (500)
- `ConfigurationError`: Configuration problems (500)
- `AuthenticationError`: Auth failures (401)

## Key Entry Points

### Main Application
**File**: `backend/main.py`
- FastAPI app initialization
- Router registration
- Middleware setup (CORS, Auth, Session)
- Database initialization
- LLM provider setup

### Router Registration
Routers are registered in `main.py`:
```python
app.include_router(search_router, prefix="/api/v1/search", tags=["search"])
app.include_router(collection_router, prefix="/api/v1/collections", tags=["collections"])
app.include_router(conversation_router, prefix="/api/v1/conversations", tags=["conversations"])
# ... more routers
```

### CLI Applications
1. **rag-cli** (`cli/main.py`): General-purpose CLI
2. **rag-search** (`cli/search_cli.py`): Search interface
3. **rag-admin** (`cli/admin_cli.py`): Admin operations

## Module Descriptions

### services/
**Purpose**: Business logic implementation
**Key Files**:
- `search_service.py`: RAG search orchestration
- `chain_of_thought_service.py`: CoT reasoning
- `conversation_service.py`: Chat management
- `collection_service.py`: Collection CRUD
- `pipeline_service.py`: Pipeline management
- `llm_provider_service.py`: LLM provider management
- `token_tracking_service.py`: Token usage tracking
- `dashboard_service.py`: Analytics & metrics

**Pattern**: Services orchestrate operations across repositories and external services

### models/
**Purpose**: SQLAlchemy ORM models
**Key Files**:
- `collection.py`: Collection entity
- `file.py`: Document file entity
- `conversation_session.py`: Chat session
- `conversation_message.py`: Chat messages
- `user.py`: User entity
- `pipeline.py`: Pipeline configuration
- `llm_provider.py`: LLM provider config

**Pattern**: Models define database schema with relationships

### schemas/
**Purpose**: Pydantic validation schemas
**Key Files**:
- `search_schema.py`: Search request/response
- `collection_schema.py`: Collection DTOs
- `conversation_schema.py`: Conversation DTOs
- `llm_provider_schema.py`: Provider config DTOs
- `chain_of_thought_schema.py`: CoT reasoning DTOs

**Pattern**: Schemas validate and serialize API data

### router/
**Purpose**: FastAPI HTTP endpoint handlers
**Key Files**:
- `search_router.py`: Search endpoints
- `collection_router.py`: Collection CRUD
- `conversation_router.py`: Conversation management
- `websocket_router.py`: Real-time messaging
- `dashboard_router.py`: Analytics endpoints
- `auth_router.py`: Authentication

**Pattern**: Minimal logic, delegates to services

### repository/
**Purpose**: Data access layer
**Key Files**:
- `collection_repository.py`: Collection queries
- `file_repository.py`: File queries
- `conversation_repository.py`: Conversation queries
- `user_collection_repository.py`: User-collection relations
- `llm_provider_repository.py`: Provider config queries

**Pattern**: Clean data access abstraction

### generation/
**Purpose**: LLM provider integration
**Structure**:
```
generation/
├── providers/          # Provider implementations
│   ├── factory.py      # Provider factory
│   ├── watsonx_provider.py
│   ├── openai_provider.py
│   └── anthropic_provider.py
└── base_generator.py   # Base interface
```

**Pattern**: Common interface for all LLM providers

### retrieval/
**Purpose**: Vector database operations
**Key Files**:
- `factories.py`: Vector DB factory
- `retrieval_augmentation.py`: RAG search logic

**Pattern**: Abstraction over multiple vector databases

### data_ingestion/
**Purpose**: Document processing
**Key Files**:
- `base_processor.py`: Base document processor
- `pdf_processor.py`: PDF processing
- `txt_processor.py`: Text processing
- `chunking.py`: Document chunking
- `hierarchical_chunking.py`: Semantic chunking

**Pattern**: Strategy pattern for different doc types

### pipeline/
**Purpose**: RAG pipeline orchestration
**Key Files**:
- `pipeline_factory.py`: Pipeline creation
- Pipeline configuration management

**Pattern**: Pipeline composition and execution

### query_rewriting/
**Purpose**: Query enhancement
**Key Files**:
- `query_rewriter.py`: Query reformulation

**Pattern**: Query optimization for better retrieval

### file_management/
**Purpose**: File storage integration
**Key Files**:
- `database.py`: Database connection factory
- MinIO integration

**Pattern**: S3-compatible object storage

### cli/
**Purpose**: Command-line interface
**Structure**:
```
cli/
├── main.py             # Main CLI entry point
├── search_cli.py       # Search interface
├── admin_cli.py        # Admin operations
├── commands/           # CLI command modules
│   ├── collections.py
│   ├── documents.py
│   ├── search.py
│   └── ...
└── client.py           # API client for CLI
```

**Pattern**: Click-based CLI with command groups

### utils/
**Purpose**: Utility functions
**Pattern**: Shared helpers across modules

## Common Development Patterns

### Adding a New Feature

1. **Define Schema** (`schemas/`)
   ```python
   from pydantic import BaseModel, UUID4

   class FeatureInput(BaseModel):
       name: str
       config: dict[str, Any]

   class FeatureOutput(BaseModel):
       id: UUID4
       name: str
       status: str
   ```

2. **Create Model** (`models/`) if database entity needed
   ```python
   from sqlalchemy.orm import Mapped, mapped_column

   class Feature(Base):
       __tablename__ = "features"
       id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True)
       name: Mapped[str] = mapped_column(String)
   ```

3. **Implement Repository** (`repository/`)
   ```python
   class FeatureRepository:
       def __init__(self, db: Session):
           self.db = db

       def create(self, feature: Feature) -> Feature:
           self.db.add(feature)
           self.db.commit()
           return feature
   ```

4. **Build Service** (`services/`)
   ```python
   class FeatureService:
       def __init__(self, db: Session, settings: Settings):
           self.db = db
           self.settings = settings
           self._feature_repo = FeatureRepository(db)

       def create_feature(self, input: FeatureInput) -> FeatureOutput:
           # Business logic here
           feature = self._feature_repo.create(...)
           return FeatureOutput.model_validate(feature)
   ```

5. **Add Router** (`router/`)
   ```python
   from fastapi import APIRouter, Depends

   router = APIRouter()

   @router.post("/features", response_model=FeatureOutput)
   async def create_feature(
       input: FeatureInput,
       db: Session = Depends(get_db)
   ):
       service = FeatureService(db, get_settings())
       return service.create_feature(input)
   ```

6. **Write Tests** (`tests/`)
   - Unit tests for service logic
   - Integration tests for database operations
   - API tests for endpoints

### Lazy Initialization for Circular Dependencies

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag_solution.services.other_service import OtherService

class MyService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        self._other_service: "OtherService | None" = None

    @property
    def other_service(self) -> "OtherService":
        if self._other_service is None:
            from rag_solution.services.other_service import OtherService
            self._other_service = OtherService(self.db, self.settings)
        return self._other_service
```

## Important Conventions

### Type Hints
- Required throughout codebase
- Use Python 3.12+ union syntax: `str | None` instead of `Optional[str]`
- Use `from typing import TYPE_CHECKING` for circular imports

### Async/Await
- Use `async def` for I/O-bound operations (database, API calls)
- Use regular `def` for CPU-bound operations
- FastAPI handles async automatically

### Error Handling
```python
from core.custom_exceptions import NotFoundError, ValidationError
from fastapi import HTTPException

try:
    result = service.operation()
except NotFoundError as e:
    raise HTTPException(status_code=404, detail=str(e))
except ValidationError as e:
    raise HTTPException(status_code=400, detail=str(e))
```

### Logging
```python
from core.logging_utils import get_logger

logger = get_logger(__name__)

logger.debug("Debug info")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error occurred: %s", error)
```

## Configuration

### Settings Access
```python
from core.config import get_settings

settings = get_settings()
db_host = settings.collectiondb_host
vector_db = settings.vector_db
```

### Environment Variables
All settings loaded from `.env` via `core/config.py`

## Testing

### Test Structure
```
tests/
├── unit/                   # Fast unit tests
│   ├── test_services/
│   ├── test_repositories/
│   └── ...
├── integration/            # Integration tests
│   ├── test_search_integration.py
│   └── ...
├── api/                    # API endpoint tests
│   ├── test_auth.py
│   └── ...
└── conftest.py            # Shared fixtures
```

### Test Markers
```python
@pytest.mark.unit          # Fast unit test
@pytest.mark.integration   # Integration test
@pytest.mark.api           # API test
```

## Key Features Implemented

### Chain of Thought (CoT) Reasoning
**Location**: `services/chain_of_thought_service.py`
- Automatic complex question detection
- Iterative reasoning with context building
- Source attribution across reasoning steps
- Integration with SearchService

### Automatic Pipeline Resolution
**Location**: `services/search_service.py`
- Automatic pipeline creation for new users
- Intelligent error handling
- Simplified API (no pipeline_id required)

### Conversation System
**Components**:
- Models: `conversation_session.py`, `conversation_message.py`
- Service: `conversation_service.py`
- Router: `conversation_router.py`, `websocket_router.py`
- Features: LLM-based naming, summarization, real-time messaging

### Token Tracking
**Location**: `services/token_tracking_service.py`
- Track token usage per user, collection, and operation
- Cost calculation
- Usage analytics

## Next Steps for Contributors

1. Read this file and understand the package structure
2. Review module-specific AGENTS.md files in subdirectories
3. Follow the layered architecture pattern strictly
4. Write tests for all new features
5. Run `make quick-check` before committing
6. Update relevant AGENTS.md files when adding features

## Documentation

- **API Docs**: Auto-generated at `/docs` (Swagger UI)
- **Module Docs**: AGENTS.md files in each subdirectory
- **Code Docs**: Google-style docstrings throughout
