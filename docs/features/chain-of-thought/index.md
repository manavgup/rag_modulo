# Chain of Thought (CoT) Reasoning

Chain of Thought (CoT) reasoning is an advanced feature that enhances RAG search quality by breaking down complex questions into manageable sub-questions and reasoning through them step-by-step.

## Overview

The Chain of Thought system automatically:

1. **Classifies questions** to determine if CoT reasoning is needed
2. **Decomposes complex queries** into logical sub-questions
3. **Executes reasoning steps** sequentially with context preservation
4. **Tracks source attributions** for each reasoning step
5. **Synthesizes final answers** from intermediate results
6. **Provides transparency** through detailed reasoning traces

## Key Features

- **Automatic Question Classification**: Determines complexity and CoT necessity
- **Multi-Strategy Decomposition**: Supports decomposition, iterative, hierarchical, and causal strategies
- **Source Attribution**: Tracks document sources used in each reasoning step
- **Context Preservation**: Maintains context across reasoning steps
- **Configurable Depth**: Adjustable maximum reasoning depth
- **Token Budget Management**: Efficient token usage with configurable multipliers
- **Confidence Scoring**: Per-step and aggregate confidence metrics

## When CoT is Used

CoT reasoning is automatically triggered for:

- **Multi-part questions** (containing "and", "or", "but", "however")
- **Comparison questions** (containing "compare", "differ", "versus", "better")
- **Causal questions** (containing "why", "how", "cause", "reason", "explain")
- **Complex analytical questions** (long questions or procedural content)
- **Questions exceeding complexity thresholds** (word count, complexity analysis)

## Architecture Components

### Core Services

1. **[ChainOfThoughtService](./services.md#chainofthoughtservice)** - Main orchestration service
2. **[QuestionDecomposer](./services.md#questiondecomposer)** - Breaks down complex questions
3. **[AnswerSynthesizer](./services.md#answersynthesizer)** - Synthesizes final answers
4. **[SourceAttributionService](./source-attribution.md)** - Tracks document sources

### Data Models

- **[Schemas](./schemas.md)** - Pydantic models for CoT data structures
- **[Configuration](./configuration.md)** - CoT configuration options
- **[Source Attribution](./source-attribution.md#schemas)** - Source tracking schemas

## Quick Start

### Basic Usage

```python
from rag_solution.services.chain_of_thought_service import ChainOfThoughtService
from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput

# Initialize service
cot_service = ChainOfThoughtService(settings=settings)

# Create input
cot_input = ChainOfThoughtInput(
    question="Compare machine learning and deep learning approaches for image recognition",
    collection_id=collection_uuid,
    user_id=user_uuid
)

# Execute reasoning
result = await cot_service.execute_chain_of_thought(cot_input)

# Access results
print(f"Final Answer: {result.final_answer}")
print(f"Reasoning Steps: {len(result.reasoning_steps)}")
print(f"Sources Used: {len(result.source_summary.all_sources)}")
```

### Integration with RAG Search

```python
# In your search service
if await self._should_use_cot(search_input.question):
    cot_result = await self.cot_service.execute_chain_of_thought(
        cot_input=ChainOfThoughtInput(
            question=search_input.question,
            collection_id=search_input.collection_id,
            user_id=search_input.user_id,
            cot_config=search_input.config_metadata.get("cot_config")
        ),
        context_documents=retrieved_documents
    )

    # Use CoT result with source attribution
    return SearchOutput(
        answer=cot_result.final_answer,
        sources=cot_result.source_summary.primary_sources,
        reasoning_trace=cot_result.reasoning_steps
    )
```

## Configuration

CoT behavior is configurable through environment variables and runtime configuration:

```python
# Environment configuration
COT_MAX_REASONING_DEPTH=3
COT_REASONING_STRATEGY="decomposition"
COT_TOKEN_BUDGET_MULTIPLIER=2.0

# Runtime configuration
cot_config = {
    "enabled": True,
    "max_reasoning_depth": 4,
    "reasoning_strategy": "hierarchical",
    "evaluation_threshold": 0.7
}
```

## Documentation Structure

- **[Services](./services.md)** - Detailed service documentation
- **[Schemas](./schemas.md)** - Data model specifications
- **[Source Attribution](./source-attribution.md)** - Source tracking system
- **[Configuration](./configuration.md)** - Configuration options
- **[API Reference](./api-reference.md)** - Complete API documentation
- **[Examples](./examples.md)** - Usage examples and patterns
- **[Testing](./testing.md)** - Testing approach and examples

## Benefits

### Enhanced Search Quality
- Complex questions get thorough, step-by-step analysis
- Multi-faceted queries are properly decomposed
- Context is preserved across reasoning steps

### Transparency and Trust
- Complete reasoning traces show how answers were derived
- Source attributions track which documents influenced each step
- Confidence scores indicate answer reliability

### Flexibility and Control
- Multiple reasoning strategies for different question types
- Configurable depth and complexity thresholds
- Integration with existing RAG workflows

## Next Steps

1. **[Read the Services Guide](./services.md)** to understand the core components
2. **[Explore Source Attribution](./source-attribution.md)** to see how sources are tracked
3. **[Check out Examples](./examples.md)** for practical implementation patterns
4. **[Review the API Reference](./api-reference.md)** for complete technical details
