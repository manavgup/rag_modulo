# RAG Solution Development Guide

## Project Overview
This is a highly configurable RAG (Retrieval Augmented Generation) solution built with Python, focusing on IBM watsonx integration. The system follows a service-based architecture with repository pattern implementation.

## Core Development Principles

### Service Layer Architecture
```python
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

class BaseService:
    """Base class for all services."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self._initialize_dependencies()

    def _initialize_dependencies(self) -> None:
        """Initialize service dependencies."""
        pass

class ExampleService(BaseService):
    """Example service demonstrating architecture."""

    def __init__(self, db: Session):
        """Initialize service with dependencies."""
        super().__init__(db)
        self._repository: Optional[ExampleRepository] = None

    @property
    def repository(self) -> ExampleRepository:
        """Lazy initialization of repository."""
        if self._repository is None:
            self._repository = ExampleRepository(self.db)
        return self._repository
```

### Service Integration
```python
# Service initialization
db = SessionLocal()
provider_service = LLMProviderService(db)
parameters_service = LLMParametersService(db)
template_service = PromptTemplateService(db)

# Get provider and parameters
provider = provider_service.get_provider_by_name("watsonx")
parameters = parameters_service.get_parameters(parameters_id)

# Create template
template = template_service.create_template(
    PromptTemplateInput(
        name="example-template",
        provider="watsonx",
        template_type=PromptTemplateType.RAG_QUERY,
        template_format="Context:\n{context}\nQuestion:{question}"
    )
)
```

### Error Handling
```python
from core.custom_exceptions import (
    ValidationError,
    NotFoundError,
    ConfigurationError
)

try:
    # Service operations
    provider = provider_service.get_provider_by_name("watsonx")
    parameters = parameters_service.get_parameters(parameters_id)
    template = template_service.get_by_type(PromptTemplateType.RAG_QUERY)

except ValidationError as e:
    logger.error(f"Validation error: {str(e)}")
except NotFoundError as e:
    logger.error(f"Not found error: {str(e)}")
except ConfigurationError as e:
    logger.error(f"Configuration error: {str(e)}")
```

## Component Guidelines

### Pipeline Service
```python
class PipelineService(BaseService):
    """Service for managing RAG pipelines."""

    def __init__(self, db: Session):
        """Initialize pipeline service."""
        super().__init__(db)
        self._pipeline_repository: Optional[PipelineRepository] = None
        self._provider_service: Optional[LLMProviderService] = None
        self._template_service: Optional[PromptTemplateService] = None
        self._parameters_service: Optional[LLMParametersService] = None
        self._evaluator: Optional[RAGEvaluator] = None

    async def initialize(self, collection_id: UUID) -> None:
        """Initialize pipeline components."""
        # Initialize services
        self._initialize_services()

        # Get configuration
        config = await self._get_pipeline_config(collection_id)

        # Initialize components
        self.provider = self.provider_service.get_provider_by_name(config.provider)
        self.parameters = self.parameters_service.get_parameters(config.parameters_id)
        self.template = self.template_service.get_by_type(
            PromptTemplateType.RAG_QUERY,
            collection_id
        )

        # Initialize evaluator
        self._evaluator = RAGEvaluator(
            provider=self.provider,
            parameters=self.parameters
        )

    async def execute_pipeline(
        self,
        search_input: SearchInput,
        user_id: Optional[UUID] = None
    ) -> PipelineResult:
        """Execute RAG pipeline with error handling and evaluation."""
        try:
            # Rewrite query
            rewritten_query = await self.query_rewriter.rewrite(
                search_input.question
            )

            # Retrieve relevant documents
            query_results = await self.retriever.search(
                rewritten_query,
                search_input.collection_id,
                search_input.metadata
            )

            # Generate answer
            generated_answer = await self._generate_answer(
                rewritten_query,
                query_results,
                search_input.metadata
            )

            # Evaluate result
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
            return PipelineResult(
                rewritten_query="",
                query_results=[],
                generated_answer="",
                evaluation={"error": str(e)}
            )
```

### Question Service
```python
class QuestionService(BaseService):
    """Service for managing question suggestions."""

    def __init__(
        self,
        db: Session,
        provider: LLMProvider,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize question service."""
        super().__init__(db)
        self.provider = provider
        self.config = config or {}
        self._question_repository: Optional[QuestionRepository] = None
        self._template_service: Optional[PromptTemplateService] = None

    async def suggest_questions(
        self,
        texts: List[str],
        collection_id: UUID,
        num_questions: Optional[int] = None
    ) -> List[str]:
        """Generate questions from texts."""
        # Get template
        template = self.template_service.get_by_type(
            PromptTemplateType.QUESTION_GENERATION,
            collection_id
        )

        # Format prompt
        formatted_prompt = self.template_service.format_prompt(
            template.id,
            {
                "context": "\n\n".join(texts),
                "num_questions": str(num_questions or self.num_questions)
            }
        )

        # Generate questions
        questions = await self._generate_questions(
            formatted_prompt,
            template
        )

        return questions
```

### Template Service
```python
class PromptTemplateService(BaseService):
    """Service for managing prompt templates."""

    def __init__(self, db: Session):
        """Initialize template service."""
        super().__init__(db)
        self._template_repository: Optional[PromptTemplateRepository] = None

    def get_by_type(
        self,
        template_type: PromptTemplateType,
        collection_id: Optional[UUID] = None
    ) -> Optional[PromptTemplate]:
        """Get template by type."""
        return self.template_repository.get_by_type(
            template_type,
            collection_id
        )

    def format_prompt(
        self,
        template_id: UUID,
        variables: Dict[str, Any]
    ) -> str:
        """Format prompt with variables."""
        template = self.template_repository.get_by_id(template_id)
        if not template:
            raise NotFoundError(f"Template {template_id} not found")

        return template.format_prompt(variables)
```

## Testing Guidelines

### Test Organization

1. Unit Tests
   ```python
   # Service tests
   class TestPipelineService:
       """Tests for PipelineService."""

       @pytest.fixture
       def pipeline_service(self, db_session: Session) -> PipelineService:
           """Create pipeline service."""
           return PipelineService(db_session)

       @pytest.mark.asyncio
       async def test_pipeline_initialization(self, pipeline_service: PipelineService):
           """Test pipeline initialization."""
           await pipeline_service.initialize(UUID("test-id"))
           assert pipeline_service.provider is not None
           assert pipeline_service.parameters is not None
           assert pipeline_service.template is not None

   # Repository tests
   class TestPipelineRepository:
       """Tests for PipelineRepository."""

       def test_create_pipeline(self, db_session: Session):
           """Test pipeline creation."""
           repo = PipelineRepository(db_session)
           pipeline = repo.create(PipelineCreate(...))
           assert pipeline.id is not None
   ```

2. Integration Tests
   ```python
   @pytest.mark.integration
   class TestPipelineFlow:
       """Integration tests for pipeline flow."""

       @pytest.mark.asyncio
       async def test_complete_pipeline_flow(
           self,
           pipeline_service: PipelineService,
           test_collection: Collection,
           test_documents: List[Document]
       ):
           """Test complete pipeline flow."""
           # Initialize pipeline
           await pipeline_service.initialize(test_collection.id)

           # Execute pipeline
           result = await pipeline_service.execute_pipeline(
               SearchInput(
                   question="Test question",
                   collection_id=test_collection.id
               )
           )

           # Verify complete flow
           assert result.rewritten_query != ""
           assert len(result.query_results) > 0
           assert result.generated_answer != ""
           assert result.evaluation is not None
   ```

3. Performance Tests
   ```python
   @pytest.mark.performance
   class TestPipelinePerformance:
       """Performance tests for pipeline."""

       @pytest.mark.asyncio
       async def test_pipeline_throughput(
           self,
           pipeline_service: PipelineService,
           test_collection: Collection
       ):
           """Test pipeline throughput."""
           # Configure test
           num_requests = 50
           concurrent_requests = 10

           # Execute concurrent requests
           start_time = time.time()
           results = await asyncio.gather(*[
               pipeline_service.execute_pipeline(
                   SearchInput(
                       question=f"Question {i}",
                       collection_id=test_collection.id
                   )
               )
               for i in range(num_requests)
           ])
           end_time = time.time()

           # Calculate metrics
           execution_time = end_time - start_time
           throughput = num_requests / execution_time
           success_rate = len([r for r in results if r.generated_answer]) / num_requests

           # Assert performance requirements
           assert throughput >= 1.0  # 1 request per second minimum
           assert success_rate >= 0.95  # 95% success rate minimum
   ```

4. Error Tests
   ```python
   @pytest.mark.asyncio
   async def test_pipeline_error_handling(
       self,
       pipeline_service: PipelineService,
       test_collection: Collection
   ):
       """Test pipeline error handling."""
       # Break provider
       pipeline_service.provider.client = None

       # Execute pipeline
       result = await pipeline_service.execute_pipeline(
           SearchInput(
               question="Test question",
               collection_id=test_collection.id
           )
       )

       # Verify error handling
       assert result.generated_answer == ""
       assert result.evaluation is not None
       assert "error" in result.evaluation
   ```

## Configuration Management

### Environment Configuration
```bash
# Authentication
JWT_SECRET_KEY=your-secure-jwt-secret-key

# WatsonX.ai Credentials
WATSONX_INSTANCE_ID=your-watsonx-instance-id
WATSONX_APIKEY=your-watsonx-key
WATSONX_URL=https://bam-api.res.ibm.com
```

### Runtime Configuration
```python
# Provider Configuration
provider_config = ProviderConfigInput(
    provider="watsonx",
    api_key="${WATSONX_APIKEY}",
    project_id="${WATSONX_INSTANCE_ID}",
    active=True
)
config_service.create_provider_config(provider_config)

# Template Configuration
template = PromptTemplateInput(
    name="rag-query",
    provider="watsonx",
    template_type=PromptTemplateType.RAG_QUERY,
    template_format="Context:\n{context}\nQuestion:{question}"
)
template_service.create_template(template)
```

## Best Practices

1. Service Layer:
   - Use dependency injection
   - Initialize services properly
   - Handle database sessions
   - Clean up resources
   - Follow repository pattern
   - Use async/await properly
   - Handle service dependencies
   - Implement proper error handling

2. Error Handling:
   - Use custom exceptions
   - Log errors with context
   - Provide clear messages
   - Handle all cases
   - Implement graceful fallbacks
   - Monitor error rates
   - Add error tracing
   - Document error scenarios

3. Testing:
   - Write comprehensive tests
   - Follow test organization
   - Include performance tests
   - Test error scenarios
   - Monitor test coverage
   - Use test fixtures properly
   - Document test scenarios
   - Maintain test data

4. Performance:
   - Monitor throughput
   - Track latency
   - Handle concurrency
   - Optimize resource usage
   - Set performance baselines
   - Regular benchmarking
   - Load testing
   - Stress testing

5. Documentation:
   - Document services
   - Document APIs
   - Document configuration
   - Keep docs updated
   - Include examples
   - Document best practices
   - Add troubleshooting guides
   - Maintain changelog

Remember:
- Follow service pattern
- Use dependency injection
- Handle errors properly
- Write comprehensive tests
- Document everything
- Monitor performance
- Regular maintenance
- Security first
