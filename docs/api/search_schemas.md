# Search Schemas

## Overview

The search schemas define the data structures for search requests and responses in the RAG system. The schemas have been simplified to remove client-side pipeline management complexity while maintaining full search functionality.

## Core Schema Architecture

### Pydantic V2 Integration

```python
from pydantic import BaseModel, ConfigDict, UUID4
from typing import Any

# Base configuration for all search schemas
search_config = ConfigDict(
    from_attributes=True,
    extra="forbid",  # Reject unknown fields for validation
    validate_assignment=True,
    str_strip_whitespace=True
)
```

## SearchInput Schema

### Schema Definition

```python
from rag_solution.schemas.search_schema import SearchInput

class SearchInput(BaseModel):
    """Input schema for search requests.

    Defines the structure of search requests to the API.
    Pipeline selection is handled automatically by the backend based on user context.

    Attributes:
        question: The user's query text
        collection_id: UUID4 of the collection to search in
        user_id: UUID4 of the requesting user
        config_metadata: Optional search configuration parameters
    """

    question: str
    collection_id: UUID4
    user_id: UUID4
    config_metadata: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")
```

### Field Specifications

#### question: str
- **Required**: Yes
- **Type**: String
- **Validation**: Non-empty string, whitespace stripped
- **Purpose**: The user's natural language query
- **Examples**:
  - "What is machine learning?"
  - "How does RAG work?"
  - "Explain the benefits of vector databases"

#### collection_id: UUID4
- **Required**: Yes
- **Type**: UUID4 (Pydantic UUID validation)
- **Purpose**: Identifies the document collection to search
- **Validation**: Must be a valid UUID4 format
- **Example**: `123e4567-e89b-12d3-a456-426614174000`

#### user_id: UUID4
- **Required**: Yes
- **Type**: UUID4 (Pydantic UUID validation)
- **Purpose**: Identifies the user making the request
- **Used for**: Pipeline resolution, access control, audit logging
- **Example**: `987fcdeb-51a2-43d1-9f12-123456789abc`

#### config_metadata: dict[str, Any] | None
- **Required**: No
- **Type**: Optional dictionary with string keys and any values
- **Purpose**: Search configuration overrides and parameters
- **Default**: None (uses system defaults)

### Configuration Metadata Options

```python
# Complete configuration metadata example
config_metadata = {
    # Retrieval Parameters
    "max_chunks": 5,                    # Maximum chunks to retrieve (1-20)
    "similarity_threshold": 0.7,        # Minimum similarity score (0.0-1.0)
    "top_k": 10,                       # Candidates to consider (1-100)
    "reranking_enabled": True,         # Enable result reranking

    # Generation Parameters
    "temperature": 0.7,                # Generation creativity (0.0-1.0)
    "max_new_tokens": 1000,           # Maximum tokens to generate (1-4096)
    "top_p": 0.95,                    # Nucleus sampling (0.0-1.0)
    "top_k_sampling": 50,             # Top-K sampling (1-100)
    "repetition_penalty": 1.1,        # Repetition penalty (0.1-2.0)
    "stop_sequences": ["Human:", "AI:"], # Generation stop sequences

    # Processing Options
    "evaluation_enabled": True,        # Enable answer evaluation
    "streaming": False,               # Enable streaming response
    "include_metadata": True,         # Include document metadata
    "cache_enabled": True,            # Enable response caching

    # Quality Controls
    "min_chunk_length": 50,           # Minimum chunk character length
    "max_chunk_length": 2000,         # Maximum chunk character length
    "duplicate_threshold": 0.9,       # Duplicate detection threshold

    # Performance Controls
    "timeout_seconds": 30,            # Request timeout (1-300)
    "concurrent_requests": 1,         # Concurrent pipeline requests (1-5)
    "batch_size": 1,                  # Batch processing size (1-10)

    # Debug Options
    "debug_mode": False,              # Enable debug information
    "explain_ranking": False,         # Include ranking explanations
    "trace_execution": False          # Include execution tracing
}
```

### Schema Changes from Legacy

#### Removed Fields
- **`pipeline_id`**: Pipeline selection is now automatic based on user context
- **`model_parameters`**: Handled through user's default pipeline configuration
- **`provider_config`**: Managed through the pipeline service

#### Benefits of Simplification
1. **Reduced Client Complexity**: Clients no longer need to manage pipeline selection
2. **Automatic Pipeline Resolution**: Backend handles pipeline selection intelligently
3. **Better Error Handling**: Clear error messages for configuration issues
4. **Improved Security**: Reduced attack surface by limiting client-controlled parameters

### Validation Rules

```python
from pydantic import field_validator, model_validator

class SearchInput(BaseModel):
    # ... field definitions ...

    @field_validator('question')
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate question format and content."""
        if not v or not v.strip():
            raise ValueError('Question cannot be empty')

        if len(v.strip()) < 3:
            raise ValueError('Question must be at least 3 characters long')

        if len(v) > 1000:
            raise ValueError('Question cannot exceed 1000 characters')

        return v.strip()

    @field_validator('config_metadata')
    @classmethod
    def validate_config_metadata(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        """Validate configuration metadata parameters."""
        if v is None:
            return v

        # Validate numeric ranges
        if 'max_chunks' in v:
            max_chunks = v['max_chunks']
            if not isinstance(max_chunks, int) or max_chunks < 1 or max_chunks > 20:
                raise ValueError('max_chunks must be between 1 and 20')

        if 'temperature' in v:
            temp = v['temperature']
            if not isinstance(temp, (int, float)) or temp < 0.0 or temp > 1.0:
                raise ValueError('temperature must be between 0.0 and 1.0')

        if 'similarity_threshold' in v:
            threshold = v['similarity_threshold']
            if not isinstance(threshold, (int, float)) or threshold < 0.0 or threshold > 1.0:
                raise ValueError('similarity_threshold must be between 0.0 and 1.0')

        return v

    @model_validator(mode='after')
    def validate_complete_input(self) -> 'SearchInput':
        """Validate the complete search input for consistency."""
        # Additional cross-field validation can be added here
        return self
```

## SearchOutput Schema

### Schema Definition

```python
from rag_solution.schemas.search_schema import SearchOutput
from vectordbs.data_types import DocumentMetadata, QueryResult

class SearchOutput(BaseModel):
    """Output schema for search responses.

    Defines the structure of search responses from the API.
    This maps directly to what the UI needs to display:
    - The generated answer
    - List of document metadata for showing document info
    - List of chunks with their scores for showing relevant passages

    Attributes:
        answer: Generated answer to the query
        documents: List of document metadata for UI display
        query_results: List of QueryResult
        rewritten_query: Optional rewritten version of the original query
        evaluation: Optional evaluation metrics and results
        execution_time: Time taken to execute the search in seconds
    """

    answer: str
    documents: list[DocumentMetadata]
    query_results: list[QueryResult]
    rewritten_query: str | None = None
    evaluation: dict[str, Any] | None = None
    execution_time: float | None = None

    model_config = ConfigDict(from_attributes=True)
```

### Field Specifications

#### answer: str
- **Type**: String
- **Purpose**: The generated answer to the user's question
- **Content**: Natural language response based on retrieved documents
- **Example**: "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed."

#### documents: list[DocumentMetadata]
- **Type**: List of DocumentMetadata objects
- **Purpose**: Metadata about documents used to generate the answer
- **UI Usage**: Display source documents, enable document navigation
- **Structure**:
```python
class DocumentMetadata(BaseModel):
    id: str                    # Document unique identifier
    filename: str              # Original filename
    page_number: int | None    # Page number (for PDFs)
    chunk_index: int           # Chunk index within document
    title: str | None          # Document title
    author: str | None         # Document author
    created_date: str | None   # Document creation date
    file_size: int | None      # File size in bytes
    file_type: str | None      # MIME type
```

#### query_results: list[QueryResult]
- **Type**: List of QueryResult objects
- **Purpose**: Ranked chunks with similarity scores
- **UI Usage**: Show relevant passages, highlight matching content
- **Structure**:
```python
class QueryResult(BaseModel):
    content: str               # Text content of the chunk
    score: float              # Similarity score (0.0-1.0)
    metadata: dict[str, Any]  # Additional chunk metadata
    document_id: str          # Reference to source document
    chunk_index: int          # Position within document
    start_offset: int | None  # Character offset in original document
    end_offset: int | None    # End character offset
```

#### rewritten_query: str | None
- **Type**: Optional string
- **Purpose**: Query after preprocessing and rewriting
- **Use Cases**: Query expansion, typo correction, intent clarification
- **Example**:
  - Original: "ML benefits"
  - Rewritten: "machine learning benefits advantages applications"

#### evaluation: dict[str, Any] | None
- **Type**: Optional dictionary
- **Purpose**: Quality metrics and evaluation results
- **Structure**:
```python
evaluation = {
    "relevance_score": 0.89,      # Answer relevance (0.0-1.0)
    "confidence": 0.91,           # Generation confidence (0.0-1.0)
    "factuality": 0.85,           # Factual accuracy score (0.0-1.0)
    "coherence": 0.92,            # Answer coherence (0.0-1.0)
    "completeness": 0.88,         # Answer completeness (0.0-1.0)
    "citation_accuracy": 0.94,    # Citation accuracy (0.0-1.0)
    "hallucination_risk": 0.12,   # Hallucination risk (0.0-1.0)
    "sources_used": 3,            # Number of sources cited
    "total_chunks": 5,            # Total chunks considered
    "processing_steps": [         # Detailed processing steps
        "query_rewriting",
        "document_retrieval",
        "reranking",
        "generation",
        "evaluation"
    ]
}
```

#### execution_time: float | None
- **Type**: Optional float
- **Purpose**: Total search execution time in seconds
- **Usage**: Performance monitoring, user feedback
- **Example**: 1.234 (1.234 seconds)

### Response Examples

#### Basic Search Response

```json
{
    "answer": "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed. It involves algorithms that can automatically learn patterns from data and make predictions or decisions.",
    "documents": [
        {
            "id": "doc-123",
            "filename": "ml-introduction.pdf",
            "page_number": 1,
            "chunk_index": 0,
            "title": "Introduction to Machine Learning",
            "author": "Dr. Jane Smith",
            "created_date": "2023-01-15",
            "file_type": "application/pdf"
        }
    ],
    "query_results": [
        {
            "content": "Machine learning algorithms build mathematical models based on training data to make predictions or decisions without being explicitly programmed to perform the task.",
            "score": 0.92,
            "metadata": {
                "document_id": "doc-123",
                "page": 1,
                "section": "introduction"
            },
            "document_id": "doc-123",
            "chunk_index": 0,
            "start_offset": 245,
            "end_offset": 398
        }
    ],
    "rewritten_query": "machine learning definition artificial intelligence algorithms",
    "evaluation": {
        "relevance_score": 0.89,
        "confidence": 0.91,
        "sources_used": 1,
        "total_chunks": 5
    },
    "execution_time": 1.234
}
```

#### Error Response Schema

```python
class SearchErrorResponse(BaseModel):
    """Error response schema for search failures."""

    detail: str                    # Error description
    error_code: str               # Standardized error code
    timestamp: str                # ISO format timestamp
    request_id: str               # Unique request identifier
    user_id: str | None = None    # User ID if available

    model_config = ConfigDict(from_attributes=True)
```

#### Error Response Example

```json
{
    "detail": "No LLM provider available for user 123e4567-e89b-12d3-a456-426614174000. Please configure an LLM provider before searching.",
    "error_code": "CONFIGURATION_ERROR",
    "timestamp": "2023-12-07T10:30:00Z",
    "request_id": "req-abc123",
    "user_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

## Schema Validation

### Input Validation

```python
from pydantic import ValidationError

try:
    # Valid input
    search_input = SearchInput(
        question="What is machine learning?",
        collection_id="123e4567-e89b-12d3-a456-426614174000",
        user_id="987fcdeb-51a2-43d1-9f12-123456789abc",
        config_metadata={"max_chunks": 5}
    )

except ValidationError as e:
    # Handle validation errors
    print(f"Validation error: {e}")
    # e.errors() contains detailed error information
```

### Runtime Validation

```python
# Example validation function
def validate_search_input(search_input: SearchInput) -> None:
    """Additional runtime validation for search input."""

    # Check question content
    if len(search_input.question.split()) < 2:
        raise ValueError("Question should contain at least 2 words")

    # Validate config metadata
    if search_input.config_metadata:
        config = search_input.config_metadata

        # Check for conflicting parameters
        if config.get("streaming") and config.get("evaluation_enabled"):
            raise ValueError("Streaming and evaluation cannot both be enabled")

        # Validate parameter combinations
        if config.get("max_chunks", 5) > config.get("top_k", 10):
            raise ValueError("max_chunks cannot exceed top_k")
```

## Schema Evolution

### Version Management

```python
# Schema versioning approach
class SearchInputV1(BaseModel):
    """Legacy search input schema with pipeline_id."""
    question: str
    collection_id: UUID4
    user_id: UUID4
    pipeline_id: UUID4  # Deprecated
    config_metadata: dict[str, Any] | None = None

class SearchInputV2(BaseModel):
    """Current search input schema with automatic pipeline resolution."""
    question: str
    collection_id: UUID4
    user_id: UUID4
    # pipeline_id removed - handled automatically
    config_metadata: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")
```

### Migration Strategy

```python
def migrate_search_input(legacy_input: dict) -> SearchInput:
    """Migrate legacy search input to current schema."""

    # Remove deprecated fields
    migrated_data = {k: v for k, v in legacy_input.items() if k != "pipeline_id"}

    # Create new schema instance
    return SearchInput(**migrated_data)
```

## Testing Schemas

### Unit Testing

```python
import pytest
from pydantic import ValidationError
from rag_solution.schemas.search_schema import SearchInput, SearchOutput

class TestSearchInput:
    def test_valid_input(self):
        """Test valid search input creation."""
        input_data = {
            "question": "What is machine learning?",
            "collection_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "987fcdeb-51a2-43d1-9f12-123456789abc"
        }

        search_input = SearchInput(**input_data)
        assert search_input.question == "What is machine learning?"
        assert search_input.config_metadata is None

    def test_invalid_uuid(self):
        """Test validation error for invalid UUID."""
        input_data = {
            "question": "What is ML?",
            "collection_id": "invalid-uuid",
            "user_id": "987fcdeb-51a2-43d1-9f12-123456789abc"
        }

        with pytest.raises(ValidationError):
            SearchInput(**input_data)

    def test_extra_fields_rejected(self):
        """Test that extra fields are rejected."""
        input_data = {
            "question": "What is ML?",
            "collection_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "987fcdeb-51a2-43d1-9f12-123456789abc",
            "pipeline_id": "extra-field"  # Should be rejected
        }

        with pytest.raises(ValidationError):
            SearchInput(**input_data)

    def test_config_metadata_validation(self):
        """Test configuration metadata validation."""
        input_data = {
            "question": "What is ML?",
            "collection_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "987fcdeb-51a2-43d1-9f12-123456789abc",
            "config_metadata": {"max_chunks": 25}  # Invalid: > 20
        }

        with pytest.raises(ValidationError):
            SearchInput(**input_data)
```

### Integration Testing

```bash
# Test schema integration with API endpoints
pytest backend/tests/integration/test_search_schema_integration.py

# Test schema validation in real scenarios
pytest backend/tests/integration/test_schema_validation.py

# Test schema migration and compatibility
pytest backend/tests/integration/test_schema_migration.py
```

## Best Practices

1. **Schema Design**:
   - Use strict validation with `extra="forbid"`
   - Provide clear field documentation
   - Include validation examples in docstrings

2. **Field Validation**:
   - Validate field constraints early
   - Provide meaningful error messages
   - Use appropriate data types

3. **Error Handling**:
   - Catch and handle ValidationError appropriately
   - Log validation failures for debugging
   - Return user-friendly error messages

4. **Performance**:
   - Use efficient validation rules
   - Avoid complex validation logic in schemas
   - Cache validation results when appropriate

## Security Considerations

1. **Input Sanitization**:
   - Validate all input fields
   - Sanitize string inputs
   - Prevent injection attacks

2. **Field Restrictions**:
   - Use `extra="forbid"` to reject unknown fields
   - Limit field value ranges
   - Validate UUID formats strictly

3. **Configuration Safety**:
   - Validate metadata parameter ranges
   - Prevent resource exhaustion attacks
   - Limit configuration complexity

## Future Enhancements

1. **Schema Features**:
   - Dynamic schema validation based on context
   - Schema versioning and migration tools
   - Custom validation rules per deployment

2. **Enhanced Validation**:
   - Semantic validation for questions
   - Cross-field dependency validation
   - Real-time validation feedback

3. **Performance Improvements**:
   - Schema caching for frequent validations
   - Parallel validation for complex schemas
   - Optimized serialization/deserialization
