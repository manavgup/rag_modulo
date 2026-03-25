# CLAUDE.md

## Project Overview

RAG Modulo: production-ready modular RAG platform. Python/FastAPI backend, React/Carbon frontend.
Comprehensive automated test suite. Poetry at project root.

## Architecture

- Services: `backend/rag_solution/services/`
- Repositories: `backend/rag_solution/repository/`
- LLM Providers: `backend/rag_solution/generation/providers/`
- Routers: `backend/rag_solution/router/`
- Models: `backend/rag_solution/models/`
- Schemas: `backend/rag_solution/schemas/`
- Frontend: `frontend/` (React 18, Carbon Design System)
- Infra: PostgreSQL, Milvus, MinIO, MLFlow (Docker Compose)

## Commands

| Task | Command |
|---|---|
| Install deps | `poetry install --with dev,test` |
| Backend dev | `make local-dev-backend` |
| Frontend dev | `make local-dev-frontend` |
| Infra only | `make local-dev-infra` |
| All background | `make local-dev-all` |
| Atomic tests | `make test-atomic` (~5s) |
| Unit tests | `make test-unit-fast` (~30s) |
| Integration | `make test-integration` (~2m) |
| E2E tests | `make test-e2e` (~5m) |
| All tests | `make test-all` |
| Specific test | `poetry run pytest tests/unit/services/test_foo.py -v` |
| Format | `make format` |
| Lint | `make lint` |
| Pre-commit | `make pre-commit-run` |
| Coverage | `make coverage` (60% minimum) |

## Coding Standards

- Python 3.12, line length 120, double quotes, Ruff formatting
- Type hints on all functions (MyPy enforced)
- Import order: first-party (rag_solution, core, auth, vectordbs) -> third-party -> stdlib
- Service architecture with dependency injection
- Async/await where appropriate
- Structured logging: `from core.enhanced_logging import get_logger`

## Conventions

- New features: implement as services in `backend/rag_solution/services/`
- Data access: repository pattern in `backend/rag_solution/repository/`
- API endpoints: router layer in `backend/rag_solution/router/`
- Schemas: Pydantic in `backend/rag_solution/schemas/`
- Tests: `tests/unit/`, `tests/integration/`, `tests/api/`, `tests/performance/`
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.atomic`
- Poetry at project root. After editing pyproject.toml, always run `poetry lock`.

## Important Reminders

- Do what has been asked; nothing more, nothing less.
- NEVER create files unless absolutely necessary. Prefer editing existing files.
- NEVER proactively create documentation files (*.md) unless explicitly requested.
- Never commit secrets. See `docs/development/secret-management.md` if needed.
