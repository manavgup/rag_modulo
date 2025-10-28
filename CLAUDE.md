# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG Modulo is a production-ready, modular Retrieval-Augmented Generation (RAG) platform with flexible vector database support, customizable embedding models, and document processing capabilities. The project uses a service-based architecture with clean separation of concerns.

**Current Status**: Production-ready with 947+ automated tests, comprehensive Chain of Thought reasoning, automatic pipeline resolution, and enhanced security hardening. Poetry configuration has been migrated to project root for cleaner monorepo structure.

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

**Recommended for daily development work**

```bash
# One-time setup
make local-dev-setup         # Install dependencies (backend + frontend)

# Start development (recommended for daily work)
make local-dev-infra         # Start infrastructure only (Postgres, Milvus, etc.)
make local-dev-backend       # In terminal 1: Start backend with uvicorn hot-reload
make local-dev-frontend      # In terminal 2: Start frontend with Vite HMR

# OR start everything in background
make local-dev-all           # Start all services in background
make local-dev-status        # Check status
make local-dev-stop          # Stop all services

# Benefits:
# - Instant hot-reload (no container rebuilds)
# - Faster commits (pre-commit hooks optimized)
# - Native debugging with breakpoints
# - Poetry/npm caches work locally
```

**How it works:**

- **Backend**: Runs directly via `uvicorn main:app --reload` (hot-reload on code changes)
- **Frontend**: Runs directly via `npm run dev` (Vite HMR for instant updates)
- **Infrastructure**: Only Postgres, Milvus, MinIO, MLFlow run in containers
- **Access points:**
  - Frontend: <http://localhost:3000>
  - Backend API: <http://localhost:8000>
  - MLFlow: <http://localhost:5001>

#### **Production Deployment** 🐳

**Only used for production deployments - NOT for local development**

```bash
# Build Docker images (backend + frontend)
make build-backend           # Build backend Docker image
make build-frontend          # Build frontend Docker image
make build-all              # Build all images

# Start production environment (all services in containers)
make prod-start             # Start production stack
make prod-stop              # Stop production stack
make prod-restart           # Restart production
make prod-status            # Check status
make prod-logs              # View logs
```

**How it works:**

- **Backend**: Packaged in Docker image using multi-stage build (Poetry → slim runtime)
- **Frontend**: Packaged in Docker image (Node build → nginx static serving)
- **Infrastructure**: Postgres, Milvus, MinIO, MLFlow in containers (same as local dev)
- **Images published to**: GitHub Container Registry (GHCR) at `ghcr.io/manavgup/rag_modulo`

**When to use:**

- ✅ **Local dev**: Feature development, bug fixes, rapid iteration
- ✅ **Production**: Docker containers for deployment to staging/production environments

### Testing

#### Test Categories

RAG Modulo has a comprehensive test suite with **947+ automated tests** organized by speed and scope:

**1. Atomic Tests** (Fastest - ~5 seconds)

```bash
make test-atomic
```

- Fast schema/data structure tests
- Tests only `tests/unit/schemas/` directory
- No database required, no coverage collection
- Validates Pydantic models

**2. Unit Tests** (Fast - ~30 seconds)

```bash
make test-unit-fast
```

- Unit tests with mocked dependencies
- Tests entire `tests/unit/` directory
- No external services required
- Tests individual functions/classes in isolation

**3. Integration Tests** (Medium - ~2 minutes)

```bash
make test-integration              # Local (reuses dev infrastructure)
make test-integration-ci           # CI mode (isolated containers)
make test-integration-parallel     # Parallel execution with pytest-xdist
```

- Tests with real services (Postgres, Milvus, MinIO)
- Tests service interactions and database operations
- Local mode reuses `local-dev-infra` containers for speed

**4. End-to-End Tests** (Slower - ~5 minutes)

```bash
make test-e2e                    # Local with TestClient (in-memory)
make test-e2e-ci                 # CI mode with isolated backend
make test-e2e-ci-parallel        # CI mode in parallel
make test-e2e-local-parallel     # Local in parallel
```

- Full system tests from API to database
- Tests complete workflows
- Local mode uses TestClient (no separate backend needed)

**5. Run All Tests**

```bash
make test-all       # Runs: atomic → unit → integration → e2e (local)
make test-all-ci    # Runs: atomic → unit → integration-ci → e2e-ci-parallel
```

**6. Coverage Reports**

```bash
make coverage       # Generate HTML coverage report (60% minimum)
# Report available at: htmlcov/index.html
```

#### Direct pytest Commands

```bash
# Run specific test file
poetry run pytest tests/unit/services/test_search_service.py -v

# Run tests by marker
poetry run pytest tests/ -m unit          # Unit tests only
poetry run pytest tests/ -m integration   # Integration tests only
poetry run pytest tests/ -m e2e           # E2E tests only
poetry run pytest tests/ -m atomic        # Atomic tests only

# Run with coverage
poetry run pytest tests/unit/ --cov=backend/rag_solution --cov-report=html
```

### Code Quality & Linting

#### Quick Commands

```bash
# 1. Quick Format Check (fastest - no modifications)
make quick-check
# - Ruff format check
# - Ruff linting check

# 2. Auto-Format Code
make format
# - Ruff format (applies formatting)
# - Ruff check with auto-fix

# 3. Full Linting
make lint
# - Ruff check (linting)
# - MyPy type checking

# 4. Security Scanning
make security-check
# - Bandit (security linter)
# - Safety (dependency vulnerability scanner)

# 5. Complete Pre-Commit Checks (recommended before committing)
make pre-commit-run
# Step 1: Ruff format
# Step 2: Ruff lint with auto-fix
# Step 3: MyPy type checking
# Step 4: Pylint
```

#### Direct Poetry Commands

```bash
# Ruff formatting
poetry run ruff format backend/ --config pyproject.toml

# Ruff linting with auto-fix
poetry run ruff check backend/ --config pyproject.toml --fix

# Type checking
poetry run mypy backend/ --config-file pyproject.toml --ignore-missing-imports

# Security scanning
poetry run bandit -r backend/rag_solution/ -ll
poetry run safety check
```

#### Linting Requirements for All Python Files

When creating or editing Python files, the following checks **MUST** pass:

**1. Ruff Formatting (Line Length: 120 chars)**

- Double quotes for strings
- 120 character line length
- Consistent indentation (spaces, not tabs)
- Magic trailing commas respected

**2. Ruff Linting Rules**

Enabled rule categories:

- **E**: pycodestyle errors
- **F**: pyflakes (undefined names, unused imports)
- **I**: isort (import sorting)
- **W**: pycodestyle warnings
- **B**: flake8-bugbear (common bugs)
- **C4**: flake8-comprehensions
- **UP**: pyupgrade (modern Python syntax)
- **N**: pep8-naming (naming conventions)
- **Q**: flake8-quotes
- **SIM**: flake8-simplify
- **ARG**: flake8-unused-arguments
- **PIE**: flake8-pie
- **TID**: flake8-tidy-imports
- **RUF**: Ruff-specific rules

Import order (enforced by isort):

```python
# 1. First-party imports (main, rag_solution, core, auth, vectordbs)
from rag_solution.services import SearchService
from core.logging import get_logger

# 2. Third-party imports
import pandas as pd
from fastapi import FastAPI

# 3. Standard library imports
import os
from typing import Optional
```

**3. MyPy Type Checking**

- All functions must have type hints
- Return types required
- Python 3.12 target

**4. Security Checks**

- No hardcoded secrets
- No dangerous function calls (eval, exec)
- Secure file operations

#### Pre-Commit Hooks

Pre-commit hooks run automatically via `.pre-commit-config.yaml`:

**On Every Commit** (fast, 5-10 sec):

1. **General Checks**:
   - Trailing whitespace removal
   - End-of-file fixer
   - YAML/JSON/TOML validation
   - Merge conflict detection
   - Large files check
   - Debug statements detection
   - Private key detection

2. **Python Formatting & Linting**:
   - Ruff format
   - Ruff lint with auto-fix

3. **Security**:
   - detect-secrets (secret scanning with baseline)

4. **File-Specific Linters**:
   - yamllint (YAML files)
   - shellcheck (shell scripts)
   - hadolint (Dockerfiles)
   - markdownlint (Markdown files)

5. **Poetry Lock Validation**:
   - Ensures `poetry.lock` is in sync with `pyproject.toml`

**On Push** (slower, 30-60 sec):

1. **Test Execution**:
   - `test-atomic` - Fast schema tests
   - `test-unit-fast` - Unit tests with mocks

**Skip Hooks** (use sparingly for rapid iteration):

```bash
git commit --no-verify   # Skip commit hooks
git push --no-verify     # Skip push hooks
```

**Note**: All checks run in CI regardless of local hooks being skipped.

### Dependency Management

**⚠️ RECENT CHANGE**: Poetry configuration has been **moved to project root** (October 2025) for cleaner monorepo structure.

```bash
# Backend dependencies (using Poetry at root level)
poetry install --with dev,test  # Install all dependencies from root
poetry add <package>            # Add new dependency
poetry lock                     # Update lock file (REQUIRED after modifying pyproject.toml)

# Frontend dependencies
cd webui
npm install                     # Install dependencies
npm run dev                     # Development mode with hot reload
```

**⚠️ IMPORTANT: Poetry Lock File**

When modifying `pyproject.toml` (now in root), you **MUST** run `poetry lock` to keep the lock file in sync:

```bash
# After editing pyproject.toml (adding/removing/updating dependencies):
poetry lock              # Regenerates poetry.lock (run from root)
git add poetry.lock      # Stage the updated lock file
git commit -m "chore: update dependencies"
```

**Why this matters:**

- `poetry.lock` ensures reproducible builds across all environments
- CI will **fail** if `poetry.lock` is out of sync with `pyproject.toml`
- Pre-commit hooks validate lock file sync (prevents accidental drift)
- Never regenerate `poetry.lock` in CI (causes disk space exhaustion)

**Validation:**

```bash
# Check if lock file is in sync (run from root)
poetry check --lock

# Local validation happens automatically via pre-commit hook
# CI validation happens in poetry-lock-check.yml workflow
```

**Migration Notes:**

- Branch: `refactor/poetry-to-root-clean`
- Poetry files moved from `backend/` to project root
- All commands now run from root directory (no need to `cd backend`)
- Docker builds updated to reflect new structure

### Security & Secret Management

**⚠️ CRITICAL: Never commit secrets to git**

RAG Modulo uses a **3-layer defense-in-depth** approach to prevent secret leaks:

1. **Pre-commit hooks** - Fast local validation with detect-secrets (< 1 sec)
2. **Local testing** - Gitleaks scanning via `make pre-commit-run` (~1-2 sec)
3. **CI/CD pipeline** - Comprehensive Gitleaks + TruffleHog scanning (~45 sec)

**Quick Reference:**

```bash
# Run security checks before pushing
make pre-commit-run

# CI now FAILS on ANY secret detection (no exceptions)
# This ensures no secrets make their way to the repository
```

**Supported Secret Types:**

- Cloud Providers: AWS, Azure, GCP
- LLM APIs: OpenAI, Anthropic, WatsonX, Gemini
- Infrastructure: PostgreSQL, MinIO, MLFlow, JWT
- Version Control: GitHub tokens, GitLab tokens
- Generic: High-entropy strings, private keys

**False Positives:**
If secret scanning flags legitimate test data:

```bash
# Update baseline with false positives
detect-secrets scan --baseline .secrets.baseline
detect-secrets audit .secrets.baseline

# Commit updated baseline
git add .secrets.baseline
git commit -m "chore: update secrets baseline"
```

**Emergency Response:**
If a secret is accidentally committed:

1. **ROTATE the secret IMMEDIATELY** (< 5 minutes)
2. Update `.env` with new secret
3. Update CI/CD secrets (GitHub Secrets)
4. Clean git history (see documentation)
5. Verify old secret is revoked

**Full Documentation:** `docs/development/secret-management.md`

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

Required environment variables (see `.env.example` for full list):

- `COLLECTIONDB_*`: PostgreSQL configuration
- `VECTOR_DB`: Vector database type (default: milvus)
- `MILVUS_*`: Milvus configuration
- `WATSONX_*`: WatsonX API credentials
- `OPENAI_API_KEY`: OpenAI API key (optional)
- `ANTHROPIC_API_KEY`: Anthropic API key (optional)
- `JWT_SECRET_KEY`: JWT secret for authentication

## Testing Strategy

### Test Statistics

- **Total Tests**: 947+ automated tests
- **Test Organization**: Migrated to root `tests/` directory (October 2025)
- **Coverage**: Comprehensive unit, integration, API, and atomic model tests
- **Test Execution**: Runs in CI/CD pipeline via GitHub Actions

### Test Markers

- `@pytest.mark.unit`: Fast unit tests (services, utilities, models)
- `@pytest.mark.integration`: Integration tests (full stack)
- `@pytest.mark.api`: API endpoint tests (router layer)
- `@pytest.mark.performance`: Performance benchmarks
- `@pytest.mark.atomic`: Atomic model tests (database layer)

### Test Organization

**Recent Migration (October 2025)**: Tests moved from `backend/tests/` to root `tests/` directory.

- Unit tests: `tests/unit/`
  - Services: `tests/unit/services/`
  - Models: `tests/unit/models/`
  - Utilities: `tests/unit/test_*.py`
- Integration tests: `tests/integration/`
- Performance tests: `tests/performance/`
- API tests: `tests/api/`

### Test Improvements (Issue #486)

- Fixed async test configuration (pytest-asyncio)
- Unified user initialization architecture across all auth methods
- Improved mock fixtures for consistent testing
- Enhanced test isolation and teardown

## CI/CD Pipeline

### Optimized GitHub Actions Workflow (Issue #349)

The CI/CD pipeline has been optimized for **fast PR feedback** (~2-3 min) while maintaining comprehensive security coverage. Follows IBM's focused workflow pattern with one workflow per purpose.

#### On Every PR

```
01-lint.yml          → Ruff, MyPy, Pylint, Pydocstyle (~60s)
02-security.yml      → Gitleaks + TruffleHog secret scanning (~45s)
03-build-secure.yml  → Docker builds (only when Dockerfiles/deps change)
04-pytest.yml        → Unit tests with coverage (~90s)
07-frontend-lint.yml → ESLint for React/TypeScript (when frontend changes)
```

#### On Push to Main

```
05-ci.yml            → Integration tests (full stack)
03-build-secure.yml  → Docker security scans (always)
```

#### Weekly (Monday 2:00 AM UTC)

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

**Active Branch**: `refactor/poetry-to-root-clean` (Poetry migration to project root)

**Recent Achievements**:

- ✅ **Production-Ready**: 947+ automated tests, Docker + GHCR images, multi-stage CI/CD
- ✅ **Chain of Thought (CoT) Reasoning**: Production-grade hardening with retry logic and quality scoring (Issue #461, #136)
- ✅ **Simplified Pipeline Resolution**: Automatic pipeline selection (Issue #222)
- ✅ **Poetry Root Migration**: Clean monorepo structure (October 2025)
- ✅ **Enhanced Security**: Multi-layer scanning (Trivy, Bandit, Gitleaks, TruffleHog)
- ✅ **Frontend Components**: 8 reusable, type-safe UI components with 44% code reduction
- ✅ **IBM Docling Integration**: Enhanced document processing for complex formats
- ✅ **Podcast Generation**: AI-powered podcast creation with voice preview
- ✅ **Smart Suggestions**: Auto-generated relevant questions
- ✅ **User Initialization**: Automatic mock user setup at startup (Issue #480)
- ✅ **Database Management**: Production-grade scripts for backup/restore/migration (Issue #481)
- ✅ **Test Migration**: Moved tests to root directory for better organization (Issue #486)
- ✅ **Docker Optimization**: Cache-bust ARG and Poetry root support in Dockerfiles

**Recent Git History** (last 5 commits):

```
aa3deee - fix(docker): Update Dockerfiles and workflows for Poetry root migration
f74079a - fix(docker): add cache-bust ARG to invalidate stale Docker layers
acf51b6 - refactor: Move Poetry configuration to project root for cleaner monorepo structure
98572db - fix: Add API key fallback to claude.yml workflow and remove duplicate file (#491)
3cbb0e8 - chore(deps): Merge 5 safe Dependabot updates (Python deps, GitHub Actions) (#488)
```

**Modified Files (Unstaged)**:

- `.secrets.baseline` - Updated baseline for secret scanning
- `backend/rag_solution/generation/providers/factory.py` - Provider factory updates
- `backend/rag_solution/models/` - Model updates (collection, question, token_warning)
- `tests/unit/services/test_search_service.py` - Test updates

**Pending Analysis Documents** (Untracked):

- `ISSUE_461_COT_LEAKAGE_FIX.md` - CoT leakage fix documentation
- `PRIORITY_1_2_IMPLEMENTATION_SUMMARY.md` - Hardening implementation summary
- `ROOT_CAUSE_ANALYSIS_REVENUE_QUERY.md` - Query analysis
- Various analysis and progress tracking documents

### Development Best Practices

1. **Service Architecture**: Always implement features as services with dependency injection
2. **Type Hints**: Use type hints throughout the codebase
3. **Async/Await**: Use async operations where appropriate
4. **Error Handling**: Proper error handling with custom exceptions
5. **Testing**: Write tests for new features (unit + integration)
6. **Line Length**: 120 characters for Python code
7. **Enhanced Logging**: Use structured logging with context tracking (see below)

### Enhanced Logging (Issue #218)

RAG Modulo implements an enhanced logging system with structured context tracking, request correlation, and performance monitoring. Based on patterns from IBM mcp-context-forge.

**Key Features**: Dual output formats (JSON/text), context tracking, pipeline stage tracking, performance monitoring, in-memory queryable storage.

**Quick Example**:

```python
from core.enhanced_logging import get_logger
from core.logging_context import log_operation, pipeline_stage_context, PipelineStage

logger = get_logger(__name__)

with log_operation(logger, "search", "collection", coll_id, user_id=user_id):
    with pipeline_stage_context(PipelineStage.QUERY_REWRITING):
        logger.info("Query rewritten", extra={"original": q, "rewritten": rq})
```

**📖 Full Documentation**: [docs/development/logging.md](docs/development/logging.md)

- Configuration reference
- Complete usage examples
- API reference
- Migration guide
- Testing guide
- Troubleshooting

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
# Regenerate Poetry lock file (run from root)
poetry lock

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
- **Secret Management**: `docs/development/secret-management.md` - Comprehensive guide for safe secret handling

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

### Chain of Thought (CoT) Reasoning (GitHub Issues #136, #461)

**What Changed**:

- Added comprehensive CoT reasoning system for enhanced RAG search quality
- Implemented automatic question classification to detect when CoT is beneficial
- Added conversation-aware context building for better reasoning
- Integrated CoT seamlessly into existing search pipeline with fallback mechanisms
- **NEW (Oct 2025)**: Production-grade hardening to prevent reasoning leakage

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

**Production Hardening (Issue #461)**:

Following industry patterns from Anthropic Claude, OpenAI ReAct, LangChain, and LlamaIndex:

1. **Structured Output with XML Tags**: `<thinking>` and `<answer>` tags ensure clean separation
2. **Multi-Layer Parsing**: 5 fallback strategies (XML → JSON → markers → regex → full response)
3. **Quality Scoring**: Confidence assessment (0.0-1.0) with artifact detection
4. **Retry Logic**: Up to 3 attempts with quality threshold validation (default 0.6)
5. **Enhanced Prompts**: System rules + few-shot examples prevent leakage
6. **Comprehensive Telemetry**: Structured logging for quality scores, retries, parsing strategies

**Expected Performance**:

- Success Rate: ~95% (up from ~60%)
- Most queries pass on first attempt (50-80%)
- Retry rate: 20-50% (acceptable for quality improvement)
- Latency: 2.6s (no retry), 5.0s (1 retry)

**Testing**:

- Unit tests: `tests/unit/test_chain_of_thought_service_tdd.py` (31 tests)
- Integration tests: `tests/integration/test_chain_of_thought_integration.py`
- Manual test scripts: `dev_tests/manual/test_cot_*.py` for real-world validation

**Documentation**:

- Full Guide: `docs/features/chain-of-thought-hardening.md` (630 lines)
- Quick Reference: `docs/features/cot-quick-reference.md` (250 lines)
- Implementation Summary: `PRIORITY_1_2_IMPLEMENTATION_SUMMARY.md`
- Original Fix: `ISSUE_461_COT_LEAKAGE_FIX.md`

**Usage**:

- Automatic: Complex questions automatically use CoT with hardening
- Explicit: Set `cot_enabled: true` in `config_metadata`
- Transparent: Set `show_cot_steps: true` to see reasoning steps
- Tunable: Adjust quality threshold (0.4-0.7) and max retries (1-5)

# important-instruction-reminders

Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.

**Testing Commands**:

- Run atomic tests: `make test-atomic` (fastest, ~5 sec)
- Run unit tests: `make test-unit-fast` (~30 sec)
- Run integration tests: `make test-integration` (~2 min, requires `make local-dev-infra`)
- Run e2e tests: `make test-e2e` (~5 min)
- Run all tests: `make test-all` (atomic → unit → integration → e2e)
- Run coverage: `make coverage` (60% minimum)
- Run specific test file: `poetry run pytest tests/unit/services/test_search_service.py -v`
- Run with Poetry directly: `poetry run pytest tests/ -m unit`

**Poetry Commands** (all run from project root):

- Install dependencies: `poetry install --with dev,test`
- Add dependency: `poetry add <package>`
- Update lock file: `poetry lock` (REQUIRED after modifying pyproject.toml)
- Run linting: `poetry run ruff check backend/rag_solution/ tests/`
- Run type checking: `poetry run mypy backend/rag_solution/`
