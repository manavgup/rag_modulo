# Playwright E2E Tests for RAG Modulo

Comprehensive end-to-end testing suite for the RAG Modulo application using Playwright. Based on IBM MCP Context Forge testing patterns.

## 🎯 Test Coverage

### Test Categories

- **🔥 Smoke Tests** (`test_smoke.py`) - Quick validation of basic functionality
- **🔐 Authentication Tests** (`test_auth.py`) - Mock auth and access control
- **🔌 API Integration Tests** (`test_api_integration.py`) - Frontend-backend communication
- **🔄 E2E Workflow Tests** (`test_search_workflow.py`) - Complete user journeys

### Features Tested

- ✅ Application health and basic navigation
- ✅ Mock authentication bypass for development
- ✅ Collections CRUD operations
- ✅ Document upload and management
- ✅ Real-time chat with WebSocket integration
- ✅ Search functionality with source attribution
- ✅ Error handling and edge cases
- ✅ Mobile responsive layouts

## 🚀 Quick Start

### Prerequisites

```bash
# Install Python dependencies
cd tests/playwright
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Running Tests

```bash
# From project root - all tests with mock auth
make playwright-all

# Individual test categories
make playwright-smoke    # Quick smoke tests (~30s)
make playwright-auth     # Authentication tests
make playwright-api      # API integration tests
make playwright-e2e      # End-to-end workflows

# Debug mode (visible browser)
make playwright-debug
make playwright-headed   # Smoke tests with visible browser
```

### Manual Setup

```bash
# Start application with mock auth
make dev

# Run specific tests
cd tests/playwright
FRONTEND_URL=http://localhost:3000 BACKEND_URL=http://localhost:8000 pytest test_smoke.py -v

# Run with visible browser
HEADLESS=false pytest test_smoke.py -v
```

## 📁 Project Structure

```
tests/playwright/
├── conftest.py                 # Pytest configuration and fixtures
├── pytest.ini                 # Test execution settings
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
├── pages/                      # Page Object Model
│   ├── base_page.py           # Common page functionality
│   ├── collections_page.py    # Collections management pages
│   └── search_page.py         # Search/chat interface
│
├── fixtures/                  # Test data and utilities
│   └── test_data.py           # Sample data and test helpers
│
├── test_smoke.py              # Basic application health tests
├── test_auth.py               # Authentication and access control
├── test_api_integration.py    # Frontend-backend integration
└── test_search_workflow.py    # End-to-end user workflows
```

## 🏗️ Architecture

### Page Object Model

Tests use the Page Object Model pattern for maintainability:

```python
# Example usage
collections_page = CollectionsPage(page)
collections_page.navigate()
collections_page.create_collection("Test Collection", "Description")
collections_page.assert_collection_exists("Test Collection")
```

### Test Fixtures

- **`authenticated_page`** - Pre-configured page with mock auth
- **`test_collection_data`** - Sample collection data
- **`test_search_queries`** - Common search queries

### Environment Configuration

```bash
# Environment variables
FRONTEND_URL=http://localhost:3000    # Frontend URL
BACKEND_URL=http://localhost:8000     # Backend API URL
HEADLESS=true                         # Run headless (true/false)
TEST_TIMEOUT=30000                    # Default timeout (ms)
```

## 🧪 Test Categories & Markers

### Pytest Markers

```bash
pytest -m smoke     # Quick validation tests (< 30s)
pytest -m auth      # Authentication tests
pytest -m api       # API integration tests
pytest -m e2e       # End-to-end workflows
pytest -m slow      # Long-running tests (> 2min)
```

### Test Examples

```bash
# Run only smoke tests
pytest -m smoke

# Run auth and API tests
pytest -m "auth or api"

# Exclude slow tests
pytest -m "not slow"

# Run specific test file
pytest test_smoke.py::TestSmoke::test_frontend_loads
```

## 📊 Test Reports

Tests generate HTML reports with screenshots and detailed logs:

```
test-reports/playwright/
├── smoke-report.html      # Smoke test results
├── auth-report.html       # Authentication test results
├── api-report.html        # API integration results
├── e2e-report.html        # E2E workflow results
├── full-report.html       # Complete test suite
└── junit.xml              # JUnit format for CI
```

## 🔧 Configuration

### Mock Authentication

Tests use mock authentication for development:

```python
# Automatic mock auth setup in conftest.py
context.add_init_script("""
    localStorage.setItem('access_token', 'mock-dev-token');
    localStorage.setItem('mock_auth_enabled', 'true');
""")
```

### Browser Configuration

```python
# Browser launch arguments
{
    "headless": True,
    "timeout": 30000,
    "args": [
        "--disable-web-security",
        "--no-sandbox",
        "--disable-dev-shm-usage"
    ]
}
```

## 🐛 Debugging

### Debug Mode

```bash
# Run with visible browser and console output
make playwright-debug

# Run specific test with debugging
HEADLESS=false pytest test_smoke.py::test_frontend_loads -v -s
```

### Common Issues

1. **WebSocket Connection**: Tests are designed to work with or without real WebSocket connections
2. **Timing Issues**: Uses explicit waits and proper state checking
3. **Mock Data**: Handles both real API responses and mock data gracefully
4. **Container Dependencies**: Ensure `make dev` is running before tests

### Screenshots

Failed tests automatically capture screenshots:

```
tests/screenshots/
├── test_failure_1.png
├── test_failure_2.png
└── ...
```

## 🔄 CI/CD Integration

### GitHub Actions

```yaml
- name: Run Playwright Tests
  run: |
    make dev                    # Start app with mock auth
    make playwright-smoke       # Quick validation
    make playwright-all         # Full test suite
```

### Test Dependencies

Tests require:
- Frontend application running on port 3000
- Backend API running on port 8000
- Mock authentication enabled (`SKIP_AUTH=true`)

## 📈 Performance

### Test Execution Times

- **Smoke Tests**: ~30 seconds
- **Auth Tests**: ~45 seconds
- **API Tests**: ~60 seconds
- **E2E Tests**: ~90 seconds
- **Full Suite**: ~4 minutes

### Parallel Execution

```bash
# Run tests in parallel (requires pytest-xdist)
pytest -n auto  # Auto-detect worker count
pytest -n 4     # Use 4 workers
```

## 🤝 Contributing

### Adding New Tests

1. Follow the Page Object Model pattern
2. Use descriptive test names and docstrings
3. Add appropriate pytest markers
4. Include error handling for test environments
5. Update this README with new test coverage

### Test Guidelines

- Tests should work with or without real backend
- Use explicit waits, not sleep()
- Handle both success and error scenarios
- Include assertions for key user workflows
- Keep tests focused and independent

### Example Test Structure

```python
@pytest.mark.smoke
def test_feature_works(authenticated_page: Page):
    """Test that feature works correctly."""
    # Arrange
    page_object = PageObject(authenticated_page)

    # Act
    page_object.perform_action()

    # Assert
    page_object.assert_expected_result()
```
