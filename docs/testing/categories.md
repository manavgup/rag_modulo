# Test Categories

RAG Modulo's test suite is organized into four distinct categories based on speed, scope, and dependencies.

## Atomic Tests

**Speed**: ~5 seconds
**Marker**: `@pytest.mark.atomic`
**Location**: `tests/unit/schemas/`

### Purpose

Fast validation of schemas and data structures without any external dependencies.

### Characteristics

- No database connections
- No external services
- No coverage collection
- Pure Pydantic model validation
- Runs in parallel

### Examples

```python
@pytest.mark.atomic
def test_search_input_schema_valid():
    """Test SearchInput schema with valid data."""
    data = {
        "question": "What is machine learning?",
        "collection_id": str(uuid4()),
        "user_id": str(uuid4())
    }
    schema = SearchInput(**data)
    assert schema.question == data["question"]

@pytest.mark.atomic
def test_conversation_message_input_schema():
    """Test ConversationMessageInput schema validation."""
    # Test implementation
```

### When to Use

- Validating Pydantic schemas
- Testing data structure validation
- Quick sanity checks
- Pre-commit validation

### Running

```bash
make test-atomic
```

## Unit Tests

**Speed**: ~30 seconds
**Marker**: `@pytest.mark.unit`
**Location**: `tests/unit/`

### Purpose

Test individual components in isolation with mocked dependencies.

### Characteristics

- Mocked database sessions
- Mocked external services
- No real infrastructure required
- Fast execution
- High test isolation

### Examples

```python
@pytest.mark.unit
def test_search_service_basic_query(mock_db_session):
    """Test SearchService basic query with mocks."""
    service = SearchService(mock_db_session)

    # Mock repository responses
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_collection

    result = service.search(search_input)
    assert result.answer is not None

@pytest.mark.unit
def test_conversation_repository_create_session(mock_db_session):
    """Test ConversationRepository session creation."""
    # Test implementation with mocked database
```

### When to Use

- Testing service logic
- Testing repository methods
- Testing utility functions
- Testing business logic in isolation

### Running

```bash
make test-unit-fast
```

## Integration Tests

**Speed**: ~2 minutes
**Marker**: `@pytest.mark.integration`
**Location**: `tests/integration/`

### Purpose

Test component interactions with real services and databases.

### Characteristics

- Real PostgreSQL database
- Real Milvus vector database
- Real MinIO object storage
- Tests service interactions
- Validates data persistence

### Examples

```python
@pytest.mark.integration
def test_search_with_real_database(db_session, test_collection):
    """Test search with real database and vector store."""
    # Create real documents
    doc_service = DocumentService(db_session)
    doc = doc_service.create_document(document_input)

    # Perform real search
    search_service = SearchService(db_session)
    result = search_service.search(search_input)

    assert result.answer is not None
    assert len(result.sources) > 0

@pytest.mark.integration
def test_conversation_flow(db_session, test_user):
    """Test complete conversation flow with persistence."""
    # Test implementation with real database operations
```

### When to Use

- Testing multi-service workflows
- Validating database operations
- Testing vector database integration
- End-to-end feature testing

### Requirements

```bash
# Start infrastructure first
make local-dev-infra
```

### Running

```bash
# Local (reuses dev infrastructure)
make test-integration

# CI mode (isolated containers)
make test-integration-ci

# Parallel execution
make test-integration-parallel
```

## End-to-End Tests

**Speed**: ~5 minutes
**Marker**: `@pytest.mark.e2e`
**Location**: `tests/api/`, `tests/e2e/`

### Purpose

Test complete workflows from API endpoints through to database, simulating real user interactions.

### Characteristics

- Full API testing via TestClient
- Complete request/response validation
- Authentication and authorization
- Error handling validation
- Business workflow testing

### Examples

```python
@pytest.mark.e2e
def test_document_upload_and_search(test_client, auth_headers):
    """Test complete document upload and search workflow."""
    # Upload document via API
    response = test_client.post(
        "/api/documents/upload",
        files={"file": ("test.pdf", pdf_content)},
        headers=auth_headers
    )
    assert response.status_code == 200
    doc_id = response.json()["id"]

    # Search for content
    search_response = test_client.post(
        "/api/search",
        json={"question": "test query", "collection_id": collection_id},
        headers=auth_headers
    )
    assert search_response.status_code == 200
    assert len(search_response.json()["sources"]) > 0

@pytest.mark.e2e
def test_conversation_session_lifecycle(test_client, auth_headers):
    """Test complete conversation session lifecycle."""
    # Test implementation
```

### When to Use

- Testing API endpoints
- Validating complete user workflows
- Testing authentication flows
- Regression testing
- Acceptance testing

### Running

```bash
# Local with TestClient (in-memory)
make test-e2e

# CI mode with isolated backend
make test-e2e-ci

# Parallel execution
make test-e2e-ci-parallel
```

## Performance Tests

**Marker**: `@pytest.mark.performance`
**Location**: `tests/performance/`

### Purpose

Benchmark and validate performance characteristics.

### Examples

```python
@pytest.mark.performance
def test_search_latency(db_session, benchmark):
    """Benchmark search service latency."""
    result = benchmark(search_service.search, search_input)
    assert result is not None
```

### Running

```bash
poetry run pytest tests/performance/ -m performance
```

## Test Matrix

| Category | Speed | Dependencies | Use Case | Marker |
|----------|-------|--------------|----------|--------|
| Atomic | ~5s | None | Schema validation | `@pytest.mark.atomic` |
| Unit | ~30s | Mocks only | Component isolation | `@pytest.mark.unit` |
| Integration | ~2min | Real services | Service interaction | `@pytest.mark.integration` |
| E2E | ~5min | Full stack | Complete workflows | `@pytest.mark.e2e` |
| Performance | Varies | Depends on test | Benchmarking | `@pytest.mark.performance` |

## Choosing Test Category

### Use Atomic Tests When:
- Validating Pydantic schemas
- Testing data structures
- No business logic involved

### Use Unit Tests When:
- Testing single component
- Can mock all dependencies
- Fast feedback needed

### Use Integration Tests When:
- Testing service interactions
- Need real database operations
- Testing data persistence

### Use E2E Tests When:
- Testing complete workflows
- Validating API contracts
- Testing user-facing features

## See Also

- [Testing Strategy](strategy.md) - Overall testing approach
- [Running Tests](running.md) - How to run tests
- [Development Workflow](../development/workflow.md) - Development process
