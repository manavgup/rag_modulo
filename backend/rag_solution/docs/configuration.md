# Configuration Management

## Feature Flag
The configuration system supports both legacy and new settings through a feature flag:

```bash
USE_NEW_CONFIG=true|false  # Defaults to false
```

## Configuration Types

### 1. Legacy Configuration (LegacySettings)
Maintains backward compatibility with all existing settings:
```python
from core.config import get_settings

# All existing settings remain available
settings = get_settings()  # with USE_NEW_CONFIG=false
settings.chunking_strategy  # "fixed"
settings.embedding_model   # "sentence-transformers/all-minilm-l6-v2"
settings.number_of_results  # 5
```

Required fields:
- JWT_SECRET_KEY: Required for authentication
- RAG_LLM: Required for LLM configuration

### 2. New Configuration (Settings)
Minimal configuration required for startup:
```python
from core.config import get_settings

# Only essential settings
settings = get_settings()  # with USE_NEW_CONFIG=true
settings.vector_db  # "milvus"
settings.milvus_host  # "localhost"
```

Required fields:
- JWT_SECRET_KEY: Required for authentication

## Essential Settings

### Required Settings
```bash
# JWT (Required for both configurations)
JWT_SECRET_KEY=your-secure-jwt-secret-key

# Required for Legacy Settings only
RAG_LLM=your-llm-model  # e.g., "ibm/granite-13b-chat-v2"
```

### Core Settings
```bash
# WatsonX.ai Credentials
WATSONX_INSTANCE_ID=your-watsonx-instance-id
WATSONX_APIKEY=your-watsonx-key
WATSONX_URL=https://bam-api.res.ibm.com
LLM_CONCURRENCY=10

# Vector DB (Milvus)
VECTOR_DB=milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_USER=root
MILVUS_PASSWORD=milvus

# Database Settings
COLLECTIONDB_USER=rag_modulo_user
COLLECTIONDB_PASS=rag_modulo_password
COLLECTIONDB_HOST=localhost
COLLECTIONDB_PORT=5432
COLLECTIONDB_NAME=rag_modulo

# IBM OIDC Settings
IBM_CLIENT_ID=your-client-id
IBM_CLIENT_SECRET=your-client-secret
OIDC_DISCOVERY_ENDPOINT=your-discovery-endpoint
OIDC_AUTH_URL=your-auth-url
OIDC_TOKEN_URL=your-token-url
```

## Migration Strategy

### Phase 1: Feature Flag (Current)
- Added USE_NEW_CONFIG feature flag
- Both configurations available simultaneously
- Default to legacy settings (USE_NEW_CONFIG=false)
- All tests passing for both configurations
- Settings accessed through get_settings() function

### Phase 2: Runtime Configuration
Move the following to database storage:
- LLM Parameters
- Chunking Settings
- Embedding Settings
- Query Settings
- Vector DB Settings (except default Milvus)

### Phase 3: Testing and Validation
- Test both configurations in parallel
- Validate runtime configuration storage
- Ensure backward compatibility
- Update documentation

### Phase 4: Legacy Deprecation
- Switch default to new config (USE_NEW_CONFIG=true)
- Mark legacy settings as deprecated
- Plan removal timeline

## Usage Example

```python
from core.config import get_settings, LegacySettings

# Get appropriate settings based on USE_NEW_CONFIG
settings = get_settings()

# Settings will be either LegacySettings or Settings
# based on USE_NEW_CONFIG environment variable
print(settings.vector_db)  # Works in both configs

# Legacy-specific settings only available in LegacySettings
if isinstance(settings, LegacySettings):
    print(settings.chunking_strategy)
```

## Testing
Both configurations are fully tested:
```bash
# Run all configuration tests
pytest backend/tests/test_core_config.py -v

# Test cases include:
# - Legacy settings with required fields
# - New settings with required fields
# - Missing required fields validation
# - Feature flag behavior
# - Environment variable overrides
```

## Development Notes
1. When adding new settings:
   - Add to LegacySettings for backward compatibility
   - Only add to Settings if essential for startup

2. When using settings:
   - Always use get_settings() to obtain settings instance
   - Handle both configuration types
   - Check required fields documentation
   - Plan for migration to runtime config

3. Runtime Configuration:
   - Will be stored in database
   - Accessible through API
   - Cached for performance
   - Per-collection settings supported

4. Required Fields:
   - Legacy Settings: JWT_SECRET_KEY, RAG_LLM
   - New Settings: JWT_SECRET_KEY
   - All other fields have sensible defaults
