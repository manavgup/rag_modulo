# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG Modulo is a modular Retrieval-Augmented Generation (RAG) solution with flexible vector database support, customizable embedding models, and document processing capabilities. The project uses a service-based architecture with clean separation of concerns.

## Architecture

### Backend (Python/FastAPI)
- **Service Layer**: Business logic in `backend/rag_solution/services/`
- **Repository Pattern**: Data access in `backend/rag_solution/repository/`
- **Provider System**: LLM providers in `backend/rag_solution/generation/providers/`
- **Router Layer**: API endpoints in `backend/rag_solution/router/`
- **Models**: SQLAlchemy models in `backend/rag_solution/models/`
- **Schemas**: Pydantic schemas in `backend/rag_solution/schemas/`

### Frontend (React/Carbon Design)
- React 18 with Carbon Design System
- Located in `webui/` directory
- Uses axios for API calls

### Infrastructure
- PostgreSQL for metadata
- Milvus for vector storage (configurable)
- MLFlow for model tracking
- MinIO for object storage
- Docker Compose for orchestration

## Common Development Commands

### Running the Application
```bash
# Quick start with pre-built images (recommended)
make run-ghcr

# Build and run locally
make build-all
make run-app

# Access points
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# MLFlow: http://localhost:5001
```

### Testing
```bash
# Run specific test file
make test testfile=tests/api/test_auth.py

# Run test categories
make unit-tests          # Unit tests with coverage
make integration-tests   # Integration tests
make api-tests          # API endpoint tests
make performance-tests  # Performance benchmarks

# Local testing without Docker
cd backend && poetry run pytest tests/ -m unit
```

### Code Quality
```bash
# Quick quality check (formatting + linting)
make quick-check

# Auto-fix formatting and import issues
make fix-all

# Full linting (Ruff + MyPy)
make lint

# Run linting with Poetry directly
cd backend && poetry run ruff check rag_solution/ tests/ --line-length 120
cd backend && poetry run mypy rag_solution/ --ignore-missing-imports

# Security checks
make security-check
```

### Dependency Management
```bash
# Backend dependencies (using Poetry)
cd backend
poetry install --with dev,test  # Install all dependencies
poetry add <package>            # Add new dependency
poetry lock                     # Update lock file

# Frontend dependencies
cd webui
npm install                     # Install dependencies
npm run dev                    # Development mode with hot reload
```

## Key Environment Variables

Required environment variables (see `env.example` for full list):
- `COLLECTIONDB_*`: PostgreSQL configuration
- `VECTOR_DB`: Vector database type (default: milvus)
- `MILVUS_*`: Milvus configuration
- `WATSONX_*`: WatsonX API credentials
- `OPENAI_API_KEY`: OpenAI API key (optional)
- `ANTHROPIC_API_KEY`: Anthropic API key (optional)
- `JWT_SECRET_KEY`: JWT secret for authentication

## Testing Strategy

### Test Markers
- `@pytest.mark.unit`: Fast unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.api`: API endpoint tests
- `@pytest.mark.performance`: Performance tests
- `@pytest.mark.atomic`: Atomic model tests

### Test Organization
- Unit tests: `backend/tests/services/`, `backend/tests/test_*.py`
- Integration tests: `backend/tests/integration/`
- Performance tests: `backend/tests/performance/`
- API tests: `backend/tests/api/`

## CI/CD Pipeline

### GitHub Actions Workflow
1. **Lint and Unit Tests**: Fast feedback without infrastructure
2. **Build Images**: Docker images built and pushed to GHCR
3. **Integration Tests**: Full stack testing with all services

### Local CI Validation
```bash
# Run same checks as CI locally
make ci-local

# Validate CI workflows
make validate-ci
```

## Important Notes

### Current Status
- ⚠️ Authentication system needs fixing (OIDC issues blocking testing)
- ✅ Infrastructure and containers working
- ✅ Comprehensive test suite implemented (but untested)
- ⚠️ Local pytest setup may have dependency issues

### Development Best Practices
1. **Service Architecture**: Always implement features as services with dependency injection
2. **Type Hints**: Use type hints throughout the codebase
3. **Async/Await**: Use async operations where appropriate
4. **Error Handling**: Proper error handling with custom exceptions
5. **Testing**: Write tests for new features (unit + integration)
6. **Line Length**: 120 characters for Python code

### Vector Database Support
The system supports multiple vector databases through a common interface:
- Milvus (default)
- Elasticsearch
- Pinecone
- Weaviate
- ChromaDB

### LLM Provider Integration
Providers are abstracted through a common interface:
- WatsonX (IBM)
- OpenAI
- Anthropic

Each provider implementation is in `backend/rag_solution/generation/providers/`.

## Troubleshooting

### Container Issues
```bash
# Check container health
docker compose ps

# View logs
make logs

# Restart services
make stop-containers
make run-services
```

### Test Failures
```bash
# Run specific test with verbose output
make test testfile=tests/api/test_auth.py

# Check test logs
docker compose logs test
```

### Dependency Issues
```bash
# Regenerate Poetry lock file
cd backend && poetry lock

# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
```

## Documentation References

- Backend service documentation: `backend/rag_solution/docs/`
- Test documentation: `backend/tests/README.md`
- Local CI guide: `LOCAL_CI.md`
- Main README: `README.md`