# Configuration Management

## Service Layer Architecture

The configuration system is built on a service-based architecture with multiple specialized services:

```python
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.provider_config_service import ProviderConfigService
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.services.pipeline_service import PipelineService
```

## Configuration Types

### 1. Environment Configuration
Essential settings loaded from environment variables:

```bash
# Authentication
JWT_SECRET_KEY=your-secure-jwt-secret-key

# WatsonX.ai Credentials
WATSONX_INSTANCE_ID=your-watsonx-instance-id
WATSONX_APIKEY=your-watsonx-key
WATSONX_URL=https://bam-api.res.ibm.com

# Infrastructure
VECTOR_DB=milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Database
COLLECTIONDB_USER=rag_modulo_user
COLLECTIONDB_PASS=rag_modulo_password
COLLECTIONDB_HOST=localhost
```

### 2. Runtime Configuration
Configuration managed through services:

```python
# LLM Parameters Configuration
parameters = LLMParametersInput(
    name="watsonx-default",
    provider="watsonx",
    model_id="granite-13b",
    temperature=0.7,
    max_new_tokens=1000
)
parameters_service.create_parameters(parameters)

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

# Pipeline Configuration
pipeline_config = PipelineConfigInput(
    name="default-pipeline",
    provider_id=provider.id,
    llm_parameters_id=parameters.id
)
pipeline_service.create_pipeline_config(pipeline_config)
```

## Service Integration

### Provider Service Usage

```python
# Initialize services
db = SessionLocal()
provider_service = LLMProviderService(db)
parameters_service = LLMParametersService(db)

# Get provider and parameters
provider = provider_service.get_provider_by_name("watsonx")
parameters = parameters_service.get_parameters(parameters_id)

# Generate text
response = provider.generate_text(
    prompt="Your prompt",
    model_parameters=parameters
)
```

### Pipeline Service Configuration

```python
# Pipeline Service Configuration
pipeline_config = PipelineConfigInput(
    name="default-pipeline",
    provider_id=provider.id,
    llm_parameters_id=parameters.id,
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
pipeline_service.create_pipeline_config(pipeline_config)

# Pipeline Service Usage
pipeline_service = PipelineService(db)

# Initialize with configuration
await pipeline_service.initialize(
    collection_id=collection_id,
    config_overrides={
        "max_concurrent_requests": 20,
        "timeout_seconds": 45
    }
)

# Execute pipeline with runtime options
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

# Access pipeline metrics
metrics = pipeline_service.get_performance_metrics()
print(f"Average latency: {metrics.avg_latency_ms}ms")
print(f"Success rate: {metrics.success_rate}%")
print(f"Throughput: {metrics.requests_per_second} req/s")
```

## Error Handling

```python
from core.custom_exceptions import (
    ConfigurationError,
    ValidationError,
    NotFoundError
)

try:
    # Get configuration
    provider = provider_service.get_provider_by_name("watsonx")
    parameters = parameters_service.get_parameters(parameters_id)
    template = template_service.get_by_type(PromptTemplateType.RAG_QUERY)

except ConfigurationError as e:
    logger.error(f"Configuration error: {str(e)}")
except ValidationError as e:
    logger.error(f"Validation error: {str(e)}")
except NotFoundError as e:
    logger.error(f"Not found error: {str(e)}")
```

## Migration Strategy

### Phase 1: Service Migration (Current)
- Move configuration to specialized services
- Implement repository pattern
- Add validation schemas
- Support async operations

### Phase 2: Runtime Configuration
- All configuration in database
- Service-based management
- API endpoints for configuration
- UI for configuration management

### Phase 3: Legacy Removal
- Remove legacy configuration
- Update all services
- Clean up old code
- Update documentation

## Best Practices

1. Service Usage:
   - Use dependency injection
   - Initialize services properly
   - Handle database sessions
   - Clean up resources

2. Configuration Management:
   - Use service layer for all operations
   - Validate configurations early
   - Handle provider-specific requirements
   - Document configuration changes

3. Error Handling:
   - Use custom exceptions
   - Log errors with context
   - Provide clear error messages
   - Handle validation errors

4. Security:
   - Store sensitive data securely
   - Use environment variables
   - Implement access control
   - Audit configuration changes

## Testing

```bash
# Run configuration tests
pytest backend/tests/test_core_config.py
pytest backend/tests/test_provider_config.py
pytest backend/tests/test_llm_parameters.py
pytest backend/tests/test_prompt_template.py

# Run integration tests
pytest backend/tests/integration/test_configuration_flow.py
pytest backend/tests/integration/test_configuration_errors.py
```

## Development Notes

1. Adding New Configuration:
   - Create appropriate service
   - Implement repository pattern
   - Add validation schemas
   - Update documentation

2. Using Configuration:
   - Always use service layer
   - Handle all error cases
   - Log configuration access
   - Clean up resources

3. Security Considerations:
   - Validate all inputs
   - Sanitize outputs
   - Handle sensitive data
   - Implement access control

4. Performance:
   - Use caching where appropriate
   - Optimize database queries
   - Handle concurrent access
   - Monitor performance

## Future Improvements

1. Configuration Features:
   - Version control for configurations
   - Configuration inheritance and overrides
   - Dynamic validation with schemas
   - Real-time performance metrics
   - A/B testing support
   - Configuration rollback
   - Environment-specific configs

2. Service Enhancements:
   - Distributed caching layer
   - Bulk operations optimization
   - Migration and backup tools
   - Usage analytics and insights
   - Auto-scaling support
   - Circuit breakers
   - Rate limiting
   - Request queuing

3. Performance Monitoring:
   - Real-time metrics dashboard
   - Performance alerts
   - Resource utilization tracking
   - Bottleneck detection
   - Query optimization
   - Cache hit ratios
   - Error rate monitoring
   - Latency tracking

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
   - UI configuration management
   - RESTful API endpoints
   - Monitoring dashboards
   - Testing utilities
   - CI/CD integration
   - Deployment automation
   - Health checks
   - Documentation generation

6. Pipeline Optimizations:
   - Dynamic resource allocation
   - Parallel processing
   - Request batching
   - Response caching
   - Error recovery
   - Load balancing
   - Failover handling
   - Performance tuning
