# Configuration Guide

This guide covers all configuration options for RAG Modulo, including environment variables, application settings, and service configurations.

## Configuration Overview

RAG Modulo uses a hierarchical configuration system:

1. **Environment Variables**: Primary configuration method
2. **Configuration Files**: Application-specific settings
3. **Docker Compose**: Service orchestration
4. **Makefile**: Development workflow settings

## Environment Variables

### Core Application Settings

```bash
# Application Mode
PRODUCTION_MODE=false          # Enable production mode
DEBUG=false                    # Enable debug logging
LOG_LEVEL=INFO                # Logging level (DEBUG, INFO, WARNING, ERROR)
TESTING=false                 # Enable testing mode
DEVELOPMENT_MODE=false        # Enable development features

# Authentication Bypass (Development/Testing Only)
# See: docs/features/authentication-bypass.md for detailed documentation
SKIP_AUTH=false               # Set to true to bypass IBM OIDC authentication
                              # When true: Backend provides mock user + bypass token
                              # When false: Full IBM OIDC authentication required
                              # SECURITY: Never set to true in production!
                              # Application will refuse to start if SKIP_AUTH=true and ENVIRONMENT=production
```

### Security Configuration

```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-256-bits    # JWT signing secret
JWT_ALGORITHM=HS256                       # JWT algorithm
JWT_EXPIRATION_HOURS=24                   # Token expiration time

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Security Features
SECURITY_SCAN=true             # Enable security scanning
VULNERABILITY_CHECK=true       # Enable vulnerability checks
```

### Database Configuration

```bash
# PostgreSQL Settings
COLLECTIONDB_HOST=postgres     # Database host
COLLECTIONDB_PORT=5432         # Database port
COLLECTIONDB_NAME=rag_modulo   # Database name
COLLECTIONDB_USER=rag_user     # Database user
COLLECTIONDB_PASS=rag_password # Database password
COLLECTIONDB_SSL_MODE=disable  # SSL mode (disable, require, prefer)

# Connection Pooling
DB_POOL_SIZE=10               # Connection pool size
DB_MAX_OVERFLOW=20            # Maximum overflow connections
DB_POOL_TIMEOUT=30            # Connection timeout
DB_POOL_RECYCLE=3600          # Connection recycle time
```

### Vector Database Configuration

```bash
# Milvus Settings
MILVUS_HOST=milvus-standalone  # Milvus host
MILVUS_PORT=19530             # Milvus port
MILVUS_USER=                  # Milvus username (if auth enabled)
MILVUS_PASSWORD=              # Milvus password (if auth enabled)
MILVUS_DB_NAME=default        # Milvus database name
MILVUS_COLLECTION_PREFIX=collection_  # Collection name prefix
```

### AI Services Configuration

```bash
# IBM WatsonX Settings
WATSONX_INSTANCE_ID=your-instance-id     # WatsonX instance ID
WATSONX_APIKEY=your-api-key              # WatsonX API key
WATSONX_URL=https://us-south.ml.cloud.ibm.com  # WatsonX URL

# Embedding Configuration
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2  # Embedding model
EMBEDDING_DIM=384                        # Embedding dimensions
EMBEDDING_FIELD=embedding                # Embedding field name
EMBEDDING_BATCH_SIZE=32                  # Batch size for embeddings
```

### Document Processing & Chunking Configuration

```bash
# IBM Docling Document Processing
ENABLE_DOCLING=true                      # Enable IBM Docling for advanced document processing
DOCLING_FALLBACK_ENABLED=true            # Enable fallback to traditional processing if Docling fails

# HybridChunker Configuration
USE_DOCLING_CHUNKER=true                 # Use Docling's HybridChunker for token-aware chunking
CHUNKING_TOKENIZER_MODEL=ibm-granite/granite-embedding-english-r2  # Tokenizer model for token counting

# Chunking Strategy (used when USE_DOCLING_CHUNKER=false)
CHUNKING_STRATEGY=fixed                  # Chunking strategy (fixed, semantic, hierarchical)
MIN_CHUNK_SIZE=100                       # Minimum chunk size in tokens
MAX_CHUNK_SIZE=400                       # Maximum chunk size in tokens
CHUNK_OVERLAP=10                         # Overlap between chunks
```

#### HybridChunker Details

When `USE_DOCLING_CHUNKER=true`:

- **Token-Aware Chunking**: Uses HuggingFace tokenizers to count actual tokens, ensuring chunks stay within embedding model limits
- **Tokenizer Model**: Should match your embedding model family for accurate token counts:
  - IBM Slate/Granite embeddings → `ibm-granite/granite-embedding-english-r2`
  - Sentence Transformers → `sentence-transformers/all-MiniLM-L6-v2`
- **Max Tokens**: Defaults to 400 tokens (78% of IBM Slate's 512 limit) with safety margin for metadata
- **Semantic Merging**: Automatically merges semantically similar chunks when `merge_peers=True`

**Benefits**:

- ✅ Prevents "token count exceeds maximum" errors
- ✅ Accurate token counting (no tokenizer mismatch)
- ✅ Better chunk quality with semantic boundaries
- ✅ Optimal for IBM Slate/Granite embeddings

**When to Use**:

- ✅ Using IBM Slate/Granite embeddings (recommended)
- ✅ Processing long documents (PDFs, reports)
- ✅ Need precise token control for embedding models

**When to Disable**:

- Traditional fixed-size chunking preferred
- Custom chunking strategy needed
- Docling not installed

### Object Storage Configuration

```bash
# MinIO Settings
MINIO_ENDPOINT=minio:9000     # MinIO endpoint
MINIO_ACCESS_KEY=minioadmin   # MinIO access key
MINIO_SECRET_KEY=minioadmin   # MinIO secret key
MINIO_BUCKET_NAME=rag-modulo  # Default bucket name
MINIO_SECURE=false            # Use HTTPS
```

### MLflow Configuration

```bash
# MLflow Settings
MLFLOW_TRACKING_URI=http://mlflow-server:5000  # MLflow tracking URI
MLFLOW_TRACKING_USERNAME=mlflow                # MLflow username
MLFLOW_TRACKING_PASSWORD=mlflow123             # MLflow password
MLFLOW_EXPERIMENT_NAME=rag-modulo              # Default experiment name
```

### OIDC Configuration

```bash
# IBM OIDC Settings
OIDC_DISCOVERY_ENDPOINT=https://your-oidc-provider/.well-known/openid_configuration
OIDC_AUTH_URL=https://your-oidc-provider/auth
OIDC_TOKEN_URL=https://your-oidc-provider/token
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
FRONTEND_URL=http://localhost:3000
```

## Configuration Files

### Backend Configuration

```python
# backend/core/config.py
from pydantic import BaseSettings, Field
from typing import Optional

class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    production_mode: bool = Field(default=False, env="PRODUCTION_MODE")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    testing: bool = Field(default=False, env="TESTING")
    skip_auth: bool = Field(default=False, env="SKIP_AUTH")
    development_mode: bool = Field(default=False, env="DEVELOPMENT_MODE")

    # Security
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")

    # Database
    collectiondb_host: str = Field(default="postgres", env="COLLECTIONDB_HOST")
    collectiondb_port: int = Field(default=5432, env="COLLECTIONDB_PORT")
    collectiondb_name: str = Field(default="rag_modulo", env="COLLECTIONDB_NAME")
    collectiondb_user: str = Field(default="rag_user", env="COLLECTIONDB_USER")
    collectiondb_pass: str = Field(env="COLLECTIONDB_PASS")

    # AI Services
    watsonx_instance_id: str = Field(env="WATSONX_INSTANCE_ID")
    watsonx_apikey: str = Field(env="WATSONX_APIKEY")
    watsonx_url: str = Field(env="WATSONX_URL")

    class Config:
        env_file = ".env"
        case_sensitive = False
```

### Frontend Configuration

```javascript
// webui/src/config.js
const config = {
  // API Configuration
  apiUrl: process.env.REACT_APP_API_URL || 'http://localhost:8000',

  // Environment
  environment: process.env.NODE_ENV || 'development',

  // Features
  features: {
    analytics: process.env.REACT_APP_ANALYTICS_ENABLED === 'true',
    debug: process.env.REACT_APP_DEBUG === 'true',
    hotReload: process.env.NODE_ENV === 'development'
  },

  // Authentication
  auth: {
    provider: process.env.REACT_APP_AUTH_PROVIDER || 'jwt',
    tokenKey: 'rag_modulo_token'
  }
};

export default config;
```

## Docker Configuration

### Development Docker Compose

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.backend
    environment:
      - DEVELOPMENT_MODE=true
      - DEBUG=true
      - LOG_LEVEL=DEBUG
      - TESTING=true
      - SKIP_AUTH=true
    env_file:
      - .env.dev
    volumes:
      - ./backend:/app:ro
      - ./logs:/app/logs
    ports:
      - "8000:8000"

  frontend:
    build:
      context: ./webui
      dockerfile: Dockerfile.frontend
    environment:
      - REACT_APP_API_URL=http://localhost:8000
      - REACT_APP_DEBUG=true
    ports:
      - "3000:8080"
```

### Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.backend
    environment:
      - PRODUCTION_MODE=true
      - DEBUG=false
      - LOG_LEVEL=INFO
      - SECURITY_SCAN=true
    env_file:
      - .env.prod
    volumes:
      - backend_data:/mnt/data
      - ./logs:/app/logs
    restart: unless-stopped

  frontend:
    build:
      context: ./webui
      dockerfile: Dockerfile.frontend
    environment:
      - REACT_APP_API_URL=https://api.yourdomain.com
      - REACT_APP_DEBUG=false
    restart: unless-stopped
```

## CLI Configuration

### CLI Settings

```python
# backend/rag_solution/cli/config.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class RAGConfig(BaseModel):
    """CLI configuration model."""

    # API Configuration
    api_url: str = Field(default="http://localhost:8000", env="RAG_API_URL")
    timeout: int = Field(default=30, env="RAG_TIMEOUT")

    # Authentication
    token: Optional[str] = Field(default=None, env="RAG_TOKEN")
    username: Optional[str] = Field(default=None, env="RAG_USERNAME")
    password: Optional[str] = Field(default=None, env="RAG_PASSWORD")

    # Output Configuration
    output_format: str = Field(default="table", env="RAG_OUTPUT_FORMAT")
    verbose: bool = Field(default=False, env="RAG_VERBOSE")
    dry_run: bool = Field(default=False, env="RAG_DRY_RUN")

    # Profile Management
    profile: str = Field(default="default", env="RAG_PROFILE")
    profiles: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
```

### CLI Profile Configuration

```yaml
# ~/.rag_modulo/profiles.yaml
profiles:
  default:
    api_url: "http://localhost:8000"
    output_format: "table"
    verbose: false

  production:
    api_url: "https://api.yourdomain.com"
    output_format: "json"
    verbose: true

  development:
    api_url: "http://localhost:8000"
    output_format: "table"
    verbose: true
    dry_run: true
```

## Environment-Specific Configuration

### Development Environment

```bash
# .env.dev
TESTING=true
SKIP_AUTH=true
DEVELOPMENT_MODE=true
DEBUG=true
LOG_LEVEL=DEBUG
JWT_SECRET_KEY=dev-jwt-secret-key-for-local-development-only
```

### Production Environment

```bash
# .env.prod
PRODUCTION_MODE=true
DEBUG=false
LOG_LEVEL=INFO
SECURITY_SCAN=true
VULNERABILITY_CHECK=true
JWT_SECRET_KEY=your-secure-production-secret-key-256-bits
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Testing Environment

```bash
# .env.test
TESTING=true
SKIP_AUTH=true
LOG_LEVEL=DEBUG
DB_NAME=rag_modulo_test
JWT_SECRET_KEY=test-jwt-secret-key
```

## Configuration Validation

### Environment Validation

```bash
# Validate environment configuration
make validate-env

# Check specific configuration
docker compose -f docker-compose.dev.yml config
```

### Application Validation

```python
# backend/core/validation.py
from pydantic import BaseModel, validator
import os

class ConfigValidator(BaseModel):
    """Configuration validation."""

    @validator('jwt_secret_key')
    def validate_jwt_secret(cls, v):
        """Validate JWT secret key strength."""
        if len(v) < 32:
            raise ValueError('JWT secret key must be at least 32 characters')
        return v

    @validator('watsonx_apikey')
    def validate_watsonx_key(cls, v):
        """Validate WatsonX API key format."""
        if not v or len(v) < 20:
            raise ValueError('WatsonX API key is required and must be valid')
        return v
```

## Configuration Management

### Environment Switching

```bash
# Switch to development
make dev-up

# Switch to production
make run-services

# Switch to testing
make test-env
```

### Configuration Backup

```bash
# Backup configuration
cp .env .env.backup
cp .env.dev .env.dev.backup
cp .env.prod .env.prod.backup

# Restore configuration
cp .env.backup .env
```

## Troubleshooting Configuration

### Common Issues

#### Environment Variables Not Loading

```bash
# Check environment file
cat .env.dev

# Verify Docker environment
docker compose -f docker-compose.dev.yml config

# Check application logs
make dev-logs
```

#### Configuration Validation Errors

```bash
# Validate configuration
make validate-env

# Check specific settings
python -c "from backend.core.config import Settings; print(Settings())"
```

#### Service Configuration Issues

```bash
# Check service status
make dev-status

# Restart with new configuration
make dev-restart

# Validate all services
make dev-validate
```

#### HybridChunker and Tokenizer Issues

**Problem**: "Failed to load tokenizer" error during startup

**Cause**: Network connectivity issues, invalid tokenizer model name, or HuggingFace access problems

**Solution**:
```bash
# 1. Verify tokenizer model exists on HuggingFace
# Visit: https://huggingface.co/ibm-granite/granite-embedding-english-r2

# 2. Check network connectivity
curl -I https://huggingface.co

# 3. Test tokenizer download manually
python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('ibm-granite/granite-embedding-english-r2')"

# 4. If behind a proxy, set environment variables
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080

# 5. Check CHUNKING_TOKENIZER_MODEL setting in .env
grep CHUNKING_TOKENIZER_MODEL .env
```

**Problem**: "Token indices sequence length is longer than maximum" errors persist

**Cause**: Chunks exceed embedding model's token limit despite HybridChunker configuration

**Solution**:
```bash
# 1. Verify CHUNKING_MAX_TOKENS is set correctly (default: 400 for IBM Slate)
grep CHUNKING_MAX_TOKENS .env

# 2. Reduce max_tokens if needed (must be < 512 for IBM Slate)
# Edit .env:
CHUNKING_MAX_TOKENS=350  # More conservative limit

# 3. Ensure USE_DOCLING_CHUNKER=true
grep USE_DOCLING_CHUNKER .env

# 4. Check logs for token count statistics
grep "Chunking complete" logs/rag_modulo.log

# 5. Verify tokenizer matches embedding model family
# IBM Slate embeddings → ibm-granite tokenizer
# Sentence Transformers → sentence-transformers tokenizer
```

**Problem**: "HybridChunker not initialized" warning in logs

**Cause**: `USE_DOCLING_CHUNKER=false` or Docling not installed

**Solution**:
```bash
# 1. Enable HybridChunker in .env
USE_DOCLING_CHUNKER=true

# 2. Verify Docling is installed
poetry show | grep docling

# 3. If not installed, add Docling
poetry add docling

# 4. Restart application
make local-dev-restart
```

## Best Practices

### Security

- Use strong, unique secrets for each environment
- Never commit secrets to version control
- Use environment-specific configuration files
- Enable security scanning in production

### Performance

- Optimize database connection pooling
- Configure appropriate log levels
- Use production-optimized settings
- Monitor resource usage

### Maintainability

- Use descriptive environment variable names
- Document all configuration options
- Validate configuration on startup
- Use configuration templates

---

**Configuration complete!** Check out the [Development Guide](development/index.md) to start developing with your configured environment.
