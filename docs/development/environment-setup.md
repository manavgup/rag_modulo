# Development Environment Setup

This guide provides detailed instructions for setting up the RAG Modulo development environment.

## Prerequisites

### System Requirements

- **Operating System**: macOS 10.15+, Ubuntu 20.04+, or Windows 10+ with WSL2
- **RAM**: Minimum 8GB, recommended 16GB
- **Storage**: At least 10GB free space
- **CPU**: 4+ cores recommended for optimal performance

### Required Software

- **Docker**: Version 20.10+ with Docker Compose 2.0+
- **Make**: For running development commands
- **Git**: Version 2.30+ for version control
- **VS Code** (optional): For enhanced development experience

### Optional Tools

- **fswatch** (macOS): For file watching (`brew install fswatch`)
- **inotify-tools** (Linux): For file watching (`sudo apt-get install inotify-tools`)
- **GitHub CLI**: For repository management (`gh`)

## Installation Methods

### Method 1: One-Command Setup (Recommended)

```bash
# Clone repository
git clone https://github.com/manavgup/rag_modulo.git
cd rag_modulo

# Complete setup in one command
make dev-setup
```

This command will:
- Initialize development environment variables
- Build all development images
- Start the development environment
- Validate everything is working
- Provide next steps

### Method 2: Step-by-Step Setup

#### 1. Clone Repository

```bash
git clone https://github.com/manavgup/rag_modulo.git
cd rag_modulo
```

#### 2. Initialize Environment

```bash
# Create development environment files
make dev-init

# This creates:
# - .env.dev (development environment variables)
# - .env (production environment variables)
```

#### 3. Configure Environment Variables

Edit `.env.dev` with your development credentials:

```bash
# Development Environment Configuration
TESTING=true
SKIP_AUTH=true
DEVELOPMENT_MODE=true
RUNTIME_EVAL=false

# Development-specific JWT Secret
JWT_SECRET_KEY=dev-jwt-secret-key-for-local-development-only

# IBM WatsonX Credentials (required)
WATSONX_INSTANCE_ID=your-dev-watsonx-instance-id
WATSONX_APIKEY=your-dev-watsonx-apikey
WATSONX_URL=https://us-south.ml.cloud.ibm.com

# Development OIDC Configuration
OIDC_DISCOVERY_ENDPOINT=http://localhost:8080/.well-known/openid_configuration
OIDC_AUTH_URL=http://localhost:8080/auth
OIDC_TOKEN_URL=http://localhost:8080/token
FRONTEND_URL=http://localhost:3000
```

#### 4. Build Development Images

```bash
# Build all development images
make dev-build

# Or build specific components
make build-backend-local
make build-frontend-local
make build-tests-local
```

#### 5. Start Development Environment

```bash
# Start all services
make dev-up

# Verify everything is running
make dev-status
```

#### 6. Validate Setup

```bash
# Run comprehensive validation
make dev-validate

# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:3000
```

## Development Environment Features

### Hot Reloading

The development environment supports hot reloading for both backend and frontend:

- **Backend**: Source code is mounted, changes reflect immediately
- **Frontend**: Development server with hot module replacement
- **Configuration**: Environment variables can be changed without rebuild

### File Watching

Automatically rebuild and restart when files change:

```bash
# Start file watcher
make dev-watch

# Watches for changes in:
# - backend/ directory (Python files)
# - webui/ directory (JavaScript/React files)
```

### Debug Mode

Enhanced debugging capabilities:

```bash
# Start in debug mode
make dev-debug

# Features:
# - Additional logging (DEBUG=true, LOG_LEVEL=DEBUG)
# - Debug shell access
# - Enhanced error reporting
# - Debug logs available
```

### Test Mode

Isolated test environment:

```bash
# Start in test mode
make dev-test

# Features:
# - Isolated test environment (.env.test)
# - Test-specific database configuration
# - Mock data and test fixtures
# - Test mode flags enabled
```

### Profiling Mode

Performance monitoring:

```bash
# Start in profiling mode
make dev-profile

# Features:
# - Performance monitoring enabled
# - Metrics collection
# - Performance data at http://localhost:8000/metrics
# - Profiling data in ./logs/profiling/
```

## VS Code Development Container

### Setup

The project includes a complete VS Code dev container configuration:

```bash
# Open in VS Code
code .

# Click "Reopen in Container" when prompted
# Wait for container to build and start
```

### Features

- **Pre-configured extensions**: Python, Ruff, Docker, GitHub Copilot, Jupyter
- **Automatic port forwarding**: Backend (8000), Frontend (3000), MLflow (5001)
- **Development environment**: All tools pre-installed
- **Debugging support**: Ready-to-use debug configurations
- **File watching**: Optimized for development workflow

### Configuration

The dev container configuration (`.devcontainer/devcontainer.json`) includes:

```json
{
  "name": "RAG Modulo Development",
  "dockerComposeFile": "../docker-compose.dev.yml",
  "service": "backend",
  "workspaceFolder": "/app",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "charliermarsh.ruff",
        "ms-azuretools.vscode-docker"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python",
        "python.linting.enabled": true,
        "python.linting.ruffEnabled": true,
        "python.formatting.provider": "none",
        "python.formatting.ruffEnabled": true
      }
    }
  }
}
```

## Environment Management

### Development Environment Reset

```bash
# Reset to clean state
make dev-reset

# This will:
# - Stop all containers
# - Clean Docker volumes
# - Clean build cache
# - Restart development environment
```

### Complete Cleanup

```bash
# Complete cleanup (destructive)
make clean-all

# This will:
# - Remove all containers
# - Remove all volumes
# - Remove all images
# - Remove build cache
# - Clean local files
```

### Environment Validation

```bash
# Validate development environment
make dev-validate

# Checks:
# - Development images exist
# - Containers are running
# - Backend health
# - Frontend health
```

## Troubleshooting

### Common Issues

#### Docker Not Running

```bash
# Start Docker Desktop
# On macOS: Open Docker Desktop application
# On Linux: sudo systemctl start docker
# On Windows: Start Docker Desktop

# Verify Docker is running
docker --version
docker compose --version
```

#### Port Conflicts

```bash
# Check what's using ports
lsof -i :8000  # Backend port
lsof -i :3000  # Frontend port
lsof -i :5001  # MLflow port

# Stop conflicting services
make dev-down
```

#### Permission Issues

```bash
# Fix Docker permissions (Linux)
sudo usermod -aG docker $USER
# Log out and log back in

# Fix volume permissions
sudo chown -R $USER:$USER volumes/
```

#### Build Failures

```bash
# Clean build cache
docker builder prune -f

# Rebuild from scratch
make clean-all
make dev-build
```

#### Environment Variable Issues

```bash
# Check environment variables
docker compose -f docker-compose.dev.yml config

# Verify .env.dev file
cat .env.dev

# Restart with new environment
make dev-restart
```

### Getting Help

- **Check logs**: `make dev-logs`
- **Validate setup**: `make dev-validate`
- **Reset environment**: `make dev-reset`
- **Create issue**: GitHub Issues
- **Ask questions**: GitHub Discussions

## Next Steps

After setting up your development environment:

1. **Read the [Development Workflow](../DEVELOPMENT_WORKFLOW.md)**
2. **Explore the [CLI Documentation](../cli/README.md)**
3. **Check out the [API Documentation](../api/README.md)**
4. **Start contributing**: [Contributing Guidelines](contributing.md)
