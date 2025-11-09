# Contributing to RAG Modulo

Thank you for your interest in contributing to RAG Modulo! This guide will help you get started.

## Getting Started

1. **Fork the Repository**
   - Fork the [RAG Modulo repository](https://github.com/manavgup/rag_modulo)
   - Clone your fork locally

2. **Set Up Development Environment**
   - Follow the [Installation Guide](installation.md)
   - Run `make local-dev-setup` to install dependencies
   - Start infrastructure: `make local-dev-infra`

## Development Workflow

### Making Changes

1. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Your Changes**
   - Follow our [Code Quality Standards](development/code-quality-standards.md)
   - Write tests for new functionality
   - Update documentation as needed

3. **Run Tests**
   ```bash
   make test-atomic      # Fast schema tests (~5 sec)
   make test-unit-fast   # Unit tests (~30 sec)
   make test-integration # Integration tests (~2 min)
   ```

4. **Run Linting**
   ```bash
   make pre-commit-run   # Full pre-commit checks
   make quick-check      # Fast format check
   ```

### Code Quality Requirements

- **Line Length**: 120 characters maximum
- **Type Hints**: Required for all functions
- **Test Coverage**: Minimum 60%
- **Linting**: All Ruff, MyPy, and Pylint checks must pass

See [Development Workflow](development/workflow.md) for details.

### Commit Guidelines

- Use descriptive commit messages
- Follow conventional commits format:
  - `feat:` - New features
  - `fix:` - Bug fixes
  - `docs:` - Documentation changes
  - `test:` - Test changes
  - `refactor:` - Code refactoring
  - `chore:` - Maintenance tasks

### Pull Request Process

1. **Create Pull Request**
   - Push your branch to your fork
   - Create PR against `main` branch
   - Fill out PR template completely

2. **CI/CD Checks**
   - All tests must pass
   - Linting checks must pass
   - Security scans must pass

3. **Code Review**
   - Address review feedback
   - Keep PR focused on single feature/fix
   - Rebase if needed to keep history clean

## Testing Guidelines

- Write unit tests for new services/functions
- Add integration tests for new features
- Ensure tests are isolated and reproducible
- Use fixtures for common test data

See [Testing Guide](testing/index.md) for comprehensive testing documentation.

## Documentation

- Update documentation for new features
- Add docstrings to all public functions/classes
- Update API documentation if changing endpoints
- Keep README.md and CLAUDE.md current

## Questions?

- Check [FAQ](faq.md)
- Review [Development Docs](development/index.md)
- Open an issue for questions

## Code of Conduct

Be respectful, constructive, and collaborative. We're all here to build great software together.

---

*Thank you for contributing to RAG Modulo!*
