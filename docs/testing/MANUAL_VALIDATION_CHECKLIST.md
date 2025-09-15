# Manual Validation Checklist

This checklist ensures all Makefile targets work correctly and handle edge cases properly.

## Prerequisites

- [ ] Docker Desktop is running
- [ ] Git is installed
- [ ] Make is available
- [ ] Project is cloned locally

## Core Development Targets

### 1. Environment Initialization

#### `make dev-init`
- [ ] **Creates `.env.dev` file**
  ```bash
  make dev-init
  ls -la .env.dev
  ```
- [ ] **File contains expected variables**
  ```bash
  grep -q "DEVELOPMENT_MODE=true" .env.dev
  grep -q "TESTING=true" .env.dev
  grep -q "SKIP_AUTH=true" .env.dev
  ```
- [ ] **Handles existing file gracefully**
  ```bash
  make dev-init  # Should not overwrite existing .env.dev
  ```

#### `make dev-build`
- [ ] **Builds backend image**
  ```bash
  make dev-build
  docker images | grep "rag-modulo.*backend.*dev"
  ```
- [ ] **Builds frontend image**
  ```bash
  docker images | grep "rag-modulo.*frontend.*dev"
  ```
- [ ] **Shows build progress**
  ```bash
  make dev-build  # Should show "Building development images..."
  ```
- [ ] **Handles build failures gracefully**
  ```bash
  # Simulate build failure and verify error handling
  ```

### 2. Service Management

#### `make dev-up`
- [ ] **Starts all services**
  ```bash
  make dev-up
  docker ps | grep "rag_modulo-dev"
  ```
- [ ] **Shows service URLs**
  ```bash
  make dev-up  # Should show Backend: http://localhost:8000
  ```
- [ ] **Creates volume directories**
  ```bash
  ls -la volumes/
  ```
- [ ] **Handles port conflicts**
  ```bash
  # Start another service on port 8000, then run make dev-up
  # Should show clear error message
  ```

#### `make dev-down`
- [ ] **Stops all services**
  ```bash
  make dev-down
  docker ps | grep "rag_modulo-dev"  # Should be empty
  ```
- [ ] **Shows confirmation message**
  ```bash
  make dev-down  # Should show "Development environment stopped"
  ```

#### `make dev-restart`
- [ ] **Rebuilds and restarts**
  ```bash
  make dev-restart
  docker ps | grep "rag_modulo-dev"
  ```
- [ ] **Shows restart progress**
  ```bash
  make dev-restart  # Should show "Rebuilding and restarting..."
  ```

### 3. Validation and Status

#### `make dev-validate`
- [ ] **Checks image existence**
  ```bash
  make dev-validate  # Should show "✅ Backend development image found"
  ```
- [ ] **Checks container status**
  ```bash
  make dev-validate  # Should show "✅ All containers running"
  ```
- [ ] **Tests backend health**
  ```bash
  make dev-validate  # Should show "✅ Backend is healthy"
  ```
- [ ] **Tests frontend health**
  ```bash
  make dev-validate  # Should show "✅ Frontend is healthy"
  ```

#### `make dev-status`
- [ ] **Shows image status**
  ```bash
  make dev-status  # Should list all development images
  ```
- [ ] **Shows container status**
  ```bash
  make dev-status  # Should list all running containers
  ```
- [ ] **Shows service URLs**
  ```bash
  make dev-status  # Should show service URLs
  ```

#### `make dev-logs`
- [ ] **Shows backend logs**
  ```bash
  make dev-logs  # Should show backend container logs
  ```
- [ ] **Shows frontend logs**
  ```bash
  make dev-logs  # Should show frontend container logs
  ```
- [ ] **Shows all service logs**
  ```bash
  make dev-logs  # Should show logs from all services
  ```

### 4. Environment Management

#### `make dev-reset`
- [ ] **Stops services**
  ```bash
  make dev-reset  # Should stop all containers
  ```
- [ ] **Removes containers**
  ```bash
  make dev-reset  # Should remove containers
  ```
- [ ] **Prunes volumes**
  ```bash
  make dev-reset  # Should clean up volumes
  ```
- [ ] **Shows reset progress**
  ```bash
  make dev-reset  # Should show "Resetting development environment..."
  ```

#### `make clean-all`
- [ ] **Removes all images**
  ```bash
  make clean-all
  docker images | grep "rag-modulo"  # Should be empty
  ```
- [ ] **Removes all containers**
  ```bash
  docker ps -a | grep "rag_modulo"  # Should be empty
  ```
- [ ] **Removes all volumes**
  ```bash
  docker volume ls | grep "rag_modulo"  # Should be empty
  ```
- [ ] **Shows cleanup progress**
  ```bash
  make clean-all  # Should show "Cleaning up all development resources..."
  ```

### 5. Advanced Features

#### `make dev-setup`
- [ ] **Performs complete setup**
  ```bash
  make dev-setup  # Should run dev-init, dev-build, dev-up, dev-validate
  ```
- [ ] **Shows setup progress**
  ```bash
  make dev-setup  # Should show each step
  ```
- [ ] **Provides next steps**
  ```bash
  make dev-setup  # Should show "Next steps: make dev-logs"
  ```

#### `make test-watch`
- [ ] **Starts file watcher**
  ```bash
  make test-watch  # Should start watching test files
  ```
- [ ] **Runs tests on file change**
  ```bash
  # Modify a test file and verify tests run
  ```
- [ ] **Handles missing watcher gracefully**
  ```bash
  # Test on system without fswatch/inotifywait
  ```

#### `make help`
- [ ] **Shows all commands**
  ```bash
  make help  # Should show all available targets
  ```
- [ ] **Shows development workflow section**
  ```bash
  make help  # Should show "Development Workflow" section
  ```
- [ ] **Shows command descriptions**
  ```bash
  make help  # Should show descriptions for each command
  ```

## Error Handling Tests

### Missing Dependencies
- [ ] **Docker not running**
  ```bash
  # Stop Docker Desktop, then run make dev-up
  # Should show clear error message
  ```
- [ ] **Docker not installed**
  ```bash
  # Test on system without Docker
  # Should show installation instructions
  ```

### Port Conflicts
- [ ] **Backend port 8000 in use**
  ```bash
  # Start another service on port 8000
  make dev-up  # Should show port conflict error
  ```
- [ ] **Frontend port 3000 in use**
  ```bash
  # Start another service on port 3000
  make dev-up  # Should show port conflict error
  ```

### File System Issues
- [ ] **No write permissions**
  ```bash
  # Make volumes directory read-only
  make dev-up  # Should show permission error
  ```
- [ ] **Disk space full**
  ```bash
  # Simulate disk full scenario
  make dev-build  # Should show disk space error
  ```

### Network Issues
- [ ] **No internet connection**
  ```bash
  # Disconnect from internet
  make dev-build  # Should handle network errors gracefully
  ```

## Performance Tests

### Build Times
- [ ] **Initial build time**
  ```bash
  time make dev-build  # Should complete within reasonable time
  ```
- [ ] **Incremental build time**
  ```bash
  make dev-build  # Second build should be faster
  ```

### Startup Times
- [ ] **Service startup time**
  ```bash
  time make dev-up  # Should start within reasonable time
  ```
- [ ] **Validation time**
  ```bash
  time make dev-validate  # Should validate quickly
  ```

## Integration Tests

### Complete Workflow
- [ ] **Fresh start to running**
  ```bash
  make clean-all
  make dev-setup
  # Should result in fully working environment
  ```

### Hot Reloading
- [ ] **Backend code changes**
  ```bash
  # Edit Python file in backend/
  # Changes should be visible immediately
  ```
- [ ] **Frontend code changes**
  ```bash
  # Edit React file in webui/
  # Changes should be visible immediately
  ```

### CLI Integration
- [ ] **CLI commands work**
  ```bash
  poetry run python -m rag_solution.cli.main --help
  poetry run python -m rag_solution.cli.main health check
  ```

## Documentation Tests

### Command Documentation
- [ ] **All commands documented**
  ```bash
  make help  # Should show all commands from docs
  ```
- [ ] **Examples work**
  ```bash
  # Test all examples from documentation
  ```

### README Instructions
- [ ] **Quick start works**
  ```bash
  # Follow README quick start exactly
  ```
- [ ] **All links work**
  ```bash
  # Check all documentation links
  ```

## Sign-off

- [ ] **All core targets work**
- [ ] **Error handling is robust**
- [ ] **Performance is acceptable**
- [ ] **Documentation is accurate**
- [ ] **Integration tests pass**

**Validated by**: _________________  
**Date**: _________________  
**Environment**: _________________
