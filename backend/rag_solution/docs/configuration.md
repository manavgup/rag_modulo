# Configuration Management

## Feature Flag
The configuration system supports both legacy and new settings through a feature flag:

```bash
USE_NEW_CONFIG=true|false  # Defaults to false
```

## Configuration Types

### 1. Legacy Configuration (LegacySettings)
Maintains backward compatibility with all existing settings:
- All LLM parameters
- Chunking settings
- Embedding settings
- Query settings
- Vector DB settings
- etc.

### 2. New Configuration (Settings)
Minimal configuration required for startup:

#### Required Settings
- **JWT Settings**
  ```
  JWT_SECRET_KEY=your-secure-jwt-secret-key  # Required
  ```

#### Core Settings
```bash
# WatsonX.ai Credentials
WATSONX_INSTANCE_ID=your-watsonx-instance-id
WATSONX_APIKEY=your-watsonx-key
WATSONX_URL=https://bam-api.res.ibm.com
LLM_CONCURRENCY=10

# Default Vector DB (Milvus)
VECTOR_DB=milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_USER=root
MILVUS_PASSWORD=milvus

# IBM OIDC Settings
IBM_CLIENT_ID=your-client-id
IBM_CLIENT_SECRET=your-client-secret
OIDC_DISCOVERY_ENDPOINT=your-discovery-endpoint
OIDC_AUTH_URL=your-auth-url
OIDC_TOKEN_URL=your-token-url
OIDC_USERINFO_ENDPOINT=your-userinfo-endpoint
OIDC_INTROSPECTION_ENDPOINT=your-introspection-endpoint

# Database Settings
COLLECTIONDB_USER=rag_modulo_user
COLLECTIONDB_PASS=rag_modulo_password
COLLECTIONDB_HOST=localhost
COLLECTIONDB_PORT=5432
COLLECTIONDB_NAME=rag_modulo

# Frontend Settings
REACT_APP_API_URL=/api
FRONTEND_URL=http://localhost:3000
FRONTEND_CALLBACK=/callback

# Project Settings
PROJECT_NAME=rag_modulo
PYTHON_VERSION=3.11
```

## Migration Strategy

### Phase 1: Feature Flag Introduction
- Add USE_NEW_CONFIG feature flag
- Keep both configuration classes
- Default to legacy settings (USE_NEW_CONFIG=false)

### Phase 2: Runtime Configuration Migration
Move the following to runtime configuration (database-stored):
- LLM Parameters
- Vector Database Settings
- Chunking Settings
- Embedding Settings
- Retrieval Settings
- Query Settings

### Phase 3: Testing and Validation
- Test both configurations in parallel
- Validate runtime configuration storage
- Ensure backward compatibility

### Phase 4: Legacy Deprecation
- Switch default to new config (USE_NEW_CONFIG=true)
- Mark legacy settings as deprecated
- Plan removal timeline

## Usage Example

```python
from core.config import settings

# Settings will be either LegacySettings or Settings
# based on USE_NEW_CONFIG environment variable
print(settings.vector_db)  # Works in both configs
```

## Testing
Both configurations are fully tested:
- Default values
- Environment overrides
- Required settings
- Optional settings
- Database settings
- Frontend settings
- JWT settings
- OIDC settings

Run tests with:
```bash
# Test legacy config
USE_NEW_CONFIG=false pytest

# Test new config
USE_NEW_CONFIG=true pytest
