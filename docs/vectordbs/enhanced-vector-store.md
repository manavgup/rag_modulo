# Enhanced VectorStore with Pydantic Integration

## Overview

The enhanced VectorStore abstract base class (Issues #211 and #212) provides a modernized interface for vector database implementations with:

- **Pydantic model integration** for type safety and validation
- **Common utilities** for batch processing and collection management
- **Standardized error handling** with consistent response structures
- **Connection management** with context managers
- **Health checks and statistics** operations
- **Full backward compatibility** with existing implementations

## Architecture

### Three-Layer Design

The enhanced VectorStore uses a three-layer architecture:

1. **Public API Layer** - Existing methods (`create_collection`, `add_documents`, etc.)
2. **Internal Implementation Layer** - New methods with pydantic support (`_create_collection_impl`, `_add_documents_impl`, etc.)
3. **Utility Layer** - Common helper methods (`_batch_chunks`, `_collection_exists`, etc.)

This design allows existing implementations to continue working while providing optional enhanced features.

## Enhanced Pydantic Models

### EmbeddedChunk

A document chunk with **required** embeddings for vector database operations.

```python
from backend.vectordbs.data_types import EmbeddedChunk, DocumentChunk

# Create from DocumentChunk with validation
chunk = DocumentChunk(
    chunk_id="chunk_1",
    text="Machine learning is a subset of AI",
    embeddings=[0.1, 0.2, 0.3, ...],  # 768-dimensional vector
)

# Convert to EmbeddedChunk (validates embeddings are present)
embedded_chunk = EmbeddedChunk.from_chunk(chunk)

# Prepare for vector DB insertion
embeddings, metadata = embedded_chunk.to_vector_db()
```

**Key Features:**
- Enforces non-empty embeddings at creation time
- Provides `from_chunk()` conversion with validation
- `to_vector_metadata()` flattens metadata for storage
- `to_vector_db()` returns tuple of (embeddings, metadata)

### CollectionConfig

Configuration for vector database collections with validation.

```python
from backend.vectordbs.data_types import CollectionConfig

config = CollectionConfig(
    name="my_collection",
    dimension=768,
    metric_type="COSINE",  # COSINE, L2, IP, EUCLIDEAN
    index_type="IVF_FLAT",  # IVF_FLAT, HNSW, etc.
    index_params={"nlist": 1024},
)

# Validation happens automatically
# ValueError raised if dimension <= 0 or invalid metric_type
```

### DocumentIngestionRequest

Request model for document ingestion with batch processing support.

```python
from backend.vectordbs.data_types import (
    DocumentIngestionRequest,
    Document,
    DocumentChunk,
    CollectionConfig,
)

request = DocumentIngestionRequest(
    collection_name="my_collection",
    documents=[doc1, doc2, doc3],
    batch_size=100,  # Process in batches of 100 chunks
    create_collection=True,  # Auto-create collection if needed
    collection_config=config,  # Required if create_collection=True
)

# Extract all embedded chunks with validation
embedded_chunks = request.extract_embedded_chunks()
# Raises ValueError if any chunk lacks embeddings
```

### VectorSearchRequest

Request model for vector database searches.

```python
from backend.vectordbs.data_types import VectorSearchRequest, QueryWithEmbedding

# Text query
request = VectorSearchRequest(
    collection_name="my_collection",
    query="What is machine learning?",
    number_of_results=10,
)

# Query with pre-computed embeddings
query_with_emb = QueryWithEmbedding(
    text="What is ML?",
    embeddings=[0.1, 0.2, 0.3, ...],
)
request = VectorSearchRequest(
    collection_name="my_collection",
    query=query_with_emb,
    number_of_results=5,
    include_embeddings=True,  # Include embeddings in results
)

# Helper methods
text = request.get_query_text()  # Get text regardless of query type
embeddings = request.get_query_embeddings()  # Get embeddings if available
```

### VectorDBResponse

Generic response wrapper with success/error states.

```python
from backend.vectordbs.data_types import VectorDBResponse

# Success response
response = VectorDBResponse.success_response(
    data={"document_ids": ["id1", "id2"]},
    message="Added 2 documents",
    metadata={"elapsed_seconds": 1.23, "batch_size": 100},
)

# Error response
response = VectorDBResponse.error_response(
    error="Connection failed: timeout",
    metadata={"timeout": 30, "retry_count": 3},
)

# Check response
if response.success:
    print(f"Success: {response.message}")
    print(f"Data: {response.data}")
else:
    print(f"Error: {response.error}")
```

**Type Aliases:**
```python
IngestionResponse = VectorDBResponse
SearchResponse = VectorDBResponse
HealthCheckResponse = VectorDBResponse
CollectionStatsResponse = VectorDBResponse
```

## Connection Management

### Basic Connection

```python
from backend.vectordbs.milvus_store import MilvusStore
from core.config import get_settings

store = MilvusStore(get_settings())

# Manual connection
store.connect()
print(f"Connected: {store.is_connected}")  # True
store.disconnect()
```

### Context Managers

```python
# Automatic connection management
with store.connection_context():
    # Connection is open here
    store.add_documents("collection", documents)
    # Connection automatically closed on exit

# Async version
async with store.async_connection_context():
    await store.async_add_documents("collection", documents)
```

## Health Checks and Statistics

### Health Check

```python
# Check database health
response = store.health_check(timeout=5.0)

if response.success:
    print("Health check passed")
    print(f"Status: {response.data}")
    print(f"Elapsed: {response.metadata['elapsed_seconds']}s")
else:
    print(f"Health check failed: {response.error}")
```

### Collection Statistics

```python
# Get collection stats
response = store.get_collection_stats("my_collection")

if response.success:
    stats = response.data
    print(f"Documents: {stats['document_count']}")
    print(f"Dimensions: {stats['dimension']}")
    print(f"Index type: {stats['index_type']}")
```

## Common Utilities

### Batch Processing

```python
from backend.vectordbs.data_types import EmbeddedChunk

# Create many chunks
chunks = [
    EmbeddedChunk(chunk_id=f"chunk_{i}", text=f"Text {i}", embeddings=[...])
    for i in range(1000)
]

# Batch for efficient processing
batches = store._batch_chunks(chunks, batch_size=100)
# Returns 10 batches of 100 chunks each

for batch in batches:
    store._add_documents_impl("collection", batch)
```

### Collection Validation

```python
# Check if collection exists
if store._collection_exists("my_collection"):
    print("Collection found")
else:
    print("Collection not found")
```

### Configuration Validation

```python
from backend.vectordbs.data_types import CollectionConfig

config = CollectionConfig(name="test", dimension=768)

# Validate against settings
store._validate_collection_config(config)
# Warns if dimension doesn't match settings
```

## Implementing a Vector Store

### Minimal Implementation

```python
from backend.vectordbs.vector_store import VectorStore
from backend.vectordbs.data_types import (
    CollectionConfig,
    EmbeddedChunk,
    VectorSearchRequest,
    QueryResult,
)

class MyVectorStore(VectorStore):
    """Custom vector store implementation."""

    # Required: Implement internal methods with pydantic models
    def _health_check_impl(self, timeout: float) -> dict[str, Any]:
        """Check database health."""
        return {"status": "healthy", "version": "1.0"}

    def _get_collection_stats_impl(self, collection_name: str) -> dict[str, Any]:
        """Get collection statistics."""
        # Raise CollectionError if not found
        return {"name": collection_name, "count": 100}

    def _create_collection_impl(self, config: CollectionConfig) -> dict[str, Any]:
        """Create collection with pydantic config."""
        # Use config.name, config.dimension, config.metric_type, etc.
        return {"name": config.name, "created": True}

    def _add_documents_impl(
        self, collection_name: str, chunks: list[EmbeddedChunk]
    ) -> list[str]:
        """Add embedded chunks to collection."""
        # chunks are guaranteed to have embeddings
        return [chunk.chunk_id for chunk in chunks]

    def _search_impl(self, request: VectorSearchRequest) -> list[QueryResult]:
        """Search with pydantic request."""
        query_text = request.get_query_text()
        query_embeddings = request.get_query_embeddings()
        # Perform search...
        return results

    def _delete_collection_impl(self, collection_name: str) -> None:
        """Delete collection."""
        # Raise CollectionError if not found
        pass

    # Required: Implement public API methods (backward compatibility)
    def create_collection(self, collection_name: str, metadata: dict | None = None) -> None:
        """Create collection (legacy API)."""
        config = CollectionConfig(
            name=collection_name,
            dimension=self.settings.embedding_dim,
            metadata_schema=metadata,
        )
        self._create_collection_impl(config)

    def add_documents(self, collection_name: str, documents: list[Document]) -> list[str]:
        """Add documents (legacy API)."""
        # Convert documents to embedded chunks
        chunks = []
        for doc in documents:
            for chunk in doc.chunks:
                if chunk.embeddings and chunk.chunk_id:
                    chunks.append(EmbeddedChunk.from_chunk(chunk))

        # Use internal batching
        batches = self._batch_chunks(chunks, batch_size=100)
        document_ids = []
        for batch in batches:
            batch_ids = self._add_documents_impl(collection_name, batch)
            document_ids.extend(batch_ids)
        return document_ids

    # ... implement other required methods
```

## Migration Guide

### For Vector Store Implementations

Existing implementations continue to work without changes. To adopt enhanced features:

1. **Implement internal methods** (`_create_collection_impl`, etc.) with pydantic models
2. **Update public methods** to use internal implementations for consistency
3. **Add health checks** by implementing `_health_check_impl`
4. **Use batch processing** utilities in `add_documents`

### For Consumers

No changes required - existing code continues to work. To use enhanced features:

```python
# Old way (still works)
store.create_collection("my_collection")
store.add_documents("my_collection", documents)

# New way (with enhanced validation and features)
from backend.vectordbs.data_types import (
    CollectionConfig,
    DocumentIngestionRequest,
)

# Create with validation
config = CollectionConfig(name="my_collection", dimension=768)
result = store._create_collection_impl(config)

# Add with batching and validation
request = DocumentIngestionRequest(
    collection_name="my_collection",
    documents=documents,
    batch_size=100,
)
chunks = request.extract_embedded_chunks()
batches = store._batch_chunks(chunks, request.batch_size)
for batch in batches:
    store._add_documents_impl("my_collection", batch)
```

## Performance Benefits

### Batch Processing

The `_batch_chunks` utility reduces API calls by up to 90%:

```python
# Without batching: 1000 API calls
for chunk in chunks:  # 1000 chunks
    store._add_single_chunk(chunk)

# With batching: 10 API calls
batches = store._batch_chunks(chunks, batch_size=100)
for batch in batches:  # 10 batches
    store._add_documents_impl("collection", batch)
```

### Connection Pooling

Context managers reduce connection overhead:

```python
# Without context manager: 1000 connections
for doc in documents:  # 1000 documents
    store.connect()
    store.add_documents("collection", [doc])
    store.disconnect()

# With context manager: 1 connection
with store.connection_context():
    for doc in documents:
        store.add_documents("collection", [doc])
```

### Validation

Pydantic validation catches errors early:

```python
# Runtime error (old way)
chunk = DocumentChunk(chunk_id="1", text="...", embeddings=None)
store.add_documents("collection", [Document(chunks=[chunk])])
# Error occurs deep in vector DB during insertion

# Validation error (new way)
try:
    embedded = EmbeddedChunk.from_chunk(chunk)
except ValueError as e:
    print(f"Validation failed: {e}")  # Caught immediately
```

## Best Practices

1. **Use EmbeddedChunk for insertions** - Ensures embeddings are present before DB operations
2. **Batch process large datasets** - Use `_batch_chunks` for efficient processing
3. **Validate configurations** - Use CollectionConfig instead of dict parameters
4. **Handle responses** - Check VectorDBResponse.success before accessing data
5. **Use context managers** - Automatic connection management
6. **Implement health checks** - Monitor database availability
7. **Log operations** - Enhanced logging context available

## See Also

- [Vector Database Architecture](../architecture/vector-databases.md)
- [Milvus Implementation](./milvus-implementation.md)
- [API Reference](../api/vectordbs.md)
- [Testing Guide](../testing/vectordbs.md)
