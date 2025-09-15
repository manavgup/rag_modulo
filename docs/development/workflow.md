# Development Workflow Guide

This guide explains the streamlined development workflow implemented to solve **Issue #210: Docker Development Workflow Problem**.

## Problem Solved

Previously, developers faced these issues:
- Code changes weren't reflected in running containers
- Docker Compose defaulted to remote GHCR images instead of local builds
- Manual intervention required to force local image usage
- Inconsistent environment variables between development and production
- Multiple manual steps: build → recreate → restart

## Solution Overview

The new development workflow provides:
- **Development-first Docker Compose** (`docker-compose.dev.yml`)
- **Smart Make targets** for automated workflow
- **Development-specific environment** (`.env.dev`)
- **Automatic local image building** and usage
- **Validation commands** to ensure local changes are running

## Quick Start

### Option 1: Dev Container + Host Docker (Recommended)

**For consistent development environments across machines:**

1. **Open in Dev Container**:
   ```bash
   # In VS Code Command Palette
   Cmd/Ctrl+Shift+P → "Dev Containers: Reopen in Container"
   ```

2. **Use Dev Container for**:
   - Code editing
   - Python development
   - VS Code extensions
   - Development tools (make, git, etc.)

3. **Use Host Terminal for**:
   - Docker commands
   - Container management
   - Service orchestration

### Option 2: Host Development

**For direct development on host machine:**

### 1. Initialize Development Environment
```bash
make dev-init
```
This creates `.env.dev` from `env.dev.example` with development-specific settings.

### 2. Build Development Images
```bash
make dev-build
```
Builds local images with `dev` tags for backend, frontend, and test containers.

### 3. Start Development Environment
```bash
make dev-up
```
Starts all services using local builds with development environment variables.

### 4. Validate Everything is Working
```bash
make dev-validate
```
Checks that development images exist, containers are running, and services are healthy.

## Development Workflow Commands

### Core Commands

| Command | Description |
|---------|-------------|
| `make dev-init` | Initialize development environment (.env.dev) |
| `make dev-build` | Build local development images |
| `make dev-up` | Start development environment with local builds |
| `make dev-restart` | Rebuild and restart with latest changes |
| `make dev-down` | Stop development environment |
| `make dev-logs` | View development environment logs |
| `make dev-status` | Show development environment status |
| `make dev-validate` | Validate development environment health |

### Typical Development Cycle

1. **Make code changes** in your editor
2. **Restart with changes**: `make dev-restart`
3. **Check status**: `make dev-status`
4. **View logs if needed**: `make dev-logs`
5. **Validate health**: `make dev-validate`

## Architecture

### Development Docker Compose (`docker-compose.dev.yml`)

Key features:
- **Local builds by default** (no GHCR images)
- **Development environment variables** (`TESTING=true`, `SKIP_AUTH=true`, `DEVELOPMENT_MODE=true`)
- **Source code mounting** for hot reloading (`./backend:/app:ro`)
- **Writable logs directory** (`./logs:/app/logs`)
- **Consistent image tags** (`rag-modulo/backend:dev`, `rag-modulo/frontend:dev`)

### Development Environment (`.env.dev`)

Contains development-specific settings:
- Development mode flags
- Development JWT secret
- Development WatsonX credentials
- Development database configuration
- Development-specific chunking settings

### Smart Make Targets

The Makefile includes comprehensive development targets:
- **Automated building** with BuildKit support
- **Environment validation** 
- **Health checking**
- **Status reporting**
- **Log viewing**

## Service URLs

When running, services are available at:
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000  
- **MLflow**: http://localhost:5001

## Environment Variables

### Development Mode Flags
```bash
TESTING=true
SKIP_AUTH=true
DEVELOPMENT_MODE=true
RUNTIME_EVAL=false
```

### Development Credentials
```bash
JWT_SECRET_KEY=dev-jwt-secret-key-for-local-development-only
WATSONX_APIKEY=your-dev-watsonx-apikey
WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

## Troubleshooting

### Common Issues

#### 1. Containers Not Starting
```bash
# Check logs
make dev-logs

# Validate environment
make dev-validate

# Restart everything
make dev-down && make dev-up
```

#### 2. Images Not Found
```bash
# Rebuild images
make dev-build

# Check image status
make dev-status
```

#### 3. Environment Variables Not Loading
```bash
# Reinitialize environment
make dev-init

# Check .env.dev file exists and has correct values
ls -la .env*
```

#### 4. Backend Health Check Failing
```bash
# Check backend logs specifically
docker compose -f docker-compose.dev.yml logs backend

# Restart backend only
docker compose -f docker-compose.dev.yml restart backend
```

### Validation Checklist

Run `make dev-validate` to check:
- ✅ Development images exist
- ✅ Containers are running
- ✅ Backend is healthy (http://localhost:8000/health)
- ✅ Frontend is healthy (http://localhost:3000)

## Comparison: Old vs New Workflow

### Old Workflow (Problematic)
```bash
# Multiple manual steps
make build-backend
docker compose down
docker compose up -d
# Often used remote images instead of local builds
# Environment variables had to be set manually
# No validation that local changes were running
```

### New Workflow (Streamlined)
```bash
# Single command for full cycle
make dev-restart

# Or step by step
make dev-build    # Build local images
make dev-up       # Start with local builds
make dev-validate # Confirm everything works
```

## Benefits

### Developer Experience
- **Faster iteration**: Changes visible immediately
- **Fewer manual steps**: Automated workflow
- **Clear feedback**: Know when local changes are active
- **Consistent environment**: Same dev setup for all developers

### Reduced Errors
- **No more old code**: Always running latest changes
- **Consistent env vars**: Development settings always applied
- **Clear state**: Know which image/configuration is running

### Team Productivity
- **Onboarding**: New developers can start quickly
- **Debugging**: Easier to reproduce and fix issues
- **Testing**: Faster validation of changes

## Integration with Existing Workflow

The development workflow integrates seamlessly with existing commands:

- **Production builds**: `make build-backend` (unchanged)
- **Production deployment**: `make run-ghcr` (unchanged)
- **Testing**: All existing test commands work with development environment
- **CI/CD**: Production pipeline unchanged

## Security Considerations

- **Development settings don't leak to production**
- **Clear separation** between dev and prod configurations
- **Development JWT secrets** are different from production
- **Development credentials** are isolated

## Performance

- **Development builds are fast** (uses Docker layer caching)
- **Multi-stage builds** optimized for development
- **Hot reloading** for frontend changes
- **Source code mounting** for backend changes

## Maintenance

- **Keep development workflow simple**
- **Regular validation** that dev workflow works
- **Clear documentation** and examples
- **Automated health checks**

## Enhanced Developer Experience (Issue #170 Integration)

### Complete Development Setup

```bash
make dev-setup
```

One-command setup for new feature development that:
- ✅ Initializes development environment
- ✅ Builds all local images
- ✅ Starts development environment
- ✅ Validates everything is working
- ✅ Provides clear next steps

### Development Environment Management

```bash
# Reset to clean state (useful when things get messy)
make dev-reset

# Complete cleanup (destructive - removes all data)
make clean-all
```

### Test-Driven Development

```bash
# Run tests automatically when test files change
make test-watch
```

Watches `backend/tests/` directory and runs atomic tests automatically on file changes.

### VS Code Dev Container

The project includes a complete VS Code dev container configuration (`.devcontainer/devcontainer.json`) with:

- ✅ **Pre-configured extensions**: Python, Ruff, Docker, GitHub Copilot, Jupyter
- ✅ **Automatic port forwarding**: Backend (8000), Frontend (3000), MLflow (5001)
- ✅ **Development environment**: All tools pre-installed
- ✅ **Debugging support**: Ready-to-use debug configurations
- ✅ **File watching**: Optimized for development workflow

**To use:**
1. Open project in VS Code
2. Click "Reopen in Container" when prompted
3. Wait for container to build and start
4. Start coding!

### GitHub Codespaces Support

The project fully supports GitHub Codespaces for cloud-based development:

- ✅ **Consistent environment**: Same Dev Container configuration as local
- ✅ **Zero local setup**: Just a web browser required
- ✅ **Cross-platform**: Works on any device (Windows, Mac, Linux, Chromebook)
- ✅ **Team collaboration**: Share Codespaces for pair programming
- ✅ **Hot reloading**: Same development experience as local

**To use Codespaces:**
1. Go to GitHub repository → "Code" → "Codespaces"
2. Click "Create codespace on main" (or your branch)
3. Wait for environment to load (2-3 minutes)
4. Start coding in browser-based VS Code!

**See [GitHub Codespaces Guide](codespaces.md) for complete details.**

### Automated PR Validation

The project includes automated GitHub Actions workflows for PR validation:

#### PR Codespace Creation
- ✅ **Automatic Codespace**: Creates Codespace for each PR
- ✅ **PR Comments**: Automatically comments with Codespace URL
- ✅ **Environment Validation**: Ensures Dev Container works
- ✅ **Quick Testing**: Enables immediate testing of PR changes

#### Codespace Testing Workflow
- ✅ **Automated Testing**: Runs tests in Codespace environment
- ✅ **Hot Reloading Validation**: Tests file change detection
- ✅ **CLI Testing**: Validates all CLI commands work
- ✅ **Service Validation**: Ensures all services start correctly

#### Environment Validation
- ✅ **Dev Container Validation**: Ensures configuration works
- ✅ **Tool Availability**: Verifies all development tools installed
- ✅ **Extension Validation**: Confirms VS Code extensions work
- ✅ **Workflow Commands**: Tests all `make` targets

**Workflow Files:**
- `.github/workflows/pr-codespace.yml` - PR Codespace creation
- `.github/workflows/codespace-testing.yml` - Automated testing
- `.github/workflows/codespace-validation.yml` - Environment validation

## Related Issues

This implementation addresses:
- **Issue #210**: Docker Development Workflow Problem
- **Issue #170**: Developer Experience Improvements (integrated above)
- **Issue #208**: Mock user initialization (benefits from streamlined workflow)
- **Issue #207**: Search quality issues (faster iteration helps debugging)

## Phase 2: Enhanced Development Experience

### Auto-rebuild on Changes (File Watchers)

```bash
make dev-watch
```

Automatically rebuilds and restarts the development environment when files change in `backend/` or `webui/` directories.

**Requirements:**
- **macOS**: `brew install fswatch`
- **Linux**: `sudo apt-get install inotify-tools`

**Features:**
- ✅ Watches for file changes in backend and frontend
- ✅ Automatically triggers `make dev-restart` on changes
- ✅ Cross-platform support (macOS/Linux)
- ✅ Graceful error handling if watcher not available

## Phase 3: Advanced Features

### Debug Mode

```bash
make dev-debug
```

Starts the development environment with enhanced debugging capabilities.

**Features:**
- ✅ Additional logging enabled (`DEBUG=true`, `LOG_LEVEL=DEBUG`)
- ✅ Debug shell access: `docker compose -f docker-compose.dev.yml exec backend bash`
- ✅ Enhanced error reporting
- ✅ Debug logs available with `make dev-logs`

### Test Mode

```bash
make dev-test
```

Starts the development environment with isolated test data and test-specific configurations.

**Features:**
- ✅ Isolated test environment (`.env.test`)
- ✅ Test-specific database configuration
- ✅ Mock data and test fixtures
- ✅ Test mode flags enabled (`TESTING=true`, `TEST_DATA_MODE=true`)

### Profiling Mode

```bash
make dev-profile
```

Starts the development environment with performance profiling and metrics collection.

**Features:**
- ✅ Performance monitoring enabled (`PROFILING=true`)
- ✅ Metrics collection (`METRICS_ENABLED=true`)
- ✅ Performance data available at `http://localhost:8000/metrics`
- ✅ Profiling data collected in `./logs/profiling/`

## Complete Feature Matrix

| Feature | Phase | Status | Command |
|---------|-------|--------|---------|
| Local builds by default | 1 | ✅ | `make dev-build` |
| Development environment variables | 1 | ✅ | `make dev-init` |
| Smart Make targets | 1 | ✅ | `make dev-up`, `make dev-restart` |
| Health validation | 2 | ✅ | `make dev-validate` |
| Status reporting | 2 | ✅ | `make dev-status` |
| Environment validation | 2 | ✅ | `make dev-validate` |
| Auto-rebuild on changes | 2 | ✅ | `make dev-watch` |
| Debug mode | 3 | ✅ | `make dev-debug` |
| Test mode | 3 | ✅ | `make dev-test` |
| Performance profiling | 3 | ✅ | `make dev-profile` |
| **Complete dev setup** | **170** | **✅** | **`make dev-setup`** |
| **Environment reset** | **170** | **✅** | **`make dev-reset`** |
| **Complete cleanup** | **170** | **✅** | **`make clean-all`** |
| **Test watching** | **170** | **✅** | **`make test-watch`** |
| **VS Code dev container** | **170** | **✅** | **`.devcontainer/devcontainer.json`** |

---

*This development workflow was implemented to solve Issue #210 and significantly improve the developer experience for RAG Modulo.*
