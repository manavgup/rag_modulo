# ============================================================================
# RAG Modulo - Streamlined Makefile
# ============================================================================
# Reduced from 1,703 lines to <500 lines per Issue #348
# Focus: Local containerless development with essential production targets
# ============================================================================

# Include environment variables from .env file if it exists
-include .env
ifneq (,$(wildcard .env))
export $(shell sed 's/=.*//' .env)
endif

# ============================================================================
# VARIABLES
# ============================================================================

# Python environment
VENV_DIR := backend/.venv
PYTHON := python3.12
POETRY := poetry

# Project info
PROJECT_NAME ?= rag-modulo
PYTHON_VERSION ?= 3.12
PROJECT_VERSION ?= 1.0.0
GHCR_REPO ?= ghcr.io/manavgup/rag_modulo

# Docker tools
CONTAINER_CLI := docker
DOCKER_COMPOSE_V2 := $(shell docker compose version >/dev/null 2>&1 && echo "yes" || echo "no")
ifeq ($(DOCKER_COMPOSE_V2),yes)
DOCKER_COMPOSE := docker compose
else
DOCKER_COMPOSE := echo "ERROR: Docker Compose V2 not found. Install docker-compose-plugin" && false
endif

# BuildKit support
BUILDX_AVAILABLE := $(shell docker buildx version >/dev/null 2>&1 && echo "yes" || echo "no")
ifeq ($(BUILDX_AVAILABLE),yes)
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
endif

# Colors for terminal output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m

.DEFAULT_GOAL := help
.PHONY: help venv clean-venv local-dev-setup local-dev-infra local-dev-backend local-dev-frontend local-dev-all local-dev-stop local-dev-status build-backend build-frontend build-all prod-start prod-stop prod-restart prod-logs prod-status test-atomic test-unit-fast test-integration lint format quick-check security-check pre-commit-run clean

# ============================================================================
# VIRTUAL ENVIRONMENT
# ============================================================================

venv: $(VENV_DIR)/bin/activate

$(VENV_DIR)/bin/activate:
	@echo "$(CYAN)🐍 Setting up Python virtual environment with Poetry...$(NC)"
	@if ! command -v poetry >/dev/null 2>&1; then \
		echo "$(RED)❌ Poetry not found. Installing Poetry...$(NC)"; \
		curl -sSL https://install.python-poetry.org | $(PYTHON) -; \
	fi
	@cd backend && $(POETRY) config virtualenvs.in-project true
	@cd backend && $(POETRY) install --with dev,test
	@echo "$(GREEN)✅ Virtual environment created at backend/.venv$(NC)"
	@echo "$(CYAN)💡 Activate with: source backend/.venv/bin/activate$(NC)"

clean-venv:
	@echo "$(CYAN)🧹 Cleaning virtual environment...$(NC)"
	@rm -rf $(VENV_DIR)
	@echo "$(GREEN)✅ Virtual environment cleaned$(NC)"

# ============================================================================
# LOCAL DEVELOPMENT (Containerless - RECOMMENDED)
# ============================================================================
# Fastest iteration: Run Python/React directly on your machine
# Infrastructure (Postgres, Milvus) runs in containers
# ============================================================================

local-dev-setup:
	@echo "$(CYAN)🚀 Setting up local development environment...$(NC)"
	@echo ""
	@echo "$(CYAN)📦 Installing backend dependencies (Poetry)...$(NC)"
	@$(MAKE) venv
	@echo "$(GREEN)✅ Backend dependencies installed$(NC)"
	@echo ""
	@echo "$(CYAN)📦 Installing frontend dependencies (npm)...$(NC)"
	@cd frontend && npm install
	@echo "$(GREEN)✅ Frontend dependencies installed$(NC)"
	@echo ""
	@echo "$(GREEN)✅ Local development setup complete!$(NC)"
	@echo "$(CYAN)💡 Next steps:$(NC)"
	@echo "  1. make local-dev-infra      # Start infrastructure"
	@echo "  2. make local-dev-backend    # Start backend (Terminal 1)"
	@echo "  3. make local-dev-frontend   # Start frontend (Terminal 2)"
	@echo "  OR: make local-dev-all       # Start everything in background"

local-dev-infra:
	@echo "$(CYAN)🏗️  Starting infrastructure (Postgres, Milvus, MinIO, MLFlow)...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose-infra.yml up -d
	@echo "$(GREEN)✅ Infrastructure started$(NC)"
	@echo "$(CYAN)💡 Services:$(NC)"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Milvus:     localhost:19530"
	@echo "  MinIO:      localhost:9001"
	@echo "  MLFlow:     localhost:5001"

local-dev-backend:
	@echo "$(CYAN)🐍 Starting backend with hot-reload (uvicorn)...$(NC)"
	@echo "$(YELLOW)⚠️  Make sure infrastructure is running: make local-dev-infra$(NC)"
	@cd backend && $(POETRY) run uvicorn main:app --reload --host 0.0.0.0 --port 8000

local-dev-frontend:
	@echo "$(CYAN)⚛️  Starting frontend with HMR (Vite)...$(NC)"
	@cd frontend && npm run dev

local-dev-all:
	@echo "$(CYAN)🚀 Starting full local development stack...$(NC)"
	@PROJECT_ROOT=$$(pwd); \
	mkdir -p $$PROJECT_ROOT/logs; \
	$(MAKE) local-dev-infra; \
	echo "$(CYAN)🐍 Starting backend in background...$(NC)"; \
	cd backend && $(POETRY) run uvicorn main:app --reload --host 0.0.0.0 --port 8000 > $$PROJECT_ROOT/logs/backend.log 2>&1 & \
	echo "Waiting for backend to start..."; \
	for i in 1 2 3 4 5 6 7 8 9 10; do \
		if curl -s http://localhost:8000/api/health >/dev/null 2>&1; then \
			echo "$(GREEN)✅ Backend started and responding$(NC)"; \
			break; \
		fi; \
		if [ $$i -eq 10 ]; then \
			echo "$(RED)❌ Backend failed to start - check logs/backend.log$(NC)"; \
			exit 1; \
		fi; \
		sleep 1; \
	done; \
	echo "$(CYAN)⚛️  Starting frontend in background...$(NC)"; \
	cd frontend && npm run dev > $$PROJECT_ROOT/logs/frontend.log 2>&1 & \
	echo "Waiting for frontend to start..."; \
	for i in 1 2 3 4 5 6 7 8 9 10; do \
		if curl -s http://localhost:3000 >/dev/null 2>&1; then \
			echo "$(GREEN)✅ Frontend started and responding$(NC)"; \
			break; \
		fi; \
		if [ $$i -eq 10 ]; then \
			echo "$(YELLOW)⚠️  Frontend may still be starting - check logs/frontend.log$(NC)"; \
			break; \
		fi; \
		sleep 1; \
	done; \
	echo "$(GREEN)✅ Local development environment running!$(NC)"; \
	echo "$(CYAN)💡 Services:$(NC)"; \
	echo "  Frontend:  http://localhost:3000"; \
	echo "  Backend:   http://localhost:8000"; \
	echo "  MLFlow:    http://localhost:5001"; \
	echo "$(CYAN)📋 Logs:$(NC)"; \
	echo "  Backend:   tail -f logs/backend.log"; \
	echo "  Frontend:  tail -f logs/frontend.log"; \
	echo "$(CYAN)🛑 Stop:$(NC) make local-dev-stop"

local-dev-stop:
	@echo "$(CYAN)🛑 Stopping local development services...$(NC)"
	@echo "Stopping backend..."
	@pkill -f "uvicorn main:app" || echo "Backend not running"
	@echo "Stopping frontend..."
	@pkill -f "vite.*frontend" || echo "Frontend not running"
	@$(DOCKER_COMPOSE) -f docker-compose-infra.yml down
	@echo "$(GREEN)✅ Local development stopped$(NC)"

local-dev-status:
	@echo "$(CYAN)📊 Local Development Status$(NC)"
	@echo ""
	@echo "$(CYAN)🐳 Infrastructure:$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose-infra.yml ps
	@echo ""
	@echo "$(CYAN)🐍 Backend:$(NC)"
	@if curl -s http://localhost:8000/api/health >/dev/null 2>&1; then \
		echo "$(GREEN)✅ Running and healthy at http://localhost:8000$(NC)"; \
		pgrep -f "uvicorn main:app" | head -1 | xargs -I {} echo "   PID: {}"; \
	else \
		echo "$(RED)❌ Not responding$(NC)"; \
	fi
	@echo ""
	@echo "$(CYAN)⚛️  Frontend:$(NC)"
	@if curl -s http://localhost:3000 >/dev/null 2>&1; then \
		echo "$(GREEN)✅ Running at http://localhost:3000$(NC)"; \
		pgrep -f "vite.*frontend" | head -1 | xargs -I {} echo "   PID: {}"; \
	else \
		echo "$(RED)❌ Not responding$(NC)"; \
	fi

# ============================================================================
# BUILD TARGETS
# ============================================================================

build-backend:
	@echo "$(CYAN)🔨 Building backend image...$(NC)"
	@if [ "$(BUILDX_AVAILABLE)" = "yes" ]; then \
		echo "Using Docker BuildKit with buildx..."; \
		cd backend && $(CONTAINER_CLI) buildx build --load \
			-t $(GHCR_REPO)/backend:$(PROJECT_VERSION) \
			-t $(GHCR_REPO)/backend:latest \
			-f Dockerfile.backend .; \
	else \
		echo "Using standard Docker build..."; \
		cd backend && $(CONTAINER_CLI) build \
			-t $(GHCR_REPO)/backend:$(PROJECT_VERSION) \
			-t $(GHCR_REPO)/backend:latest \
			-f Dockerfile.backend .; \
	fi
	@echo "$(GREEN)✅ Backend image built$(NC)"

build-frontend:
	@echo "$(CYAN)🔨 Building frontend image...$(NC)"
	@if [ "$(BUILDX_AVAILABLE)" = "yes" ]; then \
		echo "Using Docker BuildKit with buildx..."; \
		cd frontend && $(CONTAINER_CLI) buildx build --load \
			-t $(GHCR_REPO)/frontend:$(PROJECT_VERSION) \
			-t $(GHCR_REPO)/frontend:latest .; \
	else \
		echo "Using standard Docker build..."; \
		cd frontend && $(CONTAINER_CLI) build \
			-t $(GHCR_REPO)/frontend:$(PROJECT_VERSION) \
			-t $(GHCR_REPO)/frontend:latest .; \
	fi
	@echo "$(GREEN)✅ Frontend image built$(NC)"

build-all: build-backend build-frontend
	@echo "$(GREEN)✅ All images built successfully$(NC)"

# ============================================================================
# TESTING
# ============================================================================
# Test Strategy:
# - test-atomic: Fast schema/data structure tests (local, no DB, no coverage)
# - test-unit-fast: Unit tests with mocked dependencies (local, no containers)
# - test-integration: Integration tests with real services (Docker containers)
# - test-all: Runs all test categories in sequence
# ============================================================================

test-atomic: venv
	@echo "$(CYAN)⚡ Running atomic tests (no DB, no coverage)...$(NC)"
	@$(POETRY) -C backend run pytest -c pytest-atomic.ini tests/atomic/ -v
	@echo "$(GREEN)✅ Atomic tests passed$(NC)"

test-unit-fast: venv
	@echo "$(CYAN)🏃 Running unit tests (mocked dependencies)...$(NC)"
	@$(POETRY) -C backend run pytest tests/unit/ -v
	@echo "$(GREEN)✅ Unit tests passed$(NC)"

test-integration: venv
	@echo "$(CYAN)🔗 Running integration tests in isolated environment...$(NC)"
	@echo "$(CYAN)🧹 Cleaning up any previous test environment...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose.test.yml down -v --remove-orphans 2>/dev/null || true
	@echo "$(CYAN)🐳 Starting isolated test infrastructure...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose.test.yml up -d postgres-test etcd-test minio-test milvus-standalone-test createbuckets-test mlflow-test
	@echo "$(CYAN)⏳ Waiting for services to be healthy (max 90s)...$(NC)"
	@timeout=90; elapsed=0; \
	while [ $$elapsed -lt $$timeout ]; do \
		postgres_health=$$(docker inspect --format='{{.State.Health.Status}}' rag-modulo-postgres-test 2>/dev/null || echo "starting"); \
		milvus_health=$$(docker inspect --format='{{.State.Health.Status}}' rag-modulo-milvus-test 2>/dev/null || echo "starting"); \
		if [ "$$postgres_health" = "healthy" ] && [ "$$milvus_health" = "healthy" ]; then \
			echo "$(GREEN)✅ All critical test services healthy$(NC)"; \
			break; \
		fi; \
		echo "  Waiting... (postgres: $$postgres_health, milvus: $$milvus_health) [$$elapsed/$$timeout s]"; \
		sleep 3; \
		elapsed=$$((elapsed + 3)); \
		if [ $$elapsed -ge $$timeout ]; then \
			echo "$(RED)❌ Services failed to become healthy within $$timeout seconds$(NC)"; \
			echo "$(CYAN)📋 Service status:$(NC)"; \
			$(DOCKER_COMPOSE) -f docker-compose.test.yml ps; \
			echo "$(CYAN)📋 Health details:$(NC)"; \
			docker inspect --format='Postgres: {{.State.Health.Status}}' rag-modulo-postgres-test 2>/dev/null || echo "Postgres: not found"; \
			docker inspect --format='Milvus: {{.State.Health.Status}}' rag-modulo-milvus-test 2>/dev/null || echo "Milvus: not found"; \
			echo "$(CYAN)📋 Recent logs:$(NC)"; \
			$(DOCKER_COMPOSE) -f docker-compose.test.yml logs --tail=50; \
			$(DOCKER_COMPOSE) -f docker-compose.test.yml down -v --remove-orphans; \
			exit 1; \
		fi; \
	done
	@echo "$(CYAN)🧪 Running integration tests...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose.test.yml run --rm test-runner || \
		(echo "$(RED)❌ Integration tests failed$(NC)" && \
		 echo "$(CYAN)📋 Test logs:$(NC)" && \
		 $(DOCKER_COMPOSE) -f docker-compose.test.yml logs test-runner && \
		 $(DOCKER_COMPOSE) -f docker-compose.test.yml down -v --remove-orphans && \
		 exit 1)
	@echo "$(GREEN)✅ Integration tests passed$(NC)"
	@echo "$(CYAN)🧹 Cleaning up test environment...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose.test.yml down -v --remove-orphans
	@echo "$(GREEN)✅ Test environment cleaned$(NC)"

test-all: test-atomic test-unit-fast test-integration
	@echo "$(GREEN)✅ All tests passed$(NC)"

# ============================================================================
# CODE QUALITY
# ============================================================================

lint: venv
	@echo "$(CYAN)🔍 Running linters...$(NC)"
	@cd backend && $(POETRY) run ruff check . --config pyproject.toml
	@cd backend && $(POETRY) run mypy . --config-file pyproject.toml --ignore-missing-imports
	@echo "$(GREEN)✅ Linting passed$(NC)"

format: venv
	@echo "$(CYAN)🎨 Formatting code...$(NC)"
	@cd backend && $(POETRY) run ruff format . --config pyproject.toml
	@cd backend && $(POETRY) run ruff check --fix . --config pyproject.toml
	@echo "$(GREEN)✅ Code formatted$(NC)"

quick-check: venv
	@echo "$(CYAN)⚡ Running quick quality checks...$(NC)"
	@cd backend && $(POETRY) run ruff format --check . --config pyproject.toml
	@cd backend && $(POETRY) run ruff check . --config pyproject.toml
	@echo "$(GREEN)✅ Quick checks passed$(NC)"

security-check: venv
	@echo "$(CYAN)🔒 Running security checks...$(NC)"
	@cd backend && $(POETRY) run bandit -r rag_solution/ -ll || echo "$(YELLOW)⚠️  Security issues found$(NC)"
	@cd backend && $(POETRY) run safety check || echo "$(YELLOW)⚠️  Vulnerabilities found$(NC)"
	@echo "$(GREEN)✅ Security scan complete$(NC)"

pre-commit-run: venv
	@echo "$(CYAN)🎯 Running pre-commit checks (matches CI/CD pipelines)...$(NC)"
	@echo "$(CYAN)💡 Only checking tracked files (respects .gitignore)$(NC)"
	@echo ""
	@echo "$(CYAN)Step 1/10: Security - Detecting secrets and sensitive data...$(NC)"
	@echo "  🔐 Checking for hardcoded secrets with Gitleaks (staged files only - FAST)..."
	@if command -v gitleaks >/dev/null 2>&1; then \
		echo "$(CYAN)  ℹ️  Scanning staged files only (~1 second)...$(NC)"; \
		GITLEAKS_OUTPUT=$$(gitleaks protect --config .gitleaks.toml --no-banner --staged 2>&1); \
		if echo "$$GITLEAKS_OUTPUT" | grep -q "leaks found: [1-9]"; then \
			echo "$(RED)  ❌ Secrets detected in staged files:$(NC)"; \
			echo "$$GITLEAKS_OUTPUT"; \
			exit 1; \
		else \
			echo "$(GREEN)  ✅ No secrets in staged files$(NC)"; \
		fi; \
	else \
		echo "$(YELLOW)  ⚠️  gitleaks not installed. Install: brew install gitleaks$(NC)"; \
	fi
	@echo "  🔑 Checking for private keys in source code (tracked files only)..."
	@if git ls-files '*.py' '*.js' '*.ts' '*.java' '*.go' '*.rb' | xargs grep -l "BEGIN.*PRIVATE KEY" 2>/dev/null | grep -v ".gitleaks.toml" | grep -v ".github/workflows"; then \
		echo "$(RED)  ❌ Private keys detected in source code! Remove before committing.$(NC)"; \
		exit 1; \
	else \
		echo "$(GREEN)  ✅ No private keys in source code$(NC)"; \
	fi
	@echo "  🤖 Checking for AI-generated artifacts (tracked files only)..."
	@if git ls-files '*.py' '*.md' '*.js' '*.ts' | xargs grep -nE "(as an ai language model|i am an ai developed by|source=chatgpt\.com|\[oaicite:\?\?\d+\]|:contentReference)" 2>/dev/null | grep -v "Makefile"; then \
		echo "$(RED)  ❌ AI-generated artifacts detected! Clean before committing.$(NC)"; \
	else \
		echo "$(GREEN)  ✅ No AI artifacts found$(NC)"; \
	fi
	@echo ""
	@echo "$(CYAN)Step 2/10: File hygiene - Text quality checks...$(NC)"
	@echo "  🧹 Checking for trailing whitespace (tracked files only)..."
	@if git ls-files '*.py' '*.js' '*.ts' '*.tsx' '*.jsx' '*.md' | xargs grep -n "[[:space:]]$$" 2>/dev/null | head -5; then \
		echo "$(YELLOW)  ⚠️  Trailing whitespace found (showing first 5)$(NC)"; \
	else \
		echo "$(GREEN)  ✅ No trailing whitespace$(NC)"; \
	fi
	@echo "  📝 Checking for merge conflict markers (tracked files only)..."
	@if git ls-files '*.py' '*.js' '*.ts' '*.tsx' '*.jsx' '*.md' | xargs grep -n "^<<<<<<< \|^=======$\|^>>>>>>> " 2>/dev/null; then \
		echo "$(RED)  ❌ Merge conflict markers detected!$(NC)"; \
	else \
		echo "$(GREEN)  ✅ No merge conflicts$(NC)"; \
	fi
	@echo "  📏 Checking for large files (tracked files only)..."
	@if git ls-files | xargs ls -lh 2>/dev/null | awk '$$5 ~ /^[0-9]+M$$/ && $$5+0 > 5 {print}' | head -3; then \
		echo "$(YELLOW)  ⚠️  Large files detected (>5MB)$(NC)"; \
	else \
		echo "$(GREEN)  ✅ No large files$(NC)"; \
	fi
	@echo ""
	@echo "$(CYAN)Step 3/10: Formatting backend code...$(NC)"
	@cd backend && $(POETRY) run ruff format . --config pyproject.toml
	@echo "$(GREEN)✅ Backend code formatted$(NC)"
	@echo ""
	@echo "$(CYAN)Step 4/10: Running ruff linter...$(NC)"
	@cd backend && $(POETRY) run ruff check --fix . --config pyproject.toml
	@echo "$(GREEN)✅ Ruff checks passed$(NC)"
	@echo ""
	@echo "$(CYAN)Step 5/10: Running mypy type checker...$(NC)"
	@cd backend && $(POETRY) run mypy . --config-file pyproject.toml --ignore-missing-imports || echo "$(YELLOW)⚠️  Type check issues found (non-blocking)$(NC)"
	@echo ""
	@echo "$(CYAN)Step 6/10: Running pylint...$(NC)"
	@cd backend && $(POETRY) run pylint rag_solution/ --rcfile=pyproject.toml || echo "$(YELLOW)⚠️  Pylint warnings found (non-blocking)$(NC)"
	@echo ""
	@echo "$(CYAN)Step 7/10: Linting configuration files (YAML/JSON/TOML)...$(NC)"
	@if command -v yamllint >/dev/null 2>&1; then \
		yamllint .github/ 2>/dev/null || echo "$(YELLOW)⚠️  YAML linting skipped$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  yamllint not installed, skipping YAML checks$(NC)"; \
	fi
	@if command -v jq >/dev/null 2>&1; then \
		find . -name '*.json' -not -path './node_modules/*' -not -path './.git/*' -not -path './frontend/node_modules/*' -exec jq empty {} \; 2>/dev/null || echo "$(YELLOW)⚠️  JSON validation issues found$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  jq not installed, skipping JSON checks$(NC)"; \
	fi
	@python3 -c "import toml; toml.load(open('backend/pyproject.toml'))" 2>/dev/null && echo "$(GREEN)✅ TOML files valid$(NC)" || echo "$(YELLOW)⚠️  TOML validation failed$(NC)"
	@echo ""
	@echo "$(CYAN)Step 8/10: Running frontend ESLint...$(NC)"
	@if [ -d "frontend/node_modules" ]; then \
		cd frontend && npm run lint && echo "$(GREEN)✅ Frontend lint passed$(NC)" || echo "$(YELLOW)⚠️  Frontend lint issues found$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  Frontend dependencies not installed. Run: make local-dev-setup$(NC)"; \
	fi
	@echo ""
	@echo "$(CYAN)Step 9/10: Checking Python code quality...$(NC)"
	@echo "  🐍 Checking for debug statements (tracked files only)..."
	@if git ls-files 'backend/rag_solution/**/*.py' | xargs grep -n "import pdb\|breakpoint()\|import ipdb" 2>/dev/null; then \
		echo "$(YELLOW)  ⚠️  Debug statements found$(NC)"; \
	else \
		echo "$(GREEN)  ✅ No debug statements$(NC)"; \
	fi
	@echo "  🐍 Checking Python AST validity (tracked files only)..."
	@if git ls-files 'backend/rag_solution/**/*.py' | head -5 | xargs -I {} python3 -c "import ast; ast.parse(open('{}').read())" 2>/dev/null; then \
		echo "$(GREEN)  ✅ Python syntax valid (sampled 5 files)$(NC)"; \
	else \
		echo "$(YELLOW)  ⚠️  Syntax validation failed or no files found$(NC)"; \
	fi
	@echo ""
	@echo "$(CYAN)Step 10/10: Running fast unit tests...$(NC)"
	@cd backend && $(POETRY) run pytest tests/ -m "unit or atomic" --maxfail=3 -q && echo "$(GREEN)✅ Unit tests passed$(NC)" || echo "$(RED)❌ Unit tests failed - fix before committing$(NC)"
	@echo ""
	@echo "$(GREEN)✅ Pre-commit checks complete!$(NC)"
	@echo "$(CYAN)💡 These checks match what CI/CD will run on your PR$(NC)"
	@echo "$(CYAN)📋 Summary:$(NC)"
	@echo "  🔐 Security scanning (secrets, keys, AI artifacts)"
	@echo "  🧹 File hygiene (whitespace, conflicts, large files)"
	@echo "  🎨 Code formatting (Ruff, ESLint)"
	@echo "  🔍 Linting (Ruff, Pylint, YAML, JSON, TOML)"
	@echo "  🏷️  Type checking (MyPy)"
	@echo "  🐍 Python quality (AST, debug statements)"
	@echo "  🧪 Unit tests"

coverage: venv
	@echo "$(CYAN)📊 Running tests with coverage...$(NC)"
	@cd backend && $(POETRY) run pytest tests/ \
		--cov=rag_solution \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=60 \
		-v
	@echo "$(GREEN)✅ Coverage report generated$(NC)"
	@echo "$(CYAN)💡 View report: open backend/htmlcov/index.html$(NC)"

# ============================================================================
# PRODUCTION DEPLOYMENT
# ============================================================================

create-volumes:
	@echo "$(CYAN)📁 Creating volume directories...$(NC)"
	@mkdir -p ./volumes/{postgres,etcd,minio,milvus,backend}
	@chmod -R 777 ./volumes
	@echo "$(GREEN)✅ Volumes created$(NC)"

prod-start: create-volumes
	@echo "$(CYAN)🚀 Starting production environment...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose.production.yml up -d
	@echo "$(GREEN)✅ Production environment started$(NC)"
	@echo "$(CYAN)💡 Services:$(NC)"
	@echo "  Frontend:  http://localhost:3000"
	@echo "  Backend:   http://localhost:8000"
	@echo "  MLFlow:    http://localhost:5001"

prod-stop:
	@echo "$(CYAN)🛑 Stopping production environment...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose.production.yml down
	@echo "$(GREEN)✅ Production stopped$(NC)"

prod-restart: prod-stop prod-start

prod-logs:
	@$(DOCKER_COMPOSE) -f docker-compose.production.yml logs -f

prod-status:
	@echo "$(CYAN)📊 Production Status$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose.production.yml ps

# ============================================================================
# UTILITIES
# ============================================================================

clean:
	@echo "$(CYAN)🧹 Cleaning up...$(NC)"
	@rm -rf .pytest_cache .mypy_cache .ruff_cache backend/htmlcov backend/.coverage .dev-pids
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

clean-all: clean local-dev-stop
	@echo "$(CYAN)🧹 Deep cleaning (containers, volumes, images)...$(NC)"
	@echo "$(RED)⚠️  WARNING: This will remove ALL Docker containers, volumes, and images!$(NC)"
	@echo "$(YELLOW)This is a DESTRUCTIVE operation that cannot be undone.$(NC)"
	@read -p "Are you sure you want to continue? (yes/no): " confirm && \
		if [ "$$confirm" = "yes" ]; then \
			docker system prune -af --volumes && \
			echo "$(GREEN)✅ Deep cleanup complete$(NC)"; \
		else \
			echo "$(YELLOW)Cleanup cancelled$(NC)"; \
			exit 1; \
		fi

logs:
	@$(DOCKER_COMPOSE) -f docker-compose-infra.yml logs -f

check-docker:
	@echo "$(CYAN)🔍 Checking Docker requirements...$(NC)"
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "$(RED)❌ Docker not installed$(NC)"; \
		exit 1; \
	fi
	@if [ "$(DOCKER_COMPOSE_V2)" != "yes" ]; then \
		echo "$(RED)❌ Docker Compose V2 not found$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ Docker ready$(NC)"

# ============================================================================
# HELP
# ============================================================================

help:
	@echo ""
	@echo "$(CYAN)╔══════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(CYAN)║         RAG Modulo - Streamlined Development Guide          ║$(NC)"
	@echo "$(CYAN)╚══════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(CYAN)🚀 Quick Start (Local Development - RECOMMENDED):$(NC)"
	@echo "  $(GREEN)make local-dev-setup$(NC)      Install dependencies (backend + frontend)"
	@echo "  $(GREEN)make local-dev-infra$(NC)      Start infrastructure (Postgres, Milvus, etc.)"
	@echo "  $(GREEN)make local-dev-backend$(NC)    Start backend with hot-reload (Terminal 1)"
	@echo "  $(GREEN)make local-dev-frontend$(NC)   Start frontend with HMR (Terminal 2)"
	@echo "  $(GREEN)make local-dev-all$(NC)        Start everything in background"
	@echo "  $(GREEN)make local-dev-status$(NC)     Check status of local services"
	@echo "  $(GREEN)make local-dev-stop$(NC)       Stop all local services"
	@echo ""
	@echo "$(CYAN)🐍 Virtual Environment:$(NC)"
	@echo "  $(GREEN)make venv$(NC)                 Create Python virtual environment"
	@echo "  $(GREEN)make clean-venv$(NC)           Remove virtual environment"
	@echo ""
	@echo "$(CYAN)🧪 Testing:$(NC)"
	@echo "  $(GREEN)make test-atomic$(NC)          Fast atomic tests (no DB)"
	@echo "  $(GREEN)make test-unit-fast$(NC)       Unit tests (mocked dependencies)"
	@echo "  $(GREEN)make test-integration$(NC)     Integration tests (requires infra)"
	@echo "  $(GREEN)make test-all$(NC)             Run all tests"
	@echo "  $(GREEN)make coverage$(NC)             Generate coverage report"
	@echo ""
	@echo "$(CYAN)🎨 Code Quality:$(NC)"
	@echo "  $(GREEN)make pre-commit-run$(NC)       Run all pre-commit checks (format + lint + type)"
	@echo "  $(GREEN)make quick-check$(NC)          Fast lint + format check"
	@echo "  $(GREEN)make lint$(NC)                 Run all linters (ruff + mypy)"
	@echo "  $(GREEN)make format$(NC)               Auto-format code"
	@echo "  $(GREEN)make security-check$(NC)       Security scanning (bandit + safety)"
	@echo ""
	@echo "$(CYAN)🐳 Production Deployment:$(NC)"
	@echo "  $(GREEN)make build-backend$(NC)        Build backend Docker image"
	@echo "  $(GREEN)make build-frontend$(NC)       Build frontend Docker image"
	@echo "  $(GREEN)make build-all$(NC)            Build all images"
	@echo "  $(GREEN)make prod-start$(NC)           Start production environment"
	@echo "  $(GREEN)make prod-stop$(NC)            Stop production environment"
	@echo "  $(GREEN)make prod-restart$(NC)         Restart production"
	@echo "  $(GREEN)make prod-status$(NC)          Show production status"
	@echo "  $(GREEN)make prod-logs$(NC)            View production logs"
	@echo ""
	@echo "$(CYAN)🛠️  Utilities:$(NC)"
	@echo "  $(GREEN)make clean$(NC)                Clean cache files"
	@echo "  $(GREEN)make clean-all$(NC)            Deep clean (containers + volumes)"
	@echo "  $(GREEN)make check-docker$(NC)         Verify Docker installation"
	@echo "  $(GREEN)make logs$(NC)                 View infrastructure logs"
	@echo ""
	@echo "$(CYAN)📚 Documentation:$(NC)"
	@echo "  Full docs: https://manavgup.github.io/rag_modulo"
	@echo "  API docs:  http://localhost:8000/docs (when backend running)"
	@echo ""
	@echo "$(CYAN)💡 Pro Tips:$(NC)"
	@echo "  • Use local development for fastest iteration (no container rebuilds)"
	@echo "  • Run $(GREEN)make pre-commit-run$(NC) before committing (format + lint + type)"
	@echo "  • Use $(GREEN)make prod-start$(NC) for production-like testing"
	@echo "  • Check $(GREEN)make local-dev-status$(NC) to verify services"
	@echo ""
