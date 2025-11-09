# Performance Troubleshooting Guide

This guide covers performance profiling, bottleneck analysis, and optimization techniques for RAG Modulo in development and production environments.

## Table of Contents

- [Overview](#overview)
- [Performance Metrics](#performance-metrics)
- [Profiling Tools](#profiling-tools)
- [Database Performance](#database-performance)
- [Vector Database Performance](#vector-database-performance)
- [LLM API Performance](#llm-api-performance)
- [Search Pipeline Performance](#search-pipeline-performance)
- [Optimization Strategies](#optimization-strategies)

## Overview

RAG Modulo performance depends on multiple factors:

1. **Database Performance**: PostgreSQL query optimization
2. **Vector Search**: Milvus index types and search parameters
3. **LLM API Latency**: WatsonX/OpenAI/Anthropic response times
4. **Network I/O**: API calls, database connections
5. **Application Logic**: Python code efficiency
6. **Resource Allocation**: CPU, memory, disk I/O

**Typical Performance Targets**:
- Health check: < 100ms
- Simple search: < 2s
- Complex search (with CoT): < 10s
- Document ingestion: < 5s per document
- API response (p95): < 5s

## Performance Metrics

### Application-Level Metrics

**Pipeline Stage Timing** (via enhanced logging):

```python
# File: backend/rag_solution/services/search_service.py
from core.logging_context import pipeline_stage_context, PipelineStage
import time

async def search(self, search_input: SearchInput):
    overall_start = time.time()

    with pipeline_stage_context(PipelineStage.QUERY_REWRITING):
        rewrite_start = time.time()
        rewritten = await self._rewrite_query(search_input.question)
        self.logger.info(
            "Query rewriting completed",
            extra={"execution_time_ms": (time.time() - rewrite_start) * 1000}
        )

    with pipeline_stage_context(PipelineStage.RETRIEVAL):
        retrieval_start = time.time()
        docs = await self._retrieve_documents(rewritten)
        self.logger.info(
            "Document retrieval completed",
            extra={"execution_time_ms": (time.time() - retrieval_start) * 1000}
        )

    # ... more stages ...

    total_time = (time.time() - overall_start) * 1000
    self.logger.info("Search completed", extra={"execution_time_ms": total_time})
```

**Analyzing Pipeline Performance**:

```bash
# Find slow pipeline stages
cat logs/rag_modulo.log | jq 'select(.context.pipeline_stage) | {stage: .context.pipeline_stage, time: .execution_time_ms}' | jq -s 'group_by(.stage) | map({stage: .[0].stage, avg_time: (map(.time) | add / length), max_time: (map(.time) | max)})'

# Output:
# [
#   {"stage": "query_rewriting", "avg_time": 234.5, "max_time": 450.2},
#   {"stage": "retrieval", "avg_time": 1234.8, "max_time": 3500.0},
#   {"stage": "generation", "avg_time": 2345.6, "max_time": 8000.0}
# ]
```

### System-Level Metrics

**Docker Container Stats**:

```bash
# Real-time monitoring
docker stats

# One-shot stats
docker stats --no-stream

# Specific container
docker stats rag-modulo-backend-1 --no-stream

# JSON format for parsing
docker stats --format "{{json .}}" --no-stream | jq '.'

# Memory usage over time
while true; do
    docker stats --no-stream --format "{{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}" | grep backend
    sleep 5
done
```

**PostgreSQL Stats**:

```sql
-- Connection stats
SELECT count(*) as connections,
       state,
       wait_event_type,
       wait_event
FROM pg_stat_activity
GROUP BY state, wait_event_type, wait_event;

-- Database size
SELECT pg_size_pretty(pg_database_size('rag_modulo_db'));

-- Table sizes
SELECT schemaname,
       tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Cache hit ratio (should be >90%)
SELECT
    sum(heap_blks_read) as heap_read,
    sum(heap_blks_hit)  as heap_hit,
    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as cache_hit_ratio
FROM pg_statio_user_tables;
```

**Milvus Metrics**:

```bash
# Metrics endpoint
curl http://localhost:9091/metrics

# Parse specific metrics
curl -s http://localhost:9091/metrics | grep milvus_search_latency

# Collection statistics
curl -X POST http://localhost:9091/api/v1/collection/statistics \
  -H "Content-Type: application/json" \
  -d '{"collection_name": "documents"}' | jq '.'
```

## Profiling Tools

### Python cProfile

**Profile entire application**:

```bash
# Run backend with profiling
cd /home/user/rag_modulo
poetry run python -m cProfile -o profile.stats backend/main.py

# Analyze profile
poetry run python -m pstats profile.stats
>>> sort cumulative
>>> stats 20  # Top 20 functions by cumulative time
>>> sort tottime
>>> stats 20  # Top 20 functions by total time
```

**Profile specific function**:

```python
import cProfile
import pstats
from io import StringIO

def profile_search(search_service, search_input):
    profiler = cProfile.Profile()
    profiler.enable()

    result = search_service.search(search_input)

    profiler.disable()
    s = StringIO()
    stats = pstats.Stats(profiler, stream=s)
    stats.sort_stats('cumulative')
    stats.print_stats(20)
    print(s.getvalue())

    return result
```

### line_profiler (Line-by-Line Profiling)

```bash
# Install
poetry add --dev line-profiler

# Add @profile decorator to function
# File: backend/rag_solution/services/search_service.py
@profile
async def search(self, search_input: SearchInput):
    # ... function code ...
    pass

# Run with line_profiler
poetry run kernprof -l -v backend/main.py
```

### memory_profiler (Memory Usage)

```bash
# Install
poetry add --dev memory-profiler

# Add @profile decorator
from memory_profiler import profile

@profile
async def search(self, search_input: SearchInput):
    # ... function code ...
    pass

# Run
poetry run python -m memory_profiler backend/main.py

# Output:
# Line #    Mem usage    Increment  Occurrences   Line Contents
# =====================================================
#     10    50.0 MiB     0.0 MiB           1   @profile
#     11                                       async def search(self, search_input):
#     12    55.2 MiB     5.2 MiB           1       docs = await self._retrieve_documents()
```

### py-spy (Sampling Profiler)

```bash
# Install
pip install py-spy

# Profile running process (no code changes needed!)
# Get process ID
PID=$(docker compose exec backend pgrep -f uvicorn)

# Record profile
docker compose exec backend py-spy record -o profile.svg --pid $PID

# Generate flamegraph
docker compose exec backend py-spy record -o flamegraph.svg --format speedscope --pid $PID

# Top functions in real-time
docker compose exec backend py-spy top --pid $PID
```

## Database Performance

### Slow Query Analysis

**Enable slow query logging**:

```sql
-- Set log threshold to 1 second
ALTER SYSTEM SET log_min_duration_statement = 1000;
SELECT pg_reload_conf();

-- Check current setting
SHOW log_min_duration_statement;
```

**Analyze slow queries**:

```sql
-- Install pg_stat_statements extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- View slowest queries
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time,
    stddev_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Queries consuming most time
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

**Query Execution Plans**:

```sql
-- Get execution plan (without executing)
EXPLAIN SELECT * FROM collections WHERE user_id = 'uuid-here';

-- Get execution plan with costs
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM collections WHERE user_id = 'uuid-here';

-- Look for:
-- - Sequential scans (should use indexes)
-- - High cost operations
-- - Large row estimates
```

### Index Optimization

**Check existing indexes**:

```sql
-- List all indexes
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- Index usage statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan;

-- Unused indexes (idx_scan = 0)
SELECT
    schemaname,
    tablename,
    indexname
FROM pg_stat_user_indexes
WHERE idx_scan = 0
AND schemaname = 'public';
```

**Create performance indexes**:

```sql
-- Index on frequently queried columns
CREATE INDEX idx_collections_user_id ON collections(user_id);
CREATE INDEX idx_conversations_collection_id ON conversations(collection_id);
CREATE INDEX idx_conversations_user_id ON conversations(user_id);

-- Composite index for common query patterns
CREATE INDEX idx_conversations_user_collection ON conversations(user_id, collection_id);

-- Partial index for active records
CREATE INDEX idx_active_collections ON collections(id) WHERE deleted_at IS NULL;

-- Index on foreign keys
CREATE INDEX idx_documents_collection_id ON documents(collection_id);
```

### Connection Pooling

**Current Configuration**:

```python
# File: backend/rag_solution/file_management/database.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,          # Number of connections to maintain
    max_overflow=10,      # Max connections beyond pool_size
    pool_timeout=30,      # Timeout waiting for connection
    pool_recycle=3600,    # Recycle connections after 1 hour
    pool_pre_ping=True,   # Validate connections before use
)
```

**Optimize Pool Settings**:

```python
# For high-concurrency workloads
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,         # Increase for more concurrent requests
    max_overflow=30,
    pool_timeout=10,      # Fail fast under load
    pool_recycle=1800,    # Recycle more frequently
)
```

## Vector Database Performance

### Milvus Index Types

**Index Selection Guide**:

```python
# File: backend/vectordbs/milvus_store.py

# FLAT (Exact search, best accuracy, slowest)
# Use for: Small datasets (<10k vectors), highest accuracy required
index_params = {
    "index_type": "FLAT",
    "metric_type": "L2"
}

# IVF_FLAT (Fast, good accuracy)
# Use for: Medium datasets (10k-1M vectors), balanced performance
index_params = {
    "index_type": "IVF_FLAT",
    "metric_type": "L2",
    "params": {"nlist": 1024}  # Number of clusters (sqrt(n) to 4*sqrt(n))
}

# IVF_SQ8 (Faster, reduced memory, slight accuracy loss)
# Use for: Large datasets (>1M vectors), memory constrained
index_params = {
    "index_type": "IVF_SQ8",
    "metric_type": "L2",
    "params": {"nlist": 1024}
}

# HNSW (Fastest, highest memory, excellent accuracy)
# Use for: Real-time search, highest performance required
index_params = {
    "index_type": "HNSW",
    "metric_type": "L2",
    "params": {
        "M": 16,              # Max connections per layer (4-64, 16 recommended)
        "efConstruction": 200 # Build-time accuracy (100-500)
    }
}
```

**Search Parameter Tuning**:

```python
# IVF search parameters
search_params = {
    "metric_type": "L2",
    "params": {
        "nprobe": 16  # Number of clusters to search (1-nlist)
                      # Higher = more accurate, slower
                      # Recommended: 8-32
    }
}

# HNSW search parameters
search_params = {
    "metric_type": "L2",
    "params": {
        "ef": 64  # Search-time accuracy (top_k to 512)
                  # Higher = more accurate, slower
                  # Recommended: 32-128
    }
}
```

**Performance Benchmarking**:

```python
import time
from pymilvus import Collection

collection = Collection("documents")

# Test different search parameters
for nprobe in [8, 16, 32, 64]:
    search_params = {"metric_type": "L2", "params": {"nprobe": nprobe}}

    start = time.time()
    results = collection.search(
        data=[embedding],
        anns_field="embedding",
        param=search_params,
        limit=10
    )
    elapsed = time.time() - start

    print(f"nprobe={nprobe}: {elapsed*1000:.2f}ms, {len(results[0])} results")
```

### Milvus Resource Tuning

**Memory Configuration** (docker-compose-infra.yml):

```yaml
milvus-standalone:
  deploy:
    resources:
      limits:
        memory: 8G  # Increase for larger datasets
      reservations:
        memory: 4G
  environment:
    # Cache size (in MB)
    - CACHE_SIZE=4096  # 4GB cache for vector data
```

**Query Optimization**:

```python
# Batch queries for better throughput
embeddings = [emb1, emb2, emb3, ...]  # Multiple queries
results = collection.search(
    data=embeddings,
    anns_field="embedding",
    param=search_params,
    limit=10
)

# Use expression filtering efficiently
# Good: Filter on indexed column
results = collection.search(
    data=[embedding],
    anns_field="embedding",
    param=search_params,
    expr="collection_id == 'uuid-here'",  # Indexed field
    limit=10
)

# Bad: Filter on non-indexed column
results = collection.search(
    data=[embedding],
    anns_field="embedding",
    param=search_params,
    expr="metadata.field == 'value'",  # Slow JSON filter
    limit=10
)
```

## LLM API Performance

### API Call Optimization

**Async Requests** (current implementation):

```python
# File: backend/rag_solution/generation/providers/watsonx_provider.py
import httpx

async def generate(self, prompt: str) -> str:
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            self.api_url,
            headers=self.headers,
            json=payload
        )
    return response.json()
```

**Batch Requests** (for multiple queries):

```python
import asyncio

async def batch_generate(prompts: list[str]) -> list[str]:
    tasks = [provider.generate(prompt) for prompt in prompts]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

**Caching LLM Responses**:

```python
from functools import lru_cache
import hashlib

class LLMProvider:
    def __init__(self):
        self.cache = {}

    async def generate_cached(self, prompt: str) -> str:
        # Generate cache key
        cache_key = hashlib.sha256(prompt.encode()).hexdigest()

        # Check cache
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Generate response
        response = await self.generate(prompt)

        # Store in cache (with TTL in production)
        self.cache[cache_key] = response

        return response
```

### Timeout Configuration

**Request Timeouts**:

```python
# File: backend/rag_solution/generation/providers/base_provider.py

# Current settings
async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minutes
    response = await client.post(...)

# For production (fail faster)
async with httpx.AsyncClient(
    timeout=httpx.Timeout(
        connect=5.0,   # Connection timeout: 5s
        read=60.0,     # Read timeout: 60s
        write=10.0,    # Write timeout: 10s
        pool=5.0       # Pool timeout: 5s
    )
) as client:
    response = await client.post(...)
```

**Retry Logic** (for transient failures):

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def generate_with_retry(self, prompt: str) -> str:
    return await self.generate(prompt)
```

## Search Pipeline Performance

### Chain of Thought Performance

**CoT Performance Characteristics**:

- **Without CoT**: 1-3s (simple retrieval + generation)
- **With CoT**: 3-10s (multi-step reasoning + retries)
- **CoT with Retries**: Up to 15s (3 retries × 5s per attempt)

**Optimize CoT Configuration**:

```python
# File: backend/rag_solution/schemas/search_schema.py

# Default settings (balanced)
config_metadata = {
    "cot_enabled": True,
    "cot_config": {
        "max_reasoning_depth": 3,  # Reduce to 2 for faster response
        "quality_threshold": 0.6,  # Lower = fewer retries
        "max_retries": 3           # Reduce to 1-2 for speed
    }
}

# Fast mode (lower quality, faster)
config_metadata = {
    "cot_enabled": False,  # Skip CoT entirely
}

# Or minimal CoT
config_metadata = {
    "cot_enabled": True,
    "cot_config": {
        "max_reasoning_depth": 1,  # Single step
        "quality_threshold": 0.4,  # Accept lower quality
        "max_retries": 1           # Only one retry
    }
}
```

### Embedding Generation

**Batch Embeddings** (for document ingestion):

```python
# Current: One document at a time
for doc in documents:
    embedding = await embedding_service.embed(doc.text)
    # ... store embedding ...

# Optimized: Batch processing
batch_size = 32
for i in range(0, len(documents), batch_size):
    batch = documents[i:i+batch_size]
    texts = [doc.text for doc in batch]
    embeddings = await embedding_service.embed_batch(texts)
    # ... store embeddings ...
```

## Optimization Strategies

### Application-Level Optimizations

**1. Database Query Optimization**:

```python
# Before: N+1 query problem
for collection in collections:
    owner = db.query(User).filter(User.id == collection.owner_id).first()
    # ... use owner ...

# After: Join with eager loading
from sqlalchemy.orm import joinedload

collections = db.query(Collection)\
    .options(joinedload(Collection.owner))\
    .all()
```

**2. Async I/O**:

```python
# Before: Sequential API calls
result1 = await api_call_1()
result2 = await api_call_2()
result3 = await api_call_3()

# After: Parallel API calls
results = await asyncio.gather(
    api_call_1(),
    api_call_2(),
    api_call_3()
)
```

**3. Response Caching**:

```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

@router.get("/collections")
@cache(expire=60)  # Cache for 60 seconds
async def get_collections(user_id: str):
    return db.query(Collection).filter_by(user_id=user_id).all()
```

### Infrastructure Optimizations

**1. Resource Allocation**:

```yaml
# docker-compose.production.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '4.0'    # Increase CPU
          memory: 8G     # Increase memory
        reservations:
          cpus: '2.0'
          memory: 4G
```

**2. Container Scaling** (Kubernetes):

```yaml
# backend-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**3. Load Balancing**:

```nginx
# nginx.conf
upstream backend {
    least_conn;  # Least connections algorithm
    server backend-1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server backend-2:8000 weight=1 max_fails=3 fail_timeout=30s;
    server backend-3:8000 weight=1 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl http2;

    location / {
        proxy_pass http://backend;
        proxy_next_upstream error timeout http_502 http_503 http_504;
    }
}
```

### Monitoring Performance Improvements

**Before/After Comparison**:

```bash
# Benchmark before optimization
ab -n 1000 -c 10 http://localhost:8000/api/health

# Apply optimization
# ... make changes ...

# Benchmark after optimization
ab -n 1000 -c 10 http://localhost:8000/api/health

# Compare results:
# - Requests per second
# - Mean response time
# - 95th percentile latency
```

**Load Testing**:

```bash
# Install locust
pip install locust

# Create locustfile.py
from locust import HttpUser, task, between

class RAGUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def search(self):
        self.client.post("/api/search", json={
            "question": "What is machine learning?",
            "collection_id": "uuid-here",
            "user_id": "uuid-here"
        })

# Run load test
locust -f locustfile.py --host=http://localhost:8000
```

## Related Documentation

- [Debugging Guide](debugging.md) - Debug tools and techniques
- [Docker Troubleshooting](docker.md) - Container performance
- [Monitoring Guide](../deployment/monitoring.md) - Performance metrics
- [Database Management](../development/backend/database.md) - Database optimization
