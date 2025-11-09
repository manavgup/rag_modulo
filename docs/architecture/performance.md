# Performance Optimization

This document describes performance optimization techniques, benchmarks, and best practices implemented in RAG Modulo to ensure fast response times and efficient resource utilization.

## Performance Overview

RAG Modulo achieves the following performance characteristics:

| Operation | Latency (P50) | Latency (P95) | Latency (P99) |
|-----------|---------------|---------------|---------------|
| Simple search (no CoT) | 0.8s | 1.5s | 2.0s |
| Complex search (with CoT) | 2.6s | 4.5s | 6.0s |
| Vector search only | 15ms | 40ms | 80ms |
| Document embedding | 50ms/chunk | 100ms/chunk | 150ms/chunk |
| Document processing | 10s/file | 25s/file | 45s/file |

## Database Optimization

### Connection Pooling

**SQLAlchemy connection pooling** reduces connection overhead:

```python
# backend/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,

    # Pool configuration
    pool_size=20,              # Persistent connections
    max_overflow=10,           # Additional burst connections
    pool_pre_ping=True,        # Verify connections before use
    pool_recycle=3600,         # Recycle connections after 1 hour
    pool_timeout=30,           # Wait 30s for connection

    # Performance settings
    echo=False,                # Disable SQL logging
    future=True,               # SQLAlchemy 2.0 style
)
```

### Query Optimization

**Eager loading** prevents N+1 query problems:

```python
# Bad: N+1 queries (1 + N where N = number of collections)
collections = db.query(Collection).all()
for collection in collections:
    files = collection.files  # Separate query for each collection
    users = collection.users  # Another separate query

# Good: 1 query with joins
collections = (
    db.query(Collection)
    .options(
        joinedload(Collection.files),
        joinedload(Collection.users)
    )
    .all()
)
```

**Selective field loading** reduces data transfer:

```python
# Load only needed fields
users = (
    db.query(User.id, User.email, User.name)
    .filter(User.role == "user")
    .all()
)

# Instead of loading entire User objects with all relationships
```

### Indexing Strategy

**Database indexes** for frequently queried fields:

```python
# backend/rag_solution/models/collection.py
class Collection(Base):
    __tablename__ = "collections"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String, index=True)  # Index for name searches
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    created_at = Column(DateTime, index=True)  # Index for time-based queries
    status = Column(String, index=True)  # Index for status filtering

    # Composite index for common query patterns
    __table_args__ = (
        Index("ix_collection_user_status", "user_id", "status"),
        Index("ix_collection_created_at", "created_at"),
    )
```

### Query Pagination

**Cursor-based pagination** for large result sets:

```python
def get_collections_paginated(
    user_id: UUID,
    cursor: str | None = None,
    limit: int = 20
) -> tuple[list[Collection], str | None]:
    """Efficient pagination using cursor"""
    query = (
        db.query(Collection)
        .filter(Collection.user_id == user_id)
        .order_by(Collection.created_at.desc())
    )

    if cursor:
        # Decode cursor to get last seen timestamp
        last_seen = datetime.fromisoformat(cursor)
        query = query.filter(Collection.created_at < last_seen)

    # Fetch one extra to check if more results exist
    collections = query.limit(limit + 1).all()

    has_next = len(collections) > limit
    collections = collections[:limit]

    # Generate next cursor
    next_cursor = None
    if has_next and collections:
        next_cursor = collections[-1].created_at.isoformat()

    return collections, next_cursor
```

## Vector Database Optimization

### Index Configuration

**HNSW index** for fast approximate nearest neighbor search:

```python
# backend/vectordbs/milvus/store.py
class MilvusStore:
    def create_index(self, collection_name: str):
        """Create optimized HNSW index"""
        index_params = {
            "index_type": "HNSW",
            "metric_type": "L2",
            "params": {
                "M": 16,                # Connections per node (8-48)
                "efConstruction": 256,  # Build time parameter (64-512)
            }
        }

        self.collection.create_index(
            field_name="embedding",
            index_params=index_params
        )

        # Load index into memory for fast search
        self.collection.load()
```

**Index parameter tuning**:

| Parameter | Low Accuracy | Balanced | High Accuracy |
|-----------|--------------|----------|---------------|
| M | 8 | 16 | 32 |
| efConstruction | 64 | 256 | 512 |
| ef (search) | 32 | 64 | 128 |
| Latency | ~10ms | ~20ms | ~40ms |
| Recall | ~85% | ~95% | ~99% |

### Search Optimization

**Batch vector search** for multiple queries:

```python
async def batch_search(
    queries: list[str],
    collection_name: str,
    top_k: int = 10
) -> list[list[QueryResult]]:
    """Search multiple queries in one batch"""
    # Generate embeddings in batch
    embeddings = await embedding_service.embed_batch(queries)

    # Execute batch search
    results = self.collection.search(
        data=embeddings,
        anns_field="embedding",
        param={"metric_type": "L2", "params": {"ef": 64}},
        limit=top_k,
        output_fields=["document_id", "content", "metadata"]
    )

    return results
```

**Search result caching**:

```python
from functools import lru_cache
import hashlib

class VectorStore:
    @lru_cache(maxsize=1000)
    def search_cached(
        self,
        query_hash: str,
        collection_name: str,
        top_k: int
    ) -> list[QueryResult]:
        """Cache search results for identical queries"""
        # Cache key includes query hash + parameters
        # Automatically expires least recently used entries
        return self._search_internal(query_hash, collection_name, top_k)

    async def search(self, query: str, collection_name: str, top_k: int):
        # Hash query for cache key
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return self.search_cached(query_hash, collection_name, top_k)
```

### Collection Sharding

**Distribute data** across multiple shards for parallel search:

```python
def create_sharded_collection(
    collection_name: str,
    dimension: int,
    shard_num: int = 2  # Number of shards
):
    """Create collection with sharding for parallel search"""
    schema = CollectionSchema(
        fields=[
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dimension),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
        ]
    )

    collection = Collection(
        name=collection_name,
        schema=schema,
        shards_num=shard_num,  # Parallel search across shards
        consistency_level="Eventually"  # Faster reads
    )

    return collection
```

## LLM Provider Optimization

### Provider Instance Caching

**Singleton pattern** to reuse expensive LLM client connections:

```python
# backend/rag_solution/generation/providers/factory.py
from threading import Lock

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

        # Thread-safe cache check
        if cache_key in self._instances:
            return self._instances[cache_key]

        # Double-checked locking pattern
        with self._lock:
            if cache_key not in self._instances:
                provider = self._create_provider(provider_name, model_id)
                self._instances[cache_key] = provider

        return self._instances[cache_key]
```

### Prompt Optimization

**Reduce token usage** with optimized prompts:

```python
# Before: Verbose prompt (250 tokens)
prompt = f"""
Please analyze the following document and provide a comprehensive answer
to the user's question. Make sure to cite sources and provide detailed
explanations. Here is the context:

{context}

And here is the question:

{question}

Please provide your answer below:
"""

# After: Concise prompt (120 tokens)
prompt = f"""Context: {context}

Question: {question}

Provide a concise answer citing sources."""
```

**Streaming responses** for faster perceived latency:

```python
async def generate_streaming_response(
    prompt: str,
    provider: LLMBase
) -> AsyncIterator[str]:
    """Stream LLM response tokens as they're generated"""
    async for chunk in provider.generate_stream(prompt):
        yield chunk

# Usage in endpoint
@router.post("/search/stream")
async def search_stream(search_input: SearchInput):
    async def generate():
        async for chunk in generate_streaming_response(prompt, provider):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

### Parallel LLM Calls

**Execute multiple LLM calls** concurrently:

```python
import asyncio

async def generate_with_multiple_providers(
    prompt: str,
    providers: list[LLMBase]
) -> list[str]:
    """Call multiple LLM providers in parallel"""
    tasks = [
        provider.generate_response(prompt)
        for provider in providers
    ]

    # Execute all calls concurrently
    responses = await asyncio.gather(*tasks)

    return responses

# Chain of Thought parallel sub-question processing
async def process_subquestions_parallel(
    subquestions: list[str],
    context: SearchContext
) -> list[ReasoningStep]:
    """Process multiple sub-questions concurrently"""
    tasks = [
        process_subquestion(sq, context)
        for sq in subquestions
    ]

    # Process all sub-questions in parallel
    reasoning_steps = await asyncio.gather(*tasks)

    return reasoning_steps
```

## Document Processing Optimization

### Async Document Processing

**Non-blocking document processing** with background tasks:

```python
from fastapi import BackgroundTasks

@router.post("/files/upload")
async def upload_file(
    file: UploadFile,
    collection_id: UUID4,
    background_tasks: BackgroundTasks
):
    # Store file synchronously (fast)
    file_id = await file_service.store_file(file, collection_id)

    # Process document in background (slow)
    background_tasks.add_task(
        process_document_background,
        file_id=file_id,
        collection_id=collection_id
    )

    # Return immediately
    return {
        "file_id": file_id,
        "status": "processing",
        "message": "File uploaded, processing in background"
    }
```

### Batch Embedding Generation

**Process multiple document chunks** in one batch:

```python
async def embed_documents_batch(
    chunks: list[str],
    batch_size: int = 100
) -> list[list[float]]:
    """Generate embeddings in batches for efficiency"""
    embeddings = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]

        # Batch embedding (10x faster than individual)
        batch_embeddings = await embedding_model.encode_batch(
            batch,
            batch_size=batch_size,
            show_progress_bar=False
        )

        embeddings.extend(batch_embeddings)

    return embeddings
```

### Parallel Document Processing

**Process multiple files** concurrently:

```python
async def process_multiple_files(
    file_ids: list[UUID],
    collection_id: UUID
) -> list[ProcessingResult]:
    """Process multiple files in parallel"""
    tasks = [
        process_document(file_id, collection_id)
        for file_id in file_ids
    ]

    # Process all files concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results
```

## Caching Strategies

### Application-Level Caching

**In-memory caching** for frequently accessed data:

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedService:
    def __init__(self):
        self._cache = {}
        self._cache_ttl = timedelta(minutes=5)

    @lru_cache(maxsize=128)
    def get_user_provider(self, user_id: UUID) -> LLMProvider:
        """Cache user's LLM provider configuration"""
        return self.db.query(LLMProvider).filter(
            LLMProvider.user_id == user_id
        ).first()

    def get_collection_with_cache(
        self,
        collection_id: UUID
    ) -> Collection:
        """Manual cache with TTL"""
        cache_key = f"collection:{collection_id}"

        # Check cache
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < self._cache_ttl:
                return data

        # Fetch from database
        collection = self.collection_repo.get(collection_id)

        # Update cache
        self._cache[cache_key] = (collection, datetime.now())

        return collection
```

### Redis Caching

**Distributed cache** for multi-instance deployments:

```python
import redis
import json
from typing import Any

class RedisCache:
    def __init__(self):
        self.client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True
        )

    async def get_or_compute(
        self,
        key: str,
        compute_fn: callable,
        ttl: int = 3600
    ) -> Any:
        """Get from cache or compute and cache"""
        # Try to get from cache
        cached = self.client.get(key)
        if cached:
            return json.loads(cached)

        # Compute value
        value = await compute_fn()

        # Cache with TTL
        self.client.setex(key, ttl, json.dumps(value))

        return value

# Usage
async def get_search_results_cached(
    query: str,
    collection_id: UUID
) -> SearchOutput:
    """Cache search results"""
    cache_key = f"search:{collection_id}:{query}"

    return await redis_cache.get_or_compute(
        key=cache_key,
        compute_fn=lambda: search_service.search(query, collection_id),
        ttl=3600  # Cache for 1 hour
    )
```

## Frontend Performance

### Code Splitting

**Lazy load components** to reduce initial bundle size:

```typescript
// frontend/src/App.tsx
import { lazy, Suspense } from 'react';

// Lazy load heavy components
const SearchInterface = lazy(() => import('./components/search/LightweightSearchInterface'));
const PodcastGenerator = lazy(() => import('./components/podcasts/PodcastGenerator'));
const AdminPanel = lazy(() => import('./components/admin/AdminPanel'));

function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/search" element={<SearchInterface />} />
        <Route path="/podcasts" element={<PodcastGenerator />} />
        <Route path="/admin" element={<AdminPanel />} />
      </Routes>
    </Suspense>
  );
}
```

### API Request Optimization

**Debounce search requests** to reduce API calls:

```typescript
import { debounce } from 'lodash';

const SearchInput: React.FC = () => {
  const [query, setQuery] = useState('');

  // Debounce search to avoid excessive API calls
  const debouncedSearch = useMemo(
    () => debounce(async (q: string) => {
      if (q.length >= 3) {
        const results = await apiClient.search(q);
        setResults(results);
      }
    }, 300),  // Wait 300ms after user stops typing
    []
  );

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    debouncedSearch(value);
  };

  return <input value={query} onChange={handleInputChange} />;
};
```

**Request batching** for multiple API calls:

```typescript
// Batch multiple requests into one
async function batchFetch(
  requests: Array<{ url: string; params: any }>
): Promise<any[]> {
  // Send batch request
  const response = await apiClient.post('/batch', {
    requests: requests
  });

  return response.data.results;
}

// Usage
const [collections, files, users] = await batchFetch([
  { url: '/collections', params: { user_id } },
  { url: '/files', params: { collection_id } },
  { url: '/users', params: { team_id } }
]);
```

### Image Optimization

**Lazy load images** to improve initial page load:

```typescript
import { LazyLoadImage } from 'react-lazy-load-image-component';

const DocumentThumbnail: React.FC<{ src: string }> = ({ src }) => {
  return (
    <LazyLoadImage
      src={src}
      alt="Document thumbnail"
      effect="blur"
      threshold={100}  // Load 100px before visible
      placeholder={<Skeleton />}
    />
  );
};
```

## Monitoring and Profiling

### Performance Metrics

**Track performance metrics** for optimization:

```python
from prometheus_client import Histogram
import time

# Define metrics
search_duration = Histogram(
    'rag_search_duration_seconds',
    'Search request duration',
    ['stage']
)

# Instrument code
async def search_with_metrics(search_input: SearchInput) -> SearchOutput:
    start_time = time.time()

    # Stage 1: Query Enhancement
    with search_duration.labels(stage='query_enhancement').time():
        enhanced_query = await enhance_query(search_input.question)

    # Stage 2: Retrieval
    with search_duration.labels(stage='retrieval').time():
        documents = await retrieve_documents(enhanced_query)

    # Stage 3: Generation
    with search_duration.labels(stage='generation').time():
        answer = await generate_answer(enhanced_query, documents)

    total_time = time.time() - start_time
    search_duration.labels(stage='total').observe(total_time)

    return SearchOutput(answer=answer, execution_time=total_time)
```

### Profiling Tools

**Profile slow endpoints** to identify bottlenecks:

```python
import cProfile
import pstats
from functools import wraps

def profile(func):
    """Decorator to profile function performance"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()

        result = await func(*args, **kwargs)

        profiler.disable()
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.print_stats(20)  # Print top 20 functions

        return result

    return wrapper

# Usage
@profile
async def slow_endpoint(request: Request):
    # This will print profiling stats
    return await process_request(request)
```

## Performance Benchmarks

### Benchmark Suite

**Run performance benchmarks** regularly:

```python
# tests/performance/test_search_performance.py
import pytest
import time

@pytest.mark.performance
async def test_simple_search_latency():
    """Benchmark simple search latency"""
    iterations = 100
    total_time = 0

    for _ in range(iterations):
        start = time.time()
        result = await search_service.search(
            SearchInput(
                question="What is machine learning?",
                collection_id=test_collection_id,
                user_id=test_user_id
            )
        )
        total_time += time.time() - start

    avg_latency = total_time / iterations
    assert avg_latency < 1.5, f"Average latency {avg_latency}s exceeds 1.5s target"

@pytest.mark.performance
async def test_vector_search_throughput():
    """Benchmark vector search throughput"""
    queries = 1000
    start = time.time()

    tasks = [
        vector_store.search(f"query {i}", collection_id)
        for i in range(queries)
    ]
    await asyncio.gather(*tasks)

    elapsed = time.time() - start
    throughput = queries / elapsed

    assert throughput > 100, f"Throughput {throughput} qps below 100 qps target"
```

### Performance Regression Testing

**Detect performance regressions** in CI/CD:

```yaml
# .github/workflows/performance-tests.yml
name: Performance Tests

on:
  pull_request:
    paths:
      - 'backend/**'

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - name: Run performance tests
        run: poetry run pytest tests/performance/ -v

      - name: Compare with baseline
        run: |
          python scripts/compare_benchmarks.py \
            --current results.json \
            --baseline baseline.json \
            --threshold 0.1  # Fail if 10% slower
```

## Best Practices

### Development

1. **Profile before optimizing** - Measure first, optimize second
2. **Use lazy loading** - Defer expensive operations
3. **Implement caching** - Cache frequently accessed data
4. **Batch operations** - Process multiple items together
5. **Use async/await** - Non-blocking I/O operations

### Database

1. **Use connection pooling** - Reuse connections
2. **Add indexes** - Index frequently queried fields
3. **Eager load relationships** - Prevent N+1 queries
4. **Paginate results** - Use cursor-based pagination
5. **Optimize queries** - Select only needed fields

### API

1. **Implement caching** - Cache API responses
2. **Use compression** - gzip response compression
3. **Batch requests** - Combine multiple API calls
4. **Stream large responses** - Use streaming for large data
5. **Rate limiting** - Prevent abuse

## Related Documentation

- [Scalability](scalability.md) - Scaling strategies
- [Components](components.md) - System architecture
- [Troubleshooting - Performance](../troubleshooting/performance.md) - Debug performance issues
