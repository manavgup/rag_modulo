# Include environment variables from .env file if it exists
-include .env
# Only export .env variables if the file exists
ifneq (,$(wildcard .env))
export $(shell sed 's/=.*//' .env)
endif

# Set PYTHONPATH
export PYTHONPATH=$(pwd):$(pwd)/vectordbs:$(pwd)/rag_solution

# Virtual environment setup
VENVS_DIR := backend/.venv
PYTHON := $(VENVS_DIR)/bin/python
UV := $(shell which uv 2>/dev/null || echo "uv")
POETRY := poetry

# Directories
SOURCE_DIR := ./backend/rag_solution
TEST_DIR := ./tests
PROJECT_DIRS := $(SOURCE_DIR) $(TEST_DIR)

# Project info
PROJECT_NAME ?= rag-modulo
PYTHON_VERSION ?= 3.12
PROJECT_VERSION ?= 1.0.0
GHCR_REPO ?= ghcr.io/manavgup/rag_modulo

# Tools
CONTAINER_CLI := docker
DOCKER_COMPOSE := docker compose

# Check Docker version and available build methods
DOCKER_VERSION := $(shell docker version --format '{{.Client.Version}}' 2>/dev/null)
BUILDX_AVAILABLE := $(shell docker buildx version >/dev/null 2>&1 && echo "yes" || echo "no")

# Only enable BuildKit if buildx is available
ifeq ($(BUILDX_AVAILABLE),yes)
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1
else
export DOCKER_BUILDKIT=0
export COMPOSE_DOCKER_CLI_BUILD=0
endif

# Set a default value for VECTOR_DB if not already set
VECTOR_DB ?= milvus

.DEFAULT_GOAL := help

.PHONY: init-env sync-frontend-deps build-frontend build-backend build-tests build-all build-frontend-local build-backend-local build-tests-local build-all-local test tests api-tests unit-tests integration-tests performance-tests service-tests pipeline-tests all-tests run-app run-backend run-frontend run-services stop-containers restart-backend restart-frontend restart-app restart-backend-safe clean create-volumes logs info help pull-ghcr-images venv clean-venv format-imports check-imports quick-check security-check coverage coverage-report quality fix-all check-deps check-deps-tree export-requirements docs-generate docs-serve search-test search-batch search-components uv-install uv-sync uv-export validate-env health-check build-optimize build-performance

# Init
init-env:
	@touch .env
	@echo "PROJECT_NAME=${PROJECT_NAME}" >> .env
	@echo "PYTHON_VERSION=${PYTHON_VERSION}" >> .env
	@echo "VECTOR_DB=${VECTOR_DB}" >> .env

# Virtual environment management
venv: $(VENVS_DIR)/bin/activate

$(VENVS_DIR)/bin/activate:
	@echo "Setting up Python virtual environment..."
	@cd backend && $(POETRY) config virtualenvs.in-project true
	@cd backend && $(POETRY) install --with dev
	@echo "Virtual environment ready."

clean-venv:
	@echo "Cleaning virtual environment..."
	@rm -rf $(VENVS_DIR)
	@echo "Virtual environment cleaned."

sync-frontend-deps:
	@echo "Syncing frontend dependencies..."
	@cd webui && npm install
	@echo "Frontend dependencies synced."

# Install Docker buildx to eliminate deprecation warnings
install-buildx:
	@echo "Installing Docker buildx plugin..."
	@if command -v brew >/dev/null 2>&1; then \
		echo "Installing via Homebrew..."; \
		brew install docker-buildx; \
	else \
		echo "Please install Docker Desktop or Docker buildx manually:"; \
		echo "  - Docker Desktop: https://www.docker.com/products/docker-desktop"; \
		echo "  - Or manual install: https://github.com/docker/buildx#installing"; \
	fi
	@echo "After installation, buildx will be available and deprecation warnings will disappear."

# Build and Push - GHCR-first strategy
build-frontend:
	@echo "Building and pushing frontend image..."
	@if [ "$(BUILDX_AVAILABLE)" = "yes" ]; then \
		echo "Using Docker BuildKit with buildx..."; \
		cd webui && $(CONTAINER_CLI) buildx build -t ${GHCR_REPO}/frontend:${PROJECT_VERSION} -t ${GHCR_REPO}/frontend:latest -f Dockerfile.frontend . --push; \
	else \
		echo "Using standard Docker build (buildx not available)..."; \
		cd webui && $(CONTAINER_CLI) build -t ${GHCR_REPO}/frontend:${PROJECT_VERSION} -t ${GHCR_REPO}/frontend:latest -f Dockerfile.frontend .; \
		$(CONTAINER_CLI) push ${GHCR_REPO}/frontend:${PROJECT_VERSION}; \
		$(CONTAINER_CLI) push ${GHCR_REPO}/frontend:latest; \
	fi

build-backend:
	@echo "Building and pushing backend image..."
	@if [ "$(BUILDX_AVAILABLE)" = "yes" ]; then \
		echo "Using Docker BuildKit with buildx..."; \
		cd backend && $(CONTAINER_CLI) buildx build -t ${GHCR_REPO}/backend:${PROJECT_VERSION} -t ${GHCR_REPO}/backend:latest -f Dockerfile.backend . --push; \
	else \
		echo "Using standard Docker build (buildx not available)..."; \
		cd backend && $(CONTAINER_CLI) build -t ${GHCR_REPO}/backend:${PROJECT_VERSION} -t ${GHCR_REPO}/backend:latest -f Dockerfile.backend .; \
		$(CONTAINER_CLI) push ${GHCR_REPO}/backend:${PROJECT_VERSION}; \
		$(CONTAINER_CLI) push ${GHCR_REPO}/backend:latest; \
	fi

build-tests:
	@echo "Building test image..."
	@if [ "$(BUILDX_AVAILABLE)" = "yes" ]; then \
		echo "Using Docker BuildKit with buildx..."; \
		cd backend && $(CONTAINER_CLI) buildx build -t ${GHCR_REPO}/backend:test-${PROJECT_VERSION} -f Dockerfile.test . --push; \
	else \
		echo "Using standard Docker build (buildx not available)..."; \
		cd backend && $(CONTAINER_CLI) build -t ${GHCR_REPO}/backend:test-${PROJECT_VERSION} -f Dockerfile.test .; \
		$(CONTAINER_CLI) push ${GHCR_REPO}/backend:test-${PROJECT_VERSION}; \
	fi

build-all: build-frontend build-backend build-tests

# Local build targets (without push to GHCR)
build-frontend-local:
	@echo "Building frontend image locally..."
	@if [ "$(BUILDX_AVAILABLE)" = "yes" ]; then \
		echo "Using Docker BuildKit with buildx..."; \
		cd webui && $(CONTAINER_CLI) buildx build --load -t ${GHCR_REPO}/frontend:${PROJECT_VERSION} -t ${GHCR_REPO}/frontend:latest -f Dockerfile.frontend .; \
	else \
		echo "Using standard Docker build (buildx not available)..."; \
		cd webui && $(CONTAINER_CLI) build -t ${GHCR_REPO}/frontend:${PROJECT_VERSION} -t ${GHCR_REPO}/frontend:latest -f Dockerfile.frontend .; \
	fi

build-backend-local:
	@echo "Building backend image locally..."
	@if [ "$(BUILDX_AVAILABLE)" = "yes" ]; then \
		echo "Using Docker BuildKit with buildx..."; \
		cd backend && $(CONTAINER_CLI) buildx build --load -t ${GHCR_REPO}/backend:${PROJECT_VERSION} -t ${GHCR_REPO}/backend:latest -f Dockerfile.backend .; \
	else \
		echo "Using standard Docker build (buildx not available)..."; \
		cd backend && $(CONTAINER_CLI) build -t ${GHCR_REPO}/backend:${PROJECT_VERSION} -t ${GHCR_REPO}/backend:latest -f Dockerfile.backend .; \
	fi

build-tests-local:
	@echo "Building test image locally..."
	@if [ "$(BUILDX_AVAILABLE)" = "yes" ]; then \
		echo "Using Docker BuildKit with buildx..."; \
		cd backend && $(CONTAINER_CLI) buildx build --load -t ${GHCR_REPO}/backend:test-${PROJECT_VERSION} -f Dockerfile.test .; \
	else \
		echo "Using standard Docker build (buildx not available)..."; \
		cd backend && $(CONTAINER_CLI) build -t ${GHCR_REPO}/backend:test-${PROJECT_VERSION} -f Dockerfile.test .; \
	fi

build-all-local: build-frontend-local build-backend-local build-tests-local

# Pull latest images from GHCR
pull-ghcr-images:
	@echo "Pulling latest images from GitHub Container Registry..."
	$(CONTAINER_CLI) pull ${GHCR_REPO}/frontend:latest
	$(CONTAINER_CLI) pull ${GHCR_REPO}/backend:latest
	@echo "Images pulled successfully. Use 'make run-ghcr' to start with GHCR images."

# Configure for GHCR images (production)
use-ghcr-images:
	@echo "Configuring environment for GHCR images..."
	@echo "BACKEND_IMAGE=${GHCR_REPO}/backend:latest" > .env.local
	@echo "FRONTEND_IMAGE=${GHCR_REPO}/frontend:latest" >> .env.local
	@echo "TEST_IMAGE=${GHCR_REPO}/backend:test-${PROJECT_VERSION}" >> .env.local
	@echo "GHCR image configuration saved to .env.local"

# Helper function to check if containers are healthy

# Environment and health validation
validate-env:
	@echo "Validating environment configuration..."
	@./scripts/validate-env.sh

health-check:
	@echo "Running comprehensive health check..."
	@./scripts/health-check.sh

# Build optimization and testing
build-optimize:
	@echo "Running build optimization tests..."
	@echo "Checking build context sizes..."
	@echo "Frontend build context:"
	@cd webui && du -sh . 2>/dev/null | head -1 || echo "Could not determine size"
	@echo "Backend build context:"
	@cd backend && du -sh . 2>/dev/null | head -1 || echo "Could not determine size"
	@echo ""
	@echo "Testing Docker BuildKit..."
	@if [ "$(BUILDX_AVAILABLE)" = "yes" ]; then \
		echo "✓ BuildKit available with buildx"; \
	else \
		echo "⚠ BuildKit disabled - buildx not available, using standard builds"; \
	fi
	@echo ""
	@echo "Checking .dockerignore files..."
	@[ -f "webui/.dockerignore" ] && echo "✓ Frontend .dockerignore exists" || echo "✗ Frontend .dockerignore missing"
	@[ -f "backend/.dockerignore" ] && echo "✓ Backend .dockerignore exists" || echo "✗ Backend .dockerignore missing"
	@echo ""
	@echo "Testing guide available at: docs/TESTING_PHASES.md"

# Performance testing
build-performance:
	@echo "Running comprehensive build performance tests..."
	@./scripts/build-performance.sh
check_containers:
	@echo "Checking if required containers are running and healthy..."
	@if [ -z "$$(docker compose ps -q backend)" ] || \
		[ -z "$$(docker compose ps -q postgres)" ] || \
		[ -z "$$(docker compose ps -q milvus-standalone)" ] || \
		[ -z "$$(docker compose ps -q mlflow-server)" ]; then \
		echo "Some containers are not running. Starting services..."; \
		$(MAKE) run-backend; \
		echo "Waiting for containers to be healthy..."; \
		sleep 10; \
	else \
		echo "All required containers are running."; \
	fi

# Create test report directories
create-test-dirs:
	@mkdir -p ./test-reports/{unit,integration,performance,coverage}
	@chmod -R 777 ./test-reports

# Test targets with proper volume mounting and reporting
test: check_containers create-test-dirs build-tests
	@if [ -z "$(testfile)" ]; then \
		echo "Error: Please provide testfile. Example: make test testfile=tests/api/test_auth.py"; \
		exit 1; \
	else \
		echo "Running test: $(testfile)"; \
		$(DOCKER_COMPOSE) run --rm \
			-v $$(pwd)/backend:/app/backend:ro \
			-v $$(pwd)/tests:/app/tests:ro \
			-v $$(pwd)/test-reports:/app/test-reports \
			-e TESTING=true \
			-e CONTAINER_ENV=false \
			test pytest -v $(testfile) || \
		{ \
			echo "Test $(testfile) failed"; \
			if [ "$(cleanup)" = "true" ]; then \
				echo "Cleaning up containers (cleanup=true)..."; \
				$(MAKE) stop-containers; \
			fi; \
			exit 1; \
		}; \
		if [ "$(cleanup)" = "true" ]; then \
			echo "Tests completed. Cleaning up containers (cleanup=true)..."; \
			$(MAKE) stop-containers; \
		fi \
	fi

# Clean test run that stops containers afterward
test-clean: cleanup=true
test-clean: test

# Helper to just run tests if containers are already running
test-only:
	@if [ -z "$(testfile)" ]; then \
		echo "Error: Please provide testfile. Example: make test-only testfile=tests/api/test_auth.py"; \
		exit 1; \
	else \
		echo "Running test: $(testfile)"; \
		$(DOCKER_COMPOSE) run --rm \
			-v $$(pwd)/backend:/app/backend:ro \
			-v $$(pwd)/tests:/app/tests:ro \
			-e TESTING=true \
			-e CONTAINER_ENV=false \
			test pytest -v -s /app/$(testfile); \
	fi

# Specialized test targets
unit-tests: run-backend create-test-dirs
	$(DOCKER_COMPOSE) run --rm \
		-v $$(pwd)/backend:/app/backend:ro \
		-v $$(pwd)/tests:/app/tests:ro \
		-v $$(pwd)/test-reports:/app/test-reports \
		-e TESTING=true \
		-e CONTAINER_ENV=false \
		test pytest -v -s -m "unit" \
		--html=/app/test-reports/unit/report.html \
		--self-contained-html \
		--junitxml=/app/test-reports/unit/junit.xml \
		--cov=backend/rag_solution \
		--cov-report=html:/app/test-reports/coverage/html \
		--cov-report=xml:/app/test-reports/coverage/coverage.xml \
		|| { echo "Unit tests failed"; $(MAKE) stop-containers; exit 1; }

integration-tests: run-backend create-test-dirs
	$(DOCKER_COMPOSE) run --rm \
		-v $$(pwd)/backend:/app/backend:ro \
		-v $$(pwd)/tests:/app/tests:ro \
		-v $$(pwd)/test-reports:/app/test-reports \
		-e TESTING=true \
		-e CONTAINER_ENV=false \
		test pytest -v -s -m "integration" \
		--html=/app/test-reports/integration/report.html \
		--self-contained-html \
		--junitxml=/app/test-reports/integration/junit.xml \
		|| { echo "Integration tests failed"; $(MAKE) stop-containers; exit 1; }

performance-tests: run-backend create-test-dirs
	$(DOCKER_COMPOSE) run --rm \
		-v $$(pwd)/backend:/app/backend:ro \
		-v $$(pwd)/tests:/app/tests:ro \
		-v $$(pwd)/test-reports:/app/test-reports \
		-e TESTING=true \
		-e CONTAINER_ENV=false \
		-e PERF_TEST_DURATION=300 \
		-e PERF_TEST_CONCURRENT=10 \
		-e PERF_TEST_TOTAL=100 \
		-e PERF_TEST_MEMORY_LIMIT=80 \
		-e PERF_REPORT_DIR=/app/test-reports/performance \
		-e PERF_REPORT_FORMAT=html,json \
		-e PERF_METRICS_ENABLED=true \
		test pytest -v -s -m "performance" \
		--html=/app/test-reports/performance/report.html \
		--self-contained-html \
		--junitxml=/app/test-reports/performance/junit.xml \
		|| { echo "Performance tests failed"; $(MAKE) stop-containers; exit 1; }

service-tests: run-backend create-test-dirs
	$(DOCKER_COMPOSE) run --rm \
		-v $$(pwd)/backend:/app/backend:ro \
		-v $$(pwd)/tests:/app/tests:ro \
		-v $$(pwd)/test-reports:/app/test-reports \
		-e TESTING=true \
		-e CONTAINER_ENV=false \
		test pytest -v -s -m "service" \
		--html=/app/test-reports/service/report.html \
		--self-contained-html \
		--junitxml=/app/test-reports/service/junit.xml \
		|| { echo "Service tests failed"; $(MAKE) stop-containers; exit 1; }

pipeline-tests: run-backend create-test-dirs
	$(DOCKER_COMPOSE) run --rm \
		-v $$(pwd)/backend:/app/backend:ro \
		-v $$(pwd)/test-reports:/app/test-reports \
		-e TESTING=true \
		-e CONTAINER_ENV=false \
		test pytest -v -s -m "pipeline" \
		--html=/app/test-reports/pipeline/report.html \
		--self-contained-html \
		--junitxml=/app/test-reports/pipeline/junit.xml \
		|| { echo "Pipeline tests failed"; $(MAKE) stop-containers; exit 1; }

api-tests: run-backend create-test-dirs
	$(DOCKER_COMPOSE) run --rm \
		-v $$(pwd)/backend:/app/backend:ro \
		-v $$(pwd)/tests:/app/tests:ro \
		-v $$(pwd)/test-reports:/app/test-reports \
		-e TESTING=true \
		-e CONTAINER_ENV=false \
		test pytest -v -s -m "api and not (chromadb or elasticsearch or pinecone or weaviate)" \
		--html=/app/test-reports/api/report.html \
		--self-contained-html \
		--junitxml=/app/test-reports/api/junit.xml \
		|| { echo "API Tests failed"; $(MAKE) stop-containers; exit 1; }

tests: validate-env run-backend create-test-dirs
	$(DOCKER_COMPOSE) run --rm \
		-v $$(pwd)/backend:/app/backend:ro \
		-v $$(pwd)/tests:/app/tests:ro \
		-v $$(pwd)/test-reports:/app/test-reports \
		-e TESTING=true \
		-e CONTAINER_ENV=false \
		test pytest -v -s -m "not (chromadb or elasticsearch or pinecone or weaviate)" \
		--html=/app/test-reports/report.html \
		--self-contained-html \
		--junitxml=/app/test-reports/junit.xml \
		--cov=backend/rag_solution \
		--cov-report=html:/app/test-reports/coverage/html \
		--cov-report=xml:/app/test-reports/coverage/coverage.xml \
		|| { echo "Tests failed"; $(MAKE) stop-containers; exit 1; }

# NEW: Layered Testing Targets (Issue #187)
test-atomic: venv
	@echo "⚡ Running atomic tests (no coverage, no database, no reports)..."
	cd backend && poetry run pytest -c pytest-atomic.ini tests/atomic/ -v

test-unit-fast: venv
	@echo "🏃 Running unit tests (mocked dependencies)..."
	cd backend && poetry run pytest -c pytest-atomic.ini tests/unit/ -v

test-integration: run-backend create-test-dirs
	@echo "🔗 Running integration tests (testcontainers)..."
	$(DOCKER_COMPOSE) run --rm \
		-v $$(pwd)/backend:/app/backend:ro \
		-v $$(pwd)/tests:/app/tests:ro \
		-v $$(pwd)/test-reports:/app/test-reports \
		-e TESTING=true \
		-e CONTAINER_ENV=false \
		test pytest -v backend/tests/integration/

run-backend-e2e: run-services
	@echo "Starting backend with E2E configuration (auth disabled)..."
	SKIP_AUTH=true TESTING=true DEVELOPMENT_MODE=true $(DOCKER_COMPOSE) up -d backend
	@echo "Backend is now running in E2E mode."

test-e2e: run-backend-e2e create-test-dirs
	@echo "🌐 Running E2E tests (full stack)..."
	@echo "Waiting for backend to be ready..."
	@sleep 10  # Give backend time to initialize
	$(DOCKER_COMPOSE) run --rm \
		-v $$(pwd)/backend:/app/backend:ro \
		-v $$(pwd)/tests:/app/tests:ro \
		-v $$(pwd)/test-reports:/app/test-reports \
		-e TESTING=true \
		-e CONTAINER_ENV=false \
		test pytest -v backend/tests/e2e/

# Combined test targets
test-fast: test-atomic test-unit-fast
test-all: test-atomic test-unit-fast test-integration test-e2e

# Code quality validation for tests
test-lint: venv
	@echo "🔍 Running code quality checks on test files..."
	cd backend && poetry run ruff check tests/ --fix
	cd backend && poetry run mypy tests/
	cd backend && poetry run pylint tests/

# Pre-commit validation
test-validate: test-lint test-atomic
	@echo "✅ All tests pass quality checks and run successfully"

# Combined test targets with quality validation
test-fast-validated: test-lint test-atomic test-unit-fast
test-all-validated: test-lint test-atomic test-unit-fast test-integration test-e2e

# Run - Local Development (default - uses local builds)
run-app: build-all-local run-backend run-frontend
	@echo "All application containers are now running with local images."

run-backend: run-services
	@echo "Starting backend..."
	$(DOCKER_COMPOSE) up -d backend
	@echo "Backend is now running."

run-frontend: run-services
	@echo "Starting frontend..."
	$(DOCKER_COMPOSE) up -d frontend
	@echo "Frontend is now running."

# Run - GHCR Images (for production-like testing)
run-ghcr: pull-ghcr-images use-ghcr-images
	@echo "Starting services with GHCR images..."
	$(DOCKER_COMPOSE) --env-file .env.local up -d
	@echo "All application containers are now running with GHCR images."

run-services: create-volumes
	@echo "Starting services:"
	$(DOCKER_COMPOSE) up -d postgres minio milvus-etcd milvus-standalone createbuckets mlflow-server || \
	{ \
		echo "Failed to infra services"; \
		unhealthy_containers=$$($(CONTAINER_CLI) ps -f health=unhealthy -q); \
		if [ -n "$$unhealthy_containers" ]; then \
			echo "Logs from unhealthy containers:"; \
			for container in $$unhealthy_containers; do \
				echo "Container ID: $$container"; \
				$(CONTAINER_CLI) logs $$container; \
			done; \
		else \
			echo "No unhealthy containers found, checking for failed containers..."; \
					failed_containers=$$($(CONTAINER_CLI) ps -f status=exited -q); \
		if [ -n "$$failed_containers" ]; then \
			echo "No failed containers found, showing logs for all services."; \
				$(DOCKER_COMPOSE) logs; \
			fi; \
		fi; \
		exit 1; \
	}

# Stop / clean
stop-containers:
	@echo "Stopping containers..."
	$(DOCKER_COMPOSE) down -v

# Restart services with proper dependency handling
restart-backend:
	@echo "Restarting backend service..."
	$(DOCKER_COMPOSE) restart backend
	@echo "Waiting for backend to be healthy..."
	@docker-compose exec -T backend python healthcheck.py 2>/dev/null || (echo "Waiting for backend to be ready..." && sleep 10)
	@echo "Backend restarted successfully!"

restart-frontend:
	@echo "Restarting frontend service..."
	$(DOCKER_COMPOSE) restart frontend
	@echo "Waiting for frontend to be ready..."
	@sleep 5
	@echo "Frontend restarted successfully!"

restart-app: restart-backend restart-frontend
	@echo "Application restarted successfully!"

# Restart only backend but also reload frontend nginx to reconnect
restart-backend-safe:
	@echo "Restarting backend service with frontend reload..."
	$(DOCKER_COMPOSE) restart backend
	@echo "Waiting for backend to be healthy..."
	@docker-compose exec -T backend python healthcheck.py 2>/dev/null || (echo "Waiting for backend to be ready..." && sleep 10)
	@echo "Reloading frontend nginx configuration..."
	@docker-compose exec -T frontend nginx -s reload 2>/dev/null || echo "Frontend reload not needed"
	@echo "Backend restarted and frontend reconnected successfully!"

clean: stop-containers
	@echo "Cleaning up existing containers and volumes..."
	-@$(CONTAINER_CLI) pod rm -f $$($(CONTAINER_CLI) pod ls -q) || true
	-@$(CONTAINER_CLI) rm -f $$($(CONTAINER_CLI) ps -aq) || true
	-@$(CONTAINER_CLI) volume prune -f || true
	-@$(CONTAINER_CLI) container prune -f || true
	rm -rf .pytest_cache .mypy_cache data volumes my_chroma_data tests

# Service / reusable targets
create-volumes:
	@echo "Creating volume directories with correct permissions..."
	@mkdir -p ./volumes/postgres ./volumes/etcd ./volumes/minio ./volumes/milvus ./volumes/backend
	@chmod -R 777 ./volumes
	@echo "Volume directories created and permissions set."

logs:
	$(DOCKER_COMPOSE) logs -f

info:
	@echo "Project name: ${PROJECT_NAME}"
	@echo "Project version: ${PROJECT_VERSION}"
	@echo "Python version: ${PYTHON_VERSION}"
	@echo "Vector DB: ${VECTOR_DB}"
	@echo "GHCR repository: ${GHCR_REPO}"

# Colors for better output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Local CI targets (mirror GitHub Actions)

## Linting targets
lint: lint-ruff lint-mypy lint-pylint
	@echo "$(GREEN)✅ All linting checks completed$(NC)"

lint-ruff: venv
	@echo "$(CYAN)🔍 Running Ruff linter...$(NC)"
	@cd backend && $(POETRY) run ruff check rag_solution/ tests/ --line-length=200 --config pyproject.toml
	@echo "$(GREEN)✅ Ruff checks passed$(NC)"

lint-mypy: venv
	@echo "$(CYAN)🔎 Running Mypy type checker...$(NC)"
	@cd backend && $(POETRY) run mypy . --disable-error-code=misc --disable-error-code=unused-ignore --no-strict-optional

lint-pylint: venv
	@echo "$(CYAN)🔍 Running Pylint checks...$(NC)"
	@pylint --rcfile=.pylintrc backend/rag_solution tests || true
	@cd backend && $(POETRY) run mypy . --disable-error-code=misc --disable-error-code=unused-ignore --no-strict-optional
	@echo "$(GREEN)✅ Mypy type checks passed$(NC)"

## NEW: Strict type checking target
lint-mypy-strict:
	@echo "$(CYAN)🔎 Running strict Mypy type checker...$(NC)"
	cd backend && poetry run mypy . \
		--strict \
		--warn-redundant-casts \
		--warn-unused-ignores \
		--explicit-package-bases
	@echo "$(GREEN)✅ Strict Mypy checks passed$(NC)"

lint-docstrings:
	@echo "$(CYAN)📝 Checking docstring coverage...$(NC)"
	cd backend && poetry run interrogate --fail-under=50 rag_solution/ -v || echo "$(YELLOW)⚠️  Docstring coverage needs improvement$(NC)"
	cd backend && poetry run pydocstyle rag_solution/ || echo "$(YELLOW)⚠️  Some docstring issues found$(NC)"
	@echo "$(GREEN)✅ Docstring checks completed$(NC)"

## NEW: Strict docstring checking target
lint-docstrings-strict:
	@echo "$(CYAN)📝 Checking docstring coverage (50% threshold)...$(NC)"
	cd backend && poetry run interrogate rag_solution/ -v
	cd backend && poetry run pydocstyle rag_solution/
	@echo "$(GREEN)✅ Strict docstring checks passed$(NC)"

## Strangler Pattern targets for gradual linting adoption
lint-progress:
	@echo "$(CYAN)📊 Checking linting progress (strangler pattern)...$(NC)"
	@python scripts/check_linting_progress.py

lint-migrate-file:
	@echo "$(CYAN)🔄 Migrating file to full linting compliance...$(NC)"
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)❌ Usage: make lint-migrate-file FILE=path/to/file.py$(NC)"; \
		exit 1; \
	fi
	@python scripts/migrate_file_to_compliance.py "$(FILE)"

lint-strangler-status:
	@echo "$(CYAN)📈 Showing strangler pattern status...$(NC)"
	@python scripts/show_strangler_status.py

init-strangler:
	@echo "$(CYAN)🔧 Initializing strangler pattern...$(NC)"
	@./scripts/init-strangler-pattern.sh

## NEW: Doctest execution target
test-doctest:
	@echo "$(CYAN)📖 Running doctest examples...$(NC)"
	cd backend && poetry run pytest --doctest-modules rag_solution/ -v
	@echo "$(GREEN)✅ Doctest examples passed$(NC)"

## Import sorting targets
format-imports: venv
	@echo "$(CYAN)🔧 Sorting imports...$(NC)"
	@cd backend && $(POETRY) run ruff check --select I --fix rag_solution/ tests/ --config pyproject.toml
	@echo "$(GREEN)✅ Import sorting completed$(NC)"

check-imports: venv
	@echo "$(CYAN)🔍 Checking import order...$(NC)"
	@cd backend && $(POETRY) run ruff check --select I rag_solution/ tests/ --config pyproject.toml
	@echo "$(GREEN)✅ Import check completed$(NC)"

## Formatting targets
format: format-ruff format-imports
	@echo "$(GREEN)✅ All formatting completed$(NC)"

format-ruff: venv
	@echo "$(CYAN)🔧 Running Ruff formatter...$(NC)"
	@cd backend && $(POETRY) run ruff format rag_solution/ tests/ --line-length=200 --config pyproject.toml
	@cd backend && $(POETRY) run ruff check --fix rag_solution/ tests/ --line-length=200 --config pyproject.toml
	@echo "$(GREEN)✅ Ruff formatting completed$(NC)"

format-check: venv
	@echo "$(CYAN)🔍 Checking code formatting...$(NC)"
	@cd backend && $(POETRY) run ruff format --check rag_solution/ tests/ --line-length=200 --config pyproject.toml
	@cd backend && $(POETRY) run ruff check rag_solution/ tests/ --line-length=200 --config pyproject.toml
	@echo "$(GREEN)✅ Format check completed$(NC)"

## Pre-commit targets
pre-commit-run:
	@echo "$(CYAN)🔧 Running pre-commit hooks on all files...$(NC)"
	@cd backend && $(POETRY) run pre-commit run --all-files
	@echo "$(GREEN)✅ Pre-commit run completed$(NC)"

pre-commit-update:
	@echo "$(CYAN)⬆️  Updating pre-commit hooks...$(NC)"
	@cd backend && $(POETRY) run pre-commit autoupdate
	@echo "$(GREEN)✅ Pre-commit hooks updated$(NC)"

setup-pre-commit:
	@echo "$(CYAN)📦 Setting up pre-commit hooks...$(NC)"
	pip install pre-commit
	pre-commit install
	@echo "$(GREEN)✅ Pre-commit hooks installed$(NC)"

## Unit tests
unit-tests-local:
	@echo "$(CYAN)🧪 Running unit tests locally...$(NC)"
	cd backend && poetry run pytest tests/ -m unit --maxfail=5 -v
	@echo "$(GREEN)✅ Unit tests completed$(NC)"

## NEW: Composite quality targets
check-fast: format-check lint-ruff
	@echo "$(GREEN)✅ Fast quality checks completed$(NC)"

check-quality: format lint lint-mypy-strict
	@echo "$(GREEN)✅ Comprehensive quality checks completed$(NC)"

check-style: format-check
	@echo "$(GREEN)✅ Style checks completed$(NC)"

strict: check-quality lint-docstrings-strict test-doctest
	@echo "$(GREEN)✅ Strictest quality requirements met$(NC)"

## NEW: Code analysis target
analyze:
	@echo "$(CYAN)📊 Running code analysis...$(NC)"
	cd backend && poetry run ruff check . --statistics || true
	cd backend && poetry run mypy rag_solution/ --show-error-codes --show-error-context || true
	@echo "$(GREEN)✅ Code analysis completed$(NC)"

## Security scanning targets
security-check: venv
	@echo "$(CYAN)🔒 Running security checks...$(NC)"
	@cd backend && $(POETRY) run bandit -r rag_solution/ -ll --format json -o bandit-report.json || true
	@cd backend && $(POETRY) run bandit -r rag_solution/ -ll || echo "$(YELLOW)⚠️  Some security issues found$(NC)"
	@cd backend && $(POETRY) run safety check --output json > safety-report.json || true
	@cd backend && $(POETRY) run safety check || echo "$(YELLOW)⚠️  Some dependency vulnerabilities found$(NC)"
	@echo "$(GREEN)✅ Security checks completed$(NC)"

## Coverage targets
coverage: venv
	@echo "$(CYAN)📈 Running tests with coverage...$(NC)"
	@cd backend && $(POETRY) run pytest tests/ \
		--cov=rag_solution \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=60 \
		--maxfail=10 \
		-x || echo "$(YELLOW)⚠️  Some tests failed, but coverage report was generated$(NC)"
	@echo "$(GREEN)✅ Coverage report generated (60% threshold)$(NC)"

coverage-report: coverage
	@echo "$(CYAN)📊 Opening coverage report...$(NC)"
	@if command -v open >/dev/null 2>&1; then \
		open backend/htmlcov/index.html; \
	elif command -v xdg-open >/dev/null 2>&1; then \
		xdg-open backend/htmlcov/index.html; \
	else \
		echo "Coverage report available at: backend/htmlcov/index.html"; \
	fi

## Enhanced quality targets
quality: format-check check-imports lint security-check coverage
	@echo "$(GREEN)✅ All quality checks passed$(NC)"

fix-all: format-ruff format-imports
	@echo "$(GREEN)✅ All auto-fixes applied$(NC)"

## Dependency management targets
check-deps: venv
	@echo "$(CYAN)📦 Checking for outdated dependencies...$(NC)"
	@cd backend && $(POETRY) show --outdated || echo "$(GREEN)✅ All dependencies are up to date$(NC)"
	@echo "$(GREEN)✅ Dependency check completed$(NC)"

check-deps-tree: venv
	@echo "$(CYAN)🌳 Showing dependency tree...$(NC)"
	@cd backend && $(POETRY) show --tree
	@echo "$(GREEN)✅ Dependency tree displayed$(NC)"

export-requirements: venv
	@echo "$(CYAN)📝 Exporting requirements...$(NC)"
	@cd backend && $(POETRY) show --only=main --no-ansi > requirements.txt || echo "$(YELLOW)⚠️ Main requirements exported with Poetry show$(NC)"
	@cd backend && $(POETRY) show --with=dev --no-ansi > requirements-dev.txt || echo "$(YELLOW)⚠️ Dev requirements exported with Poetry show$(NC)"
	@cd backend && $(POETRY) show --with=test --no-ansi > requirements-test.txt || echo "$(YELLOW)⚠️ Test requirements exported with Poetry show$(NC)"
	@echo "$(GREEN)✅ Requirements exported to backend/ directory$(NC)"
	@echo "$(CYAN)💡 Note: For pip-compatible format, consider installing poetry-plugin-export$(NC)"

## Documentation generation targets
docs-generate: venv
	@echo "$(CYAN)📚 Generating documentation...$(NC)"
	@cd backend && $(POETRY) run python -m pydoc -w rag_solution || echo "$(YELLOW)⚠️ pydoc generation completed with warnings$(NC)"
	@echo "$(GREEN)✅ Documentation generated in backend/ directory$(NC)"

docs-serve: venv
	@echo "$(CYAN)🌐 Serving documentation locally...$(NC)"
	@cd backend && $(POETRY) run python -m http.server 8080 || echo "$(YELLOW)⚠️ Documentation server stopped$(NC)"
	@echo "$(GREEN)✅ Documentation served at http://localhost:8080$(NC)"

## RAG Search Testing
search-test: venv
	@echo "$(CYAN)🔍 Testing RAG search functionality...$(NC)"
	@if [ -z "$(QUERY)" ]; then \
		echo "$(RED)Error: QUERY parameter required. Usage: make search-test QUERY='your question'$(NC)"; \
		exit 1; \
	fi
	@if [ -z "$(COLLECTION_ID)" ]; then \
		echo "$(RED)Error: COLLECTION_ID parameter required$(NC)"; \
		exit 1; \
	fi
	@if [ -z "$(USER_ID)" ]; then \
		echo "$(RED)Error: USER_ID parameter required$(NC)"; \
		exit 1; \
	fi
	@cd backend && $(POETRY) run python -m cli.search_test test \
		--query "$(QUERY)" \
		--collection-id "$(COLLECTION_ID)" \
		--user-id "$(USER_ID)" \
		$(if $(PIPELINE_ID),--pipeline-id "$(PIPELINE_ID)") \
		$(if $(VERBOSE),--verbose) \
		$(if $(OUTPUT),--output "$(OUTPUT)")
	@echo "$(GREEN)✅ Search test completed$(NC)"

search-batch: venv
	@echo "$(CYAN)📊 Running batch search quality tests...$(NC)"
	@if [ -z "$(COLLECTION_ID)" ]; then \
		echo "$(RED)Error: COLLECTION_ID parameter required$(NC)"; \
		exit 1; \
	fi
	@if [ -z "$(USER_ID)" ]; then \
		echo "$(RED)Error: USER_ID parameter required$(NC)"; \
		exit 1; \
	fi
	@cd backend && $(POETRY) run python -m cli.search_test batch-test \
		--queries-file "${QUERIES_FILE:-test_data/search_queries.json}" \
		--collection-id "$(COLLECTION_ID)" \
		--user-id "$(USER_ID)" \
		$(if $(PIPELINE_ID),--pipeline-id "$(PIPELINE_ID)") \
		$(if $(OUTPUT),--output "$(OUTPUT)")
	@echo "$(GREEN)✅ Batch testing completed$(NC)"

search-components: venv
	@echo "$(CYAN)🔧 Testing individual RAG components...$(NC)"
	@if [ -z "$(QUERY)" ]; then \
		echo "$(RED)Error: QUERY parameter required. Usage: make search-components QUERY='your question'$(NC)"; \
		exit 1; \
	fi
	@if [ -z "$(COLLECTION_ID)" ]; then \
		echo "$(RED)Error: COLLECTION_ID parameter required$(NC)"; \
		exit 1; \
	fi
	@cd backend && $(POETRY) run python -m cli.search_test test-components \
		--query "$(QUERY)" \
		--collection-id "$(COLLECTION_ID)" \
		--strategy "${STRATEGY:-simple}"
	@echo "$(GREEN)✅ Component testing completed$(NC)"

## UV alternative support (experimental)
uv-install:
	@echo "$(CYAN)⚡ Installing UV (experimental)...$(NC)"
	@if ! command -v uv >/dev/null 2>&1; then \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
		echo "$(GREEN)✅ UV installed$(NC)"; \
	else \
		echo "$(GREEN)✅ UV already installed$(NC)"; \
	fi

uv-sync: uv-install
	@echo "$(CYAN)⚡ Syncing dependencies with UV (experimental)...$(NC)"
	@cd backend && uv sync || echo "$(YELLOW)⚠️ UV sync completed with warnings$(NC)"
	@echo "$(GREEN)✅ UV sync completed$(NC)"

uv-export: uv-install
	@echo "$(CYAN)⚡ Exporting requirements with UV (experimental)...$(NC)"
	@cd backend && uv export --format requirements-txt --output-file requirements-uv.txt || echo "$(YELLOW)⚠️ UV export completed with warnings$(NC)"
	@echo "$(GREEN)✅ UV requirements exported to backend/requirements-uv.txt$(NC)"

## Quick check target for developer workflow
quick-check: format-check check-imports lint-ruff
	@echo "$(GREEN)✅ Quick checks passed$(NC)"

## Combined targets
ci-local: format-check lint unit-tests-local
	@echo "$(GREEN)✅ Local CI checks completed successfully!$(NC)"

ci-fix: format lint
	@echo "$(GREEN)✅ Code formatting and linting fixes applied!$(NC)"

validate-ci:
	@echo "$(CYAN)🔍 Validating CI workflows...$(NC)"
	./scripts/validate-ci.sh

## Environment Setup
setup-env:
	@echo "$(CYAN)🚀 Setting up RAG Modulo environment...$(NC)"
	@if [ ! -f scripts/setup_env.py ]; then \
		echo "❌ Setup script not found. Make sure you're in the project root."; \
		exit 1; \
	fi
	@python scripts/setup_env.py

env-help:
	@echo "$(CYAN)🔐 Environment Setup Help$(NC)"
	@echo ""
	@echo "Quick Start:"
	@echo "  1. make setup-env     # Interactive setup"
	@echo "  2. Edit .env file     # Fill in your API keys"
	@echo "  3. make validate-env  # Verify setup"
	@echo "  4. make tests         # Test everything works"
	@echo ""
	@echo "Required Credentials:"
	@echo "  🔑 WATSONX_APIKEY     - Get from IBM Cloud > Watson AI"
	@echo "  🔑 OPENAI_API_KEY     - Get from https://platform.openai.com/api-keys"
	@echo "  🔑 ANTHROPIC_API_KEY  - Get from https://console.anthropic.com/settings/keys"
	@echo ""
	@echo "Troubleshooting:"
	@echo "  - Container failures? Check MinIO credentials (MINIO_ROOT_USER/PASSWORD)"
	@echo "  - Missing .env? Run 'make setup-env'"
	@echo "  - Wrong values? Compare with .env.example"

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "$(CYAN)🚀 Quick Commands:$(NC)"
	@echo "  ci-local      \t\tRun full local CI (format-check + lint + tests)"
	@echo "  ci-fix        \t\tAuto-fix formatting and linting issues"
	@echo "  pre-commit-run\t\tRun all pre-commit hooks"
	@echo ""
	@echo "$(CYAN)🔍 Linting Targets:$(NC)"
	@echo "  lint          \t\tRun all linters (ruff + mypy)"
	@echo "  lint-ruff     \t\tRun Ruff linter"
	@echo "  lint-mypy     \t\tRun MyPy type checker"
	@echo "  lint-mypy-strict\t\tRun strict MyPy type checker"
	@echo "  lint-docstrings\t\tCheck docstring coverage (50% threshold)"
	@echo "  lint-docstrings-strict\tCheck docstring coverage (50% threshold)"
	@echo "  lint-progress     \tShow strangler pattern linting progress"
	@echo "  lint-migrate-file \tMigrate file to full linting compliance (FILE=path)"
	@echo "  lint-strangler-status\tShow strangler pattern status"
	@echo "  init-strangler    \tInitialize strangler pattern for gradual linting"
	@echo ""
	@echo "$(CYAN)🎨 Formatting Targets:$(NC)"
	@echo "  format        \t\tAuto-format code and sort imports"
	@echo "  format-check  \t\tCheck formatting without changes"
	@echo "  format-ruff   \t\tRun Ruff formatter with fixes"
	@echo "  format-imports\t\tSort imports with ruff"
	@echo "  check-imports \t\tCheck import order without fixes"
	@echo ""
	@echo "$(CYAN)🧪 Testing Targets:$(NC)"
	@echo "  unit-tests-local  \tRun unit tests locally"
	@echo "  test-doctest      \tRun doctest examples"
	@echo ""
	@echo "$(CYAN)🎯 Quality Targets:$(NC)"
	@echo "  check-fast        \tQuick essential checks (format-check + lint-ruff)"
	@echo "  quick-check       \tQuick checks for development (format-check + check-imports + lint-ruff)"
	@echo "  security-check    \tRun security scanning (bandit + safety)"
	@echo "  coverage          \tRun tests with coverage (60% threshold)"
	@echo "  coverage-report   \tGenerate and open coverage report"
	@echo "  quality           \tComprehensive quality checks (format + lint + security + coverage)"
	@echo "  fix-all           \tFix all auto-fixable issues"
	@echo "  check-quality     \tComprehensive quality with formatting"
	@echo "  check-style       \tStyle checks without fixes"
	@echo "  strict            \tStrictest quality requirements"
	@echo "  analyze           \tCode analysis and metrics"
	@echo ""
	@echo "$(CYAN)📦 Dependency Targets:$(NC)"
	@echo "  check-deps        \tCheck for outdated dependencies"
	@echo "  check-deps-tree   \tShow dependency tree"
	@echo "  export-requirements\tExport requirements to txt files"
	@echo ""
	@echo "$(CYAN)📚 Documentation Targets:$(NC)"
	@echo "  docs-generate     \tGenerate API documentation"
	@echo "  docs-serve        \tServe documentation locally (http://localhost:8080)"
	@echo ""
	@echo "$(CYAN)⚡ UV Experimental Targets:$(NC)"
	@echo "  uv-install        \tInstall UV package manager"
	@echo "  uv-sync           \tSync dependencies with UV"
	@echo "  uv-export         \tExport requirements with UV"
	@echo ""
	@echo "$(CYAN)🔍 RAG Search Testing:$(NC)"
	@echo "  search-test       \tTest single search query (QUERY, COLLECTION_ID, USER_ID required)"
	@echo "  search-batch      \tRun batch search quality tests"
	@echo "  search-components \tTest individual RAG pipeline components"
	@echo ""
	@echo "$(CYAN)🛠️ Setup Targets:$(NC)"
	@echo "  venv              \tSet up Python virtual environment"
	@echo "  clean-venv        \tClean Python virtual environment"
	@echo "  setup-pre-commit  \tInstall pre-commit hooks"
	@echo "  pre-commit-update \tUpdate pre-commit hooks to latest"
	@echo "  validate-ci   \t\tValidate CI workflows with act"
	@echo ""
	@echo "$(CYAN)📦 Container Targets:$(NC)"
	@echo "  init-env      		Initialize .env file with default values"
	@echo "  build-frontend  	Build frontend code/container"
	@echo "  build-backend   	Build backend code/container"
	@echo "  build-tests   		Build test code/container"
	@echo "  build-all   		Build frontend/backend/test code/container"
	@echo "  pull-ghcr-images   Pull latest images from GitHub Container Registry"
	@echo "  use-ghcr-images    Configure environment for GHCR images"
	@echo "  test          		Run specific test with coverage and reports"
	@echo "  test-only     		Run specific test without coverage (if containers running)"
	@echo "  test-clean    		Run specific test and cleanup containers afterward"
	@echo "  unit-tests    		Run unit tests with coverage and reports"
	@echo "  integration-tests   Run integration tests with reports"
	@echo "  performance-tests   Run performance tests with metrics"
	@echo "  service-tests       Run service-specific tests"
	@echo "  pipeline-tests      Run pipeline-related tests"
	@echo "  api-tests      	Run API tests with reports"
	@echo "  tests          	Run all tests with coverage and reports"
	@echo "  run-app       		Run both backend and frontend using local images"
	@echo "  run-backend   		Run backend using local images"
	@echo "  run-frontend  		Run frontend using local images"
	@echo "  run-ghcr      		Run both backend and frontend using GHCR images"
	@echo "  run-services  		Run services using Docker Compose"
	@echo "  stop-containers  	Stop all containers using Docker Compose"
	@echo "  restart-backend  	Restart backend service with health check"
	@echo "  restart-frontend 	Restart frontend service with wait"
	@echo "  restart-app      	Restart both backend and frontend services"
	@echo "  restart-backend-safe Restart backend and reload frontend nginx"
	@echo "  clean         		Clean up Docker Compose volumes and cache"
	@echo "  create-volumes     Create folders for container volumes"
	@echo "  create-test-dirs   Create test report directories"
	@echo "  logs          		View logs of running containers"
	@echo "  info          		Display project information"
	@echo "  help          		Display this help message"
	@echo ""
	@echo "Examples:"
	@echo "  make test testfile=tests/api/test_auth.py"
	@echo "  make test testfile=tests/api/test_auth.py::test_login"
	@echo "  make test-only testfile=tests/core/test_database.py"
	@echo "  make pull-ghcr-images  # Pull latest images from GHCR"
	@echo "  make check-fast        # Quick quality check"
	@echo "  make strict            # Strictest quality requirements"
	@echo ""
	@echo "$(CYAN)🔐 Environment Setup:$(NC)"
	@echo "  setup-env     	Interactive environment setup"
	@echo "  validate-env  	Validate environment configuration"
	@echo "  env-help      	Show environment setup help"
