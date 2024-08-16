# Include environment variables from .env file
-include .env
export $(shell sed 's/=.*//' .env)

# Set PYTHONPATH
export PYTHONPATH=$(pwd):$(pwd)/vectordbs:$(pwd)/rag_solution

# Directories
SOURCE_DIR := rag_solution
TEST_DIR := tests
PROJECT_DIRS := $(SOURCE_DIR) $(TEST_DIR)

# Project info
PROJECT_NAME ?= rag_modulo
PYTHON_VERSION ?= 3.11
PROJECT_VERSION ?= v$(shell poetry version -s)

# Tools
DOCKER_COMPOSE := docker-compose

# Set a default value for VECTOR_DB if not already set
VECTOR_DB ?= milvus

.DEFAULT_GOAL := help

.PHONY: init-env init check-toml format lint audit test run-services build-app run-app clean all info help

init-env:
	@touch .env
	@echo "PROJECT_NAME=${PROJECT_NAME}" >> .env
	@echo "PYTHON_VERSION=${PYTHON_VERSION}" >> .env
	@echo "VECTOR_DB=${VECTOR_DB}" >> .env

init: init-env
	pip install -r requirements.txt

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
		if docker-compose exec postgres pg_isready -U ${COLLECTIONDB_USER} -d ${COLLECTIONDB_NAME}; then \
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
			if docker-compose exec milvus-standalone curl -s http://localhost:9091/healthz | grep -q "OK"; then \
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
	@echo "Starting backend and frontend..."
	$(DOCKER_COMPOSE) up -d backend frontend
	@echo "Docker containers status:"
	@docker ps
	@echo "Milvus logs saved to milvus.log:"
	@$(DOCKER_COMPOSE) logs milvus-standalone > milvus.log

build-app:
	$(DOCKER_COMPOSE) build

run-app: build-app run-services
	@echo "Starting remaining application containers..."
	$(DOCKER_COMPOSE) up -d
	@echo "All application containers are now running."

logs:
	$(DOCKER_COMPOSE) logs -f

clean:
	$(DOCKER_COMPOSE) down -v
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
	@echo "  init          Install dependencies"
	@echo "  check-toml    Check TOML files for syntax errors"
	@echo "  format        Format code using ruff, black, and isort"
	@echo "  lint          Lint code using ruff and mypy"
	@echo "  audit         Audit code using bandit"
	@echo "  test          Run tests using pytest"
	@echo "  run-services  Start services using Docker Compose"
	@echo "  build-app     Build app using Docker Compose"
	@echo "  run-app       Run app using Docker Compose"
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