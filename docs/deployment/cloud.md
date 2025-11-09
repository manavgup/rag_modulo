# Cloud Deployment Guide

This guide covers Docker-based deployment of RAG Modulo to cloud environments using production-ready container images from GitHub Container Registry (GHCR).

## Table of Contents

- [Overview](#overview)
- [Production Images](#production-images)
- [Docker Deployment](#docker-deployment)
- [Container Orchestration](#container-orchestration)
- [Cloud Platform Deployment](#cloud-platform-deployment)
- [Configuration Management](#configuration-management)
- [Health Checks & Monitoring](#health-checks--monitoring)
- [Troubleshooting](#troubleshooting)

## Overview

RAG Modulo uses a multi-container architecture with the following components:

- **Backend API**: FastAPI application (`ghcr.io/manavgup/rag_modulo/backend:latest`)
- **Frontend**: React application with Carbon Design (`ghcr.io/manavgup/rag_modulo/frontend:latest`)
- **PostgreSQL**: Metadata and user database
- **Milvus**: Vector database for embeddings
- **MinIO**: S3-compatible object storage
- **MLFlow**: Model tracking and experimentation

## Production Images

### GitHub Container Registry (GHCR)

All production images are published to GHCR with automated builds via GitHub Actions:

```bash
# Backend image
ghcr.io/manavgup/rag_modulo/backend:latest
ghcr.io/manavgup/rag_modulo/backend:v1.0.0

# Frontend image
ghcr.io/manavgup/rag_modulo/frontend-tailwind:latest
ghcr.io/manavgup/rag_modulo/frontend-tailwind:v1.0.0

# Test image
ghcr.io/manavgup/rag_modulo/backend:test-1.0.0
```

### Image Features

**Backend Image** (`backend/Dockerfile.backend`):
- Multi-stage build for optimized size (~800MB)
- CPU-only PyTorch to avoid 6-8GB NVIDIA dependencies
- Non-root user (uid=10001) for security
- Health check support via `/api/health`
- Built with Poetry for dependency management

**Frontend Image** (`frontend/Dockerfile.frontend`):
- Nginx-based static file serving
- Optimized React production build
- Health check on port 8080
- ~150MB final image size

### Pulling Images

```bash
# Authenticate to GHCR (if private repository)
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull latest images
docker pull ghcr.io/manavgup/rag_modulo/backend:latest
docker pull ghcr.io/manavgup/rag_modulo/frontend-tailwind:latest

# Pull specific version
docker pull ghcr.io/manavgup/rag_modulo/backend:v1.0.0
```

## Docker Deployment

### Production Docker Compose

The production deployment uses `docker-compose.yml` with infrastructure from `docker-compose-infra.yml`:

```bash
# File: docker-compose.yml
# Location: /home/user/rag_modulo/docker-compose.yml

# Start production stack
make prod-start

# Or manually:
docker compose -f docker-compose.yml up -d

# Check status
make prod-status
docker compose ps
```

### Infrastructure Configuration

**File**: `/home/user/rag_modulo/docker-compose-infra.yml`

Services included:
- **postgres**: PostgreSQL 13 with health checks
- **milvus-standalone**: Milvus v2.4.4 vector database
- **milvus-etcd**: etcd for Milvus metadata
- **minio**: S3-compatible storage (ports 9000/9001)
- **mlflow-server**: Model tracking (port 5001)

```yaml
# Key health check configuration
postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${COLLECTIONDB_USER} -d ${COLLECTIONDB_NAME}"]
    interval: 10s
    timeout: 5s
    retries: 5

milvus-standalone:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
    interval: 30s
    timeout: 10s
    retries: 5
    start_period: 60s
```

### Environment Variables

**Required Variables** (`.env` file):

```bash
# Database
COLLECTIONDB_HOST=postgres
COLLECTIONDB_PORT=5432
COLLECTIONDB_NAME=rag_modulo_db
COLLECTIONDB_USER=postgres
COLLECTIONDB_PASS=your-secure-password

# Vector Database
VECTOR_DB=milvus
MILVUS_HOST=milvus-standalone
MILVUS_PORT=19530

# Object Storage
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=your-secure-password

# MLFlow
MLFLOW_TRACKING_USERNAME=mlflow
MLFLOW_TRACKING_PASSWORD=your-secure-password

# Authentication
JWT_SECRET_KEY=your-jwt-secret-key-min-32-chars
SKIP_AUTH=false  # NEVER set to true in production!

# LLM Providers
WATSONX_APIKEY=your-watsonx-api-key
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_INSTANCE_ID=your-instance-id

# OIDC (if using IBM W3ID)
OIDC_DISCOVERY_ENDPOINT=https://w3id.sso.ibm.com/auth/sps/samlidp2/saml20
OIDC_AUTH_URL=https://w3id.sso.ibm.com/pkmsoidc/authorize
OIDC_TOKEN_URL=https://w3id.sso.ibm.com/pkmsoidc/token
IBM_CLIENT_ID=your-client-id
IBM_CLIENT_SECRET=your-client-secret

# Application
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
ENVIRONMENT=production
```

### Volumes and Data Persistence

**Volume Mapping** (production):

```yaml
volumes:
  postgres_data:
    driver_opts:
      type: none
      device: ${PWD}/volumes/postgres
      o: bind

  milvus_data:
    driver_opts:
      type: none
      device: ${PWD}/volumes/milvus
      o: bind

  minio_data:
    driver_opts:
      type: none
      device: ${PWD}/volumes/minio
      o: bind

  backend_data:
    driver_opts:
      type: none
      device: ${PWD}/volumes/backend
      o: bind
```

**Backup Recommendations**:

```bash
# Backup volumes directory
tar -czf rag-modulo-backup-$(date +%Y%m%d).tar.gz volumes/

# Restore volumes
tar -xzf rag-modulo-backup-20250109.tar.gz

# Database-specific backup (see docs/deployment/backup-disaster-recovery.md)
docker compose exec postgres pg_dump -U postgres rag_modulo_db > backup.sql
```

## Container Orchestration

### Building Production Images

```bash
# Build all images
make build-all

# Build backend only
make build-backend

# Build frontend only
make build-frontend

# Manual build with specific tags
docker build -f backend/Dockerfile.backend -t rag-modulo-backend:custom .
docker build -f frontend/Dockerfile.frontend -t rag-modulo-frontend:custom frontend/
```

### Multi-Stage Build Process

**Backend Build** (Dockerfile.backend):

```dockerfile
# Stage 1: Builder (Rust + Poetry dependencies)
FROM python:3.12-slim AS builder
ENV POETRY_VERSION=2.1.3
# Install Rust for tokenizers/safetensors compilation
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
# Install dependencies with CPU-only PyTorch
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu

# Stage 2: Final runtime (slim image)
FROM python:3.12-slim
# Copy only compiled packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
# Create non-root user
RUN useradd --uid 10001 -g backend backend
USER backend
```

### Container Resource Limits

**Recommended Resource Allocation**:

```yaml
# docker-compose.production.yml example
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G

  postgres:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G

  milvus-standalone:
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G
```

## Cloud Platform Deployment

### AWS ECS/Fargate

**Task Definition** (backend service):

```json
{
  "family": "rag-modulo-backend",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "ghcr.io/manavgup/rag_modulo/backend:latest",
      "portMappings": [{"containerPort": 8000, "protocol": "tcp"}],
      "environment": [
        {"name": "COLLECTIONDB_HOST", "value": "postgres.internal"},
        {"name": "MILVUS_HOST", "value": "milvus.internal"}
      ],
      "secrets": [
        {"name": "COLLECTIONDB_PASS", "valueFrom": "arn:aws:secretsmanager:..."},
        {"name": "JWT_SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:..."}
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "python healthcheck.py"],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ],
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096"
}
```

### Google Cloud Run

```bash
# Deploy backend to Cloud Run
gcloud run deploy rag-modulo-backend \
  --image ghcr.io/manavgup/rag_modulo/backend:latest \
  --platform managed \
  --region us-central1 \
  --port 8000 \
  --set-env-vars COLLECTIONDB_HOST=postgres-ip,MILVUS_HOST=milvus-ip \
  --set-secrets COLLECTIONDB_PASS=postgres-secret:latest \
  --min-instances 1 \
  --max-instances 10 \
  --memory 4Gi \
  --cpu 2 \
  --timeout 300s \
  --allow-unauthenticated
```

### Azure Container Instances

```bash
# Deploy backend container
az container create \
  --resource-group rag-modulo-rg \
  --name rag-modulo-backend \
  --image ghcr.io/manavgup/rag_modulo/backend:latest \
  --cpu 2 \
  --memory 4 \
  --ports 8000 \
  --environment-variables \
    COLLECTIONDB_HOST=postgres.azure \
    MILVUS_HOST=milvus.azure \
  --secure-environment-variables \
    COLLECTIONDB_PASS=$POSTGRES_PASSWORD \
    JWT_SECRET_KEY=$JWT_SECRET
```

### IBM Cloud Code Engine

See detailed guide: [docs/deployment/ibm-cloud-code-engine.md](/home/user/rag_modulo/docs/deployment/ibm-cloud-code-engine.md)

```bash
# Deploy to Code Engine
ibmcloud ce application create \
  --name rag-modulo-backend \
  --image ghcr.io/manavgup/rag_modulo/backend:latest \
  --port 8000 \
  --cpu 2 \
  --memory 4G \
  --env COLLECTIONDB_HOST=postgres-service \
  --env-from-secret rag-modulo-secrets \
  --min-scale 1 \
  --max-scale 10
```

## Configuration Management

### Environment Variable Priority

1. Container environment variables (docker-compose.yml)
2. `.env` file in project root
3. Default values in `core/config.py`

### Secrets Management

**Best Practices**:

```bash
# Use Docker secrets (Docker Swarm)
echo "your-postgres-password" | docker secret create postgres_password -

# Use Kubernetes secrets (see kubernetes.md)
kubectl create secret generic rag-modulo-secrets \
  --from-literal=postgres-password=your-password \
  --from-literal=jwt-secret=your-jwt-secret

# Use cloud provider secret managers
# AWS Secrets Manager, Azure Key Vault, Google Secret Manager
```

### Configuration Files

**Key Configuration Locations**:

```bash
/home/user/rag_modulo/
├── .env                              # Environment variables
├── docker-compose.yml                # Production compose
├── docker-compose-infra.yml          # Infrastructure services
├── pyproject.toml                    # Python dependencies (Poetry)
├── backend/
│   ├── core/config.py                # Application settings
│   ├── main.py                       # FastAPI app initialization
│   └── healthcheck.py                # Health check script
└── frontend/
    └── .env.production               # Frontend production config
```

## Health Checks & Monitoring

### Backend Health Check

**Endpoint**: `GET /api/health`

**File**: `/home/user/rag_modulo/backend/healthcheck.py`

```python
# Health check implementation
import http.client

conn = http.client.HTTPConnection("localhost", 8000)
conn.request("GET", "/api/health")
response = conn.getresponse()
# Returns 200 if healthy, exits with code 1 if unhealthy
```

**Docker Health Check**:

```yaml
# In docker-compose.yml
backend:
  healthcheck:
    test: ["CMD", "python", "healthcheck.py"]
    interval: 30s
    timeout: 10s
    start_period: 60s
    retries: 5
```

### Application Startup Checks

**File**: `/home/user/rag_modulo/backend/main.py`

Startup sequence (lifespan event):

1. **Security Validation**: Prevents `SKIP_AUTH=true` in production
2. **Database Connection**: Tests PostgreSQL connectivity
3. **Table Creation**: Ensures all SQLAlchemy models exist
4. **LLM Provider Initialization**: Validates WatsonX/OpenAI/Anthropic credentials
5. **Mock User Creation**: Initializes system test user (if enabled)

```python
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # 1. Security validation
    validate_production_security()

    # 2. Database initialization
    Base.metadata.create_all(bind=engine)

    # 3. LLM provider setup
    factory = LLMProviderFactory(db, settings)
    factory.cleanup_all()  # Clear cached providers

    # 4. System initialization
    system_init_service = SystemInitializationService(db, settings)
    await system_init_service.initialize_all()

    yield  # Application runs

    # Cleanup on shutdown
    logger.info("Application shutdown complete")
```

### Monitoring Endpoints

**Available Endpoints**:

```bash
# Health check (no auth required)
GET http://localhost:8000/api/health

# API documentation
GET http://localhost:8000/docs
GET http://localhost:8000/redoc

# MLFlow tracking
GET http://localhost:5001/

# MinIO console
GET http://localhost:9001/
```

## Troubleshooting

### Common Deployment Issues

**Issue 1: Backend fails health checks**

```bash
# Check logs
docker compose logs backend | tail -50

# Common causes:
# - Database not ready (wait for postgres health check)
# - Missing environment variables
# - Invalid LLM provider credentials

# Verify database connection
docker compose exec backend python -c "
from rag_solution.file_management.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    print(conn.execute(text('SELECT 1')).fetchone())
"
```

**Issue 2: Image pull failures**

```bash
# Authenticate to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Check image availability
docker manifest inspect ghcr.io/manavgup/rag_modulo/backend:latest

# Use specific version instead of latest
docker pull ghcr.io/manavgup/rag_modulo/backend:v1.0.0
```

**Issue 3: Out of memory errors**

```bash
# Check container resource usage
docker stats

# Increase Docker Desktop memory allocation (Settings → Resources)
# Or set resource limits in docker-compose.yml

# For Milvus specifically (requires 4-8GB)
docker compose up -d milvus-standalone --memory=8g
```

**Issue 4: Port conflicts**

```bash
# Check what's using the port
lsof -i :8000  # Backend
lsof -i :3000  # Frontend
lsof -i :5432  # PostgreSQL

# Kill conflicting process or change port in docker-compose.yml
ports:
  - "8001:8000"  # Map external 8001 to container 8000
```

### Production Deployment Checklist

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Set `SKIP_AUTH=false` (authentication enabled)
- [ ] Generate secure `JWT_SECRET_KEY` (min 32 characters)
- [ ] Use strong database passwords
- [ ] Configure HTTPS/TLS certificates
- [ ] Enable firewall rules (only expose necessary ports)
- [ ] Configure backup automation (see backup-disaster-recovery.md)
- [ ] Set up monitoring alerts (see monitoring.md)
- [ ] Review security hardening (see security.md)
- [ ] Test disaster recovery procedures
- [ ] Document deployment-specific configuration

### Related Documentation

- [Kubernetes Deployment](kubernetes.md) - K8s manifests and Helm charts
- [Monitoring & Observability](monitoring.md) - Prometheus metrics and logging
- [Security Hardening](security-hardening.md) - Container security best practices
- [Backup & Disaster Recovery](backup-disaster-recovery.md) - Data protection strategies
- [Troubleshooting: Docker Issues](../troubleshooting/docker.md) - Container debugging guide
