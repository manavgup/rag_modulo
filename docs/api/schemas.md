# API Schemas

This page documents the request and response schemas used by the RAG Modulo API.

## Search Schemas

### SearchInput

Request schema for search operations.

```python
{
  "question": str,                    # Required: Search query
  "collection_id": UUID4,             # Required: Collection to search
  "user_id": UUID4,                   # Required: User performing search
  "config_metadata": dict | None      # Optional: Search configuration
}
```

**Example**:
```json
{
  "question": "What is machine learning?",
  "collection_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "config_metadata": {
    "cot_enabled": true,
    "show_cot_steps": true,
    "max_results": 5
  }
}
```

### SearchOutput

Response schema for search operations.

```python
{
  "answer": str,                      # Generated answer
  "sources": list[Source],            # Document sources
  "reasoning_steps": list[Step] | None,  # CoT steps (if enabled)
  "metadata": dict                    # Response metadata
}
```

**Example**:
```json
{
  "answer": "Machine learning is a subset of artificial intelligence...",
  "sources": [
    {
      "document_id": "456e7890-e89b-12d3-a456-426614174000",
      "chunk_id": "chunk_1",
      "content": "Machine learning involves...",
      "score": 0.95,
      "page": 1
    }
  ],
  "reasoning_steps": null,
  "metadata": {
    "total_tokens": 1250,
    "response_time_ms": 850,
    "pipeline_id": "pipe_123"
  }
}
```

## Collection Schemas

### CollectionInput

Request schema for creating collections.

```python
{
  "name": str,                        # Required: Collection name
  "description": str | None,          # Optional: Description
  "user_id": UUID4,                   # Required: Owner user ID
  "metadata": dict | None             # Optional: Custom metadata
}
```

**Example**:
```json
{
  "name": "Research Papers",
  "description": "AI and ML research papers",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "metadata": {
    "category": "research",
    "tags": ["AI", "ML"]
  }
}
```

### CollectionOutput

Response schema for collection operations.

```python
{
  "id": UUID4,                        # Collection ID
  "name": str,                        # Collection name
  "description": str | None,          # Description
  "user_id": UUID4,                   # Owner user ID
  "document_count": int,              # Number of documents
  "created_at": datetime,             # Creation timestamp
  "updated_at": datetime,             # Last update timestamp
  "metadata": dict | None             # Custom metadata
}
```

## Document Schemas

### DocumentInput

Request schema for document upload.

```python
{
  "file": UploadFile,                 # Required: File to upload
  "collection_id": UUID4,             # Required: Target collection
  "user_id": UUID4,                   # Required: Uploader user ID
  "metadata": dict | None             # Optional: Document metadata
}
```

### DocumentOutput

Response schema for document operations.

```python
{
  "id": UUID4,                        # Document ID
  "filename": str,                    # Original filename
  "collection_id": UUID4,             # Parent collection
  "user_id": UUID4,                   # Owner user ID
  "status": str,                      # processing | indexed | failed
  "chunk_count": int | None,          # Number of chunks
  "created_at": datetime,             # Upload timestamp
  "metadata": dict | None             # Custom metadata
}
```

**Example**:
```json
{
  "id": "456e7890-e89b-12d3-a456-426614174000",
  "filename": "research_paper.pdf",
  "collection_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "indexed",
  "chunk_count": 42,
  "created_at": "2025-01-09T10:00:00Z",
  "metadata": {
    "author": "John Doe",
    "year": 2025
  }
}
```

## Conversation Schemas

### ConversationSessionInput

Request schema for creating conversation sessions.

```python
{
  "user_id": UUID4,                   # Required: User ID
  "title": str | None,                # Optional: Session title
  "metadata": dict | None             # Optional: Session metadata
}
```

### ConversationSessionOutput

Response schema for conversation sessions.

```python
{
  "id": UUID4,                        # Session ID
  "user_id": UUID4,                   # Owner user ID
  "title": str | None,                # Session title
  "status": str,                      # active | paused | archived
  "message_count": int,               # Number of messages
  "is_archived": bool,                # Archive status
  "is_pinned": bool,                  # Pin status
  "created_at": datetime,             # Creation timestamp
  "updated_at": datetime,             # Last update timestamp
  "metadata": dict | None             # Custom metadata
}
```

### ConversationMessageInput

Request schema for adding messages.

```python
{
  "session_id": UUID4,                # Required: Parent session
  "role": str,                        # Required: user | assistant | system
  "message_type": str,                # Required: question | answer | system
  "content": str,                     # Required: Message content
  "token_count": int | None,          # Optional: Token count
  "metadata": dict | None             # Optional: Message metadata
}
```

### ConversationMessageOutput

Response schema for conversation messages.

```python
{
  "id": UUID4,                        # Message ID
  "session_id": UUID4,                # Parent session
  "role": str,                        # user | assistant | system
  "message_type": str,                # question | answer | system
  "content": str,                     # Message content
  "token_count": int | None,          # Token count
  "created_at": datetime,             # Creation timestamp
  "metadata": dict | None             # Custom metadata
}
```

## Pipeline Schemas

### PipelineInput

Request schema for creating pipelines.

```python
{
  "name": str,                        # Required: Pipeline name
  "user_id": UUID4,                   # Required: Owner user ID
  "stages": list[str],                # Required: Processing stages
  "is_default": bool,                 # Optional: Set as default
  "config": dict | None               # Optional: Stage configuration
}
```

**Example**:
```json
{
  "name": "Custom RAG Pipeline",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "stages": [
    "query_rewriting",
    "retrieval",
    "reranking",
    "generation"
  ],
  "is_default": false,
  "config": {
    "retrieval": {
      "max_results": 10,
      "min_score": 0.7
    },
    "generation": {
      "max_tokens": 500
    }
  }
}
```

### PipelineOutput

Response schema for pipeline operations.

```python
{
  "id": UUID4,                        # Pipeline ID
  "name": str,                        # Pipeline name
  "user_id": UUID4,                   # Owner user ID
  "stages": list[str],                # Processing stages
  "is_default": bool,                 # Default status
  "created_at": datetime,             # Creation timestamp
  "config": dict | None               # Stage configuration
}
```

## Common Types

### Source

Document source information.

```python
{
  "document_id": UUID4,               # Source document ID
  "chunk_id": str,                    # Chunk identifier
  "content": str,                     # Chunk content
  "score": float,                     # Relevance score (0-1)
  "page": int | None,                 # Page number (if available)
  "metadata": dict | None             # Additional metadata
}
```

### ReasoningStep

Chain of Thought reasoning step.

```python
{
  "sub_question": str,                # Decomposed question
  "answer": str,                      # Step answer
  "sources": list[Source],            # Sources for this step
  "confidence": float                 # Confidence score (0-1)
}
```

## Validation

All schemas use Pydantic for validation with `extra="forbid"` mode, meaning:

- Extra fields are **not allowed**
- All required fields must be present
- Types must match exactly
- UUIDs must be valid UUID4 format

**Example Validation Error**:
```json
{
  "detail": [
    {
      "type": "extra_forbidden",
      "loc": ["body", "invalid_field"],
      "msg": "Extra inputs are not permitted"
    }
  ]
}
```

## See Also

- [API Endpoints](endpoints.md) - Available endpoints
- [Authentication](authentication.md) - Authentication guide
- [Examples](examples.md) - API usage examples
- [Error Handling](error-handling.md) - Error response format
