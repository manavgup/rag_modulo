# CoT Configuration Guide

This guide covers all configuration options for the Chain of Thought system, including environment variables, runtime configuration, and best practices for different use cases.

## Overview

The CoT system is highly configurable to adapt to different:

- **Question complexity levels**: Simple vs. complex analytical questions
- **Performance requirements**: Speed vs. thoroughness trade-offs
- **Token budget constraints**: Cost optimization
- **Domain-specific needs**: Different reasoning strategies for different domains

## Environment Configuration

### Core Settings

Add these environment variables to your `.env` file:

```bash
# CoT Feature Toggle
COT_ENABLED=true

# Reasoning Parameters
COT_MAX_REASONING_DEPTH=3
COT_REASONING_STRATEGY=decomposition
COT_TOKEN_BUDGET_MULTIPLIER=2.0

# Quality Thresholds
COT_EVALUATION_THRESHOLD=0.6
COT_CONFIDENCE_THRESHOLD=0.7

# Performance Tuning
COT_CONTEXT_PRESERVATION=true
COT_PARALLEL_EXECUTION=false
COT_TIMEOUT_SECONDS=30

# Debug and Logging
COT_DEBUG_MODE=false
COT_LOG_REASONING_TRACES=true
```

### Environment Variable Reference

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `COT_ENABLED` | bool | `false` | Global CoT feature toggle |
| `COT_MAX_REASONING_DEPTH` | int | `3` | Maximum number of reasoning steps |
| `COT_REASONING_STRATEGY` | str | `"decomposition"` | Default reasoning strategy |
| `COT_TOKEN_BUDGET_MULTIPLIER` | float | `2.0` | Token budget multiplier vs. regular search |
| `COT_EVALUATION_THRESHOLD` | float | `0.6` | Minimum confidence score for step acceptance |
| `COT_CONFIDENCE_THRESHOLD` | float | `0.7` | Minimum confidence for high-quality responses |
| `COT_CONTEXT_PRESERVATION` | bool | `true` | Preserve context across reasoning steps |
| `COT_TIMEOUT_SECONDS` | int | `30` | Maximum execution time per CoT request |

## Runtime Configuration

### ChainOfThoughtConfig Schema

Runtime configuration overrides environment settings:

```python
from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtConfig

# Basic configuration
config = ChainOfThoughtConfig(
    enabled=True,
    max_reasoning_depth=4,
    reasoning_strategy="hierarchical",
    evaluation_threshold=0.7
)
```

### Configuration via API

Pass configuration through the search API:

```python
search_input = SearchInput(
    question="Compare supervised and unsupervised learning",
    collection_id=collection_id,
    user_id=user_id,
    config_metadata={
        "cot_config": {
            "enabled": True,
            "max_reasoning_depth": 5,
            "reasoning_strategy": "comparison",
            "token_budget_multiplier": 3.0
        }
    }
)
```

### CLI Configuration

Configure CoT through CLI parameters:

```bash
# Enable CoT with custom depth
./rag-cli search query col_123 "Complex question" --cot-enabled --cot-depth 4

# Use specific strategy
./rag-cli search query col_123 "Why does X cause Y?" --cot-strategy causal

# High-quality mode
./rag-cli search query col_123 "Detailed analysis" --cot-quality high
```

## Reasoning Strategies

### Available Strategies

#### 1. Decomposition Strategy

**Best for**: Multi-part questions, complex queries

```python
config = ChainOfThoughtConfig(
    reasoning_strategy="decomposition",
    max_reasoning_depth=3
)
```

**How it works**:
- Breaks complex questions into sub-questions
- Solves each sub-question independently
- Combines results into final answer

**Example**:
```
Question: "Compare supervised and unsupervised learning for image recognition"
Step 1: "What is supervised learning?"
Step 2: "What is unsupervised learning?"
Step 3: "How do they differ for image recognition?"
```

#### 2. Iterative Strategy

**Best for**: Refining understanding, exploratory questions

```python
config = ChainOfThoughtConfig(
    reasoning_strategy="iterative",
    max_reasoning_depth=4
)
```

**How it works**:
- Builds understanding incrementally
- Each step refines the previous understanding
- Converges on a comprehensive answer

#### 3. Hierarchical Strategy

**Best for**: Structured analysis, taxonomic questions

```python
config = ChainOfThoughtConfig(
    reasoning_strategy="hierarchical",
    max_reasoning_depth=5
)
```

**How it works**:
- Starts with high-level concepts
- Progressively drills down to specifics
- Maintains hierarchical relationships

#### 4. Causal Strategy

**Best for**: Why/how questions, cause-effect analysis

```python
config = ChainOfThoughtConfig(
    reasoning_strategy="causal",
    max_reasoning_depth=4
)
```

**How it works**:
- Identifies causal relationships
- Traces cause-effect chains
- Explains mechanisms and processes

### Strategy Selection Guidelines

| Question Type | Recommended Strategy | Depth | Example |
|---------------|---------------------|-------|---------|
| Multi-part | decomposition | 3-4 | "Compare A and B, and explain C" |
| Comparison | decomposition | 3 | "What's better: A or B?" |
| Causal | causal | 3-4 | "Why does X happen?" |
| Exploratory | iterative | 4-5 | "Tell me about X" |
| Structured | hierarchical | 4-5 | "Categorize types of X" |
| Definition | decomposition | 2-3 | "What is X and how does it work?" |

## Performance Configuration

### Token Budget Management

Control token usage for cost optimization:

```python
# Conservative: Lower token usage
config = ChainOfThoughtConfig(
    token_budget_multiplier=1.5,
    max_reasoning_depth=2
)

# Balanced: Standard usage
config = ChainOfThoughtConfig(
    token_budget_multiplier=2.0,
    max_reasoning_depth=3
)

# Aggressive: Higher quality, more tokens
config = ChainOfThoughtConfig(
    token_budget_multiplier=3.0,
    max_reasoning_depth=5
)
```

### Quality vs. Speed Trade-offs

#### Speed-Optimized Configuration

```python
speed_config = ChainOfThoughtConfig(
    enabled=True,
    max_reasoning_depth=2,
    reasoning_strategy="decomposition",
    evaluation_threshold=0.5,
    context_preservation=False,
    token_budget_multiplier=1.5
)
```

**Use cases**: Real-time applications, cost-sensitive deployments

#### Quality-Optimized Configuration

```python
quality_config = ChainOfThoughtConfig(
    enabled=True,
    max_reasoning_depth=5,
    reasoning_strategy="hierarchical",
    evaluation_threshold=0.8,
    context_preservation=True,
    token_budget_multiplier=3.0
)
```

**Use cases**: Research applications, critical decision support

#### Balanced Configuration

```python
balanced_config = ChainOfThoughtConfig(
    enabled=True,
    max_reasoning_depth=3,
    reasoning_strategy="decomposition",
    evaluation_threshold=0.6,
    context_preservation=True,
    token_budget_multiplier=2.0
)
```

**Use cases**: General-purpose applications

## Domain-Specific Configurations

### Academic Research

```python
academic_config = ChainOfThoughtConfig(
    enabled=True,
    max_reasoning_depth=5,
    reasoning_strategy="hierarchical",
    evaluation_threshold=0.8,
    token_budget_multiplier=3.0,
    context_preservation=True
)
```

**Features**: Deep analysis, high accuracy, comprehensive source attribution

### Business Intelligence

```python
business_config = ChainOfThoughtConfig(
    enabled=True,
    max_reasoning_depth=3,
    reasoning_strategy="decomposition",
    evaluation_threshold=0.7,
    token_budget_multiplier=2.0
)
```

**Features**: Structured analysis, actionable insights, cost-effective

### Technical Support

```python
support_config = ChainOfThoughtConfig(
    enabled=True,
    max_reasoning_depth=4,
    reasoning_strategy="causal",
    evaluation_threshold=0.6,
    token_budget_multiplier=2.5
)
```

**Features**: Troubleshooting focus, step-by-step guidance

### Content Analysis

```python
content_config = ChainOfThoughtConfig(
    enabled=True,
    max_reasoning_depth=3,
    reasoning_strategy="iterative",
    evaluation_threshold=0.6,
    token_budget_multiplier=2.0
)
```

**Features**: Exploratory analysis, synthesis of multiple sources

## Configuration Validation

### Validation Rules

The system validates configuration parameters:

```python
# This will raise ValidationError
try:
    invalid_config = ChainOfThoughtConfig(
        max_reasoning_depth=0,        # Must be > 0
        evaluation_threshold=-0.1,    # Must be 0.0-1.0
        reasoning_strategy="invalid"  # Must be valid strategy
    )
except ValidationError as e:
    print(f"Configuration errors: {e.errors()}")
```

### Configuration Testing

Test configurations before deployment:

```python
def test_configuration(config: ChainOfThoughtConfig):
    """Test a CoT configuration with sample questions."""
    test_questions = [
        "What is machine learning?",
        "Compare A and B",
        "Why does X cause Y?",
        "Analyze the relationship between X, Y, and Z"
    ]

    results = []
    for question in test_questions:
        # Test with configuration
        result = await cot_service.execute_chain_of_thought(
            ChainOfThoughtInput(
                question=question,
                collection_id=test_collection_id,
                user_id=test_user_id,
                cot_config=config.model_dump()
            )
        )

        results.append({
            "question": question,
            "steps": len(result.reasoning_steps),
            "confidence": result.total_confidence,
            "execution_time": result.total_execution_time,
            "token_usage": result.token_usage
        })

    return results
```

## Dynamic Configuration

### User-Specific Configuration

Configure CoT per user based on preferences:

```python
def get_user_cot_config(user_id: UUID) -> ChainOfThoughtConfig:
    user_prefs = get_user_preferences(user_id)

    if user_prefs.analysis_depth == "deep":
        return ChainOfThoughtConfig(
            max_reasoning_depth=5,
            evaluation_threshold=0.8,
            token_budget_multiplier=3.0
        )
    elif user_prefs.analysis_depth == "quick":
        return ChainOfThoughtConfig(
            max_reasoning_depth=2,
            evaluation_threshold=0.5,
            token_budget_multiplier=1.5
        )
    else:
        return ChainOfThoughtConfig()  # Default
```

### Context-Aware Configuration

Adapt configuration based on question characteristics:

```python
async def get_adaptive_config(question: str) -> ChainOfThoughtConfig:
    classification = await cot_service.classify_question(question)

    if classification.complexity_level == "very_high":
        return ChainOfThoughtConfig(
            max_reasoning_depth=5,
            reasoning_strategy="hierarchical",
            token_budget_multiplier=3.0
        )
    elif classification.question_type == "causal":
        return ChainOfThoughtConfig(
            reasoning_strategy="causal",
            max_reasoning_depth=4
        )
    else:
        return ChainOfThoughtConfig(
            reasoning_strategy="decomposition",
            max_reasoning_depth=3
        )
```

## Best Practices

### Configuration Guidelines

1. **Start Conservative**: Begin with default settings and adjust based on results
2. **Monitor Performance**: Track token usage, execution time, and quality metrics
3. **Domain Adaptation**: Customize configurations for specific use cases
4. **User Feedback**: Incorporate user satisfaction into configuration tuning

### Common Patterns

#### Progressive Enhancement

```python
def get_progressive_config(attempt: int) -> ChainOfThoughtConfig:
    """Increase depth/quality with each retry."""
    configs = [
        ChainOfThoughtConfig(max_reasoning_depth=2, token_budget_multiplier=1.5),
        ChainOfThoughtConfig(max_reasoning_depth=3, token_budget_multiplier=2.0),
        ChainOfThoughtConfig(max_reasoning_depth=4, token_budget_multiplier=2.5),
        ChainOfThoughtConfig(max_reasoning_depth=5, token_budget_multiplier=3.0),
    ]
    return configs[min(attempt, len(configs) - 1)]
```

#### Confidence-Based Adjustment

```python
def adjust_config_by_confidence(config: ChainOfThoughtConfig, confidence: float) -> ChainOfThoughtConfig:
    """Adjust configuration based on previous result confidence."""
    if confidence < 0.5:
        # Increase depth and quality for low confidence
        return ChainOfThoughtConfig(
            **config.model_dump(),
            max_reasoning_depth=config.max_reasoning_depth + 1,
            token_budget_multiplier=config.token_budget_multiplier * 1.2
        )
    return config
```

### Monitoring and Debugging

Enable debug mode for development:

```python
debug_config = ChainOfThoughtConfig(
    # ... other settings ...
    # Enable through environment variable
)

# Set COT_DEBUG_MODE=true in environment
```

Debug information includes:
- Step-by-step reasoning traces
- Source attribution details
- Token usage breakdown
- Performance metrics
- Configuration application logs

This comprehensive configuration system allows fine-tuning of CoT behavior for optimal performance across different use cases and requirements.
