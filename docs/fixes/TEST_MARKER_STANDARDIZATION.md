# Test Marker Standardization

## Problem
The test suite had inconsistent pytest markers, causing tests to be skipped or not run correctly in the CI pipeline. Only 16 out of 101 test files had appropriate markers.

## Solution
Implemented comprehensive pytest marker standardization across all test files to ensure proper CI execution.

## Marker Categories

### Unit Tests: `@pytest.mark.atomic`
**Used for**: Fast tests that don't require external services
- Service logic tests
- Data processing tests
- Model tests
- Utility function tests

**CI Command**: `pytest -m "atomic"`
**Files**: 58 test files

### Integration Tests: `@pytest.mark.integration`
**Used for**: Tests requiring external services or database connections
- Vector database tests
- Full pipeline tests
- External service integration
- End-to-end workflows

**CI Command**: `pytest -m "integration and not performance"`
**Files**: 25 test files

### API Tests: `@pytest.mark.api`
**Used for**: HTTP API endpoint tests
- Router tests
- Authentication tests
- Request/response validation

**Files**: 17 test files (currently run as part of integration tests)

## Test File Categorization Rules

### Automatic Categorization by Path:
- `backend/tests/unit/` → `@pytest.mark.atomic`
- `backend/tests/integration/` → `@pytest.mark.integration`
- `backend/tests/api/` → `@pytest.mark.api`
- `backend/tests/service*/` → `@pytest.mark.atomic`
- `backend/tests/data_ingestion/` → `@pytest.mark.atomic`
- `backend/tests/model/` → `@pytest.mark.atomic`
- `backend/tests/vectordb*/` → `@pytest.mark.integration`
- `backend/tests/router/` → `@pytest.mark.api`

### Content-Based Categorization:
Tests are categorized as `integration` if they contain references to:
- External services: `milvus`, `elasticsearch`, `pinecone`, `weaviate`, `chroma`
- FastAPI clients: `fastapi`, `httpx`, `client`

## CI Pipeline Integration

### Current Workflow
1. **Unit Test Phase**: Runs `@pytest.mark.atomic` tests
   - Fast execution (< 2 minutes)
   - No external dependencies
   - Coverage reporting

2. **Integration Test Phase**: Runs `@pytest.mark.integration` tests
   - Requires Docker services
   - Database connections
   - External service mocks

### Commands Used in CI:
```bash
# Unit tests (lint-and-unit job)
pytest tests/ -m "atomic" --cov=rag_solution

# Integration tests (integration-test job)
pytest -v -s -m "integration and not performance"
```

## Scripts Created

### `scripts/analyze_test_markers.py`
Analyzes all test files for marker compliance:
- Counts marker usage
- Identifies missing markers
- Provides categorization recommendations

### `scripts/add_test_markers.py`
Automatically adds appropriate markers to test files:
- Categorizes based on path and content
- Adds markers before first test function/class
- Preserves existing markers

## Results

### Before Standardization:
- 101 total test files
- 16 files with `@pytest.mark.atomic`
- 0 files with `@pytest.mark.integration`
- 85 files missing markers

### After Standardization:
- 101 total test files
- 58 files with `@pytest.mark.atomic`
- 25 files with `@pytest.mark.integration`
- 17 files with `@pytest.mark.api`
- 1 file without tests (empty file)

## Benefits

1. **Proper CI Execution**: Tests now run in appropriate phases
2. **Faster Feedback**: Unit tests run quickly without infrastructure
3. **Reliable Integration Testing**: Infrastructure tests run with proper setup
4. **Clear Test Organization**: Developers understand test categories
5. **Maintainable**: Scripts ensure ongoing compliance

## Maintenance

The pre-commit hook `validate-ci-environment-fixes` includes marker validation to ensure new test files have appropriate markers.

### Manual Validation:
```bash
# Check marker compliance
python scripts/analyze_test_markers.py

# Add missing markers
python scripts/add_test_markers.py
```
