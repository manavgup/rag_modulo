# Development Guide

Welcome to the RAG Modulo development guide! This comprehensive documentation will help you set up, build, test, and contribute to the RAG Modulo project.

## Table of Contents

- [Quick Start](#quick-start)
- [Development Environment Setup](#development-environment-setup)
- [Building the Project](#building-the-project)
- [Running Tests](#running-tests)
- [Development Workflow](#development-workflow)
- [Contributing Guidelines](#contributing-guidelines)
- [Troubleshooting](#troubleshooting)

## Quick Start

Get up and running in under 5 minutes:

```bash
# Clone the repository
git clone https://github.com/manavgup/rag_modulo.git
cd rag_modulo

# One-command development setup
make dev-setup

# Start coding!
```

That's it! Your development environment is ready. See [Development Environment Setup](#development-environment-setup) for detailed information.

## Development Environment Setup

### Prerequisites

- **Docker & Docker Compose**: Required for containerized development
- **Make**: For running development commands
- **Git**: For version control
- **VS Code** (optional): For enhanced development experience with dev containers

### System Requirements

- **macOS**: 10.15+ (Catalina or later)
- **Linux**: Ubuntu 20.04+ or equivalent
- **Windows**: Windows 10+ with WSL2
- **RAM**: Minimum 8GB, recommended 16GB
- **Storage**: At least 10GB free space

### Installation Steps

#### 1. Clone the Repository

```bash
git clone https://github.com/manavgup/rag_modulo.git
cd rag_modulo
```

#### 2. Initialize Development Environment

```bash
# One-command setup (recommended)
make dev-setup

# OR manual setup
make dev-init
make dev-build
make dev-up
make dev-validate
```

#### 3. Verify Installation

```bash
# Check that everything is working
make dev-status

# Test the API
curl http://localhost:8000/health
```

### Development Environment Features

- ✅ **Hot Reloading**: Backend changes reflect immediately
- ✅ **File Watching**: Auto-rebuild on file changes (`make dev-watch`)
- ✅ **Debug Mode**: Enhanced debugging (`make dev-debug`)
- ✅ **Test Mode**: Isolated test environment (`make dev-test`)
- ✅ **Profiling**: Performance monitoring (`make dev-profile`)
- ✅ **VS Code Integration**: Complete dev container support

## Building the Project

### Development Builds

```bash
# Build all development images
make dev-build

# Build specific components
make build-backend-local
make build-frontend-local
make build-tests-local
```

### Production Builds

```bash
# Build production images
make build-backend
make build-frontend
make build-all
```

### Build Configuration

The project uses multi-stage Docker builds for optimization:

- **Development**: Includes dev tools, debugging, hot reload
- **Production**: Optimized for size and security
- **Testing**: Includes test dependencies and fixtures

## Running Tests

### Test Types

RAG Modulo follows a comprehensive testing pyramid:

- **Atomic Tests**: Fast, isolated unit tests
- **Unit Tests**: Component-level testing
- **Integration Tests**: Service integration testing
- **End-to-End Tests**: Full workflow testing

### Running Tests

```bash
# Run all tests
make test

# Run specific test types
make test-atomic
make test-unit
make test-integration
make test-e2e

# Run tests with coverage
make coverage

# Watch tests (auto-run on file changes)
make test-watch
```

### Test Configuration

Tests are configured with:
- **Pytest**: Test framework
- **Coverage**: Code coverage reporting
- **Mocking**: Isolated testing
- **Fixtures**: Reusable test data

### Development Test Scripts

In addition to the automated test suite, RAG Modulo includes manual development test scripts for debugging, feature exploration, and performance testing. These scripts are located in `backend/dev_tests/` and are NOT part of the CI/CD pipeline.

For comprehensive documentation on all available development test scripts, including usage examples, prerequisites, and expected outputs, see:

📖 **[Development Test Scripts Guide](dev-test-scripts.md)**

Quick examples:
```bash
cd backend

# Test Chain of Thought reasoning
python dev_tests/manual/test_cot_comparison.py

# Test embedding models
python dev_tests/manual/test_embedding_models.py

# Debug RAG failures
python dev_tests/manual/debug_rag_failure.py
```

## Development Workflow

### Daily Development

```bash
# Start development session
make dev-up

# Make changes to code
# Changes are automatically reflected (hot reload)

# Run tests
make test-atomic

# Check code quality
make lint

# Commit changes
git add .
git commit -m "feat: your feature description"
```

### Feature Development

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Set up development environment
make dev-setup

# Develop your feature
# ... make changes ...

# Test your changes
make test-watch

# Validate before commit
make lint
make test

# Commit and push
git add .
git commit -m "feat: implement your feature"
git push origin feature/your-feature-name
```

### Debugging

```bash
# Start in debug mode
make dev-debug

# Access debug shell
docker compose -f docker-compose.dev.yml exec backend bash

# View debug logs
make dev-logs

# Profile performance
make dev-profile
```

## Contributing Guidelines

### Code Standards

- **Python**: Follow PEP 8, use type hints, Pydantic 2.0
- **JavaScript**: ESLint configuration, modern ES6+
- **Documentation**: Markdown, clear and comprehensive
- **Testing**: Comprehensive test coverage

### Pre-commit Hooks

The project uses pre-commit hooks for code quality:

```bash
# Install pre-commit hooks
pre-commit install

# Run all hooks manually
make pre-commit-run
```

Hooks include:
- **Ruff**: Python linting and formatting
- **MyPy**: Type checking
- **Pylint**: Code quality analysis
- **Pydocstyle**: Documentation standards

### Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** thoroughly
5. **Submit** a pull request

### Commit Message Format

Use conventional commits:

```
feat: add new feature
fix: resolve bug
docs: update documentation
test: add tests
refactor: code refactoring
```

## Troubleshooting

### Common Issues

#### Development Environment Won't Start

```bash
# Reset development environment
make dev-reset

# Check Docker status
docker ps
docker compose -f docker-compose.dev.yml ps
```

#### Tests Failing

```bash
# Run tests with verbose output
make test-atomic -- -v

# Check test logs
make dev-logs
```

#### Build Issues

```bash
# Clean build cache
docker builder prune -f

# Rebuild from scratch
make clean-all
make dev-build
```

#### Port Conflicts

```bash
# Check what's using ports
lsof -i :8000
lsof -i :3000

# Stop conflicting services
make dev-down
```

### Getting Help

- **Issues**: Create a GitHub issue
- **Discussions**: Use GitHub Discussions
- **Documentation**: Check this guide and inline docs

### Development Tools

- **VS Code**: Recommended IDE with dev container support
- **Docker Desktop**: Container management
- **Postman/Insomnia**: API testing
- **Git**: Version control

## Next Steps

- [Deployment Guide](../deployment/README.md)
- [CLI Documentation](../cli/README.md)
- [API Documentation](../api/README.md)
- [Architecture Overview](../architecture/README.md)
