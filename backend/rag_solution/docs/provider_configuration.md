# Provider Configuration System

## Overview

The provider configuration system enables dynamic registration and management of LLM providers and their models. It provides a flexible way to configure and manage different LLM providers with their specific parameters, active status, and verification tracking.

## Configuration Types

### 1. Provider Configuration
Managed by provider_config_service, these are essential configurations required for provider initialization:

```python
# Example Provider Configuration
watsonx_config = provider_config_service.get_provider_config("watsonx")
if not watsonx_config:
    raise LLMProviderError(
        provider="watsonx",
        error_type=PROVIDER_ERROR_TYPES["CONFIG_INVALID"],
        message="No configuration found for WatsonX provider"
    )
```

Provider-specific requirements:
- WatsonX: api_key, api_url, project_id
- OpenAI: api_key, org_id
- Anthropic: api_key

### 2. Runtime Configuration
Managed through ProviderConfig, these settings control runtime behavior:

```python
runtime_config = ProviderConfig(
    concurrency_limit=5,
    timeout=60,
    batch_size=20,
    stream=True,
    rate_limit=20,
    retry_attempts=3,
    retry_delay=1.0
)
```

Settings include:
- concurrency_limit: Maximum concurrent requests
- timeout: Request timeout in seconds
- batch_size: Size of batches for bulk operations
- stream: Whether to use streaming mode
- rate_limit: Maximum requests per second
- retry_attempts: Number of retry attempts
- retry_delay: Delay between retries in seconds

## Architecture

### Configuration Storage Hierarchy

```
ProviderModelConfig (SQLAlchemy Model)
├── Provider Configuration
│   ├── Provider name
│   ├── Model ID
│   ├── Active status
│   └── Verification status
└── LLM Parameters (Foreign Key)
    ├── Model parameters
    ├── Token limits
    └── Temperature settings
```

### Components

1. **Model (ProviderModelConfig)**
   - SQLAlchemy model for database storage
   - Links to LLM parameters
   - Status tracking
   - Verification timestamps

2. **Schema**
   - `ProviderModelConfigBase`: Common fields and validation
   - `ProviderModelConfigCreate`: Creation schema
   - `ProviderModelConfigUpdate`: Partial update support
   - `ProviderModelConfigResponse`: API response format

3. **Repository**
   - CRUD operations
   - Provider-specific queries
   - Status management
   - Verification tracking

4. **Service**
   - Business logic
   - Provider registration
   - Model verification
   - Parameter management

## Error Handling

The system provides standardized error types for consistent error handling across providers:

### Error Categories

1. Initialization Errors
```python
PROVIDER_ERROR_TYPES = {
    "INIT_FAILED": "initialization_failed",
    "AUTH_FAILED": "authentication_failed",
    "CONFIG_INVALID": "configuration_invalid"
}
```

2. Runtime Errors
```python
PROVIDER_ERROR_TYPES = {
    "RATE_LIMIT": "rate_limit_exceeded",
    "TIMEOUT": "request_timeout",
    "API_ERROR": "api_error"
}
```

3. Generation Errors
```python
PROVIDER_ERROR_TYPES = {
    "PROMPT_ERROR": "prompt_preparation_failed",
    "TEMPLATE_ERROR": "template_formatting_failed",
    "PARAM_ERROR": "invalid_parameters"
}
```

4. Resource Errors
```python
PROVIDER_ERROR_TYPES = {
    "MODEL_ERROR": "model_not_available",
    "RESOURCE_ERROR": "resource_exhausted"
}
```

5. Response Errors
```python
PROVIDER_ERROR_TYPES = {
    "RESPONSE_ERROR": "invalid_response",
    "PARSING_ERROR": "response_parsing_failed"
}
```

## Integration Examples

### Provider Implementation

```python
class WatsonXProvider(LLMProvider):
    def __init__(self, provider_config_service: ProviderConfigService) -> None:
        """Initialize WatsonX provider.
        
        Args:
            provider_config_service: Service for provider configuration
        """
        # Initialize base attributes
        self.provider_config_service = provider_config_service
        self.client = None
        self.embeddings_client = None
        self._model_cache = {}
        
        # Get and validate configuration
        self._provider_config = self.provider_config_service.get_provider_config("watsonx")
        if not self._provider_config:
            raise LLMProviderError(
                provider="watsonx",
                error_type=PROVIDER_ERROR_TYPES["CONFIG_INVALID"],
                message="No configuration found for WatsonX provider"
            )

        # Initialize base class
        super().__init__()

    def initialize_client(self) -> None:
        """Initialize WatsonX client."""
        try:
            self.client = APIClient(
                project_id=self._provider_config.project_id,
                credentials=Credentials(
                    api_key=self._provider_config.api_key,
                    url=self._provider_config.api_url
                )
            )
        except Exception as e:
            raise LLMProviderError(
                provider="watsonx",
                error_type=PROVIDER_ERROR_TYPES["INIT_FAILED"],
                message=f"Failed to initialize client: {str(e)}"
            )
```

### Factory Implementation

```python
class LLMProviderFactory:
    """Factory for creating and managing LLM providers with logging."""
    
    _providers: Dict[str, Type[LLMProvider]] = {
        "watsonx": WatsonXProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider
    }
    _instances: Dict[str, LLMProvider] = {}

    def __init__(self, db: Session) -> None:
        """Initialize factory with database session."""
        self._provider_config_service = ProviderConfigService(db)

    def get_provider(self, provider_type: str) -> LLMProvider:
        """Get or create a provider instance."""
        provider_type = provider_type.lower()
        
        if provider_type not in self._providers:
            raise LLMProviderError(
                provider=provider_type,
                error_type="unknown_provider",
                message=f"Unknown provider type: {provider_type}"
            )

        # Create new instance if needed
        if provider_type not in self._instances:
            self._instances[provider_type] = self._providers[provider_type](
                provider_config_service=self._provider_config_service
            )

        return self._instances[provider_type]
```

## Best Practices

1. **Configuration Management**
   - Use provider_config_service for provider settings
   - Use ProviderConfig for runtime settings
   - Validate configurations at startup

2. **Error Handling**
   - Use standardized error types from PROVIDER_ERROR_TYPES
   - Include provider name in errors
   - Log errors with context

3. **Provider Implementation**
   - Initialize configuration in __init__
   - Handle client initialization separately
   - Clean up resources in close()

4. **Testing**
   - Test provider validation
   - Test error handling
   - Mock external services

## Future Improvements

1. **Configuration Management**
   - Dynamic runtime configuration updates
   - Configuration validation rules
   - Configuration versioning

2. **Error Handling**
   - Custom error recovery strategies
   - Error aggregation and analysis
   - Automatic error recovery

3. **Monitoring**
   - Configuration usage metrics
   - Error rate tracking
   - Performance monitoring

4. **Security**
   - Configuration encryption
   - Access control
   - Audit logging
