-include .env

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
	$(POETRY) install

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

test:
	$(POETRY) run pytest $(TEST_DIR)

run-services:
	$(DOCKER_COMPOSE) up -d elasticsearch milvus

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