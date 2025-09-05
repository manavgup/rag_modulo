# RAG Solution Test Suite

This directory contains the test suite for the RAG solution, implementing comprehensive testing with strong typing and validation.

## 🏗️ Test Structure

The test suite is organized into the following categories:

### Unit Tests (`@pytest.mark.unit`)
- Test individual components in isolation
- Located in `tests/test_*.py`
- Fast execution, no external dependencies
- Focus on business logic and validation

### Integration Tests (`@pytest.mark.integration`)
- Test multiple components working together
- Located in `tests/integration/`
- Test end-to-end flows
- Verify component interactions

### Error Tests (`@pytest.mark.error`)
- Verify error handling and edge cases
- Test validation failures
- Test boundary conditions
- Test error recovery

### Performance Tests (`@pytest.mark.performance`)
- Measure system performance
- Located in `tests/performance/`
- Benchmark critical operations
- Test under load conditions

## 🚀 Running Tests

### Basic Usage
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_specific_file.py

# Run tests with specific marker
pytest -m unit
pytest -m integration
pytest -m error
pytest -m performance

# Run tests with coverage report
pytest --cov=rag_solution
```

### Test Markers
- `unit`: Unit tests
- `integration`: Integration tests
- `error`: Error handling tests
- `performance`: Performance tests
- `service`: Service layer tests
- `repository`: Repository layer tests
- `schema`: Schema validation tests
- `router`: API endpoint tests
- `auth`: Authentication tests
- `watsonx`: WatsonX integration tests
- `pipeline`: RAG pipeline tests
- `config`: Configuration tests
- `slow`: Long-running tests

## 📝 Writing Tests

### Test Organization
- Use appropriate markers for test categorization
- Follow naming conventions:
  - Files: `test_*.py`
  - Classes: `Test*`
  - Functions: `test_*`
- Group related tests in classes
- Use descriptive test names

### Test Best Practices
1. Use strong typing with type hints
2. Use proper assertions
3. Use fixtures for setup/teardown
4. Test both success and failure cases
5. Test edge cases and boundaries
6. Use meaningful test data
7. Keep tests focused and isolated
8. Document test purpose and requirements
9. Use appropriate markers
10. Clean up test resources

### Example Test with Atomic Fixtures
```python
import pytest
from pydantic import UUID4
from typing import Optional, List
from datetime import datetime

from rag_solution.models.user import User
from rag_solution.models.collection import Collection
from rag_solution.models.question import SuggestedQuestion
from rag_solution.services.question_service import QuestionService

# Atomic Model Fixtures in conftest.py
@pytest.fixture
def base_user(db_session) -> User:
    """Create a base user model."""
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def base_collection(db_session, base_user) -> Collection:
    """Create a base collection model."""
    collection = Collection(
        name="Test Collection",
        is_private=False,
        vector_db_name="test_collection",
        users=[base_user]
    )
    db_session.add(collection)
    db_session.commit()
    return collection

# Test Class Using Atomic Fixtures
@pytest.mark.integration
class TestQuestionGeneration:
    """Test question generation functionality."""

    async def test_suggest_questions(
        self,
        question_service: QuestionService,
        base_user: User,
        base_collection: Collection,
        test_documents: List[str]
    ) -> None:
        """Test successful question generation."""
        # Generate questions
        questions = await question_service.suggest_questions(
            texts=test_documents,
            collection_id=base_collection.id,
            user_id=base_user.id,
            num_questions=3
        )

        # Verify results
        assert len(questions) > 0
        for question in questions:
            # Verify model attributes
            assert isinstance(question, SuggestedQuestion)
            assert question.collection_id == base_collection.id
            assert isinstance(question.question, str)
            assert question.question.endswith('?')
            assert len(question.question) >= 10
            assert len(question.question) <= 500
            assert isinstance(question.created_at, datetime)
            assert question.is_valid
```

## 🔧 Configuration

### pytest.ini
- Test discovery paths
- Logging configuration
- Test markers
- Test execution options
- Environment variables
- Coverage settings

### conftest.py
- Shared fixtures
- Database setup/teardown
- Environment setup
- Test data setup

## 📊 Test Coverage

Coverage reports can be generated using:
```bash
# Generate coverage report
pytest --cov=rag_solution --cov-report=html

# View report
open htmlcov/index.html
```

### Coverage Goals
- Aim for high test coverage (>90%)
- Focus on critical paths
- Test edge cases
- Test error conditions
- Test configuration variations

## 🐛 Debugging Tests

### Debug Options
```bash
# Show local variables in failures
pytest --showlocals

# Increase verbosity
pytest -vv

# Show slow tests
pytest --durations=10

# Stop on first failure
pytest -x
```

### Common Issues
1. Database cleanup between tests
2. Environment variable conflicts
3. Resource cleanup
4. Test isolation
5. Async/await usage
6. Fixture scope
7. Test ordering
8. Resource leaks

## 🔍 Code Quality

The test suite enforces:
- Strong typing with type hints
- Pydantic 2.0 validation
- Proper error handling
- Clear documentation
- Test isolation
- Resource cleanup
- Performance monitoring
- Coverage tracking

## 📚 Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [WatsonX Documentation](https://www.ibm.com/products/watsonx-ai)
