# System Components

This document describes the core components and architecture of RAG Modulo, a production-ready Retrieval-Augmented Generation (RAG) platform.

## Overview

RAG Modulo follows a **clean architecture pattern** with clear separation of concerns across multiple layers:

```
Frontend (React/Carbon) ←→ API Gateway ←→ Backend (FastAPI)
                                            ↓
                                      Service Layer
                                            ↓
                                     Repository Layer
                                            ↓
                                    Database (PostgreSQL)
                                    Vector DB (Milvus)
```

## Backend Components

### Service Layer

The service layer contains business logic and orchestrates operations across repositories and external services.

**Location**: `backend/rag_solution/services/`

#### Core Services

**SearchService** (`search_service.py`)
- Orchestrates RAG search pipeline execution
- Implements 6-stage pipeline architecture:
    1. Pipeline Resolution
    2. Query Enhancement
    3. Retrieval
    4. Reranking
    5. Reasoning (Chain of Thought)
    6. Generation
- Manages automatic pipeline resolution for users
- Handles complex question detection and CoT reasoning

```python
class SearchService:
    async def search(self, search_input: SearchInput) -> SearchOutput:
        # Resolve user's default pipeline
        pipeline = await self._resolve_user_default_pipeline(user_id)

        # Execute 6-stage pipeline
        result = await self._search_with_pipeline(search_input, pipeline)

        return result
```

**ChainOfThoughtService** (`chain_of_thought_service.py`)
- Implements advanced reasoning for complex questions
- Decomposes multi-part questions into sub-questions
- Executes iterative reasoning with accumulated context
- Provides conversation-aware context building
- Features production-grade hardening (95% success rate)
- Includes quality scoring and retry logic

**PipelineService** (`pipeline_service.py`)
- Manages RAG pipeline configurations
- Handles pipeline execution and orchestration
- Supports custom pipeline creation per user
- Integrates query rewriting, retrieval, and generation

**CollectionService** (`collection_service.py`)
- Manages document collections
- Handles collection CRUD operations
- Manages user access to collections
- Tracks collection status and metadata

**FileManagementService** (`file_management_service.py`)
- Handles document uploads and storage
- Orchestrates document processing pipeline
- Manages file metadata and status
- Integrates with MinIO for object storage

**LLMProviderService** (`llm_provider_service.py`)
- Manages LLM provider instances
- Handles provider configuration and credentials
- Supports multiple providers (WatsonX, OpenAI, Anthropic)
- Provides provider factory for dynamic instantiation

**TokenTrackingService** (`token_tracking_service.py`)
- Monitors LLM token usage per user
- Enforces token limits and quotas
- Generates token warnings for users
- Tracks usage across all LLM operations

#### Supporting Services

- **QuestionService**: Generates suggested questions for collections
- **EvaluationService**: Evaluates search result quality
- **UserService**: Manages user accounts and authentication
- **TeamService**: Handles team management and permissions
- **ConversationService**: Manages chat history and sessions
- **PodcastService**: Generates AI-powered podcasts from documents

### Repository Layer

The repository layer handles data access using SQLAlchemy ORM.

**Location**: `backend/rag_solution/repository/`

#### Key Repositories

**CollectionRepository** (`collection_repository.py`)
```python
class CollectionRepository:
    def get(self, collection_id: UUID4) -> CollectionOutput:
        collection = (
            self.db.query(Collection)
            .options(joinedload(Collection.users), joinedload(Collection.files))
            .filter(Collection.id == collection_id)
            .first()
        )
        return self._collection_to_output(collection)
```

**Other Repositories:**
- **FileRepository**: Document file management
- **PipelineRepository**: Pipeline configurations
- **UserRepository**: User account data
- **ConversationRepository**: Chat history and sessions
- **LLMProviderRepository**: LLM provider configurations
- **PromptTemplateRepository**: Reusable prompt templates

### Router Layer

The router layer defines API endpoints using FastAPI.

**Location**: `backend/rag_solution/router/`

**Key Routers:**
- **SearchRouter**: `/api/search` - Search and RAG operations
- **CollectionRouter**: `/api/collections` - Collection management
- **FileRouter**: `/api/files` - Document upload and management
- **AuthRouter**: `/api/auth` - Authentication and authorization
- **ConversationRouter**: `/api/conversations` - Chat history
- **PipelineRouter**: `/api/pipelines` - Pipeline configuration
- **PodcastRouter**: `/api/podcasts` - Podcast generation

```python
@router.post("/search", response_model=SearchOutput)
async def search(
    search_input: SearchInput,
    current_user: Annotated[dict, Depends(get_current_user)],
    search_service: Annotated[SearchService, Depends(get_search_service)],
) -> SearchOutput:
    # Extract user_id from JWT token (never trust client input)
    user_id = UUID(current_user.get("uuid"))
    search_input.user_id = user_id

    result = await search_service.search(search_input)
    return result
```

### Model Layer

Database models using SQLAlchemy ORM.

**Location**: `backend/rag_solution/models/`

**Key Models:**

**User Model** (`user.py`)
```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    ibm_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="user")

    # Relationships
    collections: Mapped[list[UserCollection]] = relationship(
        "UserCollection", back_populates="user", cascade="all, delete-orphan"
    )
```

**Other Models:**
- **Collection**: Document collections with metadata
- **File**: Document files with processing status
- **Pipeline**: RAG pipeline configurations
- **LLMProvider**: LLM provider configurations
- **ConversationSession**: Chat sessions
- **ConversationMessage**: Individual chat messages
- **Podcast**: Generated podcast metadata
- **TokenWarning**: User token usage warnings

### Schema Layer

Pydantic schemas for request/response validation.

**Location**: `backend/rag_solution/schemas/`

**Key Schemas:**

**SearchInput** (`search_schema.py`)
```python
class SearchInput(BaseModel):
    question: str
    collection_id: UUID4
    user_id: UUID4
    config_metadata: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")
```

**SearchOutput**
```python
class SearchOutput(BaseModel):
    answer: str
    documents: list[DocumentMetadata]
    query_results: list[QueryResult]
    rewritten_query: str | None = None
    evaluation: dict[str, Any] | None = None
    execution_time: float | None = None
    cot_output: dict[str, Any] | None = None
    token_warning: TokenWarning | None = None
```

## Frontend Components

**Location**: `frontend/src/`

### Component Structure

```
components/
├── search/                    # Search and chat interface
│   ├── LightweightSearchInterface.tsx    # Main chat UI
│   ├── ChainOfThoughtAccordion.tsx       # CoT reasoning display
│   ├── SourcesAccordion.tsx              # Document sources
│   └── TokenAnalysisAccordion.tsx        # Token usage tracking
├── collections/               # Collection management
│   ├── CollectionList.tsx
│   ├── CollectionDetail.tsx
│   └── FileUpload.tsx
├── podcasts/                 # AI podcast generation
│   ├── PodcastGenerator.tsx
│   └── PodcastPlayer.tsx
├── ui/                       # Reusable UI components
│   ├── Button.tsx
│   ├── Input.tsx
│   ├── Modal.tsx
│   ├── Card.tsx
│   └── Select.tsx
└── layout/                   # App layout
    ├── Header.tsx
    ├── Sidebar.tsx
    └── MainLayout.tsx
```

### Key Features

**Search Interface**
- Real-time chat with WebSocket support
- Markdown rendering with syntax highlighting
- Chain of Thought reasoning visualization
- Source attribution with modal views
- Token usage monitoring

**Collection Management**
- File upload with drag-and-drop
- Collection creation and management
- Document processing status tracking
- Suggested questions generation

**Podcast Generation**
- AI-powered podcast creation
- Voice preview and selection
- Audio player with controls
- Podcast sharing capabilities

## Infrastructure Components

### Vector Database

**Supported Databases:**
- **Milvus** (default): High-performance vector search at scale
- **Elasticsearch**: Full-text + vector hybrid search
- **Pinecone**: Managed vector database service
- **Weaviate**: GraphQL-based vector search

**Factory Pattern:**
```python
class VectorStoreFactory:
    def get_datastore(self, datastore: str) -> VectorStore:
        store_class = self._datastore_mapping[datastore]
        return store_class(self.settings)
```

### LLM Providers

**Supported Providers:**
- **WatsonX** (IBM): Enterprise-grade AI platform
- **OpenAI**: GPT-3.5/GPT-4 models
- **Anthropic**: Claude models

**Factory Pattern with Caching:**
```python
class LLMProviderFactory:
    _instances: ClassVar[dict[str, LLMBase]] = {}

    def get_provider(self, provider_name: str, model_id: str) -> LLMBase:
        cache_key = f"{provider_name}:{model_id}"

        if cache_key in self._instances:
            return self._instances[cache_key]

        provider = self._create_provider(provider_name, model_id)
        self._instances[cache_key] = provider
        return provider
```

### Storage Services

**PostgreSQL**
- User accounts and authentication
- Collection metadata
- File metadata and status
- Conversation history
- Pipeline configurations
- LLM provider settings

**MinIO (S3-compatible)**
- Document file storage
- Generated podcast files
- Temporary processing files
- Model artifacts

**Milvus**
- Vector embeddings storage
- Semantic search indexes
- Collection-based isolation
- Efficient similarity search

### Monitoring Services

**MLFlow**
- Model tracking and versioning
- Experiment management
- Performance metrics
- Parameter tuning history

**Structured Logging**
- Request correlation IDs
- Pipeline stage tracking
- Performance profiling
- In-memory queryable logs

## Component Communication

### Service Dependencies

Services use **lazy initialization** for efficient dependency management:

```python
class SearchService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        self._collection_service: CollectionService | None = None

    @property
    def collection_service(self) -> CollectionService:
        if self._collection_service is None:
            self._collection_service = CollectionService(self.db, self.settings)
        return self._collection_service
```

### Dependency Injection

FastAPI provides built-in dependency injection:

```python
def get_search_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
) -> SearchService:
    return SearchService(db, settings)

@router.post("/search")
async def search(
    search_service: Annotated[SearchService, Depends(get_search_service)]
) -> SearchOutput:
    return await search_service.search(search_input)
```

## Testing Architecture

**Test Organization:**
- **Unit Tests**: `tests/unit/` - Services, models, utilities
- **Integration Tests**: `tests/integration/` - Full stack tests
- **API Tests**: `tests/api/` - Router endpoint tests
- **Performance Tests**: `tests/performance/` - Benchmarks

**Test Count**: 947+ automated tests

**Coverage**: 60% minimum requirement

## Related Documentation

- [Data Flow](data-flow.md) - Request processing flow
- [Security](security.md) - Authentication and authorization
- [Scalability](scalability.md) - Scaling strategies
- [Performance](performance.md) - Optimization techniques
