# Modern RAG Pipeline Architecture

## Overview

The RAG Modulo search system uses a modern, stage-based pipeline architecture that provides modularity, testability, and maintainability. This architecture has **fully replaced** the previous monolithic search implementation (as of 100% rollout completion).

**Status:** ✅ **Production** (100% rollout completed)

## Architecture Design

### Key Components

```
SearchService.search()
    └─ _search_with_pipeline() [Stage-Based]
        └─ PipelineExecutor
            ├─ Stage 1: PipelineResolutionStage
            ├─ Stage 2: QueryEnhancementStage
            ├─ Stage 3: RetrievalStage
            ├─ Stage 4: RerankingStage
            ├─ Stage 5: ReasoningStage (CoT)
            └─ Stage 6: GenerationStage
```

**Note:** The legacy monolithic implementation and feature flag system have been removed after successful 100% rollout.

## Pipeline Stages

### Stage 1: Pipeline Resolution

**File:** `backend/rag_solution/services/pipeline/stages/pipeline_resolution_stage.py`

**Purpose:** Resolves the user's default pipeline configuration

**Responsibilities:**
- Fetch user's preferred pipeline
- Validate pipeline accessibility
- Initialize collection name

**Output:**
- `context.pipeline_id`: UUID of resolved pipeline
- `context.collection_name`: Vector DB collection name

### Stage 2: Query Enhancement

**File:** `backend/rag_solution/services/pipeline/stages/query_enhancement_stage.py`

**Purpose:** Enhances the user's query for better retrieval

**Responsibilities:**
- Query expansion and rewriting
- Conversation-aware context building
- Synonym expansion

**Output:**
- `context.rewritten_query`: Enhanced query string

### Stage 3: Retrieval

**File:** `backend/rag_solution/services/pipeline/stages/retrieval_stage.py`

**Purpose:** Retrieves relevant documents from vector database

**Responsibilities:**
- Vector similarity search
- Top-k document selection
- Initial relevance filtering

**Input:**
- `context.rewritten_query`
- `context.collection_id`
- `config_metadata.top_k` (optional, default: 10)

**Output:**
- `context.query_results`: List of QueryResult objects

### Stage 4: Reranking

**File:** `backend/rag_solution/services/pipeline/stages/reranking_stage.py`

**Purpose:** Reranks retrieved documents for better relevance

**Responsibilities:**
- Cross-encoder reranking
- LLM-based reranking (optional)
- Score normalization

**Output:**
- `context.query_results`: Reranked list with updated scores

### Stage 5: Reasoning (Chain of Thought)

**File:** `backend/rag_solution/services/pipeline/stages/reasoning_stage.py`

**Purpose:** Applies Chain of Thought reasoning for complex queries

**Responsibilities:**
- Detect if CoT is beneficial
- Execute multi-step reasoning
- Track reasoning steps and confidence

**Output:**
- `context.cot_output`: ChainOfThoughtOutput object (if used)

### Stage 6: Generation

**File:** `backend/rag_solution/services/pipeline/stages/generation_stage.py`

**Purpose:** Generates final answer from retrieved context

**Responsibilities:**
- LLM prompt construction
- Answer generation
- Quality evaluation
- Token tracking

**Output:**
- `context.generated_answer`: Final answer string
- `context.evaluation`: Quality metrics
- `context.token_warning`: Token usage warnings

## Search Context

The `SearchContext` dataclass serves as the single source of truth throughout the pipeline:

```python
@dataclass
class SearchContext:
    # Input
    search_input: SearchInput
    user_id: UUID4
    collection_id: UUID4

    # Pipeline Configuration
    pipeline_id: UUID4 | None = None
    collection_name: str | None = None

    # Retrieval Results
    query_results: list[QueryResult] = field(default_factory=list)
    rewritten_query: str | None = None
    document_metadata: list[DocumentMetadata] = field(default_factory=list)

    # Generation Results
    generated_answer: str = ""
    evaluation: dict[str, Any] | None = None
    cot_output: ChainOfThoughtOutput | None = None
    token_warning: TokenWarning | None = None

    # Execution Metadata
    start_time: float = field(default_factory=time.time)
    execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
```

## Pipeline Executor

The `PipelineExecutor` orchestrates stage execution:

```python
from rag_solution.services.pipeline.pipeline_executor import PipelineExecutor

# Create executor
executor = PipelineExecutor(stages=[])

# Add stages in order
executor.add_stage(PipelineResolutionStage(search_service))
executor.add_stage(QueryEnhancementStage(pipeline_service))
executor.add_stage(RetrievalStage(pipeline_service))
executor.add_stage(RerankingStage(pipeline_service))
executor.add_stage(ReasoningStage(search_service))
executor.add_stage(GenerationStage(pipeline_service))

# Execute pipeline
result_context = await executor.execute(context)
```

**Key Features:**
- Sequential stage execution
- Error accumulation (non-fatal)
- Metadata tracking per stage
- Automatic execution time tracking

## Implementation Details

### SearchService Implementation

**File:** `backend/rag_solution/services/search_service.py`

**Main Method:**

**`search()`** - Entry point for all search requests
```python
@handle_search_errors
async def search(self, search_input: SearchInput) -> SearchOutput:
    """Process a search query using modern pipeline architecture."""
    logger.info("🔍 Processing search query: %s", search_input.question)

    # Validate search input before executing pipeline
    self._validate_search_input(search_input)
    self._validate_collection_access(search_input.collection_id, search_input.user_id)

    return await self._search_with_pipeline(search_input)
```

**`_search_with_pipeline()`** - Stage-based implementation
- Creates SearchContext from input
- Configures PipelineExecutor with all 6 stages
- Executes pipeline sequentially
- Converts context to SearchOutput
- Handles errors gracefully

### Type Conversions

**ChainOfThoughtOutput to dict:**
```python
cot_output_dict = (
    result_context.cot_output.model_dump()
    if result_context.cot_output
    else None
)
```

## Benefits

### 1. Modularity
- Each stage is independent
- Easy to add/remove/modify stages
- Clear separation of concerns

### 2. Testability
- Unit test each stage independently
- Integration test stage combinations
- Mock individual stages easily

### 3. Maintainability
- Changes isolated to specific stages
- Easy to understand data flow
- Self-documenting architecture

### 4. Extensibility
- Add new stages without touching existing code
- Conditional stage execution
- Custom stage implementations

### 5. Monitoring
- Per-stage execution metrics
- Error tracking per stage
- Performance profiling

## Deployment Status

### ✅ Migration Complete (100% Rollout)

The stage-based pipeline architecture has been successfully rolled out to 100% of users:

**Timeline:**
- **Phase 1** (5% rollout): Validation and initial monitoring ✅
- **Phase 2** (25% rollout): Expanded testing and stability confirmation ✅
- **Phase 3** (50% rollout): Production readiness verified ✅
- **Phase 4** (100% rollout): Full migration completed ✅
- **Phase 5** (Cleanup): Legacy code removed ✅

**Current State:**
- ✅ All users using stage-based pipeline
- ✅ Legacy `_search_legacy()` method removed
- ✅ Feature flag system removed (`feature_flags.py` deleted)
- ✅ Documentation updated to reflect production state

## Testing

### Unit Tests

Test individual stages:
```python
@pytest.mark.unit
async def test_retrieval_stage():
    stage = RetrievalStage(mock_pipeline_service)
    context = SearchContext(...)
    result = await stage.execute(context)
    assert result.success
    assert len(result.context.query_results) > 0
```

### Integration Tests

Test full pipeline:
```python
@pytest.mark.integration
async def test_pipeline_execution():
    executor = PipelineExecutor(stages=[...])
    context = SearchContext(...)
    result = await executor.execute(context)
    assert result.generated_answer
    assert result.query_results
```

## Performance Considerations

### Stage Execution Time

Typical execution times:
- Pipeline Resolution: ~10ms
- Query Enhancement: ~50ms
- Retrieval: ~100-200ms (vector DB query)
- Reranking: ~200-500ms (cross-encoder)
- Reasoning (CoT): ~2-5s (if used)
- Generation: ~1-3s (LLM call)

**Total:** 1.5-8.5 seconds (depending on CoT usage)

### Optimization Opportunities

1. **Parallel Stage Execution**
   - Some stages could run in parallel
   - Future enhancement opportunity

2. **Caching**
   - Cache query enhancements
   - Cache reranking results
   - Cache LLM responses

3. **Early Termination**
   - Skip stages based on conditions
   - Example: Skip CoT for simple queries

## Configuration

### Environment Variables

```bash
# Pipeline settings
DEFAULT_TOP_K=10           # Default number of documents to retrieve
ENABLE_RERANKING=true      # Enable cross-encoder reranking
ENABLE_COT=true            # Enable Chain of Thought reasoning

# Vector DB settings
VECTOR_DB=milvus           # Vector database provider
MILVUS_HOST=localhost
MILVUS_PORT=19530

# LLM provider settings
WATSONX_API_KEY=<key>      # WatsonX API key
OPENAI_API_KEY=<key>       # OpenAI API key (optional)
```

### Per-Request Configuration

The `config_metadata` field in `SearchInput` allows fine-grained control:

```python
search_input = SearchInput(
    question="What is machine learning?",
    collection_id=collection_uuid,
    user_id=user_uuid,
    config_metadata={
        # Retrieval Configuration
        "top_k": 20,                    # Override default (10)
        "similarity_threshold": 0.7,    # Minimum similarity score

        # Reranking Configuration
        "reranking_enabled": True,      # Enable/disable reranking
        "max_chunks": 5,                # Max chunks after reranking

        # Chain of Thought Configuration
        "cot_enabled": True,            # Force CoT for this query
        "show_cot_steps": True,         # Include reasoning steps in response
        "max_reasoning_depth": 3,       # Max CoT iterations

        # Generation Configuration
        "temperature": 0.7,             # LLM temperature (0.0-1.0)
        "max_new_tokens": 1000,        # Max tokens to generate
    }
)
```

## Error Handling

### Stage-Level Errors

Stages can fail without stopping the pipeline:
- Error logged and added to `context.errors`
- Pipeline continues to next stage
- Partial results still returned

### Critical Errors

Some errors stop the pipeline:
- Pipeline resolution failure
- Collection access denied
- Database connection failure

### Error Recovery

```python
if result_context.errors:
    logger.warning(
        "Pipeline completed with %d errors: %s",
        len(result_context.errors),
        result_context.errors
    )
```

## Monitoring and Metrics

### Key Metrics to Track

1. **Stage Performance**
   - Execution time per stage
   - Success/failure rates
   - Error types and frequency

2. **Pipeline Performance**
   - End-to-end latency
   - Stage bottlenecks
   - Resource utilization

3. **Business Metrics**
   - Answer quality scores
   - User satisfaction
   - Feature flag adoption

### Logging

Each stage logs:
- Entry/exit points
- Execution time
- Results summary
- Error details

## Troubleshooting

### Common Issues

**Issue:** Pipeline returns empty results
- **Check:** Retrieval stage logs for vector DB queries
- **Solution:**
  - Verify collection has documents indexed
  - Check embedding dimensions match (1536 for WatsonX)
  - Review `query_results` in SearchContext

**Issue:** Slow response times
- **Check:** Per-stage execution times in logs
- **Common bottlenecks:**
  - Retrieval: ~100-200ms (vector DB query)
  - Reranking: ~200-500ms (cross-encoder)
  - Reasoning: ~2-5s (CoT if enabled)
  - Generation: ~1-3s (LLM call)
- **Solution:**
  - Reduce `top_k` for faster retrieval
  - Disable reranking for simple queries
  - Skip CoT for straightforward questions

**Issue:** Validation errors on search input
- **Check:** `SearchInput` schema validation
- **Common causes:**
  - Invalid `collection_id` (not UUID4)
  - Missing required fields (`question`, `user_id`)
  - Extra fields in request (schema uses `extra="forbid"`)
- **Solution:** Validate input schema before calling search

**Issue:** Pipeline resolution fails
- **Check:** User has default pipeline configured
- **Solution:**
  - System auto-creates pipeline on first search
  - Verify user has LLM provider configured
  - Check `initialize_user_pipeline()` logs

## Future Enhancements

### Planned Improvements

1. **Parallel Stage Execution**
   - Run independent stages concurrently
   - Reduce total latency

2. **Dynamic Stage Selection**
   - Enable/disable stages based on query type
   - Optimize for simple queries

3. **A/B Testing Framework**
   - Test different stage configurations
   - Compare performance metrics

4. **Stage Marketplace**
   - Plugin system for custom stages
   - Community-contributed stages

## References

- [Issue #549: Modern RAG Search Architecture](https://github.com/manavgup/rag_modulo/issues/549)
- [PR #551: Pipeline Architecture Implementation](https://github.com/manavgup/rag_modulo/pull/551)
- [Testing Guide](../testing/index.md)
- [Search API Documentation](../api/search_api.md)
- [Stage Implementation Guide](../development/pipeline-architecture/)

## Related Documentation

- [Chain of Thought Integration](../features/chain-of-thought/index.md)
- [Pipeline Service API](../api/service_configuration.md)
- [SearchContext Schema](../api/search_schemas.md)
