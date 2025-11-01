# Pipeline Architecture Overview

## Introduction

The RAG Modulo Search Pipeline Architecture is a modern, modular approach to implementing the search service.
It replaces the monolithic 400+ line `search()` method with a composable pipeline of discrete stages,
each under 100 lines of code.

## Goals

- **Maintainability**: Break complex logic into manageable, testable components
- **Extensibility**: Easy to add new stages or modify existing ones
- **Performance**: Enable stage-level optimization and monitoring
- **Backward Compatibility**: Zero breaking changes to external APIs
- **Gradual Rollout**: Feature flags enable safe, incremental deployment

## Architecture Principles

### 1. **Stage-Based Design**

Each stage represents a discrete step in the search pipeline:

- **PipelineResolutionStage**: Resolve user's default pipeline configuration
- **QueryEnhancementStage**: Enhance and rewrite user queries
- **RetrievalStage**: Retrieve relevant documents from vector database
- **RerankingStage**: Rerank results using cross-encoder models
- **ReasoningStage**: Apply Chain of Thought reasoning (optional)
- **GenerationStage**: Generate final answer using LLM

### 2. **Context Flow**

A `SearchContext` object flows through all stages, accumulating results:

```python
SearchContext:
  - search_input: Original request
  - pipeline_id: Resolved pipeline
  - query_results: Retrieved documents
  - generated_answer: Final answer
  - execution_time: Performance metrics
  - metadata: Stage-specific data
  - errors: Non-fatal errors
```

### 3. **Error Handling**

- **Non-fatal errors**: Logged and accumulated, pipeline continues
- **Fatal errors**: Caught at stage level, pipeline may stop
- **Graceful degradation**: Failed optional stages don't block execution

### 4. **Feature Flags**

Gradual rollout strategy:

```python
# Environment variable
USE_PIPELINE_ARCHITECTURE=true

# Percentage-based rollout
feature_manager.set_rollout_percentage(
    FeatureFlag.USE_PIPELINE_ARCHITECTURE,
    percentage=25  # 25% of users
)
```

## Core Components

### BaseStage (Abstract Class)

```python
class BaseStage(ABC):
    @abstractmethod
    async def execute(self, context: SearchContext) -> StageResult:
        """Execute this pipeline stage."""
        pass
```

Each stage:

- Receives a `SearchContext`
- Performs its specific operation
- Returns a `StageResult` with updated context
- Under 100 lines of code

### SearchContext (Dataclass)

```python
@dataclass
class SearchContext:
    # Input
    search_input: SearchInput
    user_id: UUID4
    collection_id: UUID4

    # Results
    query_results: list[QueryResult]
    generated_answer: str

    # Metadata
    execution_time: float
    metadata: dict[str, Any]
    errors: list[str]
```

### PipelineExecutor

```python
class PipelineExecutor:
    def __init__(self, stages: list[BaseStage]):
        self.stages = stages

    async def execute(self, context: SearchContext) -> SearchContext:
        """Execute all stages in sequence."""
        for stage in self.stages:
            result = await stage.execute(context)
            context = result.context
        return context
```

### FeatureFlagManager

```python
class FeatureFlagManager:
    def is_enabled(
        self,
        flag: FeatureFlag,
        user_id: str | None = None
    ) -> bool:
        """Check if feature is enabled."""
        # Check env vars, explicit flags, and percentage rollout
        pass
```

## Benefits

### Compared to Monolithic Approach

| Aspect | Monolithic | Pipeline |
|--------|-----------|----------|
| Code Size | 400+ lines | <100 lines per stage |
| Testability | Difficult | Easy (isolated stages) |
| Maintainability | Complex | Clear separation |
| Extensibility | Hard | Simple (add new stage) |
| Performance Monitoring | Global | Stage-level granularity |
| Error Handling | Centralized | Stage-specific |
| Onboarding | Slow | Fast (clear structure) |

### Test Coverage

- **100% code coverage** on all pipeline framework components
- **41 unit tests** covering:
  - Stage initialization and execution
  - Context flow and data accumulation
  - Error handling and recovery
  - Feature flag behavior
  - Pipeline orchestration

### Performance Instrumentation

Each stage tracks:

- Execution time
- Success/failure status
- Metadata about operations performed
- Errors encountered

Example metrics:

```json
{
  "pipeline_execution_time": 2.35,
  "stages": {
    "PipelineResolutionStage": {"time": 0.12, "success": true},
    "QueryEnhancementStage": {"time": 0.45, "success": true},
    "RetrievalStage": {"time": 0.78, "success": true},
    "RerankingStage": {"time": 0.52, "success": true},
    "GenerationStage": {"time": 0.48, "success": true}
  }
}
```

## Migration Strategy

### Phase 1: Framework (Week 1) ✅

- Implement `BaseStage` abstract class
- Create `SearchContext` dataclass
- Build `PipelineExecutor`
- Add feature flag system
- Achieve 100% test coverage

### Phase 2: Core Stages (Week 2)

- `PipelineResolutionStage` (wraps existing PipelineService)
- `QueryEnhancementStage` (wraps existing EmbeddingService)
- `RetrievalStage` (wraps existing RetrievalService)
- Test coverage for each stage

### Phase 3: Advanced Stages (Week 3)

- `RerankingStage` (cross-encoder integration)
- `ReasoningStage` (Chain of Thought wrapper)
- `GenerationStage` (LLM generation wrapper)
- Integration tests

### Phase 4: Rollout (Week 4)

- Feature flag implementation in SearchService
- Gradual rollout: 5% → 25% → 50% → 100%
- Equivalence testing between implementations
- Performance monitoring and comparison
- Documentation updates

## External Contracts (Unchanged)

The following interfaces remain **100% unchanged**:

### SearchInput Schema

```python
class SearchInput(BaseModel):
    user_id: UUID4
    collection_id: UUID4
    question: str
    config_metadata: dict[str, Any] | None = None
```

### SearchOutput Schema

```python
class SearchOutput(BaseModel):
    answer: str
    documents: list[DocumentMetadata]
    query_results: list[QueryResult]
    rewritten_query: str | None
    evaluation: dict[str, Any] | None
    execution_time: float
    cot_output: dict[str, Any] | None
    token_warning: TokenWarning | None
    metadata: dict[str, Any]
```

### SearchService Interface

```python
class SearchService:
    async def search(self, search_input: SearchInput) -> SearchOutput:
        """Process a search query through the RAG pipeline."""

        # NEW: Check feature flag
        if feature_flag_manager.is_enabled(
            FeatureFlag.USE_PIPELINE_ARCHITECTURE,
            str(search_input.user_id)
        ):
            # Use new pipeline architecture
            return await self._search_pipeline(search_input)

        # OLD: Use existing monolithic implementation
        return await self._search_monolithic(search_input)
```

## Testing Strategy

### Unit Tests (41 tests, 100% coverage)

```bash
poetry run pytest tests/unit/services/pipeline/ -v \
    --cov=backend/rag_solution/services/pipeline \
    --cov-fail-under=100
```

- `test_base_stage.py`: Stage lifecycle and error handling
- `test_search_context.py`: Context initialization and mutation
- `test_pipeline_executor.py`: Stage orchestration and flow
- `test_feature_flags.py`: Flag management and rollout

### Integration Tests (Week 2-3)

- End-to-end pipeline execution
- Real service integration
- Performance benchmarks
- Equivalence tests (old vs new)

### Regression Tests

- All 947+ existing tests must pass unchanged
- No modifications to test files
- Validates backward compatibility

## Success Criteria

✅ **Code Quality**

- 100% test coverage on new code
- All linting passes (mypy, ruff, pylint, pydocstyle)
- Code follows autopep8 style

✅ **Performance**

- Maintains <15s p95 response time
- No performance regressions

✅ **Compatibility**

- All 947+ existing tests pass unchanged
- Zero breaking changes to external APIs
- SearchInput/SearchOutput schemas unchanged

✅ **Documentation**

- Comprehensive mkdocs documentation
- Migration guide for developers
- Architecture diagrams and examples

## Next Steps

### Week 2: Core Retrieval Pipeline

1. Implement `PipelineResolutionStage`
2. Implement `QueryEnhancementStage`
3. Implement `RetrievalStage`
4. Write stage-specific tests
5. Integration tests for core flow

### Week 3: Advanced Features

1. Implement `RerankingStage`
2. Implement `ReasoningStage`
3. Implement `GenerationStage`
4. Performance optimization
5. End-to-end integration tests

### Week 4: Production Rollout

1. Integrate feature flags into SearchService
2. Gradual rollout with monitoring
3. Equivalence testing and validation
4. Performance comparison and tuning
5. Final documentation and training

## References

- **Issue**: [#549 - Modern RAG Search Architecture](https://github.com/manavgup/rag_modulo/issues/549)
- **Branch**: `feature/issue-549-pipeline-architecture`
- **Timeline**: 4 weeks
- **Status**: Week 1 Complete (Framework)
