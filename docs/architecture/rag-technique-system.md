# RAG Technique System Architecture

## Overview

This document describes the architecture for dynamically selecting and composing RAG techniques at runtime in the RAG Modulo system. The design enables users to configure which retrieval augmentation techniques to apply on a per-query basis without code changes.

## Design Goals

1. **Dynamic Selection**: Users select techniques via API configuration (no code changes)
2. **Composability**: Techniques can be chained and combined
3. **Extensibility**: New techniques can be added without modifying core system
4. **Type Safety**: Strong typing with Pydantic schemas
5. **Observability**: Track which techniques are applied and their impact
6. **Performance**: Minimal overhead for technique orchestration
7. **Backward Compatibility**: Existing API continues to work
8. **Validation**: Ensure technique combinations are valid

## Core Design Patterns

### 1. Strategy Pattern
Each technique is a strategy that can be applied to different pipeline stages.

### 2. Chain of Responsibility
Techniques form a chain where each can transform the data before passing to the next.

### 3. Pipeline Pattern
Configurable pipeline of techniques executed in sequence.

### 4. Registry Pattern
Central registry for discovering and instantiating techniques.

### 5. Builder Pattern
Fluent API for constructing technique pipelines.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (SearchInput)                  │
│  {techniques: ["hyde", "fusion_retrieval", "reranking"]}    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   Technique Orchestrator                     │
│  • Validates technique configuration                         │
│  • Builds technique pipeline from config                     │
│  • Executes pipeline with error handling                     │
│  • Tracks metrics and performance                            │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Technique Registry                        │
│  • Discovers available techniques                            │
│  • Provides technique metadata (stage, dependencies)         │
│  • Factory for instantiating techniques                      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  Technique Implementations                   │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Query      │  │  Retrieval   │  │ Post-        │     │
│  │   Transform  │  │  Techniques  │  │ Processing   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  • HyDE           • Fusion         • Reranking             │
│  • Query Rewrite  • Semantic       • Compression           │
│  • Step-back      • Adaptive       • Filtering             │
│  • Decomposition  • Multi-faceted  • Synthesis             │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Technique Interface

All techniques implement a common interface:

```python
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Generic, TypeVar

class TechniqueStage(Enum):
    """Pipeline stages where techniques can be applied."""
    QUERY_PREPROCESSING = "query_preprocessing"      # Before retrieval
    QUERY_TRANSFORMATION = "query_transformation"    # Query enhancement
    RETRIEVAL = "retrieval"                          # Document retrieval
    POST_RETRIEVAL = "post_retrieval"                # After retrieval
    RERANKING = "reranking"                          # Result reordering
    COMPRESSION = "compression"                      # Context compression
    GENERATION = "generation"                        # Answer generation

InputT = TypeVar('InputT')
OutputT = TypeVar('OutputT')

class BaseTechnique(ABC, Generic[InputT, OutputT]):
    """Abstract base class for all RAG techniques."""

    # Metadata
    technique_id: str
    name: str
    description: str
    stage: TechniqueStage

    # Dependencies
    requires_llm: bool = False
    requires_embeddings: bool = False

    # Performance characteristics
    estimated_latency_ms: int = 0
    token_cost_multiplier: float = 1.0

    @abstractmethod
    async def execute(
        self,
        input_data: InputT,
        context: TechniqueContext
    ) -> TechniqueResult[OutputT]:
        """Execute the technique."""
        pass

    @abstractmethod
    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate technique-specific configuration."""
        pass

    def get_metadata(self) -> TechniqueMetadata:
        """Return technique metadata."""
        return TechniqueMetadata(
            technique_id=self.technique_id,
            name=self.name,
            description=self.description,
            stage=self.stage,
            requires_llm=self.requires_llm,
            requires_embeddings=self.requires_embeddings,
            estimated_latency_ms=self.estimated_latency_ms,
            token_cost_multiplier=self.token_cost_multiplier
        )
```

### 2. Technique Context

Context object passed through the pipeline:

```python
@dataclass
class TechniqueContext:
    """Context shared across technique pipeline."""

    # Request context
    user_id: UUID4
    collection_id: UUID4
    original_query: str

    # Services (dependency injection)
    llm_provider: LLMBase | None = None
    vector_store: Any | None = None
    db_session: Session | None = None

    # Pipeline state
    current_query: str = ""  # May be transformed
    retrieved_documents: list[QueryResult] = field(default_factory=list)
    intermediate_results: dict[str, Any] = field(default_factory=dict)

    # Metrics
    metrics: dict[str, Any] = field(default_factory=dict)
    execution_trace: list[str] = field(default_factory=list)

    # Configuration
    config: dict[str, Any] = field(default_factory=dict)
```

### 3. Technique Result

Standardized result format:

```python
@dataclass
class TechniqueResult(Generic[T]):
    """Result from technique execution."""

    success: bool
    output: T
    metadata: dict[str, Any]

    # Metrics
    execution_time_ms: float
    tokens_used: int = 0

    # Observability
    technique_id: str
    trace_info: dict[str, Any] = field(default_factory=dict)

    # Error handling
    error: str | None = None
    fallback_used: bool = False
```

### 4. Technique Registry

Central registry for technique discovery:

```python
class TechniqueRegistry:
    """Registry for discovering and instantiating techniques."""

    def __init__(self):
        self._techniques: dict[str, type[BaseTechnique]] = {}
        self._metadata_cache: dict[str, TechniqueMetadata] = {}

    def register(
        self,
        technique_id: str,
        technique_class: type[BaseTechnique]
    ) -> None:
        """Register a technique."""
        self._techniques[technique_id] = technique_class
        # Cache metadata
        instance = technique_class()
        self._metadata_cache[technique_id] = instance.get_metadata()

    def get_technique(
        self,
        technique_id: str,
        **kwargs
    ) -> BaseTechnique:
        """Instantiate a technique by ID."""
        if technique_id not in self._techniques:
            raise ValueError(f"Unknown technique: {technique_id}")
        return self._techniques[technique_id](**kwargs)

    def list_techniques(
        self,
        stage: TechniqueStage | None = None
    ) -> list[TechniqueMetadata]:
        """List available techniques, optionally filtered by stage."""
        if stage is None:
            return list(self._metadata_cache.values())
        return [
            meta for meta in self._metadata_cache.values()
            if meta.stage == stage
        ]

    def validate_pipeline(
        self,
        technique_ids: list[str]
    ) -> tuple[bool, str | None]:
        """Validate a technique pipeline configuration."""
        # Check all techniques exist
        for tid in technique_ids:
            if tid not in self._techniques:
                return False, f"Unknown technique: {tid}"

        # Check stage ordering is valid
        stages = [
            self._metadata_cache[tid].stage
            for tid in technique_ids
        ]
        # Ensure stages are in valid order (preprocessing -> retrieval -> post)

        return True, None

# Global registry instance
technique_registry = TechniqueRegistry()
```

### 5. Pipeline Builder

Fluent API for constructing pipelines:

```python
class TechniquePipelineBuilder:
    """Builder for constructing technique pipelines."""

    def __init__(self, registry: TechniqueRegistry):
        self.registry = registry
        self.techniques: list[tuple[str, dict[str, Any]]] = []

    def add_technique(
        self,
        technique_id: str,
        config: dict[str, Any] | None = None
    ) -> "TechniquePipelineBuilder":
        """Add a technique to the pipeline."""
        self.techniques.append((technique_id, config or {}))
        return self

    def add_query_transformation(
        self,
        method: str = "rewrite"
    ) -> "TechniquePipelineBuilder":
        """Convenience method for query transformation."""
        return self.add_technique("query_transformation", {"method": method})

    def add_hyde(self) -> "TechniquePipelineBuilder":
        """Convenience method for HyDE."""
        return self.add_technique("hyde")

    def add_fusion_retrieval(
        self,
        vector_weight: float = 0.7
    ) -> "TechniquePipelineBuilder":
        """Convenience method for fusion retrieval."""
        return self.add_technique(
            "fusion_retrieval",
            {"vector_weight": vector_weight}
        )

    def add_reranking(
        self,
        top_k: int = 10
    ) -> "TechniquePipelineBuilder":
        """Convenience method for reranking."""
        return self.add_technique("reranking", {"top_k": top_k})

    def add_contextual_compression(self) -> "TechniquePipelineBuilder":
        """Convenience method for contextual compression."""
        return self.add_technique("contextual_compression")

    def validate(self) -> tuple[bool, str | None]:
        """Validate the pipeline configuration."""
        technique_ids = [tid for tid, _ in self.techniques]
        return self.registry.validate_pipeline(technique_ids)

    def build(self) -> "TechniquePipeline":
        """Build the pipeline."""
        is_valid, error = self.validate()
        if not is_valid:
            raise ValueError(f"Invalid pipeline: {error}")

        # Instantiate techniques
        instances = []
        for technique_id, config in self.techniques:
            technique = self.registry.get_technique(technique_id)
            if not technique.validate_config(config):
                raise ValueError(
                    f"Invalid config for {technique_id}: {config}"
                )
            instances.append((technique, config))

        return TechniquePipeline(instances)
```

### 6. Pipeline Executor

Executes the technique pipeline:

```python
class TechniquePipeline:
    """Executable pipeline of RAG techniques."""

    def __init__(
        self,
        techniques: list[tuple[BaseTechnique, dict[str, Any]]]
    ):
        self.techniques = techniques
        self.metrics: dict[str, Any] = {}

    async def execute(
        self,
        context: TechniqueContext
    ) -> TechniqueContext:
        """Execute all techniques in sequence."""

        for technique, config in self.techniques:
            try:
                # Update context with technique config
                context.config.update(config)

                # Log execution
                context.execution_trace.append(
                    f"Executing: {technique.technique_id}"
                )

                # Execute technique
                start_time = time.time()
                result = await technique.execute(context, config)
                execution_time = (time.time() - start_time) * 1000

                # Track metrics
                self.metrics[technique.technique_id] = {
                    "execution_time_ms": execution_time,
                    "tokens_used": result.tokens_used,
                    "success": result.success,
                    "fallback_used": result.fallback_used
                }

                # Update context with result
                if result.success:
                    context.intermediate_results[technique.technique_id] = result.output
                else:
                    logger.warning(
                        f"Technique {technique.technique_id} failed: {result.error}"
                    )
                    # Continue pipeline execution (techniques should be resilient)

            except Exception as e:
                logger.error(
                    f"Error executing technique {technique.technique_id}: {e}"
                )
                # Record error but continue pipeline
                self.metrics[technique.technique_id] = {
                    "execution_time_ms": 0,
                    "success": False,
                    "error": str(e)
                }

        # Add pipeline metrics to context
        context.metrics["pipeline_metrics"] = self.metrics

        return context

    def get_estimated_cost(self) -> dict[str, Any]:
        """Estimate pipeline execution cost."""
        total_latency = sum(
            t.estimated_latency_ms for t, _ in self.techniques
        )
        total_token_multiplier = sum(
            t.token_cost_multiplier for t, _ in self.techniques
        )

        return {
            "estimated_latency_ms": total_latency,
            "token_cost_multiplier": total_token_multiplier,
            "technique_count": len(self.techniques)
        }
```

## Configuration Schema

### API Request Format

```python
class TechniqueConfig(BaseModel):
    """Configuration for a single technique."""
    technique_id: str
    enabled: bool = True
    config: dict[str, Any] = {}

class SearchInput(BaseModel):
    """Enhanced search input with technique selection."""
    question: str
    collection_id: UUID4
    user_id: UUID4

    # Technique configuration
    techniques: list[TechniqueConfig] | None = None

    # Shorthand for common presets
    technique_preset: str | None = None  # "default", "fast", "accurate", "cost_optimized"

    # Legacy config_metadata (backward compatible)
    config_metadata: dict[str, Any] | None = None
```

### Technique Presets

Pre-configured technique combinations:

```python
TECHNIQUE_PRESETS = {
    "default": [
        TechniqueConfig(technique_id="vector_retrieval"),
        TechniqueConfig(technique_id="reranking", config={"top_k": 10})
    ],
    "fast": [
        TechniqueConfig(technique_id="vector_retrieval"),
    ],
    "accurate": [
        TechniqueConfig(technique_id="query_transformation", config={"method": "rewrite"}),
        TechniqueConfig(technique_id="hyde"),
        TechniqueConfig(technique_id="fusion_retrieval"),
        TechniqueConfig(technique_id="reranking", config={"top_k": 20}),
        TechniqueConfig(technique_id="contextual_compression")
    ],
    "cost_optimized": [
        TechniqueConfig(technique_id="semantic_chunking"),
        TechniqueConfig(technique_id="vector_retrieval"),
        TechniqueConfig(technique_id="multi_faceted_filtering", config={
            "min_similarity": 0.7,
            "ensure_diversity": True
        })
    ]
}
```

## Usage Examples

### 1. Simple Query with HyDE

```python
search_input = SearchInput(
    question="What is machine learning?",
    collection_id=collection_uuid,
    user_id=user_uuid,
    techniques=[
        TechniqueConfig(technique_id="hyde"),
        TechniqueConfig(technique_id="vector_retrieval"),
        TechniqueConfig(technique_id="reranking", config={"top_k": 5})
    ]
)
```

### 2. Using Presets

```python
search_input = SearchInput(
    question="Explain quantum computing",
    collection_id=collection_uuid,
    user_id=user_uuid,
    technique_preset="accurate"
)
```

### 3. Advanced Composition

```python
search_input = SearchInput(
    question="Compare neural networks and decision trees",
    collection_id=collection_uuid,
    user_id=user_uuid,
    techniques=[
        TechniqueConfig(
            technique_id="query_transformation",
            config={"method": "decomposition"}
        ),
        TechniqueConfig(
            technique_id="fusion_retrieval",
            config={"vector_weight": 0.8}
        ),
        TechniqueConfig(
            technique_id="reranking",
            config={"top_k": 15}
        ),
        TechniqueConfig(technique_id="contextual_compression"),
        TechniqueConfig(
            technique_id="multi_faceted_filtering",
            config={
                "min_similarity": 0.75,
                "ensure_diversity": True,
                "metadata_filters": {"document_type": "research_paper"}
            }
        )
    ]
)
```

### 4. Backward Compatible (Legacy)

```python
# Old style still works
search_input = SearchInput(
    question="What is machine learning?",
    collection_id=collection_uuid,
    user_id=user_uuid,
    config_metadata={
        "top_k": 10,
        "use_reranking": True
    }
)
# Internally converted to default preset with overrides
```

## Integration with SearchService

```python
class SearchService:
    """Enhanced SearchService with technique pipeline support."""

    def __init__(self, db: Session, settings: Settings):
        self.db = db
        self.settings = settings
        self.technique_registry = technique_registry
        # ... other services

    async def search(self, search_input: SearchInput) -> SearchOutput:
        """Execute search with technique pipeline."""

        # 1. Build technique pipeline from config
        pipeline = self._build_pipeline(search_input)

        # 2. Create execution context
        context = TechniqueContext(
            user_id=search_input.user_id,
            collection_id=search_input.collection_id,
            original_query=search_input.question,
            current_query=search_input.question,
            llm_provider=self.llm_provider_service.get_provider(
                search_input.user_id
            ),
            vector_store=self.vector_store,
            db_session=self.db
        )

        # 3. Execute pipeline
        context = await pipeline.execute(context)

        # 4. Generate final answer (existing logic)
        answer = await self._generate_answer(
            query=context.current_query,
            documents=context.retrieved_documents,
            llm_provider=context.llm_provider
        )

        # 5. Return enriched response
        return SearchOutput(
            answer=answer,
            documents=[r.chunk.metadata for r in context.retrieved_documents],
            query_results=context.retrieved_documents,
            rewritten_query=context.current_query,
            execution_time=sum(
                m["execution_time_ms"]
                for m in context.metrics["pipeline_metrics"].values()
            ),
            metadata={
                "techniques_applied": context.execution_trace,
                "technique_metrics": context.metrics["pipeline_metrics"]
            }
        )

    def _build_pipeline(
        self,
        search_input: SearchInput
    ) -> TechniquePipeline:
        """Build technique pipeline from search input."""

        builder = TechniquePipelineBuilder(self.technique_registry)

        # Use preset if specified
        if search_input.technique_preset:
            preset_techniques = TECHNIQUE_PRESETS.get(
                search_input.technique_preset
            )
            if not preset_techniques:
                raise ValueError(
                    f"Unknown preset: {search_input.technique_preset}"
                )
            for tech_config in preset_techniques:
                builder.add_technique(
                    tech_config.technique_id,
                    tech_config.config
                )

        # Add explicitly configured techniques
        elif search_input.techniques:
            for tech_config in search_input.techniques:
                if tech_config.enabled:
                    builder.add_technique(
                        tech_config.technique_id,
                        tech_config.config
                    )

        # Fallback to default preset
        else:
            for tech_config in TECHNIQUE_PRESETS["default"]:
                builder.add_technique(
                    tech_config.technique_id,
                    tech_config.config
                )

        return builder.build()
```

## Observability & Monitoring

### Metrics Collection

```python
@dataclass
class TechniqueMetrics:
    """Metrics for technique execution."""
    technique_id: str
    execution_time_ms: float
    tokens_used: int
    success: bool
    error: str | None
    fallback_used: bool

    # Technique-specific metrics
    custom_metrics: dict[str, Any]

class MetricsCollector:
    """Collect and aggregate technique metrics."""

    def record_technique_execution(
        self,
        metrics: TechniqueMetrics
    ) -> None:
        """Record technique execution metrics."""
        # Log to structured logging
        logger.info(
            "Technique executed",
            extra={
                "technique_id": metrics.technique_id,
                "execution_time_ms": metrics.execution_time_ms,
                "tokens_used": metrics.tokens_used,
                "success": metrics.success
            }
        )

        # Send to MLFlow/monitoring system
        # mlflow.log_metrics({...})

    def get_technique_performance_summary(
        self,
        technique_id: str,
        time_window: timedelta
    ) -> dict[str, Any]:
        """Get performance summary for a technique."""
        # Query metrics database
        return {
            "avg_execution_time_ms": 0.0,
            "success_rate": 0.0,
            "total_executions": 0,
            "p50_latency": 0.0,
            "p95_latency": 0.0,
            "p99_latency": 0.0
        }
```

### Tracing

Use the existing enhanced logging system:

```python
from core.enhanced_logging import get_logger
from core.logging_context import log_operation, pipeline_stage_context

logger = get_logger(__name__)

async def execute_technique(
    technique: BaseTechnique,
    context: TechniqueContext
) -> TechniqueResult:
    """Execute technique with full tracing."""

    with log_operation(
        logger,
        f"technique_{technique.technique_id}",
        "pipeline",
        context.collection_id,
        user_id=context.user_id
    ):
        with pipeline_stage_context(
            PipelineStage.from_technique_stage(technique.stage)
        ):
            logger.info(
                f"Executing technique: {technique.technique_id}",
                extra={
                    "technique": technique.technique_id,
                    "config": context.config
                }
            )

            result = await technique.execute(context, context.config)

            logger.info(
                f"Technique completed: {technique.technique_id}",
                extra={
                    "success": result.success,
                    "execution_time_ms": result.execution_time_ms,
                    "tokens_used": result.tokens_used
                }
            )

            return result
```

## Implementation Roadmap

### Phase 1: Core Framework (Week 1)
- [ ] Create technique interfaces and base classes
- [ ] Implement technique registry
- [ ] Build pipeline builder and executor
- [ ] Update SearchInput schema
- [ ] Add backward compatibility layer

### Phase 2: Basic Techniques (Week 2-3)
- [ ] Migrate existing retrievers to technique interface
- [ ] Migrate existing reranker to technique interface
- [ ] Implement HyDE technique
- [ ] Implement query transformation technique
- [ ] Implement fusion retrieval technique

### Phase 3: Advanced Techniques (Week 4-6)
- [ ] Implement contextual compression
- [ ] Implement semantic chunking
- [ ] Implement adaptive retrieval
- [ ] Implement multi-faceted filtering
- [ ] Implement proposition chunking

### Phase 4: Polish & Documentation (Week 7)
- [ ] Add comprehensive tests
- [ ] Update API documentation
- [ ] Create user guide with examples
- [ ] Add performance benchmarks
- [ ] Set up monitoring dashboards

## Testing Strategy

### Unit Tests
- Test each technique in isolation
- Test pipeline builder validation
- Test registry operations
- Test context propagation

### Integration Tests
- Test technique combinations
- Test preset configurations
- Test error handling and fallbacks
- Test backward compatibility

### Performance Tests
- Benchmark technique overhead
- Measure latency impact
- Profile token usage
- Test under load

### End-to-End Tests
- Test complete search flows
- Validate answer quality
- Test CLI integration
- Test API integration

## Migration Plan

### Backward Compatibility

Existing code continues to work:

```python
# Old style (still works)
search_input = SearchInput(
    question="What is ML?",
    collection_id=coll_id,
    user_id=user_id,
    config_metadata={"top_k": 10}
)
# Internally: converted to default preset + config overrides
```

### Gradual Migration

1. Phase 1: Deploy framework with backward compatibility
2. Phase 2: Migrate internal services to use techniques
3. Phase 3: Update documentation and examples
4. Phase 4: Encourage new API usage via examples
5. Phase 5: (Future) Deprecate config_metadata

## Security Considerations

1. **Input Validation**: Validate all technique configurations
2. **Resource Limits**: Prevent excessive technique chaining
3. **Cost Controls**: Track and limit LLM token usage
4. **Access Control**: Validate user permissions for techniques
5. **Rate Limiting**: Apply rate limits per user/technique

## Cost Estimation

### Per-Query Cost Model

```python
def estimate_query_cost(techniques: list[TechniqueConfig]) -> dict[str, Any]:
    """Estimate cost for a query with given techniques."""

    base_cost = {
        "vector_search_ops": 1,
        "llm_calls": 0,
        "tokens": 0,
        "estimated_latency_ms": 100  # Base retrieval
    }

    for tech_config in techniques:
        technique = technique_registry.get_technique(tech_config.technique_id)
        metadata = technique.get_metadata()

        if metadata.requires_llm:
            base_cost["llm_calls"] += 1
            base_cost["tokens"] += 500  # Estimate per call

        base_cost["estimated_latency_ms"] += metadata.estimated_latency_ms

    return base_cost
```

## Performance Optimization

1. **Caching**: Cache technique results where appropriate
2. **Parallel Execution**: Execute independent techniques in parallel
3. **Lazy Loading**: Only instantiate techniques when needed
4. **Resource Pooling**: Reuse LLM connections
5. **Early Termination**: Stop pipeline if critical technique fails

## Appendix: Technique Interface Examples

### Query Transformation Technique

```python
class QueryTransformationTechnique(BaseTechnique[str, str]):
    """Transform query using various methods (rewrite, step-back, etc.)."""

    technique_id = "query_transformation"
    name = "Query Transformation"
    description = "Rewrite queries for better retrieval"
    stage = TechniqueStage.QUERY_TRANSFORMATION
    requires_llm = True
    estimated_latency_ms = 200
    token_cost_multiplier = 1.2

    async def execute(
        self,
        context: TechniqueContext
    ) -> TechniqueResult[str]:
        """Transform the query."""
        method = context.config.get("method", "rewrite")

        if method == "rewrite":
            transformed = await self._rewrite_query(
                context.current_query,
                context.llm_provider
            )
        elif method == "stepback":
            transformed = await self._stepback_query(
                context.current_query,
                context.llm_provider
            )
        else:
            return TechniqueResult(
                success=False,
                output=context.current_query,
                error=f"Unknown method: {method}",
                metadata={},
                execution_time_ms=0,
                technique_id=self.technique_id
            )

        # Update context query
        context.current_query = transformed

        return TechniqueResult(
            success=True,
            output=transformed,
            metadata={"original": context.original_query, "method": method},
            execution_time_ms=0,  # Measured by caller
            technique_id=self.technique_id
        )

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate configuration."""
        method = config.get("method")
        if method and method not in ["rewrite", "stepback", "decomposition"]:
            return False
        return True
```

### HyDE Technique

```python
class HyDETechnique(BaseTechnique[str, str]):
    """Hypothetical Document Embeddings technique."""

    technique_id = "hyde"
    name = "HyDE"
    description = "Generate hypothetical answer for better retrieval"
    stage = TechniqueStage.QUERY_TRANSFORMATION
    requires_llm = True
    requires_embeddings = True
    estimated_latency_ms = 300
    token_cost_multiplier = 1.5

    async def execute(
        self,
        context: TechniqueContext
    ) -> TechniqueResult[str]:
        """Generate hypothetical document."""

        # Generate hypothetical answer
        hypothetical_answer = await self._generate_hypothetical_answer(
            context.current_query,
            context.llm_provider
        )

        # Update context to search with hypothetical answer
        context.current_query = hypothetical_answer
        context.intermediate_results["hyde_original_query"] = context.original_query

        return TechniqueResult(
            success=True,
            output=hypothetical_answer,
            metadata={
                "original_query": context.original_query,
                "hypothetical_answer": hypothetical_answer
            },
            execution_time_ms=0,
            technique_id=self.technique_id
        )
```

---

**Document Version**: 1.0
**Last Updated**: 2025-10-23
**Author**: Claude Code Architecture Team
