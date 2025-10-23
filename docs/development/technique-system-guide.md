# RAG Technique System - Developer Guide

## Overview

This guide shows how to use and extend the RAG technique system for dynamic technique selection at runtime. The system enables users to configure which retrieval augmentation techniques to apply on a per-query basis without code changes.

## Table of Contents

1. [Using the Technique System](#using-the-technique-system)
2. [Creating Custom Techniques](#creating-custom-techniques)
3. [Registering Techniques](#registering-techniques)
4. [Building Pipelines](#building-pipelines)
5. [Testing Techniques](#testing-techniques)
6. [Best Practices](#best-practices)

## Using the Technique System

### Basic Usage

#### Using Presets (Easiest)

```python
from rag_solution.schemas.search_schema import SearchInput

# Use a preset configuration
search_input = SearchInput(
    question="What is machine learning?",
    collection_id=collection_uuid,
    user_id=user_uuid,
    technique_preset="accurate"  # Options: default, fast, accurate, cost_optimized, comprehensive
)
```

Available presets:
- **default**: Balanced performance (vector retrieval + reranking)
- **fast**: Minimal latency (vector retrieval only)
- **accurate**: Maximum quality (query transformation + HyDE + fusion + reranking + compression)
- **cost_optimized**: Minimal token usage (semantic chunking + filtering)
- **comprehensive**: All techniques (query decomposition + adaptive retrieval + full pipeline)

#### Explicit Technique Selection

```python
from rag_solution.techniques.base import TechniqueConfig

# Specify exact techniques to use
search_input = SearchInput(
    question="Explain quantum computing",
    collection_id=collection_uuid,
    user_id=user_uuid,
    techniques=[
        TechniqueConfig(technique_id="hyde"),
        TechniqueConfig(technique_id="vector_retrieval", config={"top_k": 10}),
        TechniqueConfig(technique_id="reranking", config={"top_k": 5})
    ]
)
```

#### Advanced Composition

```python
# Complex technique pipeline with custom configuration
search_input = SearchInput(
    question="Compare neural networks and decision trees for image classification",
    collection_id=collection_uuid,
    user_id=user_uuid,
    techniques=[
        TechniqueConfig(
            technique_id="query_transformation",
            config={"method": "decomposition"}
        ),
        TechniqueConfig(
            technique_id="fusion_retrieval",
            config={"vector_weight": 0.8, "top_k": 20}
        ),
        TechniqueConfig(
            technique_id="reranking",
            config={"top_k": 10}
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

### Understanding Search Results

```python
# Execute search
search_output = await search_service.search(search_input)

# Access results
print(f"Answer: {search_output.answer}")
print(f"Documents: {len(search_output.documents)}")

# Observability - see which techniques were applied
print(f"Techniques applied: {search_output.techniques_applied}")
# Output: ['hyde', 'vector_retrieval', 'reranking']

# Performance metrics
print(f"Execution time: {search_output.execution_time}ms")

# Per-technique metrics
for technique_id, metrics in search_output.technique_metrics.items():
    print(f"{technique_id}: {metrics['execution_time_ms']}ms, "
          f"tokens: {metrics.get('tokens_used', 0)}, "
          f"success: {metrics['success']}")
```

## Creating Custom Techniques

### Step 1: Define Your Technique

```python
from rag_solution.techniques.base import (
    BaseTechnique,
    TechniqueContext,
    TechniqueResult,
    TechniqueStage
)
from typing import Any

class MyCustomTechnique(BaseTechnique[str, str]):
    """Custom technique that does something useful.

    This technique transforms queries by adding domain-specific context.
    """

    # Required metadata
    technique_id = "my_custom_technique"
    name = "My Custom Technique"
    description = "Adds domain-specific context to queries"
    stage = TechniqueStage.QUERY_TRANSFORMATION

    # Resource requirements
    requires_llm = True  # Set to True if you need LLM access
    requires_embeddings = False
    requires_vector_store = False

    # Performance characteristics (for cost estimation)
    estimated_latency_ms = 150
    token_cost_multiplier = 1.2

    async def execute(
        self,
        context: TechniqueContext
    ) -> TechniqueResult[str]:
        """Execute the technique logic.

        Args:
            context: Pipeline context with query, services, and state

        Returns:
            TechniqueResult with output and metadata
        """
        try:
            # Get configuration
            domain = context.config.get("domain", "general")

            # Access LLM if needed
            llm_provider = context.llm_provider
            if llm_provider is None:
                return TechniqueResult(
                    success=False,
                    output=context.current_query,
                    metadata={},
                    technique_id=self.technique_id,
                    execution_time_ms=0,
                    error="LLM provider not available"
                )

            # Perform transformation
            enhanced_query = await self._add_domain_context(
                context.current_query,
                domain,
                llm_provider
            )

            # Update context
            context.current_query = enhanced_query

            # Return success result
            return TechniqueResult(
                success=True,
                output=enhanced_query,
                metadata={
                    "original_query": context.original_query,
                    "domain": domain
                },
                technique_id=self.technique_id,
                execution_time_ms=0,  # Set by wrapper
                tokens_used=50,  # Estimate or track actual usage
                llm_calls=1
            )

        except Exception as e:
            # Always handle errors gracefully
            return TechniqueResult(
                success=False,
                output=context.current_query,  # Return original
                metadata={},
                technique_id=self.technique_id,
                execution_time_ms=0,
                error=str(e),
                fallback_used=True
            )

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate technique configuration.

        Args:
            config: Configuration dictionary

        Returns:
            True if valid, False otherwise
        """
        domain = config.get("domain")
        if domain is not None:
            valid_domains = ["general", "medical", "legal", "technical"]
            if domain not in valid_domains:
                return False
        return True

    def get_default_config(self) -> dict[str, Any]:
        """Get default configuration."""
        return {
            "domain": "general"
        }

    def get_config_schema(self) -> dict[str, Any]:
        """Get JSON schema for configuration validation."""
        return {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "enum": ["general", "medical", "legal", "technical"],
                    "description": "Domain for context enhancement",
                    "default": "general"
                }
            },
            "additionalProperties": False
        }

    async def _add_domain_context(
        self,
        query: str,
        domain: str,
        llm_provider
    ) -> str:
        """Helper method to add domain context."""
        # Implementation here
        prompt = f"Add {domain} domain context to this query: {query}"
        response = await llm_provider.generate(prompt)
        return response
```

### Step 2: Register Your Technique

#### Method 1: Using Decorator (Recommended)

```python
from rag_solution.techniques.registry import register_technique

@register_technique()  # Uses technique_id from class
class MyCustomTechnique(BaseTechnique[str, str]):
    technique_id = "my_custom_technique"
    # ... rest of implementation
```

#### Method 2: Manual Registration

```python
from rag_solution.techniques.registry import technique_registry

# Register manually
technique_registry.register(
    "my_custom_technique",
    MyCustomTechnique,
    singleton=True  # Reuse single instance (default)
)
```

### Step 3: Use Your Technique

```python
# Now you can use it in search requests
search_input = SearchInput(
    question="What is mitochondria?",
    collection_id=collection_uuid,
    user_id=user_uuid,
    techniques=[
        TechniqueConfig(
            technique_id="my_custom_technique",
            config={"domain": "medical"}
        ),
        TechniqueConfig(technique_id="vector_retrieval"),
        TechniqueConfig(technique_id="reranking")
    ]
)
```

## Common Technique Patterns

### Query Transformation Pattern

Transform the query before retrieval:

```python
class QueryEnhancementTechnique(BaseTechnique[str, str]):
    stage = TechniqueStage.QUERY_TRANSFORMATION

    async def execute(self, context: TechniqueContext) -> TechniqueResult[str]:
        # Enhance query
        enhanced = await self._enhance(context.current_query)

        # Update context
        context.current_query = enhanced

        return TechniqueResult(
            success=True,
            output=enhanced,
            metadata={"original": context.original_query},
            technique_id=self.technique_id,
            execution_time_ms=0
        )
```

### Retrieval Pattern

Retrieve documents and store in context:

```python
class CustomRetrievalTechnique(BaseTechnique[str, list[QueryResult]]):
    stage = TechniqueStage.RETRIEVAL
    requires_vector_store = True

    async def execute(self, context: TechniqueContext) -> TechniqueResult[list[QueryResult]]:
        # Retrieve documents
        results = await self._retrieve(
            context.current_query,
            context.vector_store
        )

        # Store in context for later techniques
        context.retrieved_documents = results

        return TechniqueResult(
            success=True,
            output=results,
            metadata={"count": len(results)},
            technique_id=self.technique_id,
            execution_time_ms=0
        )
```

### Post-Retrieval Processing Pattern

Process retrieved documents:

```python
class DocumentFilteringTechnique(BaseTechnique[list[QueryResult], list[QueryResult]]):
    stage = TechniqueStage.POST_RETRIEVAL

    async def execute(self, context: TechniqueContext) -> TechniqueResult[list[QueryResult]]:
        # Get documents from context
        documents = context.retrieved_documents

        # Filter
        filtered = self._filter_documents(
            documents,
            context.config.get("min_score", 0.7)
        )

        # Update context
        context.retrieved_documents = filtered

        return TechniqueResult(
            success=True,
            output=filtered,
            metadata={
                "original_count": len(documents),
                "filtered_count": len(filtered)
            },
            technique_id=self.technique_id,
            execution_time_ms=0
        )
```

## Building Pipelines Programmatically

### Using the Builder API

```python
from rag_solution.techniques.pipeline import TechniquePipelineBuilder
from rag_solution.techniques.registry import technique_registry

# Create builder
builder = TechniquePipelineBuilder(technique_registry)

# Build pipeline with fluent API
pipeline = (
    builder
    .add_query_transformation(method="rewrite")
    .add_hyde()
    .add_fusion_retrieval(vector_weight=0.8, top_k=20)
    .add_reranking(top_k=10)
    .add_contextual_compression()
    .build()
)

# Get cost estimate
cost = pipeline.get_estimated_cost()
print(f"Estimated latency: {cost['estimated_latency_ms']}ms")
print(f"Techniques: {cost['technique_count']}")
print(f"LLM calls: {cost['llm_techniques']}")

# Execute pipeline
from rag_solution.techniques.base import TechniqueContext

context = TechniqueContext(
    user_id=user_uuid,
    collection_id=collection_uuid,
    original_query="What is machine learning?",
    llm_provider=llm_provider,
    vector_store=vector_store
)

result_context = await pipeline.execute(context)

# Access results
print(f"Final query: {result_context.current_query}")
print(f"Documents: {len(result_context.retrieved_documents)}")
print(f"Execution trace: {result_context.execution_trace}")
```

### Creating Custom Presets

```python
from rag_solution.techniques.pipeline import TECHNIQUE_PRESETS
from rag_solution.techniques.base import TechniqueConfig

# Add a custom preset
TECHNIQUE_PRESETS["medical_domain"] = [
    TechniqueConfig(
        technique_id="my_custom_technique",
        config={"domain": "medical"}
    ),
    TechniqueConfig(
        technique_id="fusion_retrieval",
        config={"vector_weight": 0.9, "top_k": 15}
    ),
    TechniqueConfig(
        technique_id="reranking",
        config={"top_k": 8}
    )
]

# Use the custom preset
search_input = SearchInput(
    question="What causes diabetes?",
    collection_id=collection_uuid,
    user_id=user_uuid,
    technique_preset="medical_domain"
)
```

## Testing Techniques

### Unit Testing

```python
import pytest
from pydantic import UUID4
from rag_solution.techniques.base import TechniqueContext

@pytest.mark.asyncio
async def test_my_custom_technique():
    """Test custom technique execution."""
    # Create technique instance
    technique = MyCustomTechnique()

    # Create test context
    context = TechniqueContext(
        user_id=UUID4("12345678-1234-5678-1234-567812345678"),
        collection_id=UUID4("87654321-4321-8765-4321-876543218765"),
        original_query="test query",
        current_query="test query",
        config={"domain": "medical"}
    )

    # Execute technique
    result = await technique.execute_with_timing(context)

    # Assertions
    assert result.success
    assert result.output != "test query"  # Should be transformed
    assert result.tokens_used > 0
    assert result.technique_id == "my_custom_technique"
    assert "domain" in result.metadata


def test_config_validation():
    """Test configuration validation."""
    technique = MyCustomTechnique()

    # Valid config
    assert technique.validate_config({"domain": "medical"})

    # Invalid config
    assert not technique.validate_config({"domain": "invalid"})


def test_metadata():
    """Test technique metadata."""
    technique = MyCustomTechnique()
    metadata = technique.get_metadata()

    assert metadata.technique_id == "my_custom_technique"
    assert metadata.stage == TechniqueStage.QUERY_TRANSFORMATION
    assert metadata.requires_llm is True
```

### Integration Testing

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_technique_in_pipeline(db_session, llm_provider):
    """Test technique integrated in full pipeline."""
    from rag_solution.techniques.pipeline import TechniquePipelineBuilder
    from rag_solution.techniques.registry import technique_registry

    # Build pipeline with custom technique
    builder = TechniquePipelineBuilder(technique_registry)
    pipeline = (
        builder
        .add_technique("my_custom_technique", {"domain": "medical"})
        .add_vector_retrieval(top_k=10)
        .build()
    )

    # Create context with real services
    context = TechniqueContext(
        user_id=test_user_id,
        collection_id=test_collection_id,
        original_query="What is diabetes?",
        llm_provider=llm_provider,
        vector_store=vector_store,
        db_session=db_session
    )

    # Execute
    result_context = await pipeline.execute(context)

    # Verify
    assert result_context.current_query != "What is diabetes?"
    assert len(result_context.retrieved_documents) > 0
    assert "pipeline_metrics" in result_context.metrics
```

## Best Practices

### 1. Error Handling

Always handle errors gracefully and return a TechniqueResult:

```python
async def execute(self, context: TechniqueContext) -> TechniqueResult:
    try:
        # Main logic
        result = await self._do_work(context)
        return TechniqueResult(
            success=True,
            output=result,
            metadata={},
            technique_id=self.technique_id,
            execution_time_ms=0
        )
    except Exception as e:
        logger.error(f"Technique {self.technique_id} failed: {e}")
        return TechniqueResult(
            success=False,
            output=self._get_fallback_value(context),
            metadata={},
            technique_id=self.technique_id,
            execution_time_ms=0,
            error=str(e),
            fallback_used=True
        )
```

### 2. Configuration Validation

Always validate configuration in `validate_config()`:

```python
def validate_config(self, config: dict[str, Any]) -> bool:
    # Check required fields
    if "required_field" not in config:
        logger.warning("Missing required field")
        return False

    # Validate types
    if not isinstance(config["required_field"], int):
        logger.warning("Invalid type for required_field")
        return False

    # Validate ranges
    if config["required_field"] < 0:
        logger.warning("required_field must be non-negative")
        return False

    return True
```

### 3. Logging and Observability

Use structured logging:

```python
import logging
logger = logging.getLogger(__name__)

async def execute(self, context: TechniqueContext) -> TechniqueResult:
    logger.debug(
        f"Executing {self.technique_id}",
        extra={
            "technique": self.technique_id,
            "query": context.current_query[:100],
            "config": context.config
        }
    )

    # ... execution

    logger.info(
        f"Completed {self.technique_id}",
        extra={
            "technique": self.technique_id,
            "success": result.success,
            "tokens_used": result.tokens_used
        }
    )
```

### 4. Resource Management

Check for required resources:

```python
async def execute(self, context: TechniqueContext) -> TechniqueResult:
    # Validate dependencies
    if self.requires_llm and context.llm_provider is None:
        return TechniqueResult(
            success=False,
            output=None,
            metadata={},
            technique_id=self.technique_id,
            execution_time_ms=0,
            error="LLM provider required but not available"
        )

    # Continue with execution
    # ...
```

### 5. Cost Tracking

Track and report token usage:

```python
async def execute(self, context: TechniqueContext) -> TechniqueResult:
    tokens_before = self._get_token_count(context.llm_provider)

    # Execute LLM calls
    result = await context.llm_provider.generate(prompt)

    tokens_after = self._get_token_count(context.llm_provider)
    tokens_used = tokens_after - tokens_before

    return TechniqueResult(
        success=True,
        output=result,
        metadata={},
        technique_id=self.technique_id,
        execution_time_ms=0,
        tokens_used=tokens_used,
        llm_calls=1
    )
```

### 6. Technique Composition

Design techniques to work well with others:

```python
# Don't assume context state - check what's available
async def execute(self, context: TechniqueContext) -> TechniqueResult:
    # Check if previous techniques provided documents
    if not context.retrieved_documents:
        # This technique needs documents - return error or skip
        return TechniqueResult(
            success=False,
            output=[],
            metadata={},
            technique_id=self.technique_id,
            execution_time_ms=0,
            error="No documents available for processing"
        )

    # Process documents
    processed = self._process(context.retrieved_documents)
    context.retrieved_documents = processed

    return TechniqueResult(success=True, ...)
```

## Advanced Topics

### Conditional Technique Execution

```python
class AdaptiveTechnique(BaseTechnique):
    """Technique that adapts based on query characteristics."""

    async def execute(self, context: TechniqueContext) -> TechniqueResult:
        # Analyze query
        query_type = await self._classify_query(context.current_query)

        # Execute different logic based on query type
        if query_type == "factual":
            result = await self._factual_strategy(context)
        elif query_type == "analytical":
            result = await self._analytical_strategy(context)
        else:
            result = await self._default_strategy(context)

        return result
```

### Technique Versioning

```python
@register_technique("my_technique_v2")
class MyTechniqueV2(BaseTechnique):
    """Improved version of my_technique with better performance."""
    technique_id = "my_technique_v2"
    # ... implementation

    # Track compatibility
    compatible_with = ["my_technique", "other_technique"]
    incompatible_with = ["old_incompatible_technique"]
```

### Custom Pipeline Validation

```python
from rag_solution.techniques.registry import TechniqueRegistry

class CustomRegistry(TechniqueRegistry):
    """Registry with custom validation rules."""

    def validate_pipeline(self, technique_ids: list[str]) -> tuple[bool, str | None]:
        # Call base validation
        is_valid, error = super().validate_pipeline(technique_ids)
        if not is_valid:
            return False, error

        # Custom validation: ensure certain combinations
        if "hyde" in technique_ids and "query_transformation" in technique_ids:
            return False, "HyDE and query_transformation are redundant"

        return True, None
```

## Troubleshooting

### Technique Not Found

```
ValueError: Unknown technique: my_technique
```

**Solution**: Ensure technique is registered:
```python
from rag_solution.techniques.registry import technique_registry
print(technique_registry.list_techniques())  # Check if registered
```

### Invalid Stage Ordering

```
ValueError: Invalid stage ordering
```

**Solution**: Techniques must be ordered by stage. Check stage order in architecture doc.

### Configuration Validation Failed

```
ValueError: Invalid config for my_technique: {...}
```

**Solution**: Check `validate_config()` implementation and ensure config matches schema.

### Pipeline Execution Failure

Check technique metrics in search output:
```python
for technique_id, metrics in search_output.technique_metrics.items():
    if not metrics["success"]:
        print(f"{technique_id} failed: {metrics.get('error')}")
```

---

**Document Version**: 1.0
**Last Updated**: 2025-10-23
**Maintained by**: RAG Modulo Development Team
