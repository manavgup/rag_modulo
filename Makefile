# Include environment variables from .env file
-include .env
export $(shell sed 's/=.*//' .env)

# Set PYTHONPATH
export PYTHONPATH=$(pwd):$(pwd)/vectordbs:$(pwd)/rag_solution

# Directories
SOURCE_DIR := ./backend/rag_solution
TEST_DIR := ./backend/tests
PROJECT_DIRS := $(SOURCE_DIR) $(TEST_DIR)

# Project info
PROJECT_NAME ?= rag-modulo
PYTHON_VERSION ?= 3.11
PROJECT_VERSION ?= 1.0.0

# Tools
CONTAINER_CLI := podman
DOCKER_COMPOSE := docker compose

# Set a default value for VECTOR_DB if not already set
VECTOR_DB ?= milvus

.DEFAULT_GOAL := help

.PHONY: init-env sync-frontend-deps build-frontend build-backend build-tests build-all test tests api-tests all-tests run-app run-backend run-frontend run-services stop-containers clean create-volumes logs info help

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

# Build
build-frontend:
	$(CONTAINER_CLI) build -t ${PROJECT_NAME}/frontend:${PROJECT_VERSION} -f ./webui/Dockerfile.frontend ./webui

build-backend:
	$(CONTAINER_CLI) build -t ${PROJECT_NAME}/backend:${PROJECT_VERSION} -f ./backend/Dockerfile.backend ./backend

build-tests:
	$(CONTAINER_CLI) build -t ${PROJECT_NAME}/backend-test:${PROJECT_VERSION} -f ./backend/Dockerfile.test ./backend

build-all: build-frontend build-backend build-tests

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

# Test target with proper volume mounting and path handling
test: check_containers
	@if [ -z "$(test_name)" ]; then \
		echo "Error: Please provide test_name. Example: make test test_name=tests/router/test_user_collection_router.py"; \
		exit 1; \
	else \
		echo "Running test: $(test_name)"; \
		$(DOCKER_COMPOSE) run --rm \
			-v $$(pwd)/backend:/app/backend:ro \
			test pytest -s $(test_name) || \
		{ \
			echo "Test $(test_name) failed"; \
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
	@if [ -z "$(test_name)" ]; then \
		echo "Error: Please provide test_name. Example: make test-only test_name=tests/router/test_user_collection_router.py"; \
		exit 1; \
	else \
		echo "Running test: $(test_name)"; \
		$(DOCKER_COMPOSE) run --rm \
			-v $$(pwd)/backend:/app/backend:ro \
			test pytest -v -s /app/$(test_name); \
	fi

tests: run-backend
	$(DOCKER_COMPOSE) run --rm test pytest -v -s -m "not (chromadb or elasticsearch or pinecone or weaviate)" || { echo "Tests failed"; $(MAKE) stop-containers; exit 1; }

api-tests: run-backend
	$(DOCKER_COMPOSE) run --rm test pytest -v -s -m "api and not (chromadb or elasticsearch or pinecone or weaviate)" || { echo "API Tests failed"; $(MAKE) stop-containers; exit 1; }

# Run
run-app: build-all run-backend run-frontend
	@echo "All application containers are now running."

run-backend: run-services
	@echo "Starting backend..."
	$(DOCKER_COMPOSE) up -d backend
	@echo "Backend is now running."

run-frontend: run-services
	@echo "Starting frontend..."
	$(DOCKER_COMPOSE) up -d frontend
	@echo "Frontend is now running."

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
				echo "Logs from failed containers:"; \
				for container in $$failed_containers; do \
					echo "Container ID: $$container"; \
					$(CONTAINER_CLI) logs $$container; \
				done; \
			else \
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

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  init-env      		Initialize .env file with default values"
	@echo "  build-frontend  	Build frontend code/container"
	@echo "  build-backend   	Build backend code/container"
	@echo "  build-tests   		Build test code/container"
	@echo "  build-all   		Build frontend/backend/test code/container"
	@echo "  test          		Run specific test, test_name param is required (make test test_name=tests/router/test_user_collection_router.py)"
	@echo "  tests          	Run all tests using pytest"
	@echo "  api-tests      	Run API tests only (using pytest)"
	@echo "  all-tests   		Run all tests: REST API and others"
	@echo "  run-app       		Run both backend and frontend using Docker Compose"
	@echo "  run-backend   		Run backend using Docker Compose"
	@echo "  run-frontend  		Run frontend using Docker Compose"
	@echo "  run-services  		Run services using Docker Compose"
	@echo "  stop-containers  	Stop all containers using Docker Compose"
	@echo "  clean         		Clean up Docker Compose volumes and cache"
	@echo "  create-volumes     Create folders for container volumes"
	@echo "  logs          		View logs of running containers"
	@echo "  info          		Display project information"
	@echo "  help          		Display this help message"