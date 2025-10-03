# Services Layer - AI Agent Context

## Overview

The services layer contains ALL business logic for the RAG Modulo platform. Services orchestrate operations across repositories, external services (LLM providers, vector databases), and implement complex workflows. This is the core of the application's functionality.

## Architectural Principles

### Single Responsibility
Each service has a clear, focused purpose:
- **SearchService**: RAG search orchestration
- **CollectionService**: Collection lifecycle management
- **ConversationService**: Chat and conversation operations
- **ChainOfThoughtService**: Complex reasoning workflows

### Dependency Injection
All services follow this pattern:

```python
class MyService:
    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        # Lazy initialization for dependencies
        self._dependency: DependencyService | None = None

    @property
    def dependency(self) -> DependencyService:
        """Lazy load to avoid circular imports."""
        if self._dependency is None:
            self._dependency = DependencyService(self.db, self.settings)
        return self._dependency
```

### No Direct Repository Creation
Services should use lazy properties for repositories:

```python
@property
def collection_repo(self) -> CollectionRepository:
    if self._collection_repo is None:
        self._collection_repo = CollectionRepository(self.db)
    return self._collection_repo
```

## Service Categories

### Core RAG Services

#### SearchService (`search_service.py`)
**Purpose**: Orchestrates the complete RAG search pipeline

**Key Methods**:
- `search(input: SearchInput) -> SearchOutput`: Main search orchestration
- `_resolve_user_default_pipeline()`: Automatic pipeline resolution
- `_should_use_chain_of_thought()`: CoT decision logic
- `_search_with_cot()`: Chain of Thought search path
- `_search_standard()`: Standard RAG search path

**Dependencies**:
- FileManagementService
- CollectionService
- PipelineService
- LLMProviderService
- ChainOfThoughtService (lazy)
- TokenTrackingService

**Features**:
- Automatic pipeline creation for new users
- Chain of Thought reasoning for complex questions
- Token usage tracking
- Source attribution
- Error handling with fallbacks

**Usage Example**:
```python
search_service = SearchService(db, settings)
result = await search_service.search(
    SearchInput(
        question="What is RAG?",
        collection_id=collection_id,
        user_id=user_id
    )
)
```

#### ChainOfThoughtService (`chain_of_thought_service.py`)
**Purpose**: Implements iterative reasoning for complex questions

**Key Methods**:
- `execute_chain_of_thought()`: Main CoT execution
- `_should_use_cot()`: Determine if CoT is beneficial
- `_execute_reasoning_steps()`: Iterative reasoning loop
- `_synthesize_final_answer()`: Combine reasoning steps

**Components**:
- QuestionDecomposer: Breaks complex questions into sub-questions
- AnswerSynthesizer: Combines answers from reasoning steps
- SourceAttributionService: Tracks sources across steps

**Features**:
- Automatic question complexity detection
- Conversation-aware context building
- Iterative reasoning with context accumulation
- Source attribution across all steps
- Fallback to standard search if CoT fails

**Usage Example**:
```python
cot_service = ChainOfThoughtService(db, settings)
result = await cot_service.execute_chain_of_thought(
    input=ChainOfThoughtInput(
        question="How does X work and what are its implications?",
        collection_id=collection_id,
        ...
    )
)
```

### Collection Management Services

#### CollectionService (`collection_service.py`)
**Purpose**: Collection lifecycle management

**Key Methods**:
- `create_collection()`: Create new collection
- `get_collection()`: Retrieve collection by ID
- `update_collection()`: Update collection metadata
- `delete_collection()`: Delete collection and associated data
- `list_collections()`: List user's collections
- `get_collection_files()`: Get files in collection

**Features**:
- Collection status management (CREATED, PROCESSING, COMPLETED, FAILED)
- User permissions validation
- Vector database integration
- File association management

#### FileManagementService (`file_management_service.py`)
**Purpose**: Document and file operations

**Key Methods**:
- `upload_file()`: Upload document to collection
- `download_file()`: Retrieve document
- `delete_file()`: Remove document
- `get_file_metadata()`: Get file information
- `process_document()`: Trigger document processing

**Features**:
- MinIO object storage integration
- Document format validation
- Processing status tracking
- Batch upload support

### Conversation Services

#### ConversationService (`conversation_service.py`)
**Purpose**: Chat and conversation management

**Key Methods**:
- `create_session()`: Create new conversation session
- `get_session()`: Retrieve conversation
- `add_message()`: Add message to conversation
- `get_messages()`: Retrieve conversation history
- `generate_conversation_name()`: LLM-based naming
- `update_conversation_names()`: Bulk naming update
- `summarize_conversation()`: Generate conversation summary

**Features**:
- Session management with persistence
- LLM-generated conversation titles
- Conversation summarization
- Message history tracking
- User permissions

**Usage Example**:
```python
conv_service = ConversationService(db, settings)
session = conv_service.create_session(
    user_id=user_id,
    collection_id=collection_id
)
conv_service.add_message(
    session_id=session.id,
    role="user",
    content="What is RAG?"
)
```

#### ConversationSummarizationService (`conversation_summarization_service.py`)
**Purpose**: Generate conversation summaries

**Key Methods**:
- `summarize_conversation()`: Create conversation summary
- `update_summary()`: Update existing summary

**Features**:
- LLM-based summarization
- Configurable summary length
- Summary caching

### LLM Provider Services

#### LLMProviderService (`llm_provider_service.py`)
**Purpose**: Manage LLM provider configurations

**Key Methods**:
- `get_provider()`: Get provider instance
- `list_providers()`: List available providers
- `create_provider_config()`: Add provider configuration
- `update_provider_config()`: Update provider settings
- `delete_provider_config()`: Remove provider

**Supported Providers**:
- WatsonX (IBM)
- OpenAI
- Anthropic

#### LLMModelService (`llm_model_service.py`)
**Purpose**: Manage LLM model configurations

**Key Methods**:
- `get_model()`: Get model configuration
- `list_models()`: List available models
- `create_model()`: Add model configuration
- `update_model()`: Update model settings

### Pipeline Services

#### PipelineService (`pipeline_service.py`)
**Purpose**: RAG pipeline configuration and management

**Key Methods**:
- `create_pipeline()`: Create pipeline configuration
- `get_pipeline()`: Retrieve pipeline
- `update_pipeline()`: Update pipeline settings
- `delete_pipeline()`: Remove pipeline
- `get_user_default_pipeline()`: Get user's default pipeline
- `create_default_pipeline()`: Create default for new users

**Features**:
- Pipeline component configuration
- Embedding model selection
- Chunking strategy configuration
- Retrieval parameter tuning

### Analytics Services

#### DashboardService (`dashboard_service.py`)
**Purpose**: System analytics and metrics

**Key Methods**:
- `get_dashboard_stats()`: Get system-wide statistics
- `get_recent_activity()`: Get recent user activity
- `get_collection_analytics()`: Collection-specific metrics
- `get_user_analytics()`: User-specific metrics

**Metrics Provided**:
- Total collections, users, documents, searches
- Storage usage
- Processing status
- Recent activity timeline

#### TokenTrackingService (`token_tracking_service.py`)
**Purpose**: Track LLM token usage and costs

**Key Methods**:
- `track_usage()`: Record token usage
- `get_usage_stats()`: Get usage statistics
- `calculate_cost()`: Calculate token costs
- `check_token_limits()`: Validate usage limits

**Features**:
- Per-operation tracking
- User-level aggregation
- Collection-level aggregation
- Cost calculation

### User Management Services

#### UserService (`user_service.py`)
**Purpose**: User account management

**Key Methods**:
- `create_user()`: Create new user
- `get_user()`: Retrieve user by ID
- `update_user()`: Update user profile
- `delete_user()`: Remove user account
- `authenticate_user()`: Validate credentials

#### UserCollectionService (`user_collection_service.py`)
**Purpose**: Manage user-collection relationships

**Key Methods**:
- `add_user_to_collection()`: Grant collection access
- `remove_user_from_collection()`: Revoke access
- `get_user_collections()`: List user's collections
- `get_collection_users()`: List collection members

#### TeamService (`team_service.py`)
**Purpose**: Team collaboration management

**Key Methods**:
- `create_team()`: Create new team
- `add_member()`: Add team member
- `remove_member()`: Remove team member
- `list_teams()`: List user's teams

### Supporting Services

#### SystemInitializationService (`system_initialization_service.py`)
**Purpose**: Application startup initialization

**Key Methods**:
- `initialize_providers()`: Setup LLM providers
- `verify_database()`: Check database connectivity
- `setup_default_configs()`: Create default configurations

#### QuestionService (`question_service.py`)
**Purpose**: Suggested question management

**Key Methods**:
- `generate_questions()`: Auto-generate suggested questions
- `get_questions()`: Retrieve questions for collection
- `add_question()`: Add custom question

#### PodcastService (`podcast_service.py`)
**Purpose**: Generate podcasts from documents

**Key Methods**:
- `generate_podcast()`: Create podcast from collection
- `get_podcast()`: Retrieve podcast
- `list_podcasts()`: List collection podcasts

## Common Service Patterns

### Error Handling

```python
from core.custom_exceptions import NotFoundError, ValidationError

class MyService:
    def operation(self, id: UUID4) -> Result:
        entity = self.repository.get(id)
        if not entity:
            raise NotFoundError(f"Entity {id} not found")

        if not self._validate(entity):
            raise ValidationError("Invalid entity state")

        return self._process(entity)
```

### Transaction Management

```python
def update_with_transaction(self, id: UUID4, data: dict) -> Entity:
    try:
        entity = self.repository.get(id)
        entity.update(data)
        self.db.commit()
        return entity
    except Exception as e:
        self.db.rollback()
        raise
```

### Async Operations

```python
async def async_operation(self, input: Input) -> Output:
    # Use async for I/O operations
    result = await self.external_service.call(input)
    # Process result
    return self._transform(result)
```

## Testing Services

### Unit Testing
```python
@pytest.mark.unit
def test_service_operation(db_session, mock_settings):
    service = MyService(db_session, mock_settings)
    result = service.operation(input_data)
    assert result.status == "success"
```

### Integration Testing
```python
@pytest.mark.integration
async def test_service_with_dependencies(db_session, settings):
    service = MyService(db_session, settings)
    result = await service.complex_operation(input_data)
    # Verify database state
    assert db_session.query(Entity).count() == 1
```

### Mocking Dependencies
```python
from unittest.mock import Mock, patch

def test_with_mocked_llm(db_session, settings):
    with patch('rag_solution.services.llm_provider_service.LLMProviderService') as mock_llm:
        mock_llm.return_value.generate.return_value = "mocked response"
        service = MyService(db_session, settings)
        result = service.operation_using_llm()
        assert "mocked response" in result
```

## Best Practices

### 1. Keep Services Focused
- One service = one domain responsibility
- Don't create "utility" or "helper" services
- Split large services into smaller, focused ones

### 2. Use Lazy Initialization
- Avoid circular dependencies
- Improve startup performance
- Load dependencies only when needed

### 3. Validate Inputs Early
```python
def create(self, input: CreateInput) -> Entity:
    # Validate first
    self._validate_input(input)

    # Then proceed
    return self.repository.create(input)
```

### 4. Handle Errors Consistently
- Use custom exceptions from `core/custom_exceptions.py`
- Provide meaningful error messages
- Log errors with context

### 5. Document Public Methods
```python
def operation(self, param: str) -> Result:
    """
    Perform operation on parameter.

    Args:
        param: Input parameter description

    Returns:
        Result object with operation outcome

    Raises:
        NotFoundError: If parameter not found
        ValidationError: If parameter invalid
    """
    ...
```

### 6. Use Type Hints
```python
def typed_method(
    self,
    required: str,
    optional: str | None = None,
    collection: list[str] | None = None
) -> tuple[str, int]:
    ...
```

## Common Pitfalls to Avoid

### ❌ Don't Access Database Directly in Services
```python
# BAD
result = self.db.query(Entity).filter(Entity.id == id).first()

# GOOD
result = self.repository.get(id)
```

### ❌ Don't Put Business Logic in Repositories
```python
# BAD - in repository
def get_active_collections(self):
    collections = self.db.query(Collection).all()
    return [c for c in collections if c.status == "active" and c.file_count > 0]

# GOOD - in service
def get_active_collections(self):
    collections = self.repository.get_all()
    return self._filter_active(collections)
```

### ❌ Don't Create Service Instances in Routers
```python
# BAD
@router.get("/items")
def get_items(db: Session = Depends(get_db)):
    service = MyService(db, get_settings())
    return service.get_items()

# GOOD
def get_service(db: Session = Depends(get_db)) -> MyService:
    return MyService(db, get_settings())

@router.get("/items")
def get_items(service: MyService = Depends(get_service)):
    return service.get_items()
```

## Adding a New Service

1. **Create service file** in `services/`
2. **Define class** with `__init__(db, settings)`
3. **Add lazy properties** for dependencies
4. **Implement methods** with proper error handling
5. **Write docstrings** for public methods
6. **Add type hints** throughout
7. **Create tests** in `tests/unit/test_services/`
8. **Update this file** with service description

## Related Documentation

- Repository Layer: `../repository/AGENTS.md`
- Router Layer: `../router/AGENTS.md`
- Models: `../models/AGENTS.md`
- Schemas: `../schemas/AGENTS.md`
