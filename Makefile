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
POETRY := poetry
DOCKER_COMPOSE := docker-compose

.DEFAULT_GOAL := all

.PHONY: init-env init check-toml format lint audit test run-services build-app run-app clean all info

init-env:
	@touch .env
	@echo "PROJECT_NAME=${PROJECT_NAME}" >> .env
	@echo "PYTHON_VERSION=${PYTHON_VERSION}" >> .env

init: init-env
	$(POETRY) install --no-root

check-toml:
	$(POETRY) check

format:
	$(POETRY) run black $(PROJECT_DIRS)
	$(POETRY) run isort $(PROJECT_DIRS)

lint:
	$(POETRY) run ruff check $(SOURCE_DIR)
	$(POETRY) run mypy --install-types --show-error-codes --non-interactive $(SOURCE_DIR)

audit:
	$(POETRY) run bandit -r $(SOURCE_DIR) -x $(TEST_DIR)

test: run-services
	$(POETRY) run pytest $(TEST_DIR) || { echo "Tests failed"; exit 1; }
	@trap '$(DOCKER_COMPOSE) down' EXIT; \
	echo "Waiting for Docker containers to stop..."
	@while docker ps | grep -q "milvus-standalone"; do sleep 1; done

run-services:
	@echo "Starting services for VECTOR_DB=${VECTOR_DB}"
	if [ "$(VECTOR_DB)" = "elasticsearch" ]; then \
	    $(DOCKER_COMPOSE) up -d --scale elasticsearch=1 elasticsearch; \
	elif [ "$(VECTOR_DB)" = "milvus" ]; then \
	    $(DOCKER_COMPOSE) up -d --scale milvus=1 milvus; \
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
	$(DOCKER_COMPOSE) build backend frontend

run-app: build-app
	$(DOCKER_COMPOSE) up -d backend frontend

clean:
	$(DOCKER_COMPOSE) down -v
	rm -rf .pytest_cache .mypy_cache

all: format lint audit test

info:
	@echo "Project name: ${PROJECT_NAME}"
	@echo "Project version: ${PROJECT_VERSION}"
	@echo "Python version: ${PYTHON_VERSION}"