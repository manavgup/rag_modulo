# Debugging Guide

This guide covers debugging tools, techniques, and common issues for RAG Modulo development and production environments.

## Table of Contents

- [Overview](#overview)
- [Debug Tools](#debug-tools)
- [Logging & Log Analysis](#logging--log-analysis)
- [Database Debugging](#database-debugging)
- [Vector Database Debugging](#vector-database-debugging)
- [API Debugging](#api-debugging)
- [Common Issues](#common-issues)
- [Production Debugging](#production-debugging)

## Overview

RAG Modulo provides multiple debugging layers:

1. **Enhanced Logging**: Structured JSON/text logs with context tracking
2. **Health Checks**: Service-level health monitoring
3. **Docker Logs**: Container-level debugging
4. **Interactive Debugging**: Python debugger (pdb) support
5. **Database Tools**: PostgreSQL and Milvus query tools
6. **API Documentation**: Interactive API docs at `/docs`

## Debug Tools

### Python Debugger (pdb)

**Interactive Debugging**:

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint() (Python 3.7+)
breakpoint()

# Example: Debug search service
# File: backend/rag_solution/services/search_service.py
async def search(self, search_input: SearchInput):
    breakpoint()  # Execution will pause here
    # ... search logic ...
```

**Running with debugger**:

```bash
# Local development (containerless)
cd /home/user/rag_modulo
poetry run python -m pdb backend/main.py

# Or with uvicorn
poetry run uvicorn main:app --reload

# When breakpoint() is hit:
# (Pdb) n          # Next line
# (Pdb) s          # Step into function
# (Pdb) c          # Continue execution
# (Pdb) l          # List source code
# (Pdb) p variable # Print variable
# (Pdb) pp dict    # Pretty print dict
# (Pdb) q          # Quit debugger
```

### VS Code Debugging

**Configuration** (`.vscode/launch.json`):

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Backend: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "cwd": "${workspaceFolder}/backend",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/backend",
        "DEVELOPMENT_MODE": "true"
      },
      "console": "integratedTerminal"
    },
    {
      "name": "Backend: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/backend"
      },
      "console": "integratedTerminal"
    },
    {
      "name": "Pytest: Current File",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "${file}",
        "-v",
        "-s"
      ],
      "cwd": "${workspaceFolder}",
      "console": "integratedTerminal"
    }
  ]
}
```

### IPython Interactive Shell

```bash
# Install ipython
poetry add --dev ipython

# Start interactive shell with context
poetry run ipython

# Load application context
from rag_solution.file_management.database import get_db, engine
from rag_solution.services.search_service import SearchService
from core.config import get_settings

# Test database connection
with engine.connect() as conn:
    result = conn.execute("SELECT 1")
    print(result.fetchone())

# Test service
settings = get_settings()
db = next(get_db())
search_service = SearchService(db, settings)
```

### Docker Debugging

**Attach to running container**:

```bash
# List containers
docker compose ps

# Attach shell to backend
docker compose exec backend /bin/bash

# Or with poetry shell
docker compose exec backend poetry shell

# Run Python commands
docker compose exec backend python -c "
from rag_solution.file_management.database import engine
print(engine.url)
"

# Check environment variables
docker compose exec backend env | grep COLLECTION

# View file contents
docker compose exec backend cat /app/main.py

# Test API endpoint
docker compose exec backend curl http://localhost:8000/api/health
```

**Debug container startup issues**:

```bash
# View container logs
docker compose logs backend

# Follow logs in real-time
docker compose logs -f backend

# View last 50 lines
docker compose logs --tail 50 backend

# Filter logs by level
docker compose logs backend | grep ERROR
docker compose logs backend | grep -i exception

# Inspect container
docker inspect rag-modulo-backend-1

# Check container processes
docker compose exec backend ps aux

# Check disk space
docker compose exec backend df -h
```

## Logging & Log Analysis

### Enhanced Logging System

**Location**: `/home/user/rag_modulo/backend/core/enhanced_logging.py`

**Key Features**:
- Dual output (JSON for production, text for development)
- Context tracking (collection_id, user_id, request_id)
- Pipeline stage tracking
- In-memory queryable storage

### Viewing Logs

**Local Development**:

```bash
# Log location
ls -la /home/user/rag_modulo/logs/

# View logs
tail -f logs/rag_modulo.log

# Filter by level
grep ERROR logs/rag_modulo.log
grep -i exception logs/rag_modulo.log

# JSON logs (use jq for parsing)
cat logs/rag_modulo.log | jq 'select(.levelname == "ERROR")'
cat logs/rag_modulo.log | jq 'select(.context.collection_id == "YOUR_COLLECTION_ID")'
```

**Container Logs**:

```bash
# All backend logs
docker compose logs backend

# Follow logs
docker compose logs -f backend

# Since timestamp
docker compose logs --since 2025-01-09T14:00:00 backend

# Multiple services
docker compose logs backend postgres milvus-standalone

# Export logs to file
docker compose logs backend > backend-logs-$(date +%Y%m%d).log
```

### Log Analysis Examples

**Find errors in last hour**:

```bash
# Docker logs
docker compose logs --since 1h backend | grep ERROR

# Local logs
find logs/ -name "*.log" -mmin -60 -exec grep ERROR {} \;

# JSON logs with jq
cat logs/rag_modulo.log | jq 'select(.timestamp > "'$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)'")'
```

**Track request by correlation ID**:

```bash
# Find all logs for specific request
CORRELATION_ID="req_abc123"
cat logs/rag_modulo.log | jq "select(.context.correlation_id == \"$CORRELATION_ID\")"

# Or with grep
docker compose logs backend | grep $CORRELATION_ID
```

**Analyze search performance**:

```bash
# Find slow searches (>5 seconds)
cat logs/rag_modulo.log | jq 'select(.execution_time_ms > 5000)'

# Group by pipeline stage
cat logs/rag_modulo.log | jq 'select(.context.pipeline_stage) | {stage: .context.pipeline_stage, time: .execution_time_ms}'
```

### Log-Based Debugging Patterns

**Pattern 1: Find root cause of failure**:

```bash
# Get error message
ERROR_MSG="Database connection failed"
docker compose logs backend | grep -A 20 "$ERROR_MSG"

# Find when error started
docker compose logs --since 24h backend | grep "$ERROR_MSG" | head -1

# Check logs before error
docker compose logs --until $(date -d '5 minutes ago' -u +%Y-%m-%dT%H:%M:%S) backend
```

**Pattern 2: Trace user request flow**:

```python
# Add correlation tracking to log queries
from core.log_storage_service import LogStorageService

log_storage = LogStorageService.get_instance()

# Find all logs for user
user_logs = log_storage.query_logs(
    entity_type="user",
    entity_id="user-uuid-here",
    limit=100
)

for log in user_logs:
    print(f"{log.timestamp} [{log.level}] {log.message}")
```

## Database Debugging

### PostgreSQL Debugging

**Connect to database**:

```bash
# Via Docker
docker compose exec postgres psql -U postgres -d rag_modulo_db

# Via local psql
psql -h localhost -p 5432 -U postgres -d rag_modulo_db
```

**Common SQL queries**:

```sql
-- List all tables
\dt

-- Describe table structure
\d+ collections
\d+ users
\d+ conversations

-- Count records
SELECT COUNT(*) FROM collections;
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM conversations;

-- Find recent collections
SELECT id, name, created_at
FROM collections
ORDER BY created_at DESC
LIMIT 10;

-- Check database size
SELECT pg_size_pretty(pg_database_size('rag_modulo_db'));

-- Find active connections
SELECT pid, usename, application_name, client_addr, state
FROM pg_stat_activity
WHERE datname = 'rag_modulo_db';

-- Find slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check for locks
SELECT * FROM pg_locks
WHERE NOT granted;

-- Analyze table statistics
ANALYZE collections;
VACUUM ANALYZE collections;
```

**Debug database connection issues**:

```python
# Test connection from Python
# File: debug_database.py
from rag_solution.file_management.database import engine, get_db
from sqlalchemy import text

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Database connected:", result.fetchone())

        # Check tables
        result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
        print("Tables:", [row[0] for row in result])

except Exception as e:
    print("❌ Database connection failed:", e)
    import traceback
    traceback.print_exc()
```

**Reset database**:

```bash
# WARNING: This deletes all data!
docker compose down -v  # Remove volumes
docker compose up -d    # Recreate with fresh DB

# Or manually
docker compose exec postgres psql -U postgres -c "DROP DATABASE rag_modulo_db;"
docker compose exec postgres psql -U postgres -c "CREATE DATABASE rag_modulo_db;"
```

## Vector Database Debugging

### Milvus Debugging

**Check Milvus health**:

```bash
# Health check
curl http://localhost:9091/healthz

# Metrics endpoint
curl http://localhost:9091/metrics

# Via Docker
docker compose exec milvus-standalone curl http://localhost:9091/healthz
```

**Milvus CLI**:

```bash
# Install Milvus CLI
pip install pymilvus

# Connect to Milvus
python
>>> from pymilvus import connections, utility
>>> connections.connect(host='localhost', port='19530')
>>> print("Collections:", utility.list_collections())

# Get collection info
>>> from pymilvus import Collection
>>> collection = Collection("documents")
>>> print("Count:", collection.num_entities)
>>> print("Schema:", collection.schema)

# Search test
>>> search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
>>> results = collection.search(
...     data=[[0.1]*384],  # Example embedding
...     anns_field="embedding",
...     param=search_params,
...     limit=10
... )
>>> print("Results:", results)
```

**Debug Milvus issues**:

```bash
# Check Milvus logs
docker compose logs milvus-standalone | tail -100

# Check etcd (Milvus dependency)
docker compose logs milvus-etcd | tail -100

# Check MinIO (Milvus storage)
docker compose logs minio | tail -100

# Restart Milvus
docker compose restart milvus-standalone
docker compose restart milvus-etcd
```

**Common Milvus errors**:

```bash
# Error: "collection not found"
# Solution: Check collection exists
python -c "from pymilvus import connections, utility; connections.connect(); print(utility.list_collections())"

# Error: "index not built"
# Solution: Build index
python -c "from pymilvus import Collection; c = Collection('documents'); c.create_index('embedding', {'index_type': 'IVF_FLAT', 'metric_type': 'L2', 'params': {'nlist': 128}})"

# Error: "dimension mismatch"
# Solution: Check embedding dimension matches collection schema
python -c "from pymilvus import Collection; c = Collection('documents'); print(c.schema)"
```

## API Debugging

### Interactive API Documentation

**Swagger UI**: `http://localhost:8000/docs`

- View all endpoints
- Test API calls directly
- See request/response schemas
- Inspect error responses

**ReDoc**: `http://localhost:8000/redoc`

- Alternative API documentation
- Better for reading/reference

### Testing API Endpoints

**Health check**:

```bash
# Basic health
curl http://localhost:8000/api/health

# With verbose output
curl -v http://localhost:8000/api/health

# Check response time
time curl http://localhost:8000/api/health
```

**Authenticated requests**:

```bash
# Login to get token
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test@example.com","password":"password"}' \
  | jq -r '.access_token')

# Use token in requests
curl http://localhost:8000/api/collections \
  -H "Authorization: Bearer $TOKEN"

# Search request
curl -X POST http://localhost:8000/api/search \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is machine learning?",
    "collection_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "123e4567-e89b-12d3-a456-426614174000"
  }'
```

**Debug API errors**:

```bash
# Verbose output with headers
curl -v http://localhost:8000/api/search

# Include timing information
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/health

# curl-format.txt:
#     time_namelookup:  %{time_namelookup}\n
#        time_connect:  %{time_connect}\n
#     time_appconnect:  %{time_appconnect}\n
#    time_pretransfer:  %{time_pretransfer}\n
#       time_redirect:  %{time_redirect}\n
#  time_starttransfer:  %{time_starttransfer}\n
#                     ----------\n
#          time_total:  %{time_total}\n
```

### FastAPI Request Inspection

```python
# Add request inspection middleware
# File: backend/core/debug_middleware.py

from fastapi import Request
import time

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Log request
    print(f"→ {request.method} {request.url}")
    print(f"  Headers: {dict(request.headers)}")
    print(f"  Client: {request.client.host}:{request.client.port}")

    # Process request
    response = await call_next(request)

    # Log response
    process_time = time.time() - start_time
    print(f"← {response.status_code} ({process_time:.3f}s)")

    return response
```

## Common Issues

### Issue 1: Import Errors

**Symptom**:
```
ModuleNotFoundError: No module named 'rag_solution'
```

**Solution**:
```bash
# Check PYTHONPATH
echo $PYTHONPATH

# Set PYTHONPATH
export PYTHONPATH=/home/user/rag_modulo/backend:$PYTHONPATH

# Or use poetry run
cd /home/user/rag_modulo
poetry run python backend/main.py

# In Docker, PYTHONPATH is set in Dockerfile
ENV PYTHONPATH=/app:/app/vectordbs:/app/rag_solution:/app/core
```

### Issue 2: Database Migration Failures

**Symptom**:
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solution**:
```bash
# Check PostgreSQL is running
docker compose ps postgres

# Check PostgreSQL logs
docker compose logs postgres | tail -50

# Test connection
docker compose exec postgres pg_isready -U postgres

# Verify credentials
docker compose exec backend env | grep COLLECTIONDB

# Manual connection test
docker compose exec backend python -c "
from rag_solution.file_management.database import engine
print(engine.url)
with engine.connect() as conn:
    print('Connected!')
"
```

### Issue 3: Milvus Connection Timeout

**Symptom**:
```
MilvusException: <MilvusException: (code=1, message=Fail connecting to server)>
```

**Solution**:
```bash
# Check Milvus is healthy
curl http://localhost:9091/healthz

# Check Milvus dependencies
docker compose ps milvus-etcd minio

# Restart Milvus stack
docker compose restart milvus-etcd
docker compose restart minio
docker compose restart milvus-standalone

# Check Milvus logs
docker compose logs milvus-standalone | grep -i error
```

### Issue 4: LLM Provider Errors

**Symptom**:
```
HTTPError: 401 Unauthorized - Invalid API key
```

**Solution**:
```bash
# Check API key is set
docker compose exec backend env | grep WATSONX_APIKEY

# Test API key manually
curl -H "Authorization: Bearer YOUR_API_KEY" https://us-south.ml.cloud.ibm.com/ml/v1/deployments

# Clear provider cache
docker compose exec backend python -c "
from rag_solution.generation.providers.factory import LLMProviderFactory
from rag_solution.file_management.database import get_db
from core.config import get_settings

db = next(get_db())
settings = get_settings()
factory = LLMProviderFactory(db, settings)
factory.cleanup_all()
print('Provider cache cleared')
"
```

## Production Debugging

### Production Log Analysis

```bash
# Find errors in last hour
docker compose logs --since 1h backend | grep -i error

# Count errors by type
docker compose logs backend | grep ERROR | sort | uniq -c | sort -rn

# Find slow requests (>10s)
cat /app/logs/rag_modulo.log | jq 'select(.execution_time_ms > 10000)'

# Memory usage over time
docker stats --no-stream | grep backend
```

### Health Check Monitoring

```bash
# Continuous health monitoring
while true; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health)
    if [ $STATUS -ne 200 ]; then
        echo "$(date): ❌ Health check failed: $STATUS"
        # Send alert (Slack, email, PagerDuty, etc.)
    else
        echo "$(date): ✅ Healthy"
    fi
    sleep 30
done
```

### Performance Profiling

```python
# Add profiling to specific endpoint
from cProfile import Profile
from pstats import Stats

@router.post("/search")
async def search(search_input: SearchInput):
    profiler = Profile()
    profiler.enable()

    # ... search logic ...
    result = await search_service.search(search_input)

    profiler.disable()
    stats = Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions

    return result
```

## Related Documentation

- [Performance Troubleshooting](performance.md) - Performance optimization guide
- [Docker Troubleshooting](docker.md) - Container-specific issues
- [Authentication Troubleshooting](authentication.md) - Auth debugging
- [Monitoring Guide](../deployment/monitoring.md) - Logging and observability
- [Common Issues](common-issues.md) - Quick solutions to frequent problems
