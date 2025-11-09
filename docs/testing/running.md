# Running Tests

This guide covers all methods for running tests in RAG Modulo.

## Quick Commands

### Atomic Tests (Fastest - ~5 seconds)

```bash
make test-atomic
```

Fast schema and data structure tests. No database required.

### Unit Tests (Fast - ~30 seconds)

```bash
make test-unit-fast
```

Unit tests with mocked dependencies. No external services required.

### Integration Tests (Medium - ~2 minutes)

```bash
# Local mode (reuses dev infrastructure)
make test-integration

# CI mode (isolated containers)
make test-integration-ci

# Parallel execution
make test-integration-parallel
```

Tests with real services (Postgres, Milvus, MinIO). Local mode reuses `local-dev-infra` containers for speed.

### End-to-End Tests (Slower - ~5 minutes)

```bash
# Local with TestClient (in-memory)
make test-e2e

# CI mode with isolated backend
make test-e2e-ci

# Parallel execution
make test-e2e-ci-parallel
make test-e2e-local-parallel
```

Full system tests from API to database.

### Run All Tests

```bash
# Local: atomic → unit → integration → e2e
make test-all

# CI: atomic → unit → integration-ci → e2e-ci-parallel
make test-all-ci
```

## Coverage Reports

```bash
# Generate HTML coverage report (60% minimum)
make coverage

# Report available at: htmlcov/index.html
open htmlcov/index.html
```

## Direct pytest Commands

### Run Specific Test File

```bash
poetry run pytest tests/unit/services/test_search_service.py -v
```

### Run Tests by Marker

```bash
# Unit tests only
poetry run pytest tests/ -m unit

# Integration tests only
poetry run pytest tests/ -m integration

# E2E tests only
poetry run pytest tests/ -m e2e

# Atomic tests only
poetry run pytest tests/ -m atomic
```

### Run with Verbose Output

```bash
poetry run pytest tests/unit/ -v -s
```

- `-v` - Verbose output
- `-s` - Show print statements

### Run Specific Test Function

```bash
poetry run pytest tests/unit/services/test_search_service.py::test_search_basic -v
```

### Run with Coverage

```bash
poetry run pytest tests/unit/ --cov=backend/rag_solution --cov-report=html
```

## Parallel Test Execution

Use pytest-xdist for parallel execution:

```bash
# Auto-detect CPU cores
poetry run pytest tests/unit/ -n auto

# Specify number of workers
poetry run pytest tests/unit/ -n 4
```

## Test Filtering

### Run Tests Matching Pattern

```bash
# Run all tests with "search" in name
poetry run pytest tests/ -k search

# Run tests NOT matching pattern
poetry run pytest tests/ -k "not slow"
```

### Run Last Failed Tests

```bash
poetry run pytest --lf
```

### Run Failed Tests First

```bash
poetry run pytest --ff
```

## Test Output Options

### Show Local Variables on Failure

```bash
poetry run pytest tests/unit/ -l
```

### Show Test Summary

```bash
poetry run pytest tests/unit/ -ra
```

- `-ra` - Show all test results summary

### Stop on First Failure

```bash
poetry run pytest tests/unit/ -x
```

### Stop After N Failures

```bash
poetry run pytest tests/unit/ --maxfail=3
```

## Debugging Tests

### Run with PDB Debugger

```bash
poetry run pytest tests/unit/services/test_search_service.py --pdb
```

Drops into debugger on failure.

### Show Print Statements

```bash
poetry run pytest tests/unit/ -s
```

## CI/CD Test Execution

Tests run automatically in GitHub Actions:

### On Every PR

```bash
# Runs: atomic + unit tests (~2 min)
make test-atomic
make test-unit-fast
```

### On Push to Main

```bash
# Runs: all tests including integration (~5 min)
make test-all-ci
```

See [CI/CD Documentation](../development/ci-cd-security.md) for workflow details.

## Test Requirements

Before running integration tests:

```bash
# Start infrastructure services
make local-dev-infra

# Verify services are running
docker compose ps
```

## Troubleshooting

### Tests Failing Locally

1. **Clean Python cache**
   ```bash
   find . -type d -name __pycache__ -exec rm -r {} +
   ```

2. **Restart infrastructure**
   ```bash
   make local-dev-stop
   make local-dev-infra
   ```

3. **Reinstall dependencies**
   ```bash
   poetry install --with dev,test
   ```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker compose ps postgres

# View logs
docker compose logs postgres
```

### Vector Database Issues

```bash
# Check Milvus is running
docker compose ps milvus-standalone

# View logs
docker compose logs milvus-standalone
```

## See Also

- [Testing Strategy](strategy.md) - Overall testing approach
- [Test Categories](categories.md) - Detailed category descriptions
- [Development Workflow](../development/workflow.md) - Development process
