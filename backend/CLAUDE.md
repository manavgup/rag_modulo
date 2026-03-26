# Backend Development

## Patterns

- Service Layer: business logic in `rag_solution/services/`, dependency injection via constructors
- Repository Pattern: data access in `rag_solution/repository/`, SQLAlchemy models in `rag_solution/models/`
- Router Layer: FastAPI endpoints in `rag_solution/router/`, thin controllers delegating to services
- Provider System: LLM providers in `rag_solution/generation/providers/`, common interface pattern

## Search Pipeline

- Automatic pipeline resolution: `SearchService._resolve_user_default_pipeline()`
- Chain of Thought: `ChainOfThoughtService` with structured XML output, quality scoring, retry logic
- CoT auto-detection: `SearchService._should_use_chain_of_thought()`
- See `docs/features/chain-of-thought-hardening.md` for full CoT documentation

## Docker

- Backend Dockerfile: `Dockerfile.backend` (multi-stage: Poetry -> slim runtime)
- Cache invalidation: builder stage uses static CACHE_BUST, runtime uses dynamic BACKEND_CACHE_BUST
- CI uses content-based hash: `hashFiles('backend/**/*.py', 'pyproject.toml', 'poetry.lock')`
- See `docs/troubleshooting/docker.md` for cache issues

## Logging

- Use `from core.enhanced_logging import get_logger` (not stdlib logging)
- Structured context: `from core.logging_context import log_operation, pipeline_stage_context`
- Full docs: `docs/development/logging.md`
