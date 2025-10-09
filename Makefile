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
.PHONY: help venv clean-venv local-dev-setup local-dev-infra local-dev-backend local-dev-frontend local-dev-all local-dev-stop local-dev-status build-backend build-frontend build-all prod-start prod-stop prod-restart prod-logs prod-status test-atomic test-unit-fast test-integration lint format quick-check security-check clean

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
	@$(MAKE) local-dev-infra
	@echo "$(CYAN)🐍 Starting backend in background...$(NC)"
	@cd backend && $(POETRY) run uvicorn main:app --reload --host 0.0.0.0 --port 8000 > /tmp/rag-backend.log 2>&1 &
	@echo "$(CYAN)⚛️  Starting frontend in background...$(NC)"
	@cd frontend && npm run dev > /tmp/rag-frontend.log 2>&1 &
	@echo "$(GREEN)✅ Local development environment running!$(NC)"
	@echo "$(CYAN)💡 Services:$(NC)"
	@echo "  Frontend:  http://localhost:3000"
	@echo "  Backend:   http://localhost:8000"
	@echo "  MLFlow:    http://localhost:5001"
	@echo "$(CYAN)📋 Logs:$(NC)"
	@echo "  Backend:   tail -f /tmp/rag-backend.log"
	@echo "  Frontend:  tail -f /tmp/rag-frontend.log"
	@echo "$(CYAN)🛑 Stop:$(NC) make local-dev-stop"

local-dev-stop:
	@echo "$(CYAN)🛑 Stopping local development services...$(NC)"
	@pkill -f "uvicorn main:app" || echo "Backend not running"
	@pkill -f "vite" || echo "Frontend not running"
	@$(DOCKER_COMPOSE) -f docker-compose-infra.yml down
	@echo "$(GREEN)✅ Local development stopped$(NC)"

local-dev-status:
	@echo "$(CYAN)📊 Local Development Status$(NC)"
	@echo ""
	@echo "$(CYAN)🐳 Infrastructure:$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose-infra.yml ps
	@echo ""
	@echo "$(CYAN)🐍 Backend:$(NC)"
	@if pgrep -f "uvicorn main:app" > /dev/null; then \
		echo "$(GREEN)✅ Running (PID: $$(pgrep -f 'uvicorn main:app'))$(NC)"; \
	else \
		echo "$(RED)❌ Not running$(NC)"; \
	fi
	@echo ""
	@echo "$(CYAN)⚛️  Frontend:$(NC)"
	@if pgrep -f "vite" > /dev/null; then \
		echo "$(GREEN)✅ Running (PID: $$(pgrep -f 'vite'))$(NC)"; \
	else \
		echo "$(RED)❌ Not running$(NC)"; \
	fi

# ============================================================================
# BUILD TARGETS
# ============================================================================

build-backend:
	@echo "$(CYAN)🔨 Building backend image...$(NC)"
	@cd backend && $(CONTAINER_CLI) build -t $(GHCR_REPO)/backend:$(PROJECT_VERSION) -t $(GHCR_REPO)/backend:latest -f Dockerfile.backend .
	@echo "$(GREEN)✅ Backend image built$(NC)"

build-frontend:
	@echo "$(CYAN)🔨 Building frontend image...$(NC)"
	@cd frontend && $(CONTAINER_CLI) build -t $(GHCR_REPO)/frontend:$(PROJECT_VERSION) -t $(GHCR_REPO)/frontend:latest .
	@echo "$(GREEN)✅ Frontend image built$(NC)"

build-all: build-backend build-frontend
	@echo "$(GREEN)✅ All images built successfully$(NC)"

# ============================================================================
# TESTING
# ============================================================================

test-atomic: venv
	@echo "$(CYAN)⚡ Running atomic tests (no DB, no coverage)...$(NC)"
	@cd backend && $(POETRY) run pytest -c pytest-atomic.ini tests/atomic/ -v
	@echo "$(GREEN)✅ Atomic tests passed$(NC)"

test-unit-fast: venv
	@echo "$(CYAN)🏃 Running unit tests (mocked dependencies)...$(NC)"
	@cd backend && $(POETRY) run pytest -c pytest-atomic.ini tests/unit/ -v
	@echo "$(GREEN)✅ Unit tests passed$(NC)"

test-integration: local-dev-infra
	@echo "$(CYAN)🔗 Running integration tests...$(NC)"
	@$(DOCKER_COMPOSE) run --rm \
		-v $$(pwd)/backend:/app/backend:ro \
		-v $$(pwd)/backend/tests:/app/tests:ro \
		-e TESTING=true \
		test pytest -v tests/integration/
	@echo "$(GREEN)✅ Integration tests passed$(NC)"

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
	@rm -rf .pytest_cache .mypy_cache .ruff_cache backend/htmlcov backend/.coverage
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

clean-all: clean local-dev-stop
	@echo "$(CYAN)🧹 Deep cleaning (containers, volumes, images)...$(NC)"
	@docker system prune -af --volumes
	@echo "$(GREEN)✅ Deep cleanup complete$(NC)"

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
	@echo "  • Run $(GREEN)make quick-check$(NC) before committing"
	@echo "  • Use $(GREEN)make prod-start$(NC) for production-like testing"
	@echo "  • Check $(GREEN)make local-dev-status$(NC) to verify services"
	@echo ""
