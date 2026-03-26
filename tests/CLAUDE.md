# Testing Conventions

## Organization

- `unit/` - Mocked dependencies, no external services (~30s)
- `integration/` - Real services (Postgres, Milvus, MinIO) (~2m)
- `api/` - API endpoint tests (router layer)
- `performance/` - Performance benchmarks
- `unit/schemas/` - Atomic Pydantic model tests (~5s)

## Markers

Always apply: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.atomic`

## Patterns

- pytest-asyncio for async tests (asyncio_mode = "auto" in pyproject.toml)
- Mock fixtures in conftest.py files per directory
- Use `unittest.mock.patch` / `MagicMock` for service mocks
- Integration tests reuse `make local-dev-infra` containers

## Quick Run

- Single file: `poetry run pytest tests/unit/services/test_search_service.py -v`
- By marker: `poetry run pytest tests/ -m unit`
- With coverage: `poetry run pytest tests/unit/ --cov=backend/rag_solution --cov-report=html`
- Coverage minimum: 60%
