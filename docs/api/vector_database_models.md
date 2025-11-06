# Vector Database Models

Comprehensive guide to the enhanced Pydantic models for vector database operations in RAG Modulo.

## Overview

The vector database models provide type-safe, validated structures for all vector database operations. These models eliminate manual dictionary parsing, improve error handling, and enable better IDE support through comprehensive type hints.

## Key Features

- **Type Safety**: Full Pydantic v2 validation with Python 3.12+ type hints
- **Automatic Validation**: Field-level and cross-field validation
- **Conversion Methods**: Easy conversion between formats
- **Generic Responses**: Type-safe response handling
- **Performance Optimized**: Efficient serialization for large batches

## Core Models

### EmbeddedChunk

A `DocumentChunk` with mandatory (non-optional) embeddings, ensuring that all vector database operations have the required embedding data.

**Attributes:**

- `embeddings` (required): Vector embedding as list of floats
- All other attributes inherited from `DocumentChunk`

**Key Methods:**

```python
from vectordbs.data_types import EmbeddedChunk, DocumentChunk

# Create from DocumentChunk
chunk = DocumentChunk(
    chunk_id="chunk_001",
    text="Sample text",
    embeddings=[0.1, 0.2, 0.3]
)

embedded = EmbeddedChunk.from_chunk(chunk)

# Or provide embeddings explicitly
embedded = EmbeddedChunk.from_chunk(chunk, embeddings=[0.1, 0.2, 0.3])

# Convert to vector metadata
metadata = embedded.to_vector_metadata()
# Returns: {"chunk_id": "chunk_001", "text": "Sample text", ...}

# Convert to vector DB format
db_format = embedded.to_vector_db()
# Returns: {"id": "chunk_001", "vector": [0.1, 0.2, 0.3], "metadata": {...}}
```

**Validation:**

- Embeddings cannot be `None`
- Embeddings list cannot be empty
- Raises `ValueError` if attempting to create without valid embeddings

**Example:**

```python
from vectordbs.data_types import EmbeddedChunk, DocumentChunkMetadata, Source

metadata = DocumentChunkMetadata(
    source=Source.PDF,
    document_id="doc_123",
    page_number=1,
    chunk_number=1
)

chunk = EmbeddedChunk(
    chunk_id="chunk_001",
    text="This is a sample document chunk.",
    embeddings=[0.1, 0.2, 0.3, 0.4],
    metadata=metadata,
    document_id="doc_123"
)

# Ready for vector database insertion
vector_db_format = chunk.to_vector_db()
```

---

### DocumentIngestionRequest

Request model for ingesting documents into a vector database with support for batching and embedded chunk extraction.

**Attributes:**

- `chunks`: List of `DocumentChunk` to ingest (required, non-empty)
- `collection_id`: Target collection identifier (required)
- `batch_size`: Number of chunks per batch (default: 100, range: 1-1000)

**Key Methods:**

```python
from vectordbs.data_types import DocumentIngestionRequest, DocumentChunk

chunks = [
    DocumentChunk(chunk_id="1", text="Text 1", embeddings=[0.1, 0.2]),
    DocumentChunk(chunk_id="2", text="Text 2", embeddings=[0.3, 0.4])
]

request = DocumentIngestionRequest(
    chunks=chunks,
    collection_id="my_collection",
    batch_size=100
)

# Get only chunks with embeddings
embedded_chunks = request.get_embedded_chunks()
# Returns: List[EmbeddedChunk]

# Split into batches
batches = request.get_batches()
# Returns: List[List[DocumentChunk]]
```

**Validation:**

- `chunks` list cannot be empty
- `batch_size` must be between 1 and 1000
- All fields validated at creation time

**Example: Batch Processing**

```python
# Create request with 500 chunks
request = DocumentIngestionRequest(
    chunks=large_chunk_list,
    collection_id="documents",
    batch_size=100
)

# Process in batches
for batch in request.get_batches():
    # Each batch has up to 100 chunks
    for chunk in batch:
        if chunk.embeddings:
            embedded = EmbeddedChunk.from_chunk(chunk)
            # Insert into vector DB
```

---

### VectorSearchRequest

Standardized request model for vector database searches, supporting both text and vector queries.

**Attributes:**

- `query_text`: Text query (optional if `query_vector` provided)
- `query_vector`: Pre-computed embedding (optional if `query_text` provided)
- `collection_id`: Collection to search in (required)
- `top_k`: Number of results (default: 10, range: 1-100)
- `metadata_filter`: Optional metadata filtering
- `include_metadata`: Include metadata in results (default: True)
- `include_vectors`: Include vectors in results (default: False)

**Key Methods:**

```python
from vectordbs.data_types import VectorSearchRequest

# Text-based search
request = VectorSearchRequest(
    query_text="What is machine learning?",
    collection_id="ml_documents",
    top_k=10
)

# Vector-based search
request = VectorSearchRequest(
    query_vector=[0.1, 0.2, 0.3, ...],
    collection_id="ml_documents",
    top_k=5
)

# Convert to VectorQuery (backward compatibility)
vector_query = request.to_vector_query()
```

**Validation:**

- At least one of `query_text` or `query_vector` must be provided
- `top_k` must be between 1 and 100
- Validates at instantiation via `model_post_init`

**Example: Search with Filtering**

```python
from vectordbs.data_types import VectorSearchRequest, DocumentMetadataFilter

metadata_filter = DocumentMetadataFilter(
    field_name="document_type",
    operator="eq",
    value="technical"
)

request = VectorSearchRequest(
    query_text="API documentation",
    collection_id="documents",
    top_k=20,
    metadata_filter=metadata_filter,
    include_metadata=True,
    include_vectors=False
)
```

---

### CollectionConfig

Configuration model for vector database collections with database-specific validation.

**Attributes:**

- `collection_name`: Collection name (1-255 chars, required)
- `dimension`: Vector dimension (1-4096, required)
- `metric_type`: Distance metric (default: "L2")
  - Valid values: `L2`, `IP`, `COSINE`, `HAMMING`, `JACCARD`
- `index_type`: Index type (default: "HNSW")
  - Valid values: `FLAT`, `IVF_FLAT`, `IVF_SQ8`, `IVF_PQ`, `HNSW`, `ANNOY`
- `index_params`: Database-specific parameters (dict)
- `description`: Optional description (max 1000 chars)

**Key Methods:**

```python
from vectordbs.data_types import CollectionConfig

config = CollectionConfig(
    collection_name="embeddings_768",
    dimension=768,
    metric_type="COSINE",
    index_type="HNSW",
    index_params={
        "M": 16,
        "efConstruction": 200
    }
)

# Convert to dict for vector DB
config_dict = config.to_dict()
```

**Validation:**

- Collection name length: 1-255 characters
- Dimension range: 1-4096
- Metric type must be in valid list (case-insensitive)
- Index type must be in valid list (case-insensitive)
- Description max length: 1000 characters

**Example: Different Embedding Models**

```python
# OpenAI embeddings (1536 dimensions)
openai_config = CollectionConfig(
    collection_name="openai_embeddings",
    dimension=1536,
    metric_type="COSINE",
    index_type="HNSW",
    description="OpenAI text-embedding-ada-002 vectors"
)

# Sentence Transformers (384 dimensions)
st_config = CollectionConfig(
    collection_name="sentence_transformers",
    dimension=384,
    metric_type="L2",
    index_type="IVF_FLAT",
    index_params={"nlist": 1024}
)
```

---

### VectorDBResponse[T]

Generic response wrapper providing consistent success/error handling across all vector database operations.

**Attributes:**

- `success`: Operation success status (bool)
- `data`: Response data (generic type T, optional)
- `error`: Error message (optional)
- `metadata`: Additional operation metadata (dict)

**Key Methods:**

```python
from vectordbs.data_types import VectorDBResponse

# Create success response
response = VectorDBResponse.create_success(
    data=["id1", "id2", "id3"],
    metadata={"time": "0.5s", "count": 3}
)

# Create error response
response = VectorDBResponse.create_error(
    error="Connection timeout",
    metadata={"retry_count": 3}
)

# Check status
if response.is_success():
    data = response.get_data_or_raise()
else:
    print(f"Error: {response.error}")
```

**Type Aliases:**

```python
# Predefined type aliases for common operations
VectorDBIngestionResponse = VectorDBResponse[list[str]]  # Ingested IDs
VectorDBSearchResponse = VectorDBResponse[list[QueryResult]]  # Search results
VectorDBCollectionResponse = VectorDBResponse[dict[str, Any]]  # Collection info
VectorDBDeleteResponse = VectorDBResponse[bool]  # Delete status
```

**Example: Operation Chain**

```python
from vectordbs.data_types import VectorDBIngestionResponse, VectorDBSearchResponse

# Ingestion
ingestion_response: VectorDBIngestionResponse = VectorDBIngestionResponse.create_success(
    data=["id1", "id2", "id3"],
    metadata={"ingestion_time": "1.2s"}
)

if ingestion_response.is_success():
    ingested_ids = ingestion_response.get_data_or_raise()
    print(f"Ingested {len(ingested_ids)} chunks")

# Search
search_response: VectorDBSearchResponse = VectorDBSearchResponse.create_success(
    data=[...],  # List of QueryResult
    metadata={"search_time": "0.05s"}
)
```

---

## Usage Patterns

### Complete Ingestion Workflow

```python
from vectordbs.data_types import (
    DocumentChunk,
    DocumentIngestionRequest,
    EmbeddedChunk,
    VectorDBIngestionResponse
)

# Step 1: Prepare chunks
chunks = [
    DocumentChunk(
        chunk_id=f"chunk_{i}",
        text=f"Content {i}",
        embeddings=generate_embedding(f"Content {i}"),
        document_id=f"doc_{i // 10}"
    )
    for i in range(100)
]

# Step 2: Create ingestion request
request = DocumentIngestionRequest(
    chunks=chunks,
    collection_id="my_collection",
    batch_size=25
)

# Step 3: Process batches
ingested_ids = []
for batch in request.get_batches():
    embedded_chunks = [
        EmbeddedChunk.from_chunk(chunk)
        for chunk in batch
        if chunk.embeddings
    ]

    # Insert into vector DB
    for embedded in embedded_chunks:
        vector_db_format = embedded.to_vector_db()
        # vector_db.insert(vector_db_format)
        ingested_ids.append(embedded.chunk_id)

# Step 4: Create response
response = VectorDBIngestionResponse.create_success(
    data=ingested_ids,
    metadata={"total_ingested": len(ingested_ids)}
)
```

### Complete Search Workflow

```python
from vectordbs.data_types import (
    VectorSearchRequest,
    QueryResult,
    VectorDBSearchResponse
)

# Step 1: Create search request
request = VectorSearchRequest(
    query_text="What is machine learning?",
    collection_id="ml_documents",
    top_k=10,
    include_metadata=True
)

# Step 2: Execute search (pseudo-code)
# results = vector_db.search(request.to_vector_query())

# Step 3: Create response
response = VectorDBSearchResponse.create_success(
    data=results,
    metadata={
        "query_time": "0.05s",
        "total_found": 100
    }
)

# Step 4: Handle results
if response.is_success():
    for result in response.data:
        print(f"Score: {result.score}, Text: {result.chunk.text}")
```

### Collection Management

```python
from vectordbs.data_types import (
    CollectionConfig,
    VectorDBCollectionResponse
)

# Create collection config
config = CollectionConfig(
    collection_name="embeddings_768",
    dimension=768,
    metric_type="COSINE",
    index_type="HNSW",
    index_params={
        "M": 16,
        "efConstruction": 200
    },
    description="BERT embeddings collection"
)

# Use config to create collection
config_dict = config.to_dict()
# collection_created = vector_db.create_collection(**config_dict)

# Create response
response = VectorDBCollectionResponse.create_success(
    data=config_dict,
    metadata={"created_at": "2025-11-06T10:00:00Z"}
)
```

---

## Error Handling

All models provide comprehensive validation and error handling:

```python
from pydantic import ValidationError
from vectordbs.data_types import EmbeddedChunk, DocumentIngestionRequest

# Example 1: Missing required field
try:
    chunk = EmbeddedChunk(
        chunk_id="test",
        text="Sample text"
        # Missing embeddings!
    )
except ValidationError as e:
    print(f"Validation error: {e}")

# Example 2: Empty chunks list
try:
    request = DocumentIngestionRequest(
        chunks=[],  # Empty!
        collection_id="test"
    )
except ValidationError as e:
    print(f"Validation error: {e}")

# Example 3: Invalid metric type
try:
    config = CollectionConfig(
        collection_name="test",
        dimension=768,
        metric_type="INVALID"  # Not in valid list!
    )
except ValidationError as e:
    print(f"Validation error: {e}")

# Example 4: Operation failure handling
response = VectorDBIngestionResponse.create_error(
    error="Database connection failed",
    metadata={"retry_count": 3}
)

try:
    data = response.get_data_or_raise()
except ValueError as e:
    print(f"Operation failed: {e}")
```

---

## Performance Considerations

### Batch Processing

Process large datasets in batches to optimize memory and performance:

```python
request = DocumentIngestionRequest(
    chunks=large_chunk_list,
    collection_id="documents",
    batch_size=100  # Adjust based on memory constraints
)

for batch in request.get_batches():
    # Process batch
    pass
```

### Serialization

Models use efficient Pydantic v2 serialization:

```python
# JSON serialization
json_str = request.model_dump_json()

# Dictionary serialization
data_dict = request.model_dump()

# Exclude None values
data_dict = request.model_dump(exclude_none=True)
```

### Memory Optimization

For very large batches (10,000+ chunks), consider:

1. Smaller batch sizes (50-100)
2. Streaming processing
3. Exclude unnecessary fields during serialization

**Performance Benchmarks:**

- Serialization: < 100ms for 1,000 chunks with 768-dim embeddings
- Batching: < 10ms for 10,000 chunks
- Validation: < 1ms per model instance

---

## Migration Guide

### From Manual Dict Construction

**Before:**

```python
# Manual dictionary construction
chunk_dict = {
    "id": chunk_id,
    "vector": embeddings,
    "metadata": {
        "chunk_id": chunk_id,
        "text": text,
        "document_id": doc_id
    }
}
```

**After:**

```python
# Type-safe model
embedded = EmbeddedChunk(
    chunk_id=chunk_id,
    text=text,
    embeddings=embeddings,
    document_id=doc_id
)

chunk_dict = embedded.to_vector_db()
```

### From VectorQuery to VectorSearchRequest

**Before:**

```python
query = VectorQuery(
    text="query text",
    embeddings=None,
    number_of_results=10
)
```

**After:**

```python
request = VectorSearchRequest(
    query_text="query text",
    collection_id="documents",
    top_k=10
)

# Convert back if needed
query = request.to_vector_query()
```

---

## Type Checking with MyPy

All models are fully type-safe and work with MyPy:

```python
from vectordbs.data_types import (
    VectorDBIngestionResponse,
    VectorDBSearchResponse
)

def process_ingestion(response: VectorDBIngestionResponse) -> list[str]:
    """Process ingestion response."""
    if response.is_success():
        return response.get_data_or_raise()  # Type: list[str]
    return []

def process_search(response: VectorDBSearchResponse) -> list[QueryResult]:
    """Process search response."""
    if response.is_success():
        return response.get_data_or_raise()  # Type: list[QueryResult]
    return []
```

Run type checking:

```bash
poetry run mypy backend/vectordbs/data_types.py
```

---

## Best Practices

1. **Always use EmbeddedChunk for vector operations**
   - Ensures embeddings are present
   - Provides convenient conversion methods

2. **Use batch processing for large datasets**
   - Set appropriate batch_size (50-100 typical)
   - Monitor memory usage

3. **Leverage type aliases**
   - Use `VectorDBIngestionResponse`, `VectorDBSearchResponse`, etc.
   - Improves code readability and type safety

4. **Handle errors explicitly**
   - Check `is_success()` before accessing data
   - Use `get_data_or_raise()` when failure is unexpected

5. **Validate early**
   - Models validate at creation
   - Catch errors before database operations

6. **Use conversion methods**
   - `to_vector_db()`, `to_vector_metadata()`
   - Ensures consistent format

---

## API Reference

### Module: `vectordbs.data_types`

**Models:**
- `EmbeddedChunk` - DocumentChunk with mandatory embeddings
- `DocumentIngestionRequest` - Batch ingestion request
- `VectorSearchRequest` - Search request with text or vector query
- `CollectionConfig` - Collection configuration
- `VectorDBResponse[T]` - Generic response wrapper

**Type Aliases:**
- `VectorDBIngestionResponse` - Response for ingestion operations
- `VectorDBSearchResponse` - Response for search operations
- `VectorDBCollectionResponse` - Response for collection operations
- `VectorDBDeleteResponse` - Response for delete operations

**Existing Models** (unchanged):
- `DocumentChunk` - Basic document chunk
- `DocumentChunkWithScore` - Chunk with similarity score
- `DocumentChunkMetadata` - Chunk-level metadata
- `DocumentMetadata` - Document-level metadata
- `VectorQuery` - Legacy query model
- `QueryResult` - Search result wrapper

---

## See Also

- [API Documentation](index.md)
- [Search API](search_api.md)
- [Vector Database Guide](../guides/vector_databases.md)
- [Testing Guide](../testing/index.md)
