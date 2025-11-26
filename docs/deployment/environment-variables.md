# Environment Variables Reference

This document provides a comprehensive reference for all environment variables required to run RAG Modulo in different deployment scenarios.

## Table of Contents

- [Critical Startup Variables](#critical-startup-variables)
- [Required for Full Functionality](#required-for-full-functionality)
- [Optional Configuration](#optional-configuration)
- [Deployment-Specific Requirements](#deployment-specific-requirements)
- [Variable Categories](#variable-categories)

---

## Critical Startup Variables

These variables are **REQUIRED** for the application to start successfully. The application may crash or fall back to limited functionality without them.

### Database Configuration

| Variable | Default | Description | Required For |
|----------|---------|-------------|--------------|
| `COLLECTIONDB_HOST` | `localhost` | PostgreSQL host | All deployments |
| `COLLECTIONDB_PORT` | `5432` | PostgreSQL port | All deployments |
| `COLLECTIONDB_USER` | `rag_modulo_user` | Database username | All deployments |
| `COLLECTIONDB_PASS` | `rag_modulo_password` | Database password | All deployments |
| `COLLECTIONDB_NAME` | `rag_modulo` | Database name | All deployments |

**Why Critical**: Application cannot initialize user records, collections, or any persistent data without database access.

### LLM Provider Configuration (At Least One Required)

#### WatsonX (Recommended)

| Variable | Default | Description | Required For |
|----------|---------|-------------|--------------|
| `WATSONX_APIKEY` | - | IBM WatsonX API key | WatsonX provider |
| `WATSONX_INSTANCE_ID` | - | WatsonX project/instance ID | WatsonX provider |
| `WATSONX_URL` | `https://us-south.ml.cloud.ibm.com` | WatsonX API endpoint | WatsonX provider |

**Why Critical**: Without at least one LLM provider configured:

- User initialization fails (`ValidationError: No provider configurations available`)
- All RAG queries fail (no LLM for generation)
- Pipeline creation fails

#### Alternative Providers

| Variable | Default | Description | Required For |
|----------|---------|-------------|--------------|
| `OPENAI_API_KEY` | - | OpenAI API key | OpenAI provider |
| `ANTHROPIC_API_KEY` | - | Anthropic Claude API key | Anthropic provider |

**Note**: At least ONE of the above LLM providers must be configured for full functionality.

### Vector Database Configuration

| Variable | Default | Description | Required For |
|----------|---------|-------------|--------------|
| `VECTOR_DB` | `milvus` | Vector database type | All deployments |
| `MILVUS_HOST` | `localhost` | Milvus server host | Milvus deployments |
| `MILVUS_PORT` | `19530` | Milvus gRPC port | Milvus deployments |

**Why Critical**: Application cannot store or retrieve document embeddings without vector database access.

### Authentication & Security

| Variable | Default | Description | Required For |
|----------|---------|-------------|--------------|
| `JWT_SECRET_KEY` | `dev-secret-key-change-in-production-f8a7b2c1` | JWT signing secret | Production deployments |
| `SKIP_AUTH` | `false` | Bypass authentication (dev only) | Development only |

**Why Critical**:

- `JWT_SECRET_KEY`: Required for secure token generation/validation in production
- `SKIP_AUTH`: Must be `true` for development without OIDC, `false` for production

---

## Required for Full Functionality

These variables are not strictly required for startup but are needed for specific features.

### IBM OIDC Authentication (Production)

| Variable | Default | Description | Required For |
|----------|---------|-------------|--------------|
| `IBM_CLIENT_ID` | - | IBM OIDC client ID | OIDC authentication |
| `IBM_CLIENT_SECRET` | - | IBM OIDC client secret | OIDC authentication |
| `OIDC_DISCOVERY_ENDPOINT` | - | OIDC discovery URL | OIDC authentication |
| `OIDC_AUTH_URL` | - | OIDC authorization URL | OIDC authentication |
| `OIDC_TOKEN_URL` | - | OIDC token URL | OIDC authentication |
| `OIDC_USERINFO_ENDPOINT` | - | OIDC userinfo URL | OIDC authentication |

**Why Required**: Production deployments typically require IBM OIDC authentication. Without these, users cannot authenticate via IBM SSO.

### Embedding Model Configuration

| Variable | Default | Description | Required For |
|----------|---------|-------------|--------------|
| `EMBEDDING_MODEL` | `sentence-transformers/all-minilm-l6-v2` | Embedding model name | Document ingestion |
| `EMBEDDING_DIM` | `384` | Embedding dimension | Document ingestion |

**Why Required**: Document ingestion requires embedding generation. Mismatch between model and dimension causes failures.

### MLFlow Experiment Tracking

| Variable | Default | Description | Required For |
|----------|---------|-------------|--------------|
| `MLFLOW_TRACKING_URI` | `http://rag-modulo-mlflow-server-1:5000` | MLFlow server URL | Experiment tracking |
| `MLFLOW_TRACKING_USERNAME` | `admin` | MLFlow username | MLFlow authentication |
| `MLFLOW_TRACKING_PASSWORD` | `password` | MLFlow password | MLFlow authentication |

**Why Required**: RAG pipeline performance tracking and A/B testing requires MLFlow.

### MinIO/S3 Storage

| Variable | Default | Description | Required For |
|----------|---------|-------------|--------------|
| `MINIO_ROOT_USER` | `minioadmin` | MinIO admin username | Milvus backend storage |
| `MINIO_ROOT_PASSWORD` | `minioadmin` | MinIO admin password | Milvus backend storage |

**Why Required**: Milvus uses MinIO/S3 for vector data persistence.

---

## Optional Configuration

These variables customize behavior but have sensible defaults.

### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `ENVIRONMENT` | - | Environment name (development, production) |
| `DEVELOPMENT_MODE` | `false` | Enable development features |
| `PORT` | `8000` | Backend server port |
| `FRONTEND_URL` | `http://localhost:3000` | Frontend URL for CORS |

### LLM Generation Parameters

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_LLM` | `ibm/granite-3-3-8b-instruct` | Default LLM model |
| `MAX_NEW_TOKENS` | `800` | Maximum tokens in response |
| `MIN_NEW_TOKENS` | `200` | Minimum tokens in response |
| `TEMPERATURE` | `0.7` | Response randomness (0.0-1.0) |
| `TOP_P` | `0.95` | Nucleus sampling threshold |
| `TOP_K` | `5` | Top-k sampling value |
| `REPETITION_PENALTY` | `1.1` | Penalty for repetitive tokens |

### Chunking Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CHUNKING_STRATEGY` | `sentence` | Chunking method (sentence, semantic, hierarchical) |
| `MIN_CHUNK_SIZE` | `200` | Minimum chunk size (tokens) |
| `MAX_CHUNK_SIZE` | `300` | Maximum chunk size (tokens) |
| `CHUNK_OVERLAP` | `40` | Overlap between chunks (tokens) |
| `USE_DOCLING_CHUNKER` | `false` | Use IBM Docling's HybridChunker |

### Retrieval Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `RETRIEVAL_TYPE` | `vector` | Retrieval method (vector, keyword, hybrid) |
| `RETRIEVAL_TOP_K` | `20` | Number of documents to retrieve |
| `ENABLE_RERANKING` | `true` | Enable document reranking |
| `RERANKER_TYPE` | `llm` | Reranking method (llm, simple, cross-encoder) |
| `CROSS_ENCODER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cross-encoder model |

### Podcast Generation (Optional Feature)

| Variable | Default | Description |
|----------|---------|-------------|
| `ELEVENLABS_API_KEY` | - | ElevenLabs API key for TTS |
| `PODCAST_ENVIRONMENT` | `development` | Podcast generation mode |
| `PODCAST_STORAGE_BACKEND` | `local` | Storage backend (local, minio, s3) |

---

## Deployment-Specific Requirements

### Local Development (Docker Compose)

**Minimal Configuration**:

```bash
# Database (containers auto-configured)
COLLECTIONDB_HOST=rag-modulo-postgres-1
COLLECTIONDB_PORT=5432

# Vector DB (container auto-configured)
MILVUS_HOST=rag-modulo-standalone-1
MILVUS_PORT=19530

# LLM Provider (REQUIRED - pick one)
WATSONX_APIKEY=your-api-key
WATSONX_INSTANCE_ID=your-project-id
WATSONX_URL=https://us-south.ml.cloud.ibm.com

# Development mode
SKIP_AUTH=true
ENVIRONMENT=development
```

### Kubernetes/OpenShift (ROKS)

**Required ConfigMap Variables** (non-sensitive):

```yaml
# Application
ENVIRONMENT: production
LOG_LEVEL: INFO
PORT: "8000"

# Database (from service discovery)
COLLECTIONDB_HOST: rag-modulo-postgres-rw.rag-modulo.svc.cluster.local
COLLECTIONDB_PORT: "5432"
COLLECTIONDB_NAME: rag_modulo

# Vector Database (from service discovery)
VECTOR_DB: milvus
MILVUS_HOST: my-release-milvus-proxy.rag-modulo.svc.cluster.local
MILVUS_PORT: "19530"

# LLM Configuration
LLM_PROVIDER: watsonx
RAG_LLM: ibm/granite-3-3-8b-instruct
EMBEDDING_MODEL: ibm/slate-125m-english-rtrvr-v2
EMBEDDING_DIM: "768"

# Feature flags
SKIP_AUTH: "false"
DEVELOPMENT_MODE: "false"
```

**Required Secret Variables** (sensitive):

```yaml
# Create secret: oc create secret generic rag-modulo-secrets
JWT_SECRET_KEY: <generated-secret>
WATSONX_APIKEY: <ibm-api-key>
WATSONX_INSTANCE_ID: <project-id>
COLLECTIONDB_USER: rag_modulo_user
COLLECTIONDB_PASS: <generated-password>
IBM_CLIENT_ID: <oidc-client-id>
IBM_CLIENT_SECRET: <oidc-client-secret>
OPENAI_API_KEY: <optional>
ANTHROPIC_API_KEY: <optional>
ELEVENLABS_API_KEY: <optional>
```

### IBM Code Engine

**Required Environment Variables**:

```bash
# Same as Kubernetes, but:
COLLECTIONDB_HOST=<cloud-postgres-host>
MILVUS_HOST=<cloud-milvus-host>

# Code Engine specific
WEB_CONCURRENCY=4  # Number of worker processes
PORT=8080          # Code Engine listens on 8080
```

---

## Variable Categories

### By Sensitivity Level

**🔴 Critical Secrets** (never log, store in Kubernetes Secrets):

- `JWT_SECRET_KEY`
- `WATSONX_APIKEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `ELEVENLABS_API_KEY`
- `IBM_CLIENT_SECRET`
- `COLLECTIONDB_PASS`
- `MINIO_ROOT_PASSWORD`

**🟡 Service Credentials** (sensitive, but less critical):

- `IBM_CLIENT_ID`
- `WATSONX_INSTANCE_ID`
- `COLLECTIONDB_USER`
- `MINIO_ROOT_USER`

**🟢 Configuration** (safe to log/expose):

- All other variables (hosts, ports, model names, etc.)

### By Deployment Phase

**Build-time** (Docker image):

- None - all configuration via environment variables

**Startup** (required for successful boot):

- Database: `COLLECTIONDB_*`
- Vector DB: `MILVUS_HOST`, `MILVUS_PORT`, `VECTOR_DB`
- LLM Provider: `WATSONX_*` OR `OPENAI_API_KEY` OR `ANTHROPIC_API_KEY`
- Security: `JWT_SECRET_KEY` (production)

**Runtime** (required for features):

- OIDC: `IBM_CLIENT_*`, `OIDC_*`
- MLFlow: `MLFLOW_*`
- Podcast: `ELEVENLABS_API_KEY`

---

## Validation

### Check Required Variables

```bash
# Run validation helper
make validate-env

# Or manually check critical variables
for var in COLLECTIONDB_HOST WATSONX_APIKEY MILVUS_HOST JWT_SECRET_KEY; do
  if [ -z "${!var}" ]; then
    echo "❌ Missing: $var"
  else
    echo "✅ Set: $var"
  fi
done
```

### Security Checklist

- [ ] `JWT_SECRET_KEY` is at least 32 characters (64+ recommended)
- [ ] `JWT_SECRET_KEY` is randomly generated (not default `dev-secret-key-*`)
- [ ] No API keys committed to git (use `.env` excluded by `.gitignore`)
- [ ] Production uses `SKIP_AUTH=false`
- [ ] Secrets stored in Kubernetes Secrets (not ConfigMaps)
- [ ] Database passwords are strong (16+ characters, mixed case, symbols)

---

## Troubleshooting

### Backend Crashes on Startup

**Symptom**: `ValidationError: No provider configurations available`

**Solution**: Configure at least one LLM provider:

```bash
# For WatsonX
WATSONX_APIKEY=your-api-key
WATSONX_INSTANCE_ID=your-project-id

# OR for OpenAI
OPENAI_API_KEY=sk-...

# OR for Anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

### Mock User Initialization Fails

**Symptom**: `WARNING - Failed to ensure mock user exists via UserService`

**Cause**: No LLM providers configured

**Workaround**: Application falls back to static mock user ID. Limited functionality until LLM provider is added.

### Database Connection Errors

**Symptom**: `OperationalError: could not connect to server`

**Solution**: Verify database configuration:

```bash
# Check connectivity
psql -h $COLLECTIONDB_HOST -p $COLLECTIONDB_PORT -U $COLLECTIONDB_USER -d $COLLECTIONDB_NAME

# Verify service discovery (Kubernetes)
kubectl get svc rag-modulo-postgres-rw -n rag-modulo
```

### Milvus Connection Errors

**Symptom**: `Failed to connect to Milvus at xxx:19530`

**Solution**: Verify Milvus configuration:

```bash
# Check Milvus cluster (ROKS)
oc get milvus my-release -n rag-modulo

# Test connectivity
nc -zv $MILVUS_HOST $MILVUS_PORT
```

---

## References

- [Deployment Guide](./kubernetes.md)
- [ROKS Troubleshooting](./roks-troubleshooting.md)
- [Secret Management](../development/secret-management.md)
- [Configuration Settings](../configuration.md)
