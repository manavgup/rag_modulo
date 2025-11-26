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
VENV_DIR := .venv
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

# Platform detection for multi-architecture builds
PLATFORM := $(shell uname -m)
UNAME_S := $(shell uname -s)

ifeq ($(PLATFORM),arm64)
    DOCKER_PLATFORM := linux/arm64
    IS_MAC_ARM := yes
    PLATFORM_WARNING := "$(YELLOW)⚠️  Running on ARM64 (Mac). Some services (Milvus/MLFlow) may have compatibility issues.$(NC)"
else ifeq ($(PLATFORM),x86_64)
    DOCKER_PLATFORM := linux/amd64
    IS_MAC_ARM := no
    PLATFORM_WARNING := ""
else
    DOCKER_PLATFORM := linux/$(PLATFORM)
    IS_MAC_ARM := no
    PLATFORM_WARNING := ""
endif

.DEFAULT_GOAL := help
.PHONY: help venv clean-venv local-dev-setup local-dev-infra local-dev-backend local-dev-frontend local-dev-all local-dev-stop local-dev-status build-backend build-frontend build-all build-multiarch-backend build-multiarch-frontend build-multiarch-all build-amd64-backend build-amd64-frontend build-amd64-all build-arm64-backend build-arm64-frontend build-arm64-all dev-full-build dev-full-start dev-full-stop dev-full-restart dev-full-logs dev-full-status dev-full-build-multiarch push-backend push-frontend push-all build-push-backend build-push-frontend build-push-all build-multiarch-push-backend build-multiarch-push-frontend build-multiarch-push-all deploy-pull-images deploy-remote prod-start prod-stop prod-restart prod-logs prod-status test-atomic test-unit-fast test-integration test-integration-ci test-e2e test-e2e-ci test-e2e-local-parallel test-e2e-ci-parallel test-all test-all-ci lint format quick-check security-check pre-commit-run clean clean-all

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
	@$(POETRY) config virtualenvs.in-project true
	@$(POETRY) install --with dev,test
	@echo "$(GREEN)✅ Virtual environment created at .venv$(NC)"
	@echo "$(CYAN)💡 Activate with: source .venv/bin/activate$(NC)"

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
	@if docker ps --format '{{.Names}}' | grep -q 'milvus-etcd'; then \
		echo "$(YELLOW)⚠️  Infrastructure containers already running$(NC)"; \
	else \
		$(DOCKER_COMPOSE) -f docker-compose-infra.yml up -d --remove-orphans || \
		(echo "$(YELLOW)⚠️  Containers exist but stopped, starting them...$(NC)" && \
		 $(DOCKER_COMPOSE) -f docker-compose-infra.yml start); \
	fi
	@echo "$(GREEN)✅ Infrastructure ready$(NC)"
	@echo "$(CYAN)💡 Services:$(NC)"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Milvus:     localhost:19530"
	@echo "  MinIO:      localhost:9001"
	@echo "  MLFlow:     localhost:5001"

local-dev-backend: venv
	@echo "$(CYAN)🐍 Starting backend with hot-reload (uvicorn)...$(NC)"
	@echo "$(YELLOW)⚠️  Make sure infrastructure is running: make local-dev-infra$(NC)"
	@$(POETRY) run uvicorn main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend

local-dev-frontend:
	@echo "$(CYAN)⚛️  Starting frontend with HMR (Vite)...$(NC)"
	@cd frontend && DANGEROUSLY_DISABLE_HOST_CHECK=true npm run dev

local-dev-all: venv
	@echo "$(CYAN)🚀 Starting full local development stack...$(NC)"
	@PROJECT_ROOT=$$(pwd); \
	mkdir -p $$PROJECT_ROOT/.dev-pids $$PROJECT_ROOT/logs; \
	$(MAKE) local-dev-infra; \
	echo "$(CYAN)🐍 Starting backend in background...$(NC)"; \
	$(POETRY) run uvicorn main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend > $$PROJECT_ROOT/logs/backend.log 2>&1 & echo $$! > $$PROJECT_ROOT/.dev-pids/backend.pid; \
	sleep 2; \
	if [ -f $$PROJECT_ROOT/.dev-pids/backend.pid ]; then \
		if kill -0 $$(cat $$PROJECT_ROOT/.dev-pids/backend.pid) 2>/dev/null; then \
			echo "$(GREEN)✅ Backend started (PID: $$(cat $$PROJECT_ROOT/.dev-pids/backend.pid))$(NC)"; \
		else \
			echo "$(RED)❌ Backend failed to start - check logs/backend.log$(NC)"; \
			exit 1; \
		fi; \
	fi; \
	echo "$(CYAN)⚛️  Starting frontend in background...$(NC)"; \
	cd frontend && DANGEROUSLY_DISABLE_HOST_CHECK=true npm run dev > $$PROJECT_ROOT/logs/frontend.log 2>&1 & echo $$! > $$PROJECT_ROOT/.dev-pids/frontend.pid; \
	sleep 2; \
	if [ -f $$PROJECT_ROOT/.dev-pids/frontend.pid ]; then \
		if kill -0 $$(cat $$PROJECT_ROOT/.dev-pids/frontend.pid) 2>/dev/null; then \
			echo "$(GREEN)✅ Frontend started (PID: $$(cat $$PROJECT_ROOT/.dev-pids/frontend.pid))$(NC)"; \
		else \
			echo "$(RED)❌ Frontend failed to start - check logs/frontend.log$(NC)"; \
			exit 1; \
		fi; \
	fi; \
	echo "$(GREEN)✅ Local development environment running!$(NC)"; \
	echo "$(CYAN)💡 Services:$(NC)"; \
	echo "  Frontend:  http://localhost:3000"; \
	echo "  Backend:   http://localhost:8000"; \
	echo "  MLFlow:    http://localhost:5001"; \
	echo "$(CYAN)📋 Logs:$(NC)"; \
	echo "  Backend:   tail -f logs/backend.log"; \
	echo "  Frontend:  tail -f logs/frontend.log"; \
	echo "$(CYAN)🛑 Stop:$(NC) make local-dev-stop"

local-dev-stop:
	@echo "$(CYAN)🛑 Stopping local development services...$(NC)"
	@if [ -f .dev-pids/backend.pid ]; then \
		if kill -0 $$(cat .dev-pids/backend.pid) 2>/dev/null; then \
			kill $$(cat .dev-pids/backend.pid) && echo "$(GREEN)✅ Backend stopped$(NC)"; \
		fi; \
		rm -f .dev-pids/backend.pid; \
	else \
		echo "Backend not running (no PID file)"; \
	fi
	@if [ -f .dev-pids/frontend.pid ]; then \
		if kill -0 $$(cat .dev-pids/frontend.pid) 2>/dev/null; then \
			kill $$(cat .dev-pids/frontend.pid) && echo "$(GREEN)✅ Frontend stopped$(NC)"; \
		fi; \
		rm -f .dev-pids/frontend.pid; \
	else \
		echo "Frontend not running (no PID file)"; \
	fi
	@$(DOCKER_COMPOSE) -f docker-compose-infra.yml down
	@rm -rf .dev-pids
	@echo "$(GREEN)✅ Local development stopped$(NC)"

local-dev-status:
	@echo "$(CYAN)📊 Local Development Status$(NC)"
	@echo ""
	@echo "$(CYAN)🐳 Infrastructure:$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose-infra.yml ps
	@echo ""
	@echo "$(CYAN)🐍 Backend:$(NC)"
	@if [ -f .dev-pids/backend.pid ]; then \
		if kill -0 $$(cat .dev-pids/backend.pid) 2>/dev/null; then \
			echo "$(GREEN)✅ Running (PID: $$(cat .dev-pids/backend.pid))$(NC)"; \
		else \
			echo "$(RED)❌ PID file exists but process is dead$(NC)"; \
			rm -f .dev-pids/backend.pid; \
		fi; \
	else \
		echo "$(RED)❌ Not running$(NC)"; \
	fi
	@echo ""
	@echo "$(CYAN)⚛️  Frontend:$(NC)"
	@if [ -f .dev-pids/frontend.pid ]; then \
		if kill -0 $$(cat .dev-pids/frontend.pid) 2>/dev/null; then \
			echo "$(GREEN)✅ Running (PID: $$(cat .dev-pids/frontend.pid))$(NC)"; \
		else \
			echo "$(RED)❌ PID file exists but process is dead$(NC)"; \
			rm -f .dev-pids/frontend.pid; \
		fi; \
	else \
		echo "$(RED)❌ Not running$(NC)"; \
	fi

# ============================================================================
# BUILD TARGETS
# ============================================================================

build-backend:
	@echo "$(CYAN)🔨 Building backend image...$(NC)"
	@if [ "$(BUILDX_AVAILABLE)" = "yes" ]; then \
		echo "Using Docker BuildKit with buildx..."; \
		$(CONTAINER_CLI) buildx build --load \
			-t $(GHCR_REPO)/backend:$(PROJECT_VERSION) \
			-t $(GHCR_REPO)/backend:latest \
			-f backend/Dockerfile.backend \
			--build-arg BUILDKIT_INLINE_CACHE=1 \
			.; \
	else \
		echo "Using standard Docker build..."; \
		$(CONTAINER_CLI) build \
			-t $(GHCR_REPO)/backend:$(PROJECT_VERSION) \
			-t $(GHCR_REPO)/backend:latest \
			-f backend/Dockerfile.backend \
			.; \
	fi
	@echo "$(GREEN)✅ Backend image built$(NC)"

build-frontend:
	@echo "$(CYAN)🔨 Building frontend image...$(NC)"
	@if [ "$(BUILDX_AVAILABLE)" = "yes" ]; then \
		echo "Using Docker BuildKit with buildx..."; \
		$(CONTAINER_CLI) buildx build --load \
			-t $(GHCR_REPO)/frontend:$(PROJECT_VERSION) \
			-t $(GHCR_REPO)/frontend:latest \
			-f frontend/Dockerfile.frontend \
			frontend/; \
	else \
		echo "Using standard Docker build..."; \
		$(CONTAINER_CLI) build \
			-t $(GHCR_REPO)/frontend:$(PROJECT_VERSION) \
			-t $(GHCR_REPO)/frontend:latest \
			-f frontend/Dockerfile.frontend \
			frontend/; \
	fi
	@echo "$(GREEN)✅ Frontend image built$(NC)"

build-all: build-backend build-frontend
	@echo "$(GREEN)✅ All images built successfully$(NC)"

# ============================================================================
# CLOUD DEPLOYMENT BUILDS (AMD64 for ROKS/EKS/AKS/GKE)
# ============================================================================
# Build AMD64 images for cloud deployment (Linux servers)
# NOTE: Slow on Mac ARM (QEMU cross-compilation), fast on GitHub Actions
# RECOMMENDED: Use GitHub Actions for cloud builds, local only for testing
# ============================================================================

build-cloud-backend:
	@echo "$(CYAN)🔨 Building backend for AMD64 (cloud deployment)...$(NC)"
	@if [ "$(IS_MAC_ARM)" = "yes" ]; then \
		echo "$(YELLOW)⚠️  Cross-compiling ARM64→AMD64 (slow, ~10-15 min)$(NC)"; \
		echo "$(YELLOW)💡 Tip: Push code to git and let GitHub Actions build (1-2 min)$(NC)"; \
	fi
	$(CONTAINER_CLI) buildx build \
		--platform linux/amd64 \
		--load \
		-t $(GHCR_REPO)/backend:$(PROJECT_VERSION) \
		-t $(GHCR_REPO)/backend:latest \
		-f backend/Dockerfile.backend \
		--build-arg BUILDKIT_INLINE_CACHE=1 \
		.
	@echo "$(GREEN)✅ AMD64 backend built$(NC)"

build-cloud-frontend:
	@echo "$(CYAN)🔨 Building frontend for AMD64 (cloud deployment)...$(NC)"
	@if [ "$(IS_MAC_ARM)" = "yes" ]; then \
		echo "$(YELLOW)⚠️  Cross-compiling ARM64→AMD64 (slow, ~5-8 min)$(NC)"; \
		echo "$(YELLOW)💡 Tip: Push code to git and let GitHub Actions build (1-2 min)$(NC)"; \
	fi
	$(CONTAINER_CLI) buildx build \
		--platform linux/amd64 \
		--load \
		-t $(GHCR_REPO)/frontend:$(PROJECT_VERSION) \
		-t $(GHCR_REPO)/frontend:latest \
		-f frontend/Dockerfile.frontend \
		frontend/
	@echo "$(GREEN)✅ AMD64 frontend built$(NC)"

build-cloud-all: build-cloud-backend build-cloud-frontend
	@echo "$(GREEN)✅ All AMD64 images built$(NC)"
	@echo "$(CYAN)💡 Ready to push to GHCR: make push-all$(NC)"

# Backward compatibility (deprecated)
build-multiarch-backend: build-cloud-backend
	@echo "$(YELLOW)⚠️  DEPRECATED: Use 'make build-cloud-backend' instead$(NC)"

build-multiarch-frontend: build-cloud-frontend
	@echo "$(YELLOW)⚠️  DEPRECATED: Use 'make build-cloud-frontend' instead$(NC)"

build-multiarch-all: build-cloud-all
	@echo "$(YELLOW)⚠️  DEPRECATED: Use 'make build-cloud-all' instead$(NC)"

# Explicit architecture builds
build-amd64-backend:
	@echo "$(CYAN)🔨 Building backend for AMD64 explicitly...$(NC)"
	$(CONTAINER_CLI) buildx build \
		--platform linux/amd64 \
		--load \
		-t $(GHCR_REPO)/backend:$(PROJECT_VERSION)-amd64 \
		-f backend/Dockerfile.backend \
		.
	@echo "$(GREEN)✅ AMD64 backend built$(NC)"

build-amd64-frontend:
	@echo "$(CYAN)🔨 Building frontend for AMD64 explicitly...$(NC)"
	$(CONTAINER_CLI) buildx build \
		--platform linux/amd64 \
		--load \
		-t $(GHCR_REPO)/frontend:$(PROJECT_VERSION)-amd64 \
		-f frontend/Dockerfile.frontend \
		frontend/
	@echo "$(GREEN)✅ AMD64 frontend built$(NC)"

build-amd64-all: build-amd64-backend build-amd64-frontend
	@echo "$(GREEN)✅ All AMD64 images built$(NC)"

build-arm64-backend:
	@echo "$(CYAN)🔨 Building backend for ARM64 explicitly...$(NC)"
	$(CONTAINER_CLI) buildx build \
		--platform linux/arm64 \
		--load \
		-t $(GHCR_REPO)/backend:$(PROJECT_VERSION)-arm64 \
		-f backend/Dockerfile.backend \
		.
	@echo "$(GREEN)✅ ARM64 backend built$(NC)"

build-arm64-frontend:
	@echo "$(CYAN)🔨 Building frontend for ARM64 explicitly...$(NC)"
	$(CONTAINER_CLI) buildx build \
		--platform linux/arm64 \
		--load \
		-t $(GHCR_REPO)/frontend:$(PROJECT_VERSION)-arm64 \
		-f frontend/Dockerfile.frontend \
		frontend/
	@echo "$(GREEN)✅ ARM64 frontend built$(NC)"

build-arm64-all: build-arm64-backend build-arm64-frontend
	@echo "$(GREEN)✅ All ARM64 images built$(NC)"

# ============================================================================
# FULL CONTAINERIZED STACK (Workflow 2)
# ============================================================================
# Run everything in containers (production-like testing locally)
# ============================================================================

dev-full-build:
	@echo "$(CYAN)🔨 Building full stack (native architecture)...$(NC)"
	@echo "$(YELLOW)💡 Fast build for local testing only$(NC)"
	@if [ "$(IS_MAC_ARM)" = "yes" ]; then \
		echo $(PLATFORM_WARNING); \
	fi
	$(MAKE) build-backend
	$(MAKE) build-frontend
	@echo "$(GREEN)✅ Full stack built for native architecture$(NC)"

dev-full-start: dev-full-build create-volumes
	@echo "$(CYAN)🚀 Starting full containerized stack...$(NC)"
	@if [ "$(IS_MAC_ARM)" = "yes" ]; then \
		echo "$(YELLOW)⚠️  ARM64 detected: Using hybrid mode (infra separately, apps containerized)$(NC)"; \
		echo "$(YELLOW)💡 Starting infrastructure containers...$(NC)"; \
		$(MAKE) local-dev-infra; \
		echo "$(YELLOW)💡 Checking infrastructure health (Postgres, MinIO, MLFlow)...$(NC)"; \
		if ! docker ps --filter "name=postgres" --filter "health=healthy" | grep -q postgres; then \
			echo "$(RED)❌ PostgreSQL not healthy. Run 'docker ps' to debug.$(NC)"; \
			exit 1; \
		fi; \
		if ! docker ps --filter "name=minio" --filter "health=healthy" | grep -q minio; then \
			echo "$(RED)❌ MinIO not healthy. Run 'docker ps' to debug.$(NC)"; \
			exit 1; \
		fi; \
		if ! docker ps --filter "name=mlflow" | grep -q mlflow; then \
			echo "$(RED)❌ MLFlow not running. Run 'docker ps' to debug.$(NC)"; \
			exit 1; \
		fi; \
		echo "$(GREEN)✅ Infrastructure healthy (Milvus check skipped on ARM64)$(NC)"; \
		echo "$(YELLOW)💡 Starting backend container (ARM64, no deps)...$(NC)"; \
		$(DOCKER_COMPOSE) -f docker-compose.fullstack.yml up -d --no-deps backend; \
		echo "$(YELLOW)💡 Starting frontend container (ARM64, no deps)...$(NC)"; \
		$(DOCKER_COMPOSE) -f docker-compose.fullstack.yml up -d --no-deps frontend; \
	else \
		echo "$(CYAN)💡 AMD64/x86 detected: Starting full stack...$(NC)"; \
		BACKEND_IMAGE=$(GHCR_REPO)/backend:latest \
		FRONTEND_IMAGE=$(GHCR_REPO)/frontend:latest \
		$(DOCKER_COMPOSE) -f docker-compose.fullstack.yml up -d; \
	fi
	@echo "$(GREEN)✅ Full stack running in containers$(NC)"
	@echo "$(CYAN)💡 Services:$(NC)"
	@echo "  Frontend:  http://localhost:3000"
	@echo "  Backend:   http://localhost:8000"
	@echo "  MLFlow:    http://localhost:5001"
	@echo "$(CYAN)📋 Logs:$(NC) make dev-full-logs"
	@echo "$(CYAN)🛑 Stop:$(NC) make dev-full-stop"

dev-full-stop:
	@echo "$(CYAN)🛑 Stopping full containerized stack...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose.fullstack.yml down
	@if [ "$(IS_MAC_ARM)" = "yes" ]; then \
		echo "$(YELLOW)💡 Stopping infrastructure containers (ARM64 hybrid mode)...$(NC)"; \
		$(MAKE) local-dev-stop; \
	fi
	@echo "$(GREEN)✅ Full stack stopped$(NC)"

dev-full-restart: dev-full-stop dev-full-start

dev-full-logs:
	@$(DOCKER_COMPOSE) -f docker-compose.fullstack.yml logs -f

dev-full-status:
	@echo "$(CYAN)📊 Full Stack Status$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose.fullstack.yml ps

dev-full-build-multiarch:
	@echo "$(CYAN)🔨 Building full stack (native + AMD64)...$(NC)"
	@echo "$(YELLOW)⚠️  Slower build - includes cross-compilation for deployment$(NC)"
	$(MAKE) build-backend
	$(MAKE) build-multiarch-backend
	$(MAKE) build-frontend
	$(MAKE) build-multiarch-frontend
	@echo "$(GREEN)✅ Multi-arch images built (native + AMD64)$(NC)"

# ============================================================================
# PUSH & DEPLOY (Workflow 4)
# ============================================================================
# Push images to GHCR and deploy workflows
# ============================================================================

push-backend:
	@echo "$(CYAN)📤 Pushing backend to GHCR...$(NC)"
	@if [ -z "$(GHCR_TOKEN)" ] || [ -z "$(GHCR_USER)" ]; then \
		echo "$(RED)❌ GHCR_TOKEN and GHCR_USER must be set$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Logging in to GHCR...$(NC)"
	@echo "$(GHCR_TOKEN)" | $(CONTAINER_CLI) login ghcr.io -u $(GHCR_USER) --password-stdin
	@$(CONTAINER_CLI) push $(GHCR_REPO)/backend:$(PROJECT_VERSION)
	@$(CONTAINER_CLI) push $(GHCR_REPO)/backend:latest
	@echo "$(GREEN)✅ Backend pushed to GHCR$(NC)"

push-frontend:
	@echo "$(CYAN)📤 Pushing frontend to GHCR...$(NC)"
	@if [ -z "$(GHCR_TOKEN)" ] || [ -z "$(GHCR_USER)" ]; then \
		echo "$(RED)❌ GHCR_TOKEN and GHCR_USER must be set$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Logging in to GHCR...$(NC)"
	@echo "$(GHCR_TOKEN)" | $(CONTAINER_CLI) login ghcr.io -u $(GHCR_USER) --password-stdin
	@$(CONTAINER_CLI) push $(GHCR_REPO)/frontend:$(PROJECT_VERSION)
	@$(CONTAINER_CLI) push $(GHCR_REPO)/frontend:latest
	@echo "$(GREEN)✅ Frontend pushed to GHCR$(NC)"

push-all: push-backend push-frontend
	@echo "$(GREEN)✅ All images pushed to GHCR$(NC)"

# Combined build + push workflows
build-push-backend: build-backend push-backend
	@echo "$(GREEN)✅ Backend built and pushed$(NC)"

build-push-frontend: build-frontend push-frontend
	@echo "$(GREEN)✅ Frontend built and pushed$(NC)"

build-push-all: build-all push-all
	@echo "$(GREEN)✅ All images built and pushed$(NC)"

# Cloud build + push workflows (AMD64 for deployment)
build-cloud-push-backend: build-cloud-backend push-backend
	@echo "$(GREEN)✅ AMD64 backend built and pushed to GHCR$(NC)"
	@echo "$(CYAN)💡 Ready to deploy: make deploy-roks-app$(NC)"

build-cloud-push-frontend: build-cloud-frontend push-frontend
	@echo "$(GREEN)✅ AMD64 frontend built and pushed to GHCR$(NC)"
	@echo "$(CYAN)💡 Ready to deploy: make deploy-roks-app$(NC)"

build-cloud-push-all: build-cloud-all push-all
	@echo "$(GREEN)✅ AMD64 images built and pushed to GHCR$(NC)"
	@echo "$(CYAN)💡 Ready to deploy to any cloud:$(NC)"
	@echo "  - ROKS:   make deploy-roks-app"
	@echo "  - EKS:    make deploy-eks-app  (coming soon)"
	@echo "  - AKS:    make deploy-aks-app  (coming soon)"
	@echo "  - GKE:    make deploy-gke-app  (coming soon)"

# Backward compatibility (deprecated)
build-multiarch-push-backend: build-cloud-push-backend
	@echo "$(YELLOW)⚠️  DEPRECATED: Use 'make build-cloud-push-backend' instead$(NC)"

build-multiarch-push-frontend: build-cloud-push-frontend
	@echo "$(YELLOW)⚠️  DEPRECATED: Use 'make build-cloud-push-frontend' instead$(NC)"

build-multiarch-push-all: build-cloud-push-all
	@echo "$(YELLOW)⚠️  DEPRECATED: Use 'make build-cloud-push-all' instead$(NC)"

# Deploy workflows
deploy-pull-images:
	@echo "$(CYAN)📥 Pulling images from GHCR...$(NC)"
	@if [ -z "$(GHCR_TOKEN)" ] || [ -z "$(GHCR_USER)" ]; then \
		echo "$(RED)❌ GHCR_TOKEN and GHCR_USER must be set$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Logging in to GHCR...$(NC)"
	@echo "$(GHCR_TOKEN)" | $(CONTAINER_CLI) login ghcr.io -u $(GHCR_USER) --password-stdin
	@$(CONTAINER_CLI) pull $(GHCR_REPO)/backend:latest
	@$(CONTAINER_CLI) pull $(GHCR_REPO)/frontend:latest
	@echo "$(GREEN)✅ Images pulled from GHCR$(NC)"

deploy-remote: deploy-pull-images
	@echo "$(CYAN)🚀 Deploying pulled images...$(NC)"
	@BACKEND_IMAGE=$(GHCR_REPO)/backend:latest \
	 FRONTEND_IMAGE=$(GHCR_REPO)/frontend:latest \
	 $(MAKE) dev-full-start
	@echo "$(GREEN)✅ Deployment complete$(NC)"

# ============================================================================
# CLOUD-AGNOSTIC DEPLOYMENT SYSTEM (Issue #647)
# ============================================================================
# Configuration variables (can be overridden)
# Usage: make deploy-roks-app TARGET_ENV=dev
#        make k8s-deploy-app CLOUD=ibm TARGET_ENV=staging
CLOUD ?= ibm                      # ibm|aws|azure|gcp
PLATFORM ?= kubernetes             # kubernetes|serverless
TARGET_ENV ?= dev                 # dev|staging|prod
DEPLOY_REGION ?= us-south         # Cloud-specific region
HELM_TIMEOUT ?= 10m               # Helm deployment timeout

# Cloud-specific configuration
ifeq ($(CLOUD),ibm)
  TF_DIR := deployment/terraform/environments/ibm
  K8S_PLATFORM := roks
  SERVERLESS_PLATFORM := code-engine
endif
# Add AWS, Azure, GCP configurations as needed (Phase 2-3 of Issue #647)

## Kubernetes - App-Only Deployment (Cloud-Agnostic)
# Deploys applications to any Kubernetes cluster using Helm
# Automatically configures for ROKS (Routes) or vanilla K8s (Ingress)
k8s-deploy-app:
	@echo "$(CYAN)🚀 Deploying apps to $(CLOUD) $(K8S_PLATFORM) ($(TARGET_ENV))...$(NC)"
	@echo "$(YELLOW)💡 Using Helm for cloud-agnostic deployment$(NC)"
	@if ! command -v helm &> /dev/null; then \
		echo "$(RED)❌ Helm not found. Install: brew install helm$(NC)"; \
		exit 1; \
	fi
	@if ! command -v kubectl &> /dev/null; then \
		echo "$(RED)❌ kubectl not found. Install: brew install kubectl$(NC)"; \
		exit 1; \
	fi
	@echo "$(CYAN)📦 Deploying RAG Modulo v$(PROJECT_VERSION)...$(NC)"
	@helm upgrade --install rag-modulo deployment/helm/rag-modulo/ \
		--namespace rag-modulo \
		--create-namespace \
		--set image.backend.repository=$(GHCR_REPO)/backend \
		--set image.backend.tag=$(PROJECT_VERSION) \
		--set image.frontend.repository=$(GHCR_REPO)/frontend \
		--set image.frontend.tag=$(PROJECT_VERSION) \
		--set ingress.route.enabled=$(shell [ "$(K8S_PLATFORM)" = "roks" ] && echo "true" || echo "false") \
		--set ingress.kubernetes.enabled=$(shell [ "$(K8S_PLATFORM)" != "roks" ] && echo "true" || echo "false") \
		--timeout $(HELM_TIMEOUT) \
		--wait
	@echo "$(GREEN)✅ Apps deployed successfully$(NC)"
	@echo "$(CYAN)📊 Checking deployment status...$(NC)"
	@$(MAKE) k8s-status

## Kubernetes - Status & Monitoring
k8s-status:
	@echo "$(CYAN)📊 Deployment Status (namespace: rag-modulo)$(NC)"
	@echo ""
	@echo "$(CYAN)Pods:$(NC)"
	@kubectl get pods -n rag-modulo -o wide || echo "$(YELLOW)⚠️  No pods found. Is the cluster accessible?$(NC)"
	@echo ""
	@echo "$(CYAN)Services:$(NC)"
	@kubectl get svc -n rag-modulo || true
	@echo ""
	@echo "$(CYAN)Endpoints:$(NC)"
	@kubectl get routes -n rag-modulo 2>/dev/null || kubectl get ingress -n rag-modulo 2>/dev/null || echo "$(YELLOW)⚠️  No routes/ingress found$(NC)"

k8s-logs:
	@echo "$(CYAN)📜 Tailing backend logs (last 50 lines)...$(NC)"
	@echo "$(YELLOW)💡 Press Ctrl+C to stop$(NC)"
	@kubectl logs -f -n rag-modulo -l app=backend --tail=50 || \
		echo "$(RED)❌ Failed to get logs. Check if pods are running: make k8s-status$(NC)"

k8s-delete:
	@echo "$(RED)🗑️  Deleting RAG Modulo from Kubernetes...$(NC)"
	@read -p "Are you sure? This will remove all apps (infrastructure stays). (yes/no): " confirm && \
		[ "$$confirm" = "yes" ] || (echo "Cancelled" && exit 1)
	@helm uninstall rag-modulo -n rag-modulo || echo "$(YELLOW)⚠️  Helm release not found$(NC)"
	@kubectl delete namespace rag-modulo --wait || echo "$(YELLOW)⚠️  Namespace not found$(NC)"
	@echo "$(GREEN)✅ Apps deleted$(NC)"

## IBM Cloud - ROKS Shortcuts
deploy-roks-app:
	@echo "$(CYAN)🚀 IBM ROKS - App Deployment (Quick Update)$(NC)"
	@echo "$(YELLOW)Prerequisites:$(NC)"
	@echo "  1. ROKS cluster is running (provisioned via Terraform or IBM Cloud Console)"
	@echo "  2. kubectl configured to access cluster (ibmcloud ks cluster config)"
	@echo "  3. Images pushed to GHCR (make build-multiarch-push-all)"
	@echo ""
	@$(MAKE) k8s-deploy-app CLOUD=ibm PLATFORM=kubernetes TARGET_ENV=$(TARGET_ENV)
	@echo ""
	@echo "$(GREEN)✅ ROKS deployment complete!$(NC)"
	@echo "$(CYAN)💡 Next steps:$(NC)"
	@echo "  - View status:  make k8s-status"
	@echo "  - View logs:    make k8s-logs"
	@echo "  - Get routes:   kubectl get routes -n rag-modulo"

deploy-roks-full:
	@echo "$(CYAN)🚀 IBM ROKS - Full Deployment (Infrastructure + Apps)$(NC)"
	@echo "$(RED)⚠️  Not implemented yet - see Issue #647 Phase 1$(NC)"
	@echo "$(YELLOW)For now:$(NC)"
	@echo "  1. Provision ROKS cluster via IBM Cloud Console or Terraform"
	@echo "  2. Configure kubectl: ibmcloud ks cluster config --cluster <cluster-name>"
	@echo "  3. Deploy apps: make deploy-roks-app"
	@exit 1

# ============================================================================
# TESTING
# ============================================================================
# Test Strategy:
# - test-atomic: Fast schema/data structure tests (local, no DB, no coverage)
# - test-unit-fast: Unit tests with mocked dependencies (local, no containers)
# - test-integration: Integration tests with real services (Docker containers)
# - test-all: Runs all test categories in sequence
# ============================================================================

test-atomic: venv
	@echo "$(CYAN)⚡ Running atomic tests (no DB, no coverage)...$(NC)"
	@$(POETRY) run pytest -c pytest-atomic.ini tests/unit/schemas/ -v -m atomic
	@echo "$(GREEN)✅ Atomic tests passed$(NC)"

test-unit-fast: venv
	@echo "$(CYAN)🏃 Running unit tests (mocked dependencies)...$(NC)"
	@$(POETRY) run pytest tests/unit/ -v
	@echo "$(GREEN)✅ Unit tests passed$(NC)"

test-integration: venv local-dev-infra
	@echo "$(CYAN)🔗 Running integration tests (with real services)...$(NC)"
	@echo "$(YELLOW)💡 Using shared dev infrastructure (fast, reuses containers)$(NC)"
	@$(POETRY) run pytest tests/integration/ -v -m integration
	@echo "$(GREEN)✅ Integration tests passed$(NC)"

test-integration-ci: venv
	@echo "$(CYAN)🔗 Running integration tests in CI mode (isolated)...$(NC)"
	@echo "$(YELLOW)🏗️  Starting isolated test infrastructure...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose-ci.yml up -d --wait
	@echo "$(CYAN)🧪 Running tests with isolated services...$(NC)"
	@COLLECTIONDB_PORT=5433 MILVUS_PORT=19531 \
		cd backend && poetry run pytest ../tests/integration/ -v -m integration || \
		($(DOCKER_COMPOSE) -f docker-compose-ci.yml down -v && exit 1)
	@echo "$(CYAN)🧹 Cleaning up test infrastructure...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose-ci.yml down -v
	@echo "$(GREEN)✅ CI integration tests passed$(NC)"

test-integration-parallel: venv local-dev-infra
	@echo "$(CYAN)🔗 Running integration tests in parallel...$(NC)"
	@echo "$(YELLOW)⚡ Using pytest-xdist for parallel execution$(NC)"
	@cd backend && poetry run pytest ../tests/integration/ -v -m integration -n auto
	@echo "$(GREEN)✅ Parallel integration tests passed$(NC)"

test-e2e: venv local-dev-infra
	@echo "$(CYAN)🌐 Running end-to-end tests (full system)...$(NC)"
	@echo "$(YELLOW)💡 Using shared dev infrastructure (fast, reuses containers)$(NC)"
	@echo "$(YELLOW)💡 Using TestClient (in-memory, no backend required)$(NC)"
	# Port 5432 is used by the postgres container in docker-compose-infra.yml
	@cd backend && SKIP_AUTH=true COLLECTIONDB_HOST=localhost MILVUS_HOST=localhost \
		env > env_dump.txt && cat env_dump.txt && \
		poetry run pytest ../tests/e2e/ -v -m e2e
	@echo "$(GREEN)✅ E2E tests passed$(NC)"

test-e2e-ci: venv
	@echo "$(CYAN)🌐 Running E2E tests in CI mode (isolated, with backend)...$(NC)"
	@echo "$(YELLOW)🏗️  Starting isolated test infrastructure + backend...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose-e2e.yml up -d --wait
	@echo "$(CYAN)🧪 Running E2E tests with isolated services...$(NC)"
	@SKIP_AUTH=true E2E_MODE=ci COLLECTIONDB_PORT=5434 COLLECTIONDB_HOST=localhost MILVUS_PORT=19532 MILVUS_HOST=milvus-e2e LLM_PROVIDER=watsonx \
		cd backend && poetry run pytest ../tests/e2e/ -v -m e2e || \
		($(DOCKER_COMPOSE) -f docker-compose-e2e.yml down -v && exit 1)
	@echo "$(CYAN)🧹 Cleaning up E2E infrastructure...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose-e2e.yml down -v
	@echo "$(GREEN)✅ CI E2E tests passed$(NC)"

test-e2e-ci-parallel: venv
	@echo "$(CYAN)🌐 Running E2E tests in CI mode (isolated, with backend) in parallel...$(NC)"
	@echo "$(YELLOW)🏗️  Starting isolated test infrastructure + backend...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose-e2e.yml up -d --wait
	@echo "$(CYAN)🧪 Running E2E tests with isolated services in parallel...$(NC)"
	@SKIP_AUTH=true E2E_MODE=ci COLLECTIONDB_PORT=5434 COLLECTIONDB_HOST=localhost MILVUS_PORT=19532 MILVUS_HOST=milvus-e2e LLM_PROVIDER=watsonx \
		cd backend && poetry run pytest ../tests/e2e/ -v -m e2e -n auto || \
		($(DOCKER_COMPOSE) -f docker-compose-e2e.yml down -v && exit 1)
	@echo "$(CYAN)🧹 Cleaning up E2E infrastructure...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose-e2e.yml down -v
	@echo "$(GREEN)✅ CI E2E tests passed in parallel$(NC)"

test-e2e-local-parallel: venv local-dev-infra
	@echo "$(CYAN)🌐 Running E2E tests in parallel (local TestClient)...$(NC)"
	@echo "$(YELLOW)⚡ Using pytest-xdist for parallel execution$(NC)"
	@echo "$(YELLOW)💡 Using TestClient (in-memory, no backend required)$(NC)"
	@SKIP_AUTH=true COLLECTIONDB_HOST=localhost MILVUS_HOST=localhost \
		cd backend && poetry run pytest ../tests/e2e/ -v -m e2e -n auto
	@echo "$(GREEN)✅ Parallel E2E tests passed (local TestClient)$(NC)"

test-all: test-atomic test-unit-fast test-integration test-e2e
	@echo "$(GREEN)✅ All tests passed$(NC)"

test-all-ci: test-atomic test-unit-fast test-integration-ci test-e2e-ci-parallel
	@echo "$(GREEN)✅ All CI tests passed$(NC)"

# ============================================================================
# CODE QUALITY
# ============================================================================

lint: venv
	@echo "$(CYAN)🔍 Running linters...$(NC)"
	@$(POETRY) run ruff check backend --config pyproject.toml
	@$(POETRY) run mypy backend --config-file pyproject.toml --ignore-missing-imports
	@echo "$(GREEN)✅ Linting passed$(NC)"

format: venv
	@echo "$(CYAN)🎨 Formatting code...$(NC)"
	@$(POETRY) run ruff format backend --config pyproject.toml
	@$(POETRY) run ruff check --fix backend --config pyproject.toml
	@echo "$(GREEN)✅ Code formatted$(NC)"

quick-check: venv
	@echo "$(CYAN)⚡ Running quick quality checks...$(NC)"
	@$(POETRY) run ruff format --check backend --config pyproject.toml
	@$(POETRY) run ruff check backend --config pyproject.toml
	@echo "$(GREEN)✅ Quick checks passed$(NC)"

security-check: venv
	@echo "$(CYAN)🔒 Running security checks...$(NC)"
	@$(POETRY) run bandit -r backend/rag_solution/ -ll || echo "$(YELLOW)⚠️  Security issues found$(NC)"
	# Note: Using deprecated 'check' instead of 'scan' because scan requires Safety CLI authentication.
	# TODO: Migrate to 'safety scan' with authentication when CI/CD authentication is configured.
	@$(POETRY) run safety check --file poetry.lock 2>&1 | grep -v -E "DEPRECATED|deprecated|highly encourage|unsupported|June 2024" || echo "$(YELLOW)⚠️  Vulnerabilities found$(NC)"
	@echo "$(GREEN)✅ Security scan complete$(NC)"

pre-commit-run: venv
	@echo "$(CYAN)🎯 Running pre-commit checks...$(NC)"
	@echo "$(CYAN)Step 1/4: Formatting code...$(NC)"
	@$(POETRY) run ruff format backend --config pyproject.toml
	@echo "$(GREEN)✅ Code formatted$(NC)"
	@echo ""
	@echo "$(CYAN)Step 2/4: Running ruff linter...$(NC)"
	@$(POETRY) run ruff check --fix backend --config pyproject.toml
	@echo "$(GREEN)✅ Ruff checks passed$(NC)"
	@echo ""
	@echo "$(CYAN)Step 3/4: Running mypy type checker...$(NC)"
	@$(POETRY) run mypy backend --config-file pyproject.toml --ignore-missing-imports
	@echo "$(GREEN)✅ Type checks passed$(NC)"
	@echo ""
	@echo "$(CYAN)Step 4/4: Running pylint...$(NC)"
	@$(POETRY) run pylint backend/rag_solution/ --rcfile=pyproject.toml || echo "$(YELLOW)⚠️  Pylint warnings found$(NC)"
	@echo ""
	@echo "$(GREEN)✅ Pre-commit checks complete!$(NC)"
	@echo "$(CYAN)💡 Tip: Always run this before committing$(NC)"

coverage: venv
	@echo "$(CYAN)📊 Running tests with coverage...$(NC)"
	@$(POETRY) run pytest tests/unit/ \
		--cov=backend/rag_solution \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=60 \
		-v
	@echo "$(GREEN)✅ Coverage report generated$(NC)"
	@echo "$(CYAN)💡 View report: open htmlcov/index.html$(NC)"

# ============================================================================
# PRODUCTION DEPLOYMENT
# ============================================================================

create-volumes:
	@echo "$(CYAN)📁 Creating volume directories...$(NC)"
	@mkdir -p ./volumes/postgres ./volumes/etcd ./volumes/minio ./volumes/milvus ./volumes/backend
	# Note: chmod 777 is for LOCAL DEVELOPMENT ONLY to avoid permission issues
	# For production deployments, use proper user/group mapping with Docker user namespaces
	# or run containers with specific UIDs/GIDs that match your infrastructure
	@find ./volumes -maxdepth 1 -type d -exec chmod 777 {} \; 2>/dev/null || true
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
	@rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

clean-all: clean local-dev-stop
	@echo "$(CYAN)🧹 Deep cleaning (containers, volumes, images)...$(NC)"
	@echo "$(RED)⚠️  WARNING: This will remove ALL Docker containers, volumes, and images!$(NC)"
	@echo "$(YELLOW)This is a DESTRUCTIVE operation that cannot be undone.$(NC)"
	@read -p "Are you sure you want to continue? (yes/no): " confirm && \
		if [ "$$confirm" = "yes" ]; then \
			docker system prune -af --volumes && \
			echo "$(GREEN)✅ Deep cleanup complete$(NC)"; \
		else \
			echo "$(YELLOW)Cleanup cancelled$(NC)"; \
			exit 1; \
		fi

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
	@echo "$(CYAN)║         RAG Modulo - Complete Workflow Guide                ║$(NC)"
	@echo "$(CYAN)╚══════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(CYAN)🚀 WORKFLOW 1: Local Development (Hot Reload - Fastest)$(NC)"
	@echo "  $(GREEN)make local-dev-setup$(NC)       Install dependencies"
	@echo "  $(GREEN)make local-dev-infra$(NC)       Start infrastructure only"
	@echo "  $(GREEN)make local-dev-backend$(NC)     Uvicorn hot reload (Terminal 1)"
	@echo "  $(GREEN)make local-dev-frontend$(NC)    Vite HMR (Terminal 2)"
	@echo "  $(GREEN)make local-dev-all$(NC)         Start all in background"
	@echo "  $(GREEN)make local-dev-status$(NC)      Check status"
	@echo "  $(GREEN)make local-dev-stop$(NC)        Stop all services"
	@echo ""
	@echo "$(CYAN)🐳 WORKFLOW 2: Full Containerized Stack (Production-like Testing)$(NC)"
	@echo "  $(GREEN)make dev-full-build$(NC)        Build images (native arch, fast)"
	@echo "  $(GREEN)make dev-full-start$(NC)        Start full stack in containers"
	@echo "  $(GREEN)make dev-full-stop$(NC)         Stop container stack"
	@echo "  $(GREEN)make dev-full-logs$(NC)         View container logs"
	@echo "  $(GREEN)make dev-full-status$(NC)       Check container status"
	@echo "  $(GREEN)make dev-full-build-multiarch$(NC)  Build native + AMD64 (slower)"
	@if [ "$(IS_MAC_ARM)" = "yes" ]; then \
		echo "  $(YELLOW)⚠️  ARM64 Mac: Use Workflow 1 for faster dev iteration$(NC)"; \
	fi
	@echo ""
	@echo "$(CYAN)🔨 WORKFLOW 3: Multi-Architecture Builds$(NC)"
	@echo "  $(GREEN)make build-all$(NC)             Build for native architecture"
	@echo "  $(GREEN)make build-multiarch-all$(NC)   Build AMD64 (for Linux deployment)"
	@echo "  $(GREEN)make build-amd64-all$(NC)       Explicitly build AMD64"
	@echo "  $(GREEN)make build-arm64-all$(NC)       Explicitly build ARM64"
	@echo ""
	@echo "$(CYAN)📤 WORKFLOW 4: Push & Deploy to GHCR$(NC)"
	@echo "  $(GREEN)make push-all$(NC)              Push images to GHCR"
	@echo "  $(GREEN)make build-push-all$(NC)        Build + push (native arch)"
	@echo "  $(GREEN)make build-multiarch-push-all$(NC)  Build AMD64 + push to GHCR"
	@echo "  $(GREEN)make deploy-pull-images$(NC)    Pull images from GHCR"
	@echo "  $(GREEN)make deploy-remote$(NC)         Pull + deploy locally"
	@echo "  $(YELLOW)💡 Requires: GHCR_TOKEN and GHCR_USER env vars$(NC)"
	@echo ""
	@echo "$(CYAN)🧪 Testing:$(NC)"
	@echo "  $(GREEN)make test-atomic$(NC)           Fast schema tests (no DB, ~5s)"
	@echo "  $(GREEN)make test-unit-fast$(NC)        Unit tests (~30s)"
	@echo "  $(GREEN)make test-integration$(NC)      Integration tests (~2min)"
	@echo "  $(GREEN)make test-e2e$(NC)              End-to-end tests (~5min)"
	@echo "  $(GREEN)make test-all$(NC)              Run all tests"
	@echo "  $(GREEN)make coverage$(NC)              Generate coverage report"
	@echo ""
	@echo "$(CYAN)🎨 Code Quality:$(NC)"
	@echo "  $(GREEN)make pre-commit-run$(NC)        All pre-commit checks"
	@echo "  $(GREEN)make quick-check$(NC)           Fast lint + format check"
	@echo "  $(GREEN)make lint$(NC)                  Ruff + MyPy"
	@echo "  $(GREEN)make format$(NC)                Auto-format code"
	@echo "  $(GREEN)make security-check$(NC)        Security scanning"
	@echo ""
	@echo "$(CYAN)🏭 Production:$(NC)"
	@echo "  $(GREEN)make prod-start$(NC)            Start production environment"
	@echo "  $(GREEN)make prod-stop$(NC)             Stop production"
	@echo "  $(GREEN)make prod-logs$(NC)             View production logs"
	@echo ""
	@echo "$(CYAN)💡 Common Workflows:$(NC)"
	@echo "  Daily dev:          $(GREEN)make local-dev-all$(NC) (hot reload, fastest)"
	@echo "  Container testing:  $(GREEN)make dev-full-start$(NC) (production-like)"
	@echo "  Mac → Linux deploy: $(GREEN)make build-multiarch-push-all$(NC)"
	@echo "  Pull & run:         $(GREEN)make deploy-remote$(NC)"
	@echo ""
	@echo "$(CYAN)📚 Documentation:$(NC)"
	@echo "  Full docs: https://manavgup.github.io/rag_modulo"
	@echo "  API docs:  http://localhost:8000/docs (when backend running)"
	@echo ""
