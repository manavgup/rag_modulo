-include .env
export $(shell sed 's/=.*//' .env)
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

.DEFAULT_GOAL := help

.PHONY: init-env init check-toml format lint audit test run-services build-app run-app clean all info help

init-env:
	@touch .env
	@echo "PROJECT_NAME=${PROJECT_NAME}" >> .env
	@echo "PYTHON_VERSION=${PYTHON_VERSION}" >> .env

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

run-services:
	@echo "Starting services..."
	$(DOCKER_COMPOSE) up -d postgres
	@echo "Waiting for PostgreSQL to be ready..."
	@until docker exec $(shell docker ps -q -f name=postgres) pg_isready; do sleep 1; done
	@echo "Starting services for VECTOR_DB=${VECTOR_DB}"
	if [ "$(VECTOR_DB)" = "elasticsearch" ]; then \
	    $(DOCKER_COMPOSE) up -d --scale elasticsearch=1 elasticsearch; \
	elif [ "$(VECTOR_DB)" = "milvus" ]; then \
	    $(DOCKER_COMPOSE) up -d --scale milvus-standalone=1 milvus-standalone; \
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
	@echo "Waiting for services to be ready..."
	@sleep 120
	@echo "Docker containers status:"
	@docker ps
	@echo "${VECTOR_DB} logs saved to ${VECTOR_DB}.log:"
	@$(DOCKER_COMPOSE) logs ${VECTOR_DB} > ${VECTOR_DB}.log

build-app:
	$(DOCKER_COMPOSE) build

run-app: build-app
	$(DOCKER_COMPOSE) up -d

# Add a new target for logs
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

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  init-env      Initialize .env file with default values"
	@echo "  init          Install dependencies"
	@echo "  check-toml    Check TOML files for syntax errors"
	@echo "  format        Format code using black and isort"
	@echo "  lint          Lint code using ruff and mypy"
	@echo "  audit         Audit code using bandit"
	@echo "  test          Run tests using pytest"
	@echo "  run-services  Start services using Docker Compose"
	@echo "  build-app     Build app using Docker Compose"
	@echo "  run-app       Run app using Docker Compose"
	@echo "  clean         Clean up Docker Compose volumes"
	@echo "  all           Format, lint, audit, and test"
	@echo "  info          Display project information"
	@echo "  help          Display this help message"