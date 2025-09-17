# Question Suggestion

The question suggestion feature automatically generates relevant questions from document content using the RAG pipeline and WatsonX LLM.

## Quick Start

```python
from sqlalchemy.orm import Session
from rag_solution.services.question_service import QuestionService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.schemas.prompt_template_schema import PromptTemplateType

# Initialize services
db: Session = SessionLocal()
provider_service = LLMProviderService(db)
template_service = PromptTemplateService(db)

# Get provider and template
provider = provider_service.get_provider_by_name("watsonx")
template = template_service.get_by_type(PromptTemplateType.QUESTION_GENERATION)

# Initialize question service
question_service = QuestionService(db, provider)

# Generate questions from collection
questions = await question_service.suggest_questions(
    texts=["Your text content here"],
    collection_id=collection_id,
    num_questions=5
)

print(f"Generated Questions: {questions}")
```

## Configuration

### Core Settings

The question service uses settings from `core.config`:

```python
# Question generation settings
question_suggestion_num: int = Field(default=5)
question_min_length: int = Field(default=15)
question_max_length: int = Field(default=150)

# Question types and patterns
question_types: List[str] = Field(
    default=[
        "What is",
        "How does",
        "Why is",
        "When should",
        "Which factors"
    ]
)
```

### Template Configuration

Question generation uses prompt templates:

```python
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType

template = PromptTemplateInput(
    name="question-generation",
    provider="watsonx",
    template_type=PromptTemplateType.QUESTION_GENERATION,
    system_prompt="You are a helpful AI assistant.",
    template_format=(
        "Based on this context:\n{context}\n\n"
        "Generate {num_questions} specific, well-formed questions."
    ),
    input_variables={
        "context": "The text content to generate questions from",
        "num_questions": "Number of questions to generate"
    },
    validation_schema={
        "type": "object",
        "properties": {
            "context": {"type": "string", "minLength": 1},
            "num_questions": {"type": "string", "pattern": "^[0-9]+$"}
        },
        "required": ["context", "num_questions"]
    },
    context_strategy={
        "strategy": "priority",
        "max_chunks": 3,
        "chunk_separator": "\n\n",
        "ordering": "relevance"
    }
)

# Create template
template_service.create_template(template)
```

## Features

### Context Handling

The service supports different context strategies:

```python
# Priority strategy (default)
context_strategy = {
    "strategy": "priority",
    "max_chunks": 3,
    "ordering": "relevance"
}

# Concatenation strategy
context_strategy = {
    "strategy": "concatenate",
    "chunk_separator": "\n\n"
}

# Summarization strategy
context_strategy = {
    "strategy": "summarize",
    "max_length": 1000
}
```

### Question Validation

Generated questions are validated against:

1. Length Constraints:
   - Minimum length
   - Maximum length
   - Question mark

2. Pattern Matching:
   - Must start with configured patterns
   - Must be properly formatted
   - Must be unique

3. Content Requirements:
   - Required terms (if specified)
   - Relevance to content
   - Proper formatting

## Error Handling

The service handles errors with custom exceptions:

```python
from core.custom_exceptions import ValidationError, NotFoundError

try:
    questions = await question_service.suggest_questions(
        texts=texts,
        collection_id=collection_id
    )
except ValidationError as e:
    # Handle validation errors (e.g., invalid inputs)
    print(f"Validation error: {str(e)}")
except NotFoundError as e:
    # Handle not found errors (e.g., missing template)
    print(f"Not found error: {str(e)}")
except Exception as e:
    # Handle other errors
    print(f"Error generating questions: {str(e)}")
```

## Integration

### Service Layer Integration

```python
# Initialize services
db = SessionLocal()
provider_service = LLMProviderService(db)
template_service = PromptTemplateService(db)

# Get provider
provider = provider_service.get_provider_by_name("watsonx")

# Create question service
question_service = QuestionService(
    db=db,
    provider=provider,
    config={
        'num_questions': 5,
        'min_length': 10,
        'max_length': 100
    }
)

# Generate questions
questions = await question_service.suggest_questions(
    texts=texts,
    collection_id=collection_id
)
```

### Pipeline Integration

The question service integrates with the pipeline service:

```python
from rag_solution.services.pipeline_service import PipelineService

# Initialize pipeline service
pipeline_service = PipelineService(db)

# Initialize pipeline for collection
await pipeline_service.initialize(collection_name)

# Generate questions using pipeline
result = await pipeline_service.execute_pipeline(
    search_input=search_input,
    user_id=user_id
)
```

## Testing

1. Service Tests:
```bash
# Run service tests
pytest backend/tests/services/test_question_service.py
```

2. Integration Tests:
```bash
# Run integration tests
pytest backend/tests/integration/test_question_generation_flow.py
```

3. Template Tests:
```bash
# Run template tests
pytest backend/tests/test_prompt_template.py
```

## Best Practices

1. Service Initialization:
   - Use dependency injection
   - Initialize services properly
   - Close database sessions

2. Template Management:
   - Use typed templates
   - Validate inputs
   - Handle context properly

3. Error Handling:
   - Use custom exceptions
   - Provide clear error messages
   - Log errors appropriately

4. Resource Management:
   - Clean up resources
   - Use async/await properly
   - Handle database sessions

## Support

For issues or questions:
1. Check service configuration
2. Verify template setup
3. Check error messages
4. Review input validation
5. Test with minimal examples

## API Reference

### QuestionService

```python
class QuestionService:
    def __init__(
        self,
        db: Session,
        provider: LLMProvider,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize question service."""
        pass

    async def suggest_questions(
        self,
        texts: List[str],
        collection_id: UUID,
        num_questions: Optional[int] = None
    ) -> List[str]:
        """Generate questions from texts."""
        pass

    def get_collection_questions(
        self,
        collection_id: UUID
    ) -> List[str]:
        """Get stored questions for collection."""
        pass

    async def regenerate_questions(
        self,
        collection_id: UUID,
        texts: List[str],
        num_questions: Optional[int] = None
    ) -> List[str]:
        """Regenerate questions for collection."""
        pass
