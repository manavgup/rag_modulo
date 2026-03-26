---
name: Backend Service Pattern
description: How to create new services, repositories, routers, and schemas in RAG Modulo. Trigger when creating new backend features, endpoints, or data models.
allowed-tools: Read, Grep, Glob, Write, Edit
---

# Backend Service Pattern

When creating a new feature in the RAG Modulo backend, follow this layered architecture:

## Layer Order (build bottom-up)

1. **Schema** (`backend/rag_solution/schemas/`) - Pydantic models for request/response
2. **Model** (`backend/rag_solution/models/`) - SQLAlchemy model if DB storage needed
3. **Repository** (`backend/rag_solution/repository/`) - Data access layer
4. **Service** (`backend/rag_solution/services/`) - Business logic, dependency injection
5. **Router** (`backend/rag_solution/router/`) - FastAPI endpoint, thin controller

## Key Conventions

- Services receive dependencies via constructor injection
- Repositories handle all database operations (never direct DB calls from services)
- Routers are thin: validate input, call service, return response
- All functions have type hints and return types
- Use `from core.enhanced_logging import get_logger` for logging
- Use `from core.logging_context import log_operation` for structured context

## Testing (create alongside implementation)

- Unit test per service method in `tests/unit/services/test_<service>.py`
- Use `@pytest.mark.unit` marker
- Mock repository layer in unit tests
- Integration test in `tests/integration/` for full-stack validation

See `references/service-example.md` for a complete worked example.
