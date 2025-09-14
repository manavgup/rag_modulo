# Test Marker Audit Report

## Critical Issue: Test Markers Are Incorrectly Applied

### Summary
**MAJOR PROBLEM**: Tests are incorrectly marked throughout the codebase. Unit tests are marked as integration tests, and integration tests are marked as unit tests. This causes tests to run in the wrong contexts and with incorrect configurations.

## Current State Analysis

### 1. Test File Organization
```
tests/
├── atomic/      # ✅ Correctly marked with @pytest.mark.atomic
├── unit/        # ❌ INCORRECTLY marked with @pytest.mark.integration
├── integration/ # ❌ INCORRECTLY marked with @pytest.mark.unit
├── e2e/         # ✅ Correctly marked with @pytest.mark.e2e
└── fixtures/    # Shared fixtures across all test types
```

### 2. Marker Misalignment Details

#### Unit Tests Directory (`tests/unit/`)
**Problem**: All 19 files marked as `@pytest.mark.integration` instead of `@pytest.mark.unit`

Affected files:
- test_search_database.py
- test_milvus_connection.py
- test_vectordbs.py
- test_provider_config.py
- test_search_service.py
- test_team_database.py
- test_user_router.py
- test_data_helper.py
- test_user_team.py
- test_postgresql_connection.py
- test_core_config.py
- test_prompt_template.py
- test_user_flow.py
- test_chunking.py
- test_data_ingestion.py
- test_user_service.py
- test_evaluation.py
- test_team_service.py
- test_watsonx.py

**Exception**: Only `test_simple_unit.py` is correctly marked with `@pytest.mark.unit`

#### Integration Tests Directory (`tests/integration/`)
**Problem**: At least one file (`test_chunking.py`) marked as `@pytest.mark.unit` instead of `@pytest.mark.integration`

### 3. Makefile Test Targets

The Makefile defines four test categories:

```makefile
test-atomic:     # Uses pytest-atomic.ini, runs tests/atomic/
test-unit-fast:  # Uses pytest-atomic.ini, runs tests/unit/
test-integration: # Standard pytest.ini, runs tests/integration/
test-e2e:        # Standard pytest.ini, runs tests/e2e/
```

**Issue**: The Makefile expects:
- `tests/unit/` to contain unit tests
- `tests/integration/` to contain integration tests

But the actual markers don't match this expectation!

### 4. Configuration Files

#### pytest.ini
```ini
markers =
    unit: Unit tests that do not require external services
    integration: Integration tests requiring external services
    e2e: End-to-end tests that test complete workflows
    atomic: Atomic fixture tests
```

#### pytest-atomic.ini
```ini
markers =
    atomic: Ultra-fast tests with no external dependencies
    unit: Fast unit tests with minimal setup
    integration: Database/service integration tests
    e2e: End-to-end workflow tests
```

Both configuration files define the markers correctly, but tests aren't using them properly.

### 5. Test Dependencies Analysis

#### E2E Tests (`tests/e2e/`)
- **Current**: Using real services but WITH MOCKS
- **Problem**: Not true E2E tests
- Example: `test_search_service_real.py` uses `Mock(spec=Session)` for database

#### Unit Tests (`tests/unit/`)
- **Current**: Marked as integration, may try to connect to real services
- **Problem**: Will fail when run without infrastructure
- Contains files like `test_milvus_connection.py` and `test_postgresql_connection.py` which suggest integration testing

#### Integration Tests (`tests/integration/`)
- **Current**: Some marked as unit tests
- **Problem**: Won't run with integration test command

## Impact of Incorrect Markers

1. **Performance**: Unit tests may try to connect to databases, making them slow
2. **Reliability**: Tests fail when infrastructure isn't available
3. **CI/CD**: Wrong tests run at wrong stages of pipeline
4. **Coverage**: Incorrect coverage reports due to miscategorized tests

## Fixture Organization Issues

### Current Fixture Structure
```
tests/fixtures/
├── auth.py         # Authentication fixtures
├── integration.py  # Integration test fixtures
└── user.py        # User-related fixtures
```

### Fixture Import Chain
- `tests/unit/conftest.py` imports from `tests/fixtures/auth.py`
- Unit tests are using integration fixtures
- No clear separation between unit and integration fixtures

## Recommended Actions

### 1. Immediate Fixes Required

```bash
# Fix all unit test markers
find tests/unit -name "*.py" -exec sed -i '' 's/@pytest.mark.integration/@pytest.mark.unit/g' {} \;

# Fix all integration test markers
find tests/integration -name "*.py" -exec sed -i '' 's/@pytest.mark.unit/@pytest.mark.integration/g' {} \;
```

### 2. Test Categorization Guidelines

| Test Type | Marker | Dependencies | Execution Time | Location |
|-----------|--------|-------------|----------------|----------|
| Atomic | `@pytest.mark.atomic` | None | <100ms | `tests/atomic/` |
| Unit | `@pytest.mark.unit` | Mocked only | <500ms | `tests/unit/` |
| Integration | `@pytest.mark.integration` | Real DB, mocked external | <5s | `tests/integration/` |
| E2E | `@pytest.mark.e2e` | All real services | >5s | `tests/e2e/` |

### 3. Proper Test Structure

#### Unit Test Example
```python
@pytest.mark.unit
class TestSearchService:
    def test_search_with_mock_db(self, mock_db, mock_settings):
        # Uses only mocked dependencies
        service = SearchService(mock_db, mock_settings)
        assert service is not None
```

#### Integration Test Example
```python
@pytest.mark.integration
class TestSearchServiceIntegration:
    def test_search_with_real_db(self, real_db, test_settings):
        # Uses real database but mocked external services
        service = SearchService(real_db, test_settings)
        result = service.search("test query")
        assert result is not None
```

#### E2E Test Example
```python
@pytest.mark.e2e
class TestSearchE2E:
    def test_complete_search_flow(self, test_client):
        # Uses real API endpoint with all real services
        response = test_client.post("/api/search", json={...})
        assert response.status_code == 200
```

### 4. Files That Need Reclassification

#### Move from `unit/` to `integration/`:
- test_milvus_connection.py
- test_postgresql_connection.py
- test_search_database.py
- test_team_database.py
- test_user_database.py
- test_vectordbs.py

#### Keep in `unit/` but fix markers:
- test_search_service.py (ensure it uses only mocks)
- test_user_service.py (ensure it uses only mocks)
- test_team_service.py (ensure it uses only mocks)
- test_collection_service.py (ensure it uses only mocks)

### 5. E2E Test Fixes

Current E2E tests are not true E2E because they use mocks. They need to:
1. Use real database connections
2. Use real Milvus connections
3. Test through API endpoints, not direct service calls
4. Only mock external third-party services (OpenAI, WatsonX)

## Test Execution Commands After Fixes

```bash
# Run only atomic tests (fastest, no dependencies)
pytest -m atomic

# Run only unit tests (fast, mocked dependencies)
pytest -m unit

# Run only integration tests (requires database)
pytest -m integration

# Run only E2E tests (requires full stack)
pytest -m e2e

# Run tests by directory (after fixing markers)
make test-atomic      # Runs tests/atomic/
make test-unit-fast   # Runs tests/unit/
make test-integration # Runs tests/integration/
make test-e2e        # Runs tests/e2e/
```

## Validation Script

Create this script to validate test markers:

```python
# validate_test_markers.py
import ast
import os
from pathlib import Path

def check_test_markers(directory, expected_marker):
    issues = []
    for file in Path(directory).glob("**/test_*.py"):
        with open(file) as f:
            tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        if hasattr(decorator, 'attr'):
                            marker = decorator.attr
                            if marker != expected_marker and marker != 'asyncio':
                                issues.append(f"{file}: Found @pytest.mark.{marker}, expected @pytest.mark.{expected_marker}")
    return issues

# Check each directory
issues = []
issues.extend(check_test_markers("tests/atomic", "atomic"))
issues.extend(check_test_markers("tests/unit", "unit"))
issues.extend(check_test_markers("tests/integration", "integration"))
issues.extend(check_test_markers("tests/e2e", "e2e"))

for issue in issues:
    print(issue)
```

## Summary

The test suite has a fundamental organizational problem where:
1. **Test markers don't match their directory locations**
2. **E2E tests aren't true end-to-end tests** (they use mocks)
3. **Unit tests are marked as integration tests** and vice versa
4. **Some unit tests appear to be integration tests** based on their names

This needs immediate correction to ensure:
- Tests run in the correct context
- CI/CD pipeline stages work correctly
- Test execution times are optimized
- Coverage reports are accurate
