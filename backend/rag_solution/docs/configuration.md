# RAG Modulo Configuration Guide

This document outlines the configuration structure for the RAG Modulo application.

## Configuration System Migration

The configuration system is currently being migrated from a monolithic approach to a more modular one. During this transition, both systems are supported through a feature flag.

### Feature Flag

Set the `USE_NEW_CONFIG` environment variable to control which configuration system is used:

```env
USE_NEW_CONFIG=true  # Use new configuration system
USE_NEW_CONFIG=false # Use legacy configuration (default)
```

## Core Configuration

The core configuration (`config.py`) contains essential startup settings that are required for the application to initialize. These settings are loaded from environment variables and are immutable during runtime.

### Critical Settings

#### Security Credentials
- `jwt_secret_key` (required): Secret key for JWT token generation
- `jwt_algorithm`: JWT algorithm (default: "HS256")

#### IBM/WatsonX Credentials
- `wx_project_id`: WatsonX instance ID
- `wx_api_key`: WatsonX API key
- `wx_url`: WatsonX base URL
- `ibm_client_id`: IBM OIDC client ID
- `ibm_client_secret`: IBM OIDC client secret

#### Database Settings
- `collectiondb_user`: Database username
- `collectiondb_pass`: Database password
- `collectiondb_host`: Database host
- `collectiondb_port`: Database port (default: 5432)
- `collectiondb_name`: Database name

### Using the New Configuration

To use the new configuration system:

```python
from backend.core.config import settings

# Ensure USE_NEW_CONFIG=true in environment
os.environ['USE_NEW_CONFIG'] = 'true'

# Use settings
db_host = settings.collectiondb_host
jwt_key = settings.jwt_secret_key
```

### Using Legacy Configuration

During migration, you can still use the legacy configuration:

```python
from backend.core.config import settings

# Ensure USE_NEW_CONFIG=false in environment
os.environ['USE_NEW_CONFIG'] = 'false'

# Use legacy settings
chunking_strategy = settings.chunking_strategy
embedding_model = settings.embedding_model
```

### Environment Variables

Settings can be configured through environment variables or a `.env` file:

```env
# Core Settings (Required)
JWT_SECRET_KEY=your-secret-key
WATSONX_INSTANCE_ID=your-instance-id
WATSONX_APIKEY=your-api-key

# Database Settings
COLLECTIONDB_USER=rag_modulo_user
COLLECTIONDB_PASS=rag_modulo_password
COLLECTIONDB_HOST=localhost
COLLECTIONDB_PORT=5432

# Legacy Settings (if USE_NEW_CONFIG=false)
RAG_LLM=your-model
CHUNKING_STRATEGY=fixed
EMBEDDING_MODEL=your-embedding-model
```

## Migration Guide

### Step 1: Enable New Configuration

Start by testing your application with the new configuration:

1. Set environment variable:
   ```bash
   export USE_NEW_CONFIG=true
   ```

2. Update your code to use only core settings:
   ```python
   from backend.core.config import settings
   
   # Use only core settings
   db_config = {
       'host': settings.collectiondb_host,
       'port': settings.collectiondb_port,
       'user': settings.collectiondb_user,
       'password': settings.collectiondb_pass,
   }
   ```

### Step 2: Move Runtime Settings

Gradually move runtime settings to their respective modules:

1. LLM Parameters → `rag_solution/models/llm_parameters.py`
2. Prompt Templates → `rag_solution/models/prompt_template.py`
3. Runtime Settings → `rag_solution/models/runtime_config.py`

Example:
```python
from rag_solution.models.llm_parameters import LLMParameters

# Instead of using settings.temperature, settings.max_new_tokens
llm_params = LLMParameters(
    temperature=0.7,
    max_new_tokens=500
)
```

### Step 3: Clean Up

Once all settings are migrated:

1. Remove `LegacySettings` class
2. Remove `USE_NEW_CONFIG` flag
3. Clean up environment variables

## Testing

To test configuration changes:

1. Run the test suite:
   ```bash
   pytest backend/tests/test_core_config.py -v
   ```

2. Test with both configurations:
   ```bash
   USE_NEW_CONFIG=true pytest ...
   USE_NEW_CONFIG=false pytest ...
   ```

## Troubleshooting

### Common Issues

1. Missing Required Settings
   ```
   pydantic.error_wrappers.ValidationError: 1 validation error for Settings
   jwt_secret_key
     field required (type=value_error.missing)
   ```
   Solution: Ensure JWT_SECRET_KEY is set in environment or .env file

2. Invalid Port Number
   ```
   pydantic.error_wrappers.ValidationError: 1 validation error for Settings
   collectiondb_port
     Port must be between 1 and 65535 (type=value_error)
   ```
   Solution: Use a valid port number between 1 and 65535
