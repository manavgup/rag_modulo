# Provider Configuration System

## Overview

The provider configuration system enables dynamic registration and management of LLM providers and their models. It provides a flexible way to configure and manage different LLM providers with their specific parameters, active status, and verification tracking.

## Service Layer Architecture

### Core Services

```python
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.provider_config_service import ProviderConfigService

# Initialize services
provider_service = LLMProviderService(db)
parameters_service = LLMParametersService(db)
config_service = ProviderConfigService(db)
```

### Provider Configuration

```python
from rag_solution.schemas.provider_config_schema import ProviderConfigInput

# Create provider configuration
config = ProviderConfigInput(
    provider="watsonx",
    api_key="your-api-key",
    api_url="https://api.watsonx.ibm.com",
    project_id="your-project-id",
    active=True,
    parameters={
        "concurrency_limit": 5,
        "timeout": 60,
        "batch_size": 20
    }
)

# Register provider
provider_config = config_service.create_provider_config(config)
```

### LLM Parameters

```python
from rag_solution.schemas.llm_parameters_schema import LLMParametersInput

# Create LLM parameters
parameters = LLMParametersInput(
    name="watsonx-default",
    provider="watsonx",
    model_id="granite-13b",
    temperature=0.7,
    top_p=0.95,
    top_k=50,
    max_new_tokens=1000,
    min_new_tokens=1,
    repetition_penalty=1.1,
    stop_sequences=["User:", "Assistant:"]
)

# Register parameters
llm_parameters = parameters_service.create_parameters(parameters)
```

## Provider Integration

### Provider Service Usage

```python
# Get provider instance
provider = provider_service.get_provider_by_name("watsonx")

# Generate text
response = provider.generate_text(
    prompt="Your prompt here",
    model_parameters=llm_parameters
)

# Generate embeddings
embeddings = provider.generate_embeddings(
    texts=["Text to embed"],
    model_parameters=llm_parameters
)
```

### Pipeline Integration

```python
from rag_solution.services.pipeline_service import PipelineService
from rag_solution.services.prompt_template_service import PromptTemplateService

# Initialize services
pipeline_service = PipelineService(db)
template_service = PromptTemplateService(db)

# Configure pipeline with templates
pipeline_config = PipelineConfigInput(
    name="default-pipeline",
    provider_id=provider.id,
    llm_parameters_id=llm_parameters.id,
    evaluator_config={
        "enabled": True,
        "metrics": ["relevance", "coherence", "factuality"],
        "threshold": 0.8
    },
    performance_config={
        "max_concurrent_requests": 10,
        "timeout_seconds": 30,
        "batch_size": 5
    },
    retrieval_config={
        "top_k": 3,
        "similarity_threshold": 0.7,
        "reranking_enabled": True
    }
)

# Create pipeline configuration
pipeline = pipeline_service.create_pipeline_config(pipeline_config)

# Initialize pipeline with templates
await pipeline_service.initialize(
    collection_id=collection_id,
    config_overrides={
        "max_concurrent_requests": 20,
        "timeout_seconds": 45
    }
)

# Execute pipeline with evaluation
result = await pipeline_service.execute_pipeline(
    search_input=SearchInput(
        question="What is RAG?",
        collection_id=collection_id,
        metadata={
            "max_length": 100,
            "temperature": 0.7
        }
    ),
    user_id=user_id,
    evaluation_enabled=True
)

# Access metrics
metrics = pipeline_service.get_performance_metrics()
print(f"Average latency: {metrics.avg_latency_ms}ms")
print(f"Success rate: {metrics.success_rate}%")
print(f"Throughput: {metrics.requests_per_second} req/s")
```

### Provider Performance Monitoring

```python
class LLMProviderService:
    def __init__(self, db: Session):
        self._metrics = ProviderMetrics()
        self._cache = ResponseCache()

    async def generate_text(
        self,
        prompt: str,
        model_parameters: LLMParameters,
        use_cache: bool = True
    ) -> str:
        """Generate text with performance monitoring."""
        # Try cache first
        if use_cache:
            cached = self._cache.get(prompt, model_parameters)
            if cached:
                self._metrics.record_cache_hit()
                return cached

        # Track metrics
        start_time = time.time()
        try:
            response = await self._generate_text_internal(
                prompt,
                model_parameters
            )
            self._metrics.record_success(time.time() - start_time)

            # Cache response
            if use_cache:
                self._cache.set(prompt, model_parameters, response)

            return response

        except Exception as e:
            self._metrics.record_error(str(e))
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get provider performance metrics."""
        return {
            "latency": self._metrics.get_average_latency(),
            "success_rate": self._metrics.get_success_rate(),
            "error_rate": self._metrics.get_error_rate(),
            "cache_hit_rate": self._metrics.get_cache_hit_rate(),
            "requests_per_second": self._metrics.get_throughput()
        }
```

## Error Handling

### Custom Exceptions

```python
from core.custom_exceptions import (
    ConfigurationError,
    ValidationError,
    ProviderError,
    NotFoundError
)

try:
    # Get provider
    provider = provider_service.get_provider_by_name("watsonx")

    # Get parameters
    parameters = parameters_service.get_parameters(parameters_id)

    # Generate text
    response = provider.generate_text(
        prompt=prompt,
        model_parameters=parameters
    )
except ConfigurationError as e:
    # Handle configuration errors
    logger.error(f"Configuration error: {str(e)}")
except ValidationError as e:
    # Handle validation errors
    logger.error(f"Validation error: {str(e)}")
except ProviderError as e:
    # Handle provider-specific errors
    logger.error(f"Provider error: {str(e)}")
except NotFoundError as e:
    # Handle not found errors
    logger.error(f"Not found error: {str(e)}")
```

### Error Types

```python
PROVIDER_ERROR_TYPES = {
    # Initialization Errors
    "INIT_FAILED": "initialization_failed",
    "AUTH_FAILED": "authentication_failed",
    "CONFIG_INVALID": "configuration_invalid",

    # Runtime Errors
    "RATE_LIMIT": "rate_limit_exceeded",
    "TIMEOUT": "request_timeout",
    "API_ERROR": "api_error",

    # Generation Errors
    "PROMPT_ERROR": "prompt_preparation_failed",
    "TEMPLATE_ERROR": "template_formatting_failed",
    "PARAM_ERROR": "invalid_parameters",

    # Resource Errors
    "MODEL_ERROR": "model_not_available",
    "RESOURCE_ERROR": "resource_exhausted",

    # Response Errors
    "RESPONSE_ERROR": "invalid_response",
    "PARSING_ERROR": "response_parsing_failed"
}
```

## Best Practices

1. Service Initialization:
   - Use dependency injection
   - Initialize services properly
   - Handle database sessions

2. Configuration Management:
   - Use service layer for all operations
   - Validate configurations early
   - Handle provider-specific requirements

3. Error Handling:
   - Use custom exceptions
   - Log errors with context
   - Provide clear error messages

4. Resource Management:
   - Clean up resources
   - Handle async operations
   - Monitor usage limits

## Security Considerations

1. API Key Management:
   - Store keys securely
   - Rotate keys regularly
   - Use environment variables

2. Access Control:
   - Implement RBAC
   - Audit configuration changes
   - Monitor usage patterns

3. Error Handling:
   - Sanitize error messages
   - Log security events
   - Handle sensitive data

## Future Improvements

1. Configuration Management:
   - Dynamic configuration updates
   - Configuration versioning
   - Validation rules
   - A/B testing support
   - Environment-specific configs
   - Configuration inheritance
   - Auto-optimization

2. Performance Monitoring:
   - Real-time metrics dashboard
   - Performance alerts
   - Resource utilization tracking
   - Bottleneck detection
   - Query optimization
   - Cache hit ratios
   - Error rate monitoring
   - Latency tracking

3. Provider Optimization:
   - Load balancing
   - Request batching
   - Response streaming
   - Token optimization
   - Concurrent request handling
   - Circuit breakers
   - Rate limiting
   - Request queuing

4. Security Enhancements:
   - Enhanced encryption at rest
   - Key rotation automation
   - Fine-grained access policies
   - Comprehensive audit logging
   - Security scanning
   - Compliance reporting
   - Data anonymization
   - Access monitoring

5. Integration Features:
   - Provider-specific optimizations
   - Custom handler support
   - Automated testing
   - CI/CD integration
   - Health checks
   - Documentation generation
   - Monitoring dashboards
   - Performance profiling

6. Caching & Storage:
   - Distributed caching
   - Response caching
   - Token optimization
   - Cache invalidation
   - Cache warming
   - Storage optimization
   - Backup strategies
   - Data retention
