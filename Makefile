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
VENV_DIR := .venv
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
.PHONY: help venv clean-venv local-dev-setup local-dev-infra local-dev-backend local-dev-frontend local-dev-all local-dev-stop local-dev-status build-backend build-frontend build-all prod-start prod-stop prod-restart prod-logs prod-status test-atomic test-unit-fast test-integration test-integration-ci test-e2e test-e2e-ci test-e2e-local-parallel test-e2e-ci-parallel test-all test-all-ci lint format quick-check security-check pre-commit-run clean

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
	@$(POETRY) config virtualenvs.in-project true
	@$(POETRY) install --with dev,test
	@echo "$(GREEN)✅ Virtual environment created at .venv$(NC)"
	@echo "$(CYAN)💡 Activate with: source .venv/bin/activate$(NC)"

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
	@if docker ps --format '{{.Names}}' | grep -q 'milvus-etcd'; then \
		echo "$(YELLOW)⚠️  Infrastructure containers already running$(NC)"; \
	else \
		$(DOCKER_COMPOSE) -f docker-compose-infra.yml up -d --remove-orphans || \
		(echo "$(YELLOW)⚠️  Containers exist but stopped, starting them...$(NC)" && \
		 $(DOCKER_COMPOSE) -f docker-compose-infra.yml start); \
	fi
	@echo "$(GREEN)✅ Infrastructure ready$(NC)"
	@echo "$(CYAN)💡 Services:$(NC)"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Milvus:     localhost:19530"
	@echo "  MinIO:      localhost:9001"
	@echo "  MLFlow:     localhost:5001"

local-dev-backend: venv
	@echo "$(CYAN)🐍 Starting backend with hot-reload (uvicorn)...$(NC)"
	@echo "$(YELLOW)⚠️  Make sure infrastructure is running: make local-dev-infra$(NC)"
	@$(POETRY) run uvicorn main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend

local-dev-frontend:
	@echo "$(CYAN)⚛️  Starting frontend with HMR (Vite)...$(NC)"
	@cd frontend && DANGEROUSLY_DISABLE_HOST_CHECK=true npm run dev

local-dev-all: venv
	@echo "$(CYAN)🚀 Starting full local development stack...$(NC)"
	@PROJECT_ROOT=$$(pwd); \
	mkdir -p $$PROJECT_ROOT/.dev-pids $$PROJECT_ROOT/logs; \
	$(MAKE) local-dev-infra; \
	echo "$(CYAN)🐍 Starting backend in background...$(NC)"; \
	$(POETRY) run uvicorn main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend > $$PROJECT_ROOT/logs/backend.log 2>&1 & echo $$! > $$PROJECT_ROOT/.dev-pids/backend.pid; \
	sleep 2; \
	if [ -f $$PROJECT_ROOT/.dev-pids/backend.pid ]; then \
		if kill -0 $$(cat $$PROJECT_ROOT/.dev-pids/backend.pid) 2>/dev/null; then \
			echo "$(GREEN)✅ Backend started (PID: $$(cat $$PROJECT_ROOT/.dev-pids/backend.pid))$(NC)"; \
		else \
			echo "$(RED)❌ Backend failed to start - check logs/backend.log$(NC)"; \
			exit 1; \
		fi; \
	fi; \
	echo "$(CYAN)⚛️  Starting frontend in background...$(NC)"; \
	cd frontend && DANGEROUSLY_DISABLE_HOST_CHECK=true npm run dev > $$PROJECT_ROOT/logs/frontend.log 2>&1 & echo $$! > $$PROJECT_ROOT/.dev-pids/frontend.pid; \
	sleep 2; \
	if [ -f $$PROJECT_ROOT/.dev-pids/frontend.pid ]; then \
		if kill -0 $$(cat $$PROJECT_ROOT/.dev-pids/frontend.pid) 2>/dev/null; then \
			echo "$(GREEN)✅ Frontend started (PID: $$(cat $$PROJECT_ROOT/.dev-pids/frontend.pid))$(NC)"; \
		else \
			echo "$(RED)❌ Frontend failed to start - check logs/frontend.log$(NC)"; \
			exit 1; \
		fi; \
	fi; \
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
	@if [ -f .dev-pids/backend.pid ]; then \
		if kill -0 $$(cat .dev-pids/backend.pid) 2>/dev/null; then \
			kill $$(cat .dev-pids/backend.pid) && echo "$(GREEN)✅ Backend stopped$(NC)"; \
		fi; \
		rm -f .dev-pids/backend.pid; \
	else \
		echo "Backend not running (no PID file)"; \
	fi
	@if [ -f .dev-pids/frontend.pid ]; then \
		if kill -0 $$(cat .dev-pids/frontend.pid) 2>/dev/null; then \
			kill $$(cat .dev-pids/frontend.pid) && echo "$(GREEN)✅ Frontend stopped$(NC)"; \
		fi; \
		rm -f .dev-pids/frontend.pid; \
	else \
		echo "Frontend not running (no PID file)"; \
	fi
	@$(DOCKER_COMPOSE) -f docker-compose-infra.yml down
	@rm -rf .dev-pids
	@echo "$(GREEN)✅ Local development stopped$(NC)"

local-dev-status:
	@echo "$(CYAN)📊 Local Development Status$(NC)"
	@echo ""
	@echo "$(CYAN)🐳 Infrastructure:$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose-infra.yml ps
	@echo ""
	@echo "$(CYAN)🐍 Backend:$(NC)"
	@if [ -f .dev-pids/backend.pid ]; then \
		if kill -0 $$(cat .dev-pids/backend.pid) 2>/dev/null; then \
			echo "$(GREEN)✅ Running (PID: $$(cat .dev-pids/backend.pid))$(NC)"; \
		else \
			echo "$(RED)❌ PID file exists but process is dead$(NC)"; \
			rm -f .dev-pids/backend.pid; \
		fi; \
	else \
		echo "$(RED)❌ Not running$(NC)"; \
	fi
	@echo ""
	@echo "$(CYAN)⚛️  Frontend:$(NC)"
	@if [ -f .dev-pids/frontend.pid ]; then \
		if kill -0 $$(cat .dev-pids/frontend.pid) 2>/dev/null; then \
			echo "$(GREEN)✅ Running (PID: $$(cat .dev-pids/frontend.pid))$(NC)"; \
		else \
			echo "$(RED)❌ PID file exists but process is dead$(NC)"; \
			rm -f .dev-pids/frontend.pid; \
		fi; \
	else \
		echo "$(RED)❌ Not running$(NC)"; \
	fi

# ============================================================================
# BUILD TARGETS
# ============================================================================

build-backend:
	@echo "$(CYAN)🔨 Building backend image...$(NC)"
	@if [ "$(BUILDX_AVAILABLE)" = "yes" ]; then \
		echo "Using Docker BuildKit with buildx..."; \
		$(CONTAINER_CLI) buildx build --load \
			-t $(GHCR_REPO)/backend:$(PROJECT_VERSION) \
			-t $(GHCR_REPO)/backend:latest \
			-f backend/Dockerfile.backend \
			--build-arg BUILDKIT_INLINE_CACHE=1 \
			.; \
	else \
		echo "Using standard Docker build..."; \
		$(CONTAINER_CLI) build \
			-t $(GHCR_REPO)/backend:$(PROJECT_VERSION) \
			-t $(GHCR_REPO)/backend:latest \
			-f backend/Dockerfile.backend \
			.; \
	fi
	@echo "$(GREEN)✅ Backend image built$(NC)"

build-frontend:
	@echo "$(CYAN)🔨 Building frontend image...$(NC)"
	@if [ "$(BUILDX_AVAILABLE)" = "yes" ]; then \
		echo "Using Docker BuildKit with buildx..."; \
		$(CONTAINER_CLI) buildx build --load \
			-t $(GHCR_REPO)/frontend:$(PROJECT_VERSION) \
			-t $(GHCR_REPO)/frontend:latest \
			-f frontend/Dockerfile.frontend \
			frontend/; \
	else \
		echo "Using standard Docker build..."; \
		$(CONTAINER_CLI) build \
			-t $(GHCR_REPO)/frontend:$(PROJECT_VERSION) \
			-t $(GHCR_REPO)/frontend:latest \
			-f frontend/Dockerfile.frontend \
			frontend/; \
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
	@$(POETRY) run pytest -c pytest-atomic.ini tests/unit/schemas/ -v -m atomic
	@echo "$(GREEN)✅ Atomic tests passed$(NC)"

test-unit-fast: venv
	@echo "$(CYAN)🏃 Running unit tests (mocked dependencies)...$(NC)"
	@$(POETRY) run pytest tests/unit/ -v
	@echo "$(GREEN)✅ Unit tests passed$(NC)"

test-integration: venv local-dev-infra
	@echo "$(CYAN)🔗 Running integration tests (with real services)...$(NC)"
	@echo "$(YELLOW)💡 Using shared dev infrastructure (fast, reuses containers)$(NC)"
	@$(POETRY) run pytest tests/integration/ -v -m integration
	@echo "$(GREEN)✅ Integration tests passed$(NC)"

test-integration-ci: venv
	@echo "$(CYAN)🔗 Running integration tests in CI mode (isolated)...$(NC)"
	@echo "$(YELLOW)🏗️  Starting isolated test infrastructure...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose-ci.yml up -d --wait
	@echo "$(CYAN)🧪 Running tests with isolated services...$(NC)"
	@COLLECTIONDB_PORT=5433 MILVUS_PORT=19531 \
		cd backend && poetry run pytest ../tests/integration/ -v -m integration || \
		($(DOCKER_COMPOSE) -f docker-compose-ci.yml down -v && exit 1)
	@echo "$(CYAN)🧹 Cleaning up test infrastructure...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose-ci.yml down -v
	@echo "$(GREEN)✅ CI integration tests passed$(NC)"

test-integration-parallel: venv local-dev-infra
	@echo "$(CYAN)🔗 Running integration tests in parallel...$(NC)"
	@echo "$(YELLOW)⚡ Using pytest-xdist for parallel execution$(NC)"
	@cd backend && poetry run pytest ../tests/integration/ -v -m integration -n auto
	@echo "$(GREEN)✅ Parallel integration tests passed$(NC)"

test-e2e: venv local-dev-infra
	@echo "$(CYAN)🌐 Running end-to-end tests (full system)...$(NC)"
	@echo "$(YELLOW)💡 Using shared dev infrastructure (fast, reuses containers)$(NC)"
	@echo "$(YELLOW)💡 Using TestClient (in-memory, no backend required)$(NC)"
	# Port 5432 is used by the postgres container in docker-compose-infra.yml
	@cd backend && SKIP_AUTH=true COLLECTIONDB_HOST=localhost MILVUS_HOST=localhost \
		env > env_dump.txt && cat env_dump.txt && \
		poetry run pytest ../tests/e2e/ -v -m e2e
	@echo "$(GREEN)✅ E2E tests passed$(NC)"

test-e2e-ci: venv
	@echo "$(CYAN)🌐 Running E2E tests in CI mode (isolated, with backend)...$(NC)"
	@echo "$(YELLOW)🏗️  Starting isolated test infrastructure + backend...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose-e2e.yml up -d --wait
	@echo "$(CYAN)🧪 Running E2E tests with isolated services...$(NC)"
	@SKIP_AUTH=true E2E_MODE=ci COLLECTIONDB_PORT=5434 COLLECTIONDB_HOST=localhost MILVUS_PORT=19532 MILVUS_HOST=milvus-e2e LLM_PROVIDER=watsonx \
		cd backend && poetry run pytest ../tests/e2e/ -v -m e2e || \
		($(DOCKER_COMPOSE) -f docker-compose-e2e.yml down -v && exit 1)
	@echo "$(CYAN)🧹 Cleaning up E2E infrastructure...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose-e2e.yml down -v
	@echo "$(GREEN)✅ CI E2E tests passed$(NC)"

test-e2e-ci-parallel: venv
	@echo "$(CYAN)🌐 Running E2E tests in CI mode (isolated, with backend) in parallel...$(NC)"
	@echo "$(YELLOW)🏗️  Starting isolated test infrastructure + backend...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose-e2e.yml up -d --wait
	@echo "$(CYAN)🧪 Running E2E tests with isolated services in parallel...$(NC)"
	@SKIP_AUTH=true E2E_MODE=ci COLLECTIONDB_PORT=5434 COLLECTIONDB_HOST=localhost MILVUS_PORT=19532 MILVUS_HOST=milvus-e2e LLM_PROVIDER=watsonx \
		cd backend && poetry run pytest ../tests/e2e/ -v -m e2e -n auto || \
		($(DOCKER_COMPOSE) -f docker-compose-e2e.yml down -v && exit 1)
	@echo "$(CYAN)🧹 Cleaning up E2E infrastructure...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose-e2e.yml down -v
	@echo "$(GREEN)✅ CI E2E tests passed in parallel$(NC)"

test-e2e-local-parallel: venv local-dev-infra
	@echo "$(CYAN)🌐 Running E2E tests in parallel (local TestClient)...$(NC)"
	@echo "$(YELLOW)⚡ Using pytest-xdist for parallel execution$(NC)"
	@echo "$(YELLOW)💡 Using TestClient (in-memory, no backend required)$(NC)"
	@SKIP_AUTH=true COLLECTIONDB_HOST=localhost MILVUS_HOST=localhost \
		cd backend && poetry run pytest ../tests/e2e/ -v -m e2e -n auto
	@echo "$(GREEN)✅ Parallel E2E tests passed (local TestClient)$(NC)"

test-all: test-atomic test-unit-fast test-integration test-e2e
	@echo "$(GREEN)✅ All tests passed$(NC)"

test-all-ci: test-atomic test-unit-fast test-integration-ci test-e2e-ci-parallel
	@echo "$(GREEN)✅ All CI tests passed$(NC)"

# ============================================================================
# CODE QUALITY
# ============================================================================

lint: venv
	@echo "$(CYAN)🔍 Running linters...$(NC)"
	@$(POETRY) run ruff check backend --config pyproject.toml
	@$(POETRY) run mypy backend --config-file pyproject.toml --ignore-missing-imports
	@echo "$(GREEN)✅ Linting passed$(NC)"

format: venv
	@echo "$(CYAN)🎨 Formatting code...$(NC)"
	@$(POETRY) run ruff format backend --config pyproject.toml
	@$(POETRY) run ruff check --fix backend --config pyproject.toml
	@echo "$(GREEN)✅ Code formatted$(NC)"

quick-check: venv
	@echo "$(CYAN)⚡ Running quick quality checks...$(NC)"
	@$(POETRY) run ruff format --check backend --config pyproject.toml
	@$(POETRY) run ruff check backend --config pyproject.toml
	@echo "$(GREEN)✅ Quick checks passed$(NC)"

security-check: venv
	@echo "$(CYAN)🔒 Running security checks...$(NC)"
	@$(POETRY) run bandit -r backend/rag_solution/ -ll || echo "$(YELLOW)⚠️  Security issues found$(NC)"
	@$(POETRY) run safety check || echo "$(YELLOW)⚠️  Vulnerabilities found$(NC)"
	@echo "$(GREEN)✅ Security scan complete$(NC)"

pre-commit-run: venv
	@echo "$(CYAN)🎯 Running pre-commit checks...$(NC)"
	@echo "$(CYAN)Step 1/4: Formatting code...$(NC)"
	@$(POETRY) run ruff format backend --config pyproject.toml
	@echo "$(GREEN)✅ Code formatted$(NC)"
	@echo ""
	@echo "$(CYAN)Step 2/4: Running ruff linter...$(NC)"
	@$(POETRY) run ruff check --fix backend --config pyproject.toml
	@echo "$(GREEN)✅ Ruff checks passed$(NC)"
	@echo ""
	@echo "$(CYAN)Step 3/4: Running mypy type checker...$(NC)"
	@$(POETRY) run mypy backend --config-file pyproject.toml --ignore-missing-imports
	@echo "$(GREEN)✅ Type checks passed$(NC)"
	@echo ""
	@echo "$(CYAN)Step 4/4: Running pylint...$(NC)"
	@$(POETRY) run pylint backend/rag_solution/ --rcfile=pyproject.toml || echo "$(YELLOW)⚠️  Pylint warnings found$(NC)"
	@echo ""
	@echo "$(GREEN)✅ Pre-commit checks complete!$(NC)"
	@echo "$(CYAN)💡 Tip: Always run this before committing$(NC)"

coverage: venv
	@echo "$(CYAN)📊 Running tests with coverage...$(NC)"
	@$(POETRY) run pytest tests/unit/ \
		--cov=backend/rag_solution \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=60 \
		-v
	@echo "$(GREEN)✅ Coverage report generated$(NC)"
	@echo "$(CYAN)💡 View report: open htmlcov/index.html$(NC)"

# ============================================================================
# PRODUCTION DEPLOYMENT
# ============================================================================

create-volumes:
	@echo "$(CYAN)📁 Creating volume directories...$(NC)"
	@mkdir -p ./volumes/postgres ./volumes/etcd ./volumes/minio ./volumes/milvus ./volumes/backend
	# Note: chmod 777 is for LOCAL DEVELOPMENT ONLY to avoid permission issues
	# For production deployments, use proper user/group mapping with Docker user namespaces
	# or run containers with specific UIDs/GIDs that match your infrastructure
	@find ./volumes -maxdepth 1 -type d -exec chmod 777 {} \; 2>/dev/null || true
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
# IBM CLOUD CODE ENGINE DEPLOYMENT
# ============================================================================
# Note: These targets require IBM Cloud CLI (ibmcloud) installed on your Mac
# Run these from your Mac workstation, not from the remote server

.PHONY: ce-cleanup ce-deploy ce-deploy-full ce-logs ce-status

ce-cleanup:
	@echo "$(CYAN)🗑️  Cleaning up Code Engine resources...$(NC)"
	@bash scripts/cleanup-code-engine.sh

ce-push:
	@echo "$(CYAN)📤 Pushing images to IBM Container Registry...$(NC)"
	@bash scripts/build-and-push-for-local-testing.sh

ce-deploy:
	@echo "$(CYAN)🚀 Deploying to IBM Cloud Code Engine...$(NC)"
	@bash scripts/deploy-to-code-engine.sh

ce-deploy-full:
	@echo "$(CYAN)🚀 Full deployment pipeline (Build → Test → Push → Deploy)...$(NC)"
	@bash scripts/deploy-end-to-end.sh

ce-deploy-quick:
	@echo "$(CYAN)🚀 Quick deployment (Build → Push → Deploy, skip local test)...$(NC)"
	@bash scripts/deploy-end-to-end.sh --skip-test

ce-logs:
	@echo "$(CYAN)📋 Fetching Code Engine logs...$(NC)"
	@bash scripts/code-engine-logs.sh

ce-status:
	@echo "$(CYAN)📊 Code Engine Status$(NC)"
	@bash -c 'source .secrets 2>/dev/null || true; \
		ibmcloud ce project select --name $${CODE_ENGINE_PROJECT:-rag-modulo} 2>/dev/null && \
		ibmcloud ce app list || echo "Run ce-deploy first"'

# ============================================================================
# UTILITIES
# ============================================================================

clean:
	@echo "$(CYAN)🧹 Cleaning up...$(NC)"
	@rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
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
	@echo "  $(GREEN)make test-e2e$(NC)             End-to-end tests (full system)"
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
