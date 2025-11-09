# Testing Strategy

RAG Modulo employs a comprehensive testing strategy with **947+ automated tests** organized by speed and scope.

## Test Organization

### Test Categories

Tests are organized into four main categories:

1. **Atomic Tests** (Fastest - ~5 seconds)
   - Schema and data structure validation
   - Pydantic model tests
   - No database required

2. **Unit Tests** (Fast - ~30 seconds)
   - Individual function/class testing
   - Mocked dependencies
   - No external services

3. **Integration Tests** (Medium - ~2 minutes)
   - Service interaction tests
   - Real database operations
   - Vector database integration

4. **End-to-End Tests** (Slower - ~5 minutes)
   - Full system tests
   - API to database workflows
   - Complete feature validation

## Test Markers

Tests use pytest markers for categorization:

- `@pytest.mark.atomic` - Atomic schema tests
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.performance` - Performance benchmarks

## Running Tests

See [Running Tests](running.md) for detailed commands and usage.

## Test Coverage

- **Minimum Coverage**: 60%
- **Current Tests**: 947+ automated tests
- **Coverage Report**: `make coverage` (generates HTML report)

## Testing Best Practices

### Unit Testing

- Mock external dependencies
- Test one component at a time
- Use fixtures for common setup
- Keep tests fast and isolated

### Integration Testing

- Use real services (Postgres, Milvus)
- Test service interactions
- Validate data persistence
- Clean up test data

### End-to-End Testing

- Test complete workflows
- Validate API contracts
- Test error handling
- Verify business logic

## Test Fixtures

Common fixtures are defined in `tests/conftest.py`:

- `db_session` - Database session
- `test_client` - FastAPI test client
- `sample_user` - Mock user for testing
- `sample_collection` - Mock collection data

## Continuous Integration

All tests run in CI/CD pipeline:

- **On Every PR**: Atomic + Unit tests (~2 min)
- **On Push to Main**: All tests including integration (~5 min)

See [CI/CD Documentation](../development/ci-cd-security.md) for details.

## Test Organization Structure

```
tests/
├── unit/           # Unit tests with mocks
│   ├── services/   # Service layer tests
│   ├── repository/ # Repository layer tests
│   └── schemas/    # Schema validation tests
├── integration/    # Integration tests with real services
├── api/            # API endpoint tests
└── performance/    # Performance benchmarks
```

## Writing New Tests

1. **Determine Test Type**
   - Atomic: Schema/model validation
   - Unit: Single component with mocks
   - Integration: Multiple components with real services
   - E2E: Full workflow testing

2. **Add Appropriate Markers**
   ```python
   @pytest.mark.unit
   def test_search_service_query():
       # Test implementation
   ```

3. **Use Fixtures**
   ```python
   def test_create_collection(db_session, sample_user):
       # Test using fixtures
   ```

4. **Assert Clearly**
   - Use descriptive assertions
   - Test both success and failure cases
   - Validate error messages

## See Also

- [Running Tests](running.md) - How to run tests
- [Test Categories](categories.md) - Detailed category descriptions
- [Development Workflow](../development/workflow.md) - Development process
