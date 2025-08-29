# Include environment variables from .env file
-include .env
export $(shell sed 's/=.*//' .env)

# Set PYTHONPATH
export PYTHONPATH=$(pwd):$(pwd)/vectordbs:$(pwd)/rag_solution

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

# Set a default value for VECTOR_DB if not already set
VECTOR_DB ?= milvus

.DEFAULT_GOAL := help

.PHONY: init-env sync-frontend-deps build-frontend build-backend build-tests build-all test tests api-tests unit-tests integration-tests performance-tests service-tests pipeline-tests all-tests run-app run-backend run-frontend run-services stop-containers clean create-volumes logs info help pull-ghcr-images

# Init
init-env:
	@touch .env
	@echo "PROJECT_NAME=${PROJECT_NAME}" >> .env
	@echo "PYTHON_VERSION=${PYTHON_VERSION}" >> .env
	@echo "VECTOR_DB=${VECTOR_DB}" >> .env

sync-frontend-deps:
	@echo "Syncing frontend dependencies..."
	@cd webui && npm install
	@echo "Frontend dependencies synced."

# Build and Push - GHCR-first strategy
build-frontend:
	@echo "Building and pushing frontend image..."
	$(CONTAINER_CLI) build -t ${GHCR_REPO}/frontend:${PROJECT_VERSION} -t ${GHCR_REPO}/frontend:latest -f ./webui/Dockerfile.frontend ./webui
	$(CONTAINER_CLI) push ${GHCR_REPO}/frontend:${PROJECT_VERSION}
	$(CONTAINER_CLI) push ${GHCR_REPO}/frontend:latest

build-backend:
	@echo "Building and pushing backend image..."
	$(CONTAINER_CLI) build -t ${GHCR_REPO}/backend:${PROJECT_VERSION} -t ${GHCR_REPO}/backend:latest -f ./backend/Dockerfile.backend ./backend
	$(CONTAINER_CLI) push ${GHCR_REPO}/backend:${PROJECT_VERSION}
	$(CONTAINER_CLI) push ${GHCR_REPO}/backend:latest

build-tests:
	@echo "Building test image..."
	$(CONTAINER_CLI) build -t ${GHCR_REPO}/backend:test-${PROJECT_VERSION} -f ./backend/Dockerfile.test ./backend
	$(CONTAINER_CLI) push ${GHCR_REPO}/backend:test-${PROJECT_VERSION}

build-all: build-frontend build-backend build-tests

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
	@echo "TEST_IMAGE=${GHCR_REPO}/backend:latest" >> .env.local
	@echo "GHCR image configuration saved to .env.local"

# Helper function to check if containers are healthy
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

tests: run-backend create-test-dirs
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

# Run - Local Development (default - uses local builds)
run-app: build-all run-backend run-frontend
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

# Local CI targets (mirror GitHub Actions)
lint:
	@echo "Running linting locally..."
	cd backend && poetry run ruff check . || echo "Linting issues found"
	@echo "✅ Linting completed"

unit-tests-local:
	@echo "Running unit tests locally..."
	cd backend && poetry run pytest tests/ -m unit --maxfail=5 || echo "Unit tests need fixing"
	@echo "✅ Unit tests completed"

ci-local: lint unit-tests-local
	@echo "✅ Local CI checks completed successfully!"

validate-ci:
	@echo "🔍 Validating CI workflows..."
	./scripts/validate-ci.sh

setup-pre-commit:
	@echo "Setting up pre-commit hooks..."
	pip install pre-commit
	pre-commit install
	@echo "✅ Pre-commit hooks installed"

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Local CI Targets:"
	@echo "  ci-local      \t\tRun full local CI (lint + unit tests)"
	@echo "  lint          \t\tRun linting locally"
	@echo "  unit-tests-local  \tRun unit tests locally"
	@echo "  validate-ci   \t\tValidate CI workflows with act"
	@echo "  setup-pre-commit  \tInstall pre-commit hooks"
	@echo ""
	@echo "Container Targets:"
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
