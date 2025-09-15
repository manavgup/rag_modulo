# Contributing Guidelines

Thank you for your interest in contributing to RAG Modulo! This guide will help you get started with contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Commit Message Format](#commit-message-format)
- [Code Review Process](#code-review-process)

## Getting Started

### Prerequisites

- Development environment set up (see [Environment Setup](environment-setup.md))
- Understanding of the project architecture
- Familiarity with Python, JavaScript, and Docker

### First Contribution

1. **Fork** the repository
2. **Clone** your fork locally
3. **Set up** development environment
4. **Create** a feature branch
5. **Make** your changes
6. **Test** thoroughly
7. **Submit** a pull request

## Development Workflow

### Branch Strategy

We use a feature branch workflow:

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes
# ... develop your feature ...

# Test changes
make test
make lint

# Commit changes
git add .
git commit -m "feat: implement your feature"

# Push to your fork
git push origin feature/your-feature-name
```

### Branch Naming Convention

- `feature/description`: New features
- `fix/description`: Bug fixes
- `docs/description`: Documentation updates
- `test/description`: Test improvements
- `refactor/description`: Code refactoring
- `perf/description`: Performance improvements

### Development Commands

```bash
# Start development environment
make dev-setup

# Run tests
make test

# Check code quality
make lint

# Format code
make format-imports

# Run security checks
make security-check

# Generate documentation
make docs-generate
```

## Code Standards

### Python Code

#### Style Guidelines

- **PEP 8**: Follow Python style guide
- **Type Hints**: Use type annotations for all functions
- **Pydantic 2.0**: Use for data validation and settings
- **Docstrings**: Document all public functions and classes

#### Example

```python
from typing import List, Optional
from pydantic import BaseModel, Field

class UserModel(BaseModel):
    """User model with validation."""
    
    id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    name: Optional[str] = Field(None, description="User display name")
    
    def get_display_name(self) -> str:
        """Get user display name."""
        return self.name or self.email.split('@')[0]

def process_users(users: List[UserModel]) -> List[str]:
    """Process a list of users and return their display names."""
    return [user.get_display_name() for user in users]
```

#### Linting Configuration

The project uses multiple linters:

- **Ruff**: Fast Python linter and formatter
- **MyPy**: Static type checker
- **Pylint**: Code quality analysis
- **Pydocstyle**: Documentation standards

```bash
# Run all linters
make lint

# Run specific linter
make lint-ruff
make lint-mypy
make lint-pylint
make lint-pydocstyle
```

### JavaScript/React Code

#### Style Guidelines

- **ESLint**: Follow configured ESLint rules
- **Prettier**: Code formatting
- **Modern ES6+**: Use modern JavaScript features
- **TypeScript**: Prefer TypeScript for new components

#### Example

```typescript
interface UserProps {
  id: string;
  email: string;
  name?: string;
}

const UserComponent: React.FC<UserProps> = ({ id, email, name }) => {
  const displayName = name || email.split('@')[0];
  
  return (
    <div className="user-component">
      <h3>{displayName}</h3>
      <p>{email}</p>
    </div>
  );
};

export default UserComponent;
```

### Documentation

#### Markdown Standards

- Use clear, concise language
- Include code examples
- Use proper heading hierarchy
- Include table of contents for long documents

#### Code Documentation

- Document all public APIs
- Include usage examples
- Explain complex algorithms
- Document configuration options

## Testing Guidelines

### Test Types

RAG Modulo follows a comprehensive testing pyramid:

#### Atomic Tests (70%)
- Fast, isolated unit tests
- Test individual functions and methods
- Use mocks for external dependencies
- Target: < 100ms per test

#### Unit Tests (20%)
- Component-level testing
- Test classes and modules
- Integration with internal services
- Target: < 1s per test

#### Integration Tests (8%)
- Service integration testing
- Test API endpoints
- Database interactions
- Target: < 10s per test

#### End-to-End Tests (2%)
- Full workflow testing
- User journey testing
- Cross-service testing
- Target: < 60s per test

### Test Structure

```python
# tests/unit/test_user_service.py
import pytest
from unittest.mock import Mock, patch
from rag_solution.services.user_service import UserService

class TestUserService:
    """Test suite for UserService."""
    
    @pytest.fixture
    def user_service(self):
        """Create UserService instance for testing."""
        return UserService()
    
    @pytest.fixture
    def mock_user_data(self):
        """Mock user data for testing."""
        return {
            "id": "test-user-123",
            "email": "test@example.com",
            "name": "Test User"
        }
    
    def test_create_user_success(self, user_service, mock_user_data):
        """Test successful user creation."""
        # Arrange
        expected_user = UserModel(**mock_user_data)
        
        # Act
        result = user_service.create_user(mock_user_data)
        
        # Assert
        assert result.id == expected_user.id
        assert result.email == expected_user.email
        assert result.name == expected_user.name
    
    def test_create_user_validation_error(self, user_service):
        """Test user creation with invalid data."""
        # Arrange
        invalid_data = {"email": "invalid-email"}
        
        # Act & Assert
        with pytest.raises(ValidationError):
            user_service.create_user(invalid_data)
```

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

# Run tests in watch mode
make test-watch

# Run specific test file
pytest tests/unit/test_user_service.py -v

# Run specific test method
pytest tests/unit/test_user_service.py::TestUserService::test_create_user_success -v
```

### Test Data Management

- Use fixtures for reusable test data
- Mock external services
- Use test-specific databases
- Clean up after tests

## Pull Request Process

### Before Submitting

1. **Ensure tests pass**: `make test`
2. **Check code quality**: `make lint`
3. **Update documentation**: If needed
4. **Add tests**: For new functionality
5. **Update changelog**: If applicable

### Pull Request Template

```markdown
## Description

Brief description of changes.

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Testing

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Performance testing (if applicable)

## Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] No breaking changes (or documented)
```

### Review Process

1. **Automated checks**: CI/CD pipeline runs tests and linting
2. **Code review**: At least one maintainer reviews the code
3. **Testing**: Reviewer tests the changes
4. **Approval**: Maintainer approves the PR
5. **Merge**: PR is merged to main branch

## Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements
- `ci`: CI/CD changes
- `build`: Build system changes

### Examples

```bash
# Feature
git commit -m "feat(auth): add OAuth2 authentication support"

# Bug fix
git commit -m "fix(search): resolve vector search timeout issue"

# Documentation
git commit -m "docs(api): update authentication endpoints documentation"

# Breaking change
git commit -m "feat(api)!: change user endpoint response format

BREAKING CHANGE: User endpoint now returns user object instead of user ID"
```

## Code Review Process

### For Contributors

- **Self-review**: Review your own code before submitting
- **Test thoroughly**: Ensure all tests pass
- **Document changes**: Update relevant documentation
- **Respond to feedback**: Address review comments promptly

### For Reviewers

- **Check functionality**: Ensure the code works as intended
- **Review for bugs**: Look for potential issues
- **Check style**: Ensure code follows project standards
- **Test changes**: Run tests and manual testing
- **Provide feedback**: Give constructive feedback

### Review Checklist

- [ ] Code follows project style guidelines
- [ ] Tests are comprehensive and pass
- [ ] Documentation is updated
- [ ] No breaking changes (or properly documented)
- [ ] Performance impact considered
- [ ] Security implications reviewed
- [ ] Error handling is appropriate
- [ ] Logging is adequate

## Getting Help

### Resources

- **Documentation**: Check project documentation
- **Issues**: Search existing GitHub issues
- **Discussions**: Use GitHub Discussions for questions
- **Code examples**: Look at existing code for patterns

### Contact

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Pull Requests**: For code contributions

## Recognition

Contributors are recognized in:

- **CONTRIBUTORS.md**: List of all contributors
- **Release notes**: Mentioned in relevant releases
- **GitHub**: Contributor statistics and activity

Thank you for contributing to RAG Modulo! 🎉
