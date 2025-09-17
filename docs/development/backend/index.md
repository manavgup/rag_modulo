# Backend Development Documentation

This section contains development-specific documentation for the RAG Modulo backend.

## Development Guidelines

- **[Development Prompt](development_prompt.md)** - Comprehensive guidelines for working with the system
- **[TODO Items](todo.md)** - Development tasks and improvements

## Architecture Overview

The backend follows a service-based architecture with:

1. **Service Layer**: Business logic implementation
2. **Repository Pattern**: Data access abstraction
3. **Provider System**: LLM and vector store providers
4. **Router Layer**: API endpoint definitions
5. **Schema Layer**: Data validation and serialization

## Key Design Principles

1. **Dependency Injection**: Services are injected for testability
2. **Async Operations**: Use async/await for I/O operations
3. **Type Safety**: Comprehensive type hints throughout
4. **Error Handling**: Custom exceptions with clear messages
5. **Testing**: Unit, integration, and API tests

## Development Workflow

1. Follow TDD (Test-Driven Development) approach
2. Write tests before implementation
3. Use service abstractions for all business logic
4. Implement proper error handling
5. Document all public APIs

## Code Quality Standards

- **Line Length**: 120 characters for Python code
- **Type Hints**: Required for all function signatures
- **Docstrings**: Required for all public methods
- **Error Handling**: Use custom exceptions appropriately
- **Testing**: Maintain high test coverage

## Next Steps

- Review the [main development guide](../index.md)
- Check the [contributing guidelines](../contributing.md)
- See the [workflow documentation](../workflow.md)
