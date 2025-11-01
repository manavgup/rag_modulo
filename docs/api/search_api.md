# Search API

## Overview

The Search API provides an intelligent question-answering system powered by Retrieval-Augmented Generation (RAG). It automatically handles pipeline resolution based on user context, eliminating the need for clients to manage pipeline selection.

## Service Layer Architecture

### Core Services

```python
from rag_solution.services.search_service import SearchService
from rag_solution.services.pipeline_service import PipelineService
from rag_solution.services.llm_provider_service import LLMProviderService

# Initialize services
search_service = SearchService(db, settings)
pipeline_service = PipelineService(db, settings)
provider_service = LLMProviderService(db)
```

### Modern Pipeline Architecture

RAG Modulo uses a modern, stage-based pipeline architecture for all search operations. The pipeline consists of 6 independent stages that execute sequentially:

1. **PipelineResolutionStage** - Resolves user's default pipeline configuration
2. **QueryEnhancementStage** - Enhances/rewrites query for better retrieval
3. **RetrievalStage** - Retrieves relevant documents from vector database
4. **RerankingStage** - Reranks results for improved relevance
5. **ReasoningStage** - Applies Chain of Thought reasoning if beneficial
6. **GenerationStage** - Generates final answer from context

**See:** [Pipeline Architecture Documentation](../architecture/pipeline-architecture.md) for detailed information.

## Simplified Search Input

### Schema Definition

```python
from rag_solution.schemas.search_schema import SearchInput

class SearchInput(BaseModel):
    """Input schema for search requests.

    Defines the structure of search requests to the API.
    Pipeline selection is handled automatically by the backend based on user context.

    Attributes:
        question: The user's query text
        collection_id: UUID4 of the collection to search in
        user_id: UUID4 of the requesting user
        config_metadata: Optional search configuration parameters
    """

    question: str
    collection_id: UUID4
    user_id: UUID4
    config_metadata: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")
```

### Key Changes from Legacy API

**Removed**: `pipeline_id` field - Pipeline selection is now handled automatically by the backend.

**Benefits**:
- Simplified client integration
- Automatic pipeline resolution based on user context
- Reduced client-side complexity
- Better error handling for missing pipelines

## Search Process Flow

### 1. Basic Search Request

```python
from rag_solution.schemas.search_schema import SearchInput

# Create search request
search_input = SearchInput(
    question="What is machine learning?",
    collection_id=collection_uuid,
    user_id=user_uuid,
    config_metadata={
        "max_chunks": 5,
        "temperature": 0.7,
        "top_k": 3
    }
)

# Execute search
result = await search_service.search(search_input)
```

### 2. Automatic Pipeline Resolution

The search service automatically resolves the appropriate pipeline:

```python
class SearchService:
    async def search(self, search_input: SearchInput) -> SearchOutput:
        """Execute search with automatic pipeline resolution."""

        # Validate input
        self._validate_search_input(search_input)

        # Validate user access to collection
        self._validate_collection_access(search_input.user_id, search_input.collection_id)

        # Resolve user's default pipeline (creates one if needed)
        pipeline_id = self._resolve_user_default_pipeline(search_input.user_id)

        # Validate pipeline exists and is accessible
        self._validate_pipeline(pipeline_id)

        # Initialize pipeline for the collection
        collection_name = await self._initialize_pipeline(
            search_input.collection_id, pipeline_id
        )

        # Execute pipeline
        result = await self.pipeline_service.execute_pipeline(
            search_input=search_input,
            collection_name=collection_name,
            pipeline_id=pipeline_id
        )

        # Process and return results
        return self._process_search_results(result, search_input.collection_id)
```

### 3. Pipeline Resolution Logic

```python
def _resolve_user_default_pipeline(self, user_id: UUID4) -> UUID4:
    """Resolve user's default pipeline, creating one if none exists."""

    # Check if user has an existing default pipeline
    default_pipeline = self.pipeline_service.get_default_pipeline(user_id)
    if default_pipeline:
        return default_pipeline.id

    # Create default pipeline for user
    logger.info(f"Creating default pipeline for user {user_id}")

    # Get user's default LLM provider
    default_provider = self.llm_provider_service.get_user_provider(user_id)
    if not default_provider:
        raise ConfigurationError(
            f"No LLM provider available for user {user_id}. "
            "Please configure an LLM provider before searching."
        )

    # Initialize default pipeline
    created_pipeline = self.pipeline_service.initialize_user_pipeline(
        user_id, default_provider.id
    )

    return created_pipeline.id
```

## Search Output

### Response Schema

```python
from rag_solution.schemas.search_schema import SearchOutput

class SearchOutput(BaseModel):
    """Output schema for search responses.

    Defines the structure of search responses from the API.
    This maps directly to what the UI needs to display.

    Attributes:
        answer: Generated answer to the query
        documents: List of document metadata for UI display
        query_results: List of QueryResult with chunks and scores
        rewritten_query: Optional rewritten version of the original query
        evaluation: Optional evaluation metrics and results
        execution_time: Time taken to execute the search
    """

    answer: str
    documents: list[DocumentMetadata]
    query_results: list[QueryResult]
    rewritten_query: str | None = None
    evaluation: dict[str, Any] | None = None
    execution_time: float | None = None
```

### Response Example

```json
{
    "answer": "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed.",
    "documents": [
        {
            "id": "doc-123",
            "filename": "ml-intro.pdf",
            "page_number": 1,
            "chunk_index": 0
        }
    ],
    "query_results": [
        {
            "content": "Machine learning algorithms build mathematical models...",
            "score": 0.92,
            "metadata": {
                "document_id": "doc-123",
                "page": 1
            }
        }
    ],
    "rewritten_query": "What is machine learning definition concepts",
    "evaluation": {
        "relevance_score": 0.89,
        "confidence": 0.91
    },
    "execution_time": 1.234
}
```

## API Endpoints

### Search Endpoint

```python
@router.post("/search", response_model=SearchOutput)
async def search_documents(
    search_input: SearchInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: AppSettings = Depends(get_settings)
) -> SearchOutput:
    """
    Search documents using RAG with automatic pipeline resolution.

    The pipeline is automatically selected based on the user's default configuration.
    If no default pipeline exists, one will be created using the user's default LLM provider.
    """

    # Initialize search service
    search_service = SearchService(db, settings)

    # Execute search
    try:
        result = await search_service.search(search_input)
        return result

    except ConfigurationError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

## Configuration Options

### Search Configuration Metadata

```python
# Example configuration metadata
config_metadata = {
    # Retrieval Configuration
    "max_chunks": 5,                    # Maximum chunks to retrieve
    "similarity_threshold": 0.7,        # Minimum similarity score
    "top_k": 10,                       # Number of candidates to consider
    "reranking_enabled": True,         # Enable result reranking

    # Generation Configuration
    "temperature": 0.7,                # Generation creativity (0.0-1.0)
    "max_new_tokens": 1000,           # Maximum tokens to generate
    "top_p": 0.95,                    # Nucleus sampling parameter
    "repetition_penalty": 1.1,        # Penalty for repetition

    # Processing Configuration
    "evaluation_enabled": True,        # Enable answer evaluation
    "streaming": False,               # Enable streaming response
    "include_metadata": True,         # Include document metadata

    # Performance Configuration
    "timeout_seconds": 30,            # Request timeout
    "cache_enabled": True,            # Enable response caching
    "concurrent_requests": 1          # Concurrent pipeline requests
}
```

## Error Handling

### Exception Types

```python
from core.custom_exceptions import (
    ConfigurationError,
    ValidationError,
    NotFoundError,
    UnauthorizedError
)

# Configuration Errors
ConfigurationError("No LLM provider available for user")
ConfigurationError("Pipeline initialization failed")
ConfigurationError("Invalid search configuration")

# Validation Errors
ValidationError("Invalid question format")
ValidationError("Collection ID not found")
ValidationError("User ID not found")

# Access Errors
UnauthorizedError("User does not have access to collection")
NotFoundError("Collection not found")
NotFoundError("Pipeline not found")
```

### Error Response Format

```json
{
    "detail": "No LLM provider available for user 123e4567-e89b-12d3-a456-426614174000. Please configure an LLM provider before searching.",
    "error_code": "CONFIGURATION_ERROR",
    "timestamp": "2023-12-07T10:30:00Z",
    "request_id": "req-abc123"
}
```

## Performance Considerations

### Automatic Pipeline Creation

- First search for new users triggers pipeline creation
- Pipeline creation includes LLM provider validation
- Default configurations are applied automatically
- Creation is logged for audit purposes

### Caching Strategy

```python
# Response caching based on search input hash
cache_key = generate_cache_key(search_input)
cached_result = await cache.get(cache_key)

if cached_result and cache_enabled:
    return cached_result

# Execute search and cache result
result = await execute_search(search_input)
await cache.set(cache_key, result, ttl=3600)  # 1 hour TTL
```

### Performance Metrics

```python
# Track search performance
search_metrics = {
    "pipeline_resolution_time": 0.05,    # Time to resolve pipeline
    "retrieval_time": 0.8,               # Time to retrieve chunks
    "generation_time": 1.2,              # Time to generate answer
    "total_execution_time": 2.1,         # Total search time
    "cache_hit": False,                  # Whether result was cached
    "chunks_retrieved": 5,               # Number of chunks used
    "tokens_generated": 156              # Tokens in generated answer
}
```

## Migration from Legacy API

### Breaking Changes

1. **Removed `pipeline_id` parameter**: Pipeline selection is now automatic
2. **Schema validation**: Extra fields are now rejected (`extra="forbid"`)
3. **Response format**: Standardized error responses

### Migration Guide

**Before (Legacy)**:
```python
# Client had to manage pipeline selection
pipeline_id = get_user_pipeline(user_id, collection_id)
search_input = SearchInput(
    question="What is ML?",
    collection_id=collection_id,
    user_id=user_id,
    pipeline_id=pipeline_id  # Client-managed
)
```

**After (Current)**:
```python
# Backend handles pipeline selection automatically
search_input = SearchInput(
    question="What is ML?",
    collection_id=collection_id,
    user_id=user_id
    # No pipeline_id needed
)
```

## Testing

### Unit Testing

```bash
# Test search service pipeline resolution
pytest backend/tests/unit/test_search_service_pipeline_resolution.py

# Test search input validation
pytest backend/tests/unit/test_search_schema_validation.py

# Test automatic pipeline creation
pytest backend/tests/unit/test_pipeline_auto_creation.py
```

### Integration Testing

```bash
# Test complete search flow
pytest backend/tests/integration/test_search_integration.py

# Test pipeline resolution with real database
pytest backend/tests/integration/test_pipeline_resolution_integration.py

# Test error handling scenarios
pytest backend/tests/integration/test_search_error_handling.py
```

### API Testing

```bash
# Test search endpoints
pytest backend/tests/api/test_search_endpoints.py

# Test error responses
pytest backend/tests/api/test_search_error_responses.py

# Test authentication and authorization
pytest backend/tests/api/test_search_auth.py
```

## Best Practices

1. **Input Validation**:
   - Always validate search input before processing
   - Use Pydantic schema validation
   - Handle malformed requests gracefully

2. **Pipeline Management**:
   - Let the backend handle pipeline resolution
   - Don't cache pipeline IDs on the client
   - Trust the automatic pipeline creation process

3. **Error Handling**:
   - Catch and handle specific exception types
   - Provide meaningful error messages to users
   - Log errors with sufficient context

4. **Performance**:
   - Use appropriate timeouts for search requests
   - Enable caching for repeated queries
   - Monitor search performance metrics

## Security Considerations

1. **Access Control**:
   - Validate user access to collections
   - Ensure pipeline isolation between users
   - Audit search activities

2. **Input Sanitization**:
   - Validate and sanitize search questions
   - Prevent injection attacks
   - Limit search query length

3. **Rate Limiting**:
   - Implement per-user rate limits
   - Monitor and alert on unusual patterns
   - Protect against abuse

## Future Improvements

1. **Enhanced Pipeline Resolution**:
   - Context-aware pipeline selection
   - Collection-specific pipeline optimization
   - A/B testing for pipeline configurations

2. **Advanced Search Features**:
   - Multi-collection search
   - Streaming responses
   - Real-time search suggestions
   - Search result personalization

3. **Performance Optimizations**:
   - Parallel chunk processing
   - Predictive pipeline warming
   - Intelligent caching strategies
   - Response compression

4. **Analytics and Monitoring**:
   - Search quality metrics
   - User behavior analysis
   - Performance dashboards
   - Automated optimization suggestions
