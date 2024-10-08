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
DOCKER_COMPOSE := docker compose

# Set a default value for VECTOR_DB if not already set
VECTOR_DB ?= milvus

.DEFAULT_GOAL := help

.PHONY: init-env build-frontend build-backend build-tests build-all test api-test newman-test all-test run-app run-backend run-frontend run-services stop-containers clean create-volumes logs info help

# Init
init-env:
	@touch .env
	@echo "PROJECT_NAME=${PROJECT_NAME}" >> .env
	@echo "PYTHON_VERSION=${PYTHON_VERSION}" >> .env
	@echo "VECTOR_DB=${VECTOR_DB}" >> .env

# Build
build-frontend:
	docker build -t ${PROJECT_NAME}/frontend:${PROJECT_VERSION} -f ./webui/Dockerfile.frontend ./webui

build-backend:
	docker build -t ${PROJECT_NAME}/backend:${PROJECT_VERSION} -f ./backend/Dockerfile.backend ./backend

build-tests:
	docker build -t ${PROJECT_NAME}/backend-test:${PROJECT_VERSION} -f ./backend/Dockerfile.test ./backend

build-all: build-frontend build-backend build-tests

# Test
test: build-backend build-tests run-backend
	$(DOCKER_COMPOSE) run test pytest -v -s -m "not (chromadb or elasticsearch or pinecone or weaviate)" || { echo "Tests failed"; $(MAKE) stop-containers; exit 1; }

api-test: build-backend build-tests run-backend
	$(DOCKER_COMPOSE) run test pytest -v -s -m "api and not (chromadb or elasticsearch or pinecone or weaviate)" || { echo "API Tests failed"; $(MAKE) stop-containers; exit 1; }

newman-test: build-backend build-tests run-backend
	$(DOCKER_COMPOSE) run test newman run tests/postman/rag_modulo_api_collection.json --env-var "backend_base_url=${REACT_APP_API_URL}" || { echo "Postman Tests failed"; $(MAKE) stop-containers; exit 1; }

all-test: build-backend build-tests run-backend
	$(DOCKER_COMPOSE) run test pytest -v -s -m "not (chromadb or elasticsearch or pinecone or weaviate)" || { echo "Tests failed"; $(MAKE) stop-containers; exit 1; }
	$(DOCKER_COMPOSE) run test newman run tests/postman/rag_modulo_api_collection.json --env-var "backend_base_url=${REACT_APP_API_URL}" || { echo "Postman Tests failed"; $(MAKE) stop-containers; exit 1; }

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

# Stop / clean
stop-containers:
	echo "Stopping containers and removing volumes ..."	
	$(DOCKER_COMPOSE) down -v

clean:
	@echo "Cleaning up Docker Compose resources..."
	$(DOCKER_COMPOSE) down -v
	@echo "Cleaning up existing pods and containers..."
	-@podman pod rm -f $(podman pod ps -q) || true
	-@podman rm -f $(podman ps -a -q) || true
	-@podman volume prune -f || true
	-@podman container prune -f || true
	rm -rf .pytest_cache .mypy_cache data volumes my_chroma_data tests

# Service / reusable targets
create-volumes:
	@echo "Creating volume directories with correct permissions..."
	@mkdir -p ./volumes/postgres ./volumes/etcd ./volumes/minio ./volumes/milvus
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
	@echo "  test          		Run all tests using pytest"
	@echo "  api-test      		Run API tests using pytest"
	@echo "  newman-test   		Run API tests using newman"
	@echo "  all-test   		Run all tests using pytest and newman"
	@echo "  run-app       		Run both backend and frontend using Docker Compose"
	@echo "  run-backend   		Run backend using Docker Compose"
	@echo "  run-frontend  		Run frontend using Docker Compose"
	@echo "  run-services  		Run services using Docker Compose"
	@echo "  stop-containers  	Stop all containers using Docker Compose"	
	@echo "  clean         		Clean up Docker Compose volumes and cache"
	@echo "  create-volumes     Create folders for container volumes"	
	@echo "  logs          		View logs of running containers"
	@echo "  info          Display project information"
	@echo "  help          Display this help message"