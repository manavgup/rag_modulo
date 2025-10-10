# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG Modulo is a modular Retrieval-Augmented Generation (RAG) solution with flexible vector database support, customizable embedding models, and document processing capabilities. The project uses a service-based architecture with clean separation of concerns.

**Recent Update**: The system has been simplified with automatic pipeline resolution, eliminating client-side pipeline management complexity while maintaining full RAG functionality.

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

#### **Local Development (No Containers) - Fastest Iteration** ⚡
```bash
# One-time setup
make local-dev-setup         # Install dependencies (backend + frontend)

# Start development (recommended for daily work)
make local-dev-infra         # Start infrastructure only (Postgres, Milvus, etc.)
make local-dev-backend       # In terminal 1: Start backend with hot-reload
make local-dev-frontend      # In terminal 2: Start frontend with HMR

# OR start everything in background
make local-dev-all           # Start all services in background
make local-dev-status        # Check status
make local-dev-stop          # Stop all services

# Benefits:
# - Instant hot-reload (no container rebuilds)
# - Faster commits (pre-commit hooks optimized)
# - Native debugging
# - Poetry/npm caches work locally
```

#### **Container Development - Production-like Environment** 🐳
```bash
# Quick start with pre-built images (for testing deployment)
make run-ghcr

# Build and run locally
make build-all
make run-app

# Access points (same for both methods)
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# MLFlow: http://localhost:5001
```

**When to use local dev**: Feature development, bug fixes, rapid iteration
**When to use containers**: Testing deployment, CI/CD validation, production-like testing

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

# Pre-commit hooks (optimized for velocity)
git commit -m "your message"  # Fast hooks run on commit (5-10 sec)
git push                       # Slow hooks run on push (mypy, security scans)
git commit --no-verify        # Skip hooks for rapid iteration (use sparingly)
```

**Note**: Pre-commit hooks are optimized for developer velocity:
- **On commit** (fast, 5-10 sec): ruff, trailing-whitespace, yaml checks
- **On push** (slow, 30-60 sec): mypy, pylint, security scans, strangler pattern
- **In CI**: All checks run regardless (ensures quality)

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

## AI-Assisted Development Workflow

This repository supports **automated development** using a multi-agent AI system:

### Architecture
- **Google Gemini**: Writes code implementations
- **Claude Code**: Reviews PRs and provides feedback
- **GitHub Actions**: Runs automated tests and quality checks

### Quick Start

```bash
# 1. Add "ai-assist" label to an issue
# 2. Gemini analyzes and posts implementation plan (2-3 min)
# 3. Review plan → Add "plan-approved" label
# 4. Gemini implements fix on new branch (5-10 min)
# 5. Gemini creates PR automatically
# 6. Claude reviews PR and posts feedback
# 7. Review and merge if approved
```

### When to Use

**✅ Good for:**
- Well-defined bug fixes
- Adding missing tests
- Implementing documented features
- Refactoring with clear goals

**❌ Not recommended for:**
- Vague or poorly described issues
- Security-critical code
- Architecture changes
- Complex algorithms

### Setup (One-Time)

1. **Add Secrets** (GitHub Settings → Secrets):
   ```
   GEMINI_API_KEY=<from https://aistudio.google.com/app/apikey>
   CLAUDE_CODE_OAUTH_TOKEN=<already configured>
   ```

2. **Create Labels**:
   ```bash
   gh label create "ai-assist" --color "4285f4"
   gh label create "plan-approved" --color "10b981"
   gh label create "ai-generated" --color "a855f7"
   ```

### Workflow Stages

1. **Planning** (Gemini): Analyzes issue, posts detailed plan
2. **Approval** (Human): Reviews plan, adds `plan-approved` label
3. **Implementation** (Gemini): Creates branch, writes code, creates PR
4. **Testing** (CI/CD): Runs linting, security scans, unit tests
5. **Review** (Claude): Analyzes code, posts review comment
6. **Merge** (Human): Final approval and merge

### Documentation

- **Quick Start**: `docs/development/AI_WORKFLOW_QUICKSTART.md`
- **Full Guide**: `docs/development/ai-assisted-workflow.md` (architecture, setup, best practices)
- **Workflows**: `.github/workflows/gemini-*.yml`

### Cost & Performance

- **Cost**: ~$0.11-0.55 per issue (~$2-11/month for 20 issues)
- **Time Savings**: 10-60 min vs 1-8 hours manual
- **ROI**: 100-200x return on investment

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

### Optimized GitHub Actions Workflow (Issue #349)

The CI/CD pipeline has been optimized for **fast PR feedback** (~2-3 min) while maintaining comprehensive security coverage. Follows IBM's focused workflow pattern with one workflow per purpose.

#### On Every PR:
```
01-lint.yml          → Ruff, MyPy, Pylint, Pydocstyle (~60s)
02-security.yml      → Gitleaks + TruffleHog secret scanning (~45s)
03-build-secure.yml  → Docker builds (only when Dockerfiles/deps change)
04-pytest.yml        → Unit tests with coverage (~90s)
07-frontend-lint.yml → ESLint for React/TypeScript (when frontend changes)
```

#### On Push to Main:
```
05-ci.yml            → Integration tests (full stack)
03-build-secure.yml  → Docker security scans (always)
```

#### Weekly (Monday 2:00 AM UTC):
```
06-weekly-security-audit.yml → Deep vulnerability scanning with SBOM
```

### Key Features

- **Concurrency Control**: Automatically cancels outdated runs when new commits are pushed
- **Smart Path Filtering**: Docker builds only when code/dependencies change
- **Parallel Execution**: All PR workflows run concurrently
- **Fast Feedback**: ~2-3 min for typical PRs (85% faster than before)
- **No Duplication**: Each workflow has single responsibility

### Performance

- **Before Optimization**: ~15 min per PR
- **After Optimization**: ~2-3 min per PR
- **Savings**: ~3,900 GitHub Actions minutes/month

### Local CI Validation
```bash
# Run same checks as CI locally
make ci-local

# Validate CI workflows
make validate-ci
```

## Important Notes

### Current Status
- ✅ **Simplified Pipeline Resolution**: Automatic pipeline selection implemented (GitHub Issue #222)
- ✅ **Chain of Thought (CoT) Reasoning**: Enhanced RAG search quality implemented (GitHub Issue #136)
- ✅ Infrastructure and containers working
- ✅ Comprehensive test suite implemented and passing
- ✅ API documentation updated for simplified architecture
- ⚠️ Authentication system needs fixing (OIDC issues blocking some features)

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

## API and Search System

### Simplified Search Architecture

The search system now uses automatic pipeline resolution:

**Search Input Schema** (simplified):
```python
class SearchInput(BaseModel):
    question: str
    collection_id: UUID4
    user_id: UUID4
    config_metadata: dict[str, Any] | None = None
    # pipeline_id removed - handled automatically
```

**Key Benefits**:
- No client-side pipeline management required
- Automatic pipeline creation for new users
- Intelligent error handling for configuration issues
- Simplified CLI and API interfaces

### Search API Usage

```python
# Simple search request
search_input = SearchInput(
    question="What is machine learning?",
    collection_id=collection_uuid,
    user_id=user_uuid
)

# Chain of Thought (CoT) enhanced search
search_input = SearchInput(
    question="How does machine learning work and what are the key components?",
    collection_id=collection_uuid,
    user_id=user_uuid,
    config_metadata={
        "cot_enabled": True,  # Explicitly enable CoT
        "show_cot_steps": True,  # Include reasoning steps in response
        "cot_config": {
            "max_reasoning_depth": 3,
            "reasoning_strategy": "decomposition"
        }
    }
)

# Backend automatically:
# 1. Resolves user's default pipeline
# 2. Creates pipeline if none exists
# 3. Uses user's LLM provider settings
# 4. Detects complex questions and applies CoT reasoning
# 5. Executes search and returns results with reasoning steps
```

### CLI Search Commands

```bash
# Simple search - no pipeline management needed
./rag-cli search query col_123abc "What is machine learning?"

# Complex questions automatically trigger Chain of Thought reasoning
./rag-cli search query col_123abc "How does machine learning work and what are the key components?"

# System automatically handles:
# - Pipeline resolution
# - LLM provider selection
# - Configuration management
# - CoT reasoning for complex questions
```

## Documentation References

### API Documentation
- **API Overview**: `docs/api/index.md` - Complete API documentation
- **Search API**: `docs/api/search_api.md` - Search system with automatic pipeline resolution
- **Search Schemas**: `docs/api/search_schemas.md` - Data structures and validation
- **Service Configuration**: `docs/api/service_configuration.md` - Backend service setup
- **Provider Configuration**: `docs/api/provider_configuration.md` - LLM provider management

### CLI Documentation
- **CLI Overview**: `docs/cli/index.md` - Command-line interface guide
- **Search Commands**: `docs/cli/commands/search.md` - Search operations
- **Authentication**: `docs/cli/authentication.md` - CLI authentication setup
- **Configuration**: `docs/cli/configuration.md` - CLI configuration management

### Development Documentation
- **Backend Development**: `docs/development/backend/index.md` - Backend development guidelines
- **Development Workflow**: `docs/development/workflow.md` - Development process
- **Contributing**: `docs/development/contributing.md` - Contribution guidelines
- **Testing Guide**: `docs/testing/index.md` - Comprehensive testing documentation

### Other References
- **Installation**: `docs/installation.md` - Setup and installation guide
- **Configuration**: `docs/configuration.md` - System configuration
- **Getting Started**: `docs/getting-started.md` - Quick start guide
- **Main README**: `README.md` - Project overview

## Key Architecture Changes

### Simplified Pipeline Resolution (GitHub Issue #222)

**What Changed**:
- Removed `pipeline_id` from `SearchInput` schema (`rag_solution/schemas/search_schema.py`)
- Added automatic pipeline resolution in `SearchService` (`rag_solution/services/search_service.py`)
- Simplified CLI search commands by removing pipeline parameters
- Enhanced error handling for configuration issues

**Implementation Details**:
- `SearchService._resolve_user_default_pipeline()` method handles automatic pipeline selection
- Creates default pipelines for new users using their LLM provider
- Validates pipeline accessibility and handles errors gracefully
- CLI commands simplified to only require collection_id and query

**Testing**:
- Unit tests: `tests/unit/test_search_service_pipeline_resolution.py`
- Integration tests: `tests/integration/test_search_integration.py`
- All tests passing with automatic pipeline resolution

**Breaking Changes**:
- SearchInput schema no longer accepts `pipeline_id` field
- CLI search commands no longer require `--pipeline-id` parameter
- API clients must update to use simplified schema

### Chain of Thought (CoT) Reasoning (GitHub Issue #136)

**What Changed**:
- Added comprehensive CoT reasoning system for enhanced RAG search quality
- Implemented automatic question classification to detect when CoT is beneficial
- Added conversation-aware context building for better reasoning
- Integrated CoT seamlessly into existing search pipeline with fallback mechanisms

**Implementation Details**:
- `ChainOfThoughtService` - Core reasoning orchestration (500+ lines)
- `QuestionDecomposer` - Breaks complex questions into sub-questions
- `AnswerSynthesizer` - Combines reasoning steps into final answers
- `SourceAttributionService` - Tracks and attributes sources across reasoning steps
- Automatic CoT detection in `SearchService._should_use_chain_of_thought()`
- Conversation-aware context enhancement with `_build_conversation_aware_context()`

**CoT Features**:
- **Automatic Detection**: Complex questions trigger CoT reasoning automatically
- **Question Decomposition**: Multi-part questions broken into logical steps
- **Iterative Reasoning**: Each step builds on previous context and answers
- **Source Attribution**: Tracks document sources across all reasoning steps
- **Fallback Handling**: Gracefully falls back to regular search if CoT fails
- **Configurable**: Users can enable/disable CoT and control reasoning depth

**Testing**:
- Unit tests: `tests/unit/test_chain_of_thought_service_tdd.py` (31 tests)
- Integration tests: `tests/integration/test_chain_of_thought_integration.py`
- Manual test scripts: `dev_tests/manual/test_cot_*.py` for real-world validation

**Usage**:
- Automatic: Complex questions automatically use CoT
- Explicit: Set `cot_enabled: true` in `config_metadata`
- Transparent: Set `show_cot_steps: true` to see reasoning steps

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
- run tests via the targets specified in the Makefile in project root
- run integration tests via make test-integration
- run unit tests via make test-unit-fast
