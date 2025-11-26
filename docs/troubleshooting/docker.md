# Docker Troubleshooting Guide

This guide covers common Docker and container-related issues in RAG Modulo, including networking problems, volume issues, and container debugging techniques.

## Table of Contents

- [Overview](#overview)
- [Container Health Issues](#container-health-issues)
- [Networking Problems](#networking-problems)
- [Volume & Storage Issues](#volume--storage-issues)
- [Image Build Problems](#image-build-problems)
- [Resource Constraints](#resource-constraints)
- [Multi-Container Coordination](#multi-container-coordination)
- [Docker Compose Issues](#docker-compose-issues)

## Overview

RAG Modulo uses Docker Compose for orchestrating multiple containers:

**Services**:

- `backend`: FastAPI application (port 8000)
- `frontend`: React/Nginx (port 3000/8080)
- `postgres`: PostgreSQL database (port 5432)
- `milvus-standalone`: Vector database (port 19530)
- `milvus-etcd`: Milvus metadata store (port 2379)
- `minio`: Object storage (ports 9000, 9001)
- `mlflow-server`: Model tracking (port 5001)

**Docker Compose Files**:

- `./docker-compose.yml` - Production deployment
- `./docker-compose-infra.yml` - Infrastructure services
- `./docker-compose.dev.yml` - Development overrides
- `./docker-compose.test.yml` - Testing configuration

## Container Health Issues

### Issue 1: Container Immediately Exits

**Symptoms**:

```bash
$ docker compose ps
NAME                     STATUS
rag-modulo-backend-1     Exited (1) 2 seconds ago
```

**Diagnosis**:

```bash
# Check exit code
docker compose ps

# View logs
docker compose logs backend | tail -50

# Check last container status
docker inspect rag-modulo-backend-1 | jq '.[0].State'
```

**Common Causes & Solutions**:

**A) Missing Environment Variables**:

```bash
# Check required variables
docker compose config | grep -A 50 backend

# Verify .env file exists
ls -la .env

# Check environment in container
docker compose exec backend env | grep COLLECTIONDB
```

**Solution**:

```bash
# Copy example .env
cp .env.example .env

# Edit with your values
vim .env

# Restart services
docker compose up -d
```

**B) Database Not Ready**:

```bash
# Check PostgreSQL health
docker compose ps postgres

# Wait for healthy status
docker compose up -d postgres
docker compose exec postgres pg_isready -U postgres

# Start backend after database is healthy
docker compose up -d backend
```

**Solution**: Use depends_on with health checks (already configured in docker-compose.yml)

```yaml
backend:
  depends_on:
    postgres:
      condition: service_healthy
    milvus-standalone:
      condition: service_healthy
```

**C) Application Startup Error**:

```bash
# View detailed startup logs
docker compose logs backend | grep -i error

# Common errors:
# - Import errors: Check PYTHONPATH
# - Configuration errors: Validate settings
# - Port conflicts: Check if port 8000 is available
```

**Solution**:

```bash
# Check PYTHONPATH in Dockerfile
cat backend/Dockerfile.backend | grep PYTHONPATH

# Test import manually
docker compose exec backend python -c "import rag_solution; print('OK')"

# Check port availability
lsof -i :8000 || netstat -tuln | grep 8000
```

### Issue 2: Container Health Check Failures

**Symptoms**:

```bash
$ docker compose ps
NAME                     STATUS
rag-modulo-backend-1     Up 2 minutes (unhealthy)
```

**Diagnosis**:

```bash
# Check health check configuration
docker inspect rag-modulo-backend-1 | jq '.[0].State.Health'

# View health check logs
docker inspect rag-modulo-backend-1 | jq '.[0].State.Health.Log[-5:]'

# Manual health check
docker compose exec backend python healthcheck.py
echo $?  # 0 = healthy, 1 = unhealthy
```

**Common Causes**:

**A) Backend Not Responding**:

```bash
# Check if process is running
docker compose exec backend ps aux | grep uvicorn

# Test health endpoint
docker compose exec backend curl -f http://localhost:8000/api/health

# Check logs for errors
docker compose logs backend | tail -50
```

**Solution**:

```bash
# Restart backend
docker compose restart backend

# Or rebuild if code changes
docker compose up -d --build backend
```

**B) Incorrect Health Check Path**:

```yaml
# Verify health check configuration
# File: docker-compose.yml
backend:
  healthcheck:
    test: ["CMD", "python", "healthcheck.py"]  # Correct
    # NOT: ["CMD", "curl", "-f", "http://localhost:8000/health"]  # Wrong path
```

### Issue 3: Container Restarts Continuously

**Symptoms**:

```bash
$ docker compose ps
NAME                     STATUS
rag-modulo-backend-1     Restarting (1) 10 seconds ago
```

**Diagnosis**:

```bash
# Check restart count
docker inspect rag-modulo-backend-1 | jq '.[0].RestartCount'

# View crash logs
docker compose logs backend | grep -i "error\|exception\|traceback"

# Check exit reason
docker inspect rag-modulo-backend-1 | jq '.[0].State'
```

**Common Causes**:

**A) Out of Memory (OOM)**:

```bash
# Check memory usage
docker stats --no-stream rag-modulo-backend-1

# Check for OOM in kernel logs
dmesg | grep -i "out of memory"

# Check Docker daemon logs
journalctl -u docker | grep oom
```

**Solution**:

```yaml
# Increase memory limit
# File: docker-compose.yml
backend:
  deploy:
    resources:
      limits:
        memory: 4G  # Increase from 2G
```

**B) Crash Loop Due to Dependencies**:

```bash
# Check dependency health
docker compose ps postgres milvus-standalone

# Ensure services start in correct order
# File: docker-compose.yml (already configured)
backend:
  depends_on:
    postgres:
      condition: service_healthy
```

## Networking Problems

### Issue 1: Cannot Connect to Database

**Symptoms**:

```python
sqlalchemy.exc.OperationalError: could not connect to server: Connection refused
```

**Diagnosis**:

```bash
# Check network connectivity
docker compose exec backend ping -c 3 postgres

# Test database port
docker compose exec backend nc -zv postgres 5432

# Check database service
docker compose ps postgres
docker compose logs postgres | tail -20
```

**Solutions**:

**A) Service Name Resolution**:

```bash
# Verify service name in connection string
# File: .env
COLLECTIONDB_HOST=postgres  # NOT 'localhost' or '127.0.0.1'

# Test DNS resolution
docker compose exec backend nslookup postgres
docker compose exec backend getent hosts postgres
```

**B) Network Configuration**:

```bash
# Check Docker networks
docker network ls

# Inspect app-network
docker network inspect rag-modulo_app-network

# Verify all containers are on same network
docker network inspect rag-modulo_app-network | jq '.[0].Containers'
```

**C) Port Conflicts**:

```bash
# Check if PostgreSQL port is exposed correctly
docker compose port postgres 5432

# Check local port usage
lsof -i :5432
netstat -tuln | grep 5432
```

### Issue 2: Cannot Access Backend from Host

**Symptoms**:

```bash
$ curl http://localhost:8000/api/health
curl: (7) Failed to connect to localhost port 8000: Connection refused
```

**Diagnosis**:

```bash
# Check port mapping
docker compose port backend 8000

# Check if backend is listening
docker compose exec backend netstat -tuln | grep 8000

# Check firewall rules
sudo iptables -L -n | grep 8000
```

**Solutions**:

**A) Incorrect Port Mapping**:

```yaml
# File: docker-compose.yml
backend:
  ports:
    - "8000:8000"  # host:container
  # NOT: "8001:8000" if you're accessing localhost:8000
```

**B) Backend Binding to Wrong Interface**:

```bash
# Check uvicorn bind address
docker compose exec backend ps aux | grep uvicorn

# Should be: --host 0.0.0.0 (not 127.0.0.1)
# File: docker-compose.yml
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**C) Docker Desktop Networking (Mac/Windows)**:

```bash
# On Mac/Windows, use host.docker.internal instead of localhost in some contexts
# But external access should use localhost:8000

# Test from container
docker compose exec backend curl http://localhost:8000/api/health

# Test from host
curl http://localhost:8000/api/health
```

### Issue 3: Container Cannot Reach External APIs

**Symptoms**:

```python
httpx.ConnectError: All connection attempts failed
# When calling WatsonX/OpenAI APIs
```

**Diagnosis**:

```bash
# Test external connectivity
docker compose exec backend ping -c 3 8.8.8.8
docker compose exec backend curl https://google.com

# Test specific API
docker compose exec backend curl https://us-south.ml.cloud.ibm.com
```

**Solutions**:

**A) DNS Resolution Issues**:

```bash
# Check DNS configuration
docker compose exec backend cat /etc/resolv.conf

# Test DNS resolution
docker compose exec backend nslookup us-south.ml.cloud.ibm.com

# Add DNS servers
# File: docker-compose.yml
backend:
  dns:
    - 8.8.8.8
    - 8.8.4.4
```

**B) Corporate Proxy**:

```yaml
# File: docker-compose.yml
backend:
  environment:
    - HTTP_PROXY=http://proxy.company.com:8080
    - HTTPS_PROXY=http://proxy.company.com:8080
    - NO_PROXY=localhost,postgres,milvus-standalone
```

**C) Firewall Blocking Outbound**:

```bash
# Check Docker daemon firewall rules
sudo iptables -L DOCKER-USER -n

# Allow outbound HTTPS
sudo iptables -I DOCKER-USER -p tcp --dport 443 -j ACCEPT
```

## Volume & Storage Issues

### Issue 1: Volume Mount Errors

**Symptoms**:

```bash
Error response from daemon: invalid mount config for type "bind": bind source path does not exist
```

**Diagnosis**:

```bash
# Check volume configuration
docker compose config | grep -A 10 volumes

# Verify paths exist
ls -la ./volumes/
ls -la ./volumes/postgres
```

**Solutions**:

**A) Create Volume Directories**:

```bash
# Create all volume directories
mkdir -p volumes/postgres
mkdir -p volumes/milvus
mkdir -p volumes/etcd
mkdir -p volumes/minio
mkdir -p volumes/backend

# Set permissions
chmod -R 755 volumes/
```

**B) Use Docker-Managed Volumes** (alternative):

```yaml
# File: docker-compose.yml
volumes:
  postgres_data:  # Docker-managed volume (no device path)
  milvus_data:
  minio_data:

services:
  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### Issue 2: Permission Denied Errors

**Symptoms**:

```bash
postgres_1  | FATAL: data directory "/var/lib/postgresql/data" has wrong ownership
backend_1   | PermissionError: [Errno 13] Permission denied: '/app/logs/rag_modulo.log'
```

**Diagnosis**:

```bash
# Check volume ownership
ls -la volumes/postgres
ls -la volumes/backend

# Check container user
docker compose exec backend id
docker compose exec postgres id
```

**Solutions**:

**A) Fix Volume Permissions**:

```bash
# For PostgreSQL (uid 999)
sudo chown -R 999:999 volumes/postgres

# For backend (uid 10001 from Dockerfile)
sudo chown -R 10001:10001 volumes/backend

# Or make world-writable (less secure)
chmod -R 777 volumes/backend/logs
```

**B) Use Named Volumes** (Docker manages permissions):

```yaml
volumes:
  backend_data:
  postgres_data:

services:
  backend:
    volumes:
      - backend_data:/mnt/data
  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### Issue 3: Disk Space Exhausted

**Symptoms**:

```bash
Error: No space left on device
```

**Diagnosis**:

```bash
# Check Docker disk usage
docker system df

# Detailed disk usage
docker system df -v

# Check host disk space
df -h

# Check specific volume
du -sh volumes/*
```

**Solutions**:

**A) Clean Docker Resources**:

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove build cache
docker builder prune

# Nuclear option: Clean everything (CAUTION!)
docker system prune -a --volumes
```

**B) Increase Docker Disk Allocation** (Docker Desktop):

```
Docker Desktop → Settings → Resources → Disk image size
Increase from 60GB to 120GB+
```

**C) Move Volumes to Larger Disk**:

```bash
# Stop services
docker compose down

# Move volumes
sudo mv volumes /mnt/large-disk/rag-modulo-volumes

# Update docker-compose.yml paths
# File: docker-compose.yml
volumes:
  postgres_data:
    driver_opts:
      device: /mnt/large-disk/rag-modulo-volumes/postgres

# Restart services
docker compose up -d
```

## Image Build Problems

### Issue 1: Build Fails with BACKEND_CACHE_BUST

**Symptoms**:

```bash
ERROR: failed to solve: failed to compute cache key:
# Or cache not invalidating when backend files change
```

**Diagnosis**:

```bash
# Check Dockerfile
cat backend/Dockerfile.backend | grep BACKEND_CACHE_BUST

# Try build with no cache
docker build --no-cache -f backend/Dockerfile.backend -t test-build .
```

**Solutions**:

**A) Local Builds** (uses default value):

```bash
# Local builds use default value 'local-build' automatically
docker build -f backend/Dockerfile.backend -t rag-modulo-backend:latest .
make build-backend  # Also works - uses default value
```

**B) Force Cache Invalidation**:

```bash
# Override with a new value to force cache invalidation
docker build --build-arg BACKEND_CACHE_BUST=$(date +%s) \
  -f backend/Dockerfile.backend -t rag-modulo-backend:latest .
```

**C) CI/CD Builds** (content-based invalidation):

```yaml
# In GitHub Actions workflows, BACKEND_CACHE_BUST is set automatically
# based on content hash of backend files:
BACKEND_CACHE_BUST=${{ hashFiles('backend/**/*.py', 'backend/Dockerfile.backend', 'pyproject.toml', 'poetry.lock') }}
```

**D) Build with --pull**:

```bash
# Pull latest base image
docker build --pull -f backend/Dockerfile.backend -t rag-modulo-backend:latest .
```

**Understanding Cache Invalidation Strategy**:

- **Local builds**: Use default `BACKEND_CACHE_BUST=local-build` - cache invalidates only on manual rebuilds
- **CI builds**: Use content hash - cache invalidates automatically when backend Python files, Dockerfile, or dependency files change
- **Cache benefits**: Docker layer cache is preserved when backend files are unchanged, significantly speeding up builds

### Issue 2: Poetry Lock File Issues

**Symptoms**:

```bash
ERROR: poetry.lock does not exist or is out of sync with pyproject.toml
```

**Diagnosis**:

```bash
# Check if poetry.lock exists
ls -la ./poetry.lock

# Validate lock file
poetry check --lock
```

**Solutions**:

```bash
# Regenerate lock file
cd .
poetry lock

# Rebuild image
docker compose build backend

# Or use build argument to skip validation
docker build --build-arg SKIP_LOCK_CHECK=1 -f backend/Dockerfile.backend .
```

### Issue 3: Build Timeouts

**Symptoms**:

```bash
ERROR: failed to solve: DeadlineExceeded
```

**Solutions**:

```bash
# Increase BuildKit timeout
export BUILDKIT_STEP_LOG_MAX_SIZE=-1
export BUILDKIT_STEP_LOG_MAX_SPEED=-1

# Build with more time
docker build --progress=plain -f backend/Dockerfile.backend .

# Or use docker compose
COMPOSE_HTTP_TIMEOUT=600 docker compose build backend
```

## Resource Constraints

### Issue 1: Backend OOM (Out of Memory)

**Symptoms**:

```bash
docker compose ps
rag-modulo-backend-1     Restarting (137) 1 minute ago
# Exit code 137 = killed by OOM

dmesg | tail
Out of memory: Killed process 1234 (python)
```

**Diagnosis**:

```bash
# Check memory limit
docker inspect rag-modulo-backend-1 | jq '.[0].HostConfig.Memory'

# Monitor memory usage
docker stats rag-modulo-backend-1

# Check Python memory usage
docker compose exec backend python -c "
import psutil
print(f'Memory: {psutil.virtual_memory().percent}%')
"
```

**Solutions**:

**A) Increase Memory Limit**:

```yaml
# File: docker-compose.yml
backend:
  deploy:
    resources:
      limits:
        memory: 8G  # Increase from 4G
      reservations:
        memory: 4G
```

**B) Reduce Memory Usage**:

```python
# Disable CPU-intensive operations
# File: .env
WATSONX_USE_GPU=false  # Already default in container

# Reduce worker count
WEB_CONCURRENCY=2  # Default is 4

# Use CPU-only PyTorch (already configured in Dockerfile)
```

### Issue 2: CPU Throttling

**Symptoms**:

```bash
# Slow response times
# High CPU usage: docker stats shows 100% CPU
```

**Diagnosis**:

```bash
# Check CPU limits
docker inspect rag-modulo-backend-1 | jq '.[0].HostConfig.CpuQuota'

# Monitor CPU usage
docker stats rag-modulo-backend-1

# Check Docker daemon CPU
top -p $(pgrep dockerd)
```

**Solutions**:

**A) Increase CPU Limit**:

```yaml
# File: docker-compose.yml
backend:
  deploy:
    resources:
      limits:
        cpus: '4.0'  # Increase from 2.0
      reservations:
        cpus: '2.0'
```

**B) Scale Horizontally**:

```yaml
# File: docker-compose.yml
backend:
  deploy:
    replicas: 3  # Run 3 backend containers

# With load balancer (nginx)
nginx:
  image: nginx:alpine
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf
  ports:
    - "80:80"
```

## Multi-Container Coordination

### Issue 1: Services Start Out of Order

**Symptoms**:

```bash
backend_1 | sqlalchemy.exc.OperationalError: could not connect to server
# Backend starts before PostgreSQL is ready
```

**Solution**: Use health checks with depends_on (already configured):

```yaml
# File: docker-compose.yml
backend:
  depends_on:
    postgres:
      condition: service_healthy  # Wait for health check
    milvus-standalone:
      condition: service_healthy
    mlflow-server:
      condition: service_started  # No health check, just started
```

### Issue 2: Circular Dependency

**Symptoms**:

```bash
Error: Circular dependency between services:
  service1 depends on service2
  service2 depends on service1
```

**Solution**: Break the cycle by using connection retry logic:

```python
# File: backend/rag_solution/file_management/database.py
from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
def connect_to_database():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        conn.execute("SELECT 1")
    return engine
```

## Docker Compose Issues

### Issue 1: Docker Compose V1 vs V2

**Symptoms**:

```bash
docker-compose: command not found
# Or
docker compose: unknown command
```

**Solutions**:

```bash
# Check Docker Compose version
docker compose version  # V2
docker-compose version  # V1 (deprecated)

# Install Docker Compose V2
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Check Makefile compatibility
# File: Makefile uses docker compose (V2)
DOCKER_COMPOSE := docker compose
```

### Issue 2: Multiple Compose Files

**症状**:

```bash
# Confusion about which services are running
# Different configurations in different files
```

**Solution**: Understand file precedence:

```bash
# Production (default)
docker compose up -d
# Uses: docker-compose.yml + docker-compose-infra.yml

# Development (with overrides)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Testing
docker compose -f docker-compose.test.yml up -d

# Check merged configuration
docker compose config
docker compose -f docker-compose.yml -f docker-compose.dev.yml config
```

### Issue 3: Environment Variable Conflicts

**Symptoms**:

```bash
# Different values in .env vs docker-compose.yml
# Variables not being picked up
```

**Solutions**:

```bash
# Check variable precedence (highest to lowest):
# 1. Shell environment: export VAR=value
# 2. docker-compose.yml environment section
# 3. env_file (.env)
# 4. Dockerfile ENV

# View effective configuration
docker compose config | grep -A 5 environment

# Debug specific variable
docker compose exec backend env | grep COLLECTIONDB_HOST
```

## Related Documentation

- [Debugging Guide](debugging.md) - General debugging techniques
- [Performance Troubleshooting](performance.md) - Container performance
- [Cloud Deployment](../deployment/cloud.md) - Production Docker deployment
- [Common Issues](common-issues.md) - Quick fixes for frequent problems
