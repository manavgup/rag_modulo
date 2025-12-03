# Scalability Architecture

This document describes the scalability strategies, patterns, and infrastructure design that enable RAG Modulo to scale from single-user deployments to enterprise-level workloads.

## Overview

RAG Modulo is designed for **horizontal scalability** with the following characteristics:

- **Stateless backend services** - Easy to scale with load balancers
- **Distributed vector database** - Milvus supports clustering
- **Asynchronous processing** - Non-blocking I/O with FastAPI
- **Queue-based document processing** - Decoupled ingestion pipeline
- **Cached LLM provider instances** - Reduced initialization overhead
- **Multi-tenant isolation** - Collection-based data segregation

## Scalability Dimensions

### Vertical Scaling (Scale Up)

**Single Instance Optimization**:

```yaml
# docker-compose.yml
services:
  backend:
    image: ghcr.io/manavgup/rag_modulo/backend:latest
    environment:
      # Increase worker processes
      - WEB_CONCURRENCY=8  # Default: 4, Max: CPU count * 2

      # Tune database connections
      - SQLALCHEMY_POOL_SIZE=20
      - SQLALCHEMY_MAX_OVERFLOW=10

      # Increase vector search limits
      - MAX_TOP_K=100  # Maximum documents per query
      - VECTOR_BATCH_SIZE=1000  # Batch size for vector operations

    resources:
      limits:
        cpus: '4'
        memory: 8G
```

**Recommended Specifications**:
- **Development**: 2 CPU, 4GB RAM
- **Small Production**: 4 CPU, 8GB RAM
- **Medium Production**: 8 CPU, 16GB RAM
- **Large Production**: 16+ CPU, 32GB+ RAM

### Horizontal Scaling (Scale Out)

**Multiple Backend Instances**:

```yaml
# docker-compose.yml
services:
  backend-1:
    image: ghcr.io/manavgup/rag_modulo/backend:latest
    environment:
      - INSTANCE_ID=1

  backend-2:
    image: ghcr.io/manavgup/rag_modulo/backend:latest
    environment:
      - INSTANCE_ID=2

  backend-3:
    image: ghcr.io/manavgup/rag_modulo/backend:latest
    environment:
      - INSTANCE_ID=3

  # Load balancer
  nginx:
    image: nginx:latest
    ports:
      - "8000:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - backend-1
      - backend-2
      - backend-3
```

**Load Balancer Configuration**:

```nginx
# nginx.conf
upstream backend {
    # Least connections algorithm
    least_conn;

    server backend-1:8000 max_fails=3 fail_timeout=30s;
    server backend-2:8000 max_fails=3 fail_timeout=30s;
    server backend-3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Timeouts for long-running operations
        proxy_read_timeout 300s;
        proxy_connect_timeout 30s;
    }

    location /ws {
        # WebSocket support for real-time updates
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Database Scalability

### PostgreSQL Scaling

**Connection Pooling**:

```python
# backend/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    # Connection pooling
    poolclass=QueuePool,
    pool_size=20,  # Persistent connections
    max_overflow=10,  # Burst connections
    pool_pre_ping=True,  # Verify connections
    pool_recycle=3600,  # Recycle after 1 hour

    # Performance tuning
    echo=False,  # Disable SQL logging in production
    future=True,  # Use SQLAlchemy 2.0 style
)
```

**Read Replicas**:

```python
# Separate read and write database connections
class DatabaseConfig:
    def __init__(self):
        # Primary (write) connection
        self.primary_engine = create_engine(
            settings.primary_db_url,
            pool_size=10
        )

        # Read replica connections
        self.replica_engines = [
            create_engine(settings.replica_1_db_url, pool_size=20),
            create_engine(settings.replica_2_db_url, pool_size=20),
        ]

    def get_read_session(self) -> Session:
        """Get session from read replica (load balanced)"""
        engine = random.choice(self.replica_engines)
        return Session(bind=engine)

    def get_write_session(self) -> Session:
        """Get session from primary database"""
        return Session(bind=self.primary_engine)
```

**Query Optimization**:

```python
# Efficient queries with eager loading
def get_collection_with_files(collection_id: UUID) -> Collection:
    return (
        db.query(Collection)
        # Eager load relationships (1 query instead of N+1)
        .options(
            joinedload(Collection.users),
            joinedload(Collection.files),
            joinedload(Collection.pipelines)
        )
        .filter(Collection.id == collection_id)
        .first()
    )
```

### Vector Database Scaling

**Milvus Cluster Configuration**:

```yaml
# docker-compose-milvus-cluster.yml
services:
  milvus-proxy:
    image: milvusdb/milvus:v2.4.15
    command: ["milvus", "run", "proxy"]
    depends_on:
      - milvus-rootcoord
      - milvus-querynode-1
      - milvus-querynode-2

  milvus-rootcoord:
    image: milvusdb/milvus:v2.4.15
    command: ["milvus", "run", "rootcoord"]

  milvus-querynode-1:
    image: milvusdb/milvus:v2.4.15
    command: ["milvus", "run", "querynode"]

  milvus-querynode-2:
    image: milvusdb/milvus:v2.4.15
    command: ["milvus", "run", "querynode"]

  milvus-datanode-1:
    image: milvusdb/milvus:v2.4.15
    command: ["milvus", "run", "datanode"]

  milvus-datanode-2:
    image: milvusdb/milvus:v2.4.15
    command: ["milvus", "run", "datanode"]

  milvus-indexnode:
    image: milvusdb/milvus:v2.4.15
    command: ["milvus", "run", "indexnode"]

  milvus-etcd:
    image: quay.io/coreos/etcd:v3.5.0

  minio:
    image: minio/minio:latest
```

**Collection Sharding**:

```python
# Shard collections by user or organization
class VectorStoreService:
    def create_collection(
        self,
        collection_id: UUID,
        shard_num: int = 2  # Number of shards
    ):
        """Create sharded collection for parallel search"""
        self.milvus_client.create_collection(
            collection_name=str(collection_id),
            schema=self.schema,
            shards_num=shard_num,  # Distribute across shards
            consistency_level="Eventually"  # Faster reads
        )
```

**Index Optimization**:

```python
# HNSW index for fast approximate search
index_params = {
    "index_type": "HNSW",  # Hierarchical Navigable Small World
    "metric_type": "L2",   # Euclidean distance
    "params": {
        "M": 16,           # Number of connections (higher = better accuracy)
        "efConstruction": 256,  # Build time parameter
    }
}

# Create index for fast search
collection.create_index(
    field_name="embedding",
    index_params=index_params
)

# Search with ef parameter
search_params = {
    "metric_type": "L2",
    "params": {"ef": 64}  # Runtime parameter (higher = better accuracy)
}
```

## Caching Strategies

### Application-Level Caching

**LLM Provider Instance Caching**:

```python
# backend/rag_solution/generation/providers/factory.py
class LLMProviderFactory:
    _instances: ClassVar[dict[str, LLMBase]] = {}
    _lock: ClassVar[Lock] = Lock()

    def get_provider(
        self,
        provider_name: str,
        model_id: str
    ) -> LLMBase:
        """Get cached provider instance"""
        cache_key = f"{provider_name}:{model_id}"

        # Check cache first
        if cache_key in self._instances:
            return self._instances[cache_key]

        # Create and cache new instance
        with self._lock:
            if cache_key not in self._instances:
                provider = self._create_provider(provider_name, model_id)
                self._instances[cache_key] = provider

        return self._instances[cache_key]
```

**Embedding Cache**:

```python
from functools import lru_cache
import hashlib

class EmbeddingService:
    def __init__(self):
        self.cache = {}

    @lru_cache(maxsize=10000)
    def embed_text(self, text: str) -> list[float]:
        """Cache embeddings for frequently used text"""
        # Cache key from text hash
        cache_key = hashlib.md5(text.encode()).hexdigest()

        if cache_key in self.cache:
            return self.cache[cache_key]

        # Generate embedding
        embedding = self.model.encode(text)

        # Cache result
        self.cache[cache_key] = embedding

        return embedding
```

### Redis Caching

**Distributed cache for multi-instance deployments**:

```python
import redis
from typing import Any

class RedisCache:
    def __init__(self, host: str = "localhost", port: int = 6379):
        self.client = redis.Redis(
            host=host,
            port=port,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True
        )

    async def get_cached_search_result(
        self,
        query: str,
        collection_id: UUID
    ) -> SearchOutput | None:
        """Get cached search result"""
        cache_key = f"search:{collection_id}:{query}"
        cached = self.client.get(cache_key)

        if cached:
            return SearchOutput.parse_raw(cached)

        return None

    async def cache_search_result(
        self,
        query: str,
        collection_id: UUID,
        result: SearchOutput,
        ttl: int = 3600  # 1 hour TTL
    ):
        """Cache search result"""
        cache_key = f"search:{collection_id}:{query}"
        self.client.setex(
            cache_key,
            ttl,
            result.json()
        )
```

**Add Redis to docker-compose**:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru

  backend:
    depends_on:
      - redis
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
```

## Asynchronous Processing

### Document Processing Queue

**Celery task queue for background processing**:

```python
# backend/core/celery_app.py
from celery import Celery

celery_app = Celery(
    "rag_modulo",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Rate limiting
    task_default_rate_limit="10/m",
    # Concurrency
    worker_concurrency=4,
)

@celery_app.task(bind=True, max_retries=3)
def process_document_task(
    self,
    file_id: str,
    collection_id: str,
    user_id: str
):
    """Background task for document processing"""
    try:
        # Process document
        result = document_processor.process(
            file_id=UUID(file_id),
            collection_id=UUID(collection_id),
            user_id=UUID(user_id)
        )
        return result

    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

**Task submission**:

```python
@router.post("/files/upload")
async def upload_file(file: UploadFile, collection_id: UUID4):
    # Store file
    file_id = await file_service.store_file(file, collection_id)

    # Submit background task
    task = process_document_task.delay(
        file_id=str(file_id),
        collection_id=str(collection_id),
        user_id=str(user_id)
    )

    return {
        "file_id": file_id,
        "task_id": task.id,
        "status": "processing"
    }
```

**Celery workers**:

```yaml
services:
  celery-worker:
    image: ghcr.io/manavgup/rag_modulo/backend:latest
    command: celery -A core.celery_app worker --loglevel=info --concurrency=4
    depends_on:
      - redis
      - postgres
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
```

### Batch Processing

**Batch embeddings for efficiency**:

```python
async def embed_documents_batch(
    documents: list[str],
    batch_size: int = 100
) -> list[list[float]]:
    """Process documents in batches for efficiency"""
    embeddings = []

    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]

        # Batch embedding generation
        batch_embeddings = await embedding_model.encode_batch(batch)

        embeddings.extend(batch_embeddings)

    return embeddings
```

## Multi-Tenancy

### Collection-Based Isolation

**Each user/organization gets isolated collections**:

```python
# Collection naming convention
def get_collection_name(user_id: UUID, collection_id: UUID) -> str:
    """Generate isolated collection name"""
    return f"user_{user_id}_collection_{collection_id}"

# Milvus collection isolation
class VectorStore:
    def create_user_collection(
        self,
        user_id: UUID,
        collection_id: UUID
    ):
        """Create isolated collection for user"""
        collection_name = get_collection_name(user_id, collection_id)

        self.client.create_collection(
            collection_name=collection_name,
            schema=self.schema,
            # Resource allocation
            shards_num=2,
            consistency_level="Eventually"
        )
```

### Resource Quotas

**Per-user resource limits**:

```python
class UserQuotaService:
    def __init__(self, db: Session):
        self.db = db

    async def check_quota(self, user_id: UUID, resource: str) -> bool:
        """Check if user has quota for resource"""
        user = await self.user_service.get_user(user_id)

        quotas = {
            "collections": 10,  # Max collections per user
            "files": 100,       # Max files per collection
            "storage_gb": 10,   # Max storage in GB
            "tokens_per_day": 100000,  # Max LLM tokens per day
        }

        usage = await self._get_usage(user_id, resource)

        return usage < quotas.get(resource, float("inf"))

    async def enforce_quota(self, user_id: UUID, resource: str):
        """Raise exception if quota exceeded"""
        if not await self.check_quota(user_id, resource):
            raise HTTPException(
                status_code=429,
                detail=f"Quota exceeded for {resource}"
            )
```

## Monitoring and Auto-Scaling

### Metrics Collection

**Prometheus metrics for monitoring**:

```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
request_count = Counter(
    "rag_requests_total",
    "Total requests",
    ["method", "endpoint", "status"]
)

request_duration = Histogram(
    "rag_request_duration_seconds",
    "Request duration",
    ["method", "endpoint"]
)

# Search metrics
search_latency = Histogram(
    "rag_search_latency_seconds",
    "Search latency by stage",
    ["stage"]
)

active_connections = Gauge(
    "rag_active_connections",
    "Active database connections"
)

# Vector store metrics
vector_search_duration = Histogram(
    "milvus_search_duration_seconds",
    "Vector search duration"
)

# LLM metrics
llm_token_usage = Counter(
    "llm_tokens_used_total",
    "Total LLM tokens used",
    ["provider", "model", "user_id"]
)
```

**Metrics endpoint**:

```python
from prometheus_client import generate_latest

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

### Kubernetes Auto-Scaling

**Horizontal Pod Autoscaler**:

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: rag-modulo-backend
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rag-modulo-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: rag_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
```

## Performance Targets

### Current Performance

Based on production benchmarks:

| Metric | Value |
|--------|-------|
| Simple search | 0.5-1.0s |
| Complex search (no CoT) | 1.0-2.0s |
| Chain of Thought search | 2.5-5.0s |
| Document processing | 5-30s per file |
| Concurrent requests | 100-500 req/s |
| Vector search | 10-50ms |

### Scaling Targets

| Users | Backend Instances | DB Config | Vector DB |
|-------|------------------|-----------|-----------|
| 1-100 | 1 | Single instance | Standalone |
| 100-1K | 2-4 | Primary + replica | Standalone |
| 1K-10K | 4-10 | Primary + 2 replicas | 2-node cluster |
| 10K+ | 10+ | Sharded cluster | 4+ node cluster |

## Best Practices

### For Development

1. **Use connection pooling** - Reuse database connections
2. **Implement caching** - Cache frequently accessed data
3. **Batch operations** - Process multiple items together
4. **Use async/await** - Non-blocking I/O operations
5. **Profile performance** - Identify bottlenecks early

### For Deployment

1. **Horizontal scaling** - Scale out, not just up
2. **Load balancing** - Distribute traffic evenly
3. **Auto-scaling** - Automatic resource adjustment
4. **Monitoring** - Track metrics and alerts
5. **Capacity planning** - Plan for growth

## Related Documentation

- [Performance](performance.md) - Optimization techniques
- [Components](components.md) - System architecture
- [Deployment - Kubernetes](../deployment/kubernetes.md) - K8s deployment
- [Deployment - Monitoring](../deployment/monitoring.md) - Monitoring setup
