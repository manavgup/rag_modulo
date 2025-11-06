# Pydantic Models Integration Plan

## Status: IN PROGRESS

### Completed ✅

**Issue #577: MilvusStore Pydantic Integration**
- Commit: `84ebb6b`
- Branch: `feature/integrate-pydantic-models-vector-stores`

All MilvusStore methods now use Pydantic models with backward compatibility:

1. **Imports Added:**
   - `CollectionConfig`
   - `DocumentIngestionRequest`
   - `EmbeddedChunk`
   - `VectorSearchRequest`
   - `VectorDBResponse`

2. **New Pydantic-based Methods:**
   - `_create_collection_impl(config: CollectionConfig)` → `dict[str, Any]`
   - `_add_documents_impl(collection_name: str, chunks: list[EmbeddedChunk])` → `list[str]`
   - `_search_impl(request: VectorSearchRequest)` → `list[QueryResult]`
   - `delete_documents_with_response(...)` → `VectorDBResponse[dict[str, Any]]`

3. **Backward Compatibility Wrappers:**
   - `create_collection()` - converts legacy params to `CollectionConfig`
   - `add_documents()` - converts `Document` list to `EmbeddedChunk` list
   - `query()` - converts to `VectorSearchRequest`
   - `delete_documents()` - uses new response method, raises on error

---

### Remaining Work (Issue #578)

**ChromaStore** (257 lines)
- Status: Not started
- File: `backend/vectordbs/chroma_store.py`
- Pattern: Follow MilvusStore implementation

**ElasticsearchStore** (279 lines)
- Status: Not started
- File: `backend/vectordbs/elasticsearch_store.py`
- Pattern: Follow MilvusStore implementation

**PineconeStore** (292 lines)
- Status: Not started
- File: `backend/vectordbs/pinecone_store.py`
- Pattern: Follow MilvusStore implementation

**WeaviateStore** (335 lines)
- Status: Not started
- File: `backend/vectordbs/weaviate_store.py`
- Pattern: Follow MilvusStore implementation

---

## Implementation Pattern (from MilvusStore)

### 1. Update Imports

```python
from .data_types import (
    CollectionConfig,
    Document,
    DocumentChunkMetadata,
    DocumentChunkWithScore,
    DocumentIngestionRequest,
    DocumentMetadataFilter,
    EmbeddedChunk,
    QueryResult,
    QueryWithEmbedding,
    Source,
    VectorDBResponse,
    VectorSearchRequest,
)
```

### 2. Implement Pydantic Methods

```python
def _create_collection_impl(self, config: CollectionConfig) -> dict[str, Any]:
    """Implementation-specific collection creation with Pydantic model."""
    # 1. Validate config against settings
    self._validate_collection_config(config)

    # 2. Check if exists
    # 3. Create with config parameters
    # 4. Return metadata dict

def _add_documents_impl(self, collection_name: str, chunks: list[EmbeddedChunk]) -> list[str]:
    """Implementation-specific document addition with Pydantic models."""
    # 1. Get collection
    # 2. Process EmbeddedChunk list (embeddings guaranteed non-null)
    # 3. Insert into vector store
    # 4. Return chunk IDs

def _search_impl(self, request: VectorSearchRequest) -> list[QueryResult]:
    """Implementation-specific search with Pydantic model."""
    # 1. Get query vector (from request.query_vector or generate from request.query_text)
    # 2. Perform vector search
    # 3. Return QueryResult list

def delete_documents_with_response(self, collection_name: str, document_ids: list[str]) -> VectorDBResponse[dict[str, Any]]:
    """Delete with detailed response (Pydantic-enhanced)."""
    # 1. Delete documents
    # 2. Track timing
    # 3. Return VectorDBResponse.create_success() or create_error()
```

### 3. Add Backward Compatibility Wrappers

```python
def create_collection(self, collection_name: str, metadata: dict | None = None) -> None:
    """Backward compatibility wrapper."""
    config = CollectionConfig(
        collection_name=collection_name,
        dimension=self.settings.embedding_dim,
        metric_type="COSINE",  # or store-specific default
        index_type="...",      # store-specific
        description=metadata.get("description") if metadata else None,
    )
    self._create_collection_impl(config)

def add_documents(self, collection_name: str, documents: list[Document]) -> list[str]:
    """Backward compatibility wrapper."""
    chunks = [
        EmbeddedChunk(
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            embeddings=chunk.embeddings,
            metadata=chunk.metadata,
            document_id=chunk.document_id,
        )
        for doc in documents
        for chunk in doc.chunks
        if chunk.embeddings  # Filter out chunks without embeddings
    ]
    chunk_ids = self._add_documents_impl(collection_name, chunks)
    return list({chunk.document_id for chunk in chunks if chunk.document_id})

def query(self, collection_name: str, query: QueryWithEmbedding, ...) -> list[QueryResult]:
    """Backward compatibility wrapper."""
    request = VectorSearchRequest(
        query_text=query.text if hasattr(query, 'text') else None,
        query_vector=query.embeddings,
        collection_id=collection_name,
        top_k=number_of_results,
        metadata_filter=metadata_filter,
        include_metadata=True,
        include_vectors=False,
    )
    return self._search_impl(request)

def delete_documents(self, collection_name: str, document_ids: list[str]) -> None:
    """Backward compatibility wrapper."""
    response = self.delete_documents_with_response(collection_name, document_ids)
    if not response.success:
        raise DocumentError(response.error or "Unknown error")
```

---

## Testing Strategy

1. **Unit Tests** - Test Pydantic model validation
2. **Integration Tests** - Test with real vector stores
3. **Backward Compatibility** - Ensure existing code works unchanged

---

## Next Steps

1. Apply same pattern to ChromaStore
2. Apply to ElasticsearchStore
3. Apply to PineconeStore
4. Apply to WeaviateStore
5. Run full test suite
6. Update documentation
7. Create PR

---

## References

- Issue #577: https://github.com/manavgup/rag_modulo/issues/577
- Issue #578: https://github.com/manavgup/rag_modulo/issues/578
- PR #571: Pydantic models foundation
- PR #579: Enhanced VectorStore base class
