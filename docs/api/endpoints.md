# API Endpoints

This page documents all available REST API endpoints in RAG Modulo.

## Base URL

```
http://localhost:8000/api
```

## Authentication

All endpoints require JWT authentication unless otherwise noted.

See [Authentication](authentication.md) for details on obtaining and using tokens.

## Collections

### List Collections

```
GET /api/collections
```

**Response**:
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "My Documents",
    "description": "Personal document collection",
    "created_at": "2025-01-09T10:00:00Z"
  }
]
```

### Create Collection

```
POST /api/collections
```

**Request**:
```json
{
  "name": "My Documents",
  "description": "Personal document collection",
  "user_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Response**: `201 Created`

### Get Collection

```
GET /api/collections/{collection_id}
```

**Response**:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "My Documents",
  "description": "Personal document collection",
  "document_count": 42,
  "created_at": "2025-01-09T10:00:00Z"
}
```

### Delete Collection

```
DELETE /api/collections/{collection_id}
```

**Response**: `204 No Content`

## Documents

### Upload Document

```
POST /api/documents/upload
```

**Request** (multipart/form-data):
```
file: <binary>
collection_id: 123e4567-e89b-12d3-a456-426614174000
```

**Supported Formats**: PDF, DOCX, TXT, MD, HTML, CSV, Images (with OCR)

**Response**: `201 Created`
```json
{
  "id": "456e7890-e89b-12d3-a456-426614174000",
  "filename": "document.pdf",
  "collection_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing"
}
```

### List Documents

```
GET /api/documents?collection_id={collection_id}
```

**Response**:
```json
[
  {
    "id": "456e7890-e89b-12d3-a456-426614174000",
    "filename": "document.pdf",
    "status": "indexed",
    "created_at": "2025-01-09T10:00:00Z"
  }
]
```

### Delete Document

```
DELETE /api/documents/{document_id}
```

**Response**: `204 No Content`

## Search

### Basic Search

```
POST /api/search
```

**Request**:
```json
{
  "question": "What is machine learning?",
  "collection_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Response**:
```json
{
  "answer": "Machine learning is a subset of artificial intelligence...",
  "sources": [
    {
      "document_id": "456e7890-e89b-12d3-a456-426614174000",
      "chunk_id": "chunk_1",
      "content": "Machine learning involves...",
      "score": 0.95
    }
  ],
  "metadata": {
    "total_tokens": 1250,
    "response_time_ms": 850
  }
}
```

### Chain of Thought Search

```
POST /api/search
```

**Request**:
```json
{
  "question": "How does machine learning work and what are its components?",
  "collection_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "config_metadata": {
    "cot_enabled": true,
    "show_cot_steps": true
  }
}
```

**Response**:
```json
{
  "answer": "Machine learning works through...",
  "reasoning_steps": [
    {
      "sub_question": "What is machine learning?",
      "answer": "Machine learning is...",
      "sources": [...]
    },
    {
      "sub_question": "What are the key components?",
      "answer": "The key components are...",
      "sources": [...]
    }
  ],
  "sources": [...],
  "metadata": {
    "cot_used": true,
    "total_tokens": 3500,
    "response_time_ms": 2600
  }
}
```

## Conversations

### Create Session

```
POST /api/conversations/sessions
```

**Request**:
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Q&A Session",
  "metadata": {}
}
```

**Response**: `201 Created`

### Add Message

```
POST /api/conversations/messages
```

**Request**:
```json
{
  "session_id": "789e0123-e89b-12d3-a456-426614174000",
  "role": "user",
  "message_type": "question",
  "content": "What is machine learning?",
  "token_count": 15
}
```

**Response**: `201 Created`

### Get Session History

```
GET /api/conversations/sessions/{session_id}/messages
```

**Response**:
```json
{
  "session_id": "789e0123-e89b-12d3-a456-426614174000",
  "messages": [
    {
      "id": "msg_1",
      "role": "user",
      "content": "What is machine learning?",
      "created_at": "2025-01-09T10:00:00Z"
    },
    {
      "id": "msg_2",
      "role": "assistant",
      "content": "Machine learning is...",
      "created_at": "2025-01-09T10:00:05Z"
    }
  ]
}
```

## Pipelines

### List Pipelines

```
GET /api/pipelines?user_id={user_id}
```

**Response**:
```json
[
  {
    "id": "pipe_123",
    "name": "Default Pipeline",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "is_default": true
  }
]
```

### Create Pipeline

```
POST /api/pipelines
```

**Request**:
```json
{
  "name": "Custom Pipeline",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "stages": ["query_rewriting", "retrieval", "reranking", "generation"]
}
```

**Response**: `201 Created`

## Health Check

### Service Health

```
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "up",
    "vector_db": "up",
    "llm_provider": "up"
  }
}
```

**Note**: This endpoint does not require authentication.

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

- **Default**: 100 requests per minute per user
- **Search**: 20 requests per minute per user
- **Upload**: 10 requests per minute per user

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1609459200
```

## Pagination

List endpoints support pagination:

```
GET /api/collections?page=1&page_size=20
```

**Query Parameters**:
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20, max: 100)

**Response Headers**:
```
X-Total-Count: 150
X-Page: 1
X-Page-Size: 20
Link: <...>; rel="next", <...>; rel="last"
```

## See Also

- [Authentication](authentication.md) - Authentication guide
- [API Schemas](schemas.md) - Request/response schemas
- [Examples](examples.md) - API usage examples
- [Error Handling](error-handling.md) - Error response format
