# Issue: Implement DevContainers for RAG Modulo Project

## Overview
Implement DevContainers to provide a consistent, isolated development environment for the RAG Modulo project. This will ensure all developers have the same setup regardless of their local machine configuration and simplify onboarding.

## Problem Statement
Currently, developers need to:
- Install Python 3.12, Node.js, and various system dependencies locally
- Set up Poetry, npm, and other package managers
- Configure multiple vector databases (Milvus, PostgreSQL, MinIO, etc.)
- Handle environment-specific issues and dependency conflicts
- Maintain consistent development environments across team members

## Proposed Solution
Implement DevContainers using VS Code's Dev Containers extension to provide:
- Pre-configured development environment with all dependencies
- Isolated containerized development space
- Consistent tooling and configurations
- Easy onboarding for new team members

## Implementation Details

### 1. DevContainer Configuration Structure
```
.devcontainer/
├── devcontainer.json          # Main DevContainer configuration
├── docker-compose.dev.yml     # Development-specific services
├── Dockerfile.dev             # Development container image
├── post-create.sh             # Post-creation setup script
├── post-start.sh              # Post-start setup script
└── scripts/
    ├── setup-python.sh        # Python environment setup
    ├── setup-node.sh          # Node.js environment setup
    └── setup-tools.sh         # Development tools setup
```

### 2. DevContainer Configuration (`devcontainer.json`)

```json
{
  "name": "RAG Modulo Development",
  "dockerComposeFile": "docker-compose.dev.yml",
  "service": "app",
  "workspaceFolder": "/workspace",
  
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.poetry",
        "ms-python.black-formatter",
        "ms-python.ruff",
        "ms-python.mypy",
        "ms-vscode.vscode-typescript-next",
        "bradlc.vscode-tailwindcss",
        "esbenp.prettier-vscode",
        "ms-vscode.vscode-json",
        "ms-vscode.vscode-yaml",
        "ms-azuretools.vscode-docker",
        "ms-vscode-remote.remote-containers"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python",
        "python.poetryPath": "/usr/local/bin/poetry",
        "python.linting.enabled": true,
        "python.linting.ruffEnabled": true,
        "python.formatting.provider": "black",
        "python.testing.pytestEnabled": true,
        "python.testing.pytestArgs": ["backend/tests"],
        "typescript.preferences.importModuleSpecifier": "relative",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
          "source.organizeImports": true
        }
      }
    }
  },
  
  "postCreateCommand": "bash .devcontainer/scripts/setup-python.sh && bash .devcontainer/scripts/setup-node.sh",
  "postStartCommand": "bash .devcontainer/scripts/setup-tools.sh",
  
  "forwardPorts": [8000, 3000, 5432, 19530, 9000, 5000],
  "portsAttributes": {
    "8000": {
      "label": "Backend API",
      "onAutoForward": "notify"
    },
    "3000": {
      "label": "Frontend Dev Server",
      "onAutoForward": "notify"
    },
    "5432": {
      "label": "PostgreSQL",
      "onAutoForward": "silent"
    },
    "19530": {
      "label": "Milvus",
      "onAutoForward": "silent"
    },
    "9000": {
      "label": "MinIO",
      "onAutoForward": "silent"
    },
    "5000": {
      "label": "MLflow",
      "onAutoForward": "silent"
    }
  },
  
  "remoteUser": "vscode",
  "mounts": [
    "source=${localWorkspaceFolder}/.gitconfig,target=/home/vscode/.gitconfig,type=bind,consistency=cached"
  ]
}
```

### 3. Development Docker Compose (`docker-compose.dev.yml`)

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: .devcontainer/Dockerfile.dev
    volumes:
      - ..:/workspace:cached
      - /workspace/backend/venv
      - /workspace/webui/node_modules
      - /workspace/.pytest_cache
      - /workspace/__pycache__
    command: sleep infinity
    environment:
      - PYTHONPATH=/workspace:/workspace/vectordbs:/workspace/rag_solution
      - POETRY_VENV_IN_PROJECT=true
      - NODE_ENV=development
    networks:
      - dev-network

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: rag_modulo_dev
      POSTGRES_USER: dev_user
      POSTGRES_PASSWORD: dev_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dev_user -d rag_modulo_dev"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - dev-network

  milvus-standalone:
    image: milvusdb/milvus:v2.4.0
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_USE_EMBED: "true"
      ETCD_DATA_DIR: /var/lib/milvus/etcd
      ETCD_CONFIG_PATH: /milvus/configs/etcd.yml
    volumes:
      - milvus_data:/var/lib/milvus
    ports:
      - "19530:19530"
      - "9091:9091"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - dev-network

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - dev-network

  mlflow:
    image: ghcr.io/mlflow/mlflow:latest
    command: mlflow server --host 0.0.0.0 --port 5000 --backend-store-uri sqlite:///mlflow.db --default-artifact-root s3://mlflow-bucket
    environment:
      - AWS_ACCESS_KEY_ID=minioadmin
      - AWS_SECRET_ACCESS_KEY=minioadmin
      - MLFLOW_S3_ENDPOINT_URL=http://minio:9000
    volumes:
      - mlflow_data:/mlflow
    ports:
      - "5000:5000"
    depends_on:
      minio:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - dev-network

volumes:
  postgres_data:
  milvus_data:
  minio_data:
  mlflow_data:

networks:
  dev-network:
    driver: bridge
```

### 4. Development Dockerfile (`Dockerfile.dev`)

```dockerfile
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    vim \
    nano \
    htop \
    tree \
    jq \
    unzip \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 18 LTS
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Install Poetry
RUN pip install poetry

# Install global npm packages
RUN npm install -g npm@latest

# Create non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Set working directory
WORKDIR /workspace

# Switch to non-root user
USER $USERNAME

# Configure Poetry
RUN poetry config virtualenvs.in-project true

# Set environment variables
ENV PYTHONPATH=/workspace:/workspace/vectordbs:/workspace/rag_solution
ENV POETRY_VENV_IN_PROJECT=true
ENV NODE_ENV=development
```

### 5. Setup Scripts

#### `setup-python.sh`
```bash
#!/bin/bash
set -e

echo "Setting up Python environment..."

# Install Python dependencies
cd /workspace/backend
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    poetry install --with dev,test
else
    echo "Virtual environment exists, updating dependencies..."
    poetry install --with dev,test
fi

# Install pre-commit hooks
poetry run pre-commit install

echo "Python environment setup complete!"
```

#### `setup-node.sh`
```bash
#!/bin/bash
set -e

echo "Setting up Node.js environment..."

# Install Node.js dependencies
cd /workspace/webui
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
else
    echo "Node modules exist, updating dependencies..."
    npm update
fi

echo "Node.js environment setup complete!"
```

#### `setup-tools.sh`
```bash
#!/bin/bash
set -e

echo "Setting up development tools..."

# Wait for services to be healthy
echo "Waiting for services to be ready..."
until curl -f http://localhost:5432 >/dev/null 2>&1; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done

until curl -f http://localhost:19530 >/dev/null 2>&1; do
    echo "Waiting for Milvus..."
    sleep 2
done

until curl -f http://localhost:9000 >/dev/null 2>&1; do
    echo "Waiting for MinIO..."
    sleep 2
done

until curl -f http://localhost:5000 >/dev/null 2>&1; do
    echo "Waiting for MLflow..."
    sleep 2
done

echo "All services are ready!"
```

## Benefits

1. **Consistent Environment**: All developers work in identical environments
2. **Easy Onboarding**: New team members can start coding immediately
3. **Isolation**: Development dependencies don't conflict with local system
4. **Reproducible**: Environment can be version controlled and shared
5. **Performance**: Containerized development with optimized tooling
6. **Debugging**: Integrated debugging and testing capabilities

## Implementation Steps

### Phase 1: Core DevContainer Setup
1. Create `.devcontainer/` directory structure
2. Implement basic `devcontainer.json` configuration
3. Create development Dockerfile
4. Set up basic development services (PostgreSQL, Milvus)

### Phase 2: Enhanced Development Environment
1. Add development tools and extensions
2. Implement setup scripts
3. Configure linting and formatting
4. Set up testing infrastructure

### Phase 3: Integration and Testing
1. Test DevContainer with existing codebase
2. Validate all services and dependencies
3. Document usage and troubleshooting
4. Team training and adoption

## Testing Requirements

- [ ] DevContainer builds successfully
- [ ] All development services start and are healthy
- [ ] Python and Node.js dependencies install correctly
- [ ] Development tools (Poetry, npm) work as expected
- [ ] VS Code extensions load properly
- [ ] Port forwarding works for all services
- [ ] Development workflow (build, test, run) functions correctly

## Documentation Requirements

- [ ] DevContainer setup guide
- [ ] Development workflow documentation
- [ ] Troubleshooting guide
- [ ] Team onboarding checklist
- [ ] Service configuration reference

## Acceptance Criteria

1. **Functional**: DevContainer provides fully functional development environment
2. **Performance**: Container startup time < 2 minutes
3. **Usability**: Developers can start coding within 5 minutes of opening project
4. **Reliability**: Environment works consistently across different host systems
5. **Maintainability**: Configuration is version controlled and easily updatable

## Dependencies

- VS Code Dev Containers extension
- Docker or Podman
- Docker Compose
- Sufficient system resources (8GB RAM, 20GB disk space recommended)

## Risk Assessment

- **Low Risk**: Standard DevContainer implementation with well-documented patterns
- **Mitigation**: Phased implementation with testing at each stage
- **Fallback**: Existing local development setup remains available

## Timeline

- **Week 1**: Core DevContainer setup and basic services
- **Week 2**: Development tools and environment configuration
- **Week 3**: Testing and validation
- **Week 4**: Documentation and team training

## Assignee
TBD - Backend/DevOps engineer with containerization experience

## Priority
High - Improves developer experience and reduces onboarding friction

## Labels
- `enhancement`
- `developer-experience`
- `devops`
- `documentation`
- `testing`
