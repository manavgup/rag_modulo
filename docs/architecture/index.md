# Architecture Overview

RAG Modulo is a production-ready, modular Retrieval-Augmented Generation platform built with clean architecture principles.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│                    Carbon Design System                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST API
┌───────────────────────────┴─────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │  Router    │  │  Service   │  │ Repository │                │
│  │  Layer     │──│   Layer    │──│   Layer    │                │
│  └────────────┘  └────────────┘  └────────────┘                │
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │ Provider   │  │ Pipeline   │  │  Models    │                │
│  │  System    │  │  Engine    │  │  (SQLAlch) │                │
│  └────────────┘  └────────────┘  └────────────┘                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────────┐
│                      Infrastructure                              │
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │ PostgreSQL │  │  Milvus    │  │   MinIO    │                │
│  │ (Metadata) │  │  (Vectors) │  │  (Storage) │                │
│  └────────────┘  └────────────┘  └────────────┘                │
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │  WatsonX   │  │  OpenAI    │  │ Anthropic  │                │
│  │    LLM     │  │    LLM     │  │    LLM     │                │
│  └────────────┘  └────────────┘  └────────────┘                │
└─────────────────────────────────────────────────────────────────┘
```

## Core Layers

### Router Layer
- **Location**: `backend/rag_solution/router/`
- **Purpose**: API endpoints and HTTP handling
- **Key Files**:
  - `search_router.py` - Search endpoints
  - `conversation_router.py` - Conversation management
  - `collection_router.py` - Collection operations
  - `document_router.py` - Document upload/management

### Service Layer
- **Location**: `backend/rag_solution/services/`
- **Purpose**: Business logic and orchestration
- **Key Services**:
  - `SearchService` - RAG search orchestration
  - `ChainOfThoughtService` - CoT reasoning
  - `ConversationService` - Conversation management
  - `DocumentService` - Document processing
  - `PipelineService` - Pipeline resolution

### Repository Layer
- **Location**: `backend/rag_solution/repository/`
- **Purpose**: Data access abstraction
- **Key Repositories**:
  - `ConversationRepository` - Unified conversation data access
  - `CollectionRepository` - Collection operations
  - `DocumentRepository` - Document persistence

### Provider System
- **Location**: `backend/rag_solution/generation/providers/`
- **Purpose**: LLM provider abstraction
- **Providers**:
  - `WatsonXProvider` - IBM WatsonX
  - `OpenAIProvider` - OpenAI GPT models
  - `AnthropicProvider` - Anthropic Claude

## Data Flow

### Document Ingestion

```
User uploads document
    ↓
Router validates file
    ↓
DocumentService processes
    ↓
Docling extracts content
    ↓
Text chunking
    ↓
Embedding generation
    ↓
Milvus stores vectors
    ↓
PostgreSQL stores metadata
```

### Search Query

```
User submits question
    ↓
Router receives request
    ↓
SearchService orchestrates
    ↓
Pipeline resolution
    ↓
Query rewriting (optional)
    ↓
Vector similarity search (Milvus)
    ↓
Reranking (optional)
    ↓
Context building
    ↓
LLM generation (provider)
    ↓
Source attribution
    ↓
Response to user
```

### Chain of Thought Flow

```
Complex question detected
    ↓
QuestionDecomposer breaks into sub-questions
    ↓
For each sub-question:
  ├─ Vector search
  ├─ Context retrieval
  └─ LLM answer generation
    ↓
AnswerSynthesizer combines steps
    ↓
Source attribution across all steps
    ↓
Quality scoring & validation
    ↓
Final comprehensive answer
```

## Key Components

### Pipeline Engine

Automatic pipeline resolution and execution:

1. **Resolution**: Determines user's default pipeline
2. **Creation**: Auto-creates pipelines for new users
3. **Execution**: Runs pipeline stages sequentially
4. **Fallback**: Graceful error handling

Stages:
- Query rewriting
- Retrieval
- Reranking
- Generation

### Chain of Thought Service

Production-hardened reasoning system:

- **5-layer parsing** for leakage prevention
- **Quality scoring** with confidence thresholds
- **Retry logic** with exponential backoff
- **Source attribution** across reasoning steps

See [Chain of Thought](../features/chain-of-thought/index.md) for details.

### Conversation System

Unified repository pattern for session management:

- Session lifecycle management
- Message persistence
- Conversation history
- Summarization support

See [Conversation System Refactoring](conversation-system-refactoring.md) for migration details.

## Technology Stack

### Backend
- **Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Validation**: Pydantic
- **Testing**: pytest (947+ tests)
- **Linting**: Ruff, MyPy, Pylint

### Frontend
- **Framework**: React 18
- **UI Library**: Carbon Design System
- **State Management**: React hooks
- **HTTP Client**: axios

### Infrastructure
- **Database**: PostgreSQL
- **Vector DB**: Milvus (configurable)
- **Object Storage**: MinIO
- **Model Tracking**: MLFlow
- **Containerization**: Docker + Docker Compose

### LLM Providers
- **Default**: IBM WatsonX
- **Alternatives**: OpenAI, Anthropic

## Design Patterns

### Repository Pattern
Abstracts data access with clean interfaces:
```python
class ConversationRepository:
    def create_session(self, input: ConversationSessionInput) -> ConversationSession
    def get_message_by_id(self, message_id: UUID4) -> ConversationMessage
    def create_message(self, input: ConversationMessageInput) -> ConversationMessage
```

### Factory Pattern
Provider instantiation via factory:
```python
provider_factory = ProviderFactory(settings)
provider = provider_factory.get_provider(provider_type)
```

### Service Layer Pattern
Business logic separated from HTTP handling:
```python
@router.post("/search")
async def search(input: SearchInput, service: SearchService = Depends()):
    return await service.search(input)
```

### Dependency Injection
FastAPI dependency injection for testability:
```python
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## Configuration

Environment-based configuration via `.env`:

- **Database**: `COLLECTIONDB_*` variables
- **Vector DB**: `VECTOR_DB`, `MILVUS_*` variables
- **LLM**: `WATSONX_*`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
- **Security**: `JWT_SECRET_KEY`

See [Configuration Guide](../configuration.md) for details.

## Scalability Considerations

### Horizontal Scaling
- Stateless API services
- Database connection pooling
- Distributed vector database (Milvus)

### Performance Optimization
- Async I/O with FastAPI
- Database query optimization
- Vector search indexing (HNSW)
- Response caching

See [Performance](performance.md) and [Scalability](scalability.md) for details.

## Security Architecture

### Authentication & Authorization
- JWT-based authentication
- Role-based access control (future)
- API key management

### Secret Management
- Environment variables for secrets
- Multi-layer secret scanning (Gitleaks, TruffleHog)
- Pre-commit hooks for prevention

### Data Protection
- HTTPS in production
- Database encryption at rest
- Secure file uploads

See [Security](security.md) for comprehensive security documentation.

## Testing Strategy

947+ automated tests across categories:

- **Atomic**: Schema validation (~5s)
- **Unit**: Component isolation (~30s)
- **Integration**: Service interaction (~2 min)
- **E2E**: Full workflows (~5 min)

See [Testing Guide](../testing/index.md) for details.

## Deployment

### Local Development
```bash
make local-dev-setup        # One-time setup
make local-dev-infra        # Start infrastructure
make local-dev-backend      # Start backend
make local-dev-frontend     # Start frontend
```

### Production
```bash
make build-all              # Build Docker images
make prod-start             # Start production stack
```

Images published to GitHub Container Registry (GHCR).

See [Deployment Guide](../deployment/index.md) for details.

## See Also

- [System Design](system-design.md) - Detailed system design
- [Components](components.md) - Component documentation
- [Data Flow](data-flow.md) - Data flow diagrams
- [Security](security.md) - Security architecture
- [Performance](performance.md) - Performance optimization
