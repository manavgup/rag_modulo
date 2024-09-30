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
PROJECT_NAME ?= rag_modulo
PYTHON_VERSION ?= 3.11
PROJECT_VERSION ?= v$(shell poetry version -s)

# Tools
DOCKER_COMPOSE := podman-compose

# Set a default value for VECTOR_DB if not already set
VECTOR_DB ?= milvus

.DEFAULT_GOAL := help

.PHONY: init-env init check-toml format lint audit test run-services build-app run-app clean all info help api-test install-deps newman-test run-backend run-frontend

init-env:
	@touch .env
	@echo "PROJECT_NAME=${PROJECT_NAME}" >> .env
	@echo "PYTHON_VERSION=${PYTHON_VERSION}" >> .env
	@echo "VECTOR_DB=${VECTOR_DB}" >> .env

install-deps:
	pip install -r requirements.txt

init: init-env install-deps

check-toml:
	# No equivalent for pip, so this can be left empty or removed

format:
	ruff check $(SOURCE_DIR) && black $(PROJECT_DIRS) && isort $(PROJECT_DIRS)

lint:
	ruff check $(SOURCE_DIR)
	mypy --install-types --show-error-codes --non-interactive $(SOURCE_DIR)

audit:
	bandit -r $(SOURCE_DIR) -x $(TEST_DIR)

test: run-services
	pytest $(TEST_DIR) || { echo "Tests failed"; exit 1; }
	@trap '$(DOCKER_COMPOSE) down' EXIT; \
	echo "Waiting for Docker containers to stop..."
	@while docker ps | grep -q "milvus-standalone"; do sleep 1; done

api-test: run-services
	pytest $(TEST_DIR)/api -v -m api || { echo "API Tests failed"; exit 1; }
	@trap '$(DOCKER_COMPOSE) down' EXIT; \
	echo "Waiting for Docker containers to stop..."
	@while docker ps | grep -q "milvus-standalone"; do sleep 1; done

newman-test: run-services
	newman run postman/rag_modulo_api_collection.json
	@trap '$(DOCKER_COMPOSE) down' EXIT; \
	echo "Waiting for Docker containers to stop..."
	@while docker ps | grep -q "milvus-standalone"; do sleep 1; done

create-volumes:
	@echo "Creating volume directories with correct permissions..."
	@mkdir -p ./volumes/postgres ./volumes/etcd ./volumes/minio ./volumes/milvus
	@chmod -R 777 ./volumes
	@echo "Volume directories created and permissions set."

run-services: create-volumes
	@if [ -z "$(VECTOR_DB)" ]; then \
		echo "Warning: VECTOR_DB is not set. Using default value: milvus"; \
		export VECTOR_DB=milvus; \
	fi
	@echo "Starting services..."
	$(DOCKER_COMPOSE) up -d postgres
	@echo "Waiting for PostgreSQL to be ready..."
	@for i in $$(seq 1 30); do \
		if $(DOCKER_COMPOSE) exec postgres pg_isready -U ${COLLECTIONDB_USER} -d ${COLLECTIONDB_NAME}; then \
			echo "PostgreSQL is ready"; \
			break; \
		fi; \
		if [ $$i -eq 30 ]; then \
			echo "PostgreSQL did not become ready in time"; \
			exit 1; \
		fi; \
		echo "Waiting for PostgreSQL to be ready... ($$i/30)"; \
		sleep 2; \
	done
	@echo "Starting services for VECTOR_DB=${VECTOR_DB}"
	if [ "$(VECTOR_DB)" = "milvus" ]; then \
		echo "Starting Milvus and its dependencies..."; \
		$(DOCKER_COMPOSE) up -d etcd minio milvus-standalone || { echo "Failed to start Milvus and its dependencies"; $(DOCKER_COMPOSE) logs; exit 1; }; \
		echo "Waiting for Milvus to be ready..."; \
		for i in $$(seq 1 30); do \
			if $(DOCKER_COMPOSE) exec milvus-standalone curl -s http://localhost:9091/healthz | grep -q "OK"; then \
				echo "Milvus is ready"; \
				break; \
			fi; \
			if [ $$i -eq 30 ]; then \
				echo "Milvus did not become ready in time"; \
				$(DOCKER_COMPOSE) logs milvus-standalone; \
				exit 1; \
			fi; \
			echo "Waiting for Milvus to be ready... ($$i/30)"; \
			sleep 10; \
		done; \
	elif [ "$(VECTOR_DB)" = "elasticsearch" ]; then \
		$(DOCKER_COMPOSE) up -d --scale elasticsearch=1 elasticsearch; \
	elif [ "$(VECTOR_DB)" = "chroma" ]; then \
		$(DOCKER_COMPOSE) up -d --scale chroma=1 chroma; \
	elif [ "$(VECTOR_DB)" = "weaviate" ]; then \
		$(DOCKER_COMPOSE) up -d --scale weaviate=1 weaviate; \
	elif [ "$(VECTOR_DB)" = "pinecone" ]; then \
		echo "Pinecone does not require a local Docker container."; \
	else \
		echo "Unknown VECTOR_DB value: $(VECTOR_DB)"; \
		exit 1; \
	fi
	@echo "Docker containers status:"
	@docker ps
	@echo "Milvus logs saved to milvus.log:"
	@$(DOCKER_COMPOSE) logs milvus-standalone > milvus.log

run-tests:
	$(DOCKER_COMPOSE) run --rm test pytest $(ARGS)

build-frontend:
	docker build -t $(PROJECT_NAME)-frontend -f webui/Dockerfile.frontend ./webui

build-backend:
	docker build --build-arg CACHEBUST=$(date +%s) -t $(PROJECT_NAME)-backend --no-cache -f Dockerfile.backend .

build-app:
	@echo "Building application containers..."
	$(DOCKER_COMPOSE) build

run-backend: run-services
	@echo "Starting backend..."
	$(DOCKER_COMPOSE) up -d backend
	@echo "Backend is now running."

run-frontend: run-services
	@echo "Starting frontend..."
	$(DOCKER_COMPOSE) up -d frontend
	@echo "Frontend is now running."

run-app: build-app run-backend run-frontend
	@echo "All application containers are now running."

logs:
	$(DOCKER_COMPOSE) logs -f

clean:
	@echo "Cleaning up Docker Compose resources..."
	$(DOCKER_COMPOSE) down -v
	@echo "Cleaning up existing pods and containers..."
	-@podman pod rm -f $(podman pod ps -q) || true
	-@podman rm -f $(podman ps -a -q) || true
	-@podman volume prune -f || true
	rm -rf .pytest_cache .mypy_cache data volumes my_chroma_data tests

all: format lint audit test

info:
	@echo "Project name: ${PROJECT_NAME}"
	@echo "Project version: ${PROJECT_VERSION}"
	@echo "Python version: ${PYTHON_VERSION}"
	@echo "Vector DB: ${VECTOR_DB}"

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  init-env      Initialize .env file with default values"
	@echo "  init          Initialize environment and install dependencies"
	@echo "  install-deps  Install project dependencies"
	@echo "  check-toml    Check TOML files for syntax errors"
	@echo "  format        Format code using ruff, black, and isort"
	@echo "  lint          Lint code using ruff and mypy"
	@echo "  audit         Audit code using bandit"
	@echo "  test          Run all tests using pytest"
	@echo "  api-test      Run API tests using pytest"
	@echo "  newman-test   Run API tests using Newman"
	@echo "  run-services  Start services using Docker Compose"
	@echo "  build-app     Build app using Docker Compose"
	@echo "  run-backend   Run backend using Docker Compose"
	@echo "  run-frontend  Run frontend using Docker Compose"
	@echo "  run-app       Run both backend and frontend using Docker Compose"
	@echo "  logs          View logs of running containers"
	@echo "  clean         Clean up Docker Compose volumes and cache"
	@echo "  all           Format, lint, audit, and test"
	@echo "  info          Display project information"
	@echo "  help          Display this help message"
	@echo "  dev           Start development environment"
	@echo "  dev-build     Build development environment"
	@echo "  dev-down      Stop development environment"
	@echo "  dev-backend   Start backend development server"
	@echo "  dev-frontend  Start frontend development server"

dev:
	docker-compose -f docker-compose.dev.yml up

dev-build:
	docker-compose -f docker-compose.dev.yml build

dev-down:
	docker-compose -f docker-compose.dev.yml down

dev-backend:
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd webui && npm start