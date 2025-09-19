# CoT API Reference

Complete API reference for the Chain of Thought system, including all classes, methods, parameters, and return values.

## Core Classes

### ChainOfThoughtService

Main orchestration service for CoT reasoning.

#### Constructor

```python
def __init__(
    self,
    settings: Settings | None = None,
    llm_service: Any = None,
    search_service: Any = None,
    db: Session | None = None
) -> None
```

**Parameters:**
- `settings`: Application settings instance (default: creates new Settings())
- `llm_service`: LLM service instance for answer generation
- `search_service`: Search service instance for context retrieval
- `db`: Database session for persistence

#### Methods

##### `classify_question(question: str) -> QuestionClassification`

Analyzes question complexity and determines if CoT is needed.

**Parameters:**
- `question` (str): User's input question

**Returns:**
- `QuestionClassification`: Classification result with type, complexity, and CoT recommendation

**Example:**
```python
classification = await cot_service.classify_question("Compare machine learning and deep learning")
print(f"Type: {classification.question_type}")  # "comparison"
print(f"Requires CoT: {classification.requires_cot}")  # True
```

##### `execute_chain_of_thought(cot_input: ChainOfThoughtInput, context_documents: list[str] | None = None) -> ChainOfThoughtOutput`

Executes the complete CoT reasoning pipeline.

**Parameters:**
- `cot_input` (ChainOfThoughtInput): Input configuration and question
- `context_documents` (list[str] | None): Optional context documents

**Returns:**
- `ChainOfThoughtOutput`: Complete reasoning results

**Raises:**
- `ValidationError`: Invalid input configuration
- `LLMProviderError`: LLM service failures
- `TimeoutError`: Execution timeout exceeded

**Example:**
```python
cot_input = ChainOfThoughtInput(
    question="Why is the sky blue?",
    collection_id=uuid4(),
    user_id=uuid4()
)

result = await cot_service.execute_chain_of_thought(cot_input)
print(f"Answer: {result.final_answer}")
print(f"Steps: {len(result.reasoning_steps)}")
```

##### `execute_reasoning_step(step_number: int, question: str, context: list[str], previous_answers: list[str]) -> ReasoningStep`

Executes a single reasoning step.

**Parameters:**
- `step_number` (int): Step number (1-based)
- `question` (str): Question for this step
- `context` (list[str]): Context documents
- `previous_answers` (list[str]): Previous step answers

**Returns:**
- `ReasoningStep`: Step result with answer and metadata

**Raises:**
- `LLMProviderError`: LLM service failure

**Example:**
```python
step = await cot_service.execute_reasoning_step(
    step_number=1,
    question="What is machine learning?",
    context=["Machine learning is a subset of AI..."],
    previous_answers=[]
)
print(f"Answer: {step.intermediate_answer}")
print(f"Confidence: {step.confidence_score}")
```

##### `decompose_question(question: str, max_depth: int = 3) -> Any`

Decomposes complex question into sub-questions.

**Parameters:**
- `question` (str): Question to decompose
- `max_depth` (int): Maximum decomposition depth

**Returns:**
- Decomposition result with sub_questions list

##### `synthesize_answer(original_question: str, reasoning_steps: list[ReasoningStep]) -> str`

Synthesizes final answer from reasoning steps.

**Parameters:**
- `original_question` (str): Original user question
- `reasoning_steps` (list[ReasoningStep]): Completed reasoning steps

**Returns:**
- `str`: Final synthesized answer

#### Properties

##### `question_decomposer: QuestionDecomposer`

Lazy-initialized question decomposer instance.

##### `answer_synthesizer: AnswerSynthesizer`

Lazy-initialized answer synthesizer instance.

##### `source_attribution_service: SourceAttributionService`

Lazy-initialized source attribution service instance.

### SourceAttributionService

Service for tracking document sources used in reasoning.

#### Constructor

```python
def __init__(self) -> None
```

Initializes empty source cache for deduplication.

#### Methods

##### `create_source_attribution(**kwargs) -> SourceAttribution`

Creates structured source attribution object.

**Parameters:**
- `document_id` (str): Unique document identifier
- `relevance_score` (float): Relevance score (0.0-1.0)
- `document_title` (str | None): Document title
- `excerpt` (str | None): Relevant text excerpt
- `chunk_index` (int | None): Chunk index within document
- `retrieval_rank` (int | None): Original retrieval ranking

**Returns:**
- `SourceAttribution`: Created attribution object

**Example:**
```python
attribution = service.create_source_attribution(
    document_id="doc_123",
    relevance_score=0.85,
    document_title="Machine Learning Guide",
    excerpt="Machine learning algorithms can be categorized...",
    retrieval_rank=1
)
```

##### `extract_sources_from_context(context_documents: List[str], search_results: Optional[List[Dict[str, Any]]] = None) -> List[SourceAttribution]`

Extracts source attributions from context or search results.

**Parameters:**
- `context_documents` (List[str]): Raw context document strings
- `search_results` (Optional[List[Dict[str, Any]]]): Structured search results

**Returns:**
- `List[SourceAttribution]`: List of extracted attributions

**Example:**
```python
# From structured search results
search_results = [
    {
        "document_id": "doc_1",
        "title": "AI Introduction",
        "score": 0.92,
        "content": "Artificial intelligence involves..."
    }
]
attributions = service.extract_sources_from_context([], search_results)

# From raw context strings
context = ["id:doc_1 AI content here...", "More AI information..."]
attributions = service.extract_sources_from_context(context)
```

##### `aggregate_sources_across_steps(reasoning_steps: List[ReasoningStep]) -> SourceSummary`

Aggregates sources from all reasoning steps.

**Parameters:**
- `reasoning_steps` (List[ReasoningStep]): Steps with source attributions

**Returns:**
- `SourceSummary`: Aggregated source information

**Example:**
```python
summary = service.aggregate_sources_across_steps([step1, step2, step3])
print(f"Total sources: {len(summary.all_sources)}")
print(f"Primary sources: {len(summary.primary_sources)}")
print(f"Step breakdown: {summary.source_usage_by_step}")
```

##### `enhance_reasoning_step_with_sources(step: ReasoningStep, retrieved_documents: Optional[List[Dict[str, Any]]] = None) -> ReasoningStep`

Adds source attributions to reasoning step.

**Parameters:**
- `step` (ReasoningStep): Step to enhance
- `retrieved_documents` (Optional[List[Dict[str, Any]]]): Retrieved documents for this step

**Returns:**
- `ReasoningStep`: Enhanced step with source attributions

##### `format_sources_for_display(source_summary: SourceSummary, include_excerpts: bool = True) -> Dict[str, Any]`

Formats sources for UI display.

**Parameters:**
- `source_summary` (SourceSummary): Summary to format
- `include_excerpts` (bool): Whether to include text excerpts

**Returns:**
- `Dict[str, Any]`: UI-friendly formatted source information

### QuestionDecomposer

Service for breaking down complex questions.

#### Constructor

```python
def __init__(self, settings: Settings) -> None
```

**Parameters:**
- `settings`: Application settings

#### Methods

##### `decompose(question: str, max_depth: int = 3) -> QuestionDecomposition`

Decomposes question into sub-questions.

**Parameters:**
- `question` (str): Question to decompose
- `max_depth` (int): Maximum decomposition depth

**Returns:**
- Question decomposition with sub_questions list

**Decomposition Strategies:**
- Multi-part questions: Split on conjunctions
- Comparison questions: Create definition + comparison steps
- Causal questions: Create why → how → impact chains

### AnswerSynthesizer

Service for combining reasoning step results.

#### Constructor

```python
def __init__(self, settings: Settings) -> None
```

#### Methods

##### `synthesize(original_question: str, reasoning_steps: List[ReasoningStep]) -> str`

Synthesizes final answer from steps.

**Parameters:**
- `original_question` (str): Original question
- `reasoning_steps` (List[ReasoningStep]): Completed reasoning steps

**Returns:**
- `str`: Final synthesized answer

## Data Models

### ChainOfThoughtInput

Input schema for CoT requests.

```python
class ChainOfThoughtInput(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    collection_id: UUID4 = Field(..., description="Collection ID")
    user_id: UUID4 = Field(..., description="User ID")
    cot_config: Optional[Dict[str, Any]] = Field(None, description="CoT configuration")
    context_metadata: Optional[Dict[str, Any]] = Field(None, description="Context metadata")
```

### ChainOfThoughtOutput

Output schema for CoT results.

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

**Validation:**
- `total_confidence`: 0.0-1.0
- `token_usage`: > 0 if specified
- `total_execution_time`: > 0 if specified

### ChainOfThoughtConfig

Configuration schema for CoT behavior.

```python
class ChainOfThoughtConfig(BaseModel):
    enabled: bool = Field(default=False, description="Whether CoT is enabled")
    max_reasoning_depth: int = Field(default=3, description="Maximum reasoning steps")
    reasoning_strategy: str = Field(default="decomposition", description="Strategy: decomposition, iterative, hierarchical, causal")
    context_preservation: bool = Field(default=True, description="Preserve context across steps")
    token_budget_multiplier: float = Field(default=2.0, description="Token budget multiplier")
    evaluation_threshold: float = Field(default=0.6, description="Evaluation threshold")
```

**Validation:**
- `max_reasoning_depth`: > 0
- `token_budget_multiplier`: > 0
- `evaluation_threshold`: 0.0-1.0
- `reasoning_strategy`: One of ["decomposition", "iterative", "hierarchical", "causal"]

### QuestionClassification

Question analysis result.

```python
class QuestionClassification(BaseModel):
    question_type: str = Field(..., description="Type of question")
    complexity_level: str = Field(..., description="Complexity level")
    requires_cot: bool = Field(..., description="Whether CoT is needed")
    estimated_steps: Optional[int] = Field(None, description="Estimated reasoning steps")
    confidence: Optional[float] = Field(None, description="Classification confidence")
    reasoning: Optional[str] = Field(None, description="Classification reasoning")
```

**Validation:**
- `question_type`: One of ["simple", "multi_part", "comparison", "causal", "complex_analytical"]
- `complexity_level`: One of ["low", "medium", "high", "very_high"]
- `confidence`: 0.0-1.0 if specified
- `estimated_steps`: > 0 if specified

### ReasoningStep

Individual reasoning step result.

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

### SourceAttribution

Source document attribution.

```python
class SourceAttribution(BaseModel):
    document_id: str = Field(..., description="Unique identifier for the source document")
    document_title: Optional[str] = Field(None, description="Title or name of the source document")
    relevance_score: float = Field(..., description="Relevance score for this source (0-1)")
    excerpt: Optional[str] = Field(None, description="Relevant excerpt from the source")
    chunk_index: Optional[int] = Field(None, description="Index of the chunk within the document")
    retrieval_rank: Optional[int] = Field(None, description="Rank in the retrieval results")
```

### SourceSummary

Aggregated source information.

```python
class SourceSummary(BaseModel):
    all_sources: List[SourceAttribution] = Field(default_factory=list, description="All unique sources used")
    primary_sources: List[SourceAttribution] = Field(default_factory=list, description="Most influential sources")
    source_usage_by_step: Dict[int, List[str]] = Field(default_factory=dict, description="Sources used by each step")
```

## Error Handling

### Custom Exceptions

#### LLMProviderError

Raised when LLM service operations fail.

```python
class LLMProviderError(Exception):
    def __init__(self, provider: str, error_type: str = None, message: str = None, operation: str | None = None, details: dict[str, Any] | None = None)
```

**Parameters:**
- `provider`: LLM provider name
- `error_type`: Type of error (optional)
- `message`: Error message (optional)
- `operation`: Failed operation (optional)
- `details`: Additional error details (optional)

#### ValidationError

Raised for configuration validation failures.

```python
class ValidationError(Exception):
    def __init__(self, field: str, value: Any, message: str)
```

**Parameters:**
- `field`: Field that failed validation
- `value`: Invalid value
- `message`: Validation error message

### Error Examples

```python
try:
    result = await cot_service.execute_chain_of_thought(invalid_input)
except ValidationError as e:
    print(f"Configuration error: {e.message}")
except LLMProviderError as e:
    print(f"LLM error: {e.message}")
except TimeoutError as e:
    print(f"Execution timeout: {e}")
```

## Integration Examples

### With Search Service

```python
class SearchService:
    def __init__(self, cot_service: ChainOfThoughtService):
        self.cot_service = cot_service

    async def search_with_cot(self, search_input: SearchInput) -> SearchOutput:
        # Check if CoT should be used
        classification = await self.cot_service.classify_question(search_input.question)

        if classification.requires_cot:
            # Execute CoT reasoning
            cot_input = ChainOfThoughtInput(
                question=search_input.question,
                collection_id=search_input.collection_id,
                user_id=search_input.user_id,
                cot_config=search_input.config_metadata.get("cot_config")
            )

            cot_result = await self.cot_service.execute_chain_of_thought(cot_input)

            return SearchOutput(
                answer=cot_result.final_answer,
                sources=cot_result.source_summary.primary_sources,
                confidence=cot_result.total_confidence,
                reasoning_trace=cot_result.reasoning_steps
            )
        else:
            # Regular search
            return await self.regular_search(search_input)
```

### With FastAPI

```python
from fastapi import FastAPI, HTTPException
from rag_solution.schemas.chain_of_thought_schema import ChainOfThoughtInput, ChainOfThoughtOutput

app = FastAPI()

@app.post("/cot/execute", response_model=ChainOfThoughtOutput)
async def execute_cot(cot_input: ChainOfThoughtInput):
    try:
        result = await cot_service.execute_chain_of_thought(cot_input)
        return result
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LLMProviderError as e:
        raise HTTPException(status_code=502, detail=f"LLM service error: {e}")
```

### Testing Support

```python
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_cot_service():
    mock_llm = Mock()
    mock_search = Mock()
    return ChainOfThoughtService(
        settings=test_settings,
        llm_service=mock_llm,
        search_service=mock_search
    )

async def test_cot_execution(mock_cot_service):
    cot_input = ChainOfThoughtInput(
        question="Test question",
        collection_id=uuid4(),
        user_id=uuid4()
    )

    result = await mock_cot_service.execute_chain_of_thought(cot_input)

    assert result.final_answer is not None
    assert len(result.reasoning_steps) > 0
    assert result.total_confidence >= 0.0
```

## Performance Monitoring

### Metrics Collection

```python
def collect_cot_metrics(result: ChainOfThoughtOutput) -> Dict[str, Any]:
    return {
        "execution_time": result.total_execution_time,
        "token_usage": result.token_usage,
        "steps_count": len(result.reasoning_steps),
        "confidence_score": result.total_confidence,
        "sources_count": len(result.source_summary.all_sources) if result.source_summary else 0,
        "avg_step_confidence": sum(s.confidence_score for s in result.reasoning_steps) / len(result.reasoning_steps) if result.reasoning_steps else 0
    }
```

This comprehensive API reference covers all public interfaces and usage patterns for the Chain of Thought system.
