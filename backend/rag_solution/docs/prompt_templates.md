# Prompt Template System

## Overview

The prompt template system provides a flexible way to manage and customize prompts for different LLM providers, with support for validation, context handling, and template types.

## Architecture

### Template Storage Hierarchy

```
PromptTemplate (SQLAlchemy Model)
├── Core Fields
│   ├── id: UUID
│   ├── collection_id: Optional[UUID]
│   ├── name: str
│   ├── provider: str
│   └── template_type: PromptTemplateType
├── Template Content
│   ├── system_prompt: Optional[str]
│   ├── template_format: str
│   └── input_variables: Optional[Dict[str, str]]
├── Validation & Examples
│   ├── validation_schema: Optional[Dict]
│   └── example_inputs: Optional[Dict]
└── Context Handling
    ├── context_strategy: Optional[Dict]
    ├── max_context_length: Optional[int]
    └── stop_sequences: Optional[List[str]]
```

### Template Types

```python
class PromptTemplateType(str, Enum):
    RAG_QUERY = "rag_query"
    QUESTION_GENERATION = "question_generation"
    RESPONSE_EVALUATION = "response_evaluation"
    CUSTOM = "custom"
```

### Context Strategies

```python
class ContextStrategyType(str, Enum):
    CONCATENATE = "concatenate"
    SUMMARIZE = "summarize"
    TRUNCATE = "truncate"
    PRIORITY = "priority"
```

## Configuration

### Template Creation

```python
from rag_solution.schemas.prompt_template_schema import (
    PromptTemplateInput,
    PromptTemplateType,
    ContextStrategyType
)

template = PromptTemplateInput(
    name="rag-query-template",
    provider="watsonx",
    template_type=PromptTemplateType.RAG_QUERY,
    system_prompt="You are a helpful AI assistant.",
    template_format=(
        "Context:\n{context}\n\n"
        "Question: {question}\n\n"
        "Answer:"
    ),
    input_variables={
        "context": "Retrieved passages from knowledge base",
        "question": "User's question to answer"
    },
    validation_schema={
        "type": "object",
        "properties": {
            "context": {"type": "string", "minLength": 1},
            "question": {"type": "string", "minLength": 1}
        },
        "required": ["context", "question"]
    },
    context_strategy={
        "strategy": ContextStrategyType.PRIORITY,
        "max_chunks": 3,
        "chunk_separator": "\n\n",
        "ordering": "relevance"
    },
    example_inputs={
        "simple": {
            "context": "Python was created by Guido van Rossum.",
            "question": "Who created Python?"
        }
    }
)
```

### Context Strategy Configuration

Different strategies for handling context:

```python
# Priority Strategy
{
    "strategy": "priority",
    "max_chunks": 3,
    "ordering": "relevance"
}

# Concatenation Strategy
{
    "strategy": "concatenate",
    "chunk_separator": "\n\n",
    "max_chunks": 5
}

# Truncation Strategy
{
    "strategy": "truncate",
    "max_length": 1000,
    "truncation": "end"  # or "start" or "middle"
}

# Summarization Strategy
{
    "strategy": "summarize",
    "max_length": 1000,
    "style": "extractive"  # or "abstractive"
}
```

## Service Layer Usage

### Template Management

```python
from rag_solution.services.prompt_template_service import PromptTemplateService

# Initialize service
template_service = PromptTemplateService(db)

# Create template
template = template_service.create_template(template_input)

# Get template by type
rag_template = template_service.get_by_type(
    PromptTemplateType.RAG_QUERY,
    collection_id
)

# Format prompt
formatted_prompt = template_service.format_prompt(
    template.id,
    {
        "context": context_text,
        "question": query
    }
)

# Apply context strategy
formatted_context = template_service.apply_context_strategy(
    template.id,
    context_chunks
)
```

### Pipeline Integration

```python
from rag_solution.services.pipeline_service import PipelineService
from rag_solution.services.prompt_template_service import PromptTemplateService

class PipelineService:
    def __init__(self, db: Session):
        self._template_service = PromptTemplateService(db)
        self._evaluator = None
        self._provider = None

    async def initialize(
        self,
        collection_id: UUID,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize pipeline with templates."""
        # Get templates
        self.query_template = self._template_service.get_by_type(
            PromptTemplateType.RAG_QUERY,
            collection_id
        )
        self.eval_template = self._template_service.get_by_type(
            PromptTemplateType.RESPONSE_EVALUATION,
            collection_id
        )

        # Initialize evaluator with template
        self._evaluator = RAGEvaluator(
            provider=self._provider,
            template=self.eval_template
        )

    async def execute_pipeline(
        self,
        search_input: SearchInput,
        user_id: Optional[UUID] = None,
        evaluation_enabled: bool = True
    ) -> PipelineResult:
        """Execute pipeline with template handling."""
        try:
            # Format query template
            formatted_query = self._template_service.format_prompt(
                self.query_template.id,
                {
                    "context": self._get_context(query_results),
                    "question": search_input.question
                }
            )

            # Generate answer
            generated_answer = await self._provider.generate_text(
                formatted_query,
                search_input.metadata
            )

            # Run evaluation if enabled
            evaluation = None
            if evaluation_enabled:
                evaluation = await self._evaluator.evaluate(
                    question=search_input.question,
                    answer=generated_answer,
                    context=self._get_context(query_results)
                )

            return PipelineResult(
                rewritten_query=rewritten_query,
                query_results=query_results,
                generated_answer=generated_answer,
                evaluation=evaluation
            )

        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}")
            return self._create_error_result(str(e))
```

### Template Performance Optimization

```python
class PromptTemplateService:
    def __init__(self, db: Session):
        self._template_repository = PromptTemplateRepository(db)
        self._cache = TemplateCache()

    def format_prompt(
        self,
        template_id: UUID,
        variables: Dict[str, Any],
        use_cache: bool = True
    ) -> str:
        """Format prompt with caching."""
        # Try cache first
        if use_cache:
            cache_key = self._get_cache_key(template_id, variables)
            cached = self._cache.get(cache_key)
            if cached:
                return cached

        # Format prompt
        template = self._template_repository.get_by_id(template_id)
        formatted = template.format_prompt(variables)

        # Cache result
        if use_cache:
            self._cache.set(cache_key, formatted)

        return formatted

    def apply_context_strategy(
        self,
        template_id: UUID,
        context_chunks: List[str],
        max_tokens: Optional[int] = None
    ) -> str:
        """Apply context strategy with token limit."""
        template = self._template_repository.get_by_id(template_id)
        strategy = template.context_strategy

        if strategy["strategy"] == ContextStrategyType.PRIORITY:
            return self._apply_priority_strategy(
                context_chunks,
                strategy,
                max_tokens
            )
        elif strategy["strategy"] == ContextStrategyType.SUMMARIZE:
            return self._apply_summarize_strategy(
                context_chunks,
                strategy,
                max_tokens
            )
        # ... other strategies
```

## Error Handling

The system provides specific exceptions:

```python
from core.custom_exceptions import (
    ValidationError,
    NotFoundError,
    ConfigurationError
)

try:
    # Format prompt
    formatted_prompt = template_service.format_prompt(
        template_id,
        variables
    )
except ValidationError as e:
    # Handle validation errors
    logger.error(f"Template validation failed: {str(e)}")
except NotFoundError as e:
    # Handle missing template
    logger.error(f"Template not found: {str(e)}")
except ConfigurationError as e:
    # Handle configuration errors
    logger.error(f"Configuration error: {str(e)}")
```

## Best Practices

1. Template Management:
   - Use appropriate template types
   - Validate inputs with schemas
   - Provide example inputs
   - Document template purposes

2. Context Handling:
   - Choose appropriate strategies
   - Configure chunk limits
   - Consider token limits
   - Test with different content

3. Error Handling:
   - Use custom exceptions
   - Validate inputs early
   - Log errors appropriately
   - Provide helpful messages

4. Service Integration:
   - Use dependency injection
   - Initialize services properly
   - Handle async operations
   - Clean up resources

## Future Improvements

1. Template Features:
   - Version control and history
   - Template inheritance and composition
   - Dynamic validation with feedback
   - Real-time performance metrics
   - A/B testing support
   - Template analytics
   - Auto-optimization

2. Context Handling:
   - Advanced context strategies
   - ML-based summarization
   - Dynamic chunk optimization
   - Context relevance scoring
   - Token optimization
   - Cross-reference support
   - Context caching

3. Service Enhancements:
   - Distributed caching
   - Bulk operations
   - Template migration tools
   - Usage analytics
   - Performance monitoring
   - Error tracking
   - Auto-scaling

4. Performance Optimization:
   - Template compilation
   - Caching strategies
   - Batch processing
   - Token optimization
   - Response streaming
   - Async processing
   - Load balancing

5. Integration Features:
   - Provider-specific optimizations
   - Custom strategy support
   - Template marketplace
   - Testing tools
   - Monitoring dashboards
   - Documentation generation
   - CI/CD integration

6. Template Management:
   - UI-based editor
   - Version control
   - Template sharing
   - Access control
   - Validation tools
   - Testing suite
   - Documentation
