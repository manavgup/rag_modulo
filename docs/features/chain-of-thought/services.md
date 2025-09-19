# CoT Services Documentation

This document provides detailed information about the core services that power the Chain of Thought reasoning system.

## ChainOfThoughtService

The main orchestration service that coordinates the entire CoT reasoning process.

### Class Definition

```python
class ChainOfThoughtService:
    def __init__(self, settings: Settings | None = None, llm_service: Any = None, search_service: Any = None, db: Session | None = None) -> None
```

### Key Methods

#### `classify_question(question: str) -> QuestionClassification`

Analyzes a question to determine if CoT reasoning is needed and estimates the complexity.

**Parameters:**
- `question`: The user's input question

**Returns:**
- `QuestionClassification` object with:
  - `question_type`: Type classification (simple, multi_part, comparison, causal, complex_analytical)
  - `complexity_level`: Complexity assessment (low, medium, high, very_high)
  - `requires_cot`: Boolean indicating if CoT should be used
  - `estimated_steps`: Expected number of reasoning steps
  - `confidence`: Classification confidence score (0-1)

**Classification Logic:**
```python
# Multi-part detection
has_multiple_parts = any(word in question_lower for word in [" and ", " or ", " but ", " however "])

# Comparison detection
has_comparison = any(word in question_lower for word in ["compare", "differ", "versus", "vs", "better"])

# Causal reasoning detection
has_causal = any(word in question_lower for word in ["why", "how", "cause", "reason", "explain"])
```

#### `execute_chain_of_thought(cot_input: ChainOfThoughtInput, context_documents: list[str] | None = None) -> ChainOfThoughtOutput`

Executes the complete CoT reasoning pipeline.

**Parameters:**
- `cot_input`: CoT configuration and input data
- `context_documents`: Optional retrieved documents for context

**Returns:**
- `ChainOfThoughtOutput` with complete reasoning chain and results

**Process Flow:**
1. Validate configuration and check if CoT is enabled
2. Decompose question into sub-questions
3. Execute reasoning steps sequentially
4. Synthesize final answer from intermediate results
5. Generate source attribution summary
6. Calculate confidence and performance metrics

#### `execute_reasoning_step(step_number: int, question: str, context: list[str], previous_answers: list[str]) -> ReasoningStep`

Executes a single reasoning step in the chain.

**Parameters:**
- `step_number`: Current step number (1-based)
- `question`: Question for this specific step
- `context`: Context documents available
- `previous_answers`: Answers from previous steps

**Returns:**
- `ReasoningStep` with intermediate answer and metadata

**Features:**
- Integrates with LLM services for answer generation
- Tracks execution time per step
- Calculates confidence scores based on context availability
- Handles LLM service failures gracefully
- Enhances steps with source attributions

#### `decompose_question(question: str, max_depth: int = 3) -> Any`

Delegates to QuestionDecomposer for breaking down complex questions.

#### `synthesize_answer(original_question: str, reasoning_steps: list[ReasoningStep]) -> str`

Delegates to AnswerSynthesizer for final answer generation.

### Properties

#### `question_decomposer: QuestionDecomposer`
Lazy-initialized QuestionDecomposer instance.

#### `answer_synthesizer: AnswerSynthesizer`
Lazy-initialized AnswerSynthesizer instance.

#### `source_attribution_service: SourceAttributionService`
Lazy-initialized SourceAttributionService instance.

### Error Handling

The service handles various error conditions:

```python
# LLM service failures
try:
    await self.llm_service.generate_response(question, full_context)
except Exception as e:
    if hasattr(e, '__class__') and 'LLMProviderError' in str(type(e)):
        raise  # Re-raise LLMProviderError as-is
    raise LLMProviderError(
        provider="chain_of_thought",
        error_type="reasoning_step",
        message=f"Failed to execute reasoning step: {str(e)}"
    ) from e

# Configuration validation
try:
    return ChainOfThoughtConfig(**cot_input.cot_config)
except Exception as e:
    if isinstance(e, PydanticValidationError):
        raise ValidationError(
            field="cot_config",
            value=cot_input.cot_config,
            message=str(e)
        ) from e
```

## QuestionDecomposer

Handles the decomposition of complex questions into manageable sub-questions.

### Key Methods

#### `decompose(question: str, max_depth: int = 3) -> QuestionDecomposition`

Breaks down questions using various strategies:

**Decomposition Strategies:**
- **Multi-part questions**: Split on conjunctions ("and", "or", "but")
- **Comparison questions**: Generate definition + comparison steps
- **Causal questions**: Create why → how → impact chains
- **Complex analytical**: Break into components and analysis

**Example Decomposition:**
```python
# Input: "Compare machine learning and deep learning for image recognition"
# Output:
[
    "What is machine learning?",
    "What is deep learning?",
    "How do machine learning and deep learning differ for image recognition?"
]
```

### Complexity Scoring

Questions are scored on complexity (0-1) based on:
- Word count and sentence structure
- Presence of technical terms
- Number of concepts involved
- Logical relationships required

## AnswerSynthesizer

Combines intermediate answers from reasoning steps into coherent final responses.

### Key Methods

#### `synthesize(original_question: str, reasoning_steps: list[ReasoningStep]) -> str`

**Synthesis Strategies:**
- **Single step**: Direct passthrough for simple cases
- **Multi-step**: Combines insights from multiple reasoning steps
- **Context preservation**: Maintains logical flow between steps
- **Confidence weighting**: Prioritizes higher-confidence steps

**Synthesis Logic:**
```python
if len(reasoning_steps) == 1:
    return reasoning_steps[0].intermediate_answer

# Multi-step synthesis
answers = [step.intermediate_answer for step in reasoning_steps if step.intermediate_answer]
if not answers:
    return "Unable to provide a comprehensive answer based on the available information."

# Combine with context preservation
combined_insights = ". ".join(answers)
return f"Based on the analysis: {combined_insights}"
```

## SourceAttributionService

Tracks and manages source document attributions throughout the reasoning process.

### Key Methods

#### `create_source_attribution(document_id: str, relevance_score: float, ...) -> SourceAttribution`

Creates structured source attribution objects.

#### `extract_sources_from_context(context_documents: List[str], search_results: Optional[List[Dict[str, Any]]]) -> List[SourceAttribution]`

Extracts source attributions from context or structured search results.

#### `aggregate_sources_across_steps(reasoning_steps: List[ReasoningStep]) -> SourceSummary`

Aggregates source usage across all reasoning steps, identifying:
- All unique sources used
- Primary sources (highest relevance)
- Step-by-step source usage breakdown

#### `enhance_reasoning_step_with_sources(step: ReasoningStep, retrieved_documents: Optional[List[Dict[str, Any]]]) -> ReasoningStep`

Enhances reasoning steps with source attribution information.

### Source Deduplication

The service automatically deduplicates sources across steps:

```python
# Track unique sources and update with highest relevance score
if attribution.document_id not in all_sources:
    all_sources[attribution.document_id] = attribution
else:
    existing = all_sources[attribution.document_id]
    if attribution.relevance_score > existing.relevance_score:
        all_sources[attribution.document_id] = attribution
```

## Service Integration

### Dependency Injection

All services support dependency injection for testing and flexibility:

```python
# Production setup
cot_service = ChainOfThoughtService(
    settings=app_settings,
    llm_service=llm_provider,
    search_service=search_service,
    db=database_session
)

# Testing setup
cot_service = ChainOfThoughtService(
    settings=test_settings,
    llm_service=mock_llm,
    search_service=mock_search
)
```

### Lazy Initialization

Services use lazy initialization to improve startup performance:

```python
@property
def question_decomposer(self) -> QuestionDecomposer:
    if self._question_decomposer is None:
        self._question_decomposer = QuestionDecomposer(self.settings)
    return self._question_decomposer
```

### Async/Await Support

All core methods support asynchronous execution:

```python
# Async execution
result = await cot_service.execute_chain_of_thought(cot_input)

# Individual steps
step = await cot_service.execute_reasoning_step(1, question, context, [])
```

## Performance Considerations

### Token Budget Management

The system tracks and manages token usage:

```python
# Estimate token usage
token_usage = len(question.split()) * 10 + len(reasoning_steps) * 100

# Apply budget multiplier from configuration
actual_budget = base_budget * config.token_budget_multiplier
```

### Execution Time Tracking

Each reasoning step tracks its execution time:

```python
start_time = time.time()
# ... reasoning logic ...
step.execution_time = time.time() - start_time
```

### Confidence Thresholds

Steps below confidence thresholds can be filtered:

```python
# Only include high-confidence steps
valid_steps = [s for s in reasoning_steps if s.confidence_score >= config.evaluation_threshold]
```

## Testing Support

Services are designed with comprehensive testing in mind:

- Mock-friendly interfaces
- Configurable behavior for testing scenarios
- Detailed error reporting
- Isolated functionality for unit testing

Example test setup:
```python
@pytest.fixture
def mock_cot_service():
    mock_llm = Mock()
    mock_search = Mock()
    return ChainOfThoughtService(
        settings=test_settings,
        llm_service=mock_llm,
        search_service=mock_search
    )
```