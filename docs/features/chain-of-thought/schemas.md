# CoT Schemas and Data Models

This document provides detailed information about all Pydantic schemas and data models used in the Chain of Thought system.

## Overview

The CoT system uses strongly-typed Pydantic models for:

- **Input validation**: Ensuring data integrity at API boundaries
- **Configuration management**: Type-safe configuration handling
- **Data serialization**: Consistent JSON serialization/deserialization
- **Documentation**: Self-documenting schema with field descriptions
- **Testing**: Reliable test fixtures and data generation

All schemas include comprehensive field validation and descriptive error messages.

## Input/Output Schemas

### ChainOfThoughtInput

Input schema for initiating CoT reasoning.

```python
class ChainOfThoughtInput(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    collection_id: UUID4 = Field(..., description="Collection ID")
    user_id: UUID4 = Field(..., description="User ID")
    cot_config: Optional[Dict[str, Any]] = Field(None, description="CoT configuration")
    context_metadata: Optional[Dict[str, Any]] = Field(None, description="Context metadata")
```

**Field Details:**
- **question**: User's input question (required, non-empty)
- **collection_id**: UUID of the document collection to search
- **user_id**: UUID of the requesting user
- **cot_config**: Optional runtime configuration overrides
- **context_metadata**: Additional context information

**Usage Example:**
```python
cot_input = ChainOfThoughtInput(
    question="Compare supervised and unsupervised learning approaches",
    collection_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
    user_id=UUID("987fcdeb-51d2-43a1-b123-456789abcdef"),
    cot_config={
        "max_reasoning_depth": 4,
        "reasoning_strategy": "comparison",
        "evaluation_threshold": 0.75
    }
)
```

### ChainOfThoughtOutput

Comprehensive output from CoT reasoning process.

```python
class ChainOfThoughtOutput(BaseModel):
    original_question: str = Field(..., description="Original user question")
    final_answer: str = Field(..., description="Final synthesized answer")
    reasoning_steps: List[ReasoningStep] = Field(default_factory=list, description="Reasoning steps taken")
    source_summary: Optional[SourceSummary] = Field(None, description="Summary of source attributions")
    total_confidence: float = Field(default=0.0, description="Overall confidence score")
    token_usage: Optional[int] = Field(None, description="Total tokens used")
    total_execution_time: Optional[float] = Field(None, description="Total execution time")
    reasoning_strategy: Optional[str] = Field(None, description="Strategy used")
```

**Validation Rules:**
- `total_confidence`: Must be between 0.0 and 1.0
- `token_usage`: Must be positive if specified
- `total_execution_time`: Must be positive if specified

**Usage Example:**
```python
output = ChainOfThoughtOutput(
    original_question="Compare supervised and unsupervised learning",
    final_answer="Supervised learning uses labeled data while unsupervised learning...",
    reasoning_steps=[step1, step2, step3],
    source_summary=source_summary,
    total_confidence=0.87,
    token_usage=1250,
    total_execution_time=3.2,
    reasoning_strategy="comparison"
)
```

## Configuration Schemas

### ChainOfThoughtConfig

Configuration parameters for CoT reasoning behavior.

```python
class ChainOfThoughtConfig(BaseModel):
    enabled: bool = Field(default=False, description="Whether CoT is enabled")
    max_reasoning_depth: int = Field(default=3, description="Maximum reasoning steps")
    reasoning_strategy: str = Field(
        default="decomposition",
        description="Strategy: decomposition, iterative, hierarchical, causal"
    )
    context_preservation: bool = Field(default=True, description="Preserve context across steps")
    token_budget_multiplier: float = Field(default=2.0, description="Token budget multiplier")
    evaluation_threshold: float = Field(default=0.6, description="Evaluation threshold")
```

**Field Validation:**
- `max_reasoning_depth`: Must be > 0
- `token_budget_multiplier`: Must be > 0
- `evaluation_threshold`: Must be between 0.0 and 1.0
- `reasoning_strategy`: Must be one of ["decomposition", "iterative", "hierarchical", "causal"]

**Strategy Descriptions:**
- **decomposition**: Break complex questions into sub-questions
- **iterative**: Build understanding through iterative refinement
- **hierarchical**: Use hierarchical reasoning from general to specific
- **causal**: Follow causal chains of reasoning

**Configuration Examples:**
```python
# Conservative configuration
conservative_config = ChainOfThoughtConfig(
    enabled=True,
    max_reasoning_depth=2,
    reasoning_strategy="decomposition",
    evaluation_threshold=0.8
)

# Aggressive configuration
aggressive_config = ChainOfThoughtConfig(
    enabled=True,
    max_reasoning_depth=5,
    reasoning_strategy="hierarchical",
    token_budget_multiplier=3.0,
    evaluation_threshold=0.5
)
```

## Process Schemas

### QuestionClassification

Classification of questions to determine CoT applicability.

```python
class QuestionClassification(BaseModel):
    question_type: str = Field(..., description="Type of question")
    complexity_level: str = Field(..., description="Complexity level")
    requires_cot: bool = Field(..., description="Whether CoT is needed")
    estimated_steps: Optional[int] = Field(None, description="Estimated reasoning steps")
    confidence: Optional[float] = Field(None, description="Classification confidence")
    reasoning: Optional[str] = Field(None, description="Classification reasoning")
```

**Validation Rules:**
- `question_type`: Must be one of ["simple", "multi_part", "comparison", "causal", "complex_analytical"]
- `complexity_level`: Must be one of ["low", "medium", "high", "very_high"]
- `confidence`: Must be between 0.0 and 1.0 if specified
- `estimated_steps`: Must be > 0 if specified

**Classification Matrix:**

| Question Type | Complexity Level | Requires CoT | Estimated Steps |
|---------------|------------------|--------------|-----------------|
| simple | low | False | 1 |
| multi_part | medium | True | 2-3 |
| comparison | high | True | 3-4 |
| causal | high | True | 3-4 |
| complex_analytical | very_high | True | 4-5 |

### DecomposedQuestion

Individual sub-question in the reasoning chain.

```python
class DecomposedQuestion(BaseModel):
    sub_question: str = Field(..., description="The sub-question")
    reasoning_step: int = Field(..., description="Step number in reasoning chain")
    dependency_indices: List[int] = Field(default_factory=list, description="Dependencies on other steps")
    question_type: Optional[str] = Field(None, description="Type of question")
    complexity_score: float = Field(default=0.5, description="Complexity score 0-1")
```

**Validation Rules:**
- `reasoning_step`: Must be > 0
- `complexity_score`: Must be between 0.0 and 1.0
- `question_type`: Must be one of ["definition", "comparison", "causal", "procedural", "analytical"] if specified

**Example Decomposition:**
```python
decomposed = [
    DecomposedQuestion(
        sub_question="What is supervised learning?",
        reasoning_step=1,
        question_type="definition",
        complexity_score=0.3
    ),
    DecomposedQuestion(
        sub_question="What is unsupervised learning?",
        reasoning_step=2,
        question_type="definition",
        complexity_score=0.3
    ),
    DecomposedQuestion(
        sub_question="How do supervised and unsupervised learning differ?",
        reasoning_step=3,
        dependency_indices=[1, 2],
        question_type="comparison",
        complexity_score=0.7
    )
]
```

### ReasoningStep

Individual step in the reasoning chain with results and metadata.

```python
class ReasoningStep(BaseModel):
    step_number: int = Field(..., description="Step number")
    question: str = Field(..., description="Question for this step")
    context_used: List[str] = Field(default_factory=list, description="Context documents used (legacy)")
    source_attributions: List[SourceAttribution] = Field(default_factory=list, description="Structured source attributions")
    intermediate_answer: Optional[str] = Field(None, description="Intermediate answer")
    confidence_score: Optional[float] = Field(default=0.0, description="Confidence score 0-1")
    reasoning_trace: Optional[str] = Field(None, description="Reasoning trace")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
```

**Validation Rules:**
- `step_number`: Must be > 0
- `confidence_score`: Must be between 0.0 and 1.0 if specified
- `execution_time`: Must be > 0 if specified

**Example Step:**
```python
step = ReasoningStep(
    step_number=1,
    question="What is supervised learning?",
    source_attributions=[attribution1, attribution2],
    intermediate_answer="Supervised learning is a machine learning approach...",
    confidence_score=0.85,
    reasoning_trace="Step 1: Analyzing definition of supervised learning",
    execution_time=1.2
)
```

## Source Attribution Schemas

### SourceAttribution

Attribution information for individual source documents.

```python
class SourceAttribution(BaseModel):
    document_id: str = Field(..., description="Unique identifier for the source document")
    document_title: Optional[str] = Field(None, description="Title or name of the source document")
    relevance_score: float = Field(..., description="Relevance score for this source (0-1)")
    excerpt: Optional[str] = Field(None, description="Relevant excerpt from the source")
    chunk_index: Optional[int] = Field(None, description="Index of the chunk within the document")
    retrieval_rank: Optional[int] = Field(None, description="Rank in the retrieval results")
```

**Validation Rules:**
- `relevance_score`: Must be between 0.0 and 1.0

**Example Attribution:**
```python
attribution = SourceAttribution(
    document_id="ml_textbook_ch3",
    document_title="Machine Learning Textbook - Chapter 3: Supervised Learning",
    relevance_score=0.92,
    excerpt="Supervised learning algorithms learn from labeled training data to make predictions...",
    chunk_index=0,
    retrieval_rank=1
)
```

### SourceSummary

Aggregated source information across the reasoning chain.

```python
class SourceSummary(BaseModel):
    all_sources: List[SourceAttribution] = Field(default_factory=list, description="All unique sources used")
    primary_sources: List[SourceAttribution] = Field(default_factory=list, description="Most influential sources")
    source_usage_by_step: Dict[int, List[str]] = Field(default_factory=dict, description="Sources used by each step")
```

**Usage Patterns:**

```python
# Access all sources
for source in summary.all_sources:
    print(f"Source: {source.document_title} (relevance: {source.relevance_score})")

# Access primary sources for display
primary_display = [
    {
        "title": source.document_title,
        "relevance": f"{source.relevance_score:.1%}",
        "excerpt": source.excerpt[:100] + "..."
    }
    for source in summary.primary_sources
]

# Access step-by-step breakdown
for step_num, doc_ids in summary.source_usage_by_step.items():
    print(f"Step {step_num} used {len(doc_ids)} sources: {', '.join(doc_ids)}")
```

## Serialization and Validation

### JSON Serialization

All schemas support JSON serialization for API responses:

```python
# Serialize to JSON
output_json = cot_output.model_dump_json()

# Deserialize from JSON
parsed_output = ChainOfThoughtOutput.model_validate_json(output_json)
```

### Field Validation

Schemas include comprehensive field validation:

```python
# This will raise ValidationError
try:
    invalid_config = ChainOfThoughtConfig(
        max_reasoning_depth=-1,  # Invalid: must be > 0
        evaluation_threshold=1.5,  # Invalid: must be <= 1.0
        reasoning_strategy="invalid"  # Invalid: not in allowed list
    )
except ValidationError as e:
    print(f"Validation errors: {e.errors()}")
```

### Custom Validators

Advanced validation using Pydantic validators:

```python
@field_validator("relevance_score")
def validate_relevance_score(cls, v):
    if v < 0 or v > 1:
        raise ValueError("relevance_score must be between 0 and 1")
    return v

@field_validator("reasoning_strategy")
def validate_strategy(cls, v):
    valid_strategies = ["decomposition", "iterative", "hierarchical", "causal"]
    if v not in valid_strategies:
        raise ValueError(f"reasoning_strategy must be one of {valid_strategies}")
    return v
```

## Testing Support

### Factory Functions

Schemas can be used with factory functions for testing:

```python
def create_test_cot_input(**kwargs):
    defaults = {
        "question": "Test question",
        "collection_id": UUID("123e4567-e89b-12d3-a456-426614174000"),
        "user_id": UUID("987fcdeb-51d2-43a1-b123-456789abcdef")
    }
    defaults.update(kwargs)
    return ChainOfThoughtInput(**defaults)

# Usage in tests
def test_cot_execution():
    test_input = create_test_cot_input(
        question="Compare A and B",
        cot_config={"max_reasoning_depth": 2}
    )
    # ... test logic
```

### Mock Data Generation

Schemas support mock data generation for testing:

```python
def create_mock_reasoning_step(step_number: int = 1):
    return ReasoningStep(
        step_number=step_number,
        question=f"Mock question {step_number}",
        intermediate_answer=f"Mock answer {step_number}",
        confidence_score=0.8,
        execution_time=1.0
    )
```

## Error Handling

### Validation Errors

Schemas provide detailed validation error messages:

```python
try:
    invalid_step = ReasoningStep(
        step_number=0,  # Invalid
        question=""     # Invalid
    )
except ValidationError as e:
    for error in e.errors():
        print(f"Field: {error['loc']}, Error: {error['msg']}")
```

### Custom Error Messages

Field validators include descriptive error messages:

```python
# Example validation error output:
{
    "loc": ["max_reasoning_depth"],
    "msg": "max_reasoning_depth must be greater than 0",
    "type": "value_error"
}
```

## Schema Evolution

### Backward Compatibility

Schemas are designed with backward compatibility in mind:

- Optional fields have default values
- New fields are added as optional
- Deprecated fields are marked but not removed immediately

### Migration Support

```python
# Handle legacy data formats
def migrate_legacy_reasoning_step(legacy_data: dict) -> ReasoningStep:
    # Convert old context format to new source attribution format
    if "context_used" in legacy_data and not legacy_data.get("source_attributions"):
        # Convert context strings to basic attributions
        attributions = []
        for i, context in enumerate(legacy_data["context_used"]):
            attribution = SourceAttribution(
                document_id=f"legacy_context_{i}",
                relevance_score=0.5,
                excerpt=context[:200]
            )
            attributions.append(attribution)
        legacy_data["source_attributions"] = attributions

    return ReasoningStep(**legacy_data)
```

This comprehensive schema system provides type safety, validation, and documentation while maintaining flexibility for future enhancements to the CoT system.
