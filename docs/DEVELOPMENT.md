# Development Guide

## Quick Start for Local Development

### 1. Initialize Development Environment

```bash
# Set up Python virtual environment
make venv

# Initialize development environment configuration
make init-dev-env

# This creates .env.local with localhost connections to containerized services
```

### 2. Start Infrastructure Services

```bash
# Start PostgreSQL, Milvus, MinIO, MLflow (but NOT your backend)
make dev-infra

# Check that services are healthy
make dev-check-infra
```

### 3. Start Local Backend Development

```bash
# Start backend locally with hot reloading
make dev-backend-local

# Your backend will now run locally on http://localhost:8000
# It will connect to the containerized infrastructure services
```

## ⚠️ Important: Development Complexity

**This project has complex dependencies that make full local development challenging:**

- **SQLAlchemy models** with complex type annotations and datetime handling
- **Multiple service dependencies** (PostgreSQL, Milvus, MinIO, MLflow)
- **Authentication middleware** with OIDC integration
- **Vector database integrations** with multiple providers

**Recommendation**: Use the **hybrid approach** for most development work.

## How It Works

### Network Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Local Backend │    │   Docker Host   │    │  Infrastructure │
│   (localhost)   │◄──►│   (localhost)   │◄──►│   Containers    │
│   Port 8000     │    │   Port 5432     │    │   (PostgreSQL)  │
└─────────────────┘    │   Port 19530    │    │   (Milvus)      │
                       │   Port 9000     │    │   (MinIO)       │
                       │   Port 5000     │    │   (MLflow)      │
                       └─────────────────┘    └─────────────────┘
```

### Connection Flow
1. **Local Backend** runs on your machine
2. **Infrastructure Services** run in Docker containers
3. **Port Mapping** exposes container ports to `localhost`
4. **Environment Variables** tell backend to connect to `localhost:port`

## Development Workflow

### Daily Development (Recommended)
```bash
# 1. Start infrastructure once (morning)
make dev-infra

# 2. Use containerized backend for development
make run-backend

# 3. Make changes to code
# 4. Rebuild backend when needed: make build-backend

# 5. Stop infrastructure when done (evening)
make stop-containers
```

### Alternative: Full Local Development (Advanced)
```bash
# 1. Start infrastructure
make dev-infra

# 2. Start local backend (may have import issues)
make dev-backend-local

# 3. Debug SQLAlchemy import issues as they arise
# 4. Use for simple changes that don't touch models
```

### Testing
```bash
# Unit tests with infrastructure (recommended)
make unit-tests-local-infra

# Integration tests (local backend + containerized infrastructure)
make integration-tests-local

# Full containerized tests (most reliable)
make test testfile=tests/unit/
```

## Environment Configuration

### .env.local (Development)
```bash
# Database
COLLECTIONDB_HOST=localhost
COLLECTIONDB_PORT=5432

# Vector Database
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Object Storage
MINIO_ENDPOINT=localhost:9000

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000

# Development Settings
CONTAINER_ENV=false
PYTHONPATH=${PWD}/backend:${PWD}/vectordbs:${PWD}/rag_solution

# OIDC Configuration
OIDC_DISCOVERY_ENDPOINT=http://localhost:8080/.well-known/openid_configuration
OIDC_AUTH_URL=http://localhost:8080/auth
OIDC_TOKEN_URL=http://localhost:8080/token

# Other required variables
JWT_SECRET_KEY=test-jwt-secret-key-for-testing-only
WATSONX_INSTANCE_ID=test-instance-id
WATSONX_APIKEY=test-apikey
WATSONX_URL=https://us-south.ml.cloud.ibm.com
RAG_LLM=test-rag-llm
```

### .env (Production/Containerized)
```bash
# Database
COLLECTIONDB_HOST=postgres
COLLECTIONDB_PORT=5432

# Vector Database
MILVUS_HOST=milvus-standalone
MILVUS_PORT=19530

# Object Storage
MINIO_ENDPOINT=minio:9000

# MLflow
MLFLOW_TRACKING_URI=http://mlflow-server:5000

# Container Settings
CONTAINER_ENV=true
```

## Troubleshooting

### Common Issues

#### SQLAlchemy Import Errors
```bash
# Error: Could not resolve all types within mapped annotation: "Mapped[datetime]"
# Solution: Use containerized backend for now, or fix model imports
```

#### Port Conflicts
```bash
# Check what's using the port
lsof -i :5432  # PostgreSQL
lsof -i :19530 # Milvus
lsof -i :9000  # MinIO

# Stop conflicting services or change ports in docker-compose
```

#### Service Startup Issues
```bash
# Check service logs
docker compose logs milvus-standalone
docker compose logs mlflow-server

# Restart specific service
docker compose restart postgres
```

### Service Connection Issues
```bash
# Check if services are running
make dev-check-infra

# Test PostgreSQL connection
docker exec -it postgres-dev psql -U rag_modulo_user -d rag_modulo -c "SELECT version();"

# Test from Python
cd backend && poetry run python -c "
import psycopg2
conn = psycopg2.connect(host='localhost', port=5432, database='rag_modulo', user='rag_modulo_user', password='rag_modulo_password')
print('✅ PostgreSQL connection successful')
conn.close()
"
```

## Performance Benefits

| Approach | Backend Startup | Code Changes | Test Execution | Total Iteration | Reliability |
|----------|----------------|--------------|----------------|-----------------|-------------|
| **Full Containerized** | 30-60s | 30-60s | 30-60s | 90-180s | ⭐⭐⭐⭐⭐ |
| **Hybrid (Local + Infra)** | 2-5s | 0s (hot reload) | 2-5s | 4-10s | ⭐⭐⭐⭐ |
| **Local Only** | 2-5s | 0s (hot reload) | 2-5s | 4-10s | ⭐⭐ |

## Best Practices

1. **Use hybrid approach** for most development work
2. **Keep infrastructure running** during development sessions
3. **Use containerized backend** for complex model changes
4. **Use local backend** for simple API changes
5. **Test frequently** with containerized tests
6. **Clean up infrastructure** when done for the day

## Commands Reference

```bash
# Development
make init-dev-env          # Initialize development environment
make dev-infra             # Start infrastructure services
make dev-backend-local     # Start local backend development (may have issues)
make dev-check-infra       # Check infrastructure health

# Containerized Development (Recommended)
make run-backend           # Start containerized backend
make build-backend         # Rebuild backend after changes

# Testing
make unit-tests-local-infra # Unit tests with infrastructure
make integration-tests-local # Integration tests (local + infra)
make test testfile=tests/unit/ # Full containerized tests

# Management
make stop-infra            # Stop infrastructure services
make stop-containers       # Stop all services
make clean                 # Clean everything
```

## Alternative: Development Container

For the most reliable development experience, consider using **VS Code Dev Containers**:

1. Install VS Code Dev Containers extension
2. Open project in container
3. All dependencies and services run in the same environment
4. No import issues or environment variable problems
5. Consistent development environment across team members

This approach eliminates most of the complexity while maintaining fast iteration cycles.
