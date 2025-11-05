# Test Isolation Guidelines

> **Note**: This document references legacy `vectordbs.utils.watsonx` patterns. The codebase has migrated
> to `LLMProviderFactory`. See Issue #219 for details.

This document outlines the principles and practices for maintaining proper test isolation in the RAG Modulo project, particularly for atomic tests.

## Overview

Test isolation ensures that tests run independently without external dependencies, making them:
- **Fast**: No network calls or external service connections
- **Reliable**: Deterministic results regardless of environment
- **Portable**: Run anywhere without configuration
- **Maintainable**: Easy to debug and modify

## Test Categories

### Atomic Tests (`@pytest.mark.atomic`)

Atomic tests are the most isolated tests and should:
- ✅ Run without any environment variables
- ✅ Use mocking for all external dependencies
- ✅ Execute instantly without network calls
- ✅ Be completely deterministic

### Integration Tests (`@pytest.mark.integration`)

Integration tests can use real services but should:
- ✅ Use test-specific configuration
- ✅ Clean up after themselves
- ✅ Be marked appropriately

## Common Violations and Fixes

### ❌ **Violation: Direct Settings Access**

```python
# BAD - Accesses global settings
from core.config import settings

@pytest.mark.atomic
def test_something():
    assert settings.jwt_secret_key is not None
```

**✅ Fix: Use Mocking**

```python
# GOOD - Uses fixtures and mocking
@pytest.mark.atomic
def test_something(mock_settings):
    assert mock_settings.jwt_secret_key == "test-secret"
```

### ❌ **Violation: Module-Level API Calls**

```python
# BAD - Real API call at module level
from vectordbs.utils.watsonx import get_embeddings

sample_document = Document(
    vectors=get_embeddings(text),  # Real API call!
)
```

**✅ Fix: Move to Test Function**

```python
# GOOD - API call in test function with mocking
@pytest.mark.atomic
def test_document():
    with patch("vectordbs.utils.watsonx.get_embeddings", return_value=[0.1, 0.2, 0.3]):
        sample_document = Document(vectors=get_embeddings(text))
```

### ❌ **Violation: Conditional Skips Based on Real Settings**

```python
# BAD - Depends on real environment
@pytest.mark.skipif(
    not settings.wx_api_key,
    reason="WatsonX credentials not configured"
)
```

**✅ Fix: Remove Conditional Skips**

```python
# GOOD - Always run with mocking
@pytest.mark.atomic
@patch("rag_solution.services.question_service.ProviderFactory")
def test_question_generation(mock_provider_factory):
    # Test with mocked provider
```

## Available Fixtures

The project provides several fixtures for test isolation:

### Environment Fixtures

```python
def test_with_mock_env(mock_settings):
    """Test with mocked environment variables."""
    assert mock_settings.jwt_secret_key == "test-secret-key"

def test_with_minimal_env(minimal_test_env):
    """Test with minimal required environment variables."""
    settings = Settings()
    assert settings.rag_llm == "watsonx"

def test_isolated(isolated_test_env):
    """Test in completely isolated environment."""
    # Should fail if settings require real env vars
    with pytest.raises(Exception):
        Settings()
```

### Service Fixtures

```python
def test_with_mock_provider(mock_watsonx_provider):
    """Test with mocked WatsonX provider."""
    result = mock_watsonx_provider.get_embeddings("test")
    assert result == [0.1, 0.2, 0.3]

def test_with_mock_vector_store(mock_vector_store):
    """Test with mocked vector store."""
    mock_vector_store.retrieve_documents.return_value = []
    results = mock_vector_store.retrieve_documents("query")
    assert results == []
```

## Best Practices

### 1. Use Fixtures Instead of Global Imports

```python
# BAD
from core.config import settings

# GOOD
def test_something(mock_settings):
    pass
```

### 2. Mock External Dependencies

```python
# BAD
def test_api_call():
    result = real_api_call()

# GOOD
@patch("module.real_api_call")
def test_api_call(mock_api):
    mock_api.return_value = "mocked_result"
    result = real_api_call()
```

### 3. Use Dependency Injection

```python
# BAD
class Service:
    def __init__(self):
        self.settings = settings  # Global dependency

# GOOD
class Service:
    def __init__(self, settings=None):
        self.settings = settings or Settings()
```

### 4. Test Error Conditions

```python
@pytest.mark.atomic
def test_error_handling():
    with patch("module.external_call", side_effect=Exception("Network error")):
        with pytest.raises(ServiceError):
            service.do_something()
```

## Linting and Validation

### Pre-commit Hooks

The project includes pre-commit hooks that automatically check for test isolation violations:

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run check-test-isolation
```

### CI Validation

The CI pipeline includes a dedicated job that runs atomic tests without any environment variables to ensure proper isolation.

### Manual Checking

```bash
# Run test isolation checker
python scripts/check_test_isolation.py

# Run atomic tests without env vars
cd backend && poetry run pytest tests/ -m atomic
```

## Common Patterns

### Testing Configuration

```python
@pytest.mark.atomic
def test_config_loading(mock_env_vars):
    """Test configuration loading with mocked environment."""
    with patch.dict(os.environ, mock_env_vars, clear=True):
        config = Settings()
        assert config.jwt_secret_key == "test-secret-key"
```

### Testing Services

```python
@pytest.mark.atomic
def test_service_initialization(mock_settings, mock_vector_store):
    """Test service initialization with mocked dependencies."""
    service = MyService(settings=mock_settings, vector_store=mock_vector_store)
    assert service.is_initialized
```

### Testing API Calls

```python
@pytest.mark.atomic
@patch("external.api.call")
def test_api_integration(mock_api_call):
    """Test API integration with mocked external calls."""
    mock_api_call.return_value = {"status": "success"}
    result = my_function()
    assert result["status"] == "success"
```

## Troubleshooting

### Test Fails Without Environment Variables

**Problem**: Test requires real environment variables to run.

**Solution**: Use fixtures and mocking instead of accessing global settings.

### Test Makes Real API Calls

**Problem**: Test is calling external services.

**Solution**: Mock the external service calls using `@patch` decorators.

### Test Depends on External Services

**Problem**: Test requires database, vector store, or other services.

**Solution**: Use mocked versions of these services or mark as integration test.

## Resources

- [Pytest Fixtures Documentation](https://docs.pytest.org/en/stable/fixture.html)
- [Python Mocking Guide](https://docs.python.org/3/library/unittest.mock.html)
- [Test Isolation Best Practices](https://martinfowler.com/articles/nonDeterminism.html)
